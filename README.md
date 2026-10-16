# Sinform AI - Consultor Inteligente de Normas Acadêmicas da UFBA 🎓

O **Sinform AI** é uma plataforma institucional de inteligência artificial generativa com Recuperação Aumentada por Conhecimento (**RAG - Retrieval-Augmented Generation**), desenvolvida sob medida para discentes dos cursos de **Ciências Exatas do Instituto de Matemática e Estatística (IME) da Universidade Federal da Bahia (UFBA)**.

A plataforma atende:
1. **Estatística (Bacharelado)**
2. **Matemática (Bacharelado)**
3. **Matemática (Licenciatura)**

---

## 🏛️ Funcionalidades e Diferenciais

- **Portão Obrigatório de Seleção de Curso:** O usuário seleciona obrigatoriamente seu curso antes de acessar a interface de conversação, garantindo isolamento estrito de dados e conformidade das resoluções acadêmicas.
- **Filtro Vetorial por Metadados:** Cada busca no ChromaDB filtra exclusivamente pelo metadado `where={"curso": selected_course}`, impedindo contaminação cruzada entre cursos (por exemplo, normas de estágio de licenciatura não afetam bacharelado).
- **RAG com Citações Regulamentares Rigorosas:** Cada resposta detalha com precisão a resolução, regimento interno ou PPC consultado, indicando capítulo, seção, artigo e parágrafo.
- **Defesa Contra Prompt Injection:** Salvaguarda ativa no pipeline que detecta e neutraliza tentativas de jailbreak, desvio de persona ou comandos maliciosos, respondendo estritamente com `"Desculpe, não posso te ajudar com isso."`.
- **Filtro Fora de Escopo:** Perguntas não acadêmicas ou estranhas às resoluções dos cursos são imediatamente recusadas com a mensagem padrão de escopo.
- **Expansores de Fontes Originais:** Abaixo de cada resposta, o usuário pode inspecionar os fragmentos normativos originais utilizados como embasamento.
- **Multi-Modelo Gemini:** Suporte transparente aos modelos de última geração:
  - `gemini-3.5-flash-lite` (Padrão)
  - `gemini-3.1-flash-lite`

---

## 📂 Acervo Normativo e Documental Indexado

Todos os documentos foram obtidos oficialmente dos portais dos Colegiados (incluindo o portal oficial do COLEST: `https://colest.ime.ufba.br/` e Colegiado de Matemática):

### 1. Estatística (Bacharelado)
- **Resolução nº 03/2025:** Normas para concessão e validação de Atividades Complementares no SIGAA e creditação da extensão (120h extensionistas / 150h totais).
- **Resolução nº 05/2024:** Normas e diretrizes de Trabalho de Conclusão de Curso (TCC) e bancas examinadoras.
- **Resolução nº 01/2020 & 02/2020:** Regulamentação de Estágio Supervisionado Obrigatório e Não-Obrigatório no âmbito do IME/UFBA.
- **Resolução nº 01/2018:** Normas para trancamento parcial/total e critérios de permanência/jubilamento.
- **Resolução nº 02/2018:** Dispensa de disciplinas e aproveitamento de estudos/conhecimento prévio.
- **Instrução Normativa nº 006/2025:** Procedimentos específicos de trancamento de matrícula em TCC.
- **Guia de Registros Acadêmicos 2025.1:** Procedimentos de matrícula e calendário acadêmico.
- **Projeto Pedagógico do Curso (PPC) de Estatística:** Grade, matriz curricular, perfil do egresso e carga horária total.
- **Regulamento Acadêmico Geral da UFBA (REGPG/SUPAC).**

### 2. Matemática (Bacharelado)
- **Regulamento de Estágio Supervisionado do Bacharelado (30 horas).**
- **Regulamento de Atividades Complementares do Bacharelado em Matemática.**
- **Regimento Interno do Colegiado de Matemática (COLMAT).**
- **Projeto Pedagógico do Curso (PPC Diurno) - Bacharelado.**
- **Regulamento Acadêmico Geral da UFBA (REGPG/SUPAC).**

