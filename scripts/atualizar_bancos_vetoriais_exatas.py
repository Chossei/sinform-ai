"""
Atualização e Correção Completa dos Bancos Vetoriais - Ciências Exatas e da Terra
Sinform AI - Pipeline de Avaliação UFBA
"""

import os
import sys
import json
import time
import shutil
import hashlib
import tempfile
import unicodedata
from pathlib import Path
from typing import List, Dict, Any, Optional

import pypdf
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from google import genai
from google.genai import types

BASE_DIR = Path(__file__).resolve().parent.parent
EXP_DIR = BASE_DIR / "Experimento"
AREAS_DIR = EXP_DIR / "Áreas do conhecimento"
EXATAS_DIR = AREAS_DIR / "Ciências Exatas e da Terra"
CACHE_FILE = EXP_DIR / "cache_fatiamento_global.json"

load_dotenv(BASE_DIR / ".env")
load_dotenv(EXP_DIR / "chave2.env")

KEY_FREE_1 = os.getenv("GEMINI_API_KEY")
KEY_FREE_2 = os.getenv("GEMINI_API_KEY_2")
KEY_PAID = os.getenv("GEMINI_PAGO_RICARDO")

PRIMARY_MODEL = "gemini-3.5-flash-lite"
FALLBACK_MODEL = "gemini-3.1-flash-lite"
EMBEDDING_MODEL = "models/gemini-embedding-2"

PRE_LLM_SLICING_PROMPT = """Você é um especialista em estruturação de documentos normativos e acadêmicos universitários (UFBA).
Sua missão é analisar visual e textualmente este documento oficial e dividi-lo em blocos lógicos contíguos e sequenciais (chunks).

DIRETRIZES DE FATIAMENTO:
1. Analise a densidade de conteúdo, tabelas, seções normativas e quebras de tópicos.
2. Defina os intervalos de páginas de forma que cada bloco contenha uma unidade de sentido completa (ex: um capítulo, uma resolução específica, uma tabela de pontuação).
3. Cubra absolutamente TODAS as páginas do documento, da página 1 até a última, sem saltos e sem sobreposições.
4. Para cada intervalo, elabore um FICHAMENTO TÉCNICO, objetivo, denso e detalhado (máximo 800 tokens):
   - Cite artigos, parágrafos, incisos, números de resoluções e datas.
   - Detalhe requisitos, prazos, fluxos processuais, percentuais e critérios de deferimento/indeferimento.
   - Seja conciso e exato. Evite introduções vazias.

Retorne estritamente o JSON estruturado conforme o esquema especificado.
"""


def to_long_path(p: Path) -> Path:
    s = str(p.resolve())
    if os.name == "nt" and not s.startswith("\\\\?\\"):
        return Path("\\\\?\\" + s)
    return Path(s)


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


