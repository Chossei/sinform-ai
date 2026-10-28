import os
import sys
import json
import time
import shutil
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
from pypdf import PdfReader, PdfWriter
from pydantic import BaseModel, Field

from google import genai
from google.genai import types

PRICING = {
    "gemini-3.5-flash-lite": {
        "input_per_million": 0.30,
        "output_per_million": 2.50
    },
    "gemini-3.1-flash-lite": {
        "input_per_million": 0.25,
        "output_per_million": 1.50
    },
    "gemini-embedding-2": {
        "input_per_million": 0.20
    }
}

BASE_DIR = Path(__file__).resolve().parent.parent

COURSES = [
    "Estatística (Bacharel)",
    "Matemática (Bacharel)",
    "Matemática (Licenciatura)"
]

DOC_LINKS = {
    "Guia_Orientacoes_Registros_Academicos_2025.pdf": "https://colest.ime.ufba.br/wp-content/uploads/2025/04/Guia-de-Orienta%C3%A7%C3%B5es-sobre-Registros-2025.1.pdf",
    "Instrucao_Normativa_006_2025_Trancamento_TCC.pdf": "https://colest.ime.ufba.br/wp-content/uploads/2025/04/Instrucao_Normativa_N%C2%BA_006_2025.pdf",
    "Projeto_Pedagogico_Estatistica_Bacharelado.pdf": "https://colest.ime.ufba.br/",
    "Regulamento_Academico_Graduacao_UFBA.pdf": "https://supac.ufba.br/sites/supac.ufba.br/files/guia_do_estudante_supac.pdf",
    "Resolucao_01_2018_Trancamento_e_Permanencia.pdf": "http://colest.ime.ufba.br/wp-content/uploads/2019/03/Resolu%C3%A7%C3%A3o-01_2018_Trancamento-e-Perman%C3%AAncia.pdf",
    "Resolucao_02_2018_Exame_Conhecimento_Previo.pdf": "http://colest.ime.ufba.br/wp-content/uploads/2019/03/Resolu%C3%A7%C3%A3o-02_2018_Exame_Conhecimento_Previo.pdf",
    "Resolucao_03_2025_Atividades_Complementares_SIGAA.pdf": "https://colest.ime.ufba.br/wp-content/uploads/2026/10/Resolucao_03_2025_Atividades_Complementares_SIGAA_assinado.pdf",
    "Resolucao_05_2024_TCC_Estatistica.pdf": "https://colest.ime.ufba.br/wp-content/uploads/2025/01/Resolucao_05_2024_TCC.pdf",
    "Resolucoes_01_e_02_2020_Estagio_Nao_Obrigatorio_IME.pdf": "http://colest.ime.ufba.br/wp-content/uploads/2021/01/Resolucoes_01_e_02_2020_Estagio_nao_obrigatorio_IME.pdf",
    "Projeto_Pedagogico_Matematica_Diurno.pdf": "https://colmat.ufba.br/sites/colmat.ufba.br/files/ppc_matematica_diurno_2006.pdf",
    "Regimento_Interno_Colegiado_Matematica.pdf": "https://colmat.ufba.br/",
    "Resolucao_Atividades_Complementares_Matematica.pdf": "https://colmat.ufba.br/",
    "Resolucao_Estagio_Supervisionado_Bacharelado_Matematica.pdf": "https://colmat.ufba.br/",
    "Projeto_Pedagogico_Matematica_Diurno_Licenciatura.pdf": "https://colmat.ufba.br/sites/colmat.ufba.br/files/ppc_matematica_diurno_2006.pdf",
    "Projeto_Pedagogico_Matematica_Noturno_Licenciatura.pdf": "https://colmat.ufba.br/sites/colmat.ufba.br/files/ppc_matematica_noturno_2009_0.pdf",
    "Resolucao_Estagio_Supervisionado_Licenciatura_Matematica.pdf": "https://colmat.ufba.br/",
}

class PageChunkSpec(BaseModel):
    intervalo_paginas: List[int] = Field(
        description="Array com 1 número se página individual [1] ou 2 números [início, fim] se intervalo [2, 5] (1-indexado)."
    )
    resumo: str = Field(
        description="Fichamento/resumo detalhado e objetivo deste intervalo de páginas, com no máximo 800 tokens, detalhando normas, artigos, regras e procedimentos."
    )

class DocumentSlicingOutput(BaseModel):
    chunks: List[PageChunkSpec] = Field(
        description="Divisão sequencial e contígua de todas as páginas do documento, cobrindo da página 1 até a última página sem lacunas."
    )

def clean_doc_folder(doc_folder: Path):
    doc_folder.mkdir(parents=True, exist_ok=True)
    for item in doc_folder.iterdir():
        if item.is_file() and (item.suffix == ".txt" or item.suffix == ".json"):
            try:
                item.unlink()
            except Exception:
                pass

def slice_pdf(pdf_path: Path, start_page: int, end_page: int, out_path: Path):
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    start_idx = max(0, start_page - 1)
    end_idx = min(len(reader.pages), end_page)
    for i in range(start_idx, end_idx):
        writer.add_page(reader.pages[i])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f_out:
        writer.write(f_out)

