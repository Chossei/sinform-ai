"""
===============================================================================
ETAPA 3: EXECUÇÃO DOS 4 MÉTODOS DE RAG EM COMPARAÇÃO E AVALIAÇÃO JEV (200 PERGUNTAS)
===============================================================================
Executa a comparação rigorosa das 10 configurações de RAG sobre o conjunto de 200 perguntas
(100 únicas de 1 PDF + 50 híbridas de 2 PDFs + 50 híbridas de 3 PDFs):
1.  rag_tradicional (k=1)
2.  rag_tradicional (k=5)
3.  rag_tradicional (k=10)
4.  rag_fichamento_embedding (k=1)
5.  rag_fichamento_embedding (k=5)
6.  rag_fichamento_embedding (k=10)
7.  rag_fichamento_jev_topk (k=1)
8.  rag_fichamento_jev_topk (k=5)
9.  rag_fichamento_jev_topk (k=10)
10. rag_fichamento_jev_livre (todos os fatiamentos com prob > 0.5)

Para cada resposta, o LLM Julgador JEV 1.14 classifica em:
- Incorreta
- Parcialmente incorreta
- Parcialmente correta
- Correta

Gera continuamente a base oficial 'Experimento/Resultados do teste.xlsx'.
===============================================================================
"""

import os
import sys
import json
import time
import shutil
import threading
import unicodedata
import tempfile
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import requests
import urllib3
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pypdf import PdfReader, PdfWriter

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
EXP_DIR = BASE_DIR / "Experimento"
sys.path.append(str(BASE_DIR))
sys.path.append(str(EXP_DIR))
sys.path.append(str(EXP_DIR / "RAG Tradicional"))

load_dotenv(EXP_DIR / "chave2.env")
load_dotenv(BASE_DIR / ".env")

from pipeline_avaliacao.config import (
    GEMINI_KEY_1, GEMINI_KEY_2, GEMINI_KEY_DRVCHOSSEI, GEMINI_KEY_PAGA,
    GEMINI_KEYS_POOL, OPENROUTER_KEYS_POOL, PRIMARY_MODEL, FALLBACK_MODEL,
    EMBEDDING_MODEL, JEV_MODEL, AREAS_DIR, BACKUPS_DIR, LOGS_DIR,
    COST_PROMPT_TOKEN_FLEX, COST_CANDIDATE_TOKEN_FLEX, COST_EMBEDDING_TOKEN
)
from pipeline_avaliacao.prompts import (
    RAG_GENERATOR_SYSTEM_PROMPT, RAG_USER_PROMPT_TEMPLATE,
    JEV_CONTEXT_SELECTOR_INSTRUCTIONS, JEV_JUDGE_INSTRUCTIONS, JEV_JUDGE_CATEGORIES
)
from rate_limiter import get_rate_limiter, RPDLimitExceededError

try:
    from rag_tradicional_engine import RAGTradicional
except Exception:
    RAGTradicional = None

OPENROUTER_DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
DATASET_200_FILE = EXP_DIR / "Conjunto de Testes 200.xlsx"
RESULTADOS_TESTE_FILE = EXP_DIR / "Resultados do teste.xlsx"
CHECKPOINT_RESULTADOS_FILE = BACKUPS_DIR / "checkpoint_resultados_teste.json"
UFBA_GERAL_DIR = AREAS_DIR / "UFBA - Geral"

_SAVE_LOCK = threading.Lock()


class OpenRouterCreditsExhaustedException(Exception):
    """Exceção levantada quando a API OpenRouter retorna falta de créditos ou erro 402."""
    pass


class GeminiKeyExhaustedException(Exception):
    """Exceção levantada quando a chave Gemini atual esgota RPM/RPD (429)."""
    pass


class BudgetCapReachedException(Exception):
    """Exceção levantada quando o teto de US$ 5,00 (Gemini pago ou OpenRouter) é atingido."""
    pass


MAX_GEMINI_PAID_USD = 5.00
MAX_OPENROUTER_USD = 5.00
_PRIOR_GEMINI_PAID_USD = 0.1932
_PRIOR_OPENROUTER_USD = 0.2716

_BUDGET_LOCK = threading.Lock()
_GEMINI_PAID_SPENT_USD = _PRIOR_GEMINI_PAID_USD
_OPENROUTER_SPENT_USD = _PRIOR_OPENROUTER_USD
_OR_KEY_LOCK = threading.Lock()
_OR_KEY_IDX = 0
_OR_DEAD_KEYS: Set[str] = set()


def record_openrouter_cost(cost: float):
    global _OPENROUTER_SPENT_USD
    with _BUDGET_LOCK:
        _OPENROUTER_SPENT_USD += float(cost or 0.0)
        if _OPENROUTER_SPENT_USD >= MAX_OPENROUTER_USD:
            raise BudgetCapReachedException(
                f"Teto OpenRouter atingido: ${_OPENROUTER_SPENT_USD:.4f} >= ${MAX_OPENROUTER_USD:.2f} USD"
            )


def record_gemini_paid_cost(cost: float):
    global _GEMINI_PAID_SPENT_USD
    with _BUDGET_LOCK:
        _GEMINI_PAID_SPENT_USD += float(cost or 0.0)
        if _GEMINI_PAID_SPENT_USD >= MAX_GEMINI_PAID_USD:
            raise BudgetCapReachedException(
                f"Teto Gemini Pago atingido: ${_GEMINI_PAID_SPENT_USD:.4f} >= ${MAX_GEMINI_PAID_USD:.2f} USD"
            )


def to_long_path(p: Path) -> Path:
    s = str(p.resolve())
    if os.name == "nt" and not s.startswith("\\\\?\\"):
        return Path("\\\\?\\" + s)
    return Path(s)


def norm_str(txt: Any) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", str(txt))
        if not unicodedata.combining(c)
    ).lower().strip()


def get_openrouter_key() -> str:
    global _OR_KEY_IDX
    if not OPENROUTER_KEYS_POOL:
        raise ValueError("Nenhuma chave OpenRouter encontrada!")
    with _OR_KEY_LOCK:
        alive = [k for k in OPENROUTER_KEYS_POOL if k not in _OR_DEAD_KEYS]
        if not alive:
            raise OpenRouterCreditsExhaustedException("Todas as chaves OpenRouter ficaram sem créditos/inválidas.")
        k = alive[_OR_KEY_IDX % len(alive)]
        _OR_KEY_IDX += 1
        return k


def mark_openrouter_key_dead(key: str):
    with _OR_KEY_LOCK:
        _OR_DEAD_KEYS.add(key)


def check_openrouter_balance() -> float:
    """Consulta o saldo restante em USD na conta OpenRouter."""
    try:
        key = get_openrouter_key()
        r = requests.get("https://openrouter.ai/api/v1/credits", headers={"Authorization": f"Bearer {key}"}, timeout=10)
        if r.status_code == 200:
            d = r.json().get("data", {})
            total = float(d.get("total_credits", 0.0))
            usage = float(d.get("total_usage", 0.0))
            return max(0.0, total - usage)
    except Exception:
        pass
    return 1.0


