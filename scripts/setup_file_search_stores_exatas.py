"""
Script de Criação e Indexação das FileSearchStores (RAG Tradicional)
Para os Cursos de Ciências Exatas e da Terra - Sinform AI UFBA
"""

import os
import sys
import json
import time
import re
import shutil
import tempfile
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

BASE_DIR = Path(__file__).resolve().parent.parent
EXP_DIR = BASE_DIR / "Experimento"
EXATAS_DIR = EXP_DIR / "Áreas do conhecimento" / "Ciências Exatas e da Terra"
STORES_FILE = BASE_DIR / "google_file_search_stores.json"

load_dotenv(BASE_DIR / ".env")
load_dotenv(EXP_DIR / "chave2.env")

API_KEY = os.getenv("GEMINI_PAGO_RICARDO") or os.getenv("GEMINI_API_KEY_2") or os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)


def to_ascii(text: str) -> str:
    norm = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    return norm


def slugify(text: str) -> str:
    norm = to_ascii(text)
    slug = re.sub(r"[^\w]+", "-", norm).strip("-").lower()
    return slug[:40]


def load_stores_mapping() -> dict:
    if STORES_FILE.exists():
        try:
            with open(STORES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_stores_mapping(mapping: dict):
    with open(STORES_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)


def setup_course_store(course_name: str, course_dir: Path, mapping: dict):
    store_name = mapping.get(course_name)
    store = None

    if store_name:
        try:
            store = client.file_search_stores.get(name=store_name)
            print(f"[{course_name}] Store existente validada: {store.name}", flush=True)
        except Exception:
            store = None

    if not store:
        slug = slugify(course_name)
        display_name = f"sinform-ufba-{slug}"
        try:
            existing = list(client.file_search_stores.list())
            for s in existing:
                if s.display_name == display_name:
                    print(f"[{course_name}] Reutilizando store existente por display_name: {s.name}", flush=True)
                    store = s
                    mapping[course_name] = s.name
                    save_stores_mapping(mapping)
                    break
        except Exception:
            pass

    if not store:
        slug = slugify(course_name)
        display_name = f"sinform-ufba-{slug}"
        print(f"[{course_name}] Criando FileSearchStore '{display_name}'...", flush=True)
        store = client.file_search_stores.create(
            config=types.CreateFileSearchStoreConfig(
                display_name=display_name,
                embedding_model="models/gemini-embedding-2"
            )
        )
        mapping[course_name] = store.name
        save_stores_mapping(mapping)

    store_name = store.name

    # Verificar quais documentos já estão na store
    try:
        existing_files = list(client.file_search_stores.list_files(file_search_store_name=store_name))
        indexed_names = {to_ascii(f.display_name or "").lower() for f in existing_files}
    except Exception:
        indexed_names = set()

    pdf_files = list(course_dir.glob("*.pdf"))
    to_upload = [p for p in pdf_files if to_ascii(p.name).lower() not in indexed_names]

    if not to_upload:
        print(f"[{course_name}] Todos os {len(pdf_files)} PDFs já indexados na store.", flush=True)
        return store_name

    print(f"[{course_name}] Enviando {len(to_upload)} PDFs pendentes para {store_name}...", flush=True)

    def upload_one_pdf(pdf_item):
        idx, pdf = pdf_item
        doc_name = pdf.name
        safe_name = to_ascii(doc_name)
        tmp_ascii = Path(tempfile.gettempdir()) / f"fss_{int(time.time()*1000)%100000}_{idx}_{safe_name}"
        shutil.copy2(pdf, tmp_ascii)
        try:
            for attempt in range(1, 4):
                try:
                    op = client.file_search_stores.upload_to_file_search_store(
                        file_search_store_name=store_name,
                        file=str(tmp_ascii),
                        config=types.UploadToFileSearchStoreConfig(
                            display_name=safe_name,
                            custom_metadata=[
                                types.CustomMetadata(key="curso", string_value=to_ascii(course_name)),
                                types.CustomMetadata(key="documento", string_value=safe_name)
                            ]
                        )
                    )
                    while not op.done:
                        time.sleep(2)
                        op = client.operations.get(op)
                    print(f"   [{idx}/{len(to_upload)}] OK: {safe_name}", flush=True)
                    return True
                except Exception as e:
                    print(f"   [Tentativa {attempt}/3] Erro em {safe_name}: {e}", flush=True)
                    time.sleep(3.0 * attempt)
        finally:
            if tmp_ascii.exists():
                try:
                    tmp_ascii.unlink()
                except Exception:
                    pass
        return False

    with ThreadPoolExecutor(max_workers=4) as executor:
        futs = [executor.submit(upload_one_pdf, item) for item in enumerate(to_upload, 1)]
        for f in as_completed(futs):
            f.result()

    return store_name


def main():
    print("=" * 80, flush=True)
    print("CONFIGURAÇÃO DAS FILESEARCHSTORES PARA RAG TRADICIONAL (CIÊNCIAS EXATAS)", flush=True)
    print("=" * 80, flush=True)

    mapping = load_stores_mapping()
    courses = sorted([d for d in EXATAS_DIR.iterdir() if d.is_dir()], key=lambda x: x.name)

    for c in courses:
        try:
            setup_course_store(c.name, c, mapping)
        except Exception as e:
            print(f"[ERRO NO CURSO {c.name}]: {e}", flush=True)

    print("\n" + "=" * 80, flush=True)
    print("FILESEARCHSTORES CONFIGURADAS COM SUCESSO!", flush=True)
    print(f"Total mapeado: {len(mapping)} cursos.", flush=True)
    print("=" * 80, flush=True)


if __name__ == "__main__":
    main()
