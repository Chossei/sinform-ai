"""
Script de Avaliação Automatizada com JEV 1.14 ('typesafe/jev-1.14') via OpenRouter Decisions API.

Especificações de 'Experimento/instrucoes adicionais.md' e skill 'openrouter-decisions':
1. Endpoint oficial: POST https://openrouter.ai/api/alpha/decisions
2. Modelo: 'typesafe/jev-1.14' (primitiva de decisão booleana probabilística 'noul').
3. Chaves de API: OPEN_ROUTER_API_KEY e OPEN_ROUTER_API_KEY_2 presentes em 'Experimento/chave2.env'.
4. Engenharia de Prompt:
   "Você receberá uma pergunta e duas respostas a essa pergunta. A primeira resposta é a resposta correta, do gabarito. A segunda resposta foi construída por um LLM via RAG. Sua tarefa é verificar se a resposta do LLM via RAG contém a informação exigida pela pergunta em conformidade com o gabarito.

   PERGUNTA

   RESPOSTA GABARITO


   RESPOSTA MODELO
   "
5. Preenche no 'Conjunto de Testes.xlsx':
   - prob_acerto_jev_tradicional (probabilidade associada a TRUE em [0, 1])
   - prob_acerto_jev_fichamento  (probabilidade associada a TRUE em [0, 1])
   - acerto_95_tradicional       (TRUE quando prob_acerto_jev_tradicional >= 0.95, senão FALSE)
   - acerto_95_fichamento        (TRUE quando prob_acerto_jev_fichamento >= 0.95, senão FALSE)
6. Sistema de backup/checkpoint incremental ('Experimento/backups/') e logs em 'Experimento/logs/jev/'.
"""

import os
import sys
import json
import time
import shutil
import logging
import threading
import urllib3
import requests
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Tuple
import pandas as pd
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

EXPERIMENTO_DIR = Path(__file__).resolve().parent
BACKUP_DIR = EXPERIMENTO_DIR / "backups"
LOG_DIR = EXPERIMENTO_DIR / "logs" / "jev"

BACKUP_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

sys.path.append(str(EXPERIMENTO_DIR))
from rate_limiter import get_rate_limiter

# Carregar chaves do chave2.env
ENV_PATH = EXPERIMENTO_DIR / "chave2.env"
load_dotenv(ENV_PATH)

OR_KEY_1 = os.getenv("OPEN_ROUTER_API_KEY")
OR_KEY_2 = os.getenv("OPEN_ROUTER_API_KEY_2")
AVAILABLE_KEYS = [k for k in [OR_KEY_1, OR_KEY_2] if k]

if not AVAILABLE_KEYS:
    raise ValueError(f"Nenhuma chave OPEN_ROUTER_API_KEY encontrada em {ENV_PATH}!")

OPENROUTER_DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
JEV_MODEL_ID = "typesafe/jev-1.14"

DATASET_PATH = EXPERIMENTO_DIR / "Conjunto de Testes.xlsx"
CHECKPOINT_FILE = BACKUP_DIR / "checkpoint_jev.json"
EXCEL_BACKUP_LATEST = BACKUP_DIR / "Conjunto_de_Testes_backup_jev.xlsx"
JSONL_LOG_FILE = LOG_DIR / "detalhes_jev.jsonl"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "execucao_jev.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("RunJEVEvaluator")

_SAVE_LOCK = threading.Lock()
_KEY_LOCK = threading.Lock()
_KEY_COUNTER = 0


def _get_next_openrouter_key() -> Tuple[str, str]:
    """Alterna em round-robin entre OPEN_ROUTER_API_KEY e OPEN_ROUTER_API_KEY_2."""
    global _KEY_COUNTER
    with _KEY_LOCK:
        idx = _KEY_COUNTER % len(AVAILABLE_KEYS)
        _KEY_COUNTER += 1
        key_id = f"OPEN_ROUTER_API_KEY_{idx + 1}"
        return AVAILABLE_KEYS[idx], key_id


