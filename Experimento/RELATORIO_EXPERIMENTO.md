# Relatório Final do Experimento — Comparação de Acurácia dos RAGs (Estatística - UFBA)

**Data de conclusão:** 30/10/2026  
**Curso avaliado:** Estatística (Bacharel) — 9 documentos normativos oficiais (100 perguntas de teste)  
**Modelo Gerador (RAGs):** `gemini-3.5-flash-lite`  
**Seletores de Contexto avaliados:**
1. **RAG Tradicional:** Google `FileSearchStore` (chunking default, `top_k=10`)
2. **RAG Fichamento (Embedding):** `models/gemini-embedding-2` + similaridade de cosseno sobre os 29 fichamentos + envio dos 10 PDFs fatiados via API File
3. **RAG Fichamento (JEV 1.14):** `typesafe/jev-1.14` (OpenRouter Decisions API, primitiva booleana `noul`) ranqueando os 29 fichamentos pela maior probabilidade de `TRUE` + envio dos 10 PDFs fatiados via API File  
**Modelo Avaliador (Juiz de Decisão):** `typesafe/jev-1.14` (`typesafe/jev-1.14-20261014`) via OpenRouter Decisions API (`type: "noul"`)

---

## 1. Resumo Executivo e Verificação de Integridade

Todas as etapas foram executadas até o fim e auditadas:
- **RAG Fichamento + Embedding (`resposta_modelo_rag_fichamento`):** `100/100` perguntas respondidas sem falhas (`0` valores nulos, `10` chunks PDF fatiados anexados por consulta).
- **RAG Fichamento + JEV 1.14 (`resposta_modelo_rag_fichamento_jev`):** `100/100` perguntas respondidas sem falhas (`0` valores nulos, seleção Top-10 entre os 29 fichamentos via `typesafe/jev-1.14` + `10` chunks PDF fatiados anexados por consulta).
- **RAG Tradicional (`resposta_modelo_rag_tradicional`):** `100/100` perguntas respondidas via Google `FileSearchStore` com parâmetros de *chunking default* e `top_k=10` (`0` valores nulos).
- **Avaliação JEV 1.14 (`prob_acerto_jev_*` e `acerto_95_*`):** `100/100` respostas avaliadas para cada um dos 3 modelos (`300` decisões probabilísticas de avaliação no total, `0` valores nulos).

---

## 2. Resultados Globais (100 Perguntas)

| Métrica | RAG Tradicional (`FileSearchStore`) | RAG Fichamento (Embedding) | RAG Fichamento (JEV 1.14) |
| :--- | :---: | :---: | :---: |
| **Probabilidade Média (`prob_acerto_jev`)** | `0,8555` (85,55%) | **`0,9006` (90,06%)** | `0,8958` (89,58%) |
| **Acurácia Estrita (`prob >= 0,95`)** | `32 / 100` (32,0%) | `34 / 100` (34,0%) | **`39 / 100` (39,0%)** |
| **Acurácia (`prob >= 0,90`)** | `69 / 100` (69,0%) | **`75 / 100` (75,0%)** | `72 / 100` (72,0%) |

---

## 3. Desempenho Detalhado por Documento Normativo

| Documento | Nº Perguntas (`n`) | Prob. Média Tradicional | Prob. Média Fich. (Emb) | Prob. Média Fich. (JEV) | Acurácia ≥ 0,90 Tradicional | Acurácia ≥ 0,90 Fich. (Emb) | Acurácia ≥ 0,90 Fich. (JEV) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `Guia_Orientacoes_Registros_Academicos_2025` | 18 | 90,1% | 90,2% | **90,4%** | **72,2%** | 66,7% | 66,7% |
| `Instrucao_Normativa_006_2025_Trancamento_TCC` | 3 | 81,7% | 90,3% | **92,0%** | 66,7% | 66,7% | 66,7% |
| `Projeto_Pedagogico_Estatistica_Bacharelado` | 3 | **86,3%** | 83,7% | 86,0% | 33,3% | 33,3% | 33,3% |
| `Regulamento_Academico_Graduacao_UFBA` | 3 | **89,7%** | 87,7% | 86,7% | 33,3% | 33,3% | 33,3% |
| `Resolucao_01_2018_Trancamento_e_Permanencia` | 5 | 92,0% | 92,2% | **92,8%** | **100,0%** | 80,0% | **100,0%** |
| `Resolucao_02_2018_Exame_Conhecimento_Previo` | 3 | 68,3% | 67,0% | **74,0%** | 0,0% | **66,7%** | 33,3% |
| `Resolucao_03_2025_Atividades_Complementares_SIGAA` | 16 | 73,3% | 85,4% | **90,3%** | 50,0% | 62,5% | **68,8%** |
| `Resolucao_05_2024_TCC_Estatistica` | 23 | 83,7% | 90,3% | **91,7%** | 69,6% | **73,9%** | 69,6% |
| `Resolucoes_01_e_02_2020_Estagio_Nao_Obrigatorio_IME` | 26 | 92,2% | **95,8%** | 88,3% | 88,5% | **100,0%** | 88,5% |
| **TOTAL / MÉDIA GLOBAL** | **100** | **85,55%** | **90,06%** | **89,58%** | **69,0%** | **75,0%** | **72,0%** |

---

## 4. Arquivos Gerados e Backups

- **Planilha Oficial Preenchida:** `Experimento/Conjunto de Testes.xlsx`
- **Scripts do Experimento:**
  - `Experimento/run_rag_fichamento.py`
  - `Experimento/run_rag_fichamento_jev.py`
  - `Experimento/setup_file_search_tradicional.py` e `Experimento/run_rag_tradicional.py`
  - `Experimento/run_jev_evaluator.py`
- **Backups Incrementais:**
  - `Experimento/backups/Conjunto_de_Testes_backup_rag_fichamento.xlsx`
  - `Experimento/backups/Conjunto_de_Testes_backup_rag_fichamento_jev.xlsx`
  - `Experimento/backups/Conjunto_de_Testes_backup_rag_tradicional.xlsx`
  - `Experimento/backups/Conjunto_de_Testes_backup_jev.xlsx`
  - Checkpoints JSON: `checkpoint_rag_fichamento.json`, `checkpoint_rag_fichamento_jev.json`, `checkpoint_rag_tradicional.json`, `checkpoint_jev.json`
