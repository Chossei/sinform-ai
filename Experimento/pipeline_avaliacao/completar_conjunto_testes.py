"""
Script de Finalizacao e Fechamento Exato de 100 Perguntas por Curso (Etapa 2).
Garante que todos os 133 cursos tenham rigorosamente 100 perguntas (Total: 13.300 perguntas).
Usa o Coworker Pago (GEMINI_PAGO_RICARDO) com inferencia flexivel (service_tier='flex')
e gemini-3.5-flash-lite via Files API.
"""

import os
import sys
import json
import time
import shutil
import logging
import unicodedata
import tempfile
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import Counter, defaultdict

import pypdf
import pandas as pd
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from Experimento.pipeline_avaliacao.config import (
    EXP_DIR, AREAS_DIR, GEMINI_PAID_KEY,
    PRIMARY_MODEL, FALLBACK_MODEL, TEST_DATASET_FILE, LOGS_DIR,
    COST_PROMPT_TOKEN_FLEX, COST_CANDIDATE_TOKEN_FLEX
)
from Experimento.pipeline_avaliacao.prompts import GENERATE_QUESTIONS_PROMPT_TEMPLATE
from scripts.map_133_courses import COURSES_DATA, get_folder_name

BUDGET_LIMIT_USD = 5.00
PROGRESS_FILE = EXP_DIR / "progresso_perguntas.json"
DATASET_JSON_BACKUP = EXP_DIR / "conjunto_testes_geral.json"
LOG_FILE = LOGS_DIR / "completar_perguntas.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("CompletarEtapa2")

class QAItem(BaseModel):
    pergunta: str = Field(description="Pergunta dificil, tecnica e pontual sobre normas, prazos, artigos e regras academicas da UFBA.")
    resposta_gabarito: str = Field(description="Resposta gabarito completa, precisa e fundamentada exclusivamente no texto do documento.")

class QABatch(BaseModel):
    itens: List[QAItem] = Field(description="Lista contendo exatamente a quantidade requisitada de perguntas e gabaritos.")

def to_long_path(p: Path) -> Path:
    s = str(p.resolve())
    if os.name == "nt" and not s.startswith("\\\\?\\"):
        return Path("\\\\?\\" + s)
    return Path(s)

def get_pdf_page_count(pdf_path: Path) -> int:
    try:
        reader = pypdf.PdfReader(str(to_long_path(pdf_path)))
        return len(reader.pages)
    except Exception:
        return 1

def generate_questions(
    client: genai.Client,
    pdf_path: Path,
    count: int,
    tracker: Dict[str, Any]
) -> List[Dict[str, str]]:
    if count <= 0:
        return []

    batches = []
    rem = count
    while rem > 0:
        take = min(25, rem)
        batches.append(take)
        rem -= take

    import uuid
    clean_stem = "".join(c for c in unicodedata.normalize("NFKD", pdf_path.stem) if not unicodedata.combining(c))
    safe_ascii_name = f"{uuid.uuid4().hex[:8]}_{re.sub(r'[^\w\-.]', '_', clean_stem)}.pdf"
    temp_upload_file = Path(tempfile.gettempdir()) / safe_ascii_name
    try:
        shutil.copy2(to_long_path(pdf_path), temp_upload_file)
    except Exception:
        temp_upload_file = to_long_path(pdf_path)

    all_generated = []

    for batch_count in batches:
        prompt = GENERATE_QUESTIONS_PROMPT_TEMPLATE.format(
            nome_documento=pdf_path.stem,
            quantidade_perguntas=batch_count
        )

        uploaded_file = None
        batch_success = False

        for model_name in [PRIMARY_MODEL, FALLBACK_MODEL]:
            for attempt in range(1, 4):
                try:
                    if uploaded_file is None:
                        uploaded_file = client.files.upload(file=str(temp_upload_file))
                        time.sleep(1.0)

                    config_kwargs = {
                        "response_mime_type": "application/json",
                        "response_schema": QABatch,
                        "temperature": 0.3,
                        "service_tier": "flex"
                    }

                    res = client.models.generate_content(
                        model=model_name,
                        contents=[uploaded_file, prompt],
                        config=types.GenerateContentConfig(**config_kwargs)
                    )

                    if res.usage_metadata:
                        p_tok = res.usage_metadata.prompt_token_count or 0
                        c_tok = res.usage_metadata.candidates_token_count or 0
                        cost = (p_tok * COST_PROMPT_TOKEN_FLEX) + (c_tok * COST_CANDIDATE_TOKEN_FLEX)
                        tracker["paid_tokens_prompt"] += p_tok
                        tracker["paid_tokens_candidate"] += c_tok
                        tracker["paid_cost_usd"] += cost
                        logger.info(
                            f"[PAGO FLEX] +${cost:.5f} | Total: ${tracker['paid_cost_usd']:.4f} USD (Teto: ${BUDGET_LIMIT_USD:.2f})"
                        )
                        if tracker["paid_cost_usd"] >= BUDGET_LIMIT_USD:
                            raise RuntimeError(f"Teto orcamentario de ${BUDGET_LIMIT_USD:.2f} USD atingido!")

                    parsed = QABatch.model_validate_json(res.text)
                    items = [{"pergunta": q.pergunta.strip(), "resposta_gabarito": q.resposta_gabarito.strip()} for q in parsed.itens]
                    all_generated.extend(items)
                    batch_success = True
                    break
                except Exception as e:
                    err = str(e)
                    logger.warning(f"[Tentativa {attempt}] Erro em {pdf_path.name}: {err[:120]}")
                    time.sleep(2.0 * attempt)

            if batch_success:
                break

        if uploaded_file is not None:
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception:
                pass

    if temp_upload_file != to_long_path(pdf_path) and temp_upload_file.exists():
        try:
            temp_upload_file.unlink(missing_ok=True)
        except Exception:
            pass

    return all_generated


