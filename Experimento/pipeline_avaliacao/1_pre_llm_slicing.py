"""
===============================================================================
ETAPA 1: FATIAMENTO COM PRÉ-LLM E CONSTRUÇÃO DO BANCO VETORIAL (UFBA)
VERSÃO OTIMIZADA: CACHE GLOBAL + MULTI-WORKER (1 WORKER POR CHAVE A 15 RPM)
===============================================================================
1. Cache Global de Documentos Idênticos:
   - Documentos institucionais repetidos (Estatuto, Guias SUPAC, etc.) são fatiados
     uma única vez. Para os demais 114+ cursos, o resultado é recuperado do cache em
     0,05s com cópia local, poupando centenas de chamadas desnecessárias de IA.
2. Dois Workers Paralelos (1 por Chave Gratuita):
   - Worker 0 -> GEMINI_API_KEY (limitado a 15 RPM / intervalo seguro de 4.0s)
   - Worker 1 -> GEMINI_API_KEY_2 (limitado a 15 RPM / intervalo seguro de 4.0s)
   - Rendimento conjunto de 30 RPM sem risco de estouro de quota por minuto.
3. Chave Paga com Inferência Flexível e Teto Rígido de $2.00 USD:
   - Acionada somente se ambas as chaves gratuitas esgotarem suas cotas diárias.
   - Interrompe a execução imediatamente se o custo acumulado atingir $2.00 USD.
===============================================================================
"""

import os
import sys
import json
import time
import shutil
import hashlib
import logging
import threading
from pathlib import Path
from queue import Queue
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

import pypdf
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from Experimento.pipeline_avaliacao.config import (
    EXP_DIR, AREAS_DIR, GERAL_DIR, GEMINI_FREE_KEYS, GEMINI_PAID_KEY,
    PRIMARY_MODEL, FALLBACK_MODEL, EMBEDDING_MODEL, LOGS_DIR, PROGRESS_FILE,
    BUDGET_LIMIT_USD, COST_PROMPT_TOKEN_FLEX, COST_CANDIDATE_TOKEN_FLEX, COST_EMBEDDING_TOKEN
)
from Experimento.pipeline_avaliacao.prompts import PRE_LLM_SLICING_PROMPT
from scripts.map_133_courses import COURSES_DATA, AREAS_CONHECIMENTO, get_folder_name

LOG_FILE = LOGS_DIR / "execucao_fatiamento.log"
GLOBAL_CACHE_FILE = EXP_DIR / "cache_fatiamento_global.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("PreLLMSlicing")

_CACHE_LOCK = threading.Lock()
_PROGRESS_LOCK = threading.Lock()
_COST_LOCK = threading.Lock()


def to_long_path(p: Path) -> Path:
    """Garante suporte a caminhos longos (> 260 caracteres) no Windows."""
    s = str(p.resolve())
    if os.name == "nt" and not s.startswith("\\\\?\\"):
        return Path("\\\\?\\" + s)
    return Path(s)


def safe_rel_path(p: Path, base: Path = BASE_DIR) -> str:
    """Calcula caminho relativo de forma segura mesmo com prefixos \\\\?\\ no Windows."""
    s_p = str(p.resolve()).replace("\\\\?\\", "")
    s_base = str(base.resolve()).replace("\\\\?\\", "")
    return os.path.relpath(s_p, s_base).replace("\\", "/")


def compute_file_hash(pdf_path: Path) -> str:
    """Calcula hash MD5 dos primeiros 64KB e tamanho para identificar arquivos idênticos."""
    try:
        size = to_long_path(pdf_path).stat().st_size
        with open(to_long_path(pdf_path), "rb") as f:
            h = hashlib.md5(f.read(65536)).hexdigest()
        return f"{size}_{h}"
    except Exception:
        return pdf_path.stem


class PageChunkSpec(BaseModel):
    intervalo_paginas: List[int] = Field(
        description="Array com 1 número para página única [1] ou 2 números [início, fim] para intervalos [2, 5]."
    )
    resumo: str = Field(
        description="Fichamento detalhado e objetivo cobrindo todas as normas, artigos e prazos do intervalo (máx. 800 tokens)."
    )


class DocumentSlicingOutput(BaseModel):
    chunks: List[PageChunkSpec] = Field(
        description="Divisão contígua e sequencial cobrindo da página 1 até a última página sem omissões."
    )


