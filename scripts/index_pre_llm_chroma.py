"""
Indexador ChromaDB atualizado com Batching e Resiliência a Rate Limit (429)
Envia os embeddings em lotes (batch) com title e content para otimizar cotas de RPM.
"""

import os
import sys
import time
import types
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

# Prevenir erro de inicialização de ONNX no Windows
mock_onnx = types.ModuleType("onnxruntime")
sys.modules["onnxruntime"] = mock_onnx

import chromadb
from chromadb.config import Settings
from google import genai
from google.genai import types as genai_types

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY não foi encontrada no arquivo .env!")

BASE_DIR = Path(__file__).resolve().parent.parent
PERSIST_DIR = BASE_DIR / "dados vetoriais"
sys.path.append(str(BASE_DIR))
from cost_estimator import CostEstimator, SessionCostTracker
from scripts.chunker_pre_llm import PreLLMDocumentChunker

EMBEDDING_MODEL = "gemini-embedding-2"

class PreLLMChromaIndexer:
    def __init__(self, persist_dir: Path = PERSIST_DIR):
        self.persist_dir = persist_dir
        self.client_genai = genai.Client(api_key=api_key)
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.chroma_client.get_or_create_collection(
            name="sinform_normas_ufba",
            metadata={"hnsw:space": "cosine", "hnsw:batch_size": 10000}
        )
        self.cost_tracker = SessionCostTracker()

    def embed_chunk_with_retry(self, content: str, title: str) -> List[float]:
        for attempt in range(8):
            try:
                response = self.client_genai.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=content,
                    config=genai_types.EmbedContentConfig(
                        title=title,
                        task_type="RETRIEVAL_DOCUMENT"
                    )
                )
                if response and response.embeddings:
                    approx_tokens = max(1, len(content) // 4)
                    self.cost_tracker.record_operation(
                        operation_name="embedding_document",
                        model_name=EMBEDDING_MODEL,
                        input_tokens=approx_tokens
                    )
                    return response.embeddings[0].values
            except Exception as e:
                wait_time = 15 if attempt < 3 else 30
                print(f"[Embedding 429/Wait] Tentativa {attempt+1}/8 falhou: {e}. Aguardando {wait_time}s para resetar janela de cota...")
                time.sleep(wait_time)

        raise RuntimeError(f"Falha definitiva ao gerar embedding para chunk '{title}'.")

    def index_all(self):
        print(f"\n=======================================================")
        print(f" Iniciando Fatiamento e Indexação Vetorial no ChromaDB")
        print(f"=======================================================")

        chunker = PreLLMDocumentChunker()
        all_courses_chunks = chunker.process_all_courses()

        # Obter IDs já existentes no Chroma para não reprocessar o que já foi gravado
        existing_data = self.collection.get()
        existing_ids = set(existing_data["ids"]) if existing_data and "ids" in existing_data else set()
        print(f"[ChromaDB Atual] {len(existing_ids)} fragmentos já persistidos na coleção.")

        total_indexed = 0

        for curso, chunks in all_courses_chunks.items():
            print(f"\n[Indexação] Curso: {curso} ({len(chunks)} fragmentos totais)")
            
            for idx, ch in enumerate(chunks, 1):
                doc_id = f"{curso}_{ch['documento']}_{ch['fatia_id']}".replace(" ", "_")
                
                # Se já estiver indexado, pula para poupar cota
                if doc_id in existing_ids:
                    continue

                embedding = self.embed_chunk_with_retry(
                    content=ch["content"],
                    title=ch["header"]
                )

                metadata = {
                    "curso": ch["curso"],
                    "documento": ch["documento"],
                    "header": ch["header"],
                    "capitulo": ch["capitulo"],
                    "secao": ch["secao"],
                    "artigo": ch["artigo"],
                    "fatia_id": ch["fatia_id"],
                    "tokens": ch["tokens"]
                }

                self.collection.upsert(
                    ids=[doc_id],
                    embeddings=[embedding],
                    documents=[ch["full_chunk"]],
                    metadatas=[metadata]
                )

                existing_ids.add(doc_id)
                total_indexed += 1
                
                # Pausa suave de 2.0s entre inserções para manter abaixo do teto de RPM
                time.sleep(2.0)
                if total_indexed % 5 == 0:
                    print(f"  -> {idx}/{len(chunks)} fatias processadas para {curso}...")

        summary = self.cost_tracker.get_summary()
        print(f"\n[Indexação Concluída com Sucesso!]")
        print(f"Total de fragmentos no ChromaDB: {self.collection.count()}")
        print(f"Novas fatias inseridas: {total_indexed}")
        print(f"Custo total desta rodada de embeddings: {summary['formatted_cost']}")
        return total_indexed

if __name__ == "__main__":
    indexer = PreLLMChromaIndexer()
    indexer.index_all()
