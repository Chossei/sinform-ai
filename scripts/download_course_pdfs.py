"""
Engine centralizado para download e validação de PDFs específicos por curso
para as 8 Grandes Áreas do Conhecimento da UFBA.
"""

import os
import re
import sys
import io
import time
import urllib.parse
from pathlib import Path
import requests
import urllib3
import pypdf
from bs4 import BeautifulSoup

urllib3.disable_warnings()

BASE_DIR = Path(__file__).resolve().parent.parent
EXP_AREAS_DIR = BASE_DIR / "Experimento" / "Áreas do conhecimento"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

def to_long_path(p: Path) -> Path:
    s = str(p.resolve())
    if os.name == "nt" and not s.startswith("\\\\?\\"):
        return Path("\\\\?\\" + s)
    return p

def clean_filename(text: str) -> str:
    s = re.sub(r'[\s\-_]+', '_', text)
    s = re.sub(r'[^a-zA-Z0-9_\.]', '', s)
    s = re.sub(r'_+', '_', s).strip('_')
    return s

def validate_pdf_bytes(content: bytes) -> bool:
    if not content or len(content) < 1000:
        return False
    if not content.startswith(b"%PDF"):
        return False
    try:
        reader = pypdf.PdfReader(io.BytesIO(content))
        return len(reader.pages) > 0
    except Exception:
        return False

def download_and_save(url: str, dest_dir: Path, filename: str) -> bool:
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"
    
    clean_name = clean_filename(filename[:-4]) + ".pdf"
    dest_path = to_long_path(dest_dir / clean_name)
    
    if dest_path.exists() and dest_path.stat().st_size > 2000:
        try:
            with open(dest_path, "rb") as f:
                header = f.read(5)
                if header.startswith(b"%PDF"):
                    return True
        except Exception:
            pass

    try:
        r = requests.get(url, headers=HEADERS, verify=False, timeout=25, allow_redirects=True)
        if r.status_code == 200 and validate_pdf_bytes(r.content):
            dest_dir.mkdir(parents=True, exist_ok=True)
            with open(dest_path, "wb") as f:
                f.write(r.content)
            print(f"  [OK] Salvo: {clean_name} ({len(r.content):,} bytes) em {dest_dir.name}")
            return True
        else:
            print(f"  [FALHA] URL {url} retornou status={r.status_code}, len={len(r.content) if r else 0}")
    except Exception as e:
        print(f"  [ERRO] Download falhou para {url}: {e}")
    return False

def scrape_links(url: str, keywords: list = None, timeout: int = 15) -> list:
    results = []
    try:
        r = requests.get(url, headers=HEADERS, verify=False, timeout=timeout)
        if r.status_code != 200:
            return results
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = urllib.parse.urljoin(url, a["href"])
            txt = a.get_text(strip=True)
            if ".pdf" in href.lower():
                if keywords:
                    combined = (txt + " " + href).lower()
                    if not any(k.lower() in combined for k in keywords):
                        continue
                name = txt if len(txt) > 4 else Path(urllib.parse.urlparse(href).path).name
                results.append((href, name))
    except Exception as e:
        print(f"  [AVISO] Erro ao raspar {url}: {e}")
    return results

