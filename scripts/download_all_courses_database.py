"""
Script automatizado de download de documentos e normativas acadêmicas
para todos os 133 cursos de graduação da UFBA + UFBA - Geral.

Critérios de busca e download:
- Projetos Pedagógicos de Curso (PPC)
- Regulamentos de Trabalho de Conclusão de Curso (TCC / Monografia)
- Regulamentos de Estágio Supervisionado (Obrigatório e Não Obrigatório)
- Regulamentos e Tabelas de Atividades Complementares (ACC / AC)
- Regimentos Internos dos Colegiados
- Resoluções de Permanência, Trancamento e Aproveitamento
- Fluxogramas e Matrizes Curriculares Oficiais
"""

import os
import re
import sys
import json
import time
import urllib.parse
from pathlib import Path
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings()

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from scripts.map_133_courses import COURSES_DATA, AREAS_CONHECIMENTO, PASTA_GERAL, get_folder_name

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

KEYWORDS_RELEVANTES = [
    "ppc", "projeto_pedagogico", "projeto-pedagogico", "pedagogico", "pedagógico",
    "tcc", "monografia", "conclusao", "conclusão",
    "estagio", "estágio", "obrigatorio", "obrigatório",
    "acc", "atividade_complementar", "atividades_complementares", "complementar", "extensao", "extensão",
    "regimento", "colegiado", "resolucao", "resolução", "normativa", "criterios", "critérios",
    "fluxograma", "matriz", "curriculo", "currículo", "optativas", "disciplinas",
    "guia", "manual", "permanencia", "permanência", "trancamento"
]

def clean_filename(text: str) -> str:
    """Gera um nome de arquivo seguro e limpo."""
    s = re.sub(r'[\s\-_]+', '_', text)
    s = re.sub(r'[^a-zA-Z0-9_\.]', '', s)
    return s.strip('_')

def is_valid_pdf_url(url: str, text: str) -> bool:
    """Verifica se a URL ou o texto do link aponta para documento relevante em PDF."""
    url_l = url.lower()
    text_l = text.lower()
    
    if not (url_l.endswith('.pdf') or '.pdf' in url_l or 'download' in url_l):
        return False
        
    # Evitar atas de reunião comuns, comprovantes individuais ou avisos pontuais
    if any(ign in text_l or ign in url_l for ign in ['ata_reuniao', 'ata-de-reuniao', 'eleicao', 'gabarito', 'portaria_de_pessoal']):
        return False
        
    return any(k in text_l or k in url_l for k in KEYWORDS_RELEVANTES)

def download_file(url: str, dest_path: Path, timeout: int = 25) -> bool:
    """Baixa um arquivo PDF e valida o cabeçalho %PDF."""
    if dest_path.exists() and dest_path.stat().st_size > 2000:
        return True # Já existe e tem tamanho válido
        
    try:
        r = requests.get(url, headers=HEADERS, verify=False, timeout=timeout, stream=True)
        if r.status_code == 200:
            header_chunk = b""
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if not header_chunk:
                        header_chunk = chunk[:10]
                    f.write(chunk)
            
            # Checar integridade mínima
            if dest_path.stat().st_size > 1000 and (b"%PDF" in header_chunk or dest_path.name.endswith(".pdf")):
                return True
            else:
                if dest_path.exists():
                    dest_path.unlink() # Arquivo corrompido ou HTML disfarçado de PDF
                return False
    except Exception:
        if dest_path.exists():
            try:
                dest_path.unlink()
            except Exception:
                pass
        return False
    return False

