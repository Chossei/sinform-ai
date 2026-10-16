import os
import ssl
import urllib.request
import urllib3
from pathlib import Path

urllib3.disable_warnings()

BASE_DIR = Path(__file__).resolve().parent.parent

COURSES = {
    "Matemática (Bacharel)": BASE_DIR / "Matemática (Bacharel)",
    "Matemática (Licenciatura)": BASE_DIR / "Matemática (Licenciatura)",
    "Estatística (Bacharel)": BASE_DIR / "Estatística (Bacharel)"
}

for folder in COURSES.values():
    folder.mkdir(parents=True, exist_ok=True)

DOWNLOADS = [
    # Matemática (Bacharel)
    {
        "url": "https://drive.usercontent.google.com/download?id=1MFFPAKiwtMBajvSgjGWF6ZG8cJbVc2Rw&export=download&authuser=0",
        "dest": COURSES["Matemática (Bacharel)"] / "Resolucao_Estagio_Supervisionado_Bacharelado_Matematica.pdf"
    },
    {
        "url": "https://drive.usercontent.google.com/download?id=1zdC43GLY8qGX1bwhQXFUmy6VhUaL4MR1&export=download&authuser=0",
        "dest": COURSES["Matemática (Bacharel)"] / "Resolucao_Atividades_Complementares_Matematica.pdf"
    },
    {
        "url": "https://drive.usercontent.google.com/download?id=1sD4JV1mF7cn-aT_4Nk4bs1q2yi9IgXap&export=download&authuser=0",
        "dest": COURSES["Matemática (Bacharel)"] / "Regimento_Interno_Colegiado_Matematica.pdf"
    },
    {
        "url": "https://colmat.ufba.br/sites/colmat.ufba.br/files/ppc_matematica_diurno_2006.pdf",
        "dest": COURSES["Matemática (Bacharel)"] / "Projeto_Pedagogico_Matematica_Diurno.pdf"
    },
    {
        "url": "https://supac.ufba.br/sites/supac.ufba.br/files/guia_do_estudante_supac.pdf",
        "dest": COURSES["Matemática (Bacharel)"] / "Regulamento_Academico_Graduacao_UFBA.pdf"
    },

    # Matemática (Licenciatura)
    {
        "url": "https://colmat.ufba.br/sites/colmat.ufba.br/files/ppc_matematica_noturno_2009_0.pdf",
        "dest": COURSES["Matemática (Licenciatura)"] / "Projeto_Pedagogico_Matematica_Noturno_Licenciatura.pdf"
    },
    {
        "url": "https://colmat.ufba.br/sites/colmat.ufba.br/files/ppc_matematica_diurno_2006.pdf",
        "dest": COURSES["Matemática (Licenciatura)"] / "Projeto_Pedagogico_Matematica_Diurno_Licenciatura.pdf"
    },
    {
        "url": "https://drive.usercontent.google.com/download?id=1zdC43GLY8qGX1bwhQXFUmy6VhUaL4MR1&export=download&authuser=0",
        "dest": COURSES["Matemática (Licenciatura)"] / "Resolucao_Atividades_Complementares_Matematica.pdf"
    },
    {
        "url": "https://drive.usercontent.google.com/download?id=1sD4JV1mF7cn-aT_4Nk4bs1q2yi9IgXap&export=download&authuser=0",
        "dest": COURSES["Matemática (Licenciatura)"] / "Regimento_Interno_Colegiado_Matematica.pdf"
    },
    {
        "url": "https://supac.ufba.br/sites/supac.ufba.br/files/guia_do_estudante_supac.pdf",
        "dest": COURSES["Matemática (Licenciatura)"] / "Regulamento_Academico_Graduacao_UFBA.pdf"
    },

    # Estatística (Bacharel)
    {
        "url": "https://supac.ufba.br/sites/supac.ufba.br/files/guia_do_estudante_supac.pdf",
        "dest": COURSES["Estatística (Bacharel)"] / "Regulamento_Academico_Graduacao_UFBA.pdf"
    }
]

def download_file(url, dest_path):
    print(f"Baixando {dest_path.name}...")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
        data = response.read()
    with open(dest_path, "wb") as f:
        f.write(data)
    print(f"-> Salvo: {dest_path} ({len(data)} bytes)")

if __name__ == "__main__":
    for item in DOWNLOADS:
        try:
            download_file(item["url"], item["dest"])
        except Exception as e:
            print(f"Falha ao baixar {item['dest'].name} de {item['url']}: {e}")
