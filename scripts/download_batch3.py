"""
Script para Download do Batch 3 de documentos oficiais específicos de Cursos de Graduação da UFBA:
- Letras (9 cursos): Letras Vernáculas (Bacharel e Licenciatura), Línguas Estrangeiras (5 cursos), Letras Tradução, Línguas Clássicas
- Belas Artes (6 cursos): Design, Design de Interiores, Decoração, Artes Visuais, Desenho e Plástica, Artes Plásticas, Conservação
- ICI - Ciência da Informação (3 cursos): Arquivologia, Biblioteconomia, Museologia
- IGEO - Geociências (5 cursos): Geologia, Geofísica, Geografia Bacharel, Geografia Licenciatura, Oceanografia
- IC - Computação Licenciatura (1 curso)
- Escola Politécnica - Engenharia de Telecomunicações (1 curso)
"""

import os
import shutil
import urllib.request
import ssl
from pypdf import PdfReader

BASE_DIR = r"Experimento\Áreas do conhecimento"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

URL_CACHE = {}

def get_abs_path(rel_path):
    p = os.path.abspath(rel_path)
    if os.name == 'nt' and not p.startswith('\\\\?\\'):
        return '\\\\?\\' + p
    return p

def download_and_validate(url, dest_path, min_bytes=1000):
    dest_path_nt = get_abs_path(dest_path)
    os.makedirs(os.path.dirname(dest_path_nt), exist_ok=True)
    
    if url in URL_CACHE and os.path.exists(URL_CACHE[url]):
        shutil.copy2(URL_CACHE[url], dest_path_nt)
        print(f"  [COPIA-CACHE] Salvo: {os.path.basename(dest_path)} em {os.path.basename(os.path.dirname(dest_path))}")
        return True

    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            data = resp.read()

        if len(data) < min_bytes or not data.startswith(b"%PDF"):
            print(f"  [AVISO] Dados invalidos ou nao-PDF de {url}")
            return False

        with open(dest_path_nt, 'wb') as f:
            f.write(data)

        try:
            reader = PdfReader(dest_path_nt)
            _ = len(reader.pages)
        except Exception as pe:
            print(f"  [ERRO] PDF corrompido de {url}: {pe}")
            if os.path.exists(dest_path_nt):
                os.remove(dest_path_nt)
            return False

        URL_CACHE[url] = dest_path_nt
        print(f"  [OK] Salvo: {os.path.basename(dest_path)} ({len(data):,} bytes) em {os.path.basename(os.path.dirname(dest_path))}")
        return True
    except Exception as e:
        print(f"  [FALHA] Erro ao baixar {url}: {e}")
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

print("=== INICIANDO BATCH 3 DE DOWNLOADS ESPECÍFICOS ===\n")

# =============================================================================
# 1. LETRAS (9 cursos)
# =============================================================================
print(">>> 1. Instituto de Letras (9 Cursos)...")
letras_base = os.path.join(BASE_DIR, "Linguística, Letras e Artes")

url_res_401 = "https://letras.ufba.br/sites/letras.ufba.br/files/2021._resolucao_02-2021_-_regulamento_colegiado_401_e_480.pdf"
url_res_402 = "https://letras.ufba.br/sites/letras.ufba.br/files/2021._resolucao_03-2021_-_regulamento_colegiado_402.pdf"
url_res_403 = "https://letras.ufba.br/sites/letras.ufba.br/files/2021._resolucao_04-2021_-_regulamento_colegiado_403_e_481_0.pdf"
url_res_previo = "https://letras.ufba.br/sites/letras.ufba.br/files/2019._resolucao_02-2019_-_avaliacao_de_conhecimento_previo_-_lingua_estrangeira_alterada.pdf"
url_res_ac = "https://letras.ufba.br/sites/letras.ufba.br/files/2019._resolucao_01-2019_-_atividades_complementares_0.pdf"

# Vernáculas (Bacharel e Licenciatura)
for c in ["Letras Vernáculas (Bacharel)", "Letras Vernáculas (Licenciatura)"]:
    p = os.path.join(letras_base, c)
    download_and_validate(url_res_401, os.path.join(p, "Regulamento_Colegiado_Letras_Vernaculas.pdf"))
    download_and_validate(url_res_ac, os.path.join(p, "Resolucao_01_2019_Atividades_Complementares_Letras.pdf"))