class BudgetExceededException(Exception):
    pass


class GlobalSlicingCache:
    """Gerencia o cache global de fatiamentos para evitar requisições repetidas de PDFs idênticos."""

    def __init__(self, cache_file: Path = GLOBAL_CACHE_FILE):
        self.cache_file = cache_file
        self.cache: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.cache_file.exists():
            try:
                with open(to_long_path(self.cache_file), "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def get(self, pdf_path: Path) -> Optional[List[Dict[str, Any]]]:
        f_hash = compute_file_hash(pdf_path)
        stem = pdf_path.stem
        with _CACHE_LOCK:
            if f"hash:{f_hash}" in self.cache:
                return self.cache[f"hash:{f_hash}"].get("chunks")
            if f"name:{stem}" in self.cache:
                return self.cache[f"name:{stem}"].get("chunks")
        return None

    def put(self, pdf_path: Path, chunks: List[Dict[str, Any]]):
        f_hash = compute_file_hash(pdf_path)
        stem = pdf_path.stem
        entry = {
            "doc_stem": stem,
            "chunks": chunks,
            "updated_at": datetime.now().isoformat()
        }
        with _CACHE_LOCK:
            self.cache[f"hash:{f_hash}"] = entry
            self.cache[f"name:{stem}"] = entry
            try:
                with open(to_long_path(self.cache_file), "w", encoding="utf-8") as f:
                    json.dump(self.cache, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.warning(f"Erro ao salvar cache global: {e}")


class KeyWorkerContext:
    """Contexto isolado de uma chave de API para controle rigoroso de RPM."""

    def __init__(self, key: str, key_name: str, is_paid: bool = False, min_interval: float = 4.0):
        self.key = key
        self.key_name = key_name
        self.is_paid = is_paid
        self.min_interval = min_interval
        self.client = genai.Client(api_key=key)
        self.last_call_time = 0.0
        self.exhausted = False
        self._lock = threading.Lock()

    def acquire_slot(self):
        with self._lock:
            elapsed = time.time() - self.last_call_time
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self.last_call_time = time.time()


class QuotaAndBudgetManager:
    """Controla custos financeiros na chave paga e salva progresso."""

    def __init__(self, total_pdfs: int):
        self.total_pdfs = total_pdfs
        self.progress_data = self._load()
        self.paid_cost_usd = self.progress_data.get("paid_cost_usd", 0.0)
        self.paid_tokens_prompt = self.progress_data.get("paid_tokens_prompt", 0)
        self.paid_tokens_candidate = self.progress_data.get("paid_tokens_candidate", 0)
        self.paid_tokens_embedding = self.progress_data.get("paid_tokens_embedding", 0)
        self.processed_pdfs = set(self.progress_data.get("processed_pdfs", []))

    def _load(self) -> Dict[str, Any]:
        if PROGRESS_FILE.exists():
            try:
                with open(to_long_path(PROGRESS_FILE), "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "processed_pdfs": [],
            "completed_courses": [],
            "paid_cost_usd": 0.0,
            "paid_tokens_prompt": 0,
            "paid_tokens_candidate": 0,
            "paid_tokens_embedding": 0
        }

    def mark_done(self, pdf_rel: str):
        with _PROGRESS_LOCK:
            self.processed_pdfs.add(pdf_rel)
            pct = (len(self.processed_pdfs) / self.total_pdfs * 100.0) if self.total_pdfs > 0 else 0.0
            self.progress_data["processed_pdfs"] = list(self.processed_pdfs)
            self.progress_data["percent_completed"] = round(pct, 2)
            self.progress_data["total_pdfs"] = self.total_pdfs
            self.progress_data["paid_cost_usd"] = round(self.paid_cost_usd, 5)
            self.progress_data["paid_tokens_prompt"] = self.paid_tokens_prompt
            self.progress_data["paid_tokens_candidate"] = self.paid_tokens_candidate
            self.progress_data["paid_tokens_embedding"] = self.paid_tokens_embedding

            with open(to_long_path(PROGRESS_FILE), "w", encoding="utf-8") as f:
                json.dump(self.progress_data, f, indent=2, ensure_ascii=False)

    def is_done(self, pdf_rel: str) -> bool:
        with _PROGRESS_LOCK:
            return pdf_rel in self.processed_pdfs

    def record_paid_generation(self, p_tok: int, c_tok: int):
        with _COST_LOCK:
            cost = (p_tok * COST_PROMPT_TOKEN_FLEX) + (c_tok * COST_CANDIDATE_TOKEN_FLEX)
            self.paid_tokens_prompt += p_tok
            self.paid_tokens_candidate += c_tok
            self.paid_cost_usd += cost
            logger.info(
                f"[CUSTO PAGO] Tokens: {p_tok} in / {c_tok} out | +${cost:.5f} | "
                f"Total: ${self.paid_cost_usd:.4f} USD (Teto: ${BUDGET_LIMIT_USD:.2f})"
            )
            if self.paid_cost_usd >= BUDGET_LIMIT_USD:
                raise BudgetExceededException(
                    f"Limite de ${BUDGET_LIMIT_USD:.2f} USD atingido na chave paga! Total: ${self.paid_cost_usd:.4f} USD"
                )

    def record_paid_embedding(self, tok_count: int):
        with _COST_LOCK:
            cost = tok_count * COST_EMBEDDING_TOKEN
            self.paid_tokens_embedding += tok_count
            self.paid_cost_usd += cost
            if self.paid_cost_usd >= BUDGET_LIMIT_USD:
                raise BudgetExceededException(
                    f"Limite de ${BUDGET_LIMIT_USD:.2f} USD atingido na chave paga! Total: ${self.paid_cost_usd:.4f} USD"
                )


class SlicingEngine:
    def __init__(
        self,
        worker_ctx: KeyWorkerContext,
        fallback_paid_ctx: Optional[KeyWorkerContext],
        global_cache: GlobalSlicingCache,
        budget_mgr: QuotaAndBudgetManager
    ):
        self.worker_ctx = worker_ctx
        self.paid_ctx = fallback_paid_ctx
        self.cache = global_cache
        self.budget_mgr = budget_mgr

    def slice_pdf_with_llm(self, pdf_path: Path) -> Optional[DocumentSlicingOutput]:
        """Executa a análise no Gemini com o worker ou com chave paga em fallback."""
        ctx = self.worker_ctx if not self.worker_ctx.exhausted else self.paid_ctx
        if not ctx:
            logger.error("Nenhuma chave disponível para execução!")
            return None

        # Garante upload livre de problemas com caracteres acentuados nos cabeçalhos HTTP
        import unicodedata, tempfile, re
        clean_stem = "".join(c for c in unicodedata.normalize("NFKD", pdf_path.stem) if not unicodedata.combining(c))
        safe_ascii_name = re.sub(r"[^\w\-.]", "_", clean_stem) + ".pdf"
        temp_upload_file = Path(tempfile.gettempdir()) / safe_ascii_name
        try:
            shutil.copy2(to_long_path(pdf_path), temp_upload_file)
        except Exception:
            temp_upload_file = to_long_path(pdf_path)

        for attempt in range(1, 4):
            ctx.acquire_slot()
            uploaded_file = None
            try:
                uploaded_file = ctx.client.files.upload(file=str(temp_upload_file))
                time.sleep(1.2)

                config_kwargs = {
                    "response_mime_type": "application/json",
                    "response_schema": DocumentSlicingOutput,
                    "temperature": 0.1,
                }
                if ctx.is_paid:
                    config_kwargs["service_tier"] = "flex"

                response = ctx.client.models.generate_content(
                    model=PRIMARY_MODEL,
                    contents=[uploaded_file, PRE_LLM_SLICING_PROMPT],
                    config=types.GenerateContentConfig(**config_kwargs)
                )

                if ctx.is_paid and response.usage_metadata:
                    p_tok = response.usage_metadata.prompt_token_count or 0
                    c_tok = response.usage_metadata.candidates_token_count or 0
                    self.budget_mgr.record_paid_generation(p_tok, c_tok)

                parsed = DocumentSlicingOutput.model_validate_json(response.text)

                try:
                    ctx.client.files.delete(name=uploaded_file.name)
                except Exception:
                    pass

                return parsed

            except BudgetExceededException as be:
                raise be
            except Exception as e:
                err = str(e)
                logger.warning(f"[{ctx.key_name} | Tentativa {attempt}] Erro em {pdf_path.name}: {err[:120]}")
                if "RESOURCE_EXHAUSTED" in err or "429" in err:
                    if not ctx.is_paid and ("Queries per day" in err or attempt >= 2):
                        logger.warning(f"[QUOTA ESGOTADA] {ctx.key_name} esgotada. Chave marcada como inativa.")
                        ctx.exhausted = True
                        if self.paid_ctx:
                            ctx = self.paid_ctx
                    time.sleep(4.0 * attempt)
                else:
                    time.sleep(2.0 * attempt)
            finally:
                if uploaded_file is not None:
                    try:
                        ctx.client.files.delete(name=uploaded_file.name)
                    except Exception:
                        pass

        if temp_upload_file != to_long_path(pdf_path) and temp_upload_file.exists():
            try:
                temp_upload_file.unlink(missing_ok=True)
            except Exception:
                pass

        return None

    def slice_document(self, pdf_path: Path, output_dir: Path, course_name: str, course_site: str) -> List[Dict[str, Any]]:
        """
        Fatia um documento utilizando:
        1. Cache global (instantâneo se já fatiado em outro curso).
        2. LLM Gemini com corte físico via pypdf e armazenamento no cache global.
        """
        doc_stem = pdf_path.stem
        to_long_path(output_dir).mkdir(parents=True, exist_ok=True)

        # 1. Verificar Cache Global
        cached_chunks = self.cache.get(pdf_path)
        if cached_chunks:
            logger.info(f"[{self.worker_ctx.key_name} | CACHE HIT] {pdf_path.name} recuperado do Cache Global ({len(cached_chunks)} fatias). 0 chamadas de IA!")
            reader = pypdf.PdfReader(str(to_long_path(pdf_path)))
            total_pages = len(reader.pages)

            slices_meta = []
            for idx, c in enumerate(cached_chunks, start=1):
                # Extrair números de páginas
                raw_pag = str(c.get("páginas", "[1]")).strip("[]").replace(" ", "").split(",")
                p_start = int(raw_pag[0]) if raw_pag and raw_pag[0].isdigit() else 1
                p_end = int(raw_pag[-1]) if raw_pag and raw_pag[-1].isdigit() else p_start
                p_start = max(1, min(p_start, total_pages))
                p_end = max(p_start, min(p_end, total_pages))

                chunk_filename = f"{doc_stem}_paginas_{p_start}-{p_end}.pdf"
                chunk_file_path = output_dir / chunk_filename

                if not to_long_path(chunk_file_path).exists():
                    writer = pypdf.PdfWriter()
                    for p_num in range(p_start - 1, p_end):
                        writer.add_page(reader.pages[p_num])
                    with open(to_long_path(chunk_file_path), "wb") as f:
                        writer.write(f)

                resumo_txt = c.get("fichamento/resumo", "")
                slices_meta.append({
                    "chunk_id": f"{doc_stem}_{idx:03d}",
                    "nome do documento": doc_stem,
                    "páginas": f"[{p_start}, {p_end}]" if p_start != p_end else f"[{p_start}]",
                    "fichamento/resumo": resumo_txt,
                    "pdf_chunk_path": safe_rel_path(chunk_file_path, BASE_DIR),
                    "curso": course_name,
                    "link para acessar o documento": course_site,
                    "quantidade de tokens": len(resumo_txt.split()) * 2
                })

            meta_json = output_dir / f"{doc_stem}_meta.json"
            with open(to_long_path(meta_json), "w", encoding="utf-8") as f:
                json.dump(slices_meta, f, indent=2, ensure_ascii=False)
            return slices_meta

        # 2. Cache Miss: Fatiar via Gemini
        file_size_kb = to_long_path(pdf_path).stat().st_size / 1024.0 if to_long_path(pdf_path).exists() else 0.0
        logger.info(f"[{self.worker_ctx.key_name} | CACHE MISS] Fatiando via IA: {pdf_path.name} ({file_size_kb:.1f} KB)...")
        slicing = self.slice_pdf_with_llm(pdf_path)
        if not slicing:
            return []

        reader = pypdf.PdfReader(str(to_long_path(pdf_path)))
        total_pages = len(reader.pages)
        slices_meta = []

        for idx, chunk in enumerate(slicing.chunks, start=1):
            interval = chunk.intervalo_paginas
            if len(interval) == 1:
                p_start, p_end = interval[0], interval[0]
            elif len(interval) >= 2:
                p_start, p_end = interval[0], interval[1]
            else:
                p_start, p_end = 1, 1

            p_start = max(1, min(p_start, total_pages))
            p_end = max(p_start, min(p_end, total_pages))

            writer = pypdf.PdfWriter()
            for p_num in range(p_start - 1, p_end):
                writer.add_page(reader.pages[p_num])

            chunk_filename = f"{doc_stem}_paginas_{p_start}-{p_end}.pdf"
            chunk_file_path = output_dir / chunk_filename
            with open(to_long_path(chunk_file_path), "wb") as f:
                writer.write(f)

            slices_meta.append({
                "chunk_id": f"{doc_stem}_{idx:03d}",
                "nome do documento": doc_stem,
                "páginas": f"[{p_start}, {p_end}]" if p_start != p_end else f"[{p_start}]",
                "fichamento/resumo": chunk.resumo,
                "pdf_chunk_path": safe_rel_path(chunk_file_path, BASE_DIR),
                "curso": course_name,
                "link para acessar o documento": course_site,
                "quantidade de tokens": len(chunk.resumo.split()) * 2
            })

        meta_json = output_dir / f"{doc_stem}_meta.json"
        with open(to_long_path(meta_json), "w", encoding="utf-8") as f:
            json.dump(slices_meta, f, indent=2, ensure_ascii=False)

        # Inserir no Cache Global
        self.cache.put(pdf_path, slices_meta)
        logger.info(f"[{self.worker_ctx.key_name}] OK: {len(slices_meta)} fatias criadas e indexadas no Cache Global para {pdf_path.name}.")
        return slices_meta

    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Gera embeddings via gemini-embedding-2."""
        ctx = self.worker_ctx if not self.worker_ctx.exhausted else self.paid_ctx
        embeddings = []
        for t in texts:
            for attempt in range(1, 4):
                ctx.acquire_slot()
                try:
                    res = ctx.client.models.embed_content(
                        model=EMBEDDING_MODEL,
                        contents=t
                    )
                    emb_vals = res.embeddings[0].values if (hasattr(res, "embeddings") and res.embeddings) else getattr(res, "embedding", None).values
                    embeddings.append(emb_vals)
                    if ctx.is_paid:
                        tok_count = int(len(t.split()) * 1.3)
                        self.budget_mgr.record_paid_embedding(tok_count)
                    break
                except BudgetExceededException as be:
                    raise be
                except Exception as e:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        if not ctx.is_paid and attempt >= 2:
                            ctx.exhausted = True
                            if self.paid_ctx:
                                ctx = self.paid_ctx
                        time.sleep(3.0 * attempt)
                    else:
                        time.sleep(2.0)
        return np.array(embeddings, dtype=np.float32)


def process_course_worker(
    course_data: Dict[str, Any],
    engine: SlicingEngine
):
    """Processa todos os documentos de um curso utilizando a SlicingEngine do worker."""
    if course_data.get("area") == "UFBA - Geral" or course_data.get("nome") == "UFBA - Geral":
        f_name = "UFBA - Geral"
        course_dir = GERAL_DIR
    else:
        f_name = get_folder_name(course_data)
        course_dir = AREAS_DIR / course_data["area"] / f_name
    bv_dir = course_dir / "banco vetorial"
    parquet_path = bv_dir / "banco_vetorial.parquet"
    npy_path = bv_dir / "embeddings.npy"

    try:
        raw_names = os.listdir(to_long_path(course_dir))
        pdf_files = [course_dir / f for f in raw_names if f.lower().endswith(".pdf")]
    except Exception:
        pdf_files = [p for p in course_dir.glob("*.pdf") if to_long_path(p).is_file()]
    if not pdf_files:
        return

    # Se já concluído 100%
    if to_long_path(parquet_path).exists() and to_long_path(npy_path).exists():
        for p in pdf_files:
            engine.budget_mgr.mark_done(safe_rel_path(p, BASE_DIR))
        return

    logger.info(f"\n{'='*75}\n[{engine.worker_ctx.key_name}] INICIANDO CURSO: {f_name} ({len(pdf_files)} PDFs)\n{'='*75}")

    all_chunks_meta = []
    course_site = course_data.get("site", "https://ufba.br")

    for pdf in pdf_files:
        pdf_rel_str = safe_rel_path(pdf, BASE_DIR)
        slices_dir = course_dir / pdf.stem

        meta = engine.slice_document(
            pdf_path=to_long_path(pdf),
            output_dir=to_long_path(slices_dir),
            course_name=f_name,
            course_site=course_site
        )
        if meta:
            all_chunks_meta.extend(meta)
            engine.budget_mgr.mark_done(pdf_rel_str)

    if all_chunks_meta:
        to_long_path(bv_dir).mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(all_chunks_meta)
        df.drop_duplicates(subset=["chunk_id"], inplace=True)

        logger.info(f"[{engine.worker_ctx.key_name}] Gerando embeddings para {len(df)} fatias de {f_name}...")
        emb_matrix = engine.generate_embeddings(df["fichamento/resumo"].tolist())
        if len(emb_matrix) == len(df):
            df["embedding"] = [list(e) for e in emb_matrix]

        df.to_parquet(to_long_path(parquet_path), index=False)
        df.to_json(to_long_path(bv_dir / "banco_vetorial.json"), orient="records", force_ascii=False, indent=2)
        np.save(to_long_path(npy_path), emb_matrix)
        logger.info(f"[{engine.worker_ctx.key_name}] Banco vetorial CONCLUÍDO para {f_name}: {len(df)} fatias.")


def run_parallel_slicing():
    """Orquestra os 2 workers paralelos com Cache Global."""
    all_courses = list(COURSES_DATA)
    total_pdfs = sum(len(list((AREAS_DIR / c["area"] / get_folder_name(c)).glob("*.pdf"))) for c in all_courses if (AREAS_DIR / c["area"] / get_folder_name(c)).exists())

    global_cache = GlobalSlicingCache()
    budget_mgr = QuotaAndBudgetManager(total_pdfs)

    # 1. Configurar Workers
    # Worker 0 -> Chave 1
    # Worker 1 -> Chave 2
    # Fallback -> Chave Paga
    fallback_paid = (
        KeyWorkerContext(key=GEMINI_PAID_KEY, key_name="GEMINI_PAGO_RICARDO", is_paid=True, min_interval=1.0)
        if GEMINI_PAID_KEY else None
    )

    worker_contexts = []
    for idx, k in enumerate(GEMINI_FREE_KEYS):
        worker_contexts.append(
            KeyWorkerContext(key=k, key_name=f"FREE_KEY_{idx+1}", is_paid=False, min_interval=4.0)
        )

    num_workers = max(1, len(worker_contexts))
    logger.info(f"Iniciando pipeline paralelo com {num_workers} workers (15 RPM por chave) e Cache Global ativo.")

    course_queue = Queue()
    for c in all_courses:
        course_queue.put(c)

    def worker_thread(worker_id: int):
        ctx = worker_contexts[worker_id % len(worker_contexts)]
        engine = SlicingEngine(
            worker_ctx=ctx,
            fallback_paid_ctx=fallback_paid,
            global_cache=global_cache,
            budget_mgr=budget_mgr
        )
        logger.info(f"Worker {worker_id+1} iniciado conectado a {ctx.key_name}.")

        while not course_queue.empty():
            try:
                course = course_queue.get_nowait()
            except Exception:
                break
            try:
                process_course_worker(course, engine)
            except BudgetExceededException as be:
                logger.warning(f"Worker {worker_id+1} interrompido: {be}")
                break
            except Exception as e:
                logger.error(f"Erro inesperado no curso {course.get('nome')}: {e}")
            finally:
                course_queue.task_done()

    # Executar em paralelo
    threads = []
    for w_id in range(num_workers):
        t = threading.Thread(target=worker_thread, args=(w_id,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    # Processar UFBA - Geral se houver
    if GERAL_DIR.exists():
        engine_geral = SlicingEngine(
            worker_ctx=worker_contexts[0],
            fallback_paid_ctx=fallback_paid,
            global_cache=global_cache,
            budget_mgr=budget_mgr
        )
        process_course_worker(
            course_data={"nome": "UFBA - Geral", "area": "UFBA - Geral", "site": "https://supac.ufba.br"},
            engine=engine_geral
        )

    logger.info("Pipeline de fatiamento concluído com sucesso!")


def main():
    run_parallel_slicing()


if __name__ == "__main__":
    main()
