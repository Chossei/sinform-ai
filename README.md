# Sinform AI - Consultor Inteligente de Normas Acadêmicas da UFBA 🎓

O **Sinform AI** é uma plataforma institucional de inteligência artificial generativa com Recuperação Aumentada por Conhecimento (**RAG - Retrieval-Augmented Generation**), desenvolvida sob medida para discentes dos cursos de **Ciências Exatas do Instituto de Matemática e Estatística (IME) da Universidade Federal da Bahia (UFBA)**.

A plataforma atende:
1. **Estatística (Bacharelado)**
2. **Matemática (Bacharelado)**
3. **Matemática (Licenciatura)**

---

## 🏛️ Funcionalidades e Arquitetura Atualizada

- **Portão Obrigatório de Seleção de Curso:** O usuário seleciona seu curso antes de acessar a interface de conversação, garantindo isolamento estrito de dados e conformidade das resoluções acadêmicas.
- **Pré-LLM Multimodal de Visão Estruturada:** Cada PDF oficial é analisado pelo **Gemini 3.5 Flash Lite** (com fallback para **Gemini 3.1 Flash Lite**) via Files API multimodal. O modelo avalia a densidade visual dos artigos e seções, retornando via **Output Estruturado (Pydantic)**:
  - Cabeçalho padronizado: `| Curso | Documento (Nome do documento) |`
  - Quantidade máxima de tokens por chunk (`max_tokens_per_chunk`)
  - Quantidade máxima de sobreposição (`max_tokens_overlap`)
  - Justificativa técnica do fatiamento.
- **Vetorização no ChromaDB com Gemini Embedding 2:**
  - Embeddings gerados via `models/gemini-embedding-2` utilizando `title=header` e `content=conteudo_do_chunk`.
  - Filtro vetorial por metadados: `where={"curso": selected_course}`.
- **Multi-Query com Output Estruturado:**
  - O motor de expansão de consultas formula **duas perguntas distintas com dois vieses complementares** (Viés A: regras, limites e prazos; Viés B: procedimentos práticos, documentação e trâmites no SIGAA).
- **Busca Dupla (Top-5 + Top-5 = 10 Chunks):**
  - Recupera os 5 fragmentos mais similares via seno-cosseno para a Query A e 5 fragmentos para a Query B, fornecendo **10 fragmentos de contexto** para o chatbot.
- **Status Dinâmico em Três Fases na Tela:**
  1. `(Criando as consultas…)`
  2. `Pesquisando os documentos`
  3. `Gerando sua resposta…`
- **Auditoria de Custos da API por Milhão de Tokens (USD):**
  - Monitoramento em tempo real do custo estimado das chamadas da API:
    - *LLM Input:* $0.075 / 1M tokens
    - *LLM Output:* $0.300 / 1M tokens
    - *Embeddings:* $0.020 / 1M tokens
  - Exibição de custos no painel da sidebar e metadados de cada resposta.
- **Suporte Multiturno:**
  - O chatbot compreende saudações e interações simples sem gastar buscas vetoriais desnecessárias e preserva o contexto das mensagens anteriores.
- **Defesas Rígidas de Segurança:**
  - Recusa automática de Prompt Injections e temas fora de escopo com a resposta padrão: `"Desculpe, não posso te ajudar com isso."`
- **Citações Regulamentares Estritas:**
  - Toda resposta acadêmica fundamenta obrigatoriamente a resolução, regimento e artigo correspondente.

---

## 📂 Acervo Normativo e Documental Indexado (22 Documentos Oficiais)

### 1. Estatística (Bacharelado)
- **Resolução nº 03/2025:** Atividades Complementares no SIGAA e 120h extensionistas.
- **Resolução nº 05/2024:** Normas de TCC, prazos e bancas examinadoras.
- **Resoluções nº 01/2020 e 02/2020:** Regulamentação de Estágio no IME.
- **Resolução nº 01/2018:** Trancamento parcial/total e permanência/jubilamento.
- **Resolução nº 02/2018:** Dispensa e aproveitamento de estudos/conhecimento prévio.
- **Instrução Normativa nº 006/2025:** Trancamento específico de TCC.
- **Guia de Registros Acadêmicos 2025.1:** Matrícula e calendário acadêmico.
- **Projeto Pedagógico do Curso (PPC) de Estatística.**
- **Regulamento Acadêmico Geral da UFBA (REGPG/SUPAC).**

### 2. Matemática (Bacharelado)
- **Regulamento de Estágio Supervisionado (30h).**
- **Regulamento de Atividades Complementares (ACC).**
- **Regimento Interno do Colegiado de Matemática (COLMAT).**
- **Projeto Pedagógico do Curso (PPC Diurno) - Bacharelado.**
- **Regulamento Acadêmico Geral da UFBA (REGPG/SUPAC).**

### 3. Matemática (Licenciatura)
- **Regulamento de Estágio Supervisionado Docente (400h - Estágio I a IV).**
- **Regulamento de Atividades Complementares da Licenciatura.**
- **Regimento Interno do Colegiado de Matemática.**
- **Projeto Pedagógico do Curso (PPC Diurno) - Licenciatura.**
- **Projeto Pedagógico do Curso (PPC Noturno) - Licenciatura.**
- **Regulamento Acadêmico Geral da UFBA (REGPG/SUPAC).**

---

## 🚀 Como Executar o Sinform AI

### Pré-requisitos
- Python 3.10 ou superior
- Chave de API do Google Gemini (`GEMINI_API_KEY`)

### Instalação

```bash
git clone https://github.com/Chossei/sinform-ai.git
cd sinform-ai
pip install -r requirements.txt
```

Configure o arquivo `.env`:
```env
GEMINI_API_KEY=sua_chave_gemini_aqui
```

### Inicializando a Aplicação Web Streamlit

```bash
streamlit run app.py
```

Acesse no navegador: **[http://localhost:8501](http://localhost:8501)**.

---

## 🛠️ Scripts do Pipeline

- **Pré-LLM Multimodal (Análise de PDFs com Structured Output):**
  ```bash
  python scripts/pre_llm_analyzer.py
  ```
- **Fatiador Regulamentar Calibrado pelo Pré-LLM:**
  ```bash
  python scripts/chunker_pre_llm.py
  ```
- **Indexador Vetorial ChromaDB (com title e content):**
  ```bash
  python scripts/index_pre_llm_chroma.py
  ```
- **Teste do RAG Multiturno:**
  ```bash
  python rag_engine.py
  ```
