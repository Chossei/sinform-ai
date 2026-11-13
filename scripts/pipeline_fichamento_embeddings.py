"""
Pipeline de Fatiamento (Pré-LLM) e Geração de Embeddings - Sinform AI / UFBA
=============================================================================
Este script implementa:
1. Arquitetura Multi-Worker assíncrona/paralela com 1 Worker por chave gratuita a 15 RPM (4s de intervalo).
2. Fallback automático para gemini-3.1-flash-lite em caso de instabilidade.
3. Transição para a chave paga (GEMINI_PAGO_RICARDO) com inferência flexível quando as gratuitas esgotarem.
4. Rastreador de custos com interrupção estrita (STOP) ao atingir $2.00 USD na chave paga.
5. Cache Global de Conteúdo por SHA-256 (cache_global_fichamentos.json) para evitar requisições repetidas.
6. Geração dos arquivos finais por curso:
   - Fatias físicas de PDFs: [Curso]/[Nome_do_documento]/[Nome_do_documento]_paginas_x-x.pdf
   - Banco vetorial em DataFrame: [Curso]/banco vetorial/banco_vetorial.parquet
   - Banco vetorial legível em JSON: [Curso]/banco vetorial/banco_vetorial.json
"""

import os
import sys
import json
import time
import queue
import hashlib
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
from pypdf import PdfReader, PdfWriter
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

# ==============================================================================
# 1. SEÇÃO DE CONFIGURAÇÃO E ENGENHARIA DE PROMPT (FÁCIL CUSTOMIZAÇÃO)
# ==============================================================================

# Modelos do Pré-LLM (Slicing e Fichamento)
PRIMARY_MODEL = "models/gemini-3.5-flash-lite"
FALLBACK_MODEL = "models/gemini-3.1-flash-lite"

# Modelo de Embeddings
EMBEDDING_MODEL = "models/gemini-embedding-2"

# Parâmetros de Inferência e Limite Financeiro
PAID_COST_CAP_USD = 2.00        # Limite máximo de custo na chave paga
RPM_LIMIT_PER_FREE_KEY = 15     # Limite de requisições por minuto por chave gratuita
MIN_INTERVAL_SECONDS = 60.0 / RPM_LIMIT_PER_FREE_KEY  # 4.0 segundos por worker

# Tabela de Preços (USD por milhão de tokens) - Inferência Flexível (50% de desconto)
PRICING_FLEX = {
    "gemini-3.5-flash-lite": {
        "input_per_million": 0.15,   # Flex: metade de 0.30
        "output_per_million": 1.25   # Flex: metade de 2.50
    },
    "gemini-3.1-flash-lite": {
        "input_per_million": 0.125,  # Flex: metade de 0.25
        "output_per_million": 0.75   # Flex: metade de 1.50
    },
    "gemini-embedding-2": {
        "input_per_million": 0.10    # Flex: metade de 0.20
    }
}

# Prompt do Pré-LLM para Análise Multimodal e Fichamento Regulamentar
def get_pre_llm_prompt(course_name: str, doc_filename: str, total_pages: int) -> str:
    """
    Retorna o prompt estruturado enviado ao Pré-LLM junto com o PDF via Files API.
    Edite este prompt livremente para ajustar a engenharia de prompt do modelo.
    """
    return f"""Você é um especialista em análise regulatória universitária da Universidade Federal da Bahia (UFBA).
Analise visual e textualmente este documento oficial em PDF que possui um total de {total_pages} página(s).

CURSO DE REFERÊNCIA: {course_name}
DOCUMENTO: {doc_filename}

SUA MISSÃO:
1. FATIAMENTO LÓGICO E COESO:
   - Avalie a densidade visual e textual das páginas (capítulos, seções, artigos, tabelas, resoluções).
   - Divida o documento em intervalos contíguos de páginas (chunks).
   - Documentos curtos (1 a 3 páginas): fatias de 1 página ou 1 a 2 páginas.
   - Documentos médios ou longos: agrupar por capítulos ou tópicos regulamentares (geralmente 2 a 5 páginas).
   - OBRIGATÓRIO: Os intervalos devem ser sequenciais e cobrir da página 1 até a página {total_pages} sem lacunas e sem repetições. Exemplo: [[1], [2, 5], [6, 10]].

2. FICHAMENTO REGULAMENTAR DE ALTA PRECISÃO (máx. 800 tokens por fatia):
   - Para cada intervalo de páginas, elabore um resumo/fichamento altamente descritivo e objetivo.
   - Cite explicitamente artigos, parágrafos, prazos acadêmicos, percentuais de carga horária, regras de jubilamento, condições de estágio, TCC, trancamento e colegiados.
   - Não use termos vagos. Preserve a terminologia técnica do documento.
"""

