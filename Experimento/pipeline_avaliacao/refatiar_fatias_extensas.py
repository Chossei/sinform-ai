"""
===============================================================================
REVISÃO E REFATIAMENTO DE FATIAS EXTENSAS (>= 10 PÁGINAS) NO BANCO VETORIAL
===============================================================================
Identifica todas as fatias com >= 10 páginas (ex.: 17p a 136p) nos bancos
vetoriais de todos os cursos (e UFBA - Geral), subdivide cada uma em blocos
lógicos contíguos de NO MÁXIMO 8 páginas (alvo 2 a 6 páginas) via
gemini-3.5-flash-lite, recria os PDFs das sub-fatias, atualiza *_meta.json,
recalcula apenas os embeddings novos e atualiza banco_vetorial.parquet/json/npy.
===============================================================================
"""

import os
import re
import sys
import json
import time
import shutil
import hashlib
import tempfile
import threading
import unicodedata
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import pypdf
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

BASE_DIR = Path(__file__).resolve().parent.parent.parent
EXP_DIR = BASE_DIR / "Experimento"
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(EXP_DIR))

from Experimento.pipeline_avaliacao.config import (
    AREAS_DIR, GERAL_DIR, GEMINI_FREE_KEYS, GEMINI_PAID_KEY,
    PRIMARY_MODEL, EMBEDDING_MODEL, LOGS_DIR,
    COST_PROMPT_TOKEN_FLEX, COST_CANDIDATE_TOKEN_FLEX, COST_EMBEDDING_TOKEN
)
from rate_limiter import get_rate_limiter, RPDLimitExceededError

MAX_SPAN_ALLOWED = 9          # Refatia toda fatia com >= 10 páginas
TARGET_MAX_SUBSLICE = 8       # Limite rígido após refatiamento
WINDOW_PAGES = 32             # Subjanelas máximas enviadas ao Gemini de cada vez
CACHE_REFATIA_FILE = EXP_DIR / "cache_refatiamento_extensas.json"
GLOBAL_CACHE_FILE = EXP_DIR / "cache_fatiamento_global.json"

_LOCK = threading.Lock()
_EXHAUSTED_FREE: set = set()


class SubChunkSpec(BaseModel):
    intervalo_paginas: List[int] = Field(
        description="Array com [página] ou [início, fim] usando a numeração RELATIVA (1..N) deste PDF enviado."
    )
    resumo: str = Field(
        description="Fichamento técnico denso e objetivo (máximo 800 tokens), citando artigos, códigos, ementas, prazos e regras."
    )


class SubSlicingOutput(BaseModel):
    chunks: List[SubChunkSpec] = Field(
        description="Divisão contígua da página 1 até a última página deste trecho, onde CADA bloco tenha de 2 a 6 páginas (MÁXIMO ABSOLUTO de 8 páginas)."
    )


def to_long_path(p: Path) -> Path:
    s = str(p.resolve())
    if os.name == "nt" and not s.startswith("\\\\?\\"):
        return Path("\\\\?\\" + s)
    return Path(s)


def safe_rel_path(p: Path, base: Path = BASE_DIR) -> str:
    s_p = str(p.resolve()).replace("\\\\?\\", "")
    s_base = str(base.resolve()).replace("\\\\?\\", "")
    return os.path.relpath(s_p, s_base).replace("\\", "/")


def compute_file_hash(pdf_path: Path) -> str:
    lp = to_long_path(pdf_path)
    size = lp.stat().st_size
    with open(lp, "rb") as f:
        h = hashlib.md5(f.read(65536)).hexdigest()
    return f"{size}_{h}"


def parse_page_span(pag_str: Any) -> Tuple[int, int, int]:
    nums = [int(x) for x in re.findall(r"\d+", str(pag_str))]
    if not nums:
        return 1, 1, 1
    if len(nums) == 1:
        return nums[0], nums[0], 1
    p1, p2 = nums[0], nums[-1]
    if p2 < p1:
        p1, p2 = p2, p1
    return p1, p2, (p2 - p1 + 1)


def _get_client_pool() -> List[Tuple[str, genai.Client, bool]]:
    pool: List[Tuple[str, genai.Client, bool]] = []
    key_names = ["GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_DRVCHOSSEI"]
    for idx, k in enumerate(GEMINI_FREE_KEYS):
        kname = key_names[idx] if idx < len(key_names) else f"FREE_{idx}"
        if kname not in _EXHAUSTED_FREE:
            pool.append((kname, genai.Client(api_key=k), False))
    if not pool and GEMINI_PAID_KEY:
        pool.append(("GEMINI_PAGO_RICARDO", genai.Client(api_key=GEMINI_PAID_KEY), True))
    return pool