def build_jev_prompt(pergunta: str, resposta_gabarito: str, resposta_modelo: str) -> str:
    """
    Constrói o estado textual exatamente conforme especificado em 'instrucoes adicionais.md'.
    """
    return (
        "Você receberá uma pergunta e duas respostas a essa pergunta. "
        "A primeira resposta é a resposta correta, do gabarito. "
        "A segunda resposta foi construída por um LLM via RAG. "
        "Sua tarefa é verificar se a resposta do LLM via RAG contém a informação exigida "
        "pela pergunta em conformidade com o gabarito.\n\n"
        f"PERGUNTA\n{pergunta}\n\n"
        f"RESPOSTA GABARITO\n{resposta_gabarito}\n\n\n"
        f"RESPOSTA MODELO\n{resposta_modelo}\n"
    )


def evaluate_with_jev(
    pergunta: str,
    resposta_gabarito: str,
    resposta_modelo: str,
    rag_label: str,
    max_retries: int = 4
) -> Tuple[float, bool, Dict[str, Any]]:
    """
    Envia requisição POST para https://openrouter.ai/api/alpha/decisions com o modelo typesafe/jev-1.14
    usando a primitiva 'noul', retornando:
    - prob_true (float em [0.0, 1.0] associada a TRUE)
    - acerto_95 (bool: prob_true >= 0.95)
    - metadata da resposta (id, model, usage, cost)
    """
    instructions_text = (
        "Você receberá uma pergunta e duas respostas a essa pergunta. "
        "A primeira resposta é a resposta correta, do gabarito. "
        "A segunda resposta foi construída por um LLM via RAG. "
        "Sua tarefa é verificar se a resposta do LLM via RAG contém a informação exigida "
        "pela pergunta em conformidade com o gabarito."
    )

    state_payload = build_jev_prompt(
        pergunta=pergunta,
        resposta_gabarito=resposta_gabarito,
        resposta_modelo=resposta_modelo
    )

    request_body = {
        "model": JEV_MODEL_ID,
        "state": (
            f"PERGUNTA\n{pergunta}\n\n"
            f"RESPOSTA GABARITO\n{resposta_gabarito}\n\n\n"
            f"RESPOSTA MODELO\n{resposta_modelo}\n"
        ),
        "questions": {
            "acerto": {
                "type": "noul",
                "instructions": instructions_text
            }
        }
    }

    for attempt in range(1, max_retries + 1):
        api_key, key_id = _get_next_openrouter_key()
        limiter = get_rate_limiter(JEV_MODEL_ID, key_id=key_id)
        rate_info = limiter.acquire()

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        try:
            resp = requests.post(
                OPENROUTER_DECISIONS_URL,
                headers=headers,
                json=request_body,
                timeout=45,
                verify=False
            )

            if resp.status_code == 429:
                logger.warning(f"[JEV 429] Rate limit em {key_id} ({rag_label}). Aguardando {5 * attempt}s...")
                time.sleep(5 * attempt)
                continue

            if resp.status_code >= 400:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")

            data = resp.json()
            answers = data.get("answers", {})
            acerto_obj = answers.get("acerto", {})

            if acerto_obj.get("type") != "noul" or "noul" not in acerto_obj:
                raise ValueError(f"Formato inesperado em answers.acerto: {data}")

            prob_true = float(acerto_obj["noul"])
            is_acerto_95 = bool(prob_true >= 0.95)

            meta = {
                "decision_id": data.get("id"),
                "model_build": data.get("model"),
                "usage": data.get("usage", {}),
                "key_used": key_id,
                "rpm_current": rate_info["rpm_current"],
                "rpd_current": rate_info["rpd_current"]
            }
            return prob_true, is_acerto_95, meta

        except Exception as e:
            logger.warning(f"[JEV Tentativa {attempt}/{max_retries}] ({rag_label}) Erro: {e}")
            time.sleep(3 * attempt)

    raise RuntimeError(f"Falha ao avaliar com JEV 1.14 ({rag_label}) para a pergunta: {pergunta[:60]}...")


def load_checkpoint() -> dict:
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Falha ao ler checkpoint JEV: {e}")
    return {}


