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

# Prevenir falha de inicialização de ONNX não utilizado
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
if not api_key:
    raise ValueError("GEMINI_API_KEY não foi encontrada no arquivo .env!")

genai.configure(api_key=api_key)

BASE_DIR = SCRIPT_DIR.parent
PERSIST_DIR = BASE_DIR / "dados vetoriais"
PERSIST_DIR.mkdir(parents=True, exist_ok=True)

COURSES = [
    "Matemática (Bacharel)",
    "Matemática (Licenciatura)",
    "Estatística (Bacharel)"
]

EMBEDDING_MODEL = "models/gemini-embedding-2"

def main():
    print("=" * 75)
    print("SINFORM AI - PROCESSAMENTO DE DOCUMENTOS E INDEXAÇÃO VETORIAL (UFBA)")
    print(f"Diretório de Persistência Vetorial: {PERSIST_DIR}")
    print(f"Modelo de Embeddings: {EMBEDDING_MODEL}")
    print("=" * 75)

    chunker = DocumentChunker()
    client = chromadb.PersistentClient(
        path=str(PERSIST_DIR),
        settings=Settings(anonymized_telemetry=False)
    )

    # Cria ou obtém a coleção principal do Chroma com batch_size estendido para estabilidade
    collection = client.get_or_create_collection(
        name="sinform_normas_ufba",
        metadata={"hnsw:space": "cosine", "hnsw:batch_size": 10000}
    )

    existing_ids = set(collection.get()["ids"])
    print(f"Registros já existentes no Chroma: {len(existing_ids)}")

    all_chunks = []
    total_docs = 0

    for curso in COURSES:
        curso_dir = BASE_DIR / curso
        if not curso_dir.exists():
            continue

        pdf_files = sorted(list(curso_dir.glob("*.pdf")))
        print(f"\n[Curso: {curso}] - {len(pdf_files)} arquivos PDF:")

        for pdf_path in pdf_files:
            total_docs += 1
            doc_name = pdf_path.name

            try:
                raw_text = chunker.extract_text_from_pdf(pdf_path)
                chunks = chunker.parse_document(curso, doc_name, raw_text)

                safe_doc_name = doc_name.replace(".pdf", "")
                fatias_dir = curso_dir / safe_doc_name
                fatias_dir.mkdir(parents=True, exist_ok=True)

                for idx, c in enumerate(chunks):
                    fatia_filename = f"fatia_{idx+1:03d}.txt"
                    fatia_path = fatias_dir / fatia_filename
                    if not fatia_path.exists():
                        with open(fatia_path, "w", encoding="utf-8") as f:
                            f.write(c["header"] + "\n\n" + c["content"] + "\n")

                    c["fatia_path"] = str(fatia_path)
                    c["fatia_id"] = f"{curso}_{safe_doc_name}_{idx+1:03d}"
                    all_chunks.append(c)

                print(f"  -> {doc_name} ({len(chunks)} fatias)", flush=True)

            except Exception as e:
                print(f"  -> {doc_name}: ERRO: {e}", flush=True)

    pending_chunks = [c for c in all_chunks if c["fatia_id"] not in existing_ids]

    print("\n" + "=" * 75)
    print(f"Total de documentos lidos: {total_docs}")
    print(f"Total de fatias no acervo: {len(all_chunks)}")
    print(f"Fatias já indexadas no Chroma: {len(existing_ids)}")
    print(f"Fatias pendentes de indexação: {len(pending_chunks)}")
    print("=" * 75)

    if not pending_chunks:
        print("Todos os blocos já estão indexados no Chroma!")
    else:
        # Lotes de 8 blocos para respeitar cotas de requisição e tokens
        batch_size = 8
        inserted = len(existing_ids)

        for i in range(0, len(pending_chunks), batch_size):
            batch = pending_chunks[i:i + batch_size]
            ids = [c["fatia_id"] for c in batch]
            documents = [c["content"] for c in batch]
            metadatas = [{
                "curso": c["curso"],
                "documento": c["documento"],
                "title": c["header"],
                "capitulo": c["capitulo"],
                "secao": c["secao"],
                "artigo": c["artigo"],
                "tokens": c["tokens"]
            } for c in batch]

            batch_texts = [f"{c['header']}\n\n{c['content']}" for c in batch]

            embeddings = None
            max_retries = 8
            for attempt in range(max_retries):
                try:
                    res = genai.embed_content(
                        model=EMBEDDING_MODEL,
                        content=batch_texts,
                        task_type="retrieval_document"
                    )
                    embeddings = res["embedding"]
                    break
                except Exception as err:
                    wait_time = 20 + (attempt * 10)
                    print(f"\nAviso cota no lote {i//batch_size + 1} (tentativa {attempt+1}/{max_retries}): {err}. Aguardando {wait_time}s...", flush=True)
                    time.sleep(wait_time)

            if embeddings and len(embeddings) == len(ids):
                collection.upsert(
                    ids=ids,
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas
                )
                inserted += len(batch)
                print(f"Progresso: {inserted}/{len(all_chunks)} blocos vetorizados e persistidos...", flush=True)
            else:
                print(f"Aviso no lote {ids[0]}, tentando avançar.", flush=True)

            time.sleep(3.0)

    print("\n" + "=" * 75)
    print("INDEXAÇÃO VETORIAL FINALIZADA COM SUCESSO!")
    print(f"Total de registros na base vetorial Chroma: {collection.count()}")
    print("=" * 75)

    # Testes de validação RAG com filtro por curso
    print("\nExecutando consultas de validação RAG com filtro por curso:")
    validation_queries = [
        ("Estatística (Bacharel)", "Quais as regras para validação de horas de atividades complementares no SIGAA?"),
        ("Estatística (Bacharel)", "Como funciona o trancamento total do curso e quais as condições de permanência?"),
        ("Matemática (Bacharel)", "Quais os requisitos e carga horária para o estágio supervisionado do bacharelado?"),
        ("Matemática (Licenciatura)", "Como é organizado o estágio supervisionado de prática docente na licenciatura?")
    ]

    for curso_test, query_text in validation_queries:
        print(f"\n>> Filtro: [{curso_test}] | Pergunta: '{query_text}'")
        res_q = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=query_text,
            task_type="retrieval_query"
        )
        res = collection.query(
            query_embeddings=[res_q["embedding"]],
            n_results=2,
            where={"curso": curso_test}
        )
        for doc, meta in zip(res["documents"][0], res["metadatas"][0]):
            print(f"   [CITAÇÃO]: {meta.get('title')}")
            print(f"   [CONTEÚDO]: {doc[:160].replace(chr(10), ' ')}...\n")

if __name__ == "__main__":
    main()