def _call_gemini_structured_slice(pdf_path: Path, n_pages: int, doc_label: str) -> List[Tuple[int, int, str]]:
    """Chama Gemini para dividir um trecho PDF de `n_pages` páginas em blocos <= TARGET_MAX_SUBSLICE."""
    prompt = (
        f"Você está refatiando um trecho extenso ({n_pages} páginas) do documento oficial '{doc_label}' (UFBA).\n"
        f"Divida TODAS as páginas deste PDF anexo, da página 1 até a página {n_pages}, sem saltos e sem sobreposições.\n"
        f"REGRAS OBRIGATÓRIAS:\n"
        f"1. CADA bloco DEVE ter entre 2 e 6 páginas (MÁXIMO ABSOLUTO DE {TARGET_MAX_SUBSLICE} PÁGINAS por bloco).\n"
        f"   Mesmo que o trecho seja um anexo contínuo de ementas, grades ou tabelas, QUEBRE-O em blocos lógicos menores (ex.: grupos de disciplinas, capítulos, seções) respeitando o limite máximo de {TARGET_MAX_SUBSLICE} páginas.\n"
        f"2. Use a numeração relativa das páginas do PDF anexo (1 até {n_pages}).\n"
        f"3. Para cada bloco, elabore um FICHAMENTO TÉCNICO denso e detalhado (até 800 tokens), citando códigos de componentes, artigos, pré-requisitos, cargas horárias, regras e prazos presentes naquelas páginas.\n"
        f"Retorne estritamente o JSON conforme o schema."
    )

    clean_stem = "".join(c for c in unicodedata.normalize("NFKD", pdf_path.stem) if not unicodedata.combining(c))
    last_err = "sem resposta"

    for attempt in range(1, 9):
        pool = _get_client_pool()
        if not pool:
            raise RuntimeError(f"Nenhuma chave Gemini disponível para refatiamento ({last_err})")
        key_id, client, is_paid = pool[(attempt - 1) % len(pool)]
        limiter = get_rate_limiter(PRIMARY_MODEL, key_id=key_id)
        tmp_path = Path(tempfile.gettempdir()) / f"reslice_{threading.get_ident()}_{attempt}_{re.sub(r'[^a-zA-Z0-9_.-]', '_', clean_stem)[:30]}.pdf"
        uploaded = None
        try:
            shutil.copy2(to_long_path(pdf_path), tmp_path)
            limiter.acquire()
            uploaded = client.files.upload(file=str(tmp_path))
            time.sleep(1.0)
            cfg: Dict[str, Any] = {
                "response_mime_type": "application/json",
                "response_schema": SubSlicingOutput,
                "temperature": 0.1,
                "max_output_tokens": 32768,
            }
            if is_paid:
                cfg["service_tier"] = "flex"
            resp = client.models.generate_content(
                model=PRIMARY_MODEL,
                contents=[uploaded, prompt],
                config=types.GenerateContentConfig(**cfg),
            )
            parsed = SubSlicingOutput.model_validate_json(resp.text)
            raw_items: List[Tuple[int, int, str]] = []
            for ch in parsed.chunks:
                ivs = sorted([max(1, min(n_pages, int(x))) for x in (ch.intervalo_paginas or [1])])
                s_p = ivs[0]
                e_p = ivs[-1]
                raw_items.append((s_p, e_p, ch.resumo.strip()))
            if not raw_items:
                raise RuntimeError("Lista de chunks vazia.")
            return _normalize_intervals(raw_items, n_pages)
        except RPDLimitExceededError:
            if not is_paid:
                with _LOCK:
                    _EXHAUSTED_FREE.add(key_id)
        except Exception as e:
            last_err = str(e)
            if ("429" in last_err or "RESOURCE_EXHAUSTED" in last_err) and not is_paid:
                if "perday" in last_err.lower() or "per_day" in last_err.lower() or "daily" in last_err.lower():
                    with _LOCK:
                        _EXHAUSTED_FREE.add(key_id)
                else:
                    time.sleep(min(20.0, 4.0 * attempt))
            else:
                time.sleep(min(10.0, 2.0 * attempt))
        finally:
            if uploaded is not None:
                try:
                    client.files.delete(name=uploaded.name)
                except Exception:
                    pass
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass

    raise RuntimeError(f"Falha ao refatiar {doc_label}: {last_err}")


