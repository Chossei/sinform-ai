import os
from pathlib import Path
import requests
import urllib3

urllib3.disable_warnings()

BASE_DIR = Path(__file__).resolve().parent.parent
EST_DIR = BASE_DIR / "Estatística (Bacharel)"
EST_DIR.mkdir(parents=True, exist_ok=True)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

FILES = [
    {
        "filename": "Resolucao_03_2025_Atividades_Complementares_SIGAA.pdf",
        "url": "https://colest.ime.ufba.br/wp-content/uploads/2026/10/Resolucao_03_2025_Atividades_Complementares_SIGAA_assinado.pdf"
    },
    {
        "filename": "Resolucao_05_2024_TCC_Estatistica.pdf",
        "url": "https://colest.ime.ufba.br/wp-content/uploads/2025/01/Resolucao_05_2024_TCC.pdf"
    },
    {
        "filename": "Resolucoes_01_e_02_2020_Estagio_Nao_Obrigatorio_IME.pdf",
        "url": "http://colest.ime.ufba.br/wp-content/uploads/2021/01/Resolucoes_01_e_02_2020_Estagio_nao_obrigatorio_IME.pdf"
    },
    {
        "filename": "Resolucao_01_2018_Trancamento_e_Permanencia.pdf",
        "url": "http://colest.ime.ufba.br/wp-content/uploads/2019/03/Resolu%C3%A7%C3%A3o-01_2018_Trancamento-e-Perman%C3%AAncia.pdf"
    },
    {
        "filename": "Resolucao_02_2018_Exame_Conhecimento_Previo.pdf",
        "url": "http://colest.ime.ufba.br/wp-content/uploads/2019/03/Resolu%C3%A7%C3%A3o-02_2018_Exame_Conhecimento_Previo.pdf"
    },
    {
        "filename": "Instrucao_Normativa_006_2025_Trancamento_TCC.pdf",
        "url": "https://colest.ime.ufba.br/wp-content/uploads/2025/04/Instrucao_Normativa_N%C2%BA_006_2025.pdf"
    },
    {
        "filename": "Guia_Orientacoes_Registros_Academicos_2025.pdf",
        "url": "https://colest.ime.ufba.br/wp-content/uploads/2025/04/Guia-de-Orienta%C3%A7%C3%B5es-sobre-Registros-2025.1.pdf"
    }
]

def main():
    print("=" * 60)
    print("BAIXANDO DOCUMENTOS OFICIAIS DO COLEST (COLEGIADO DE ESTATÍSTICA)")
    print(f"Destino: {EST_DIR}")
    print("=" * 60)
    
    for item in FILES:
        dest = EST_DIR / item["filename"]
        print(f"Baixando {item['filename']}...", end=" ", flush=True)
        try:
            r = requests.get(item["url"], headers=headers, verify=False, timeout=20)
            if r.status_code == 200:
                with open(dest, "wb") as f:
                    f.write(r.content)
                print(f"OK ({len(r.content)} bytes)")
            else:
                print(f"Falha HTTP {r.status_code}")
        except Exception as e:
            print(f"Erro: {e}")

    print("\nTodos os arquivos do COLEST foram baixados e salvos com sucesso!")

if __name__ == "__main__":
    main()