# Esquema de Saída Estruturada do Fatiamento
class PageChunkSpec(BaseModel):
    intervalo_paginas: List[int] = Field(
        description="Array com 1 número para página única [1] ou 2 números [início, fim] para intervalos [2, 5] (1-indexado)."
    )
    resumo: str = Field(
        description="Fichamento detalhado e objetivo cobrindo todas as normas, artigos e prazos do intervalo (máximo 800 tokens)."
    )

class DocumentSlicingOutput(BaseModel):
    chunks: List[PageChunkSpec] = Field(
        description="Divisão contígua e sequencial de todas as páginas do documento, da página 1 até a última página."
    )

# ==============================================================================
# 2. GERENCIAMENTO DE CAMINHOS E SUPORTE A NOMES LONGOS NO WINDOWS
# ==============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
AREAS_DIR = BASE_DIR / "Experimento" / "Áreas do conhecimento"
GLOBAL_CACHE_FILE = BASE_DIR / "Experimento" / "cache_global_fichamentos.json"

def to_win_long_path(p: Path) -> Path:
    """Resolve caminhos longos no Windows (>260 caracteres) adicionando o prefixo \\\\?\\ se necessário."""
    s = str(p.resolve())
    if os.name == "nt" and not s.startswith("\\\\?\\") and not s.startswith("\\\\"):
        return Path("\\\\?\\" + s)
    return Path(s)

def compute_pdf_hash(pdf_path: Path) -> str:
    """Calcula o hash SHA-256 do arquivo PDF para cache global."""
    long_p = to_win_long_path(pdf_path)
    data = long_p.read_bytes()
    return hashlib.sha256(data).hexdigest()

def slice_pdf_file(src_pdf: Path, start_p: int, end_p: int, out_pdf: Path):
    """Extrai fisicamente as páginas especificadas de src_pdf para out_pdf."""
    long_src = to_win_long_path(src_pdf)
    long_out = to_win_long_path(out_pdf)
    long_out.parent.mkdir(parents=True, exist_ok=True)
    
    reader = PdfReader(str(long_src))
    writer = PdfWriter()
    start_idx = max(0, start_p - 1)
    end_idx = min(len(reader.pages), end_p)
    for i in range(start_idx, end_idx):
        writer.add_page(reader.pages[i])
    with open(long_out, "wb") as f_out:
        writer.write(f_out)

# ==============================================================================
# 3. GERENCIADOR DE CHAVES, RATE LIMITER E CONTROLE DE CUSTOS
# ==============================================================================

