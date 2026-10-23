import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from rag_engine import SinformRAG

rag = SinformRAG()

print("=== Testando Pergunta Acadêmica com TOP-10 Chunks ===")
ans, cits, model, cost, qs = rag.ask(
    "Como funciona a validacao de atividades complementares no SIGAA e quantas horas de extensao sao obrigatorias?",
    curso="Estatística (Bacharel)",
    status_callback=lambda s: print(f"  -> Status: {s}")
)

print(f"\n>>> Total de Chunks no Contexto do Chatbot: {len(cits)} Chunks!")
for i, c in enumerate(cits, 1):
    q_orig = c.get("origem_query", "Busca Vetorial")
    h = c.get("header", "Fragmento")
    sz = len(c.get("content", ""))
    print(f"  [{i}] {q_orig} | {h} ({sz} chars)")

print(f"\nModelo Utilizado: {model}")
print(f"Custo: {cost.get('formatted_cost', '')}")
print("\n--- Resposta Gerada pelo Sinform AI ---")
print(ans)
