import os
import sys
import time
import types
from pathlib import Path

# Configurar stdout e stderr para UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Mock ONNX para evitar falha no Windows
mock_onnx = types.ModuleType("onnxruntime")
sys.modules["onnxruntime"] = mock_onnx

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.append(str(SCRIPT_DIR))

from dotenv import load_dotenv
import chromadb
from chromadb.config import Settings
import google.generativeai as genai
from chunker import DocumentChunker

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

BASE_DIR = SCRIPT_DIR.parent
PERSIST_DIR = BASE_DIR / "dados vetoriais"
EMBEDDING_MODEL = "models/gemini-embedding-2"

def run_indexing():
    print("Iniciando indexer_runner...")
    chunker = DocumentChunker()
    client = chromadb.PersistentClient(
        path=str(PERSIST_DIR),
        settings=Settings(anonymized_telemetry=False)
    )
    collection = client.get_or_create_collection(
        name="sinform_normas_ufba",
        metadata={"hnsw:space": "cosine"}
    )

    existing_ids = set(collection.get()["ids"])
    print(f"Total já no Chroma: {len(existing_ids)}")

    courses = [
        "Matemática (Bacharel)",
        "Matemática (Licenciatura)",
        "Estatística (Bacharel)"
    ]

    all_chunks = []
    for curso in courses:
        curso_dir = BASE_DIR / curso
        for pdf_path in sorted(list(curso_dir.glob("*.pdf"))):
            raw_text = chunker.extract_text_from_pdf(pdf_path)
            chunks = chunker.parse_document(curso, pdf_path.name, raw_text)
            safe_doc_name = pdf_path.name.replace(".pdf", "")
            for idx, c in enumerate(chunks):
                c["fatia_id"] = f"{curso}_{safe_doc_name}_{idx+1:03d}"
                all_chunks.append(c)

    pending = [c for c in all_chunks if c["fatia_id"] not in existing_ids]
    print(f"Total geral de fatias: {len(all_chunks)} | Pendentes: {len(pending)}")

    if not pending:
        print("Tudo já está indexado no Chroma!")
        return

    # Processar individualmente ou em micro-lotes com controle rígido de taxa
    batch_size = 5
    for i in range(0, len(pending), batch_size):
        batch = pending[i:i + batch_size]
        ids = [c["fatia_id"] for c in batch]
        docs = [c["content"] for c in batch]
        metas = [{
            "curso": c["curso"],
            "documento": c["documento"],
            "title": c["header"],
            "capitulo": c["capitulo"],
            "secao": c["secao"],
            "artigo": c["artigo"],
            "tokens": c["tokens"]
        } for c in batch]

        batch_texts = [f"{c['header']}\n\n{c['content']}" for c in batch]
        embeddings = []

        # Gerar embeddings individualmente para cada fatia garantindo title e content
        for c, text in zip(batch, batch_texts):
            emb = None
            for attempt in range(6):
                try:
                    res = genai.embed_content(
                        model=EMBEDDING_MODEL,
                        content=c["content"],
                        task_type="retrieval_document",
                        title=c["header"]
                    )
                    emb = res["embedding"]
                    break
                except Exception as err:
                    sleep_time = 15 + (attempt * 10)
                    print(f"Aviso cota ({c['fatia_id']}), tentativa {attempt+1}: {err}. Aguardando {sleep_time}s...", flush=True)
                    time.sleep(sleep_time)

            if emb:
                embeddings.append(emb)
            else:
                print(f"Falha ao gerar embedding para {c['fatia_id']}")
                break
            time.sleep(0.5)

        if len(embeddings) == len(ids):
            collection.upsert(
                ids=ids,
                documents=docs,
                embeddings=embeddings,
                metadatas=metas
            )
            count = collection.count()
            print(f"Gravado lote {i//batch_size + 1}! Total no Chroma: {count}/{len(all_chunks)}", flush=True)

        time.sleep(1.0)

    print("\nFINALIZADO! Total final no Chroma:", collection.count())

if __name__ == "__main__":
    run_indexing()