class CostAndQuotaTracker:
    def __init__(self, cost_cap_usd: float = PAID_COST_CAP_USD):
        self.cost_cap_usd = cost_cap_usd
        self.paid_cost_usd = 0.0
        self.paid_in_tokens = 0
        self.paid_out_tokens = 0
        self.paid_emb_tokens = 0
        self.free_in_tokens = 0
        self.free_out_tokens = 0
        self.free_emb_tokens = 0
        self.lock = threading.Lock()
        self.stop_requested = False

    def add_paid_usage(self, model: str, in_tok: int, out_tok: int, emb_tok: int = 0):
        with self.lock:
            self.paid_in_tokens += in_tok
            self.paid_out_tokens += out_tok
            self.paid_emb_tokens += emb_tok
            
            # Cálculo de custo proporcional
            cost = 0.0
            if "embedding" in model:
                rates = PRICING_FLEX["gemini-embedding-2"]
                cost += (emb_tok / 1_000_000.0) * rates["input_per_million"]
            elif "3.5" in model:
                rates = PRICING_FLEX["gemini-3.5-flash-lite"]
                cost += (in_tok / 1_000_000.0) * rates["input_per_million"]
                cost += (out_tok / 1_000_000.0) * rates["output_per_million"]
            elif "3.1" in model:
                rates = PRICING_FLEX["gemini-3.1-flash-lite"]
                cost += (in_tok / 1_000_000.0) * rates["input_per_million"]
                cost += (out_tok / 1_000_000.0) * rates["output_per_million"]
            
            self.paid_cost_usd += cost
            if self.paid_cost_usd >= self.cost_cap_usd:
                self.stop_requested = True
                print(f"\n[ALERTA ORÇAMENTÁRIO] Limite de ${self.cost_cap_usd:.2f} atingido na chave paga! Custo atual: ${self.paid_cost_usd:.4f}")

    def add_free_usage(self, in_tok: int, out_tok: int, emb_tok: int = 0):
        with self.lock:
            self.free_in_tokens += in_tok
            self.free_out_tokens += out_tok
            self.free_emb_tokens += emb_tok

class KeyManager:
    def __init__(self):
        # Localiza todas as chaves gratuitas do ambiente
        self.free_keys: List[str] = []
        for k, v in os.environ.items():
            if k == "GEMINI_API_KEY" or k.startswith("GEMINI_API_KEY_") or k.startswith("GEMINI_FREE_"):
                if v and v.strip() and v not in self.free_keys:
                    self.free_keys.append(v.strip())
        
        self.paid_key: Optional[str] = os.getenv("GEMINI_PAGO_RICARDO")
        self.exhausted_free_keys = set()
        self.lock = threading.Lock()
        
        print(f"[KeyManager] Chaves gratuitas detectadas: {len(self.free_keys)}")
        print(f"[KeyManager] Chave paga disponível: {'SIM' if self.paid_key else 'NÃO'}")

    def mark_free_key_exhausted(self, key: str):
        with self.lock:
            self.exhausted_free_keys.add(key)
            print(f"[KeyManager] Chave gratuita {key[:6]}... esgotou cota diária (429/ResourceExhausted). Restantes: {len(self.free_keys) - len(self.exhausted_free_keys)}")

    def get_available_key(self) -> (str, bool):
        """Retorna (api_key, is_paid). Se nenhuma gratuita estiver livre, retorna a paga."""
        with self.lock:
            for k in self.free_keys:
                if k not in self.exhausted_free_keys:
                    return k, False
            if self.paid_key:
                return self.paid_key, True
            raise RuntimeError("Todas as chaves gratuitas estão esgotadas e nenhuma chave paga está configurada!")

# ==============================================================================
# 4. CACHE GLOBAL DE CONTEÚDO (SHA-256)
# ==============================================================================