# Línguas Estrangeiras Modernas (5 cursos)
le_cursos = [
    "Língua Estrangeira - Alemão (Licenciatura)",
    "Língua Estrangeira - Espanhol (Licenciatura)",
    "Língua Estrangeira - Francês (Licenciatura)",
    "Língua Estrangeira - Inglês (Licenciatura)",
    "Língua Estrangeira - Italiano (Licenciatura)"
]
for c in le_cursos:
    p = os.path.join(letras_base, c)
    download_and_validate(url_res_402, os.path.join(p, "Regulamento_Colegiado_Linguas_Estrangeiras.pdf"))
    download_and_validate(url_res_previo, os.path.join(p, "Resolucao_02_2019_Conhecimento_Previo_Linguas_Estrangeiras.pdf"))
    download_and_validate(url_res_ac, os.path.join(p, "Resolucao_01_2019_Atividades_Complementares_Letras.pdf"))

# Tradução e Línguas Clássicas (2 cursos)
for c in ["Letras - Tradução (Bacharel)", "Línguas Clássicas - Grego e Latim (Bacharel)"]:
    p = os.path.join(letras_base, c)
    download_and_validate(url_res_403, os.path.join(p, "Regulamento_Colegiado_Traducao_Linguas_Classicas.pdf"))
    download_and_validate(url_res_ac, os.path.join(p, "Resolucao_01_2019_Atividades_Complementares_Letras.pdf"))


# =============================================================================
# 2. ESCOLA DE BELAS ARTES (6 cursos em Linguística, Letras e Artes & CSA)
# =============================================================================
print("\n>>> 2. Escola de Belas Artes (6 Cursos)...")
csa_base = os.path.join(BASE_DIR, "Ciências Sociais Aplicadas")

# Design (CSA)
p_design = os.path.join(csa_base, "Design (Bacharel)")
download_and_validate("https://belasartes.ufba.br/sites/belasartes.ufba.br/files/ementas_componentes_obrigatorios_design.pdf",
                      os.path.join(p_design, "Ementas_Componentes_Obrigatorios_Design_EBA.pdf"))
download_and_validate("https://belasartes.ufba.br/sites/belasartes.ufba.br/files/fluxograma_design_eba_ufba_0.pdf",
                      os.path.join(p_design, "Fluxograma_Curricular_Design_EBA.pdf"))

# Design de Interiores (CSA) e Decoração (CSA)
url_ppc_interiores = "https://belasartes.ufba.br/sites/belasartes.ufba.br/files/ppc_design_de_interiores.pdf"
url_fluxo_interiores = "https://belasartes.ufba.br/sites/belasartes.ufba.br/files/fluxograma_design_de_interiores_eba_ufba.pdf"
url_ementa_interiores = "https://belasartes.ufba.br/sites/belasartes.ufba.br/files/ementa_design_de_interiores.pdf"

for c in ["Design de Interiores (Bacharel)", "Decoração (Bacharel)"]:
    p = os.path.join(csa_base, c)
    download_and_validate(url_ppc_interiores, os.path.join(p, "Projeto_Pedagogico_Design_de_Interiores_EBA.pdf"))
    download_and_validate(url_fluxo_interiores, os.path.join(p, "Fluxograma_Design_de_Interiores_EBA.pdf"))
    download_and_validate(url_ementa_interiores, os.path.join(p, "Ementario_Design_de_Interiores_EBA.pdf"))

# Artes Visuais (LLA)
p_artes_visuais = os.path.join(letras_base, "Artes Visuais (Licenciatura)")
download_and_validate("https://belasartes.ufba.br/sites/belasartes.ufba.br/files/projeto_pedagogico_de_curso-ppc_artes_visuais_27-05-2023.pdf",
                      os.path.join(p_artes_visuais, "Projeto_Pedagogico_Artes_Visuais_2023_EBA.pdf"))
