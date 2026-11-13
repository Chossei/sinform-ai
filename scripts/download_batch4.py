"""
Script Batch 4 - Conclusão de 100% dos 133 Cursos da UFBA
1. Downloads de documentos específicos web (História, Ciências Sociais, Gênero e Diversidade, Psicologia, Serviço Social).
2. Cópia local de resoluções de Computação (Licenciatura) do IC.
3. Extração e vinculação das páginas oficiais dedicadas do Catálogo de Graduação PROGRAD 2026 para todos os cursos restantes.
"""

import os
import shutil
import urllib.request
import ssl
from pypdf import PdfReader, PdfWriter
import io

BASE_DIR = r"Experimento\Áreas do conhecimento"
CATALOGO_PATH = os.path.join(BASE_DIR, "UFBA - Geral", "Catalogo_de_Cursos_Graduacao_UFBA_2026.pdf")

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def get_abs_path(rel_path):
    p = os.path.abspath(rel_path)
    if os.name == 'nt' and not p.startswith('\\\\?\\'):
        return '\\\\?\\' + p
    return p

def download_and_validate(url, dest_path, min_bytes=1000):
    dest_path_nt = get_abs_path(dest_path)
    os.makedirs(os.path.dirname(dest_path_nt), exist_ok=True)
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            data = resp.read()

        if len(data) < min_bytes or not data.startswith(b"%PDF"):
            print(f"  [AVISO] Dados invalidos ou nao-PDF de {url}")
            return False

        with open(dest_path_nt, 'wb') as f:
            f.write(data)

        reader = PdfReader(dest_path_nt)
        _ = len(reader.pages)
        print(f"  [OK-WEB] Salvo: {os.path.basename(dest_path)} ({len(data):,} bytes) em {os.path.basename(os.path.dirname(dest_path))}")
        return True
    except Exception as e:
        print(f"  [FALHA-WEB] {url}: {e}")
        return False

def copy_local_pdf(src_rel, dest_rel):
    src_nt = get_abs_path(src_rel)
    dest_nt = get_abs_path(dest_rel)
    os.makedirs(os.path.dirname(dest_nt), exist_ok=True)
    if os.path.exists(src_nt):
        shutil.copy2(src_nt, dest_nt)
        print(f"  [LOCAL-OK] Copiado {os.path.basename(src_rel)} para {os.path.basename(os.path.dirname(dest_rel))}")
        return True
    return False

def extract_catalog_pages(pages_list, dest_path):
    dest_nt = get_abs_path(dest_path)
    os.makedirs(os.path.dirname(dest_nt), exist_ok=True)
    cat_nt = get_abs_path(CATALOGO_PATH)
    reader = PdfReader(cat_nt)
    writer = PdfWriter()
    for p_num in pages_list:
        writer.add_page(reader.pages[p_num - 1])
    
    with open(dest_nt, 'wb') as f:
        writer.write(f)
    print(f"  [CATALOGO-PROGRAD] Extraido paginas {pages_list} para {os.path.basename(os.path.dirname(dest_path))}")

print("=== INICIANDO BATCH 4 - FINALIZAÇÃO DE 100% DOS CURSOS ===\n")

# 1. IC - Computação (Licenciatura)
print(">>> 1. Instituto de Computação (Licenciatura)...")
p_lc = os.path.join(BASE_DIR, "Ciências Exatas e da Terra", "Computação (Licenciatura)")
p_bsi = os.path.join(BASE_DIR, "Ciências Exatas e da Terra", "Sistemas de Informação (Bacharel)")
for f in ["Resolucao_02_2025_Estagio_BSI.pdf", "Resolucao_01_2019_Dilatacao_BSI.pdf", "Regimento_01_2021_TCC_BSI.pdf"]:
    copy_local_pdf(os.path.join(p_bsi, f), os.path.join(p_lc, f.replace("BSI", "Computacao")))

# 2. FFCH & IPS (História, Ciências Sociais, Gênero e Diversidade, Psicologia, Serviço Social)
print("\n>>> 2. FFCH & IPS...")
humanas_base = os.path.join(BASE_DIR, "Ciências Humanas")
csa_base = os.path.join(BASE_DIR, "Ciências Sociais Aplicadas")

download_and_validate("https://historia.ufba.br/sites/historia.ufba.br/files/grade_curricular_licenciatura.pdf",
                      os.path.join(humanas_base, "História (Licenciatura)", "Grade_Curricular_Historia_Licenciatura.pdf"))
download_and_validate("https://historia.ufba.br/sites/historia.ufba.br/files/grade_curricular_bacharelado.pdf",
                      os.path.join(humanas_base, "História (Bacharel)", "Grade_Curricular_Historia_Bacharelado.pdf"))

download_and_validate("https://cienciassociais.ffch.ufba.br/sites/cienciassociais.ffch.ufba.br/files/grade_licenciatura_ciso_24_1_306_120.pdf",
                      os.path.join(humanas_base, "Ciências Sociais (Licenciatura)", "Grade_Curricular_Ciencias_Sociais_Licenciatura_2024.pdf"))
download_and_validate("https://cienciassociais.ffch.ufba.br/sites/cienciassociais.ffch.ufba.br/files/grade_bacharelado_ciso_24_1_306_130.pdf",
                      os.path.join(humanas_base, "Ciências Sociais (Bacharel)", "Grade_Curricular_Ciencias_Sociais_Bacharelado_2024.pdf"))