### 3. Matemática (Licenciatura)
- **Regulamento de Estágio Supervisionado da Licenciatura em Matemática (400 horas - I, II, III e IV).**
- **Regulamento de Atividades Complementares da Licenciatura.**
- **Projeto Pedagógico do Curso (PPC Diurno) - Licenciatura.**
- **Projeto Pedagógico do Curso (PPC Noturno) - Licenciatura.**
- **Regimento Interno do Colegiado de Matemática.**
- **Regulamento Acadêmico Geral da UFBA (REGPG/SUPAC).**

---

## ⚙️ Pipeline de Processamento e Indexação

1. **Extração de Texto:** Leitura dos PDFs oficiais página a página via `PyMuPDF` (`fitz`).
2. **Fatiamento Semântico Regulamentar (`scripts/chunker.py`):**
   - Expressões regulares que identificam a hierarquia: `Capítulo`, `Seção`, `Artigo` e `Parágrafo`.
   - **Cabeçalho padronizado:** `| Curso | Documento | Capítulo xx | Seção xx | Artigo xx |`.
   - **Controle de tokens (`tiktoken` cl100k_base):**
     - Fragmentos com menos de 400 tokens são agrupados com o artigo subsequente (`Artigo X e Artigo Y`).
     - Fragmentos com mais de 1200 tokens são particionados por parágrafos (`Parágrafos X-Y`).
   - Todos os 226 fragmentos gerados são salvos fisicamente em diretórios no formato: `[Curso]/[Nome_do_documento]/fatia_XXX.txt`.
3. **Vetorização no ChromaDB (`scripts/process_and_index.py`):**
   - Banco vetorial persistente ChromaDB localizado na pasta `dados vetoriais`.
   - Embeddings gerados com `models/gemini-embedding-2` (3072 dimensões).
   - Metadados indexados: `curso`, `documento`, `capitulo`, `secao`, `artigo`, `tokens`, `fatia_id`.

---

## 🚀 Como Executar o Sinform AI

### Pré-requisitos
- Python 3.10 ou superior
- Chave de API do Google Gemini (`GEMINI_API_KEY`)

### Instalação

1. Clone o repositório ou navegue até o diretório do projeto:
```bash
git clone <URL_DO_REPOSITORIO>
cd "Aplicação - Sinform AI"
```

2. Crie e ative um ambiente virtual (opcional, mas recomendado):
```bash
python -m venv venv
# No Windows:
venv\Scripts\activate
# No Linux/Mac:
source venv/bin/activate
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
# Ou instale diretamente:
pip install streamlit chromadb google-generativeai pypdf pymupdf tiktoken python-dotenv
```

4. Configure o arquivo `.env`:
Crie um arquivo `.env` na raiz do projeto (baseando-se no `.env.example`) com a sua chave da API Gemini:
```env
GEMINI_API_KEY=sua_chave_gemini_aqui
```

### Inicializando a Aplicação Web Streamlit

Execute o comando:
```bash
streamlit run app.py
```

Acesse o endereço exibido no terminal (geralmente [http://localhost:8501](http://localhost:8501)).

---

## 🛠️ Scripts Auxiliares

- **Fatiamento dos Documentos:**
  ```bash
  python scripts/chunker.py
  ```
  *(Reprocessa todos os PDFs dos diretórios dos cursos e gera os arquivos `.txt` de fatias regulamentares).*

- **Indexação Vetorial no ChromaDB:**
  ```bash
  python scripts/process_and_index.py
  ```
  *(Gera os embeddings vetoriais com `models/gemini-embedding-2` e persiste no ChromaDB em `dados vetoriais`).*

- **Teste Automatizado de RAG:**
  ```bash
  python rag_engine.py
  ```
  *(Executa a suíte de testes de perguntas reais, tentativa de injeção de prompt e perguntas fora de escopo).*

---

## 🛡️ Segurança e Resoluções Consultadas

O Sinform AI segue estritamente as diretrizes da Universidade Federal da Bahia. As respostas são geradas com base factual direta nos regulamentos oficiais. Qualquer dúvida adicional ou situações excepcionais devem ser encaminhadas diretamente ao Colegiado do respectivo curso.