def compute_hash(path: Path) -> str:
    with open(to_long_path(path), "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            with open(to_long_path(CACHE_FILE), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_cache(cache: dict):
    with open(to_long_path(CACHE_FILE), "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def get_gemini_client():
    for k in [KEY_FREE_1, KEY_FREE_2, KEY_PAID]:
        if k:
            return genai.Client(api_key=k)
    raise ValueError("Nenhuma chave Gemini disponível!")


def slice_pdf_with_gemini(pdf_path: Path, client: genai.Client) -> Optional[List[Dict[str, Any]]]:
    clean_stem = "".join(c for c in unicodedata.normalize("NFKD", pdf_path.stem) if not unicodedata.combining(c))
    safe_ascii_name = f"slice_{int(time.time()*1000)%100000}_{clean_stem}.pdf"
    tmp_file = Path(tempfile.gettempdir()) / safe_ascii_name
    shutil.copy2(to_long_path(pdf_path), to_long_path(tmp_file))

    for attempt in range(1, 4):
        uploaded = None
        try:
            uploaded = client.files.upload(file=str(tmp_file))
            time.sleep(1.5)

            for model_name in [PRIMARY_MODEL, FALLBACK_MODEL]:
                try:
                    res = client.models.generate_content(
                        model=model_name,
                        contents=[uploaded, PRE_LLM_SLICING_PROMPT],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=DocumentSlicingOutput,
                            temperature=0.1
                        )
                    )
                    parsed = DocumentSlicingOutput.model_validate_json(res.text)
                    chunks = [c.model_dump() for c in parsed.chunks]
                    return chunks
                except Exception as me:
                    if "429" in str(me) or "RESOURCE_EXHAUSTED" in str(me):
                        time.sleep(5.0 * attempt)
                        continue
                    raise me
        except Exception as e:
            print(f"    [Tentativa {attempt}/3] Erro ao fatiar {pdf_path.name}: {e}", flush=True)
            time.sleep(3.0 * attempt)
        finally:
            if uploaded:
                try:
                    client.files.delete(name=uploaded.name)
                except Exception:
                    pass

    if tmp_file.exists():
        try:
            tmp_file.unlink()
        except Exception:
            pass
    return None


def generate_embeddings_batch(texts: List[str], client: genai.Client) -> np.ndarray:
    vectors = []
    for idx, txt in enumerate(texts):
        content = txt.strip() if txt.strip() else "Documento normativo institucional UFBA."
        for attempt in range(1, 4):
            try:
                res = client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=content,
                )
                if res.embeddings:
                    vectors.append(res.embeddings[0].values)
                break
            except Exception as e:
                print(f"    [Aviso Embedding item {idx+1}/{len(texts)} - Tentativa {attempt}/3]: {e}", flush=True)
                time.sleep(2.0 * attempt)
        time.sleep(0.3)

    if len(vectors) != len(texts):
        raise RuntimeError(f"Esperado {len(texts)} embeddings, gerado {len(vectors)}")
    return np.array(vectors, dtype=np.float32)