class GlobalContentCache:
    def __init__(self, cache_file: Path = GLOBAL_CACHE_FILE):
        self.cache_file = cache_file
        self.data: Dict[str, Any] = {}
        self.lock = threading.Lock()
        self.load()

    def load(self):
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                print(f"[Cache Global] Carregados {len(self.data)} documentos do cache persistente.")
            except Exception as e:
                print(f"[Cache Global] Erro ao carregar cache: {e}. Iniciando vazio.")
                self.data = {}

    def save(self):
        with self.lock:
            try:
                self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.cache_file, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[Cache Global] Erro ao salvar cache: {e}")

    def get(self, file_hash: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            return self.data.get(file_hash)

    def set(self, file_hash: str, entry: Dict[str, Any]):
        with self.lock:
            self.data[file_hash] = entry
            self.save()

# ==============================================================================
# 5. EXECUÇÃO DE FATIAMENTO E EMBEDDINGS (ROBUSTO COM RETENTATIVAS)
# ==============================================================================

def analyze_pdf_with_pre_llm(
    client: genai.Client,
    pdf_path: Path,
    course_name: str,
    key_manager: KeyManager,
    api_key: str,
    is_paid: bool,
    tracker: CostAndQuotaTracker
) -> List[Dict[str, Any]]:
    """
    Realiza o upload do PDF na API File e chama o Pré-LLM para obter o fatiamento e resumos.
    """
    long_pdf = to_win_long_path(pdf_path)
    reader = PdfReader(str(long_pdf))
    total_pages = len(reader.pages)
    doc_stem = pdf_path.stem
    doc_filename = pdf_path.name
    
    # 1. Upload via Files API
    uploaded_file = client.files.upload(file=str(long_pdf))
    
    prompt = get_pre_llm_prompt(course_name, doc_filename, total_pages)
    models_chain = [PRIMARY_MODEL, FALLBACK_MODEL]
    
    resp_text = None
    model_used = None
    last_err = None
    
    for model_name in models_chain:
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
                    resp_text = resp.text
                    model_used = model_name
                    in_tok = getattr(resp.usage_metadata, "prompt_token_count", 0)
                    out_tok = getattr(resp.usage_metadata, "candidates_token_count", 0)
                    
                    if is_paid:
                        tracker.add_paid_usage(model_name, in_tok, out_tok)
                    else:
                        tracker.add_free_usage(in_tok, out_tok)
                    break
            except Exception as e:
                last_err = e
                err_msg = str(e).lower()
                if "429" in err_msg or "resource_exhausted" in err_msg:
                    if not is_paid:
                        key_manager.mark_free_key_exhausted(api_key)
                    raise e
                time.sleep(2 * (attempt + 1))
        if resp_text:
            break
            
    # Cleanup do arquivo temporário
    try:
        client.files.delete(name=uploaded_file.name)
    except Exception:
        pass
        
    if not resp_text:
        raise RuntimeError(f"Falha ao processar {doc_filename} em todos os modelos: {last_err}")
        
    slicing_data = json.loads(resp_text)
    chunks_spec = slicing_data.get("chunks", [])
    
    if not chunks_spec:
        chunks_spec = [{
            "intervalo_paginas": [1, total_pages] if total_pages > 1 else [1],
            "resumo": f"Documento oficial {doc_stem} na íntegra cobrindo páginas 1 a {total_pages}."
        }]
    return chunks_spec

def generate_chunk_embedding(
    client: genai.Client,
    text: str,
    is_paid: bool,
    tracker: CostAndQuotaTracker
) -> (int, List[float]):
    """Gera o embedding com gemini-embedding-2 e conta tokens."""
    c_tok = client.models.count_tokens(model=PRIMARY_MODEL, contents=text)
    token_count = c_tok.total_tokens
    
    emb_res = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text
    )
    vec = emb_res.embeddings[0].values
    
    if is_paid:
        tracker.add_paid_usage(EMBEDDING_MODEL, 0, 0, emb_tok=token_count)
    else:
        tracker.add_free_usage(0, 0, emb_tok=token_count)
        
    return token_count, vec

# ==============================================================================
# 6. PIPELINE PRINCIPAL DE PROCESSAMENTO POR CURSO
# ==============================================================================

