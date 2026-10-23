"""
Pré-LLM Multimodal: Análise de Documentos PDF via Google GenAI SDK (Files API)
Analisa a densidade visual e estrutura de capítulos, seções e parágrafos de cada PDF oficial,
retornando output estruturado com:
- header padrão: | Curso | Documento (Nome do documento) |
- max_tokens_per_chunk
- max_tokens_overlap
- análise de densidade visual
- justificativa técnica
Modelos com fallback automático: Gemini 3.5 Flash Lite -> Gemini 3.1 Flash Lite
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY não foi encontrada no arquivo .env!")

from google import genai
from google.genai import types

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
from cost_estimator import CostEstimator

# Esquema de Output Estruturado conforme especificado no Plano de Implementação
class PreLLMDocumentAnalysis(BaseModel):
    header: str = Field(
        description="Cabeçalho padrão no formato exato: | Curso | Documento (Nome do documento limpo) |"
    )
    max_tokens_per_chunk: int = Field(
        description="Quantidade ideal de tokens por chunk para este documento específico"
    )
    max_tokens_overlap: int = Field(
        description="Quantidade ideal de tokens de sobreposição (overlap)"
    )
    densidade_visual: str = Field(
        description="Avaliação da densidade visual do PDF analisando artigos, parágrafos e tabelas"
    )
    justificativa_chunking: str = Field(
        description="Breve explicação técnica analisando a estrutura visual, artigos e tabelas do PDF"
    )

class PreLLMAnalyzer:
    def __init__(self, api_key: str = api_key):
        self.client = genai.Client(api_key=api_key)
        self.primary_model = "gemini-3.5-flash-lite"
        self.fallback_model = "gemini-3.1-flash-lite"

    def analyze_pdf(self, pdf_path: Path, curso_nome: str) -> Dict[str, Any]:
        """
        Faz o upload multimodal do PDF via Files API e solicita a análise estruturada
        ao Pré-LLM (Gemini 3.5 Flash Lite com fallback para 3.1 Flash Lite).
        """
        doc_clean_name = pdf_path.stem.replace("_", " ")
        print(f"\n[Pré-LLM] Analisando PDF: {pdf_path.name} ({curso_nome})...")
        
        # 1. Upload via Files API
        print(f"[Pré-LLM] Fazendo upload do PDF para API File...")
        uploaded_file = self.client.files.upload(file=str(pdf_path))
        
        # Aguardar processamento se necessário
        while uploaded_file.state.name == "PROCESSING":
            time.sleep(2)
            uploaded_file = self.client.files.get(name=uploaded_file.name)
            
        if uploaded_file.state.name == "FAILED":
            raise RuntimeError(f"Falha no processamento do arquivo {pdf_path.name} na Files API.")

        prompt = f"""Você é o Pré-LLM de Visão Multimodal do sistema Sinform AI (UFBA).
Sua missão é inspecionar visualmente este documento acadêmico/regulamentar em PDF pertencente ao curso: '{curso_nome}'.

DOCUMENTO: {doc_clean_name}
CURSO: {curso_nome}

INSTRUÇÕES:
1. Examine a estrutura visual do documento: capítulos, seções, artigos, parágrafos, incisos, tabelas e notas de rodapé.
2. Defina com total liberdade a quantidade ideal de tokens por chunk (max_tokens_per_chunk) para este documento específico, de acordo com o tamanho médio e densidade de seus artigos e seções.
3. Defina a quantidade ideal de tokens de sobreposição (max_tokens_overlap) para este documento (menor que max_tokens_per_chunk) para preservar a continuidade das normas.
4. Formate o cabeçalho no padrão estrito:
   | {curso_nome} | Documento ({doc_clean_name}) |
