"""
Redirecionador para etapa3_run_rag_experiments.py
"""
from Experimento.pipeline_avaliacao.etapa3_run_rag_experiments import *

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Executa o benchmark da Etapa 3 de RAGs")
    parser.add_argument("--area", type=str, default="Ciências Exatas e da Terra")
    parser.add_argument("--max-questions", type=int, default=None)
    parser.add_argument("--max-courses", type=int, default=None)
    parser.add_argument("--budget-limit", type=float, default=0.05)
    args = parser.parse_args()

    run_stage3_benchmark(
        target_area=args.area,
        max_questions_per_course=args.max_questions,
        max_courses=args.max_courses,
        budget_limit_usd=args.budget_limit
    )
