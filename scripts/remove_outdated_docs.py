"""
Script para remover documentos desatualizados da base vetorial da Google (File Search)
e do repositório de documentos do Sinform AI:
- Resolucao_Atividades_Complementares_Estatistica
- Resolucao_Estagio_Supervisionado_Estatistica
"""

import os
import sys
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

DOCS_TO_REMOVE = [
    "resolucao_atividades_complementares_estatistica",
    "resolucao_estagio_supervisionado_estatistica"
]

def norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()

def remove_from_google_file_search():
    stores_file = BASE_DIR / "google_file_search_stores.json"
    if not stores_file.exists():
        print("Arquivo de stores nao encontrado.")
        return

    with open(stores_file, "r", encoding="utf-8") as f:
        stores_mapping = json.load(f)

    for curso_nome, store_name in stores_mapping.items():
        print(f"\n[Verificando Store Google] {curso_nome} ({store_name})...")
        docs = list(client.file_search_stores.documents.list(parent=store_name))
        
        for d in docs:
            d_title = getattr(d, "display_name", "") or ""
            d_name = d.name
            
            # Buscar no custom_metadata se houver
            meta_doc = ""
            for cm in getattr(d, "custom_metadata", []):
                if cm.key == "documento":
                    meta_doc = cm.string_value or ""

            target_match = False
            for target in DOCS_TO_REMOVE:
                if target in norm(d_title) or target in norm(meta_doc):
                    target_match = True
                    break

            if target_match:
                print(f"  -> Deletando da Google File Search Store: {d_title} (ID: {d_name})...")
                try:
                    client.file_search_stores.documents.delete(
                        name=d_name,
                        config=types.DeleteDocumentConfig(force=True)
                    )
                    print(f"     [OK] Documento removido do banco vetorial da Google com sucesso!")
                except Exception as e:
                    print(f"     [ERRO ao deletar documento]: {e}")

def remove_from_local_filesystem():
    print("\n[Verificando Arquivos Locais]...")
    import shutil
    for sub in BASE_DIR.iterdir():
        if not sub.is_dir() or sub.name.startswith("."):
            continue

        for pdf_file in list(sub.glob("*.pdf")):
            target_match = False
            for target in DOCS_TO_REMOVE:
                if target in norm(pdf_file.name):
                    target_match = True
                    break
            
            if target_match:
                print(f"  -> Removendo arquivo local: {pdf_file}")
                # Mover para pasta '_desatualizados'
                archive_dir = sub / "_desatualizados"
                archive_dir.mkdir(exist_ok=True)
                target_dest = archive_dir / pdf_file.name
                try:
                    if target_dest.exists():
                        target_dest.unlink()
                    pdf_file.rename(target_dest)
                    print(f"     [OK] Movido para {target_dest}")
                except Exception as e:
                    print(f"     [Aviso ao mover arquivo]: {e}")

                # Remover subpasta correspondente gerada anteriormente se existir
                subfolder = sub / pdf_file.stem
                if subfolder.exists() and subfolder.is_dir():
                    shutil.rmtree(subfolder, ignore_errors=True)
                    print(f"     [OK] Subpasta {subfolder} limpa.")

def clean_pre_llm_json():
    json_file = BASE_DIR / "pre_llm_chunk_configs.json"
    if not json_file.exists():
        return
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    changed = False
    for curso, items in data.get("courses", {}).items():
        new_items = []
        for it in items:
            doc_file = it.get("documento", "")
            if any(t in norm(doc_file) for t in DOCS_TO_REMOVE):
                print(f"  -> Removendo do pre_llm_chunk_configs.json: {doc_file} ({curso})")
                changed = True
            else:
                new_items.append(it)
        data["courses"][curso] = new_items

    if changed:
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("  [OK] pre_llm_chunk_configs.json atualizado com sucesso!")

if __name__ == "__main__":
    remove_from_google_file_search()
    remove_from_local_filesystem()
    clean_pre_llm_json()
    print("\n[Concluído] Documentos desatualizados removidos com sucesso do RAG!")
