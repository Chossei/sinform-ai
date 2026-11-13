"""
===============================================================================
CONFIGURAÇÕES GERAIS E GERENCIADOR DE CHAVES / MODELOS
===============================================================================
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
EXP_DIR = BASE_DIR / "Experimento"

# Carregar variáveis de ambiente dos dois arquivos
load_dotenv(BASE_DIR / ".env")
load_dotenv(EXP_DIR / "chave2.env")

# 1. Chaves da Google Gemini API (prioridade estrita para chaves gratuitas)
GEMINI_KEY_1 = os.getenv("GEMINI_API_KEY")
GEMINI_KEY_2 = os.getenv("GEMINI_API_KEY_2")
GEMINI_KEY_DRVCHOSSEI = os.getenv("GEMINI_API_KEY_DRVCHOSSEI")
GEMINI_KEY_PAGA = os.getenv("GEMINI_PAGO_RICARDO")

GEMINI_FREE_KEYS = [k for k in [GEMINI_KEY_1, GEMINI_KEY_2, GEMINI_KEY_DRVCHOSSEI] if k]
GEMINI_PAID_KEY = GEMINI_KEY_PAGA

# Lista de todas as chaves (gratuitas primeiro, paga por último)
GEMINI_KEYS_POOL = GEMINI_FREE_KEYS + ([GEMINI_PAID_KEY] if GEMINI_PAID_KEY else [])

# 2. Chaves OpenRouter para JEV 1.14 (priorizar chave paga OPEN_ROUTER_API_KEY_2 com créditos)
OR_KEY_1 = os.getenv("OPEN_ROUTER_API_KEY")
OR_KEY_2 = os.getenv("OPEN_ROUTER_API_KEY_2")
OR_KEY_GENERIC = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_KEYS_POOL = list(dict.fromkeys([k for k in [OR_KEY_2, OR_KEY_1, OR_KEY_GENERIC] if k]))
OPENROUTER_KEY = OPENROUTER_KEYS_POOL[0] if OPENROUTER_KEYS_POOL else None

# 3. Nomes Oficiais dos Modelos
PRIMARY_MODEL = "gemini-3.5-flash-lite"
FALLBACK_MODEL = "gemini-3.1-flash-lite"
EMBEDDING_MODEL = "models/gemini-embedding-2"
JEV_MODEL = "typesafe/jev-1.14"

# 4. Parâmetros de Inferência
# Na engenharia de prompt, raciocínio (reasoning) deve ser o mínimo possível
GENERATION_CONFIG = {
    "temperature": 0.2,
    "top_p": 0.95,
}

# 5. Parâmetros de RAG
TOP_K_OPTIONS = [1, 5, 10]

# 6. Caminhos do Experimento
AREAS_DIR = EXP_DIR / "Áreas do conhecimento"
GERAL_DIR = AREAS_DIR / "UFBA - Geral"
TEST_DATASET_FILE = EXP_DIR / "Conjunto de Testes Geral.xlsx"
RESULTADOS_TESTE_FILE = EXP_DIR / "Resultados do teste.xlsx"
BACKUPS_DIR = EXP_DIR / "backups"
LOGS_DIR = EXP_DIR / "logs"
PROGRESS_FILE = EXP_DIR / "progresso_fatiamento.json"

# 7. Orçamento e Precificação (Chave Paga com Flex Inference: 50% de desconto)
BUDGET_LIMIT_USD = 2.00
# Gemini 3.5 Flash Lite em Flex Inference (USD por token)
COST_PROMPT_TOKEN_FLEX = 0.0375 / 1_000_000
COST_CANDIDATE_TOKEN_FLEX = 0.15 / 1_000_000
# Gemini Embedding 2 (USD por token)
COST_EMBEDDING_TOKEN = 0.02 / 1_000_000

BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
