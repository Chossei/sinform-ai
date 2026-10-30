# Relatório Final do Experimento — Comparação de Acurácia dos RAGs (Estatística - UFBA)

**Data de conclusão:** 29/10/2026  
**Curso avaliado:** Estatística (Bacharel) — 9 documentos normativos oficiais (100 perguntas de teste)  
**Modelo Gerador (RAGs):** `gemini-3.5-flash-lite` + `models/gemini-embedding-2`  
**Modelo Avaliador (Juiz de Decisão):** `typesafe/jev-1.14` (`typesafe/jev-1.14-20261014`) via OpenRouter Decisions API (`type: "noul"`)

---

## 1. Resumo Executivo e Verificação de Integridade

Todas as 3 etapas foram executadas até o fim e auditadas:
- **Etapa 1 — RAG Fichamento + API File (`resposta_modelo_rag_fichamento`):** `100/100` perguntas respondidas sem falhas (`0` valores nulos, `0` erros/fallbacks, `10` chunks PDF fatiados anexados por consulta).
- **Etapa 2 — RAG Tradicional (`resposta_modelo_rag_tradicional`):** `100/100` perguntas respondidas via Google `FileSearchStore` com parâmetros de *chunking default* e `top_k=10` (`0` valores nulos, `0` erros/fallbacks).
- **Etapa 3 — Avaliação JEV 1.14 (`prob_acerto_jev_*` e `acerto_95_*`):** `100/100` pares avaliados para ambos os RAGs (`200` decisões probabilísticas no total, `0` valores nulos).

---

## 2. Resultados Globais (100 Perguntas)

| Métrica | RAG Tradicional (`FileSearchStore` Default) | RAG Fichamento + API File (PDF Slicing) | Diferença (Fichamento vs. Tradicional) |
| :--- | :---: | :---: | :---: |
| **Probabilidade Média (`prob_acerto_jev`)** | `0,8555` (85,55%) | **`0,9006` (90,06%)** | **+4,51 p.p.** |
| **Probabilidade Mediana** | `0,9300` | **`0,9300`** | `0,00` |
| **Probabilidade Mínima / Máxima** | `0,05` / `0,98` | **`0,11` / `0,98`** | +0,06 no mínimo |
| **Acurácia Estrita (`prob >= 0,95`)** | `32 / 100` (32,0%) | **`34 / 100` (34,0%)** | **+2,0 p.p.** |
| **Acurácia (`prob >= 0,90`)** | `69 / 100` (69,0%) | **`75 / 100` (75,0%)** | **+6,0 p.p.** |
| **Vitórias Diretas (Pergunta a Pergunta)** | `36` vitórias | **`47` vitórias** | **+11 vitórias** (17 empates) |

---

## 3. Desempenho Detalhado por Documento Normativo

| Documento | Nº Perguntas | Prob. Média Tradicional | Prob. Média Fichamento | Acertos >= 0,95 Tradicional | Acertos >= 0,95 Fichamento |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `Guia_Orientacoes_Registros_Academicos_2025` | 18 | 0,9011 | **0,9022** | **4** | 3 |
| `Instrucao_Normativa_006_2025_Trancamento_TCC` | 3 | 0,8167 | **0,9033** | **1** | 0 |
| `Projeto_Pedagogico_Estatistica_Bacharelado` | 3 | **0,8633** | 0,8367 | 0 | 0 |
| `Regulamento_Academico_Graduacao_UFBA` | 3 | **0,8967** | 0,8767 | 0 | 0 |
| `Resolucao_01_2018_Trancamento_e_Permanencia` | 5 | 0,9200 | **0,9220** | 0 | **1** |
| `Resolucao_02_2018_Exame_Conhecimento_Previo` | 3 | **0,6833** | 0,6700 | 0 | 0 |
| `Resolucao_03_2025_Atividades_Complementares_SIGAA` | 16 | 0,7325 | **0,8544** | 3 | **5** |
| `Resolucao_05_2024_TCC_Estatistica` | 23 | 0,8370 | **0,9035** | **7** | 5 |
| `Resolucoes_01_e_02_2020_Estagio_Nao_Obrigatorio_IME` | 26 | 0,9223 | **0,9577** | 17 | **20** |
| **TOTAL / MÉDIA GLOBAL** | **100** | **0,8555** | **0,9006** | **32** | **34** |

---

## 4. Arquivos Gerados e Backups

- **Planilha Oficial Preenchida:** `Experimento/Conjunto de Testes.xlsx`
- **Backups Incrementais:**
  - `Experimento/backups/Conjunto_de_Testes_backup_rag_fichamento.xlsx`
  - `Experimento/backups/Conjunto_de_Testes_backup_rag_tradicional.xlsx`
  - `Experimento/backups/Conjunto_de_Testes_backup_jev.xlsx`
  - Checkpoints JSON: `checkpoint_rag_fichamento.json`, `checkpoint_rag_tradicional.json`, `checkpoint_jev.json`
- **Logs Detalhados:**
  - `Experimento/logs/rag_fichamento/execucao_rag_fichamento.log` e `detalhes_rag_fichamento.jsonl`
  - `Experimento/logs/rag_tradicional/execucao_rag_tradicional.log`, `setup_file_search.log` e `detalhes_rag_tradicional.jsonl`
  - `Experimento/logs/jev/execucao_jev.log` e `detalhes_jev.jsonl`