def call_pre_llm_with_fallback(client: genai.Client, uploaded_file: Any, prompt: str, stats: Dict[str, Any]) -> str:
    """Tenta chamar o gemini-3.5-flash-lite com retentativas e recua para gemini-3.1-flash-lite em caso de 503/429."""
    models_to_try = ["models/gemini-3.5-flash-lite", "models/gemini-3.1-flash-lite"]
    last_err = None
    for model_name in models_to_try:
        for attempt in range(3):
            try:
                resp = client.models.generate_content(
                    model=model_name,
                    contents=[uploaded_file, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=DocumentSlicingOutput,
                        temperature=0.2,
                    )
                )
                if resp and resp.text:
                    in_tok = getattr(resp.usage_metadata, "prompt_token_count", 0)
                    out_tok = getattr(resp.usage_metadata, "candidates_token_count", 0)
                    stats["pre_llm_input_tokens"] += in_tok
                    stats["pre_llm_output_tokens"] += out_tok
                    return resp.text
            except Exception as e:
                last_err = e
                print(f"       [Tentativa {attempt+1}] {model_name} erro: {e}")
                time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"Falha em todos os modelos para fatiamento: {last_err}")

def process_document(client: genai.Client, course_name: str, pdf_path: Path, stats: Dict[str, Any]) -> List[Dict[str, Any]]:
    doc_stem = pdf_path.stem
    doc_filename = pdf_path.name
    doc_url = DOC_LINKS.get(doc_filename, "https://ufba.br/")
    
    print(f"\n---> Processando: {course_name} / {doc_filename}")
    reader = PdfReader(str(pdf_path))
    total_pages = len(reader.pages)
    print(f"     Total de páginas: {total_pages}")
    
    # Upload do documento via API File
    uploaded_file = client.files.upload(file=pdf_path)
    print(f"     Upload API File concluído: {uploaded_file.name}")
    
    prompt = f"""Você é um especialista em análise regulatória universitária da UFBA.
Analise visual e textualmente este documento oficial em PDF com um total de {total_pages} página(s).
Curso de referência: {course_name}
Nome do documento: {doc_filename}

Sua tarefa:
1. Determinar os intervalos de páginas ideais para cortar este documento em fatias (chunks) lógicas e coesas, considerando a densidade visual e textual de cada página.
- Documentos curtos (1 a 3 páginas) podem ter fatias de 1 a 2 páginas.
- Documentos longos devem agrupar páginas consecutivas por capítulos, seções regulatórias ou afinidade temática (intervalos de 2 a 5 páginas).
- Todos os intervalos devem ser contíguos e cobrir sequencialmente da página 1 até a página {total_pages} sem omitir nenhuma página. Exemplo: [[1], [2, 5], [6], [7, 10]].
2. Para cada intervalo de páginas, produza um fichamento/resumo detalhado e objetivo (no máximo 800 tokens).
- O fichamento deve detalhar explicitamente os artigos, normas, obrigações, prazos, fluxos, diretrizes curriculares e procedimentos específicos presentes naquele intervalo.
- Seja extremamente fiel e abrangente para permitir recuperação semântica de alta precisão.
"""

    resp_text = call_pre_llm_with_fallback(client, uploaded_file, prompt, stats)
    
    # Remover arquivo temporário da API File
    try:
        client.files.delete(name=uploaded_file.name)
    except Exception:
        pass
        
    slicing_data = json.loads(resp_text)
    chunks_spec = slicing_data.get("chunks", [])
    
    if not chunks_spec:
        chunks_spec = [{
            "intervalo_paginas": [1, total_pages] if total_pages > 1 else [1],
            "resumo": f"Documento {doc_stem} na íntegra cobrindo páginas 1 a {total_pages}."
        }]
        
    doc_folder = pdf_path.parent / doc_stem
    clean_doc_folder(doc_folder)
    
    rows = []
    for chunk in chunks_spec:
        intervalo = chunk.get("intervalo_paginas", [1])
        start_p = intervalo[0]
        end_p = intervalo[-1] if len(intervalo) > 1 else start_p
        
        sliced_pdf_name = f"{doc_stem}_paginas_{start_p}-{end_p}.pdf"
        sliced_pdf_path = doc_folder / sliced_pdf_name
        
        slice_pdf(pdf_path, start_p, end_p, sliced_pdf_path)
        resumo_texto = chunk.get("resumo", "").strip()
        
        # Contagem de tokens
        c_tok = client.models.count_tokens(
            model="models/gemini-3.5-flash-lite",
            contents=resumo_texto
        )
        token_count = c_tok.total_tokens
        
        # Embedding com gemini-embedding-2
        emb_res = client.models.embed_content(
            model="models/gemini-embedding-2",
            contents=resumo_texto
        )
        embedding_vec = emb_res.embeddings[0].values
        stats["embedding_tokens"] += token_count
        
        paginas_str = f"[{start_p}]" if start_p == end_p else f"[{start_p}, {end_p}]"
        
        row = {
            "curso": course_name,
            "nome do documento": doc_stem,
            "link para acessar o documento": doc_url,
            "páginas": paginas_str,
            "fichamento/resumo": resumo_texto,
            "quantidade de tokens": token_count,
            "embedding": embedding_vec,
            "pdf_chunk_path": str(sliced_pdf_path.relative_to(BASE_DIR)).replace("\\", "/")
        }
        rows.append(row)
        print(f"       + Fatia [{start_p}-{end_p}]: {sliced_pdf_name} ({token_count} tokens fichamento)")
        
    time.sleep(1) # Intervalo preventivo de taxa
    return rows

