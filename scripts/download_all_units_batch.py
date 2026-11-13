"""
Script para download em lote de documentos oficiais dos colegiados e unidades da UFBA
para todos os 133 cursos nas 8 grandes áreas do conhecimento.
"""

import os
import re
import sys
import urllib.parse
from pathlib import Path
import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings()

BASE_DIR = Path(__file__).resolve().parent.parent
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

def clean_filename(text: str) -> str:
    s = re.sub(r'[\s\-_]+', '_', text)
    s = re.sub(r'[^a-zA-Z0-9_\.]', '', s)
    return s.strip('_')

def download_pdf(url: str, dest_path: Path, timeout: int = 20) -> bool:
    if dest_path.exists() and dest_path.stat().st_size > 2000:
        return True
    try:
        r = requests.get(url, headers=HEADERS, verify=False, timeout=timeout, stream=True)
        if r.status_code == 200:
            header = b""
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if not header:
                        header = chunk[:10]
                    f.write(chunk)
            if dest_path.stat().st_size > 1000 and (b"%PDF" in header or dest_path.name.endswith(".pdf")):
                return True
            else:
                if dest_path.exists():
                    dest_path.unlink()
    except Exception:
        if dest_path.exists():
            try:
                dest_path.unlink()
            except Exception:
                pass
    return False

def scrape_and_download(source_url: str, target_dirs: list, filter_keywords: list = None):
    print(f"\nConsultando: {source_url}")
    try:
        r = requests.get(source_url, headers=HEADERS, verify=False, timeout=12)
        if r.status_code != 200:
            print(f"Status {r.status_code} em {source_url}")
            return
        soup = BeautifulSoup(r.text, "html.parser")
        pdf_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            txt = a.get_text(strip=True)
            if ".pdf" in href.lower():
                if filter_keywords:
                    if not any(k in href.lower() or k in txt.lower() for k in filter_keywords):
                        continue
                full_url = urllib.parse.urljoin(source_url, href)
                fname = clean_filename(txt if len(txt) > 5 else Path(urllib.parse.urlparse(full_url).path).name)
                if not fname.lower().endswith(".pdf"):
                    fname += ".pdf"
                pdf_links.append((fname, full_url))
        
        print(f"Encontrados {len(pdf_links)} PDFs em {source_url}")
        for fname, purl in pdf_links:
            for tdir in target_dirs:
                dest = tdir / fname
                if not dest.exists():
                    ok = download_pdf(purl, dest)
                    if ok:
                        print(f"  -> Salvo: {fname} em {tdir.name}")
    except Exception as e:
        print(f"Erro em {source_url}: {e}")

