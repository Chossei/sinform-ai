import os
import ssl
import urllib.request
import urllib.parse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
EST_DIR = BASE_DIR / "Estatística (Bacharel)"
EST_DIR.mkdir(parents=True, exist_ok=True)

DOCS = [
    {
        "name": "REGPG_Regimento_Ensino_Graduacao_UFBA.pdf",
        "url": "https://www.ufba.br/sites/portal.ufba.br/files/regpg_cae_2024_final.pdf"
    },
    {
        "name": "Resolucao_03_2025_Atividades_Complementares_SIGAA.pdf",
        "url": "https://colest.ime.ufba.br/wp-content/uploads/2026/10/Resolucao_03_2025_Atividades_Complementares_SIGAA_assinado.pdf"
    },
    {
        "name": "Resolucao_05_2024_TCC_Estatistica.pdf",
        "url": "https://colest.ime.ufba.br/wp-content/uploads/2025/01/Resolucao_05_2024_TCC.pdf"
    },
    {
        "name": "Resolucoes_01_e_02_2020_Estagio_Nao_Obrigatorio_IME.pdf",
        "url": "http://colest.ime.ufba.br/wp-content/uploads/2021/01/Resolucoes_01_e_02_2020_Estagio_nao_obrigatorio_IME.pdf"
    },
    {
        "name": "Resolucao_01_2018_Trancamento_e_Permanencia.pdf",
        "url": "http://colest.ime.ufba.br/wp-content/uploads/2019/03/Resolu%C3%A7%C3%A3o-01_2018_Trancamento-e-Perman%C3%AAncia.pdf"
    },
    {
        "name": "Resolucao_02_2018_Exame_Conhecimento_Previo.pdf",
        "url": "http://colest.ime.ufba.br/wp-content/uploads/2019/03/Resolu%C3%A7%C3%A3o-02_2018_Exame_Conhecimento_Previo.pdf"
    },
    {
        "name": "Instrucao_Normativa_006_2025_Trancamento_TCC.pdf",
        "url": "https://colest.ime.ufba.br/wp-content/uploads/2025/04/Instrucao_Normativa_N%C2%BA_006_2025.pdf"
    },
    {
        "name": "Guia_Orientacoes_Registros_Academicos.pdf",
        "url": "https://colest.ime.ufba.br/wp-content/uploads/2025/04/Guia-de-Orienta%C3%A7%C3%B5es-sobre-Registros-2025.1.pdf"
    }
]

def download_all():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    print(f"Iniciando download dos documentos oficiais de Estatística para {EST_DIR}...\n")
    for item in DOCS:
        dest_path = EST_DIR / item["name"]
        print(f"Baixando: {item['name']}...")
        try:
            req = urllib.request.Request(
                item["url"],
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
            )
            with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                data = resp.read()
                with open(dest_path, "wb") as f:
                    f.write(data)
                print(f"  -> Concluído com sucesso: {dest_path.name} ({len(data)} bytes)")
        except Exception as e:
            print(f"  -> Erro ao baixar {item['name']} de {item['url']}: {e}")

if __name__ == "__main__":
    download_all()