# -----------------------------------------------------------------------------
# MAPA DE CURSOS E CARREGAMENTO MULTI-CURSO DO BANCO VETORIAL
# -----------------------------------------------------------------------------
_COURSE_DIR_MAP: Dict[str, Path] = {}
_COURSE_BV_CACHE: Dict[str, Tuple[pd.DataFrame, np.ndarray, Path]] = {}
_CACHE_LOCK = threading.Lock()


def build_course_dir_map() -> Dict[str, Path]:
    global _COURSE_DIR_MAP
    with _CACHE_LOCK:
        if _COURSE_DIR_MAP:
            return _COURSE_DIR_MAP
        tmp_map: Dict[str, Path] = {}
        if AREAS_DIR.exists():
            for area_d in AREAS_DIR.iterdir():
                if not area_d.is_dir():
                    continue
                tmp_map[area_d.name.strip()] = area_d
                tmp_map[norm_str(area_d.name)] = area_d
                for c_d in area_d.iterdir():
                    if c_d.is_dir():
                        tmp_map[c_d.name.strip()] = c_d
                        tmp_map[norm_str(c_d.name)] = c_d
        _COURSE_DIR_MAP = tmp_map
        return _COURSE_DIR_MAP


def get_course_bv(course_name: str) -> Optional[Tuple[pd.DataFrame, np.ndarray, Path]]:
    cmap = build_course_dir_map()
    c_dir = cmap.get(course_name.strip()) or cmap.get(norm_str(course_name))
    if not c_dir:
        return None
    key = c_dir.name
    with _CACHE_LOCK:
        if key in _COURSE_BV_CACHE:
            return _COURSE_BV_CACHE[key]

    bv_dir = c_dir / "banco vetorial"
    pq_path = bv_dir / "banco_vetorial.parquet"
    npy_path = bv_dir / "embeddings.npy"
    if not to_long_path(pq_path).exists() or not to_long_path(npy_path).exists():
        return None

    df_bv = pd.read_parquet(to_long_path(pq_path)).copy()
    emb_matrix = np.load(to_long_path(npy_path))
    df_bv["_course_dir"] = str(c_dir)
    with _CACHE_LOCK:
        if key not in _COURSE_BV_CACHE:
            _COURSE_BV_CACHE[key] = (df_bv, emb_matrix, c_dir)
        return _COURSE_BV_CACHE[key]


def load_union_bv_for_courses(curso_field: str) -> Tuple[pd.DataFrame, np.ndarray, Path]:
    """
    Carrega e concatena os bancos vetoriais (parquet + embeddings.npy) de todos os cursos
    envolvidos na pergunta (1 curso para únicas ou híbridas intra-curso; 2 ou 3 cursos para
    híbridas inter-cursos), desduplicando fatias idênticas.
    """
    cursos_list = [c.strip() for c in str(curso_field).split(";") if c.strip()]
    cmap = build_course_dir_map()
    include_ug = False
    for c_name in cursos_list:
        c_dir = cmap.get(c_name) or cmap.get(norm_str(c_name))
        if c_dir and len([p for p in to_long_path(c_dir).glob("*.pdf") if to_long_path(p).is_file()]) < 3:
            include_ug = True
            break
    if include_ug and "UFBA - Geral" not in cursos_list:
        cursos_list.append("UFBA - Geral")

    dfs = []
    embs = []
    primary_dir = EXP_DIR

    for idx, c_name in enumerate(cursos_list):
        loaded = get_course_bv(c_name)
        if loaded is not None:
            df_c, emb_c, c_dir = loaded
            if idx == 0:
                primary_dir = c_dir
            dfs.append(df_c)
            embs.append(emb_c)

    if not dfs:
        raise RuntimeError(f"Nenhum banco vetorial encontrado para o(s) curso(s): {curso_field}")

    if len(dfs) == 1:
        df_union = dfs[0].reset_index(drop=True)
        emb_union = embs[0]
        return df_union, emb_union, primary_dir

    df_concat = pd.concat(dfs, ignore_index=True)
    emb_concat = np.vstack(embs)

    # Desduplicar fatias idênticas (mesmo documento e mesmas páginas)
    dedup_key = df_concat["nome do documento"].astype(str) + "__" + df_concat["páginas"].astype(str)
    keep_mask = ~dedup_key.duplicated(keep="first")
    df_union = df_concat.loc[keep_mask].reset_index(drop=True)
    emb_union = emb_concat[keep_mask.to_numpy()]

    return df_union, emb_union, primary_dir


# -----------------------------------------------------------------------------
# RESOLUTOR E GERADOR DE FATIAS PDF ON-THE-FLY
# -----------------------------------------------------------------------------
def resolve_and_ensure_slice(raw_path: str, course_dir: Path) -> Optional[Path]:
    """
    Garante que a fatia PDF exista no disco. Se não existir, extrai o intervalo
    de páginas do PDF original correspondente usando pypdf.
    """
    p = Path(raw_path)
    file_name = p.name
    parent_doc_dir = p.parent.name

    candidates = [
        p,
        BASE_DIR / p,
        EXP_DIR / p,
        course_dir / p,
        course_dir / parent_doc_dir / file_name,
        course_dir / file_name,
        UFBA_GERAL_DIR / parent_doc_dir / file_name,
        UFBA_GERAL_DIR / file_name
    ]
    for c in candidates:
        lp = to_long_path(c)
        if lp.exists():
            return lp.resolve()

    m = re.search(r'paginas_(\d+)-(\d+)\.pdf$', file_name, re.IGNORECASE)
    if not m:
        return None
    p_start, p_end = int(m.group(1)), int(m.group(2))
    doc_stem = re.sub(r'_paginas_\d+-\d+$', '', Path(file_name).stem)

    orig_candidates = [
        course_dir / f"{doc_stem}.pdf",
        UFBA_GERAL_DIR / f"{doc_stem}.pdf"
    ]
    orig_pdf = None
    for c in orig_candidates:
        lp = to_long_path(c)
        if lp.exists():
            orig_pdf = lp
            break

    if not orig_pdf:
        for c in to_long_path(course_dir).glob("*.pdf"):
            if doc_stem.lower() in c.stem.lower() or c.stem.lower() in doc_stem.lower():
                orig_pdf = to_long_path(c)
                break
        if not orig_pdf and UFBA_GERAL_DIR.exists():
            for c in to_long_path(UFBA_GERAL_DIR).glob("*.pdf"):
                if doc_stem.lower() in c.stem.lower() or c.stem.lower() in doc_stem.lower():
                    orig_pdf = to_long_path(c)
                    break

    if not orig_pdf or not orig_pdf.exists():
        return None

    target_path = to_long_path(course_dir / parent_doc_dir / file_name)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        reader = PdfReader(str(orig_pdf))
        writer = PdfWriter()
        n_pages = len(reader.pages)
        start_idx = max(0, p_start - 1)
        end_idx = min(n_pages, p_end)
        for p_no in range(start_idx, end_idx):
            writer.add_page(reader.pages[p_no])
        with open(target_path, "wb") as f:
            writer.write(f)
        return target_path.resolve()
    except Exception:
        return None


