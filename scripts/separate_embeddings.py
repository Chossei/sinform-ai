import numpy as np
import pandas as pd
from pathlib import Path

courses = [
    "Estatística (Bacharel)",
    "Matemática (Bacharel)",
    "Matemática (Licenciatura)"
]

BASE_DIR = Path(__file__).resolve().parent.parent

for c in courses:
    bv_dir = BASE_DIR / c / "banco vetorial"
    p_path = bv_dir / "banco_vetorial.parquet"
    if p_path.exists():
        df = pd.read_parquet(p_path)
        print(f"=== {c} ===")
        print(f"Linhas: {len(df)} | Colunas originais: {list(df.columns)}")
        
        if "embedding" in df.columns:
            # 1. Salvar embeddings em arquivo binário numpy dedicado
            embeddings_matrix = np.array(df["embedding"].tolist(), dtype=np.float32)
            npy_path = bv_dir / "embeddings.npy"
            np.save(npy_path, embeddings_matrix)
            print(f"-> Salvo {npy_path.name} com shape {embeddings_matrix.shape} ({npy_path.stat().st_size} bytes)")
            
            # 2. Deixar o DataFrame 100% limpo sem a coluna de embedding
            clean_df = df.drop(columns=["embedding"])
            clean_df.to_parquet(p_path, index=False)
            
            json_path = bv_dir / "banco_vetorial.json"
            clean_df.to_json(json_path, orient="records", indent=2, force_ascii=False)
            
            csv_path = bv_dir / "banco_vetorial.csv"
            clean_df.to_csv(csv_path, index=False, encoding="utf-8")
            
            lines_json = len(json_path.read_text(encoding="utf-8").splitlines())
            print(f"-> DataFrame limpo salvo! Linhas no JSON agora: {lines_json} (redução de ~120.000 para {lines_json}!)")
            print(f"-> Salvo também {csv_path.name} para fácil abertura em Excel/Planilhas.\n")

print("Separação de embeddings concluída com sucesso em todos os cursos!")