def _call_gemini_summarize_small_pdf(pdf_path: Path, abs_s: int, abs_e: int, doc_label: str) -> str:
    """Gera fichamento técnico único para um sub-bloco determinístico <= 6 páginas."""
    prompt = (
        f"Elabore um FICHAMENTO TÉCNICO denso, objetivo e detalhado (máximo 800 tokens) das páginas {abs_s} a {abs_e} "
        f"do documento oficial '{doc_label}' (UFBA) em anexo.\n"
        f"Cite códigos de componentes curriculares, nomes de disciplinas, artigos, parágrafos, requisitos, prazos e tabelas presentes nestas páginas. "
        f"Responda apenas com o fichamento técnico."
    )
    clean_stem = "".join(c for c in unicodedata.normalize("NFKD", pdf_path.stem) if not unicodedata.combining(c))
    last_err = "sem resposta"
    for attempt in range(1, 8):
        pool = _get_client_pool()
        if not pool:
            raise RuntimeError(f"Sem chaves Gemini para resumir {doc_label}")
        key_id, client, is_paid = pool[(attempt - 1) % len(pool)]
        limiter = get_rate_limiter(PRIMARY_MODEL, key_id=key_id)
        tmp_path = Path(tempfile.gettempdir()) / f"subsum_{threading.get_ident()}_{attempt}_{re.sub(r'[^a-zA-Z0-9_.-]', '_', clean_stem)[:30]}.pdf"
        uploaded = None
        try:
            shutil.copy2(to_long_path(pdf_path), tmp_path)
            limiter.acquire()
            uploaded = client.files.upload(file=str(tmp_path))
            time.sleep(0.8)
            cfg: Dict[str, Any] = {"temperature": 0.15, "max_output_tokens": 2048}
            if is_paid:
                cfg["service_tier"] = "flex"
            resp = client.models.generate_content(
                model=PRIMARY_MODEL,
                contents=[uploaded, prompt],
                config=types.GenerateContentConfig(**cfg),
            )
            txt = (getattr(resp, "text", None) or "").strip()
            if txt:
                return txt
            raise RuntimeError("Resumo vazio")
        except RPDLimitExceededError:
            if not is_paid:
                with _LOCK:
                    _EXHAUSTED_FREE.add(key_id)
        except Exception as e:
            last_err = str(e)
            time.sleep(min(12.0, 2.0 * attempt))
        finally:
            if uploaded is not None:
                try:
                    client.files.delete(name=uploaded.name)
                except Exception:
                    pass
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
    return f"Trecho técnico das páginas {abs_s} a {abs_e} do documento {doc_label}."


def _normalize_intervals(items: List[Tuple[int, int, str]], n_pages: int) -> List[Tuple[int, int, str]]:
    """Garante cobertura contígua e sem sobreposição de 1 até n_pages."""
    items_sorted = sorted(items, key=lambda x: (x[0], x[1]))
    fixed: List[Tuple[int, int, str]] = []
    cursor = 1
    for s_p, e_p, res in items_sorted:
        if cursor > n_pages:
            break
        s_adj = max(cursor, s_p)
        if s_adj > cursor:
            # preencher lacuna no chunk anterior se couber, ou criar faixa
            if fixed and (s_adj - fixed[-1][0]) <= TARGET_MAX_SUBSLICE:
                ps, _, pr = fixed[-1]
                fixed[-1] = (ps, s_adj - 1, pr)
            else:
                fixed.append((cursor, s_adj - 1, res))
        e_adj = min(n_pages, max(s_adj, e_p))
        fixed.append((s_adj, e_adj, res))
        cursor = e_adj + 1
    if cursor <= n_pages:
        last_res = items_sorted[-1][2] if items_sorted else ""
        if fixed and (n_pages - fixed[-1][0] + 1) <= TARGET_MAX_SUBSLICE:
            ps, _, pr = fixed[-1]
            fixed[-1] = (ps, n_pages, pr)
        else:
            fixed.append((cursor, n_pages, last_res))
    return fixed