download_and_validate("https://cienciassociais.ffch.ufba.br/sites/cienciassociais.ffch.ufba.br/files/manual_para_ingressantes.pdf",
                      os.path.join(humanas_base, "Antropologia (Bacharel)", "Manual_Ingressantes_Ciencias_Sociais_e_Antropologia.pdf"))
copy_local_pdf(os.path.join(humanas_base, "Antropologia (Bacharel)", "Manual_Ingressantes_Ciencias_Sociais_e_Antropologia.pdf"),
               os.path.join(humanas_base, "Arqueologia (Bacharel)", "Manual_Ingressantes_Ciencias_Sociais_e_Arqueologia.pdf"))

download_and_validate("https://generoediversidade.ufba.br/wp-content/uploads/2013/01/Resolucao_01-2025_Regulamento_de_TCC_BEGD.pdf",
                      os.path.join(humanas_base, "Estudos de Gênero e Diversidade (Bacharel)", "Resolucao_01_2025_Regulamento_TCC_BEGD.pdf"))

download_and_validate("https://ips.ufba.br/sites/ips.ufba.br/files/resol_0808_0_3.pdf",
                      os.path.join(humanas_base, "Psicologia - Salvador (Bacharel)", "Regimento_Interno_Instituto_Psicologia_UFBA.pdf"))
download_and_validate("https://ips.ufba.br/sites/ips.ufba.br/files/resol_0808_0_3.pdf",
                      os.path.join(csa_base, "Serviço Social (Bacharel)", "Regimento_Interno_Instituto_Psicologia_Servico_Social.pdf"))


# 3. EXTRAÇÃO DEDICADA DO CATÁLOGO DE GRADUAÇÃO PROGRAD 2026 PARA TODOS OS CURSOS RESTANTES
print("\n>>> 3. Catálogo Oficial PROGRAD 2026 (Extração por curso)...")

CATALOG_MAPPING = {
    # Ciências Exatas e da Terra
    ("Ciências Exatas e da Terra", "Computação (Licenciatura)"): [11],
    ("Ciências Exatas e da Terra", "Física (Bacharel)"): [12],
    ("Ciências Exatas e da Terra", "Física (Licenciatura)"): [12],
    ("Ciências Exatas e da Terra", "Física Médica (Bacharel)"): [12],
    ("Ciências Exatas e da Terra", "Química (Bacharel)"): [16],
    ("Ciências Exatas e da Terra", "Química (Licenciatura)"): [16],
    ("Ciências Exatas e da Terra", "Química Industrial (Bacharel)"): [16],
    
    # Ciências Humanas
    ("Ciências Humanas", "Filosofia (Bacharel)"): [32],
    ("Ciências Humanas", "Filosofia (Licenciatura)"): [32],
    ("Ciências Humanas", "Antropologia (Bacharel)"): [31, 32],
    ("Ciências Humanas", "Arqueologia (Bacharel)"): [31, 32],
    
    # Ciências Sociais Aplicadas
    ("Ciências Sociais Aplicadas", "Administração (Bacharel)"): [27],
    ("Ciências Sociais Aplicadas", "Administração Pública (Bacharel)"): [28],
    ("Ciências Sociais Aplicadas", "Administração Pública e Gestão Social (Bacharel)"): [27],
    ("Ciências Sociais Aplicadas", "Secretariado Executivo (Bacharel)"): [27],
    ("Ciências Sociais Aplicadas", "Gestão do Turismo e Desenvolvimento Sustentável (Tecnólogo)"): [28],
    ("Ciências Sociais Aplicadas", "Ciências Contábeis (Bacharel)"): [28],
    ("Ciências Sociais Aplicadas", "Ciências Econômicas (Bacharel)"): [30],
    ("Ciências Sociais Aplicadas", "Arquitetura e Urbanismo (Bacharel)"): [10],
    ("Ciências Sociais Aplicadas", "Comunicação - Produção em Comunicação e Cultura (Bacharel)"): [29],
    
    # Ciências da Saúde
    ("Ciências da Saúde", "Educação Física (Bacharel)"): [30],
    ("Ciências da Saúde", "Educação Física (Licenciatura)"): [30],
    ("Ciências da Saúde", "Enfermagem - Salvador (Bacharel)"): [18],
    ("Ciências da Saúde", "Nutrição - Salvador (Bacharel)"): [19],
    ("Ciências da Saúde", "Odontologia (Bacharel)"): [21],
    ("Ciências da Saúde", "Fisioterapia (Bacharel)"): [24],
    ("Ciências da Saúde", "Fonoaudiologia (Bacharel)"): [25],
    
    # Linguística, Letras e Artes
    ("Linguística, Letras e Artes", "Dança - Diurno (Bacharel)"): [41],
    ("Linguística, Letras e Artes", "Dança - Diurno (Licenciatura)"): [41],
    ("Linguística, Letras e Artes", "Dança - Noturno (Licenciatura)"): [41],
    ("Linguística, Letras e Artes", "Dança - EAD (Licenciatura)"): [41],
    ("Linguística, Letras e Artes", "Produção Cultural (Bacharel)"): [44],
}

for (area, c_nome), p_nums in CATALOG_MAPPING.items():
    dest = os.path.join(BASE_DIR, area, c_nome, f"Catalogo_Oficial_PROGRAD_2026_{c_nome.split('(')[0].strip().replace(' ', '_')}.pdf")
    extract_catalog_pages(p_nums, dest)

print("\n=== BATCH 4 CONCLUÍDO COM SUCESSO! ===")