def process_course(
    course_dir: Path,
    key_manager: KeyManager,
    cache: GlobalContentCache,
    tracker: CostAndQuotaTracker
):
    course_name = course_dir.name
    print(f"\n=======================================================")
    print(f"PROCESSANDO CURSO: {course_name}")
    print(f"=======================================================")
    
    banco_dir = course_dir / "banco vetorial"
    banco_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_file = banco_dir / "checkpoint_rows.json"
    
    course_rows = []
    processed_doc_stems = set()
    if checkpoint_file.exists():
        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                course_rows = json.load(f)
                processed_doc_stems = {r["nome do documento"] for r in course_rows}
            print(f"  [Checkpoint] {len(processed_doc_stems)} documento(s) já concluídos anteriormente.")
        except Exception:
            pass
            
    # PDFs raiz do curso
    pdf_files = [f for f in course_dir.glob("*.pdf") if f.is_file()]
    print(f"  Total de PDFs específicos a analisar: {len(pdf_files)}")
    
    for pdf_path in pdf_files:
        if tracker.stop_requested:
            print("[STOP] Interrupção solicitada pelo controle de custos.")
            break
            
        doc_stem = pdf_path.stem
        if doc_stem in processed_doc_stems:
            print(f"  [Pular] {doc_stem} já processado no checkpoint.")
            continue
            
        file_hash = compute_pdf_hash(pdf_path)
        doc_folder = course_dir / doc_stem
        doc_folder.mkdir(parents=True, exist_ok=True)
        
        # 1. Verificar no Cache Global de Conteúdo
        cached_entry = cache.get(file_hash)
        if cached_entry:
            print(f"  [CACHE GLOBAL HIT] {pdf_path.name} (Hash: {file_hash[:8]}...) - Reutilizando fatiamento e embeddings!")
            chunks_spec = cached_entry["chunks_spec"]
        else:
            print(f"  [CACHE MISS] {pdf_path.name} (Hash: {file_hash[:8]}...) - Analisando com Pré-LLM...")
            
            # Obter chave ativa
            api_key, is_paid = key_manager.get_available_key()
            client = genai.Client(api_key=api_key)
            
            # Respeitar rate limit (4s para free)
            if not is_paid:
                time.sleep(MIN_INTERVAL_SECONDS)
                
            chunks_spec = analyze_pdf_with_pre_llm(
                client=client,
                pdf_path=pdf_path,
                course_name=course_name,
                key_manager=key_manager,
                api_key=api_key,
                is_paid=is_paid,
                tracker=tracker
            )
            
            # Pré-computar embeddings para salvar no cache
            cached_chunks = []
            for ch in chunks_spec:
                resumo = ch.get("resumo", "").strip()
                t_count, vec = generate_chunk_embedding(client, resumo, is_paid, tracker)
                cached_chunks.append({
                    "intervalo_paginas": ch.get("intervalo_paginas", [1]),
                    "resumo": resumo,
                    "token_count": t_count,
                    "embedding": vec
                })
            
            cache.set(file_hash, {"chunks_spec": cached_chunks})
            chunks_spec = cached_chunks
            
        # 2. Materializar fatias físicas de PDFs e alimentar DataFrame
        for chunk in chunks_spec:
            intervalo = chunk.get("intervalo_paginas", [1])
            start_p = intervalo[0]
            end_p = intervalo[-1] if len(intervalo) > 1 else start_p
            
            sliced_pdf_name = f"{doc_stem}_paginas_{start_p}-{end_p}.pdf"
            sliced_pdf_path = doc_folder / sliced_pdf_name
            
            # Extração física
            slice_pdf_file(pdf_path, start_p, end_p, sliced_pdf_path)
            
            resumo_texto = chunk.get("resumo", "").strip()
            token_count = chunk.get("token_count", 0)
            embedding_vec = chunk.get("embedding", [])
            
            paginas_str = f"[{start_p}]" if start_p == end_p else f"[{start_p}, {end_p}]"
            rel_slice_path = str(sliced_pdf_path.relative_to(BASE_DIR)).replace("\\", "/")
            
            row = {
                "curso": course_name,
                "nome do documento": doc_stem,
                "link para acessar o documento": f"https://ufba.br/experimento/{course_name}/{doc_stem}",
                "páginas": paginas_str,
                "fichamento/resumo": resumo_texto,
                "quantidade de tokens": token_count,
                "embedding": embedding_vec,
                "pdf_chunk_path": rel_slice_path
            }
            course_rows.append(row)
            
        # Salvar checkpoint
        with open(checkpoint_file, "w", encoding="utf-8") as f_chk:
            json.dump(course_rows, f_chk, ensure_ascii=False, indent=2)
            
    # Salvar Parquet e JSON final do curso
    if course_rows:
        df = pd.DataFrame(course_rows)
        parquet_path = banco_dir / "banco_vetorial.parquet"
        json_path = banco_dir / "banco_vetorial.json"
        
        to_win_long_path(parquet_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(str(to_win_long_path(parquet_path)), index=False)
        
        with open(to_win_long_path(json_path), "w", encoding="utf-8") as f_j:
            json.dump(course_rows, f_j, ensure_ascii=False, indent=2)
            
        print(f"  [OK] Banco vetorial salvo com sucesso: {len(course_rows)} chunks registrados!")

# ==============================================================================
# 7. ENTRADA PRINCIPAL (MAIN)
# ==============================================================================

def main():
    print("=" * 80)
    print("PIPELINE DE FATIAMENTO E EMBEDDINGS - SINFORM AI")
    print("=" * 80)
    
    key_manager = KeyManager()
    cache = GlobalContentCache()
    tracker = CostAndQuotaTracker(cost_cap_usd=PAID_COST_CAP_USD)
    
    # Coletar todas as pastas de cursos nas 8 áreas de conhecimento
    all_courses = []
    for area_dir in sorted(AREAS_DIR.iterdir()):
        if area_dir.is_dir() and area_dir.name != "UFBA - Geral":
            for course_dir in sorted(area_dir.iterdir()):
                if course_dir.is_dir():
                    all_courses.append(course_dir)
                    
    total_courses = len(all_courses)
    print(f"\nTotal de cursos a processar: {total_courses}")
    
    processed_count = 0
    for idx, c_dir in enumerate(all_courses, start=1):
        if tracker.stop_requested:
            print("\n" + "!" * 80)
            print(f"[PARADA OBRIGATÓRIA] Custo pago atingiu ${tracker.paid_cost_usd:.4f} (Limite: ${PAID_COST_CAP_USD:.2f})!")
            pct = (processed_count / total_courses) * 100.0
            print(f"Progresso concluído: {processed_count}/{total_courses} cursos ({pct:.1f}%)")
            print("!" * 80)
            break
            
        process_course(c_dir, key_manager, cache, tracker)
        processed_count += 1
        
    print("\n" + "=" * 80)
    print("RELATÓRIO FINAL DE EXECUÇÃO:")
    print(f" - Cursos processados: {processed_count}/{total_courses} ({(processed_count/total_courses)*100:.1f}%)")
    print(f" - Custo acumulado na chave paga: ${tracker.paid_cost_usd:.4f} USD")
    print(f" - Tokens gratuitos consumidos: Input={tracker.free_in_tokens:,} | Output={tracker.free_out_tokens:,} | Embeddings={tracker.free_emb_tokens:,}")
    print(f" - Tokens pagos consumidos: Input={tracker.paid_in_tokens:,} | Output={tracker.paid_out_tokens:,} | Embeddings={tracker.paid_emb_tokens:,}")
    print("=" * 80)

if __name__ == "__main__":
    # NÃO EXECUTAR AUTOMATICAMENTE SEM AUTORIZAÇÃO EXPRESSA DO USUÁRIO
    print("Módulo carregado com sucesso. Para executar, aguarde o comando 'prossiga' do usuário.")

