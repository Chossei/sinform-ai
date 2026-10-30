"""
Script de Construção e Indexação do Banco Vetorial do RAG Tradicional (Google FileSearchStore).

Especificações de 'Experimento/instrucoes adicionais.md':
1. Refaz os embeddings e hospeda o banco vetorial utilizando a FileSearchStore da Google.
2. Inclui todos os 9 documentos PDF do curso de 'Estatística (Bacharel)'.
3. Define os parâmetros de chunking como DEFAULT (sem ChunkingConfig customizado).
4. Utiliza exclusivamente a chave 'GEMINI_API_KEY_2' presente em 'Experimento/chave2.env'.
5. Respeita os limites de RPM (100 RPM) e RPD (1000 RPD) do modelo gemini-embedding-2.
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from google import genai
from google.genai import types

RAG_TRAD_DIR = Path(__file__).resolve().parent
EXPERIMENTO_DIR = RAG_TRAD_DIR.parent
BASE_DIR = EXPERIMENTO_DIR.parent

sys.path.append(str(EXPERIMENTO_DIR))
from rate_limiter import get_rate_limiter

# Carregar chave2.env
ENV_PATH = EXPERIMENTO_DIR / "chave2.env"
load_dotenv(ENV_PATH)

API_KEY_2 = os.getenv("GEMINI_API_KEY_2")
if not API_KEY_2:
    raise ValueError(f"GEMINI_API_KEY_2 não foi encontrada em {ENV_PATH}!")

CURSO_ALVO = "Estatística (Bacharel)"
STORE_DISPLAY_NAME = "sinform-rag-tradicional-estatistica-default"
STORE_CONFIG_FILE = RAG_TRAD_DIR / "store_tradicional_config.json"

LOG_DIR = EXPERIMENTO_DIR / "logs" / "rag_tradicional"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "setup_file_search.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("SetupRAGTradicional")


def build_traditional_file_search_store(force_recreate: bool = True) -> dict:
    """
    Cria a FileSearchStore na conta associada à GEMINI_API_KEY_2 com models/gemini-embedding-2
    e faz upload dos 9 PDFs de Estatística (Bacharel) usando parâmetros de chunking DEFAULT.
    """
    client = genai.Client(api_key=API_KEY_2)
    emb_limiter = get_rate_limiter("gemini-embedding-2", key_id="GEMINI_API_KEY_2")

    course_dir = BASE_DIR / CURSO_ALVO
    if not course_dir.exists():
        raise FileNotFoundError(f"Pasta do curso não encontrada: {course_dir}")

    pdf_files = sorted(list(course_dir.glob("*.pdf")))
    logger.info("=" * 65)
    logger.info(" INICIANDO SETUP DO RAG TRADICIONAL (FileSearchStore - Default Chunking)")
    logger.info(f" Curso: {CURSO_ALVO} | Total de PDFs: {len(pdf_files)}")
    logger.info("=" * 65)

    # Verificar stores existentes na conta GEMINI_API_KEY_2
    existing_stores = list(client.file_search_stores.list())
    for s in existing_stores:
        if s.display_name == STORE_DISPLAY_NAME:
            if force_recreate:
                logger.info(f"Deletando store anterior '{s.display_name}' ({s.name}) para recriar do zero...")
                try:
                    client.file_search_stores.delete(
                        name=s.name,
                        config=types.DeleteFileSearchStoreConfig(force=True)
                    )
                    logger.info("Store anterior removida com sucesso.")
                except Exception as e:
                    logger.warning(f"Aviso ao remover store anterior {s.name}: {e}")
            else:
                logger.info(f"Reutilizando store existente: {s.name}")

    # Criar nova FileSearchStore com gemini-embedding-2
    logger.info(f"Criando FileSearchStore '{STORE_DISPLAY_NAME}' com models/gemini-embedding-2...")
    emb_limiter.acquire()
    store = client.file_search_stores.create(
        config=types.CreateFileSearchStoreConfig(
            display_name=STORE_DISPLAY_NAME,
            embedding_model="models/gemini-embedding-2"
        )
    )
    logger.info(f"[OK] Store criada: {store.name}")

    uploaded_docs = []

    for idx, pdf_path in enumerate(pdf_files, 1):
        doc_name = pdf_path.name
        logger.info(f"[{idx}/{len(pdf_files)}] Enviando '{doc_name}' com chunking_config=DEFAULT (None)...")

        for attempt in range(1, 6):
            try:
                # Respeitar rate limit de embedding (100 RPM / 1000 RPD)
                rate_status = emb_limiter.acquire()
                logger.info(
                    f"  -> Rate Limiter (gemini-embedding-2): RPM={rate_status['rpm_current']}/100 | "
                    f"RPD={rate_status['rpd_current']}/1000"
                )

                # Upload com parâmetros de chunking DEFAULT (sem especificar chunking_config)
                op = client.file_search_stores.upload_to_file_search_store(
                    file_search_store_name=store.name,
                    file=str(pdf_path),
                    config=types.UploadToFileSearchStoreConfig(
                        display_name=doc_name,
                        custom_metadata=[
                            types.CustomMetadata(key="curso", string_value=CURSO_ALVO),
                            types.CustomMetadata(key="documento", string_value=doc_name)
                        ]
                    )
                )

                while not op.done:
                    time.sleep(3)
                    op = client.operations.get(op)

                logger.info(f"  [OK] '{doc_name}' indexado com sucesso na FileSearchStore!")
                uploaded_docs.append({
                    "documento": doc_name,
                    "size_bytes": pdf_path.stat().st_size,
                    "chunking": "default"
                })
                break
            except Exception as e:
                logger.error(f"  [Tentativa {attempt}/5] Erro ao indexar '{doc_name}': {e}")
                time.sleep(8 * attempt)

    store_metadata = {
        "created_at": datetime.now().isoformat(),
        "curso": CURSO_ALVO,
        "store_name": store.name,
        "display_name": STORE_DISPLAY_NAME,
        "embedding_model": "models/gemini-embedding-2",
        "chunking_config": "default",
        "api_key_env": "GEMINI_API_KEY_2",
        "total_documents": len(uploaded_docs),
        "documents": uploaded_docs
    }

    with open(STORE_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(store_metadata, f, ensure_ascii=False, indent=2)

    logger.info("=" * 65)
    logger.info(f" SETUP CONCLUÍDO! Store '{store.name}' salva em: {STORE_CONFIG_FILE}")
    logger.info("=" * 65)
    return store_metadata


if __name__ == "__main__":
    build_traditional_file_search_store(force_recreate=True)

