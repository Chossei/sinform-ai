import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
EXP_DIR = BASE_DIR / "Experimento"
UFBA_GERAL = EXP_DIR / "Áreas do conhecimento" / "UFBA - Geral"
EXATAS_DIR = EXP_DIR / "Áreas do conhecimento" / "Ciências Exatas e da Terra"


def to_long_path(p: Path) -> Path:
    s = str(p.resolve())
    if os.name == "nt" and not s.startswith("\\\\?\\"):
        return Path("\\\\?\\" + s)
    return Path(s)


def copy_tree_long(src: Path, dst: Path):
    src_long = to_long_path(src)
    dst_long = to_long_path(dst)
    dst_long.mkdir(parents=True, exist_ok=True)
    for root, dirs, files in os.walk(src_long):
        rel = os.path.relpath(root, src_long)
        target_dir = dst_long if rel == "." else dst_long / rel
        target_dir.mkdir(parents=True, exist_ok=True)
        for f in files:
            src_f = Path(root) / f
            dst_f = target_dir / f
            if not dst_f.exists():
                shutil.copy2(src_f, dst_f)


def main():
    geral_subdirs = [d for d in UFBA_GERAL.iterdir() if d.is_dir() and d.name != "banco vetorial"]
    courses = [d for d in EXATAS_DIR.iterdir() if d.is_dir()]
    print(f"Sincronizando {len(geral_subdirs)} pastas gerais para {len(courses)} cursos de Exatas...")

    for c in courses:
        for g in geral_subdirs:
            target = c / g.name
            copy_tree_long(g, target)

    print("Sincronização concluída com sucesso!")


if __name__ == "__main__":
    main()