def reslice_large_range(orig_pdf: Path, abs_start: int, abs_end: int, doc_label: str) -> List[Tuple[int, int, str]]:
    """Refatia [abs_start, abs_end] garantindo todos os sub-blocos com span <= TARGET_MAX_SUBSLICE."""
    reader = pypdf.PdfReader(str(to_long_path(orig_pdf)))
    total_pdf_pages = len(reader.pages)
    abs_start = max(1, min(abs_start, total_pdf_pages))
    abs_end = max(abs_start, min(abs_end, total_pdf_pages))

    all_abs_chunks: List[Tuple[int, int, str]] = []

    for win_s in range(abs_start, abs_end + 1, WINDOW_PAGES):
        win_e = min(abs_end, win_s + WINDOW_PAGES - 1)
        win_n = win_e - win_s + 1
        win_pdf = Path(tempfile.gettempdir()) / f"win_{threading.get_ident()}_{win_s}_{win_e}.pdf"
        w = pypdf.PdfWriter()
        for pi in range(win_s - 1, win_e):
            w.add_page(reader.pages[pi])
        with open(win_pdf, "wb") as f:
            w.write(f)
        try:
            if win_n <= TARGET_MAX_SUBSLICE:
                res_txt = _call_gemini_summarize_small_pdf(win_pdf, win_s, win_e, doc_label)
                all_abs_chunks.append((win_s, win_e, res_txt))
            else:
                rel_chunks = _call_gemini_structured_slice(win_pdf, win_n, f"{doc_label} (págs. {win_s}-{win_e})")
                for rs, re_p, r_txt in rel_chunks:
                    a_s = win_s + rs - 1
                    a_e = win_s + re_p - 1
                    if (a_e - a_s + 1) <= TARGET_MAX_SUBSLICE:
                        all_abs_chunks.append((a_s, a_e, r_txt))
                    else:
                        # Fallback rígido caso Gemini ainda retorne bloco > 8p (ex.: muitas páginas de tabela)
                        for sub_s in range(a_s, a_e + 1, 6):
                            sub_e = min(a_e, sub_s + 5)
                            sub_pdf = Path(tempfile.gettempdir()) / f"subdet_{threading.get_ident()}_{sub_s}_{sub_e}.pdf"
                            sw = pypdf.PdfWriter()
                            for spi in range(sub_s - 1, sub_e):
                                sw.add_page(reader.pages[spi])
                            with open(sub_pdf, "wb") as sf:
                                sw.write(sf)
                            try:
                                sub_txt = _call_gemini_summarize_small_pdf(sub_pdf, sub_s, sub_e, doc_label)
                                all_abs_chunks.append((sub_s, sub_e, sub_txt))
                            finally:
                                sub_pdf.unlink(missing_ok=True)
        finally:
            win_pdf.unlink(missing_ok=True)

    return all_abs_chunks


def generate_embeddings_for_texts(texts: List[str]) -> np.ndarray:
    """Calcula embeddings via gemini-embedding-2 usando chaves gratuitas e fallback pago."""
    if not texts:
        return np.zeros((0, 3072), dtype=np.float32)
    out: List[List[float]] = []
    batch_size = 50
    for b_start in range(0, len(texts), batch_size):
        batch = texts[b_start:b_start + batch_size]
        ok = False
        last_err = ""
        for attempt in range(1, 9):
            pool = _get_client_pool()
            key_id, client, is_paid = pool[(attempt - 1) % len(pool)]
            limiter = get_rate_limiter(EMBEDDING_MODEL, key_id=key_id)
            try:
                limiter.acquire()
                payload = [types.Content(parts=[types.Part.from_text(text=t if t.strip() else " ")]) for t in batch]
                res = client.models.embed_content(model=EMBEDDING_MODEL, contents=payload)
                if hasattr(res, "embeddings") and res.embeddings:
                    for eobj in res.embeddings:
                        out.append(list(eobj.values))
                elif hasattr(res, "embedding") and res.embedding:
                    out.append(list(res.embedding.values))
                ok = True
                break
            except RPDLimitExceededError:
                if not is_paid:
                    with _LOCK:
                        _EXHAUSTED_FREE.add(key_id)
            except Exception as e:
                last_err = str(e)
                time.sleep(min(20.0, 3.0 * attempt))
        if not ok:
            raise RuntimeError(f"Embedding falhou: {last_err}")
    return np.array(out, dtype=np.float32)


