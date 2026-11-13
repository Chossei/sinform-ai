"""
===============================================================================
ORQUESTRADOR DO PIPELINE DE AVALIAÇÃO DOS RAGs — UFBA (133 CURSOS)
===============================================================================
Permite executar cada etapa individualmente ou de forma encadeada:
  1. Fatiamento Pré-LLM e geração do Banco Vetorial
  2. Geração proporcional do Conjunto de Testes (100 perguntas por curso)
  3. Execução dos 4 métodos de RAG (Tradicional, Fichamento Emb, Fichamento JEV, RAG JEV)
  4. Julgamento automatizado com TypeSafe JEV 1.14 (4 categorias qualitativas)

Uso via linha de comando:
  python run_pipeline.py --status
  python run_pipeline.py --stage 1 --course "Estatística (Bacharel)"
  python run_pipeline.py --stage 2 --course "Estatística (Bacharel)"
  python run_pipeline.py --stage 3 --course "Estatística (Bacharel)"
  python run_pipeline.py --stage 4 --dataset "Experimento/Conjunto de Testes.xlsx"
  python run_pipeline.py --all --course "Estatística (Bacharel)"
===============================================================================
"""

import sys
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from scripts.map_133_courses import COURSES_DATA, AREAS_CONHECIMENTO, get_folder_name
from Experimento.pipeline_avaliacao.config import TEST_DATASET_FILE, AREAS_DIR, GERAL_DIR


def show_status():
    print("=" * 80)
    print("STATUS DA BASE DE DADOS E DO PIPELINE — 133 CURSOS DA UFBA")
    print("=" * 80)

    total_courses = len(COURSES_DATA)
    total_pdfs = 0
    courses_with_bv = 0

    for area in AREAS_CONHECIMENTO:
        courses_in_area = [c for c in COURSES_DATA if c["area"] == area]
        area_pdfs = 0
        area_bv = 0

        for c in courses_in_area:
            f_name = get_folder_name(c)
            c_dir = AREAS_DIR / area / f_name
            pdfs = list(c_dir.glob("*.pdf")) if c_dir.exists() else []
            area_pdfs += len(pdfs)
            bv_pq = c_dir / "banco vetorial" / "banco_vetorial.parquet"
            if bv_pq.exists():
                area_bv += 1

        total_pdfs += area_pdfs
        courses_with_bv += area_bv
        print(f"[{area}]: {len(courses_in_area)} cursos | {area_pdfs} PDFs | {area_bv} bancos vetoriais prontos")

    # UFBA - Geral
    geral_pdfs = len(list(GERAL_DIR.glob("*.pdf"))) if GERAL_DIR.exists() else 0
    total_pdfs += geral_pdfs
    print(f"[UFBA - Geral]: {geral_pdfs} PDFs normativos gerais")

    print("-" * 80)
    print(f"TOTAL GERAL: {total_courses} cursos | {total_pdfs} PDFs baixados | {courses_with_bv}/{total_courses} bancos vetoriais gerados")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Orquestrador do Pipeline de Avaliação dos RAGs (UFBA)")
    parser.add_argument("--status", action="store_true", help="Exibe o status atual de PDFs e bancos vetoriais.")
    parser.add_argument("--stage", type=int, choices=[1, 2, 3, 4], help="Executa uma etapa específica (1, 2, 3 ou 4).")
    parser.add_argument("--all", action="store_true", help="Executa todas as etapas em sequência.")
    parser.add_argument("--course", type=str, help="Nome do curso para processamento (ex: 'Estatística (Bacharel)').")
    parser.add_argument("--dataset", type=str, help="Caminho do arquivo de dataset para o estágio 4 (default: TEST_DATASET_FILE).")

    args = parser.parse_args()

    if args.status or len(sys.argv) == 1:
        show_status()
        return

    # Execução das etapas
    if args.stage == 1 or args.all:
        print("\n>>> INICIANDO ETAPA 1: Fatiamento Pré-LLM...")
        import importlib
        s1 = importlib.import_module("Experimento.pipeline_avaliacao.1_pre_llm_slicing")
        processor = s1.PreLLMProcessor()
        targets = COURSES_DATA
        if args.course:
            targets = [c for c in COURSES_DATA if get_folder_name(c) == args.course or c["nome"] == args.course]
        for c in targets:
            s1.process_course_vector_store(c, processor)

    if args.stage == 2 or args.all:
        print("\n>>> INICIANDO ETAPA 2: Geração do Conjunto de Testes...")
        import importlib
        s2 = importlib.import_module("Experimento.pipeline_avaliacao.2_generate_test_dataset")
        generator = s2.QuestionGenerator()
        targets = COURSES_DATA
        if args.course:
            targets = [c for c in COURSES_DATA if get_folder_name(c) == args.course or c["nome"] == args.course]
        all_qa = []
        for c in targets:
            qa = s2.generate_course_dataset(c, generator)
            all_qa.extend(qa)
        if all_qa:
            import pandas as pd
            df_out = pd.DataFrame(all_qa)
            df_out.to_excel(TEST_DATASET_FILE, index=False)
            print(f"Salvas {len(df_out)} perguntas em: {TEST_DATASET_FILE}")

    if args.stage == 3 or args.all:
        print("\n>>> INICIANDO ETAPA 3: Execução Comparativa dos 4 RAGs...")
        import importlib
        s3 = importlib.import_module("Experimento.pipeline_avaliacao.3_run_rag_experiments")
        d_path = Path(args.dataset) if args.dataset else TEST_DATASET_FILE
        s3.run_experiments_on_dataset(dataset_path=d_path, target_course=args.course)

    if args.stage == 4 or args.all:
        print("\n>>> INICIANDO ETAPA 4: Avaliação com LLM Julgador (TypeSafe JEV 1.14)...")
        import importlib
        s4 = importlib.import_module("Experimento.pipeline_avaliacao.4_run_jev_judge")
        d_path = Path(args.dataset) if args.dataset else TEST_DATASET_FILE
        s4.evaluate_dataset(dataset_path=d_path)


if __name__ == "__main__":
    main()