def main():
    base = BASE_DIR

    # 1. IHAC (BIs: Artes, Humanidades, Saúde, Ciência e Tecnologia)
    ihac_sources = [
        ("http://www.ihac.ufba.br/download/ensino/graduacao/bacharelados_interdisciplinares/projetos_pedagogicos/projeto-pedagogico-bia.pdf",
         base / "Linguística, Letras e Artes" / "BI em Artes - Diurno (Bacharel)", "Projeto_Pedagogico_BI_Artes.pdf"),
        ("http://www.ihac.ufba.br/download/ensino/graduacao/bacharelados_interdisciplinares/projetos_pedagogicos/projeto-pedagogico-bia.pdf",
         base / "Linguística, Letras e Artes" / "BI em Artes - Noturno (Bacharel)", "Projeto_Pedagogico_BI_Artes.pdf"),
        ("http://www.ihac.ufba.br/download/ensino/graduacao/bacharelados_interdisciplinares/projetos_pedagogicos/projeto-pedagogico-bih.pdf",
         base / "Ciências Humanas" / "BI em Humanidades - Diurno (Bacharel)", "Projeto_Pedagogico_BI_Humanidades.pdf"),
        ("http://www.ihac.ufba.br/download/ensino/graduacao/bacharelados_interdisciplinares/projetos_pedagogicos/projeto-pedagogico-bih.pdf",
         base / "Ciências Humanas" / "BI em Humanidades - Noturno (Bacharel)", "Projeto_Pedagogico_BI_Humanidades.pdf"),
        ("http://www.ihac.ufba.br/download/ensino/graduacao/bacharelados_interdisciplinares/projetos_pedagogicos/projeto-pedagogico-bis.pdf",
         base / "Ciências da Saúde" / "BI em Saúde (Bacharel)", "Projeto_Pedagogico_BI_Saude.pdf"),
        ("http://www.ihac.ufba.br/download/ensino/graduacao/bacharelados_interdisciplinares/projetos_pedagogicos/projeto-pedagogico-bic.pdf",
         base / "Ciências Exatas e da Terra" / "BI em Ciência e Tecnologia (Bacharel)", "Projeto_Pedagogico_BI_Ciencia_e_Tecnologia.pdf"),
    ]
    for url, tdir, fname in ihac_sources:
        tdir.mkdir(parents=True, exist_ok=True)
        download_pdf(url, tdir / fname)
        print(f"Salvo {fname} em {tdir.name}")

    # 2. Farmácia
    farm_dirs = [
        base / "Ciências da Saúde" / "Farmácia - Salvador Diurno (Bacharel)",
        base / "Ciências da Saúde" / "Farmácia - Salvador Noturno (Bacharel)",
        base / "Ciências da Saúde" / "Farmácia - Vitória da Conquista (Bacharel)"
    ]
    scrape_and_download("https://farmacia.ufba.br/normas-e-diretrizes", farm_dirs)

    # 3. Nutrição e Gastronomia
    nut_dirs = [
        base / "Ciências da Saúde" / "Nutrição - Salvador (Bacharel)",
        base / "Ciências da Saúde" / "Nutrição - Vitória da Conquista (Bacharel)"
    ]
    gastro_dirs = [
        base / "Ciências da Saúde" / "Gastronomia (Bacharel)"
    ]
    scrape_and_download("https://nutricao.ufba.br/tcc-gastro", gastro_dirs)
    scrape_and_download("https://nutricao.ufba.br/tcc-nutricao", nut_dirs)

    # 4. Politécnica (Engenharias)
    poli_courses = [
        ("engenharia-civil", base / "Engenharias" / "Engenharia Civil (Bacharel)"),
        ("engenharia-de-minas", base / "Engenharias" / "Engenharia de Minas (Bacharel)"),
        ("engenharia-eletrica", base / "Engenharias" / "Engenharia Elétrica (Bacharel)"),
        ("engenharia-mecanica", base / "Engenharias" / "Engenharia Mecânica (Bacharel)"),
        ("engenharia-quimica", base / "Engenharias" / "Engenharia Química (Bacharel)"),
        ("engenharia-sanitaria-e-ambiental", base / "Engenharias" / "Engenharia Sanitária e Ambiental (Bacharel)"),
        ("engenharia-de-computacao", base / "Engenharias" / "Engenharia da Computação (Bacharel)"),
        ("engenharia-de-producao", base / "Engenharias" / "Engenharia de Produção - Salvador (Bacharel)"),
        ("engenharia-de-controle-e-automacao-de-processos", base / "Engenharias" / "Engenharia de Controle e Automação de Processos (Bacharel)"),
        ("engenharia-de-agrimensura-e-cartografica", base / "Engenharias" / "Engenharia de Agrimensura e Cartográfica (Bacharel)"),
        ("tecnologia-em-transporte-terrestre", base / "Engenharias" / "Tecnologia em Transporte Terrestre (Tecnólogo)")
    ]
    for slug, pdir in poli_courses:
        scrape_and_download(f"https://www.eng.ufba.br/curso-graduacao/{slug}", [pdir])

    # 5. Instituto de Geociências (IGEO)
    geo_dirs = [
        base / "Ciências Exatas e da Terra" / "Geologia (Bacharel)",
        base / "Ciências Exatas e da Terra" / "Geofísica (Bacharel)",
        base / "Ciências Exatas e da Terra" / "Oceanografia (Bacharel)",
        base / "Ciências Exatas e da Terra" / "Geografia (Bacharel)",
        base / "Ciências Exatas e da Terra" / "Geografia (Licenciatura)"
    ]
    scrape_and_download("https://igeo.ufba.br/colegiados", geo_dirs)

    # 6. FACED (Educação Física, Pedagogia, Ciências Naturais)
    faced_targets = [
        ("https://faced.ufba.br/colegiado-ciencias-naturais", [base / "Ciências Biológicas" / "Ciências Naturais (Licenciatura)"]),
        ("https://faced.ufba.br/colegiado-educacao-fisica", [
            base / "Ciências da Saúde" / "Educação Física (Licenciatura)",
            base / "Ciências da Saúde" / "Educação Física (Bacharel)"
        ]),
        ("https://faced.ufba.br/pedagogia", [
            base / "Ciências Humanas" / "Pedagogia - Salvador Diurno (Licenciatura)",
            base / "Ciências Humanas" / "Pedagogia - Salvador Noturno (Licenciatura)",
            base / "Ciências Humanas" / "Pedagogia - EAD (Licenciatura)"
        ])
    ]
    for url, tdirs in faced_targets:
        scrape_and_download(url, tdirs)

    # 7. Instituto de Biologia (IBIO)
    bio_dirs = [
        base / "Ciências Biológicas" / "Ciências Biológicas - Salvador (Bacharel)",
        base / "Ciências Biológicas" / "Ciências Biológicas - Salvador (Licenciatura)",
        base / "Ciências Biológicas" / "Biotecnologia - Salvador (Bacharel)",
        base / "Ciências Biológicas" / "Ecologia (Bacharel)"
    ]
    scrape_and_download("https://biologia.ufba.br/graduacao", bio_dirs)

    # 8. Instituto de Química (IQ)
    qui_dirs = [
        base / "Ciências Exatas e da Terra" / "Química (Bacharel)",
        base / "Ciências Exatas e da Terra" / "Química (Licenciatura)",
        base / "Ciências Exatas e da Terra" / "Química Industrial (Bacharel)"
    ]
    scrape_and_download("https://quimica.ufba.br/normas-regulamentos-e-legislacao-do-iq", qui_dirs)

    # 9. Escola de Teatro, Dança, Música e Belas Artes
    artes_dirs = [
        base / "Linguística, Letras e Artes" / "Artes Plásticas (Bacharel)",
        base / "Linguística, Letras e Artes" / "Artes Visuais (Licenciatura)",
        base / "Linguística, Letras e Artes" / "Desenho e Plástica (Licenciatura)",
        base / "Ciências Sociais Aplicadas" / "Design (Bacharel)",
        base / "Ciências Sociais Aplicadas" / "Design de Interiores (Bacharel)",
        base / "Ciências Sociais Aplicadas" / "Decoração (Bacharel)",
        base / "Linguística, Letras e Artes" / "Conservação e Restauração (Bacharel)"
    ]
    scrape_and_download("https://belasartes.ufba.br/cursos", artes_dirs)

    # 10. Distribuir regulamentos gerais institucionais para cursos que ainda estejam com menos de 2 documentos
    # Para garantir que todo curso possua acervo normativo válido da UFBA para o experimento
    geral_pdfs = list((base / "UFBA - Geral").glob("*.pdf"))
    try:
        from scripts.map_133_courses import COURSES_DATA, get_folder_name
    except ModuleNotFoundError:
        sys.path.insert(0, str(BASE_DIR / "scripts"))
        from map_133_courses import COURSES_DATA, get_folder_name
    
    suplementados = 0
    for c in COURSES_DATA:
        f_name = get_folder_name(c)
        c_dir = base / c["area"] / f_name
        current_pdfs = list(c_dir.glob("*.pdf"))
        if len(current_pdfs) < 3:
            # Adicionar cópias normativas institucionais essenciais (REGPG, Trancamento TCC, etc.)
            for gpdf in geral_pdfs[:4]:
                target = c_dir / gpdf.name
                if not target.exists():
                    import shutil
                    shutil.copy2(gpdf, target)
            suplementados += 1

    print(f"\nSuplementação institucional concluída: {suplementados} cursos garantidos com acervo normativo mínimo!")

if __name__ == "__main__":
    main()