# -----------------------------------------------------------------------------
# 1. JEV SELETOR DE FATIAS (UMA REQUISIÇÃO INDIVIDUAL POR FATIAMENTO)
# -----------------------------------------------------------------------------
def _call_openrouter_decision(payload: Dict[str, Any], timeout: int = 30, max_attempts: int = 6) -> Dict[str, Any]:
    """Executa chamada ao endpoint OpenRouter Decisions com rotação de chaves e retentativas."""
    last_err = "sem resposta"
    for attempt in range(max_attempts):
        key = get_openrouter_key()
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        try:
            r = requests.post(OPENROUTER_DECISIONS_URL, headers=headers, json=payload, timeout=timeout, verify=False)
            if r.status_code == 200:
                data = r.json()
                cost = float(data.get("usage", {}).get("cost", 0.0))
                record_openrouter_cost(cost)
                return data
            last_err = f"HTTP {r.status_code}: {r.text[:160]}"
            low_txt = r.text.lower()
            if r.status_code == 402 or (
                r.status_code in (401, 403)
                and any(w in low_txt for w in ["credit", "balance", "insufficient", "payment", "quota", "user not found"])
            ) or any(w in low_txt for w in ["credit", "balance", "insufficient"]):
                mark_openrouter_key_dead(key)
            elif r.status_code == 429:
                time.sleep(min(15.0, 2.0 * (attempt + 1)))
            else:
                time.sleep(min(8.0, 1.5 * (attempt + 1)))
        except (OpenRouterCreditsExhaustedException, BudgetCapReachedException):
            raise
        except Exception as exc:
            last_err = str(exc)
            time.sleep(min(8.0, 1.5 * (attempt + 1)))
    raise RuntimeError(f"OpenRouter Decisions falhou após {max_attempts} tentativas ({last_err})")


def call_jev_slice_eval(doc_name: str, pergunta: str, resumo: str) -> Tuple[bool, float, float]:
    """
    Executa UMA requisição individual para avaliar a pertinência da fatia.
    Configurado no modo flexível / otimização de custos da Decisions API.
    """
    state_text = (
        f"Verifique se a informacao que o usuario solicita pode estar presente no trecho do documento "
        f"{doc_name} de acordo com seu respectivo resumo.\n\n"
        f"Mensagem do usuario:\n{pergunta}\n\n"
        f"Resumo do documento:\n{resumo}"
    )

    payload = {
        "model": JEV_MODEL,
        "state": state_text,
        "questions": {
            "selecao_fatia": {
                "type": "choice",
                "instructions": "Determine se a informacao solicitada pelo usuario pode estar presente neste trecho do documento de acordo com o resumo apresentado.",
                "criteria": {
                    "TRUE": "O resumo indica que este trecho do documento contem informacoes relevantes ou necessarias para responder a pergunta do usuario.",
                    "FALSE": "O resumo indica que este trecho nao contem informacoes relevantes para a pergunta do usuario."
                }
            }
        },
        "provider": {"sort": "price"},
        "service_tier": "flex"
    }

    data = _call_openrouter_decision(payload, timeout=25, max_attempts=6)
    ans = data.get("answers", {}).get("selecao_fatia", {})
    choice = ans.get("choice", "FALSE")
    prob_true = float(ans.get("probabilities", {}).get("TRUE", 0.0))
    cost = float(data.get("usage", {}).get("cost", 0.0))
    is_true = (prob_true > 0.50 or choice == "TRUE")
    return is_true, prob_true, cost


# -----------------------------------------------------------------------------
# 2. GERAÇÃO DA RESPOSTA VIA GEMINI 3.5 FLASH LITE COM API FILE
# -----------------------------------------------------------------------------
def generate_gemini_rag_answer_with_handles(
    client: genai.Client,
    pergunta: str,
    file_handles: List[Any],
    use_paid_key: bool = True,
    key_id: str = "GEMINI_API_KEY"
) -> Tuple[str, float]:
    """
    Gera a resposta no Gemini utilizando handles já carregados na API File.
    Usa estritamente PRIMARY_MODEL (gemini-3.5-flash-lite).
    """
    contents = list(file_handles)
    contents.append(RAG_USER_PROMPT_TEMPLATE.format(pergunta=pergunta))

    res_text = "Esta informação não consta nos documentos consultados."
    custo_gemini = 0.0

    limiter = get_rate_limiter(PRIMARY_MODEL, key_id=key_id)

    for attempt in range(1, 4):
        try:
            limiter.acquire()
            cfg_kwargs = {
                "system_instruction": RAG_GENERATOR_SYSTEM_PROMPT,
                "temperature": 0.2
            }
            if use_paid_key:
                cfg_kwargs["service_tier"] = "flex"

            res = client.models.generate_content(
                model=PRIMARY_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(**cfg_kwargs)
            )
            res_text = res.text.strip()
            if res.usage_metadata:
                p_tok = res.usage_metadata.prompt_token_count or 0
                c_tok = res.usage_metadata.candidates_token_count or 0
                custo_gemini = (p_tok * COST_PROMPT_TOKEN_FLEX) + (c_tok * COST_CANDIDATE_TOKEN_FLEX)
                if use_paid_key:
                    record_gemini_paid_cost(custo_gemini)
            return res_text, custo_gemini
        except BudgetCapReachedException:
            raise
        except RPDLimitExceededError as rpe:
            raise GeminiKeyExhaustedException(f"RPD esgotado em {key_id}: {rpe}")
        except Exception as e:
            err_str = str(e)
            print(f"    [Aviso Gemini {PRIMARY_MODEL} ({key_id}) Tentativa {attempt}/3]: {err_str[:90]}", flush=True)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                if attempt >= 2:
                    raise GeminiKeyExhaustedException(f"Cota/429 persistente em {key_id}: {err_str[:120]}")
                time.sleep(5.0)
            else:
                time.sleep(2.0 * attempt)

    return res_text, custo_gemini


# -----------------------------------------------------------------------------
# 3. LLM JULGADOR AUTOMATIZADO COM JEV 1.14 (4 CATEGORIAS OFICIAIS)
# -----------------------------------------------------------------------------
def evaluate_with_jev_judge(pergunta: str, gabarito: str, resposta_modelo: str) -> Tuple[str, Dict[str, float], float]:
    """
    Avalia a resposta do modelo contra o gabarito oficial em 4 categorias:
    - Incorreta
    - Parcialmente incorreta
    - Parcialmente correta
    - Correta
    """
    state_text = (
        f"Avalie se a resposta do modelo gerada via RAG condiz com o gabarito oficial para a pergunta apresentada.\n\n"
        f"PERGUNTA\n{pergunta}\n\n"
        f"RESPOSTA GABARITO\n{gabarito}\n\n"
        f"RESPOSTA MODELO\n{resposta_modelo}"
    )

    payload = {
        "model": JEV_MODEL,
        "state": state_text,
        "questions": {
            "decisao_julgador": {
                "type": "choice",
                "instructions": "Avalie se a resposta do modelo gerada via RAG condiz com o gabarito oficial para a pergunta apresentada.",
                "criteria": JEV_JUDGE_CATEGORIES
            }
        },
        "provider": {"sort": "price"},
        "service_tier": "flex"
    }

    data = _call_openrouter_decision(payload, timeout=30, max_attempts=6)
    ans = data.get("answers", {}).get("decisao_julgador", {})
    choice = ans.get("choice", "Incorreta")
    probs = ans.get("probabilities", {})
    cost = float(data.get("usage", {}).get("cost", 0.0))
    return choice, probs, cost


