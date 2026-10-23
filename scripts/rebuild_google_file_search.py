"""
Script para recriar e popular as Google File Search Stores com os 22 PDFs dos 3 cursos da UFBA.
- Utiliza models/gemini-embedding-2 nativo da Google
- Aplica as configurações do Pré-LLM (max_tokens <= 500, max_overlap <= 100, header oficial)
- Insere metadados (curso, documento, header)
- Sem dependência de ChromaDB ou extração manual de texto
"""

import os
import sys
import time
import json
import unicodedata
from pathlib import Path
from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from google import genai
from google.genai import types

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY nao encontrada no .env")

client = genai.Client(api_key=api_key)

COURSES = {
    "Estatística (Bacharel)": "sinform-ufba-estatistica-bacharel",
    "Matemática (Bacharel)": "sinform-ufba-matematica-bacharel",
    "Matemática (Licenciatura)": "sinform-ufba-matematica-licenciatura"
}

STORES_MAP_FILE = BASE_DIR / "google_file_search_stores.json"
PRE_LLM_CONFIG_FILE = BASE_DIR / "pre_llm_chunk_configs.json"

def norm_text(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()

def find_course_dir(curso_nome: str) -> Path:
    target = norm_text(curso_nome)
    for d in BASE_DIR.iterdir():
        if d.is_dir() and norm_text(d.name) == target:
            return d
    return None

def load_pre_llm_configs():
    if PRE_LLM_CONFIG_FILE.exists():
        with open(PRE_LLM_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("courses", {})
    return {}

def main():
    print("=" * 60)
    print(" Configurando Google File Search Stores (Banco Vetorial Google)")
    print("=" * 60)

    pre_llm_data = load_pre_llm_configs()

    # Listar stores existentes
    existing_stores = list(client.file_search_stores.list())
    stores_by_display = {s.display_name: s for s in existing_stores if s.display_name}

    # Deletar stores anteriores para reconstruir com as novas calibrações personalizadas por documento
    for s in existing_stores:
        if s.display_name in COURSES.values():
            print(f"  Deletando store anterior: {s.display_name} ({s.name})...")
            try:
                client.file_search_stores.delete(name=s.name, config=types.DeleteFileSearchStoreConfig(force=True))
                print(f"  [OK] Store deletada com sucesso.")
            except Exception as e:
                print(f"  [Aviso] Falha ao deletar {s.name}: {e}")

    final_mapping = {}

    for curso_nome, store_display in COURSES.items():
        course_dir = find_course_dir(curso_nome)
        if not course_dir:
            print(f"[ERRO] Diretorio do curso '{curso_nome}' nao encontrado!")
            continue

        pdf_files = sorted(list(course_dir.glob("*.pdf")))
        print(f"\n>>> Curso: {curso_nome} ({len(pdf_files)} PDFs)")

        print(f"  Criando nova store '{store_display}' com embedding_model='models/gemini-embedding-2'...")
        store = client.file_search_stores.create(
            config=types.CreateFileSearchStoreConfig(
                display_name=store_display,
                embedding_model="models/gemini-embedding-2"
            )
        )
        print(f"  Store criada com sucesso: {store.name}")
        final_mapping[curso_nome] = store.name

        # Mapear documentos existentes na store para evitar uploads duplicados
        existing_docs = list(client.file_search_stores.documents.list(parent=store.name))
        existing_titles = set()
        for d in existing_docs:
            if hasattr(d, "display_name") and d.display_name:
                existing_titles.add(d.display_name)
            if hasattr(d, "custom_metadata") and d.custom_metadata:
                for cm in d.custom_metadata:
                    if cm.key == "documento" and cm.string_value:
                        existing_titles.add(cm.string_value)

        # Buscar configs deste curso
        course_cfgs = {}
        for item in pre_llm_data.get(curso_nome, []):
            course_cfgs[item.get("documento")] = item

        for pdf in pdf_files:
            cfg = course_cfgs.get(pdf.name, {})
            doc_clean = pdf.stem.replace("_", " ")
            header = cfg.get("header") or f"| {curso_nome} | Documento ({doc_clean}) |"
            max_tokens = int(cfg.get("max_tokens_per_chunk", 400))
            max_overlap = int(cfg.get("max_tokens_overlap", 50))

            # Verificar se já foi indexado
            if pdf.name in existing_titles or header in existing_titles:
                print(f"  [Ja Indexado] {pdf.name}")
                continue

            print(f"  [Upload] {pdf.name} (chunk_size={max_tokens}, overlap={max_overlap})...")
            for attempt in range(5):
                try:
                    op = client.file_search_stores.upload_to_file_search_store(
                        file_search_store_name=store.name,
                        file=str(pdf),
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
                                types.CustomMetadata(key="documento", string_value=pdf.name),
                                types.CustomMetadata(key="header", string_value=header)
                            ]
                        )
                    )

                    # Esperar indexação
                    while not op.done:
                        time.sleep(3)
                        op = client.operations.get(op)

                    print(f"    [OK] Indexado com sucesso no Google File Search!")
                    time.sleep(2)
                    break
                except Exception as e:
                    print(f"    [Tentativa {attempt+1}] Erro: {e}. Aguardando 10s...")
                    time.sleep(10)

    # Salvar mapeamento
    with open(STORES_MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(final_mapping, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(" Processo finalizado com sucesso!")
    print(f" Mapeamento de stores salvo em: {STORES_MAP_FILE}")
    print("=" * 60)

if __name__ == "__main__":
    main()