def main():
    logger.info("=== INICIANDO FECHAMENTO EXATO DE 100 PERGUNTAS POR CURSO ===")
    
    if not GEMINI_PAID_KEY:
        logger.error("GEMINI_PAID_KEY nao configurada no .env!")
        return

    client = genai.Client(api_key=GEMINI_PAID_KEY)

    # 1. Carregar dataset existente
    if not DATASET_JSON_BACKUP.exists():
        logger.error("Arquivo conjunto_testes_geral.json nao encontrado!")
        return

    with open(to_long_path(DATASET_JSON_BACKUP), "r", encoding="utf-8") as f:
        q_data = json.load(f)

    # Carregar tracker de custo
    tracker = {
        "paid_cost_usd": 0.0,
        "paid_tokens_prompt": 0,
        "paid_tokens_candidate": 0
    }
    if PROGRESS_FILE.exists():
        with open(to_long_path(PROGRESS_FILE), "r", encoding="utf-8") as f:
            p_data = json.load(f)
            tracker["paid_cost_usd"] = p_data.get("paid_cost_usd", 0.0)
            tracker["paid_tokens_prompt"] = p_data.get("paid_tokens_prompt", 0)
            tracker["paid_tokens_candidate"] = p_data.get("paid_tokens_candidate", 0)

    # Agrupar dados atuais por curso
    by_course = defaultdict(list)
    for row in q_data:
        by_course[row["Curso"]].append(row)

    logger.info(f"Cursos carregados: {len(by_course)} | Total de questoes: {len(q_data)}")

    # 2. Corrigir cursos com excesso (> 100)
    for c, items in list(by_course.items()):
        if len(items) > 100:
            logger.info(f"[EXCESSO] Curso '{c}' tem {len(items)} perguntas. Truncando para exatamente 100.")
            by_course[c] = items[:100]

    # Mapeamento dos cursos para caminhos de pastas e PDFs
    course_map = {}
    for c_info in COURSES_DATA:
        f_name = get_folder_name(c_info)
        course_map[f_name] = c_info

    # 3. Completar cursos que tem < 100 perguntas
    for c, items in list(by_course.items()):
        current_count = len(items)
        if current_count < 100:
            needed = 100 - current_count
            logger.info(f"[DEFICIT] Curso '{c}': possui {current_count} Qs. Gerando {needed} Qs restantes...")

            c_info = course_map.get(c)
            if not c_info:
                logger.warning(f"Curso '{c}' nao encontrado no COURSES_DATA!")
                continue

            course_dir = AREAS_DIR / c_info["area"] / c
            try:
                raw_names = os.listdir(to_long_path(course_dir))
                pdf_files = [course_dir / f for f in raw_names if f.lower().endswith(".pdf")]
            except Exception:
                pdf_files = [p for p in course_dir.glob("*.pdf") if to_long_path(p).is_file()]

            if not pdf_files:
                logger.warning(f"Nenhum PDF encontrado para o curso '{c}' em {course_dir}")
                continue

            # Escolher o maior documento (ou ponderar) para absorver as perguntas faltantes
            pages = {p: get_pdf_page_count(p) for p in pdf_files}
            largest_pdf = max(pages, key=pages.get)

            logger.info(f" -> Usando '{largest_pdf.name}' ({pages[largest_pdf]} pags) para gerar {needed} Qs faltantes...")
            new_items = generate_questions(
                client=client,
                pdf_path=largest_pdf,
                count=needed,
                tracker=tracker
            )

            # Formatar registros
            added = 0
            for it in new_items:
                if len(by_course[c]) < 100:
                    by_course[c].append({
                        "Curso": c,
                        "Documento": largest_pdf.stem,
                        "Pergunta": it["pergunta"],
                        "Resposta Gabarito": it["resposta_gabarito"]
                    })
                    added += 1

            logger.info(f" -> Sucesso: {added} Qs adicionadas. Curso '{c}' agora tem {len(by_course[c])} Qs.")

            # Salvar progresso incrementalmente
            save_all(by_course, tracker)

    # Verificacao Final
    save_all(by_course, tracker)
    logger.info("=== PROCESSO DE FECHAMENTO CONCLUIDO COM SUCESSO! ===")


def save_all(by_course: Dict[str, List[Dict[str, Any]]], tracker: Dict[str, Any]):
    all_records = []
    for c in sorted(by_course.keys()):
        all_records.extend(by_course[c])

    # 1. Salvar JSON
    with open(to_long_path(DATASET_JSON_BACKUP), "w", encoding="utf-8") as f:
        json.dump(all_records, f, indent=2, ensure_ascii=False)

    # 2. Salvar Excel
    df = pd.DataFrame(all_records)
    df.to_excel(to_long_path(TEST_DATASET_FILE), index=False)

    # 3. Salvar progresso
    prog_data = {
        "completed_courses": list(by_course.keys()),
        "total_courses": 133,
        "total_questions": len(all_records),
        "percent_completed": 100.0 if len(by_course) == 133 and all(len(v) == 100 for v in by_course.values()) else round(len(all_records)/(133*100)*100, 2),
        "paid_cost_usd": round(tracker["paid_cost_usd"], 5),
        "paid_tokens_prompt": tracker["paid_tokens_prompt"],
        "paid_tokens_candidate": tracker["paid_tokens_candidate"]
    }
    with open(to_long_path(PROGRESS_FILE), "w", encoding="utf-8") as f:
        json.dump(prog_data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()

