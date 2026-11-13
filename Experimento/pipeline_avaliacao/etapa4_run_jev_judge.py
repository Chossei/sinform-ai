"""
===============================================================================
ETAPA 4: LLM JULGADOR AUTOMATIZADO COM TYPESAFE/JEV-1.14 (OPENROUTER DECISIONS)
===============================================================================
Avalia a conformidade de cada resposta gerada pelos métodos de RAG em relação ao
gabarito oficial, utilizando a API OpenRouter Decisions (modelo typesafe/jev-1.14)
com a primitiva 'choice' em 4 categorias qualitativas:
1. Incorreta
2. Parcialmente incorreta
3. Parcialmente correta
4. Correta

Gera métricas detalhadas de acurácia, probabilidades e relatórios para cada método.
===============================================================================
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
from typing import Dict, Any, Tuple, Optional, List
import pandas as pd

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from Experimento.pipeline_avaliacao.config import (
    OPENROUTER_KEYS_POOL, JEV_MODEL, TEST_DATASET_FILE, BACKUPS_DIR, LOGS_DIR
)
from Experimento.pipeline_avaliacao.prompts import (
    JEV_JUDGE_INSTRUCTIONS, JEV_JUDGE_STATE_TEMPLATE, JEV_JUDGE_CATEGORIES
)

OPENROUTER_DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
CHECKPOINT_FILE = BACKUPS_DIR / "checkpoint_jev_judge.json"
EXCEL_BACKUP_FILE = BACKUPS_DIR / "dataset_com_avaliacao_jev.xlsx"
JSONL_LOG_FILE = LOGS_DIR / "detalhes_jev_judge.jsonl"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "execucao_jev_judge.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("JEVJudgeEvaluator")

_SAVE_LOCK = threading.Lock()
_KEY_LOCK = threading.Lock()
_KEY_INDEX = 0


def get_next_openrouter_key() -> str:
    """Alterna em round-robin entre as chaves disponíveis no pool."""
    global _KEY_INDEX
    if not OPENROUTER_KEYS_POOL:
        raise ValueError("Nenhuma chave OpenRouter encontrada no ambiente!")
    with _KEY_LOCK:
        key = OPENROUTER_KEYS_POOL[_KEY_INDEX % len(OPENROUTER_KEYS_POOL)]
        _KEY_INDEX += 1
        return key


class JEVJudge:
    def __init__(self, model_name: str = JEV_MODEL):
        self.model = model_name

    def evaluate_response(
        self,
        pergunta: str,
        resposta_gabarito: str,
        resposta_modelo: str,
        max_retries: int = 4
    ) -> Dict[str, Any]:
        """
        Executa uma chamada de julgamento via Decisions API primitiva 'choice'.
        Retorna dicionário com choice, probabilities, confidence e metadados.
        """
        state_text = JEV_JUDGE_STATE_TEMPLATE.format(
            pergunta=pergunta,
            resposta_gabarito=resposta_gabarito,
            resposta_modelo=resposta_modelo
        )

        request_body = {
            "model": self.model,
            "state": state_text,
            "questions": {
                "avaliacao": {
                    "type": "choice",
                    "instructions": JEV_JUDGE_INSTRUCTIONS,
                    "criteria": JEV_JUDGE_CATEGORIES
                }
            }
        }

        for attempt in range(1, max_retries + 1):
            api_key = get_next_openrouter_key()
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            try:
                resp = requests.post(
                    OPENROUTER_DECISIONS_URL,
                    headers=headers,
                    json=request_body,
                    timeout=35,
                    verify=False
                )

                if resp.status_code == 429:
                    logger.warning(f"[JEV 429 Rate Limit] Tentativa {attempt}/{max_retries}. Aguardando {3 * attempt}s...")
                    time.sleep(3.0 * attempt)
                    continue

                if resp.status_code >= 400:
                    logger.error(f"[JEV Erro HTTP {resp.status_code}] {resp.text[:200]}")
                    time.sleep(2.0)
                    continue

                data = resp.json()
                answers = data.get("answers", {})
                eval_obj = answers.get("avaliacao", {})

                choice = eval_obj.get("choice", "Incorreta")
                probs = eval_obj.get("probabilities", {})
                confidence = eval_obj.get("confidence", 0.0)

                # Probabilidade associada à classe 'Correta'
                prob_correta = float(probs.get("Correta", 0.0))
                prob_parcial_correta = float(probs.get("Parcialmente correta", 0.0))
                prob_parcial_incorreta = float(probs.get("Parcialmente incorreta", 0.0))
                prob_incorreta = float(probs.get("Incorreta", 0.0))

                # Registrar no arquivo de log JSONL
                with _SAVE_LOCK:
                    with open(JSONL_LOG_FILE, "a", encoding="utf-8") as f:
                        log_entry = {
                            "timestamp": datetime.now().isoformat(),
                            "model": data.get("model", self.model),
                            "choice": choice,
                            "probabilities": probs,
                            "confidence": confidence,
                            "usage": data.get("usage", {})
                        }
                        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

                return {
                    "choice": choice,
                    "probabilities": probs,
                    "confidence": confidence,
                    "prob_correta": prob_correta,
                    "prob_parcial_correta": prob_parcial_correta,
                    "prob_parcial_incorreta": prob_parcial_incorreta,
                    "prob_incorreta": prob_incorreta,
                    "acerto_90": bool(prob_correta >= 0.90),
                    "acerto_95": bool(prob_correta >= 0.95),
                    "sucesso": True
                }

            except Exception as e:
                logger.warning(f"[JEV Exceção Tentativa {attempt}] {str(e)[:150]}")
                time.sleep(2.0)

        # Fallback de erro
        return {
            "choice": "Erro de julgamento",
            "probabilities": {},
            "confidence": 0.0,
            "prob_correta": 0.0,
            "prob_parcial_correta": 0.0,
            "prob_parcial_incorreta": 0.0,
            "prob_incorreta": 0.0,
            "acerto_90": False,
            "acerto_95": False,
            "sucesso": False
        }


def load_checkpoint() -> Dict[str, Any]:
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_checkpoint(completed_keys: List[str]):
    with _SAVE_LOCK:
        with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
            json.dump({"completed": completed_keys}, f, indent=2)


def evaluate_dataset(
    dataset_path: Path,
    output_path: Optional[Path] = None,
    max_workers: int = 4
) -> pd.DataFrame:
    """
    Avalia todas as colunas de respostas RAG presentes no arquivo do dataset.
    Identifica dinamicamente colunas no padrão 'resposta_modelo_rag_*'.
    """
    if not dataset_path.exists():
        raise FileNotFoundError(f"Arquivo de dataset não encontrado: {dataset_path}")

    df = pd.read_excel(dataset_path)
    logger.info(f"Carregado dataset com {len(df)} linhas e {len(df.columns)} colunas.")

    # Localizar todas as colunas de resposta do RAG
    rag_cols = [c for c in df.columns if c.startswith("resposta_modelo_rag_") or c == "resposta_modelo_rag_fichamento"]
    if not rag_cols:
        raise ValueError("Nenhuma coluna de resposta RAG ('resposta_modelo_rag_*') encontrada no arquivo!")

    logger.info(f"Colunas de respostas de RAG identificadas para julgamento: {rag_cols}")

    judge = JEVJudge()
    checkpoint_data = load_checkpoint()
    completed_keys = set(checkpoint_data.get("completed", []))

    # Inicializar colunas de julgamento no dataframe se não existirem
    for c in rag_cols:
        suffix = c.replace("resposta_modelo_rag_", "")
        if f"classificacao_jev_{suffix}" not in df.columns:
            df[f"classificacao_jev_{suffix}"] = None
        if f"prob_acerto_jev_{suffix}" not in df.columns:
            df[f"prob_acerto_jev_{suffix}"] = None
        if f"acerto_90_{suffix}" not in df.columns:
            df[f"acerto_90_{suffix}"] = None
        if f"acerto_95_{suffix}" not in df.columns:
            df[f"acerto_95_{suffix}"] = None

    tasks = []
    for row_idx, row in df.iterrows():
        pergunta = str(row.get("pergunta", ""))
        gabarito = str(row.get("resposta_gabarito", ""))

        for c in rag_cols:
            suffix = c.replace("resposta_modelo_rag_", "")
            task_key = f"{row_idx}_{c}"
            if task_key in completed_keys:
                continue

            resposta_modelo = str(row.get(c, ""))
            if not resposta_modelo or resposta_modelo.lower() == "nan":
                continue

            tasks.append((row_idx, c, suffix, task_key, pergunta, gabarito, resposta_modelo))

    logger.info(f"Total de avaliações pendentes a executar: {len(tasks)}")

    def worker_fn(task):
        r_idx, col_name, suffix, task_key, perg, gab, resp = task
        res = judge.evaluate_response(perg, gab, resp)
        return r_idx, col_name, suffix, task_key, res

    processed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(worker_fn, t) for t in tasks]
        for fut in as_completed(futures):
            r_idx, col_name, suffix, task_key, res = fut.result()
            processed += 1

            if res["sucesso"]:
                df.at[r_idx, f"classificacao_jev_{suffix}"] = res["choice"]
                df.at[r_idx, f"prob_acerto_jev_{suffix}"] = res["prob_correta"]
                df.at[r_idx, f"acerto_90_{suffix}"] = res["acerto_90"]
                df.at[r_idx, f"acerto_95_{suffix}"] = res["acerto_95"]
                completed_keys.add(task_key)

            if processed % 10 == 0 or processed == len(tasks):
                logger.info(f"[Progresso JEV Judge] {processed}/{len(tasks)} avaliações concluídas.")
                save_checkpoint(list(completed_keys))
                with _SAVE_LOCK:
                    df.to_excel(EXCEL_BACKUP_FILE, index=False)

    target_out = output_path or dataset_path
    df.to_excel(target_out, index=False)
    logger.info(f"Avaliação concluída com sucesso! Arquivo salvo em: {target_out}")
    return df


def main():
    print("=" * 70)
    print("SCRIPT 4: LLM JULGADOR AUTOMATIZADO COM TYPESAFE/JEV-1.14")
    print("Pronto para execução sob demanda.")
    print("=" * 70)


if __name__ == "__main__":
    main()