# =========================================================================
# 1. IHAC (Bacharelados Interdisciplinares)
# =========================================================================
def download_ihac():
    print("\n>>> Processando IHAC (Bacharelados Interdisciplinares)...")
    base = EXP_AREAS_DIR
    
    # ACC comum a todos os BIs
    acc_url = "https://ihac.ufba.br/docs/resolucao-no-01-2025-regulamenta-as-atividades-complementares-nos-curriculos-dos-bi/"
    # Scrape PDF from acc_url
    acc_links = scrape_links(acc_url)
    acc_pdf = acc_links[0][0] if acc_links else "https://ihac.ufba.br/wp-content/uploads/2025/01/Resolucao-01_2025-Atividades-Complementares-BI.pdf"
    
    ihac_items = [
        ("Humanidades", "http://www.ihac.ufba.br/download/ensino/graduacao/bacharelados_interdisciplinares/projetos_pedagogicos/projeto-pedagogico-bih.pdf",
         [base / "Ciências Humanas" / "BI em Humanidades - Diurno (Bacharel)",
          base / "Ciências Humanas" / "BI em Humanidades - Noturno (Bacharel)"],
         "Projeto_Pedagogico_BI_Humanidades.pdf"),
        ("Artes", "http://www.ihac.ufba.br/download/ensino/graduacao/bacharelados_interdisciplinares/projetos_pedagogicos/projeto-pedagogico-bia.pdf",
         [base / "Linguística, Letras e Artes" / "BI em Artes - Diurno (Bacharel)",
          base / "Linguística, Letras e Artes" / "BI em Artes - Noturno (Bacharel)"],
         "Projeto_Pedagogico_BI_Artes.pdf"),
        ("Saúde", "http://www.ihac.ufba.br/download/ensino/graduacao/bacharelados_interdisciplinares/projetos_pedagogicos/projeto-pedagogico-bis.pdf",
         [base / "Ciências da Saúde" / "BI em Saúde (Bacharel)"],
         "Projeto_Pedagogico_BI_Saude.pdf"),
        ("Ciência e Tecnologia", "http://www.ihac.ufba.br/download/ensino/graduacao/bacharelados_interdisciplinares/projetos_pedagogicos/projeto-pedagogico-bic.pdf",
         [base / "Ciências Exatas e da Terra" / "BI em Ciência e Tecnologia (Bacharel)"],
         "Projeto_Pedagogico_BI_Ciencia_e_Tecnologia.pdf"),
        ("Ciência, Tecnologia e Inovação Camaçari", "https://icti.ufba.br/sites/icti.ufba.br/files/ppc_bicti_atualizado.pdf",
         [base / "Engenharias" / "BI em Ciência, Tecnologia e Inovação (Bacharel)"],
         "Projeto_Pedagogico_BI_Ciencia_Tecnologia_Inovacao_Camacari.pdf")
    ]
    
    for nome, url, target_dirs, fname in ihac_items:
        for tdir in target_dirs:
            download_and_save(url, tdir, fname)
            # Salvar tambem a resolucao de ACC do IHAC
            if acc_pdf:
                download_and_save(acc_pdf, tdir, "Resolucao_01_2025_Atividades_Complementares_IHAC.pdf")

# =========================================================================
# 2. SISTEMAS DE INFORMAÇÃO (BSI)
# =========================================================================
def download_bsi():
    print("\n>>> Processando Sistemas de Informação (BSI)...")
    bsi_dir = EXP_AREAS_DIR / "Ciências Exatas e da Terra" / "Sistemas de Informação (Bacharel)"
    
    bsi_docs = [
        ("https://bsi.ufba.br/sites/bsi.ufba.br/files/pictures/projeto_pedagogico_bsi-v25.pdf", "Projeto_Pedagogico_BSI.pdf"),
        ("https://bsi.ufba.br/sites/bsi.ufba.br/files/pictures/ementario_bsi.pdf", "Ementario_Disciplinas_BSI.pdf"),
        ("https://bsi.ufba.br/sites/bsi.ufba.br/files/resoluo_n_02_2025_-_estgio_nao-obrigatorio.pdf", "Resolucao_02_2025_Estagio_BSI.pdf"),
        ("https://bsi.ufba.br/sites/bsi.ufba.br/files/pictures/resolucao001_2019.pdf", "Resolucao_01_2019_Dilatacao_BSI.pdf"),
        ("https://bsi.ufba.br/sites/bsi.ufba.br/files/regimento_01_2021_tcc_bsi.pdf", "Regimento_01_2021_TCC_BSI.pdf"),
    ]
    for url, fname in bsi_docs:
        download_and_save(url, bsi_dir, fname)

# =========================================================================
# 3. INSTITUTO DE BIOLOGIA (IBIO)
# =========================================================================
def download_ibio():
    print("\n>>> Processando Instituto de Biologia (IBIO)...")
    bio_dirs = [
        EXP_AREAS_DIR / "Ciências Biológicas" / "Ciências Biológicas - Salvador (Bacharel)",
        EXP_AREAS_DIR / "Ciências Biológicas" / "Ciências Biológicas - Salvador (Licenciatura)",
        EXP_AREAS_DIR / "Ciências Biológicas" / "Biotecnologia - Salvador (Bacharel)",
        EXP_AREAS_DIR / "Ciências Biológicas" / "Ecologia (Bacharel)"
    ]
    
    ppc_url = "https://biologia.ufba.br/sites/biologia.ufba.br/files/ppc_2014.1_2023.1_licenciatura_bacharelado_com_fluxogramas_e_matrizes.pdf"
    for bdir in bio_dirs[:2]: # Bacharelado e Licenciatura
        download_and_save(ppc_url, bdir, "PPC_Ciencias_Biologicas_Licenciatura_Bacharelado.pdf")
        
    # Verificar normas e documentos gerais do IBIO
    ibio_docs = scrape_links("https://biologia.ufba.br/documentos")
    for purl, pname in ibio_docs:
        for bdir in bio_dirs:
            download_and_save(purl, bdir, f"IBIO_{pname}.pdf")