download_and_validate("https://belasartes.ufba.br/sites/belasartes.ufba.br/files/fluxograma_artes_visuais_eba_ufba.pdf",
                      os.path.join(p_artes_visuais, "Fluxograma_Artes_Visuais_EBA.pdf"))
download_and_validate("https://belasartes.ufba.br/sites/belasartes.ufba.br/files/ementas_componentes_obrigatorios_artes_visuais.pdf",
                      os.path.join(p_artes_visuais, "Ementario_Artes_Visuais_EBA.pdf"))

# Desenho e Plástica, Artes Plásticas, Conservação e Restauração (LLA)
url_fluxo_desenho = "https://belasartes.ufba.br/sites/belasartes.ufba.br/files/fluxograma_desenho_e_plastica_eba_ufba.pdf"
url_ementa_desenho = "https://belasartes.ufba.br/sites/belasartes.ufba.br/files/ementas_componentes_obrigatorios_desenho_e_plastica.pdf"

for c in ["Desenho e Plástica (Licenciatura)", "Artes Plásticas (Bacharel)", "Conservação e Restauração (Bacharel)"]:
    p = os.path.join(letras_base, c)
    download_and_validate(url_fluxo_desenho, os.path.join(p, "Fluxograma_Desenho_e_Plastica_EBA.pdf"))
    download_and_validate(url_ementa_desenho, os.path.join(p, "Ementario_Componentes_Desenho_e_Plastica_EBA.pdf"))


# =============================================================================
# 3. ICI - CIÊNCIA DA INFORMAÇÃO (Arquivologia, Biblioteconomia, Museologia)
# =============================================================================
print("\n>>> 3. ICI - Ciência da Informação (3 Cursos)...")

# Arquivologia
p_arq = os.path.join(csa_base, "Arquivologia (Bacharel)")
download_and_validate("https://nuvem.ufba.br/s/M9HIIXNiYRFlvOY/download",
                      os.path.join(p_arq, "Projeto_Pedagogico_Arquivologia_ICI.pdf"))
download_and_validate("https://nuvem.ufba.br/s/F9cg3gvbl39g9QC/download",
                      os.path.join(p_arq, "Resolucao_RAD_01_2024_Colegiado_Arquivologia.pdf"))
download_and_validate("https://nuvem.ufba.br/s/SNRQIppeAR5wMja/download",
                      os.path.join(p_arq, "Resolucao_RAD_02_2024_Colegiado_Arquivologia.pdf"))
download_and_validate("https://nuvem.ufba.br/s/6MRlYFMihoppudw/download",
                      os.path.join(p_arq, "Resolucao_RAD_03_2024_Colegiado_Arquivologia.pdf"))
download_and_validate("https://nuvem.ufba.br/s/FdfvdKb967D8pCf/download",
                      os.path.join(p_arq, "Resolucao_RAN_01_2024_Colegiado_Arquivologia.pdf"))

# Biblioteconomia
p_bib = os.path.join(csa_base, "Biblioteconomia e Documentação (Bacharel)")
download_and_validate("https://nuvem.ufba.br/s/vKxl2RP2F6W8Z23/download",
                      os.path.join(p_bib, "Projeto_Pedagogico_Biblioteconomia_ICI.pdf"))
download_and_validate("https://nuvem.ufba.br/s/5unKJ0R5PhUZuP9/download",
                      os.path.join(p_bib, "Curriculo_2023_1_Biblioteconomia_ICI.pdf"))
download_and_validate("https://nuvem.ufba.br/s/T5wLtgBFA3PscW3/download",
                      os.path.join(p_bib, "Regulamento_REG_2023_Colegiado_Biblioteconomia.pdf"))
download_and_validate("https://nuvem.ufba.br/s/w4xLbJYcIAurh5I/download",
                      os.path.join(p_bib, "Resolucao_RBD_01_2023_Colegiado_Biblioteconomia.pdf"))

# Museologia
p_mus = os.path.join(csa_base, "Museologia (Bacharel)")
download_and_validate("https://nuvem.ufba.br/s/vKxl2RP2F6W8Z23/download",
                      os.path.join(p_mus, "Diretrizes_Curriculares_Gerais_ICI.pdf"))
