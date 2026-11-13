"""
Batch 2 de download de documentos específicos por curso
Cobre: IMS (Vitória da Conquista), ICTI (Camaçari), FACED (Pedagogia),
ISC (Saúde Coletiva), Teatro e Música.
"""

import os
import re
import sys
import io
import shutil
from pathlib import Path
import requests
import urllib3
import pypdf

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

# Cache em memória para evitar re-download do mesmo arquivo
URL_CACHE = {}

def download_and_save(url: str, dest_dir: Path, filename: str) -> bool:
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"
    
    clean_name = clean_filename(filename[:-4]) + ".pdf"
    dest_path = to_long_path(dest_dir / clean_name)
    
    if dest_path.exists() and dest_path.stat().st_size > 2000:
        return True

    # Se já foi baixado na sessão, copia do cache
    if url in URL_CACHE:
        content = URL_CACHE[url]
        dest_dir.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(content)
        print(f"  [COPIA-CACHE] Salvo: {clean_name} em {dest_dir.name}")
        return True

    try:
        r = requests.get(url, headers=HEADERS, verify=False, timeout=25, allow_redirects=True)
        if r.status_code == 200 and validate_pdf_bytes(r.content):
            URL_CACHE[url] = r.content
            dest_dir.mkdir(parents=True, exist_ok=True)
            with open(dest_path, "wb") as f:
                f.write(r.content)
            print(f"  [OK] Salvo: {clean_name} ({len(r.content):,} bytes) em {dest_dir.name}")
            return True
        else:
            print(f"  [FALHA] URL {url} retornou status={r.status_code}")
    except Exception as e:
        print(f"  [ERRO] Download falhou para {url}: {e}")
    return False