# =========================================================================
# 4. FACULDADE DE MEDICINA (FMB) & TERAPIA OCUPACIONAL
# =========================================================================
def download_fmb_to():
    print("\n>>> Processando Faculdade de Medicina da Bahia e Terapia Ocupacional...")
    med_dir = EXP_AREAS_DIR / "Ciências da Saúde" / "Medicina - Salvador (Bacharel)"
    to_dir = EXP_AREAS_DIR / "Ciências da Saúde" / "Terapia Ocupacional (Bacharel)"
    
    # Medicina
    med_docs = [
        ("https://fmb.ufba.br/sites/fmb.ufba.br/files/documentos/Colegiado%20-%20Medicina/Internato/Regulamento%20do%20est%C3%A1gio%20curricular%20obrigat%C3%B3rio%20%28internato%29%20do%20curso%20de%20gradua%C3%A7%C3%A3o%20em%20Medicina%20da%20FMB-UFBA.pdf",
         "Regulamento_Estagio_Internato_Medicina_FMB.pdf"),
        ("https://fmb.ufba.br/sites/fmb.ufba.br/files/documentos/Colegiado%20-%20Medicina/Matriz%20Curricular/2024%20-%20Atual/matrizcurricularfmb2026_2.pdf",
         "Matriz_Curricular_Medicina_FMB_Atual.pdf"),
        ("https://fmb.ufba.br/sites/fmb.ufba.br/files/documentos/Congrega%C3%A7%C3%A3o/Regimento%20FMB/resolucao_03.2025_-_consuni_novo_regimento.pdf",
         "Regimento_Interno_Faculdade_de_Medicina_FMB.pdf")
    ]
    for url, fname in med_docs:
        download_and_save(url, med_dir, fname)
        
    # Terapia Ocupacional
    to_docs = [
        ("https://fmb.ufba.br/sites/fmb.ufba.br/files/documentos/Colegiado%20-%20Terapia%20Ocupacional/Resolu%C3%A7%C3%B5es/resolucao_cgto_n._02_-_de_22.06.2023_atividade_complementar.pdf",
         "Resolucao_02_2023_Atividades_Complementares_TO.pdf"),
        ("https://fmb.ufba.br/sites/fmb.ufba.br/files/documentos/Colegiado%20-%20Terapia%20Ocupacional/Resolu%C3%A7%C3%B5es/resolucao_n_01_2023_aproveitamento_de_estudos.pdf",
         "Resolucao_01_2023_Aproveitamento_Estudos_TO.pdf"),
        ("https://fmb.ufba.br/sites/fmb.ufba.br/files/documentos/Colegiado%20-%20Terapia%20Ocupacional/Regulamentos/REGULAMENTO%20TCC%20TO_UFBA.pdf",
         "Regulamento_TCC_Terapia_Ocupacional.pdf"),
        ("https://fmb.ufba.br/sites/fmb.ufba.br/files/documentos/Colegiado%20-%20Terapia%20Ocupacional/Regulamentos/Regulamento%20do%20colegiado.pdf",
         "Regulamento_Colegiado_Terapia_Ocupacional.pdf"),
        ("https://fmb.ufba.br/sites/fmb.ufba.br/files/documentos/Colegiado%20-%20Terapia%20Ocupacional/Regulamentos/REGULAMENTO%20DO%20N%C3%9ACLEO%20DOCENTE%20ESTRUTURANTE%20DO%20CURSO%20DE%20TERAPIA%20OCUPACIONAL%20%28UFBA%29.pdf",
         "Regulamento_NDE_Terapia_Ocupacional.pdf"),
        ("https://fmb.ufba.br/sites/fmb.ufba.br/files/documentos/Colegiado%20-%20Terapia%20Ocupacional/Regulamentos/Regulamento%20est%C3%A1gio%20obrigat%C3%B3rio.pdf",
         "Regulamento_Estagio_Obrigatorio_Terapia_Ocupacional.pdf"),
        ("https://fmb.ufba.br/sites/fmb.ufba.br/files/documentos/Colegiado%20-%20Terapia%20Ocupacional/Regulamentos/estagios_nao_obrigatorio_regulamento.pdf",
         "Regulamento_Estagio_Nao_Obrigatorio_Terapia_Ocupacional.pdf")
    ]
    for url, fname in to_docs:
        download_and_save(url, to_dir, fname)

