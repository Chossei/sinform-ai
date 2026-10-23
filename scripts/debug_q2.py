import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.append('.')
from rag_engine import SinformRAG
from google.genai import types

rag = SinformRAG()
store_name = rag.stores_mapping['Estatística (Bacharel)']
q2_text = 'Como submeter atividades complementares e comprovantes no SIGAA para analise e aprovacao pelo colegiado do curso de Estatistica Bacharel'
curso = 'Estatística (Bacharel)'

prompts = [
    f"Pesquise nos documentos via file_search e extraia 5 trechos ou dispositivos regulamentares normativos distintos sobre: {q2_text}. Apresente 5 trechos numerados de 1 a 5.",
    f"Pesquise no file_search trechos no 'Guia de Orientações de Registros Acadêmicos' e no 'Regulamento Acadêmico' sobre procedimentos, prazos e normas correlatas a: {q2_text}. Liste 5 trechos.",
    f"Acesse o repositório de documentos do curso de {curso} no file_search e localize 5 trechos regulamentares adicionais sobre vida acadêmica, prazos ou colegiado relacionados a: {q2_text}."
]

existing_signatures = set()
for idx, p in enumerate(prompts, 1):
    print(f"\n--- Testando Prompt {idx} ---")
    resp = rag.client.models.generate_content(
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
    cand = resp.candidates[0]
    gcs = getattr(cand.grounding_metadata, "grounding_chunks", []) or []
    print(f"Grounding chunks retornados: {len(gcs)}")
    for j, gc in enumerate(gcs, 1):
        rc = getattr(gc, "retrieved_context", None)
        txt = (getattr(rc, "text", "") or "") if rc else str(gc)[:350]
        sig = txt.strip()[:80]
        is_new = sig not in existing_signatures
        print(f"  [{j}] title: {getattr(rc, 'title', '')[:40]} | is_new: {is_new}")
        if is_new:
            existing_signatures.add(sig)
print(f"\nTotal assinaturas únicas acumuladas: {len(existing_signatures)}")