def run_reslicing():
    cache_data: Dict[str, Any] = {}
    if CACHE_REFATIA_FILE.exists():
        try:
            with open(to_long_path(CACHE_REFATIA_FILE), "r", encoding="utf-8") as f:
                cache_data = json.load(f)
        except Exception:
            cache_data = {}

    # 1. Mapear todos os bancos vetoriais e coletar blocos únicos >= 10p
    course_dirs: List[Path] = []
    for area in sorted(AREAS_DIR.iterdir()):
        if not area.is_dir():
            continue
        if area.name == "UFBA - Geral":
            course_dirs.append(area)
        else:
            for c in sorted(area.iterdir()):
                if c.is_dir():
                    course_dirs.append(c)

    unique_tasks: Dict[str, Tuple[Path, str, int, int, str]] = {}
    affected_courses: List[Path] = []

    for c_dir in course_dirs:
        pq = c_dir / "banco vetorial" / "banco_vetorial.parquet"
        if not to_long_path(pq).exists():
            continue
        df_bv = pd.read_parquet(to_long_path(pq))
        has_big = False
        for _, r in df_bv.iterrows():
            p1, p2, span = parse_page_span(r["páginas"])
            if span > MAX_SPAN_ALLOWED:
                has_big = True
                doc = str(r["nome do documento"])
                orig_pdf = c_dir / f"{doc}.pdf"
                if not to_long_path(orig_pdf).exists():
                    continue
                fh = compute_file_hash(orig_pdf)
                ckey = f"{fh}::{p1}-{p2}"
                if ckey not in cache_data and ckey not in unique_tasks:
                    unique_tasks[ckey] = (orig_pdf, doc, p1, p2, ckey)
        if has_big:
            affected_courses.append(c_dir)

    print(f"[Refatiamento] Cursos afetados: {len(affected_courses)} | Blocos únicos a refatiar no Gemini: {len(unique_tasks)} (em cache: {len(cache_data)})", flush=True)

    # 2. Executar refatiamento dos blocos únicos faltantes em paralelo (3 workers = 3 chaves gratuitas)
    if unique_tasks:
        tasks_list = list(unique_tasks.values())
        done_cnt = 0

        def _worker(t):
            orig_pdf, doc, p1, p2, ckey = t
            sub_chunks = reslice_large_range(orig_pdf, p1, p2, doc)
            return ckey, sub_chunks, doc, p1, p2

        with ThreadPoolExecutor(max_workers=4) as executor:
            futs = [executor.submit(_worker, t) for t in tasks_list]
            for f in as_completed(futs):
                ckey, sub_chunks, doc, p1, p2 = f.result()
                done_cnt += 1
                with _LOCK:
                    cache_data[ckey] = [
                        {"p_start": s, "p_end": e, "resumo": txt}
                        for (s, e, txt) in sub_chunks
                    ]
                    with open(to_long_path(CACHE_REFATIA_FILE), "w", encoding="utf-8") as cf:
                        json.dump(cache_data, cf, ensure_ascii=False, indent=2)
                max_new = max((e - s + 1) for s, e, _ in sub_chunks)
                print(f"  [{done_cnt}/{len(tasks_list)}] {doc} [{p1}-{p2}] ({p2-p1+1}p) -> {len(sub_chunks)} sub-fatias (max={max_new}p)", flush=True)

    # 3. Atualizar cada curso afetado (PDFs físicos, _meta.json, parquet, json, embeddings.npy)
    print(f"\n[Atualização Local] Reconstruindo bancos vetoriais de {len(affected_courses)} cursos...", flush=True)
    for idx_c, c_dir in enumerate(affected_courses, 1):
        bv_dir = c_dir / "banco vetorial"
        pq_path = bv_dir / "banco_vetorial.parquet"
        npy_path = bv_dir / "embeddings.npy"

        df_old = pd.read_parquet(to_long_path(pq_path))
        emb_old = np.load(to_long_path(npy_path))
        old_emb_map: Dict[str, np.ndarray] = {}
        for i_r, rr in df_old.iterrows():
            if i_r < len(emb_old):
                old_emb_map[str(rr["fichamento/resumo"])] = emb_old[i_r]

        new_rows: List[Dict[str, Any]] = []
        changed_docs: set = set()
        doc_counters: Dict[str, int] = {}

        for _, rr in df_old.iterrows():
            doc = str(rr["nome do documento"])
            p1, p2, span = parse_page_span(rr["páginas"])
            orig_pdf = c_dir / f"{doc}.pdf"
            if span > MAX_SPAN_ALLOWED and to_long_path(orig_pdf).exists():
                fh = compute_file_hash(orig_pdf)
                ckey = f"{fh}::{p1}-{p2}"
                sub_list = cache_data.get(ckey)
                if sub_list:
                    changed_docs.add(doc)
                    # Remover fatia antiga gigante do disco
                    old_chunk_p = BASE_DIR / str(rr["pdf_chunk_path"])
                    if not to_long_path(old_chunk_p).exists():
                        old_chunk_p = c_dir / doc / Path(str(rr["pdf_chunk_path"])).name
                    try:
                        to_long_path(old_chunk_p).unlink(missing_ok=True)
                    except Exception:
                        pass

                    reader = pypdf.PdfReader(str(to_long_path(orig_pdf)))
                    n_total = len(reader.pages)
                    slices_dir = c_dir / doc
                    to_long_path(slices_dir).mkdir(parents=True, exist_ok=True)

                    for sub in sub_list:
                        s_p = max(1, min(int(sub["p_start"]), n_total))
                        e_p = max(s_p, min(int(sub["p_end"]), n_total))
                        res_txt = str(sub["resumo"]).strip()
                        doc_counters[doc] = doc_counters.get(doc, 0) + 1
                        ch_filename = f"{doc}_paginas_{s_p}-{e_p}.pdf"
                        ch_path = slices_dir / ch_filename
                        if not to_long_path(ch_path).exists():
                            w = pypdf.PdfWriter()
                            for pi in range(s_p - 1, e_p):
                                w.add_page(reader.pages[pi])
                            with open(to_long_path(ch_path), "wb") as pf:
                                w.write(pf)
                        new_rows.append({
                            "chunk_id": f"{doc}_{doc_counters[doc]:03d}",
                            "nome do documento": doc,
                            "páginas": f"[{s_p}, {e_p}]" if s_p != e_p else f"[{s_p}]",
                            "fichamento/resumo": res_txt,
                            "pdf_chunk_path": safe_rel_path(ch_path, BASE_DIR),
                            "curso": rr.get("curso", c_dir.name),
                            "link para acessar o documento": rr.get("link para acessar o documento", "https://ufba.br"),
                            "quantidade de tokens": len(res_txt.split()) * 2,
                        })
                    continue

            doc_counters[doc] = doc_counters.get(doc, 0) + 1
            row_dict = {k: rr[k] for k in df_old.columns if k != "embedding"}
            row_dict["chunk_id"] = f"{doc}_{doc_counters[doc]:03d}"
            new_rows.append(row_dict)

        df_new = pd.DataFrame(new_rows)
        df_new.drop_duplicates(subset=["chunk_id"], inplace=True)
        df_new.reset_index(drop=True, inplace=True)

        # Atualizar *_meta.json dos documentos modificados
        for ch_doc in changed_docs:
            doc_rows = df_new[df_new["nome do documento"] == ch_doc].to_dict(orient="records")
            meta_p = c_dir / ch_doc / f"{ch_doc}_meta.json"
            to_long_path(meta_p.parent).mkdir(parents=True, exist_ok=True)
            with open(to_long_path(meta_p), "w", encoding="utf-8") as mf:
                json.dump(doc_rows, mf, ensure_ascii=False, indent=2)

        # Recalcular apenas embeddings dos resumos novos
        resumos = df_new["fichamento/resumo"].astype(str).tolist()
        missing_idxs = [i for i, txt in enumerate(resumos) if txt not in old_emb_map]
        if missing_idxs:
            new_embs = generate_embeddings_for_texts([resumos[i] for i in missing_idxs])
            for j, orig_i in enumerate(missing_idxs):
                old_emb_map[resumos[orig_i]] = new_embs[j]

        emb_matrix = np.array([old_emb_map[txt] for txt in resumos], dtype=np.float32)
        if "embedding" in df_old.columns:
            df_new["embedding"] = [list(e) for e in emb_matrix]

        np.save(to_long_path(npy_path), emb_matrix)
        df_new.to_parquet(to_long_path(pq_path), index=False)
        df_json = df_new.drop(columns=["embedding"], errors="ignore")
        df_json.to_json(to_long_path(bv_dir / "banco_vetorial.json"), orient="records", force_ascii=False, indent=2)

        max_after = max(parse_page_span(p)[2] for p in df_new["páginas"])
        print(f"  [{idx_c}/{len(affected_courses)}] {c_dir.name}: {len(df_old)} -> {len(df_new)} fatias (novos embs={len(missing_idxs)}, max_span={max_after}p)", flush=True)

    print("\n[Refatiamento CONCLUÍDO COM SUCESSO!]")


if __name__ == "__main__":
    run_reslicing()

