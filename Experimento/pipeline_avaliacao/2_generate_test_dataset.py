"""
===============================================================================
ETAPA 2: GERAÇÃO DO CONJUNTO DE TESTES PROPORCIONAL POR CURSO (UFBA)
VERSÃO OTIMIZADA: MULTI-WORKER (15 RPM) + CONTROLE DE CUSTOS ($5.00 USD)
===============================================================================
1. Ponderação Estrita por Número de Páginas:
   - Lê a quantidade real de páginas de cada documento do curso via pypdf.
   - Aplica proporção com piso mínimo de 2 perguntas por doc (ou 1 se > 50 docs).
   - Ajusta resíduos no documento com mais páginas para fechar SEMPRE em 100 perguntas.
2. Dois Workers Paralelos em Chaves Gratuitas a 15 RPM:
   - Worker 0 -> FREE_KEY_1 (GEMINI_API_KEY) a 15 RPM (intervalo de 4,0s)
   - Worker 1 -> FREE_KEY_2 (GEMINI_API_KEY_2) a 15 RPM (intervalo de 4,0s)
3. Fallback Automático para a Chave Paga (GEMINI_PAGO_RICARDO):
   - Acionado somente se as chaves gratuitas esgotarem sua cota diária (429).
   - Usa inferência flexível (service_tier='flex' com 50% de desconto).
4. Teto Orçamentário Rígido de $5.00 USD:
   - Monitora tokens de entrada e saída em tempo real na chave paga.
   - Interrompe a execução imediatamente se o custo acumulado atingir $5.00 USD.
5. Salvamento Incremental Contínuo:
   - Atualiza 'Experimento/Conjunto de Testes Geral.xlsx' após cada curso.
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
import unicodedata
import tempfile
import re
from pathlib import Path
from queue import Queue
from datetime import datetime
from typing import List, Dict, Any, Optional

import pypdf
import pandas as pd
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from Experimento.pipeline_avaliacao.config import (
    EXP_DIR, AREAS_DIR, GERAL_DIR, GEMINI_FREE_KEYS, GEMINI_PAID_KEY,
    PRIMARY_MODEL, FALLBACK_MODEL, TEST_DATASET_FILE, BACKUPS_DIR, LOGS_DIR,
    COST_PROMPT_TOKEN_FLEX, COST_CANDIDATE_TOKEN_FLEX
)
from Experimento.pipeline_avaliacao.prompts import GENERATE_QUESTIONS_PROMPT_TEMPLATE
from scripts.map_133_courses import COURSES_DATA, get_folder_name

# Configuração de Limite Orçamentário Estrito ($5.00 USD)
BUDGET_LIMIT_USD = 5.00
PROGRESS_FILE = EXP_DIR / "progresso_perguntas.json"
DATASET_JSON_BACKUP = EXP_DIR / "conjunto_testes_geral.json"
LOG_FILE = LOGS_DIR / "execucao_geracao_perguntas.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Etapa2_QAGenerator")

_DATASET_LOCK = threading.Lock()
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


class BudgetExceededException(Exception):
    pass


# Esquema Pydantic para Saída Estruturada
class QAItem(BaseModel):
    pergunta: str = Field(description="Pergunta difícil, técnica e pontual sobre normas, prazos, artigos e regras acadêmicas da UFBA.")
    resposta_gabarito: str = Field(description="Resposta gabarito completa, precisa e fundamentada exclusivamente no texto do documento.")

class QABatch(BaseModel):
    itens: List[QAItem] = Field(description="Lista contendo exatamente a quantidade requisitada de perguntas e gabaritos.")


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


class BudgetAndDatasetManager:
    """Gerencia a persistência contínua do dataset de testes e a trava orçamentária."""
    def __init__(self, total_courses: int = 133):
        self.total_courses = total_courses
        self.progress_data = self._load_progress()
        self.completed_courses = set(self.progress_data.get("completed_courses", []))
        self.paid_cost_usd = self.progress_data.get("paid_cost_usd", 0.0)
        self.paid_tokens_prompt = self.progress_data.get("paid_tokens_prompt", 0)
        self.paid_tokens_candidate = self.progress_data.get("paid_tokens_candidate", 0)
        self.all_qa_records: List[Dict[str, Any]] = self._load_dataset()

    def _load_progress(self) -> Dict[str, Any]:
        if PROGRESS_FILE.exists():
            try:
                with open(to_long_path(PROGRESS_FILE), "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "completed_courses": [],
            "total_courses": self.total_courses,
            "total_questions": 0,
            "percent_completed": 0.0,
            "paid_cost_usd": 0.0,
            "paid_tokens_prompt": 0,
            "paid_tokens_candidate": 0
        }

    def _load_dataset(self) -> List[Dict[str, Any]]:
        if DATASET_JSON_BACKUP.exists():
            try:
                with open(to_long_path(DATASET_JSON_BACKUP), "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        if TEST_DATASET_FILE.exists():
            try:
                df = pd.read_excel(to_long_path(TEST_DATASET_FILE))
                return df.to_dict(orient="records")
            except Exception:
                pass
        return []

    def is_course_done(self, course_name: str) -> bool:
        with _PROGRESS_LOCK:
            return course_name in self.completed_courses

    def record_paid_usage(self, p_tok: int, c_tok: int):
        with _COST_LOCK:
            cost = (p_tok * COST_PROMPT_TOKEN_FLEX) + (c_tok * COST_CANDIDATE_TOKEN_FLEX)
            self.paid_tokens_prompt += p_tok
            self.paid_tokens_candidate += c_tok
            self.paid_cost_usd += cost
            logger.info(
                f"[CUSTO PAGO ETAPA 2] Tokens: {p_tok} in / {c_tok} out | +${cost:.5f} | "
                f"Total: ${self.paid_cost_usd:.4f} USD (Teto: ${BUDGET_LIMIT_USD:.2f})"
            )
            if self.paid_cost_usd >= BUDGET_LIMIT_USD:
                raise BudgetExceededException(
                    f"Limite de ${BUDGET_LIMIT_USD:.2f} USD atingido na chave paga! Total: ${self.paid_cost_usd:.4f} USD"
                )

    def save_course_questions(self, course_name: str, questions: List[Dict[str, Any]]):
        with _DATASET_LOCK:
            self.all_qa_records.extend(questions)
            self.completed_courses.add(course_name)

            pct = (len(self.completed_courses) / self.total_courses) * 100.0 if self.total_courses > 0 else 0.0

            # 1. Salvar Backup JSON
            with open(to_long_path(DATASET_JSON_BACKUP), "w", encoding="utf-8") as f:
                json.dump(self.all_qa_records, f, indent=2, ensure_ascii=False)

            # 2. Salvar Excel Geral
            df = pd.DataFrame(self.all_qa_records)
            df.to_excel(to_long_path(TEST_DATASET_FILE), index=False)

            # 3. Salvar Progresso
            self.progress_data["completed_courses"] = list(self.completed_courses)
            self.progress_data["total_questions"] = len(self.all_qa_records)
            self.progress_data["percent_completed"] = round(pct, 2)
            self.progress_data["paid_cost_usd"] = round(self.paid_cost_usd, 5)
            self.progress_data["paid_tokens_prompt"] = self.paid_tokens_prompt
            self.progress_data["paid_tokens_candidate"] = self.paid_tokens_candidate

            with open(to_long_path(PROGRESS_FILE), "w", encoding="utf-8") as f:
                json.dump(self.progress_data, f, indent=2, ensure_ascii=False)

            logger.info(f"[CHECKPOINT] Curso '{course_name}' salvo com sucesso ({len(questions)} perguntas). Progresso: {len(self.completed_courses)}/{self.total_courses} ({pct:.1f}%).")


def get_pdf_page_count(pdf_path: Path) -> int:
    """Retorna a quantidade real de páginas do arquivo PDF."""
    try:
        reader = pypdf.PdfReader(str(to_long_path(pdf_path)))
        return max(1, len(reader.pages))
    except Exception:
        return 1


def calculate_proportional_allocation(pdf_files: List[Path], total_questions: int = 100) -> Dict[Path, int]:
    """
    Calcula a distribuição proporcional de perguntas com base no número de páginas de cada documento.
    Garante piso mínimo de representatividade e fechamento estrito em total_questions (100).
    """
    n = len(pdf_files)
    if n == 0:
        return {}
    if n == 1:
        return {pdf_files[0]: total_questions}

    pages = {p: get_pdf_page_count(p) for p in pdf_files}
    total_pages = sum(pages.values())

    # Se houver mais documentos do que a cota total de perguntas (ex: cursos com mais de 100 PDFs):
    if n >= total_questions:
        sorted_files = sorted(pdf_files, key=lambda p: pages[p], reverse=True)
        alloc = {p: 0 for p in pdf_files}
        for i in range(total_questions):
            alloc[sorted_files[i]] = 1
        return alloc

    # Piso mínimo: 2 perguntas por documento (ou 1 se houver mais de 50 documentos)
    min_q = 1 if n > (total_questions // 2) else 2

    allocation = {}
    remaining = total_questions
    for p in pdf_files:
        p_count = pages[p]
        q = max(min_q, int(round((p_count / total_pages) * total_questions)))
        allocation[p] = q
        remaining -= q

    # Ajustar sobra ou excesso de arredondamento no documento com mais páginas
    largest_file = max(pages, key=pages.get)
    allocation[largest_file] += remaining
    return allocation


def generate_questions_for_doc(
    pdf_path: Path,
    count: int,
    worker_ctx: KeyWorkerContext,
    fallback_paid: Optional[KeyWorkerContext],
    budget_mgr: BudgetAndDatasetManager
) -> List[Dict[str, str]]:
    """
    Envia o PDF via Files API e gera 'count' perguntas difíceis com gabaritos oficiais.
    Para lotes grandes (count > 25), fatia em chamadas de 25 perguntas para evitar truncamento.
    """
    if count <= 0:
        return []

    # Se for mais de 25 perguntas, particionar em lotes de até 25 para evitar truncamento do LLM
    batches = []
    rem = count
    while rem > 0:
        take = min(25, rem)
        batches.append(take)
        rem -= take

    # Copiar temporariamente para nome ASCII seguro com ID único para evitar colisão entre threads
    import uuid
    clean_stem = "".join(c for c in unicodedata.normalize("NFKD", pdf_path.stem) if not unicodedata.combining(c))
    safe_ascii_name = f"{uuid.uuid4().hex[:8]}_{re.sub(r'[^\w\-.]', '_', clean_stem)}.pdf"
    temp_upload_file = Path(tempfile.gettempdir()) / safe_ascii_name
    try:
        shutil.copy2(to_long_path(pdf_path), temp_upload_file)
    except Exception:
        temp_upload_file = to_long_path(pdf_path)

    all_generated = []

    for batch_count in batches:
        ctx = worker_ctx if not worker_ctx.exhausted else fallback_paid
        if not ctx:
            logger.error("Nenhuma chave disponível para execução de perguntas!")
            break

        prompt = GENERATE_QUESTIONS_PROMPT_TEMPLATE.format(
            nome_documento=pdf_path.stem,
            quantidade_perguntas=batch_count
        )

        uploaded_file = None
        batch_success = False

        for model_name in [PRIMARY_MODEL, FALLBACK_MODEL]:
            for attempt in range(1, 4):
                ctx.acquire_slot()
                try:
                    if uploaded_file is None:
                        uploaded_file = ctx.client.files.upload(file=str(temp_upload_file))
                        time.sleep(1.2)

                    config_kwargs = {
                        "response_mime_type": "application/json",
                        "response_schema": QABatch,
                        "temperature": 0.3
                    }
                    if ctx.is_paid:
                        config_kwargs["service_tier"] = "flex"

                    res = ctx.client.models.generate_content(
                        model=model_name,
                        contents=[uploaded_file, prompt],
                        config=types.GenerateContentConfig(**config_kwargs)
                    )

                    if ctx.is_paid and res.usage_metadata:
                        p_tok = res.usage_metadata.prompt_token_count or 0
                        c_tok = res.usage_metadata.candidates_token_count or 0
                        budget_mgr.record_paid_usage(p_tok, c_tok)

                    parsed = QABatch.model_validate_json(res.text)
                    items = [{"pergunta": q.pergunta.strip(), "resposta_gabarito": q.resposta_gabarito.strip()} for q in parsed.itens]
                    all_generated.extend(items)
                    batch_success = True
                    break

                except BudgetExceededException as be:
                    raise be
                except Exception as e:
                    err = str(e)
                    logger.warning(f"[{ctx.key_name} | Tentativa {attempt}] Erro em {pdf_path.name}: {err[:120]}")
                    if "RESOURCE_EXHAUSTED" in err or "429" in err:
                        if not ctx.is_paid and ("Queries per day" in err or attempt >= 2):
                            logger.warning(f"[QUOTA ESGOTADA] {ctx.key_name} esgotada. Chave marcada como inativa.")
                            ctx.exhausted = True
                            if fallback_paid:
                                ctx = fallback_paid
                        time.sleep(4.0 * attempt)
                    else:
                        time.sleep(2.0 * attempt)

            if batch_success:
                break

        # Limpar arquivo temporário da API File após cada lote
        if uploaded_file is not None:
            try:
                ctx.client.files.delete(name=uploaded_file.name)
            except Exception:
                pass

    # Limpar cópia local temporária
    if temp_upload_file != to_long_path(pdf_path) and temp_upload_file.exists():
        try:
            temp_upload_file.unlink(missing_ok=True)
        except Exception:
            pass

    return all_generated


def process_course_questions(
    course_info: Dict[str, Any],
    worker_ctx: KeyWorkerContext,
    fallback_paid: Optional[KeyWorkerContext],
    budget_mgr: BudgetAndDatasetManager
):
    """Gera as 100 perguntas com gabarito para um curso específico."""
    f_name = get_folder_name(course_info)
    course_dir = AREAS_DIR / course_info["area"] / f_name

    if budget_mgr.is_course_done(f_name):
        logger.info(f"[{worker_ctx.key_name}] Curso '{f_name}' já concluído no checkpoint. Pulando...")
        return

    try:
        raw_names = os.listdir(to_long_path(course_dir))
        pdf_files = [course_dir / f for f in raw_names if f.lower().endswith(".pdf")]
    except Exception:
        pdf_files = [p for p in course_dir.glob("*.pdf") if to_long_path(p).is_file()]

    if not pdf_files:
        logger.warning(f"Curso '{f_name}' sem PDFs para geração de perguntas.")
        return

    allocations = calculate_proportional_allocation(pdf_files, total_questions=100)
    total_alloc = sum(allocations.values())
    logger.info(f"\n{'='*75}\n[{worker_ctx.key_name}] INICIANDO PERGUNTAS: {f_name} ({len(pdf_files)} PDFs | Meta: {total_alloc} Qs)\n{'='*75}")

    course_qa = []
    for pdf, count in allocations.items():
        if count <= 0:
            continue
        logger.info(f"[{worker_ctx.key_name}] -> {pdf.name} ({get_pdf_page_count(pdf)} págs) -> Solicitando {count} perguntas...")
        items = generate_questions_for_doc(
            pdf_path=pdf,
            count=count,
            worker_ctx=worker_ctx,
            fallback_paid=fallback_paid,
            budget_mgr=budget_mgr
        )
        for item in items:
            course_qa.append({
                "Curso": f_name,
                "Documento": pdf.stem,
                "Pergunta": item["pergunta"],
                "Resposta Gabarito": item["resposta_gabarito"]
            })

    # Salvar no dataset geral
    if course_qa:
        budget_mgr.save_course_questions(f_name, course_qa)


def run_parallel_question_generation():
    all_courses = list(COURSES_DATA)
    total_courses = len(all_courses)
    budget_mgr = BudgetAndDatasetManager(total_courses=total_courses)

    fallback_paid = (
        KeyWorkerContext(key=GEMINI_PAID_KEY, key_name="GEMINI_PAGO_RICARDO", is_paid=True, min_interval=1.0)
        if GEMINI_PAID_KEY else None
    )

    worker_contexts = []
    # 1. Workers das chaves gratuitas (15 RPM / 4.0s de intervalo)
    for idx, k in enumerate(GEMINI_FREE_KEYS):
        worker_contexts.append(
            KeyWorkerContext(key=k, key_name=f"FREE_KEY_{idx+1}", is_paid=False, min_interval=4.0)
        )

    # 2. Coworker dedicado na chave paga com Inferência Flexível (Gemini 3.5 Flash Lite + Files API)
    if GEMINI_PAID_KEY:
        worker_contexts.append(
            KeyWorkerContext(key=GEMINI_PAID_KEY, key_name="PAID_WORKER_FLEX", is_paid=True, min_interval=1.0)
        )

    num_workers = len(worker_contexts)
    logger.info(
        f"Iniciando Etapa 2 paralela com {num_workers} workers "
        f"({len(GEMINI_FREE_KEYS)} Gratuitos a 15 RPM + 1 Coworker Pago Flexível) "
        f"e Teto Orçamentário de ${BUDGET_LIMIT_USD:.2f} USD."
    )

    course_queue = Queue()
    for c in all_courses:
        course_queue.put(c)

    def worker_thread(worker_id: int):
        ctx = worker_contexts[worker_id % len(worker_contexts)]
        logger.info(f"Worker {worker_id+1} de Perguntas ativo na {ctx.key_name}.")

        while not course_queue.empty():
            try:
                course = course_queue.get_nowait()
            except Exception:
                break

            try:
                process_course_questions(
                    course_info=course,
                    worker_ctx=ctx,
                    fallback_paid=fallback_paid,
                    budget_mgr=budget_mgr
                )
            except BudgetExceededException as be:
                logger.warning(f"Worker {worker_id+1} ({ctx.key_name}) interrompido por teto orçamentário: {be}")
                with course_queue.mutex:
                    course_queue.queue.clear()
                break
            except Exception as e:
                logger.error(f"Erro inesperado no curso {course.get('nome')}: {e}")
            finally:
                course_queue.task_done()

    threads = []
    for w_id in range(num_workers):
        t = threading.Thread(target=worker_thread, args=(w_id,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    # Relatório final
    done_count = len(budget_mgr.completed_courses)
    pct = (done_count / total_courses) * 100.0 if total_courses > 0 else 0.0
    logger.info("\n" + "=" * 80)
    logger.info("FINAL DA EXECUÇÃO - ETAPA 2 (CONJUNTO DE TESTES):")
    logger.info(f" - Cursos concluídos: {done_count}/{total_courses} ({pct:.1f}%)")
    logger.info(f" - Total de perguntas geradas: {len(budget_mgr.all_qa_records)}")
    logger.info(f" - Custo acumulado na chave paga: ${budget_mgr.paid_cost_usd:.4f} USD (Teto: ${BUDGET_LIMIT_USD:.2f})")
    logger.info("=" * 80)


def main():
    run_parallel_question_generation()


if __name__ == "__main__":
    main()