5. Forneça a justificativa técnica objetiva para as escolhas de tokens deste documento específico.
"""

        models_chain = [self.primary_model, self.fallback_model]
        analysis_data = None
        model_used = None
        tokens_input = 0
        tokens_output = 0

        for model_name in models_chain:
            try:
                print(f"[Pré-LLM] Enviando para {model_name} com Output Estruturado...")
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=[uploaded_file, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=PreLLMDocumentAnalysis,
                        temperature=0.1
                    )
                )
                if response and response.text:
                    parsed = json.loads(response.text)
                    analysis_data = parsed
                    model_used = model_name
                    if hasattr(response, "usage_metadata") and response.usage_metadata:
                        tokens_input = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
                        tokens_output = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
                    break
            except Exception as e:
                print(f"[Pré-LLM Fallback] Falha no modelo {model_name}: {e}. Tentando próximo...")
                continue

        # Deletar arquivo temporário da nuvem para liberar armazenamento
        try:
            self.client.files.delete(name=uploaded_file.name)
        except Exception:
            pass

        if not analysis_data:
            # Fallback de segurança determinístico caso a API não responda
            print("[Pré-LLM] Aviso: Usando calibração padrão de segurança.")
            analysis_data = {
                "header": f"| {curso_nome} | Documento ({doc_clean_name}) |",
                "max_tokens_per_chunk": 600,
                "max_tokens_overlap": 80,
                "densidade_visual": "Média regulamentar",
                "justificativa_chunking": "Calibração padrão de segurança para artigos normativos."
            }
            model_used = "Fallback Local"

        # Garantir padrão estrito de cabeçalho
        expected_header = f"| {curso_nome} | Documento ({doc_clean_name}) |"
        if not analysis_data.get("header") or not analysis_data["header"].startswith("|"):
            analysis_data["header"] = expected_header

        cost = CostEstimator.calculate_cost(model_used, tokens_input, tokens_output)
        
        result = {
            "curso": curso_nome,
            "documento": pdf_path.name,
            "documento_nome": doc_clean_name,
            "caminho_pdf": str(pdf_path),
            "header": analysis_data["header"],
            "max_tokens_per_chunk": int(analysis_data["max_tokens_per_chunk"]),
            "max_tokens_overlap": int(analysis_data["max_tokens_overlap"]),
            "densidade_visual": analysis_data["densidade_visual"],
            "justificativa_chunking": analysis_data["justificativa_chunking"],
            "model_used": model_used,
            "input_tokens": tokens_input,
            "output_tokens": tokens_output,
            "cost_usd": cost
        }

        print(f"[Pré-LLM Sucesso] {pdf_path.name} -> Chunk Max: {result['max_tokens_per_chunk']} tokens, Overlap: {result['max_tokens_overlap']} tokens | Custo: ${cost:.6f} USD")
        return result

    def analyze_all_courses(self, base_dir: Path = BASE_DIR, force_recompute: bool = True) -> Dict[str, List[Dict[str, Any]]]:
        """
        Varre todas as pastas de cursos, executa a análise estruturada em cada PDF
        e salva um arquivo de configuração persistente `pre_llm_chunk_configs.json`.
        """
        import unicodedata
        def norm(s):
            return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()

        courses = [
            "Estatística (Bacharel)",
            "Matemática (Bacharel)",
            "Matemática (Licenciatura)"
        ]

        all_results = {}
        total_cost = 0.0

        for course in courses:
            target_norm = norm(course)
            course_dir = None
            for sub in base_dir.iterdir():
                if sub.is_dir() and norm(sub.name) == target_norm:
                    course_dir = sub
                    break

            if not course_dir or not course_dir.exists():
                print(f"[Aviso] Pasta para {course} nao encontrada.")
                continue

            # Apenas PDFs ativos (excluindo qualquer um em _desatualizados)
            pdf_files = sorted(list(course_dir.glob("*.pdf")))
            course_results = []
            print(f"\n=======================================================")
            print(f" Iniciando Pré-LLM para {course} ({len(pdf_files)} PDFs)")
            print(f"=======================================================")

            for pdf_file in pdf_files:
                doc_subfolder = course_dir / pdf_file.stem
                cache_file = doc_subfolder / "pre_llm_config.json"
                
                if not force_recompute and cache_file.exists():
                    try:
                        with open(cache_file, "r", encoding="utf-8") as f:
                            cached_res = json.load(f)
                            print(f"[Pré-LLM Cache] Carregado de cache: {pdf_file.name}")
                            course_results.append(cached_res)
                            continue
                    except Exception:
                        pass

                res = self.analyze_pdf(pdf_file, curso_nome=course)
                course_results.append(res)
                total_cost += res["cost_usd"]

                # Salvar na pasta do documento para rastreabilidade
                doc_subfolder.mkdir(parents=True, exist_ok=True)
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(res, f, ensure_ascii=False, indent=2)

                # Pequena pausa para respeitar cota de taxa (RPM)
                time.sleep(2)

            all_results[course] = course_results

        # Salvar compêndio geral de configurações
        compendium_path = base_dir / "pre_llm_chunk_configs.json"
        with open(compendium_path, "w", encoding="utf-8") as f:
            json.dump({
                "courses": all_results,
                "total_cost_usd": total_cost,
                "formatted_cost": CostEstimator.format_cost(total_cost)
            }, f, ensure_ascii=False, indent=2)

        print(f"\n[Pré-LLM Concluído] Todas as configurações salvas em: {compendium_path}")
        print(f"Custo total estimado da etapa Pré-LLM: ${total_cost:.4f} USD")
        return all_results

if __name__ == "__main__":
    analyzer = PreLLMAnalyzer()
    analyzer.analyze_all_courses()