def build_vector_store():
    print("=" * 70)
    print("INICIANDO CONSTRUÇÃO DO BANCO VETORIAL PRÓPRIO (SINFORM AI)")
    print("=" * 70)
    
    client = genai.Client()
    stats = {
        "pre_llm_input_tokens": 0,
        "pre_llm_output_tokens": 0,
        "embedding_tokens": 0,
        "total_documents": 0,
        "total_chunks": 0
    }
    
    for course in COURSES:
        course_dir = BASE_DIR / course
        if not course_dir.exists():
            print(f"Diretório não encontrado: {course_dir}")
            continue
            
        print(f"\n=======================================================")
        print(f"CURSO: {course}")
        print(f"=======================================================")
        
        banco_vetorial_dir = course_dir / "banco vetorial"
        banco_vetorial_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_file = banco_vetorial_dir / "checkpoint_rows.json"
        
        # Carregar checkpoint se existir
        processed_docs = set()
        course_rows = []
        if checkpoint_file.exists():
            try:
                with open(checkpoint_file, "r", encoding="utf-8") as f:
                    course_rows = json.load(f)
                    processed_docs = {r["nome do documento"] for r in course_rows}
                print(f"-> Checkpoint carregado: {len(processed_docs)} documentos já processados.")
            except Exception:
                course_rows = []
                processed_docs = set()
        
        pdf_files = sorted([f for f in course_dir.glob("*.pdf") if f.is_file()])
        print(f"Total de PDFs ativos para o curso: {len(pdf_files)}")
        
        for pdf_path in pdf_files:
            if pdf_path.stem in processed_docs:
                print(f"---> [Reutilizado Checkpoint]: {course} / {pdf_path.name}")
                stats["total_documents"] += 1
                continue
                
            try:
                doc_rows = process_document(client, course, pdf_path, stats)
                course_rows.extend(doc_rows)
                processed_docs.add(pdf_path.stem)
                stats["total_documents"] += 1
                stats["total_chunks"] += len(doc_rows)
                
                # Salvar checkpoint
                with open(checkpoint_file, "w", encoding="utf-8") as f:
                    json.dump(course_rows, f, ensure_ascii=False, indent=2)
                    
            except Exception as e:
                print(f"ERRO ao processar {pdf_path.name}: {e}")
                
        df = pd.DataFrame(course_rows)
        
        # Salvar Parquet
        parquet_path = banco_vetorial_dir / "banco_vetorial.parquet"
        df.to_parquet(parquet_path, index=False)
        print(f"\n-> Salvo Parquet: {parquet_path} ({len(df)} registros)")
        
        # Salvar JSON
        json_path = banco_vetorial_dir / "banco_vetorial.json"
        df.to_json(json_path, orient="records", indent=2, force_ascii=False)
        print(f"-> Salvo JSON: {json_path}")
        
    print("\n" + "=" * 70)
    print("RELATÓRIO CONSOLIDADO DE EXECUÇÃO E CUSTOS")
    print("=" * 70)
    print(f"Documentos processados: {stats['total_documents']}")
    print(f"Total de fatias (chunks) geradas: {stats['total_chunks']}")
    print(f"Tokens de Input Pre-LLM: {stats['pre_llm_input_tokens']}")
    print(f"Tokens de Output Pre-LLM: {stats['pre_llm_output_tokens']}")
    print(f"Tokens de Embedding: {stats['embedding_tokens']}")
    
    cost_pre_llm_in = (stats['pre_llm_input_tokens'] / 1_000_000) * PRICING["gemini-3.5-flash-lite"]["input_per_million"]
    cost_pre_llm_out = (stats['pre_llm_output_tokens'] / 1_000_000) * PRICING["gemini-3.5-flash-lite"]["output_per_million"]
    cost_embed = (stats['embedding_tokens'] / 1_000_000) * PRICING["gemini-embedding-2"]["input_per_million"]
    total_cost = cost_pre_llm_in + cost_pre_llm_out + cost_embed
    
    print("-" * 70)
    print(f"Custo Pre-LLM Input:  ${cost_pre_llm_in:.6f} USD")
    print(f"Custo Pre-LLM Output: ${cost_pre_llm_out:.6f} USD")
    print(f"Custo Embeddings:     ${cost_embed:.6f} USD")
    print(f"CUSTO TOTAL DE INDEXAÇÃO: ${total_cost:.6f} USD (~ R$ {total_cost * 5.75:.4f})")
    print("=" * 70)

if __name__ == "__main__":
    build_vector_store()