# -----------------------------------------------------------------------------
# 4. GERENCIAMENTO DE CHECKPOINT E RESULTADOS EXCEL
# -----------------------------------------------------------------------------
def archive_legacy_results_if_needed():
    """
    Se 'Resultados do teste.xlsx' existir mas for da etapa antiga (sem a coluna 'Classificação'),
    arquiva automaticamente na pasta backups antes de iniciar o experimento de 200 perguntas.
    """
    if RESULTADOS_TESTE_FILE.exists():
        try:
            df_existing = pd.read_excel(to_long_path(RESULTADOS_TESTE_FILE))
            if "Classificação" not in df_existing.columns and "tipo_pergunta" not in df_existing.columns:
                archive_dir = BACKUPS_DIR / "etapa_anterior_1680"
                archive_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(RESULTADOS_TESTE_FILE), str(archive_dir / "Resultados_do_teste_1680.xlsx"))
                if CHECKPOINT_RESULTADOS_FILE.exists():
                    shutil.move(str(CHECKPOINT_RESULTADOS_FILE), str(archive_dir / "checkpoint_resultados_teste_1680.json"))
                stream_file = BACKUPS_DIR / "resultados_teste_stream.jsonl"
                if stream_file.exists():
                    shutil.move(str(stream_file), str(archive_dir / "resultados_teste_stream_1680.jsonl"))
                print(f"[Arquivo] Resultados anteriores ({len(df_existing)} linhas) arquivados em: {archive_dir}", flush=True)
        except Exception as e:
            print(f"[Aviso Archive Legacy]: {e}", flush=True)


