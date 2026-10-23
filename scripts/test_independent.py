import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
from rag_engine import SinformRAG
rag = SinformRAG()
store_name = rag.stores_mapping['Estatística (Bacharel)']
q1 = 'regras prazos limites de carga horaria resolucoes aplicaveis atividades complementares extensao'
q2 = 'procedimentos operacionais envio de documentos comprovacao no SIGAA colegiado estatistica'

c1 = rag._retrieve_chunks_for_single_query(store_name, q1, 'Query 1 (Viés A)', 'Estatística (Bacharel)', set())
c2 = rag._retrieve_chunks_for_single_query(store_name, q2, 'Query 2 (Viés B)', 'Estatística (Bacharel)', set())

print(f"Query 1 chunks: {len(c1)}")
for i, c in enumerate(c1, 1):
    h = c['header'][:45]
    print(f"  Q1 [{i}]: {h} | {len(c['content'])} chars")

print(f"Query 2 chunks: {len(c2)}")
for i, c in enumerate(c2, 1):
    h = c['header'][:45]
    print(f"  Q2 [{i}]: {h} | {len(c['content'])} chars")

print(f"Total: {len(c1) + len(c2)}")