# =========================================================================
# 5. FACOM (Jornalismo e Produção Cultural)
# =========================================================================
def download_facom():
    print("\n>>> Processando FACOM...")
    jorn_dir = EXP_AREAS_DIR / "Ciências Sociais Aplicadas" / "Comunicação - Jornalismo (Bacharel)"
    prod_c_dir = EXP_AREAS_DIR / "Ciências Sociais Aplicadas" / "Comunicação - Produção em Comunicação e Cultura (Bacharel)"
    prod_cult_dir = EXP_AREAS_DIR / "Linguística, Letras e Artes" / "Produção Cultural (Bacharel)"
    
    facom_docs = [
        ("https://facom.ufba.br/portal/upload/arquivos/12_06_24_projeto_pedagogico%20jornalismo_FINAL_AJUSTES%20CARGA%20HORARIA.docx.pdf",
         jorn_dir, "Projeto_Pedagogico_Jornalismo_FACOM_2024.pdf"),
        ("https://facom.ufba.br/portal/upload/arquivos/Regulamento_TCC_Jornalismo.pdf",
         jorn_dir, "Regulamento_TCC_Jornalismo.pdf"),
        ("https://facom.ufba.br/portal/upload/arquivos/PPC_Producao_Cultural.pdf",
         prod_cult_dir, "Projeto_Pedagogico_Producao_Cultural_FACOM.pdf"),
        ("https://facom.ufba.br/portal/upload/arquivos/Regulamento_TCC_Producao.pdf",
         prod_c_dir, "Regulamento_TCC_Producao_em_Comunicacao.pdf")
    ]
    for url, target_dir, fname in facom_docs:
        download_and_save(url, target_dir, fname)

# =========================================================================
# 6. NUTRIÇÃO E GASTRONOMIA
# =========================================================================
def download_nutricao():
    print("\n>>> Processando Nutrição e Gastronomia...")
    nut_dir = EXP_AREAS_DIR / "Ciências da Saúde" / "Nutrição - Salvador (Bacharel)"
    gastro_dir = EXP_AREAS_DIR / "Ciências da Saúde" / "Gastronomia (Bacharel)"
    
    nut_docs = scrape_links("https://nutricao.ufba.br/tcc-nutricao")
    for purl, pname in nut_docs:
        download_and_save(purl, nut_dir, f"TCC_Nutricao_{pname}.pdf")
        
    gastro_docs = scrape_links("https://nutricao.ufba.br/tcc-gastro")
    for purl, pname in gastro_docs:
        download_and_save(purl, gastro_dir, f"TCC_Gastronomia_{pname}.pdf")

# =========================================================================
# 7. INSTITUTO DE QUÍMICA (IQ)
# =========================================================================
def download_quimica():
    print("\n>>> Processando Instituto de Química...")
    qui_b_dir = EXP_AREAS_DIR / "Ciências Exatas e da Terra" / "Química (Bacharel)"
    qui_l_dir = EXP_AREAS_DIR / "Ciências Exatas e da Terra" / "Química (Licenciatura)"
    qui_i_dir = EXP_AREAS_DIR / "Ciências Exatas e da Terra" / "Química Industrial (Bacharel)"
    
    q_docs = scrape_links("https://quimica.ufba.br/normas-regulamentos-e-legislacao-do-iq")
    for purl, pname in q_docs:
        for qdir in [qui_b_dir, qui_l_dir, qui_i_dir]:
            download_and_save(purl, qdir, f"IQ_{pname}.pdf")

# =========================================================================
# 8. INSTITUTO DE GEOCIÊNCIAS (IGEO)
# =========================================================================
def download_igeo():
    print("\n>>> Processando Instituto de Geociências (IGEO)...")
    igeo_dirs = [
        EXP_AREAS_DIR / "Ciências Exatas e da Terra" / "Geologia (Bacharel)",
        EXP_AREAS_DIR / "Ciências Exatas e da Terra" / "Geofísica (Bacharel)",
        EXP_AREAS_DIR / "Ciências Exatas e da Terra" / "Oceanografia (Bacharel)",
        EXP_AREAS_DIR / "Ciências Exatas e da Terra" / "Geografia (Bacharel)",
        EXP_AREAS_DIR / "Ciências Exatas e da Terra" / "Geografia (Licenciatura)"
    ]
    igeo_docs = scrape_links("https://igeo.ufba.br/documentos-e-formularios")
    for purl, pname in igeo_docs:
        for gdir in igeo_dirs:
            download_and_save(purl, gdir, f"IGEO_{pname}.pdf")

if __name__ == "__main__":
    download_ihac()
    download_bsi()
    download_ibio()
    download_fmb_to()
    download_facom()
    download_nutricao()
    download_quimica()
    download_igeo()
    print("\nLote 1 de downloads concluído com sucesso!")