def save_progress(df: pd.DataFrame, checkpoint_data: dict, log_entry: dict):
    """Salva atomicamente o checkpoint JSON, o log JSONL e atualiza a planilha Excel."""
    with _SAVE_LOCK:
        with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)

        with open(JSONL_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        for idx_str, item in checkpoint_data.items():
            idx_int = int(idx_str)
            if 0 <= idx_int < len(df):
                if "prob_tradicional" in item and item["prob_tradicional"] is not None:
                    df.at[idx_int, "prob_acerto_jev_tradicional"] = item["prob_tradicional"]
                    df.at[idx_int, "acerto_95_tradicional"] = bool(item["acerto_95_tradicional"])
                if "prob_fichamento" in item and item["prob_fichamento"] is not None:
                    df.at[idx_int, "prob_acerto_jev_fichamento"] = item["prob_fichamento"]
                    df.at[idx_int, "acerto_95_fichamento"] = bool(item["acerto_95_fichamento"])

        df.to_excel(EXCEL_BACKUP_LATEST, index=False)
        df.to_excel(DATASET_PATH, index=False)


def run_jev_evaluation(max_workers: int = 5):
    logger.info("=" * 70)
    logger.info(" INICIANDO AVALIAÇÃO COM JEV 1.14 (OpenRouter Decisions API)")
    logger.info("=" * 70)

    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Conjunto de testes não encontrado em: {DATASET_PATH}")

    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    initial_backup = BACKUP_DIR / f"Conjunto_de_Testes_pre_jev_{ts_str}.xlsx"
    shutil.copy2(DATASET_PATH, initial_backup)
    logger.info(f"Backup inicial criado em: {initial_backup}")

    df = pd.read_excel(DATASET_PATH)

    for col in ["prob_acerto_jev_tradicional", "prob_acerto_jev_fichamento"]:
        if col not in df.columns:
            df[col] = None
    for col in ["acerto_95_tradicional", "acerto_95_fichamento"]:
        if col not in df.columns:
            df[col] = None
        df[col] = df[col].astype(object)

    checkpoint = load_checkpoint()

    # Sincronizar estado existente
    for idx, row in df.iterrows():
        idx_str = str(idx)
        entry = checkpoint.get(idx_str, {})
        if pd.notna(row.get("prob_acerto_jev_tradicional")) and "prob_tradicional" not in entry:
            p_t = float(row["prob_acerto_jev_tradicional"])
            entry["prob_tradicional"] = p_t
            entry["acerto_95_tradicional"] = bool(p_t >= 0.95)
        if pd.notna(row.get("prob_acerto_jev_fichamento")) and "prob_fichamento" not in entry:
            p_f = float(row["prob_acerto_jev_fichamento"])
            entry["prob_fichamento"] = p_f
            entry["acerto_95_fichamento"] = bool(p_f >= 0.95)
        if entry:
            checkpoint[idx_str] = entry

    def is_row_pending(idx: int) -> bool:
        entry = checkpoint.get(str(idx), {})
        has_trad_resp = pd.notna(df.at[idx, "resposta_modelo_rag_tradicional"]) and str(df.at[idx, "resposta_modelo_rag_tradicional"]).strip() != ""
        has_fich_resp = pd.notna(df.at[idx, "resposta_modelo_rag_fichamento"]) and str(df.at[idx, "resposta_modelo_rag_fichamento"]).strip() != ""

        need_trad = has_trad_resp and ("prob_tradicional" not in entry or entry["prob_tradicional"] is None)
        need_fich = has_fich_resp and ("prob_fichamento" not in entry or entry["prob_fichamento"] is None)
        return need_trad or need_fich

    pending_indices = [idx for idx in range(len(df)) if is_row_pending(idx)]
    logger.info(f"Total de linhas na planilha: {len(df)} | Pendentes de avaliação JEV: {len(pending_indices)}")

    if not pending_indices:
        logger.info("Nenhuma linha pendente de avaliação JEV (verifique se as respostas dos RAGs já foram geradas).")
        return

    def process_row(row_idx: int):
        pergunta = str(df.at[row_idx, "pergunta"]).strip()
        gabarito = str(df.at[row_idx, "resposta_gabarito"]).strip()
        resp_trad = df.at[row_idx, "resposta_modelo_rag_tradicional"]
        resp_fich = df.at[row_idx, "resposta_modelo_rag_fichamento"]

        with _SAVE_LOCK:
            entry = dict(checkpoint.get(str(row_idx), {}))

        meta_trad = {}
        meta_fich = {}

        # Avaliar RAG Tradicional se disponível e ainda não avaliado
        if pd.notna(resp_trad) and str(resp_trad).strip() != "" and entry.get("prob_tradicional") is None:
            prob_t, ac95_t, meta_trad = evaluate_with_jev(
                pergunta=pergunta,
                resposta_gabarito=gabarito,
                resposta_modelo=str(resp_trad).strip(),
                rag_label="RAG_Tradicional"
            )
            entry["prob_tradicional"] = prob_t
            entry["acerto_95_tradicional"] = ac95_t

        # Avaliar RAG Fichamento se disponível e ainda não avaliado
        if pd.notna(resp_fich) and str(resp_fich).strip() != "" and entry.get("prob_fichamento") is None:
            prob_f, ac95_f, meta_fich = evaluate_with_jev(
                pergunta=pergunta,
                resposta_gabarito=gabarito,
                resposta_modelo=str(resp_fich).strip(),
                rag_label="RAG_Fichamento"
            )
            entry["prob_fichamento"] = prob_f
            entry["acerto_95_fichamento"] = ac95_f

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "question_index": row_idx,
            "question_number": row_idx + 1,
            "prob_acerto_jev_tradicional": entry.get("prob_tradicional"),
            "acerto_95_tradicional": entry.get("acerto_95_tradicional"),
            "prob_acerto_jev_fichamento": entry.get("prob_fichamento"),
            "acerto_95_fichamento": entry.get("acerto_95_fichamento"),
            "meta_tradicional": meta_trad,
            "meta_fichamento": meta_fich
        }

        with _SAVE_LOCK:
            checkpoint[str(row_idx)] = entry

        save_progress(df, checkpoint, log_entry)
        logger.info(
            f"[JEV Q-{row_idx + 1:03d}/100] "
            f"Tradicional: prob={entry.get('prob_tradicional')} (95%={entry.get('acerto_95_tradicional')}) | "
            f"Fichamento: prob={entry.get('prob_fichamento')} (95%={entry.get('acerto_95_fichamento')})"
        )
        return row_idx

    completed = 0
    failed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {executor.submit(process_row, idx): idx for idx in pending_indices}
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                future.result()
                completed += 1
            except Exception as e:
                failed += 1
                logger.error(f"[ERRO JEV Q-{idx + 1:03d}] Falha na avaliação da pergunta {idx + 1}: {e}")

    # Calcular estatísticas finais se houver dados preenchidos
    df_final = pd.read_excel(DATASET_PATH)
    trad_acertos = df_final["acerto_95_tradicional"].dropna()
    fich_acertos = df_final["acerto_95_fichamento"].dropna()

    logger.info("=" * 70)
    logger.info(f" AVALIAÇÃO JEV 1.14 CONCLUÍDA | Processadas: {completed} | Falhas: {failed}")
    if len(trad_acertos) > 0:
        acc_trad = (trad_acertos == True).mean() * 100
        prob_mean_trad = df_final["prob_acerto_jev_tradicional"].dropna().mean()
        logger.info(f" -> RAG Tradicional: Acurácia (>=0.95) = {acc_trad:.2f}% | Prob Média = {prob_mean_trad:.4f}")
    if len(fich_acertos) > 0:
        acc_fich = (fich_acertos == True).mean() * 100
        prob_mean_fich = df_final["prob_acerto_jev_fichamento"].dropna().mean()
        logger.info(f" -> RAG Fichamento:  Acurácia (>=0.95) = {acc_fich:.2f}% | Prob Média = {prob_mean_fich:.4f}")
    logger.info("=" * 70)


if __name__ == "__main__":
    run_jev_evaluation(max_workers=5)