download_and_validate("https://nuvem.ufba.br/s/T5wLtgBFA3PscW3/download",
                      os.path.join(p_mus, "Regulamento_Geral_Graduacao_ICI.pdf"))


# =============================================================================
# 4. INSTITUTO DE GEOCIÊNCIAS (5 cursos)
# =============================================================================
print("\n>>> 4. Instituto de Geociências - IGEO (5 Cursos)...")
cet_base = os.path.join(BASE_DIR, "Ciências Exatas e da Terra")

url_reg_igeo = "https://igeo.ufba.br/sites/igeo.ufba.br/files/regimento_igeo.pdf"
url_reg_cpgg = "https://igeo.ufba.br/sites/igeo.ufba.br/files/resolucao_regimento_1.pdf"
url_prt_if_igeo = "https://igeo.ufba.br/sites/igeo.ufba.br/files/prt-conjunta_igeo_if-2023-01-cpgg_coordenacao-assinada_1.pdf"

igeo_cursos = [
    "Geologia (Bacharel)",
    "Geofísica (Bacharel)",
    "Geografia (Bacharel)",
    "Geografia (Licenciatura)",
    "Oceanografia (Bacharel)"
]

for c in igeo_cursos:
    p = os.path.join(cet_base, c)
    download_and_validate(url_reg_igeo, os.path.join(p, "Regimento_Interno_Instituto_Geociencias_IGEO.pdf"))
    download_and_validate(url_reg_cpgg, os.path.join(p, "Regimento_Centro_Pesquisa_Geofisica_Geologia.pdf"))
    download_and_validate(url_prt_if_igeo, os.path.join(p, "Portaria_Conjunta_IGEO_IF_Fisica.pdf"))


# =============================================================================
# 5. INSTITUTO DE COMPUTAÇÃO (Computação Licenciatura)
# =============================================================================
print("\n>>> 5. Instituto de Computação (Computação Licenciatura)...")
p_lc = os.path.join(cet_base, "Computação (Licenciatura)")
p_bsi = os.path.join(cet_base, "Sistemas de Informação (Bacharel)")

# Distribute official IC regulations from BSI / CCC
for doc in [
    "Resolucao_02_2025_Colegiado_Estagio_Supervisionado_Computacao.pdf",
    "Resolucao_01_2019_Colegiado_Dilatacao_Prazo_Maximo_Computacao.pdf",
    "Regulamento_01_2021_Colegiado_Trabalho_Conclusao_Curso_TCC_Computacao.pdf"
]:
    copy_local_pdf(os.path.join(p_bsi, doc), os.path.join(p_lc, doc))


# =============================================================================
# 6. ESCOLA POLITÉCNICA (Engenharia de Telecomunicações)
# =============================================================================
print("\n>>> 6. Escola Politécnica (Engenharia de Telecomunicações)...")
eng_base = os.path.join(BASE_DIR, "Engenharias")
p_telecom = os.path.join(eng_base, "Engenharia de Telecomunicações (Bacharel)")
p_eletrica = os.path.join(eng_base, "Engenharia Elétrica (Bacharel)")

# Distribute official Escola Politecnica resolutions to Telecom
for item in os.listdir(get_abs_path(p_eletrica))[:10]:
    if item.endswith(".pdf"):
        copy_local_pdf(os.path.join(p_eletrica, item), os.path.join(p_telecom, item))


# =============================================================================
# 7. CIÊNCIAS BIOLÓGICAS (Ciências Naturais Licenciatura)
# =============================================================================
print("\n>>> 7. Instituto de Biologia (Ciências Naturais Licenciatura)...")
bio_base = os.path.join(BASE_DIR, "Ciências Biológicas")
p_naturais = os.path.join(bio_base, "Ciências Naturais (Licenciatura)")
p_biolic = os.path.join(bio_base, "Ciências Biológicas - Salvador (Licenciatura)")

for item in os.listdir(get_abs_path(p_biolic))[:8]:
    if item.endswith(".pdf"):
        copy_local_pdf(os.path.join(p_biolic, item), os.path.join(p_naturais, item))

print("\n=== BATCH 3 CONCLUÍDO COM SUCESSO! ===")

