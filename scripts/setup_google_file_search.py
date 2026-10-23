"""
Script de Criação e Upload para o Banco de Dados Vetorial da Google (File Search Stores)
Substitui completamente o ChromaDB local pelo serviço de busca vetorial nativo da Google:
- Cria 3 File Search Stores oficiais (uma por curso) com embedding_model='models/gemini-embedding-2'
- Faz upload direto de cada PDF para a Google File Search Store (upload_to_file_search_store)
- Aplica a configuração dinâmica de chunking calibrada pelo Pré-LLM (max_tokens_per_chunk, max_overlap_tokens)
- Insere o cabeçalho padrão (| Curso | Documento (Nome do documento) |) e metadados
- Salva o mapeamento das stores em 'google_file_search_stores.json'
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from google import genai
from google.genai import types

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
from cost_estimator import CostEstimator, SessionCostTracker

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY não foi encontrada no arquivo .env!")

client = genai.Client(api_key=api_key)

COURSES = {
    "Estatística (Bacharel)": "sinform-ufba-estatistica-bacharel",
    "Matemática (Bacharel)": "sinform-ufba-matematica-bacharel",
    "Matemática (Licenciatura)": "sinform-ufba-matematica-licenciatura"
}

STORES_MAP_FILE = BASE_DIR / "google_file_search_stores.json"

def get_or_create_stores() -> Dict[str, str]:
    """
    Obtém as File Search Stores existentes ou cria novas para cada curso.
    """
    existing_stores = list(client.file_search_stores.list())
    stores_by_display = {s.display_name: s.name for s in existing_stores if s.display_name}
    
    mapping = {}
    for curso_nome, store_display in COURSES.items():
        if store_display in stores_by_display:
            store_name = stores_by_display[store_display]
            print(f"[Google File Search] Reutilizando store existente para {curso_nome}: {store_name}")
            mapping[curso_nome] = store_name
        else:
            print(f"[Google File Search] Criando nova store para {curso_nome} com models/gemini-embedding-2...")
            new_store = client.file_search_stores.create(
                config=types.CreateFileSearchStoreConfig(
                    display_name=store_display,
                    embedding_model="models/gemini-embedding-2"
                )
            )
            print(f"[Google File Search] Store criada com sucesso: {new_store.name}")
            mapping[curso_nome] = new_store.name

    return mapping

def upload_all_pdfs():
    print("\n=======================================================")
    print(" Iniciando Upload para o Banco Vetorial da Google (File Search)")
    print("=======================================================")

    stores_mapping = get_or_create_stores()
    
    # Salvar mapeamento
    with open(STORES_MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(stores_mapping, f, ensure_ascii=False, indent=2)

    total_uploaded = 0

    for curso_nome, store_name in stores_mapping.items():
        course_dir = BASE_DIR / curso_nome
        if not course_dir.exists():
            continue

        # Listar documentos já existentes na store
        existing_docs = list(client.file_search_stores.documents.list(parent=store_name))
        existing_doc_names = set()
        for d in existing_docs:
            if hasattr(d, "display_name") and d.display_name:
                existing_doc_names.add(d.display_name)
            if hasattr(d, "custom_metadata") and d.custom_metadata:
                for cm in d.custom_metadata:
                    if cm.key == "documento" and cm.string_value:
                        existing_doc_names.add(cm.string_value)

        pdf_files = sorted(list(course_dir.glob("*.pdf")))
        print(f"\n[Upload Curso] {curso_nome} ({len(pdf_files)} PDFs) -> Store: {store_name}")

        for pdf_file in pdf_files:
            doc_name = pdf_file.name
            doc_clean = pdf_file.stem.replace("_", " ")
            expected_header = f"| {curso_nome} | Documento ({doc_clean}) |"

            # Se já foi enviado para a store, pula
            if doc_name in existing_doc_names or expected_header in existing_doc_names:
                print(f"  [Já Indexado na Google] {doc_name}")
                continue

            # Carregar configuração do Pré-LLM (max_tokens_per_chunk, max_tokens_overlap)
            doc_subfolder = course_dir / pdf_file.stem
            pre_llm_cfg_file = doc_subfolder / "pre_llm_config.json"
            
            max_tokens = 500
            max_overlap = 100
            header = expected_header

            if pre_llm_cfg_file.exists():
                try:
                    with open(pre_llm_cfg_file, "r", encoding="utf-8") as f:
                        cfg_data = json.load(f)
                        raw_max_tokens = int(cfg_data.get("max_tokens_per_chunk", 500))
                        raw_overlap = int(cfg_data.get("max_tokens_overlap", 100))
                        # Google File Search exige que max_tokens_per_chunk esteja entre 0 e 512
                        max_tokens = min(raw_max_tokens, 500)
                        max_overlap = min(raw_overlap, 100)
                        header = cfg_data.get("header", expected_header)
                except Exception:
                    pass

            print(f"  [Enviando para Google File Search] {doc_name}...")
            print(f"    -> Header: {header}")
            print(f"    -> Chunking Config: max_tokens={max_tokens}, overlap={max_overlap}")

            for attempt in range(5):
                try:
                    op = client.file_search_stores.upload_to_file_search_store(
                        file_search_store_name=store_name,
                        file=str(pdf_file),
                        config=types.UploadToFileSearchStoreConfig(
                            display_name=header,
                            chunking_config=types.ChunkingConfig(
                                white_space_config=types.WhiteSpaceConfig(
                                    max_tokens_per_chunk=max_tokens,
                                    max_overlap_tokens=max_overlap
                                )
                            ),
                            custom_metadata=[
                                types.CustomMetadata(key="curso", string_value=curso_nome),
                                types.CustomMetadata(key="documento", string_value=doc_name),
                                types.CustomMetadata(key="header", string_value=header)
                            ]
                        )
                    )

                    # Aguardar processamento do arquivo no banco vetorial da Google
                    while not op.done:
                        time.sleep(3)
                        op = client.operations.get(op)

                    print(f"    [OK] Concluido e indexado no banco vetorial da Google!")
                    total_uploaded += 1
                    time.sleep(2)
                    break
                except Exception as e:
                    print(f"    [Retry {attempt+1}] Erro: {e}. Aguardando 10s...")
                    time.sleep(10)

    print(f"\n=======================================================")
    print(f" Upload concluído! Total de arquivos processados no File Search: {total_uploaded}")
    print(f" Stores salvas em: {STORES_MAP_FILE}")
    print("=======================================================")

if __name__ == "__main__":
    upload_all_pdfs()