def run_batch2():
    base = EXP_AREAS_DIR
    print("=== INICIANDO BATCH 2 DE DOWNLOADS ESPECÍFICOS ===")

    # 1. ISC - Saúde Coletiva
    print("\n>>> 1. ISC (Saúde Coletiva)...")
    sc_dir = base / "Ciências da Saúde" / "Saúde Coletiva (Bacharel)"
    sc_docs = [
        ("https://isc.ufba.br/wp-content/uploads/2014/12/projeto_graduacao_saude_coletiva_ISC_UFBA_v10_21nov08.pdf", "Projeto_Pedagogico_Saude_Coletiva_ISC.pdf"),
        ("https://isc.ufba.br/wp-content/uploads/2014/12/folder_graduacao.pdf", "Guia_Informativo_Graduacao_Saude_Coletiva.pdf")
    ]
    for url, fname in sc_docs:
        download_and_save(url, sc_dir, fname)

    # 2. IMS - Vitória da Conquista (7 cursos)
    print("\n>>> 2. IMS Vitória da Conquista (7 Cursos)...")
    ims_map = [
        ("Biotecnologia", base / "Ciências Biológicas" / "Biotecnologia - Vitória da Conquista (Bacharel)", [
            ("https://ims.ufba.br/sites/ims.ufba.br/files/documentos/Regimento-Interno_Colegiado-de-Biotecnologia.pdf", "Regimento_Colegiado_Biotecnologia_IMS.pdf"),
            ("https://ims.ufba.br/sites/ims.ufba.br/files/paginas/planejamentosemestral/orientacao_academica_2026-1_-_biotecnologia.pdf", "Orientacao_Academica_Biotecnologia_IMS.pdf")
        ]),
        ("Ciências Biológicas", base / "Ciências Biológicas" / "Ciências Biológicas - Vitória da Conquista (Bacharel)", [
            ("https://ims.ufba.br/sites/ims.ufba.br/files/documentos/Regulamento-interno-do-colegiado-Ciencias-Biologicas-atualizado.pdf", "Regulamento_Colegiado_Ciencias_Biologicas_IMS.pdf"),
            ("https://ims.ufba.br/sites/ims.ufba.br/files/paginas/planejamentosemestral/orientacao_academica_-_ciencias_biologicas.pdf", "Orientacao_Academica_Ciencias_Biologicas_IMS.pdf")
        ]),
        ("Enfermagem", base / "Ciências da Saúde" / "Enfermagem - Vitória da Conquista (Bacharel)", [
            ("https://ims.ufba.br/sites/ims.ufba.br/files/documentos/cursos/projeto_pedagogico_do_curso_enfermagem_2024.1.pdf", "Projeto_Pedagogico_Enfermagem_IMS.pdf"),
            ("https://ims.ufba.br/sites/ims.ufba.br/files/documentos/Regulamento-interno-de-Colegiado-de-Enfermagem-.pdf", "Regulamento_Colegiado_Enfermagem_IMS.pdf"),
            ("https://ims.ufba.br/sites/ims.ufba.br/files/documentos/cursos/enfermagem_-_regulamento_interno_do_nde.pdf", "Regulamento_NDE_Enfermagem_IMS.pdf")
        ]),
        ("Farmácia", base / "Ciências da Saúde" / "Farmácia - Vitória da Conquista (Bacharel)", [
            ("https://ims.ufba.br/sites/ims.ufba.br/files/documentos/legislacao/colegiado/ppc_farmacia_2009.1_assinado.pdf", "Projeto_Pedagogico_Farmacia_IMS.pdf"),
            ("https://ims.ufba.br/sites/ims.ufba.br/files/documentos/Regulamento-interno-CCF_26.08.14.pdf", "Regimento_Colegiado_Farmacia_IMS.pdf")
        ]),
        ("Medicina", base / "Ciências da Saúde" / "Medicina - Vitória da Conquista (Bacharel)", [
            ("https://ims.ufba.br/sites/ims.ufba.br/files/documentos/cursos/projeto_politico_pedagogico_do_curso_-_ppc.pdf", "Projeto_Pedagogico_Medicina_IMS.pdf"),
            ("https://ims.ufba.br/sites/ims.ufba.br/files/documentos/cursos/2.regulamento_interno_do_colegiado_do_curso_medicina.pdf", "Regulamento_Colegiado_Medicina_IMS.pdf")
        ]),
        ("Nutrição", base / "Ciências da Saúde" / "Nutrição - Vitória da Conquista (Bacharel)", [
            ("https://ims.ufba.br/sites/ims.ufba.br/files/documentos/cursos/projetopedagogiconutricao.pdf", "Projeto_Pedagogico_Nutricao_IMS.pdf"),
            ("https://ims.ufba.br/sites/ims.ufba.br/files/documentos/legislacao/colegiado/nutricao/regimento_interno_do_colegiado_do_curso_de_nutricao_0.pdf", "Regimento_Colegiado_Nutricao_IMS.pdf")
        ]),
        ("Psicologia", base / "Ciências Humanas" / "Psicologia - Vitória da Conquista (Bacharel)", [
            ("http://www.ims.ufba.br/sites/ims.ufba.br/files/documentos/Normas-de-Est%C3%A1gio-Psicologia.pdf", "Normas_Estagio_Psicologia_IMS.pdf"),
            ("https://ims.ufba.br/sites/ims.ufba.br/files/documentos/legislacao/colegiado/regulamento_interno_psicologia.docx.pdf", "Regulamento_Colegiado_Psicologia_IMS.pdf"),
            ("http://www.ims.ufba.br/sites/ims.ufba.br/files/documentos/Regimento-Interno-do-Servi%C3%A7o-de-Psicologia.pdf", "Regimento_Servico_Psicologia_IMS.pdf")
        ])
    ]
    for cname, cdir, docs in ims_map:
        for url, fname in docs:
            download_and_save(url, cdir, fname)

    # 3. ICTI Camaçari (Engenharia de Produção)
    print("\n>>> 3. ICTI Camaçari (Engenharia de Produção)...")
    icti_dir = base / "Engenharias" / "Engenharia de Produção - Camaçari (Bacharel)"
    icti_docs = [
        ("https://icti.ufba.br/sites/icti.ufba.br/files/res_004_-_ligas_academicas_vinculadas_ao_icti.pdf", "Resolucao_04_2024_Ligas_Academicas_ICTI.pdf"),
        ("https://icti.ufba.br/sites/icti.ufba.br/files/res_003_-_normas_conhecimento_previo.pdf", "Resolucao_03_2023_Conhecimento_Previo_ICTI.pdf")
    ]
    for url, fname in icti_docs:
        download_and_save(url, icti_dir, fname)

    # 4. FACED (Pedagogia)
    print("\n>>> 4. FACED (Pedagogia)...")
    ped_targets = [
        base / "Ciências Humanas" / "Pedagogia - Salvador Diurno (Licenciatura)",
        base / "Ciências Humanas" / "Pedagogia - Salvador Noturno (Licenciatura)",
        base / "Ciências Humanas" / "Pedagogia - EAD (Licenciatura)"
    ]
    for pdir in ped_targets:
        download_and_save("https://faced.ufba.br/sites/faced.ufba.br/files/curriculo_do_curso_de_licenciatura_em_pedagogia.pdf",
                          pdir, "Projeto_Pedagogico_Curriculo_Pedagogia.pdf")
        if "EAD" in pdir.name:
            download_and_save("https://faced.ufba.br/sites/faced.ufba.br/files/documento_ead_faced.pdf",
                              pdir, "Diretrizes_Educacao_a_Distancia_FACED.pdf")

    # 5. Escola de Teatro (5 cursos)
    print("\n>>> 5. Escola de Teatro...")
    teatro_reg_url = "https://escola-de-teatro.cdn.prismic.io/escola-de-teatro/a2c3bc3b-3da5-4086-8bfe-37062aa7a0be_Regimento+Interno+da+Escola+de+Teatro+da+UFBA.pdf"
    teatro_dirs = [
        base / "Linguística, Letras e Artes" / "Artes Cênicas - Cenografia (Bacharel)",
        base / "Linguística, Letras e Artes" / "Artes Cênicas - Direção Teatral (Bacharel)",
        base / "Linguística, Letras e Artes" / "Artes Cênicas - Interpretação Teatral (Bacharel)",
        base / "Linguística, Letras e Artes" / "Teatro (Licenciatura)",
        base / "Linguística, Letras e Artes" / "Teatro - EAD (Licenciatura)"
    ]
    for tdir in teatro_dirs:
        download_and_save(teatro_reg_url, tdir, "Regimento_Interno_Escola_de_Teatro.pdf")

    # 6. Escola de Música (13 cursos)
    print("\n>>> 6. Escola de Música...")
    musica_doc_url = "https://dmusufba.com/wp-content/uploads/Oferta-2026.2-Relatorio-Geral-das-Disciplinas.pdf"
    musica_sigaa_url = "https://dmusufba.com/wp-content/uploads/Como-efetuar-matricula-no-SIGAA.pdf"
    musica_dirs = [
        base / "Linguística, Letras e Artes" / "Música (Licenciatura)",
        base / "Linguística, Letras e Artes" / "Música - EAD (Licenciatura)",
        base / "Linguística, Letras e Artes" / "Música Popular (Bacharel)",
        base / "Linguística, Letras e Artes" / "Canto (Bacharel)",
        base / "Linguística, Letras e Artes" / "Composição e Regência (Bacharel)",
        base / "Linguística, Letras e Artes" / "Instrumento - Clarinete (Bacharel)",
        base / "Linguística, Letras e Artes" / "Instrumento - Flauta (Bacharel)",
        base / "Linguística, Letras e Artes" / "Instrumento - Percussão (Bacharel)",
        base / "Linguística, Letras e Artes" / "Instrumento - Piano (Bacharel)",
        base / "Linguística, Letras e Artes" / "Instrumento - Trompete (Bacharel)",
        base / "Linguística, Letras e Artes" / "Instrumento - Violino (Bacharel)",
        base / "Linguística, Letras e Artes" / "Instrumento - Violoncelo (Bacharel)",
        base / "Linguística, Letras e Artes" / "Instrumento - Violão (Bacharel)"
    ]
    for mdir in musica_dirs:
        download_and_save(musica_doc_url, mdir, "Relatorio_Geral_Disciplinas_Musica.pdf")
        download_and_save(musica_sigaa_url, mdir, "Guia_Matricula_Musica_SIGAA.pdf")

    print("\n=== BATCH 2 CONCLUÍDO COM SUCESSO! ===")

if __name__ == "__main__":
    run_batch2()

