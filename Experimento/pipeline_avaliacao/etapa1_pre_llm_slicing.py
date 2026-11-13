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


class DailyQuotaExhaustedException(Exception):
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
        with _CACHE_LOCK:
            if f"hash:{f_hash}" in self.cache:
                return self.cache[f"hash:{f_hash}"].get("chunks")
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
        budget_mgr: QuotaAndBudgetManager,
        all_free_contexts: Optional[List[KeyWorkerContext]] = None,
        model_name: str = PRIMARY_MODEL
    ):
        self.worker_ctx = worker_ctx
        self.paid_ctx = None  # ESTRITAMENTE PROIBIDO USAR CHAVE PAGA (somente chaves gratuitas)
        self.cache = global_cache
        self.budget_mgr = budget_mgr
        self.all_free_contexts = all_free_contexts or [worker_ctx]
        self.model_name = model_name

    def _get_active_free_ctx(self, attempt: int = 1) -> KeyWorkerContext:
        """Alterna entre as chaves gratuitas disponíveis (não esgotadas)."""
        avail = [c for c in self.all_free_contexts if not c.exhausted]
        if not avail:
            raise DailyQuotaExhaustedException("Todas as chaves gratuitas atingiram a cota diária (RPD).")
        if self.worker_ctx in avail and attempt == 1:
            return self.worker_ctx
        base_idx = avail.index(self.worker_ctx) if self.worker_ctx in avail else 0
        return avail[(base_idx + attempt - 1) % len(avail)]

    def _call_gemini_for_pdf(self, upload_file: Path) -> Optional[DocumentSlicingOutput]:
        """Envia um PDF e retorna o DocumentSlicingOutput usando somente chaves gratuitas."""
        consecutive_429 = 0
        for attempt in range(1, 7):
            ctx = self._get_active_free_ctx(attempt)
            ctx.acquire_slot()
            uploaded_file = None
            try:
                uploaded_file = ctx.client.files.upload(file=str(upload_file))
                time.sleep(1.5)

                config_kwargs = {
                    "response_mime_type": "application/json",
                    "response_schema": DocumentSlicingOutput,
                    "temperature": 0.1,
                    "max_output_tokens": 65536,
                }

                response = ctx.client.models.generate_content(
                    model=self.model_name,
                    contents=[uploaded_file, PRE_LLM_SLICING_PROMPT],
                    config=types.GenerateContentConfig(**config_kwargs)
                )

                parsed = DocumentSlicingOutput.model_validate_json(response.text)
                return parsed

            except DailyQuotaExhaustedException:
                raise
            except Exception as e:
                err = str(e)
                logger.warning(f"[{ctx.key_name} | Tentativa {attempt}/6] Erro em {upload_file.name}: {err[:160]}")
                if "RESOURCE_EXHAUSTED" in err or "429" in err:
                    consecutive_429 += 1
                    err_low = err.lower()
                    if "perday" in err_low or "per_day" in err_low or "daily" in err_low or "limit: 0" in err_low or consecutive_429 >= 4:
                        logger.warning(f"[{ctx.key_name}] Cota diária (RPD) esgotada para esta chave.")
                        ctx.exhausted = True
                        if not [c for c in self.all_free_contexts if not c.exhausted]:
                            raise DailyQuotaExhaustedException("Cota diária (RPD) esgotada em todas as chaves gratuitas.")
                        continue
                    wait_s = 35.0 if attempt <= 2 else 65.0
                    logger.info(f"[{ctx.key_name}] Rate limit (429) detectado. Aguardando {wait_s:.0f}s para reset da janela de RPM/TPM...")
                    time.sleep(wait_s)
                else:
                    consecutive_429 = 0
                    time.sleep(4.0 * attempt)
            finally:
                if uploaded_file is not None:
                    try:
                        ctx.client.files.delete(name=uploaded_file.name)
                    except Exception:
                        pass
        return None

    def slice_pdf_with_llm(self, pdf_path: Path) -> Optional[DocumentSlicingOutput]:
        """Executa a análise no Gemini 3.5 Flash Lite usando EXCLUSIVAMENTE chaves gratuitas (com blocos de 150p para PDFs gigantes)."""
        import unicodedata, tempfile, re
        clean_stem = "".join(c for c in unicodedata.normalize("NFKD", pdf_path.stem) if not unicodedata.combining(c))
        safe_ascii_name = re.sub(r"[^\w\-.]", "_", clean_stem) + f"_{threading.get_ident()}.pdf"
        temp_upload_file = Path(tempfile.gettempdir()) / safe_ascii_name
        try:
            shutil.copy2(to_long_path(pdf_path), temp_upload_file)
        except Exception:
            temp_upload_file = to_long_path(pdf_path)

        try:
            try:
                total_pages = len(pypdf.PdfReader(str(to_long_path(pdf_path))).pages)
            except Exception:
                total_pages = 0

            if total_pages > 220:
                logger.info(f"[PDF EXTENSO: {total_pages}p] Fatiando {pdf_path.name} em blocos de 150 páginas...")
                reader = pypdf.PdfReader(str(to_long_path(pdf_path)))
                combined_chunks: List[PageChunkSpec] = []
                for start_idx in range(0, total_pages, 150):
                    end_idx = min(total_pages, start_idx + 150)
                    blk_path = Path(tempfile.gettempdir()) / f"{safe_ascii_name}_p{start_idx+1}_{end_idx}.pdf"
                    writer = pypdf.PdfWriter()
                    for pi in range(start_idx, end_idx):
                        writer.add_page(reader.pages[pi])
                    with open(blk_path, "wb") as bf:
                        writer.write(bf)
                    try:
                        sub_out = self._call_gemini_for_pdf(blk_path)
                        if not sub_out:
                            return None
                        for ch in sub_out.chunks:
                            ivs = ch.intervalo_paginas or [1]
                            s_p = max(1, min(end_idx - start_idx, ivs[0])) + start_idx
                            e_p = max(ivs[0], min(end_idx - start_idx, ivs[-1])) + start_idx
                            combined_chunks.append(PageChunkSpec(intervalo_paginas=[s_p, e_p] if s_p != e_p else [s_p], resumo=ch.resumo))
                    finally:
                        blk_path.unlink(missing_ok=True)
                return DocumentSlicingOutput(chunks=combined_chunks)

            return self._call_gemini_for_pdf(temp_upload_file)
        finally:
            if temp_upload_file != to_long_path(pdf_path) and temp_upload_file.exists():
                try:
                    temp_upload_file.unlink(missing_ok=True)
                except Exception:
                    pass

    def slice_document(self, pdf_path: Path, output_dir: Path, course_name: str, course_site: str) -> List[Dict[str, Any]]:
        """
        Fatia um documento utilizando:
        0. Metadados locais já existentes (<doc_stem>_meta.json) na pasta do curso.
        1. Cache global (instantâneo se já fatiado em outro curso).
        2. LLM Gemini 3.5 Flash Lite (somente chaves gratuitas) com corte físico via pypdf.
        """
        doc_stem = pdf_path.stem
        to_long_path(output_dir).mkdir(parents=True, exist_ok=True)
        meta_json = output_dir / f"{doc_stem}_meta.json"

        # 0. Verificar se já foi fatiado localmente nesta mesma pasta
        if to_long_path(meta_json).exists():
            try:
                with open(to_long_path(meta_json), "r", encoding="utf-8") as f:
                    local_meta = json.load(f)
                if isinstance(local_meta, list) and len(local_meta) > 0:
                    # Garantir que está no cache global também
                    if not self.cache.get(pdf_path):
                        self.cache.put(pdf_path, local_meta)
                    return local_meta
            except Exception:
                pass

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

            with open(to_long_path(meta_json), "w", encoding="utf-8") as f:
                json.dump(slices_meta, f, indent=2, ensure_ascii=False)
            return slices_meta

        # 2. Cache Miss: Fatiar via Gemini (somente chaves gratuitas)
        file_size_kb = to_long_path(pdf_path).stat().st_size / 1024.0 if to_long_path(pdf_path).exists() else 0.0
        logger.info(f"[{self.worker_ctx.key_name} | CACHE MISS] Fatiando via IA ({self.model_name}): {pdf_path.name} ({file_size_kb:.1f} KB)...")
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

        with open(to_long_path(meta_json), "w", encoding="utf-8") as f:
            json.dump(slices_meta, f, indent=2, ensure_ascii=False)

        # Inserir no Cache Global
        self.cache.put(pdf_path, slices_meta)
        logger.info(f"[{self.worker_ctx.key_name}] OK: {len(slices_meta)} fatias criadas e indexadas no Cache Global para {pdf_path.name}.")
        return slices_meta

    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Gera embeddings em lotes via gemini-embedding-2 usando EXCLUSIVAMENTE chaves gratuitas."""
        if not texts:
            return np.zeros((0, 3072), dtype=np.float32)

        embeddings: List[List[float]] = []
        batch_size = 50
        for b_start in range(0, len(texts), batch_size):
            batch = texts[b_start:b_start + batch_size]
            success = False
            for attempt in range(1, 7):
                ctx = self._get_active_free_ctx(attempt)
                ctx.acquire_slot()
                try:
                    contents_payload = [
                        types.Content(parts=[types.Part.from_text(text=t if t.strip() else " ")])
                        for t in batch
                    ]
                    res = ctx.client.models.embed_content(
                        model=EMBEDDING_MODEL,
                        contents=contents_payload
                    )
                    if hasattr(res, "embeddings") and res.embeddings:
                        for emb_obj in res.embeddings:
                            embeddings.append(list(emb_obj.values))
                    elif hasattr(res, "embedding") and res.embedding:
                        embeddings.append(list(res.embedding.values))
                    success = True
                    break
                except Exception as e:
                    err = str(e)
                    logger.warning(f"[{ctx.key_name} | Emb Lote {b_start//batch_size + 1} | Tentativa {attempt}/6] Erro: {err[:140]}")
                    if "429" in err or "RESOURCE_EXHAUSTED" in err:
                        wait_s = 30.0 if attempt <= 2 else 62.0
                        logger.info(f"[{ctx.key_name}] Rate limit (429) no embedding. Aguardando {wait_s:.0f}s...")
                        time.sleep(wait_s)
                    else:
                        time.sleep(3.0 * attempt)
            if not success:
                raise RuntimeError(f"Falha ao gerar embeddings para lote iniciando em {b_start} após 6 tentativas.")
        return np.array(embeddings, dtype=np.float32)


def process_course_worker(
    course_data: Dict[str, Any],
    engine: SlicingEngine
):
    """Processa todos os documentos de um curso de forma incremental, usando apenas chaves gratuitas."""
    if course_data.get("area") == "UFBA - Geral" or course_data.get("nome") == "UFBA - Geral":
        f_name = "UFBA - Geral"
        course_dir = GERAL_DIR
    else:
        f_name = course_data.get("folder_name") or get_folder_name(course_data)
        course_dir = AREAS_DIR / course_data["area"] / f_name
    bv_dir = course_dir / "banco vetorial"
    parquet_path = bv_dir / "banco_vetorial.parquet"
    npy_path = bv_dir / "embeddings.npy"

    if not to_long_path(course_dir).exists():
        return

    try:
        raw_names = os.listdir(to_long_path(course_dir))
        pdf_files = sorted([course_dir / f for f in raw_names if f.lower().endswith(".pdf") and os.path.isfile(to_long_path(course_dir / f))])
    except Exception:
        pdf_files = sorted([p for p in course_dir.glob("*.pdf") if to_long_path(p).is_file()])
    if not pdf_files:
        return

    # Se a pasta possui documentos reais além do recorte de 1 página do Catálogo PROGRAD,
    # removemos o recorte de 1 página (Catalogo_Oficial_PROGRAD_2026_*) para não poluir o RAG
    non_catalog_pdfs = [p for p in pdf_files if not p.name.startswith("Catalogo_Oficial_PROGRAD_2026_")]
    if non_catalog_pdfs and len(non_catalog_pdfs) < len(pdf_files):
        for cat_pdf in [p for p in pdf_files if p.name.startswith("Catalogo_Oficial_PROGRAD_2026_")]:
            try:
                cat_slice_dir = course_dir / cat_pdf.stem
                if to_long_path(cat_slice_dir).exists():
                    shutil.rmtree(to_long_path(cat_slice_dir), ignore_errors=True)
                to_long_path(cat_pdf).unlink(missing_ok=True)
                logger.info(f"[{f_name}] Removido recorte raso {cat_pdf.name} pois a pasta possui {len(non_catalog_pdfs)} PDFs completos.")
            except Exception as e:
                logger.warning(f"Não foi possível remover {cat_pdf.name}: {e}")
        pdf_files = non_catalog_pdfs

    expected_stems = {p.stem for p in pdf_files}

    # Verificar se o banco vetorial já existe e se contém exatamente todos os PDFs atuais da pasta
    existing_emb_map: Dict[str, np.ndarray] = {}
    if to_long_path(parquet_path).exists() and to_long_path(npy_path).exists():
        try:
            existing_df = pd.read_parquet(to_long_path(parquet_path))
            existing_emb = np.load(to_long_path(npy_path))
            if "nome do documento" in existing_df.columns and len(existing_df) == len(existing_emb) and len(existing_df) > 0:
                indexed_stems = set(existing_df["nome do documento"].astype(str).unique())
                if indexed_stems == expected_stems:
                    for p in pdf_files:
                        engine.budget_mgr.mark_done(safe_rel_path(p, BASE_DIR))
                    return
                # Guardar embeddings já calculados para reaproveitar sem gastar chamadas de API
                for idx_row, row in existing_df.iterrows():
                    resumo_key = str(row.get("fichamento/resumo", ""))
                    if resumo_key and idx_row < len(existing_emb):
                        existing_emb_map[resumo_key] = existing_emb[idx_row]
        except Exception as e:
            logger.warning(f"[{f_name}] Banco vetorial existente será reconstruído ({e}).")

    logger.info(f"\n{'='*75}\n[{engine.worker_ctx.key_name}] ATUALIZANDO CURSO: {f_name} ({len(pdf_files)} PDFs)\n{'='*75}")

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
        df.reset_index(drop=True, inplace=True)

        # Identificar quais textos já possuem embedding e quais são novos
        resumos = df["fichamento/resumo"].astype(str).tolist()
        missing_indices = [i for i, r in enumerate(resumos) if r not in existing_emb_map]

        emb_ok = True
        if missing_indices:
            logger.info(
                f"[{engine.worker_ctx.key_name}] Gerando embeddings para {len(missing_indices)} novas fatias "
                f"(reaproveitando {len(resumos) - len(missing_indices)} existentes) de {f_name}..."
            )
            new_texts = [resumos[i] for i in missing_indices]
            try:
                new_embs = engine.generate_embeddings(new_texts)
                for idx_new, orig_i in enumerate(missing_indices):
                    existing_emb_map[resumos[orig_i]] = new_embs[idx_new]
            except Exception as emb_err:
                emb_ok = False
                logger.warning(f"[{f_name}] Embeddings falharam/cota esgotada ({emb_err}); salvando fichamentos e intervalos normalmente.")
        else:
            logger.info(f"[{engine.worker_ctx.key_name}] Reaproveitando 100% dos {len(resumos)} embeddings existentes para {f_name}.")

        if emb_ok and all(r in existing_emb_map for r in resumos):
            emb_matrix = np.array([existing_emb_map[r] for r in resumos], dtype=np.float32)
            if len(emb_matrix) == len(df):
                df["embedding"] = [list(e) for e in emb_matrix]
            np.save(to_long_path(npy_path), emb_matrix)

        df.to_parquet(to_long_path(parquet_path), index=False)
        df.to_json(to_long_path(bv_dir / "banco_vetorial.json"), orient="records", force_ascii=False, indent=2)
        logger.info(f"[{engine.worker_ctx.key_name}] Fichamentos/Banco CONCLUÍDOS para {f_name}: {len(df)} fatias ({len(expected_stems)} PDFs).")


def run_parallel_slicing(model_name: str = PRIMARY_MODEL):
    """Orquestra os workers paralelos com Cache Global usando EXCLUSIVAMENTE as chaves gratuitas."""
    all_courses = list(COURSES_DATA)
    seen_folders = {(c["area"], get_folder_name(c)) for c in all_courses}

    # Incluir quaisquer pastas de cursos adicionais presentes em Experimento/Áreas do conhecimento/
    if AREAS_DIR.exists():
        for area_dir in sorted(AREAS_DIR.iterdir()):
            if not area_dir.is_dir():
                continue
            for c_dir in sorted(area_dir.iterdir()):
                if not c_dir.is_dir():
                    continue
                key = (area_dir.name, c_dir.name)
                if key not in seen_folders:
                    seen_folders.add(key)
                    all_courses.append({
                        "nome": c_dir.name,
                        "area": area_dir.name,
                        "folder_name": c_dir.name,
                        "site": "https://supac.ufba.br"
                    })

    total_pdfs = sum(
        len([f for f in os.listdir(to_long_path(AREAS_DIR / c["area"] / (c.get("folder_name") or get_folder_name(c)))) if f.lower().endswith(".pdf") and os.path.isfile(to_long_path(AREAS_DIR / c["area"] / (c.get("folder_name") or get_folder_name(c)) / f))])
        for c in all_courses
        if to_long_path(AREAS_DIR / c["area"] / (c.get("folder_name") or get_folder_name(c))).exists()
    )

    global_cache = GlobalSlicingCache()
    budget_mgr = QuotaAndBudgetManager(total_pdfs)

    # ESTRITAMENTE SOMENTE CHAVES GRATUITAS (fallback_paid = None)
    fallback_paid = None

    worker_contexts = []
    for idx, k in enumerate(GEMINI_FREE_KEYS):
        worker_contexts.append(
            KeyWorkerContext(key=k, key_name=f"FREE_KEY_{idx+1}", is_paid=False, min_interval=4.2)
        )

    num_workers = max(1, len(worker_contexts))
    logger.info(f"Iniciando pipeline paralelo ({model_name}) com {num_workers} workers GRATUITOS e Cache Global ativo (Chave paga DESATIVADA).")

    course_queue = Queue()
    for c in all_courses:
        course_queue.put(c)

    def worker_thread(worker_id: int):
        ctx = worker_contexts[worker_id % len(worker_contexts)]
        engine = SlicingEngine(
            worker_ctx=ctx,
            fallback_paid_ctx=None,
            global_cache=global_cache,
            budget_mgr=budget_mgr,
            all_free_contexts=worker_contexts,
            model_name=model_name
        )
        logger.info(f"Worker {worker_id+1} iniciado conectado a {ctx.key_name} (SOMENTE GRATUITO).")

        while not course_queue.empty():
            try:
                course = course_queue.get_nowait()
            except Exception:
                break
            try:
                process_course_worker(course, engine)
            except DailyQuotaExhaustedException as dq:
                logger.warning(f"Worker {worker_id+1} encerrado por cota diária gratuita: {dq}")
                break
            except Exception as e:
                logger.error(f"Erro inesperado no curso {course.get('nome')}: {e}")
            finally:
                course_queue.task_done()

    # Processar UFBA - Geral primeiro (para aquecer Cache Global com normativos centrais)
    if GERAL_DIR.exists():
        engine_geral = SlicingEngine(
            worker_ctx=worker_contexts[0],
            fallback_paid_ctx=None,
            global_cache=global_cache,
            budget_mgr=budget_mgr,
            all_free_contexts=worker_contexts,
            model_name=model_name
        )
        try:
            process_course_worker(
                course_data={"nome": "UFBA - Geral", "area": "UFBA - Geral", "site": "https://supac.ufba.br"},
                engine=engine_geral
            )
        except DailyQuotaExhaustedException as dq:
            logger.warning(f"UFBA - Geral interrompido por cota diária gratuita: {dq}")

    # Executar em paralelo
    threads = []
    for w_id in range(num_workers):
        t = threading.Thread(target=worker_thread, args=(w_id,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    logger.info("Pipeline de fatiamento concluído com sucesso!")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Etapa 1: Fatiamento pré-LLM com chaves gratuitas.")
    parser.add_argument("--model", type=str, default=PRIMARY_MODEL, help="Modelo Gemini a usar (ex.: gemini-3.1-flash-lite)")
    args = parser.parse_args()
    run_parallel_slicing(model_name=args.model)


if __name__ == "__main__":
    main()
