"""
Script de Execução do Experimento — RAG Tradicional (Google FileSearchStore, Default Chunking, Top-10 Chunks).

Funcionalidades:
1. Carrega as 100 perguntas do curso 'Estatística (Bacharel)' em 'Experimento/Conjunto de Testes.xlsx'.
2. Executa as consultas em paralelo (ThreadPoolExecutor) respeitando estritamente os limites de
   RPM (15 RPM p/ gemini-3.5-flash-lite; 100 RPM p/ gemini-embedding-2) e RPD (500 RPD / 1000 RPD).
3. Possui sistema de checkpoint/backup incremental a cada pergunta concluída ('Experimento/backups/')
   e salva os resultados diretamente na coluna 'resposta_modelo_rag_tradicional' de 'Conjunto de Testes.xlsx'.
4. Registra logs detalhados em 'Experimento/logs/rag_tradicional/'.
"""

import os
import sys
import json
import time
import shutil
import logging
import threading
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

EXPERIMENTO_DIR = Path(__file__).resolve().parent
RAG_TRAD_DIR = EXPERIMENTO_DIR / "RAG Tradicional"
BACKUP_DIR = EXPERIMENTO_DIR / "backups"
LOG_DIR = EXPERIMENTO_DIR / "logs" / "rag_tradicional"

BACKUP_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

sys.path.append(str(EXPERIMENTO_DIR))
sys.path.append(str(RAG_TRAD_DIR))

from rag_tradicional_engine import RAGTradicional
from setup_file_search_tradicional import build_traditional_file_search_store, STORE_CONFIG_FILE

DATASET_PATH = EXPERIMENTO_DIR / "Conjunto de Testes.xlsx"
CHECKPOINT_FILE = BACKUP_DIR / "checkpoint_rag_tradicional.json"
EXCEL_BACKUP_LATEST = BACKUP_DIR / "Conjunto_de_Testes_backup_rag_tradicional.xlsx"
JSONL_LOG_FILE = LOG_DIR / "detalhes_rag_tradicional.jsonl"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "execucao_rag_tradicional.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("RunRAGTradicional")

_SAVE_LOCK = threading.Lock()


def load_checkpoint() -> dict:
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Falha ao ler checkpoint existente: {e}")
    return {}


def save_progress(df: pd.DataFrame, checkpoint_data: dict, log_entry: dict):
    """Salva de forma atômica e thread-safe o checkpoint JSON, o log JSONL e a planilha Excel."""
    with _SAVE_LOCK:
        # 1. Atualizar checkpoint JSON
        with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)

        # 2. Adicionar entrada no log JSONL
        with open(JSONL_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        # 3. Atualizar coluna no DataFrame e salvar Excel + Backup
        for idx_str, ans in checkpoint_data.items():
            idx_int = int(idx_str)
            if 0 <= idx_int < len(df):
                df.at[idx_int, "resposta_modelo_rag_tradicional"] = ans

        df.to_excel(EXCEL_BACKUP_LATEST, index=False)
        df.to_excel(DATASET_PATH, index=False)


def run_experiment_rag_tradicional(max_workers: int = 3, use_two_step_function_call: bool = True):
    logger.info("=" * 70)
    logger.info(" INICIANDO EXECUÇÃO DO EXPERIMENTO: RAG TRADICIONAL (Estatística)")
    logger.info("=" * 70)

    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Conjunto de testes não encontrado em: {DATASET_PATH}")

    # Garantir que a FileSearchStore do RAG Tradicional esteja criada e indexada
    if not STORE_CONFIG_FILE.exists():
        logger.info("Configuração da FileSearchStore não encontrada. Executando setup inicial...")
        build_traditional_file_search_store(force_recreate=True)

    # Criar backup inicial com timestamp antes de modificar a planilha
    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    initial_backup = BACKUP_DIR / f"Conjunto_de_Testes_pre_rag_tradicional_{ts_str}.xlsx"
    shutil.copy2(DATASET_PATH, initial_backup)
    logger.info(f"Backup inicial criado em: {initial_backup}")

    df = pd.read_excel(DATASET_PATH)
    if "resposta_modelo_rag_tradicional" not in df.columns:
        df["resposta_modelo_rag_tradicional"] = None
    df["resposta_modelo_rag_tradicional"] = df["resposta_modelo_rag_tradicional"].astype(object)

    checkpoint = load_checkpoint()

    # Sincronizar respostas já existentes na planilha ou no checkpoint
    for idx, row in df.iterrows():
        idx_str = str(idx)
        val = row.get("resposta_modelo_rag_tradicional")
        if idx_str in checkpoint and checkpoint[idx_str]:
            df.at[idx, "resposta_modelo_rag_tradicional"] = checkpoint[idx_str]
        elif pd.notna(val) and str(val).strip() != "":
            checkpoint[idx_str] = str(val).strip()

    pending_indices = [
        idx for idx in range(len(df))
        if str(idx) not in checkpoint or not str(checkpoint[str(idx)]).strip()
    ]

    logger.info(
        f"Total de perguntas: {len(df)} | Já concluídas: {len(df) - len(pending_indices)} | "
        f"Pendentes: {len(pending_indices)}"
    )

    if not pending_indices:
        logger.info("Todas as 100 perguntas já possuem resposta do RAG Tradicional!")
        return

    engine = RAGTradicional(use_two_step_function_call=use_two_step_function_call)

    def process_question(row_idx: int):
        pergunta = str(df.at[row_idx, "pergunta"]).strip()
        documento = str(df.at[row_idx, "documento"]).strip()
        t0 = time.time()

        logger.info(f"[Q-{row_idx + 1:03d}/100] Iniciando consulta | Doc: {documento}")
        answer, chunks, model_label, meta = engine.ask(
            query=pergunta,
            curso="Estatística (Bacharel)"
        )
        elapsed = round(time.time() - t0, 2)

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "question_index": row_idx,
            "question_number": row_idx + 1,
            "documento_origem": documento,
            "pergunta": pergunta,
            "resposta_rag_tradicional": answer,
            "model_label": model_label,
            "elapsed_sec": elapsed,
            "chunks_retrieved_count": len(chunks),
            "chunks_titles": [c.get("documento", "") for c in chunks],
            "telemetry": meta
        }

        with _SAVE_LOCK:
            checkpoint[str(row_idx)] = answer

        save_progress(df, checkpoint, log_entry)
        logger.info(
            f"[Q-{row_idx + 1:03d}/100] Concluída em {elapsed}s | "
            f"RPM={meta.get('rpm_last')}/15 | RPD={meta.get('rpd_last')}/500 | "
            f"Chunks={len(chunks)}"
        )
        return row_idx

    # Execução em chamadas paralelas (controladas pelo rate_limiter thread-safe)
    completed_count = 0
    failed_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {executor.submit(process_question, idx): idx for idx in pending_indices}
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                future.result()
                completed_count += 1
            except Exception as e:
                failed_count += 1
                logger.error(f"[ERRO Q-{idx + 1:03d}] Falha ao processar pergunta {idx + 1}: {e}")

    logger.info("=" * 70)
    logger.info(
        f" FIM DA EXECUÇÃO DO RAG TRADICIONAL | Sucesso: {completed_count} | Falhas: {failed_count}"
    )
    logger.info(f" Planilha atualizada: {DATASET_PATH}")
    logger.info(f" Backup salvo em: {EXCEL_BACKUP_LATEST}")
    logger.info("=" * 70)


if __name__ == "__main__":
    run_experiment_rag_tradicional(max_workers=3, use_two_step_function_call=True)

