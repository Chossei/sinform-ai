---
name: chroma-db
description: >-
  Guia completo e procedimentos para utilização do banco vetorial Chroma (ChromaDB)
  em Python no projeto Sinform AI. Inclui instanciação de PersistentClient,
  função customizada de embedding Gemini, fatiamento semântico (Artigos/Parágrafos),
  contagem de tokens, filtragem por metadados de cursos e recuperação contextual para RAG.
---

# Skill: Utilização da Biblioteca Chroma (ChromaDB)

Esta skill define as melhores práticas para criação, indexação, persistência e consulta a bancos vetoriais utilizando o ChromaDB no âmbito do projeto Sinform AI.

---

## 1. Instalação e Arquitetura

### 1.1 Dependências
```bash
pip install chromadb google-generativeai python-dotenv pymupdf tiktoken
```

### 1.2 Persistência de Dados
O Chroma deve persistir seus arquivos em disco na pasta designada no plano:
```python
import chromadb
from pathlib import Path

PERSIST_DIR = Path("dados vetoriais")
PERSIST_DIR.mkdir(parents=True, exist_ok=True)

client = chromadb.PersistentClient(path=str(PERSIST_DIR))
```

---

## 2. Função de Embeddings com Gemini

O Chroma permite registrar uma `EmbeddingFunction` personalizada que se comunica diretamente com a API do Google Gemini para converter textos em vetores:

```python
import os
import google.generativeai as genai
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

class GeminiEmbeddingFunction(EmbeddingFunction):
    def __init__(self, api_key: str = None, model_name: str = "models/text-embedding-004"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Chave GEMINI_API_KEY não informada.")
        genai.configure(api_key=self.api_key)
        self.model_name = model_name

    def __call__(self, input: Documents) -> Embeddings:
        embeddings = []
        for text in input:
            try:
                res = genai.embed_content(
                    model=self.model_name,
                    content=text,
                    task_type="retrieval_document"
                )
                embeddings.append(res["embedding"])
            except Exception as e:
                # Tratamento de fallback ou retry
                raise RuntimeError(f"Erro ao gerar embedding no Gemini: {e}")
        return embeddings
```

---

## 3. Criação de Coleções e Metadados

### 3.1 Inicialização de Coleção
```python
embedding_fn = GeminiEmbeddingFunction()
collection = client.get_or_create_collection(
    name="sinform_normas_ufba",
    embedding_function=embedding_fn,
    metadata={"hnsw:space": "cosine"} # Similaridade de cosseno
)
```

### 3.2 Estrutura Padrão de Cabeçalho e Metadados
Conforme o plano do projeto:
- Cabeçalho textual:
  `| Curso | Documento (Nome do documento) | Capítulo xx | Seção xx | Artigo xx |`
- Parâmetro `title`: cabeçalho padrão
- Parâmetro `content`: texto fatiado do artigo/parágrafos
- Metadados recomendados:
  ```python
  metadata = {
      "curso": "Matemática (Bacharel)",
      "documento": "Regulamento_Estagio_Matematica.pdf",
      "capitulo": "Capítulo II",
      "secao": "Seção I",
      "artigo": "Artigo 14",
      "cabecalho": "| Matemática (Bacharel) | Regulamento_Estagio_Matematica.pdf | Capítulo II | Seção I | Artigo 14 |",
      "tokens": 482
  }
  ```

---

## 4. Regras de Fatiamento e Contagem de Tokens

Para garantir coesão semântica sem estourar limites nem perder contexto:
1. **Contagem de tokens**: Usar tokenizer (ex: `tiktoken` com encoding `cl100k_base` ou tokenizer do Gemini).
2. **Artigo < 400 tokens**:
   - Agrupar junto à fatia do artigo anterior.
   - Atualizar cabeçalho para contemplar: `"Artigo X e Artigo Y"`.
3. **Artigo > 1200 tokens**:
   - Fatiar internamente por parágrafos (ex: grupos de parágrafos entre 400 e 800 tokens).
   - Atualizar cabeçalho especificando o intervalo: `"Artigo X (Parágrafos 1-4)"`.
4. **Artigo entre 400 e 1200 tokens**:
   - Mantido como fatia única padrão.

---

## 5. Inserção em Lote (Upsert)

```python
collection.upsert(
    ids=[chunk_id],
    documents=[full_chunk_text], # title + "\n" + content
    metadatas=[metadata]
)
```

---

## 6. Consulta com Filtro de Curso (Metadata Filtering)

O plano exige que a consulta filtre pelo curso selecionado pelo usuário no frontend:
```python
results = collection.query(
    query_texts=[pergunta_do_usuario],
    n_results=4,
    where={"curso": curso_selecionado}
)

# Recuperação dos blocos mais relevantes
context_chunks = []
if results and results.get("documents"):
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        context_chunks.append({
            "cabecalho": meta.get("cabecalho"),
            "conteudo": doc,
            "documento": meta.get("documento"),
            "artigo": meta.get("artigo")
        })
```
