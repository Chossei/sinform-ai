import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
from google import genai
from google.genai import types
import json, os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

client = genai.Client()
with open(BASE_DIR / "google_file_search_stores.json", encoding="utf-8") as f:
    stores = json.load(f)

store_name = stores["Estatística (Bacharel)"]

def retrieve_5_chunks_for_query(q_text: str, q_tag: str, curso: str) -> list:
    chunks = []
    seen_texts = set()

    prompts = [
        f"Pesquise nos documentos via file_search e extraia 5 trechos ou dispositivos regulamentares normativos distintos sobre: {q_text}. Apresente 5 trechos numerados de 1 a 5.",
        f"Pesquise no file_search trechos regulamentares complementares ou correlatos sobre normas gerais, resoluções e diretrizes de {q_text}. Transcreva trechos numerados de 1 a 5."
    ]

    for p in prompts:
        if len(chunks) >= 5:
            break
        try:
            resp = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=p,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(file_search=types.FileSearch(
                        file_search_store_names=[store_name],
                        top_k=20
                    ))],
                    temperature=0.0
                )
            )
            if resp and resp.candidates:
                cand = resp.candidates[0]
                if hasattr(cand, "grounding_metadata") and cand.grounding_metadata:
                    gcs = getattr(cand.grounding_metadata, "grounding_chunks", []) or []
                    for gc in gcs:
                        rc = getattr(gc, "retrieved_context", None)
                        txt = (getattr(rc, "text", "") or "") if rc else str(gc)[:350]
                        clean_key = txt.strip()[:80]
                        if clean_key and clean_key not in seen_texts:
                            seen_texts.add(clean_key)
                            title = (getattr(rc, "title", "") if rc else "") or f"| {curso} | Fragmento Oficial |"
                            doc_name = (getattr(rc, "document_name", "") if rc else "") or "Regulamento Acadêmico Oficial"
                            chunks.append({
                                "header": title,
                                "origem_query": q_tag,
                                "documento": doc_name,
                                "capitulo": "Normas UFBA",
                                "secao": "Colegiado",
                                "artigo": f"Disposição Aplicável ({q_tag})",
                                "content": txt if txt else "Fragmento indexado no Google File Search"
                            })
                            if len(chunks) >= 5:
                                break
        except Exception as e:
            print(f"Erro na busca {q_tag}: {e}")

    return chunks[:5]

q1 = "regras prazos limites de carga horaria resolucoes aplicaveis atividades complementares extensao"
q2 = "procedimentos operacionais envio de documentos comprovacao no SIGAA colegiado estatistica"

c1 = retrieve_5_chunks_for_query(q1, "Query 1 (Viés A: Regras & Prazos)", "Estatística (Bacharel)")
c2 = retrieve_5_chunks_for_query(q2, "Query 2 (Viés B: Procedimentos & SIGAA)", "Estatística (Bacharel)")

print(f"Chunks Query 1: {len(c1)}")
for i, c in enumerate(c1, 1):
    print(f"  Q1-[{i}] {c['origem_query']} | {c['header'][:45]} | len: {len(c['content'])}")

print(f"\nChunks Query 2: {len(c2)}")
for i, c in enumerate(c2, 1):
    print(f"  Q2-[{i}] {c['origem_query']} | {c['header'][:45]} | len: {len(c['content'])}")

total = c1 + c2
print(f"\nTOTAL NO CONTEXTO: {len(total)} CHUNKS!")