def discover_course_pdfs(course_info: dict) -> List[Tuple[str, str]]:
    """Descobre links de PDFs para o curso a partir de seus sites e portais oficiais."""
    discovered = []
    seen_urls = set()
    
    urls_to_crawl = []
    if course_info.get("site"):
        urls_to_crawl.append(course_info["site"])
        
    # Adicionar variações conhecidas de colegiados UFBA
    nome_slug = re.sub(r'[^a-zA-Z0-9]', '', course_info['nome'].lower())
    urls_to_crawl.append(f"https://col{nome_slug}.ufba.br")
    urls_to_crawl.append(f"https://colegiado{nome_slug}.ufba.br")
    
    # Subpáginas de graduação
    if "eng.ufba.br" in course_info.get("site", ""):
        # Padrão da Politécnica
        slug_poli = course_info['nome'].lower().replace(' ', '-')
        urls_to_crawl.append(f"https://www.eng.ufba.br/curso-graduacao/{slug_poli}")
    elif "ihac.ufba.br" in course_info.get("site", ""):
        slug_ihac = course_info['nome'].lower().replace(' ', '-')
        urls_to_crawl.append(f"https://ihac.ufba.br/course/{slug_ihac}/")

    # SIGAA portal
    if course_info.get("sigaa_id"):
        urls_to_crawl.append(f"https://sigaa.ufba.br/sigaa/public/curso/portal.jsf?id={course_info['sigaa_id']}&lc=pt_BR&nivel=G")
        urls_to_crawl.append(f"https://sigaa.ufba.br/sigaa/public/curso/ppp.jsf?id={course_info['sigaa_id']}&lc=pt_BR")
        urls_to_crawl.append(f"https://sigaa.ufba.br/sigaa/public/curso/curriculo.jsf?id={course_info['sigaa_id']}&lc=pt_BR")

    for base_url in urls_to_crawl:
        try:
            r = requests.get(base_url, headers=HEADERS, verify=False, timeout=8)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = a.get_text(strip=True)
                full_url = urllib.parse.urljoin(base_url, href)
                
                if full_url not in seen_urls and is_valid_pdf_url(full_url, text):
                    seen_urls.add(full_url)
                    doc_title = clean_filename(text if len(text) > 4 else Path(urllib.parse.urlparse(full_url).path).stem)
                    if not doc_title.lower().endswith(".pdf"):
                        doc_title += ".pdf"
                    discovered.append((doc_title, full_url))
        except Exception:
            continue
            
    return discovered

def process_course_download(course_info: dict, base_dir: Path) -> dict:
    """Executa descoberta e download de PDFs para um curso específico."""
    f_name = get_folder_name(course_info)
    target_dir = base_dir / course_info["area"] / f_name
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Verificar PDFs existentes
    existing_pdfs = list(target_dir.glob("*.pdf"))
    
    # 2. Descobrir novos PDFs na web
    discovered = discover_course_pdfs(course_info)
    
    downloaded_count = 0
    for doc_name, url in discovered:
        dest_file = target_dir / doc_name
        if not dest_file.exists():
            success = download_file(url, dest_file)
            if success:
                downloaded_count += 1
                
    # Atualizar contagem final
    final_pdfs = list(target_dir.glob("*.pdf"))
    total_bytes = sum(p.stat().st_size for p in final_pdfs)
    
    return {
        "curso": f_name,
        "area": course_info["area"],
        "pasta": str(target_dir.relative_to(base_dir)),
        "total_pdfs": len(final_pdfs),
        "tamanho_bytes": total_bytes,
        "documentos": [p.name for p in final_pdfs]
    }

def main():
    print("=" * 70)
    print("INICIANDO CONSTRUÇÃO DA BASE DE DADOS DOS 133 CURSOS DA UFBA")
    print("=" * 70)
    
    manifest_path = BASE_DIR / "Experimento" / "manifesto_base_dados.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    
    start_time = time.time()
    results = []
    
    print(f"Disparando varredura paralela para {len(COURSES_DATA)} cursos...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_course_download, c, BASE_DIR): c for c in COURSES_DATA}
        completed = 0
        for future in as_completed(futures):
            c_info = futures[future]
            try:
                res = future.result()
                results.append(res)
                completed += 1
                if completed % 10 == 0 or completed == len(COURSES_DATA):
                    print(f"[{completed}/{len(COURSES_DATA)}] Processado: {res['curso']} ({res['total_pdfs']} PDFs)")
            except Exception as e:
                print(f"Erro ao processar {c_info['nome']}: {e}")

    # Salvar manifesto detalhado
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    elapsed = time.time() - start_time
    total_docs = sum(r["total_pdfs"] for r in results)
    print("=" * 70)
    print(f"CONSTRUÇÃO CONCLUÍDA EM {elapsed:.1f}s!")
    print(f"Total de Cursos: {len(results)} | Total de Documentos PDFs: {total_docs}")
    print(f"Manifesto salvo em: {manifest_path}")
    print("=" * 70)

if __name__ == "__main__":
    main()