def process_course_missing_pdfs(course_dir: Path, client: genai.Client, cache: dict):
    course_name = course_dir.name
    bv_dir = course_dir / "banco vetorial"
    parquet_path = bv_dir / "banco_vetorial.parquet"
    json_path = bv_dir / "banco_vetorial.json"
    npy_path = bv_dir / "embeddings.npy"

    df_bv = pd.read_parquet(to_long_path(parquet_path)) if to_long_path(parquet_path).exists() else pd.DataFrame()
    emb_matrix = np.load(to_long_path(npy_path)) if to_long_path(npy_path).exists() else np.empty((0, 3072), dtype=np.float32)
    existing_docs = set(df_bv["nome do documento"].unique()) if not df_bv.empty else set()

    root_pdfs = [p for p in course_dir.glob("*.pdf")]
    missing_pdfs = []
    for p in root_pdfs:
        doc_stem = p.stem
        if not any(doc_stem.lower() in d.lower() or d.lower() in doc_stem.lower() for d in existing_docs):
            missing_pdfs.append(p)

    if not missing_pdfs:
        print(f"[{course_name}] Todos os {len(root_pdfs)} PDFs já constam no BV. Pulando.", flush=True)
        return

    print(f"\n{'='*75}\nProcessando Curso: {course_name} ({len(missing_pdfs)} PDFs faltando no BV)\n{'='*75}", flush=True)

    new_chunks_records = []
    new_summaries = []

    for pdf in missing_pdfs:
        doc_stem = pdf.stem
        pdf_hash = compute_hash(pdf)
        cache_key_hash = f"hash:{pdf_hash}"
        cache_key_name = f"name:{doc_stem}"

        print(f"  -> Processando: {pdf.name}...", flush=True)
        chunks_specs = None

        if cache_key_hash in cache:
            print("     [Cache Hit por Hash]", flush=True)
            chunks_specs = cache[cache_key_hash].get("chunks")
        elif cache_key_name in cache:
            print("     [Cache Hit por Nome]", flush=True)
            chunks_specs = cache[cache_key_name].get("chunks")

        if not chunks_specs:
            print("     [Fatiando via Pré-LLM Gemini]...", flush=True)
            chunks_specs = slice_pdf_with_gemini(pdf, client)
            if not chunks_specs:
                print(f"     [ERRO] Falha ao fatiar {pdf.name}. Pulando documento.", flush=True)
                continue
            cache[cache_key_hash] = {"chunks": chunks_specs}
            cache[cache_key_name] = {"chunks": chunks_specs}
            save_cache(cache)

        # Fatiamento Físico com pypdf suportando Windows Long Paths
        reader = pypdf.PdfReader(str(to_long_path(pdf)))
        total_pages = len(reader.pages)
        slices_dir = course_dir / doc_stem
        to_long_path(slices_dir).mkdir(parents=True, exist_ok=True)

        for idx, chunk in enumerate(chunks_specs, 1):
            interval = chunk.get("intervalo_paginas") or chunk.get("páginas") or chunk.get("paginas")
            if isinstance(interval, str):
                try:
                    interval = json.loads(interval)
                except Exception:
                    interval = [1, total_pages]

            resumo = chunk.get("fichamento/resumo") or chunk.get("resumo") or ""
            if not resumo.strip():
                resumo = f"Documento normativo: {doc_stem}."

            if len(interval) == 1:
                p_start, p_end = interval[0], interval[0]
            elif len(interval) >= 2:
                p_start, p_end = interval[0], interval[1]
            else:
                p_start, p_end = 1, total_pages

            p_start = max(1, min(p_start, total_pages))
            p_end = max(p_start, min(p_end, total_pages))

            writer = pypdf.PdfWriter()
            for p_num in range(p_start - 1, p_end):
                writer.add_page(reader.pages[p_num])

            chunk_filename = f"{doc_stem}_paginas_{p_start}-{p_end}.pdf"
            chunk_file_path = slices_dir / chunk_filename
            with open(to_long_path(chunk_file_path), "wb") as f_out:
                writer.write(f_out)

            rel_path = os.path.relpath(str(chunk_file_path.resolve()), str(BASE_DIR.resolve())).replace("\\", "/")
            paginas_repr = f"[{p_start}, {p_end}]" if p_start != p_end else f"[{p_start}]"

            record = {
                "chunk_id": f"{doc_stem}_{idx:03d}",
                "curso": course_name,
                "nome do documento": doc_stem,
                "link para acessar o documento": "https://ufba.br",
                "páginas": paginas_repr,
                "fichamento/resumo": resumo,
                "quantidade de tokens": len(resumo.split()) * 2,
                "pdf_chunk_path": rel_path
            }
            new_chunks_records.append(record)
            new_summaries.append(resumo)

        print(f"     [OK] {len(chunks_specs)} fatias físicas geradas em {slices_dir.name}/", flush=True)

    if new_chunks_records:
        print(f"  -> Gerando embeddings para {len(new_chunks_records)} novas fatias...", flush=True)
        new_embeddings = generate_embeddings_batch(new_summaries, client)

        df_new = pd.DataFrame(new_chunks_records)
        if not df_bv.empty:
            df_updated = pd.concat([df_bv, df_new], ignore_index=True)
            if emb_matrix.shape[0] > 0:
                updated_embeddings = np.vstack([emb_matrix, new_embeddings])
            else:
                updated_embeddings = new_embeddings
        else:
            df_updated = df_new
            updated_embeddings = new_embeddings

        df_updated.drop_duplicates(subset=["nome do documento", "páginas"], inplace=True)
        to_long_path(bv_dir).mkdir(parents=True, exist_ok=True)
        df_updated.to_parquet(to_long_path(parquet_path), index=False)
        df_updated.to_json(to_long_path(json_path), orient="records", force_ascii=False, indent=2)
        np.save(to_long_path(npy_path), updated_embeddings)

        print(f"  [CONCLUÍDO] Banco vetorial de {course_name} atualizado: {len(df_updated)} fatias e embeddings salvos!", flush=True)


def main():
    print("=" * 80, flush=True)
    print("INICIANDO ATUALIZAÇÃO DOS BANCOS VETORIAIS (CIÊNCIAS EXATAS E DA TERRA)", flush=True)
    print("=" * 80, flush=True)

    client = get_gemini_client()
    cache = load_cache()

    course_folders = sorted([d for d in EXATAS_DIR.iterdir() if d.is_dir()], key=lambda x: x.name)
    print(f"Total de cursos encontrados: {len(course_folders)}", flush=True)

    for c in course_folders:
        try:
            process_course_missing_pdfs(c, client, cache)
        except Exception as e:
            print(f"[ERRO NO CURSO {c.name}]: {e}", flush=True)

    print("\n" + "=" * 80, flush=True)
    print("TODOS OS BANCOS VETORIAIS DE CIÊNCIAS EXATAS FORAM ATUALIZADOS COM SUCESSO!", flush=True)
    print("=" * 80, flush=True)


if __name__ == "__main__":
    main()