def load_checkpoint(include_pending_jev: bool = True) -> set:
    keys = set()
    if RESULTADOS_TESTE_FILE.exists():
        try:
            df_ex = pd.read_excel(to_long_path(RESULTADOS_TESTE_FILE))
            for _, row in df_ex.iterrows():
                q_id = str(row.get("ID_Pergunta", "")).strip()
                m = str(row.get("metodo_rag", "")).strip()
                k = str(row.get("top_k", "")).strip()
                dec = str(row.get("decisao_julgador", "")).strip()
                if q_id and m and k:
                    ek = f"{q_id}__{m}__k{k}"
                    if dec == "PENDENTE_JEV" and not include_pending_jev:
                        continue
                    keys.add(ek)
            return keys
        except Exception:
            pass
    if CHECKPOINT_RESULTADOS_FILE.exists():
        try:
            with open(CHECKPOINT_RESULTADOS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                keys.update(data.get("completed_keys", []))
            elif isinstance(data, list):
                keys.update(data)
        except Exception:
            pass
    return keys


def judge_pending_rows() -> int:
    """Julga todas as linhas com decisao_julgador == 'PENDENTE_JEV' usando JEV 1.14 em paralelo."""
    global _DF_RESULTS_CACHE
    if not RESULTADOS_TESTE_FILE.exists():
        return 0
    df = pd.read_excel(to_long_path(RESULTADOS_TESTE_FILE))
    pending_mask = df["decisao_julgador"].astype(str).str.strip() == "PENDENTE_JEV"
    pending_indices = df.index[pending_mask].tolist()
    if not pending_indices:
        return 0

    print(f"\n[JEV Julgador] Avaliando {len(pending_indices)} resposta(s) pendente(s) com JEV 1.14 (paralelo)...", flush=True)

    def _judge_one(idx: int):
        row = df.loc[idx]
        dec, probs, cost = evaluate_with_jev_judge(
            str(row.get("Pergunta", "")),
            str(row.get("Gabarito", "")),
            str(row.get("Resposta do modelo", "")),
        )
        return idx, dec, probs, cost

    judged = 0
    try:
        with ThreadPoolExecutor(max_workers=20) as ex:
            fut_idx_map = {ex.submit(_judge_one, idx): idx for idx in pending_indices}
            for fut in as_completed(fut_idx_map):
                idx_orig = fut_idx_map[fut]
                try:
                    idx, dec, probs, cost = fut.result()
                except (BudgetCapReachedException, OpenRouterCreditsExhaustedException):
                    raise
                except Exception as je:
                    print(f"  [Aviso JEV Julgador linha {idx_orig}]: {je}", flush=True)
                    continue
                df.at[idx, "decisao_julgador"] = dec
                df.at[idx, "logprob_julgador_Incorreta"] = probs.get("Incorreta", 0.0)
                df.at[idx, "logprob_julgador_Parcialmente_incorreta"] = probs.get("Parcialmente incorreta", 0.0)
                df.at[idx, "logprob_julgador_Parcialmente_correta"] = probs.get("Parcialmente correta", 0.0)
                df.at[idx, "logprob_julgador_Correta"] = probs.get("Correta", 0.0)
                df.at[idx, "custo_jev_julgador"] = round(cost, 6)
                judged += 1
                if judged % 50 == 0:
                    print(f"  [JEV Julgador] {judged}/{len(pending_indices)} avaliada(s) | OpenRouter: ${_OPENROUTER_SPENT_USD:.4f}", flush=True)
                if judged % 100 == 0:
                    with _SAVE_LOCK:
                        _DF_RESULTS_CACHE = df
                        df.to_excel(to_long_path(RESULTADOS_TESTE_FILE), index=False)
                        df.to_excel(to_long_path(BACKUPS_DIR / "Resultados_do_teste_backup.xlsx"), index=False)
    finally:
        with _SAVE_LOCK:
            _DF_RESULTS_CACHE = df
            df.to_excel(to_long_path(RESULTADOS_TESTE_FILE), index=False)
            df.to_excel(to_long_path(BACKUPS_DIR / "Resultados_do_teste_backup.xlsx"), index=False)
        print(f"[JEV Julgador] {judged}/{len(pending_indices)} linha(s) atualizada(s) em {RESULTADOS_TESTE_FILE}.", flush=True)
    return judged


def save_checkpoint(completed_keys: set):
    with _SAVE_LOCK:
        BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
        with open(CHECKPOINT_RESULTADOS_FILE, "w", encoding="utf-8") as f:
            json.dump({"completed_keys": list(completed_keys)}, f, indent=2)


_DF_RESULTS_CACHE: Optional[pd.DataFrame] = None


def append_result_rows(rows: List[Dict[str, Any]]):
    global _DF_RESULTS_CACHE
    with _SAVE_LOCK:
        BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

        stream_file = BACKUPS_DIR / "resultados_teste_stream.jsonl"
        with open(stream_file, "a", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        df_new_rows = pd.DataFrame(rows)
        if _DF_RESULTS_CACHE is None:
            if RESULTADOS_TESTE_FILE.exists():
                try:
                    _DF_RESULTS_CACHE = pd.read_excel(to_long_path(RESULTADOS_TESTE_FILE))
                    _DF_RESULTS_CACHE = pd.concat([_DF_RESULTS_CACHE, df_new_rows], ignore_index=True)
                except Exception:
                    _DF_RESULTS_CACHE = df_new_rows
            else:
                _DF_RESULTS_CACHE = df_new_rows
        else:
            _DF_RESULTS_CACHE = pd.concat([_DF_RESULTS_CACHE, df_new_rows], ignore_index=True)

        _DF_RESULTS_CACHE.to_excel(to_long_path(RESULTADOS_TESTE_FILE), index=False)
        _DF_RESULTS_CACHE.to_excel(to_long_path(BACKUPS_DIR / "Resultados_do_teste_backup.xlsx"), index=False)


# -----------------------------------------------------------------------------
# 5. EXECUÇÃO COMPARATIVA POR PERGUNTA (10 CONFIGURAÇÕES)
# -----------------------------------------------------------------------------
def run_evaluation_for_question(
    client: genai.Client,
    rag_trad_engine: Optional[Any],
    course_name: str,
    primary_course_dir: Path,
    df_bv: pd.DataFrame,
    emb_matrix: np.ndarray,
    question_row: Dict[str, Any],
    q_id: str,
    completed_keys: set,
    use_paid_key: bool = False,
    key_id: str = "GEMINI_API_KEY",
    allowed_methods: Optional[Set[str]] = None,
    defer_judge: bool = False,
) -> List[Dict[str, Any]]:
    """Executa as 10 configurações para uma pergunta (única ou híbrida) e avalia com JEV."""
    def clean_field(val: Any) -> str:
        if val is None or pd.isna(val):
            return ""
        return str(val).strip()

    doc_name = clean_field(question_row.get("Documento") or question_row.get("documento"))
    pergunta = clean_field(question_row.get("Pergunta") or question_row.get("pergunta"))
    gabarito = clean_field(
        question_row.get("Resposta Gabarito") or
        question_row.get("resposta_gabarito") or
        question_row.get("Gabarito") or
        question_row.get("gabarito")
    )
    classificacao = clean_field(
        question_row.get("Classificação") or
        question_row.get("tipo_pergunta") or
        "única"
    )
    qtd_pdfs_origem = int(question_row.get("Quantidade_PDFs") or (2 if ";" in doc_name else 1))

    configs = [
        ("rag_tradicional", 1),
        ("rag_tradicional", 5),
        ("rag_tradicional", 10),
        ("rag_fichamento_embedding", 1),
        ("rag_fichamento_embedding", 5),
        ("rag_fichamento_embedding", 10),
        ("rag_fichamento_jev_topk", 1),
        ("rag_fichamento_jev_topk", 5),
        ("rag_fichamento_jev_topk", 10),
        ("rag_fichamento_jev_livre", "Não se aplica"),
    ]
    pending_configs = [
        (m, k) for (m, k) in configs
        if (allowed_methods is None or m in allowed_methods)
        and f"{q_id}__{m}__k{k}" not in completed_keys
    ]
    if not pending_configs:
        return []

    needs_emb = any(m == "rag_fichamento_embedding" for m, _ in pending_configs)
    needs_jev_topk = any(m == "rag_fichamento_jev_topk" for m, _ in pending_configs)
    needs_jev_livre = any(m == "rag_fichamento_jev_livre" for m, _ in pending_configs)
    needs_jev_sel = needs_jev_topk or needs_jev_livre

    sorted_emb_indices: List[int] = []
    if needs_emb:
        # 1. Cálculo Embeddings para a pergunta
        print("    [Passo 1/4] Calculando embeddings da pergunta...", flush=True)
        try:
            res_emb = client.models.embed_content(model=EMBEDDING_MODEL, contents=pergunta)
            vals = res_emb.embeddings[0].values if hasattr(res_emb, "embeddings") else res_emb.embedding.values
            q_emb = np.array(vals, dtype=np.float32)
            norms = np.linalg.norm(emb_matrix, axis=1) * np.linalg.norm(q_emb)
            norms[norms == 0] = 1e-10
            sims = np.dot(emb_matrix, q_emb) / norms
            sorted_emb_indices = list(np.argsort(sims)[::-1])
            if use_paid_key:
                record_gemini_paid_cost(max(10, len(pergunta) // 3) * COST_EMBEDDING_TOKEN)
        except BudgetCapReachedException:
            raise
        except Exception as e:
            err_s = str(e)
            if "429" in err_s or "RESOURCE_EXHAUSTED" in err_s or "quota" in err_s.lower():
                raise GeminiKeyExhaustedException(f"Embedding 429 em {key_id}: {err_s[:120]}")
            print(f"    [Aviso Embedding]: {e}", flush=True)
            sorted_emb_indices = list(range(len(df_bv)))

    sorted_jev_indices: List[int] = []
    true_slices_indices: List[int] = []
    total_custo_jev_consultas = 0.0
    if needs_jev_sel:
        # 2. Consultas JEV (Uma chamada paralela para CADA fatiamento do banco vetorial)
        print(f"    [Passo 2/4] Avaliando {len(df_bv)} fatias com JEV Seletor (paralelo)...", flush=True)
        def eval_item(row_tuple):
            idx, row = row_tuple
            is_true, p_true, c_jev = call_jev_slice_eval(row["nome do documento"], pergunta, row["fichamento/resumo"])
            return idx, is_true, p_true, c_jev

        jev_evals = []
        with ThreadPoolExecutor(max_workers=20) as executor:
            futs = [executor.submit(eval_item, (i, r)) for i, r in df_bv.iterrows()]
            for f in as_completed(futs):
                res = f.result()
                jev_evals.append(res)
                total_custo_jev_consultas += res[3]

        jev_evals.sort(key=lambda x: x[2], reverse=True)
        sorted_jev_indices = [x[0] for x in jev_evals]
        true_slices_indices = [x[0] for x in jev_evals if x[2] > 0.50]
        if not true_slices_indices:
            true_slices_indices = [sorted_jev_indices[0]]

    uploaded_handles: Dict[int, Any] = {}
    temp_files: List[Path] = []

    if needs_emb or needs_jev_sel:
        # 3. Resolver fatias físicas apenas para as configurações pendentes
        print("    [Passo 3/4] Resolvendo fatias e preparando uploads...", flush=True)
        slice_cache: Dict[int, Optional[Path]] = {}
        def get_slice_path(idx: int) -> Optional[Path]:
            if idx not in slice_cache:
                row_s = df_bv.iloc[idx]
                raw = row_s["pdf_chunk_path"]
                c_dir_row = Path(row_s["_course_dir"]) if "_course_dir" in row_s and row_s["_course_dir"] else primary_course_dir
                slice_cache[idx] = resolve_and_ensure_slice(raw, c_dir_row)
            return slice_cache[idx]

        needed_slice_indices: Set[int] = set()
        for m, k in pending_configs:
            if m == "rag_fichamento_embedding":
                needed_slice_indices.update(sorted_emb_indices[:int(k)])
            elif m == "rag_fichamento_jev_topk":
                needed_slice_indices.update(sorted_jev_indices[:int(k)])
            elif m == "rag_fichamento_jev_livre":
                needed_slice_indices.update(true_slices_indices)

        # 4. Upload unificado para Gemini API File
        if needed_slice_indices:
            print(f"    [Passo 3/4] Fazendo upload de {len(needed_slice_indices)} fatias únicas para Gemini API File (paralelo)...", flush=True)

            def upload_single_slice(idx: int):
                sp = get_slice_path(idx)
                if sp and to_long_path(sp).exists():
                    clean_stem = "".join(c for c in unicodedata.normalize("NFKD", sp.stem) if not unicodedata.combining(c))
                    safe_ascii_name = f"rag_{idx}_{int(time.time()*1000)%100000}_{re.sub(r'[^a-zA-Z0-9_.-]', '_', clean_stem)[:40]}.pdf"
                    tmp = Path(tempfile.gettempdir()) / safe_ascii_name
                    try:
                        shutil.copy2(to_long_path(sp), tmp)
                        up = client.files.upload(file=str(tmp))
                        return idx, up, tmp
                    except Exception as e:
                        print(f"      [Erro upload fatia {idx}]: {e}", flush=True)
                return idx, None, None

            with ThreadPoolExecutor(max_workers=8) as executor:
                futs = [executor.submit(upload_single_slice, i) for i in needed_slice_indices]
                for f in as_completed(futs):
                    res_idx, up, tmp = f.result()
                    if up:
                        uploaded_handles[res_idx] = up
                    if tmp:
                        temp_files.append(tmp)

    print(f"    [Passo 4/4] Executando {len(pending_configs)} configuração(ões) pendente(s) e julgamentos JEV em paralelo...", flush=True)

    def process_config(cfg):
        metodo, k = cfg
        exec_key = f"{q_id}__{metodo}__k{k}"
        if exec_key in completed_keys:
            return None

        custo_gemini = 0.0
        custo_consultas = 0.0
        ans = "Não foi possível gerar resposta."
        qtd_docs = 0

        # --- A. RAG TRADICIONAL (FileSearchStore com PDFs inteiros) ---
        if metodo == "rag_tradicional":
            k_val = int(k)
            if not rag_trad_engine:
                raise RuntimeError(f"RAGTradicional engine indisponível para {q_id} ({key_id}).")
            try:
                resp_trad, chunks, _, usage_info = rag_trad_engine.ask(pergunta, curso=course_name, top_k=k_val)
                if not resp_trad or "Não foi possível" in resp_trad:
                    raise RuntimeError(f"Resposta inválida do RAGTradicional em {q_id} (k={k_val}): {resp_trad}")
                ans = resp_trad
                qtd_docs = len(chunks) or k_val
                p_tok = usage_info.get("input_tokens", 0)
                c_tok = usage_info.get("output_tokens", 0)
                custo_gemini = (p_tok * COST_PROMPT_TOKEN_FLEX) + (c_tok * COST_CANDIDATE_TOKEN_FLEX)
                if use_paid_key:
                    record_gemini_paid_cost(custo_gemini)
            except Exception as e:
                err_s = str(e)
                if "429" in err_s or "RESOURCE_EXHAUSTED" in err_s or "RPD" in err_s or "403" in err_s or "PERMISSION_DENIED" in err_s:
                    raise GeminiKeyExhaustedException(f"RAGTradicional cota esgotada ({key_id}): {err_s[:120]}")
                raise

        # --- B. RAG FICHAMENTO EMBEDDING ---
        elif metodo == "rag_fichamento_embedding":
            k_val = int(k)
            handles = [uploaded_handles[i] for i in sorted_emb_indices[:k_val] if i in uploaded_handles]
            qtd_docs = len(handles)
            ans, custo_gemini = generate_gemini_rag_answer_with_handles(client, pergunta, handles, use_paid_key=use_paid_key, key_id=key_id)

        # --- C. RAG FICHAMENTO JEV TOP-K ---
        elif metodo == "rag_fichamento_jev_topk":
            k_val = int(k)
            handles = [uploaded_handles[i] for i in sorted_jev_indices[:k_val] if i in uploaded_handles]
            qtd_docs = len(handles)
            custo_consultas = total_custo_jev_consultas
            ans, custo_gemini = generate_gemini_rag_answer_with_handles(client, pergunta, handles, use_paid_key=use_paid_key, key_id=key_id)

        # --- D. RAG FICHAMENTO JEV LIVRE (TODOS COM PROB > 0.5) ---
        elif metodo == "rag_fichamento_jev_livre":
            handles = [uploaded_handles[i] for i in true_slices_indices if i in uploaded_handles]
            qtd_docs = len(handles)
            custo_consultas = total_custo_jev_consultas
            ans, custo_gemini = generate_gemini_rag_answer_with_handles(client, pergunta, handles, use_paid_key=use_paid_key, key_id=key_id)

        # --- JULGAMENTO PELO JEV 1.14 ---
        if defer_judge:
            decisao = "PENDENTE_JEV"
            probs = {}
            custo_julgador = 0.0
        else:
            decisao, probs, custo_julgador = evaluate_with_jev_judge(pergunta, gabarito, ans)

        return {
            "ID_Pergunta": q_id,
            "Classificação": classificacao,
            "Quantidade_PDFs": qtd_pdfs_origem,
            "Documento": doc_name,
            "Curso": course_name,
            "Pergunta": pergunta,
            "Gabarito": gabarito,
            "Resposta do modelo": ans,
            "metodo_rag": metodo,
            "top_k": k,
            "quantidade_documentos": qtd_docs,
            "decisao_julgador": decisao,
            "logprob_julgador_Incorreta": probs.get("Incorreta", 0.0),
            "logprob_julgador_Parcialmente_incorreta": probs.get("Parcialmente incorreta", 0.0),
            "logprob_julgador_Parcialmente_correta": probs.get("Parcialmente correta", 0.0),
            "logprob_julgador_Correta": probs.get("Correta", 0.0),
            "custo_gemini": round(custo_gemini, 6),
            "custo_jev_consultas": round(custo_consultas, 6),
            "custo_jev_julgador": round(custo_julgador, 6),
        }

    new_rows = []
    with ThreadPoolExecutor(max_workers=max(1, len(pending_configs))) as executor:
        fut_cfg_map = {executor.submit(process_config, cfg): cfg for cfg in pending_configs}
        for f in as_completed(fut_cfg_map):
            cfg_cur = fut_cfg_map[f]
            try:
                res = f.result()
                if res:
                    new_rows.append(res)
            except (GeminiKeyExhaustedException, RPDLimitExceededError, BudgetCapReachedException, OpenRouterCreditsExhaustedException):
                raise
            except Exception as cfg_err:
                print(f"    [Aviso Config {q_id} {cfg_cur}]: {cfg_err}", flush=True)

    if uploaded_handles:
        def cleanup_up(up):
            try:
                client.files.delete(name=up.name)
            except Exception:
                pass

        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(cleanup_up, list(uploaded_handles.values())))

    for tmp in temp_files:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass

    return new_rows


# -----------------------------------------------------------------------------
# 6. RUNNER PRINCIPAL PARA O CONJUNTO DE 200 PERGUNTAS (ÚNICAS + HÍBRIDAS)
# -----------------------------------------------------------------------------
def run_stage3_benchmark(
    dataset_path: Optional[str] = None,
    max_questions: Optional[int] = None,
    use_free_key: bool = True,
    shutdown: bool = False,
    methods: Optional[List[str]] = None,
    defer_judge: bool = False,
    free_only: bool = False,
    judge_pending_only: bool = False,
):
    print("=" * 80, flush=True)
    print("ETAPA 3 BENCHMARK: AVALIAÇÃO COMPARATIVA DE RAGS (200 PERGUNTAS)", flush=True)
    print("=" * 80, flush=True)

    archive_legacy_results_if_needed()

    if not defer_judge:
        try:
            judge_pending_rows()
        except (BudgetCapReachedException, OpenRouterCreditsExhaustedException) as e:
            print(f"[Parada no Julgamento Pendente] {e}", flush=True)
            return

    if judge_pending_only:
        print("[Modo --judge-pending concluído]", flush=True)
        return

    allowed_methods: Optional[Set[str]] = set(methods) if methods else None
    print(f"Pool OpenRouter: {len(OPENROUTER_KEYS_POOL)} chave(s) | Teto OpenRouter: ${MAX_OPENROUTER_USD:.2f} USD | Defer Judge: {defer_judge}", flush=True)
    print(f"Teto Gemini Pago: ${MAX_GEMINI_PAID_USD:.2f} USD | Somente Gratuitas: {free_only} | Métodos: {sorted(allowed_methods) if allowed_methods else 'TODOS'}", flush=True)

    q_file = Path(dataset_path) if dataset_path else DATASET_200_FILE
    if not q_file.exists():
        q_file = EXP_DIR / "Conjunto de Testes.xlsx"
    if not q_file.exists():
        raise FileNotFoundError(f"Conjunto de testes não encontrado em {q_file}!")

    df_q = pd.read_excel(to_long_path(q_file))
    all_questions = df_q.to_dict(orient="records")
    if max_questions:
        all_questions = all_questions[:max_questions]

    print(f"Dataset carregado: {q_file.name} ({len(all_questions)} perguntas)", flush=True)

    # Pool ordenado: todas as chaves gratuitas primeiro, paga por último (a menos que --free-only)
    key_pool: List[Tuple[str, str, bool]] = []
    if use_free_key:
        for k_id, k_val in [
            ("GEMINI_API_KEY", GEMINI_KEY_1),
            ("GEMINI_API_KEY_2", GEMINI_KEY_2),
            ("GEMINI_API_KEY_DRVCHOSSEI", GEMINI_KEY_DRVCHOSSEI),
        ]:
            if k_val:
                key_pool.append((k_id, k_val, False))
    if not free_only and GEMINI_KEY_PAGA:
        key_pool.append(("GEMINI_PAGO_RICARDO", GEMINI_KEY_PAGA, True))

    if not key_pool:
        raise ValueError("Nenhuma chave Gemini configurada no pool!")

    pool_idx = 0

    def init_key_context(idx_p: int):
        k_id, k_val, is_paid = key_pool[idx_p]
        print(f"Chave Gemini ativa [{idx_p+1}/{len(key_pool)}]: {k_id} ({k_val[:10]}...) [Conta Paga: {is_paid}]", flush=True)
        cli = genai.Client(api_key=k_val)
        rte = None
        if RAGTradicional:
            try:
                rte = RAGTradicional(api_key=k_val, key_id=k_id)
                print(f"[RAGTradicional Engine] Inicializado para '{k_id}'.", flush=True)
            except Exception as e:
                print(f"[Aviso Inicialização RAGTradicional]: {e}", flush=True)
                rte = None
        return k_id, is_paid, cli, rte

    key_id, use_paid, gemini_client, rag_trad_engine = init_key_context(pool_idx)

    completed_keys = load_checkpoint(include_pending_jev=defer_judge)
    judged_checkpoint_keys = load_checkpoint(include_pending_jev=False)
    total_new_evaluations = 0

    def print_experiment_summary(reason: str):
        print("\n" + "=" * 80, flush=True)
        print(f"RESUMO DO EXPERIMENTO ({reason})", flush=True)
        print(f"Gasto Gemini Pago acumulado: ${_GEMINI_PAID_SPENT_USD:.4f} / ${MAX_GEMINI_PAID_USD:.2f} USD", flush=True)
        print(f"Gasto OpenRouter acumulado: ${_OPENROUTER_SPENT_USD:.4f} / ${MAX_OPENROUTER_USD:.2f} USD", flush=True)
        print(f"Novas avaliações salvas nesta execução: {total_new_evaluations}", flush=True)
        all_cfgs = [
            ("rag_tradicional", 1), ("rag_tradicional", 5), ("rag_tradicional", 10),
            ("rag_fichamento_embedding", 1), ("rag_fichamento_embedding", 5), ("rag_fichamento_embedding", 10),
            ("rag_fichamento_jev_topk", 1), ("rag_fichamento_jev_topk", 5), ("rag_fichamento_jev_topk", 10),
            ("rag_fichamento_jev_livre", "Não se aplica"),
        ]
        total_q = len(all_questions)
        for m, k in all_cfgs:
            done_m = sum(
                1 for i, q_it in enumerate(all_questions, 1)
                if f"{str(q_it.get('ID_Pergunta') or f'Q{i:03d}').strip()}__{m}__k{k}" in completed_keys
            )
            print(f"  - {m} (k={k}): {done_m}/{total_q} geradas | faltam {total_q - done_m}", flush=True)
        print(f"Resultados salvos em: {RESULTADOS_TESTE_FILE}", flush=True)
        print("=" * 80, flush=True)

    target_cfgs = [
        (m, k)
        for m, k in [
            ("rag_tradicional", 1), ("rag_tradicional", 5), ("rag_tradicional", 10),
            ("rag_fichamento_embedding", 1), ("rag_fichamento_embedding", 5), ("rag_fichamento_embedding", 10),
            ("rag_fichamento_jev_topk", 1), ("rag_fichamento_jev_topk", 5), ("rag_fichamento_jev_topk", 10),
            ("rag_fichamento_jev_livre", "Não se aplica"),
        ]
        if allowed_methods is None or m in allowed_methods
    ]

    pending_tasks = []
    for idx, q_item in enumerate(all_questions, 1):
        q_id = str(q_item.get("ID_Pergunta") or f"Q{idx:03d}").strip()
        c_field = str(q_item.get("Curso") or "").strip()
        classif = str(q_item.get("Classificação") or "única").strip()

        all_done = all(f"{q_id}__{m}__k{k}" in completed_keys for (m, k) in target_cfgs)
        if not all_done:
            pending_tasks.append((idx, q_id, c_field, classif, q_item))

    pending_tasks.sort(key=lambda t: (t[2], t[0]))
    print(f"Perguntas pendentes a processar: {len(pending_tasks)}/{len(all_questions)} (agrupadas por curso, ondas paralelas de 3)", flush=True)

    WAVE_SIZE = 3
    w_start = 0
    while w_start < len(pending_tasks):
        wave = pending_tasks[w_start:w_start + WAVE_SIZE]

        def run_one_question(task_tuple):
            idx, q_id, c_field, classif, q_item = task_tuple
            df_bv, emb_matrix, primary_dir = load_union_bv_for_courses(c_field)
            print(
                f"\n>>> [{idx}/{len(all_questions)}] {q_id} ({classif.upper()} | {c_field} | {len(df_bv)} fatias)\n"
                f"    Pergunta: {str(q_item.get('Pergunta', ''))[:90]}...",
                flush=True
            )
            t0 = time.time()
            rows = run_evaluation_for_question(
                client=gemini_client,
                rag_trad_engine=rag_trad_engine,
                course_name=c_field,
                primary_course_dir=primary_dir,
                df_bv=df_bv,
                emb_matrix=emb_matrix,
                question_row=q_item,
                q_id=q_id,
                completed_keys=completed_keys,
                use_paid_key=use_paid,
                key_id=key_id,
                allowed_methods=allowed_methods,
                defer_judge=defer_judge,
            )
            return task_tuple, rows, time.time() - t0

        wave_need_key_switch = False
        stop_reason = None

        with ThreadPoolExecutor(max_workers=WAVE_SIZE) as wave_exec:
            fut_map = {wave_exec.submit(run_one_question, t): t for t in wave}
            for fut in as_completed(fut_map):
                t_orig = fut_map[fut]
                q_id = t_orig[1]
                try:
                    _, rows, dt = fut.result()
                    if rows:
                        append_result_rows(rows)
                        with _SAVE_LOCK:
                            for r in rows:
                                ek = f"{r['ID_Pergunta']}__{r['metodo_rag']}__k{r['top_k']}"
                                completed_keys.add(ek)
                                if r.get("decisao_julgador") != "PENDENTE_JEV":
                                    judged_checkpoint_keys.add(ek)
                        save_checkpoint(judged_checkpoint_keys)
                        total_new_evaluations += len(rows)
                        decisoes_cnt = {}
                        for r in rows:
                            decisoes_cnt[r["decisao_julgador"]] = decisoes_cnt.get(r["decisao_julgador"], 0) + 1
                        dec_str = ", ".join(f"{k}: {v}" for k, v in decisoes_cnt.items())
                        print(
                            f"    -> [{q_id}] Concluído em {dt:.1f}s | Linhas: {len(rows)} | [{dec_str}] | "
                            f"Gemini Pago: ${_GEMINI_PAID_SPENT_USD:.4f} | OpenRouter: ${_OPENROUTER_SPENT_USD:.4f}",
                            flush=True
                        )
                except (GeminiKeyExhaustedException, RPDLimitExceededError) as gke:
                    print(f"\n[Troca de Chave Gemini - {q_id}] {gke}", flush=True)
                    wave_need_key_switch = True
                except BudgetCapReachedException as bce:
                    stop_reason = f"LIMITE DE ORÇAMENTO ATINGIDO: {bce}"
                except OpenRouterCreditsExhaustedException as oce:
                    stop_reason = f"CRÉDITOS OPENROUTER ESGOTADOS: {oce}"
                except Exception as e:
                    print(f"  [Aviso {q_id}] Erro: {e}", flush=True)

        if stop_reason:
            save_checkpoint(judged_checkpoint_keys)
            print_experiment_summary(stop_reason)
            if shutdown:
                os.system('shutdown /s /t 60 /c "Sinform AI: Execução interrompida por limite/crédito. Desligando em 60s."')
            return

        if wave_need_key_switch:
            if pool_idx + 1 < len(key_pool):
                pool_idx += 1
                key_id, use_paid, gemini_client, rag_trad_engine = init_key_context(pool_idx)
                still_pending = []
                for t_orig in wave:
                    q_id_w = t_orig[1]
                    done_w = all(f"{q_id_w}__{m}__k{k}" in completed_keys for (m, k) in target_cfgs)
                    if not done_w:
                        still_pending.append(t_orig)
                if still_pending:
                    pending_tasks[w_start:w_start + WAVE_SIZE] = still_pending
                    continue
            else:
                save_checkpoint(judged_checkpoint_keys)
                print_experiment_summary("TODAS AS CHAVES GEMINI SELECIONADAS ESGOTADAS")
                if shutdown:
                    os.system('shutdown /s /t 60 /c "Sinform AI: Todas as chaves Gemini esgotadas. Desligando em 60s."')
                return

        w_start += WAVE_SIZE

    print_experiment_summary("EXECUÇÃO SOLICITADA CONCLUÍDA COM SUCESSO")

    if shutdown:
        os.system('shutdown /s /t 60 /c "Sinform AI: Experimento finalizado com sucesso. Desligando em 60s."')


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Executa o benchmark da Etapa 3 de RAGs (200 Perguntas)")
    parser.add_argument("--dataset", type=str, default=None, help="Caminho para a planilha de perguntas")
    parser.add_argument("--max-questions", type=int, default=None)
    parser.add_argument("--use-free-key", action="store_true", default=True, help="Usar chaves gratuitas antes da paga")
    parser.add_argument("--use-paid-key", dest="use_free_key", action="store_false", help="Usar GEMINI_PAGO_RICARDO paga diretamente")
    parser.add_argument("--free-only", action="store_true", default=False, help="Parar ao esgotar as chaves gratuitas sem usar chave paga")
    parser.add_argument("--methods", type=str, default=None, help="Lista separada por vírgula dos métodos a executar")
    parser.add_argument("--defer-judge", action="store_true", default=False, help="Salvar respostas sem chamar JEV Julgador (PENDENTE_JEV)")
    parser.add_argument("--judge-pending", action="store_true", default=False, help="Apenas julgar linhas PENDENTE_JEV existentes")
    parser.add_argument("--shutdown", action="store_true", default=False, help="Desligar o PC ao finalizar ou atingir cota")
    args = parser.parse_args()

    methods_list = [m.strip() for m in args.methods.split(",") if m.strip()] if args.methods else None

    run_stage3_benchmark(
        dataset_path=args.dataset,
        max_questions=args.max_questions,
        use_free_key=args.use_free_key,
        shutdown=args.shutdown,
        methods=methods_list,
        defer_judge=args.defer_judge,
        free_only=args.free_only,
        judge_pending_only=args.judge_pending,
    )
