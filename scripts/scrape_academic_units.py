import urllib.request
import re
import json
import ssl
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

DOMAINS = [
    ("Letras", "https://letras.ufba.br"),
    ("Belas Artes", "https://belasartes.ufba.br"),
    ("Dança", "https://danca.ufba.br"),
    ("ICI", "https://ici.ufba.br"),
    ("FFCH", "https://ffch.ufba.br"),
    ("FCE", "https://fce.ufba.br"),
    ("Enfermagem", "https://enfermagem.ufba.br"),
    ("Nutrição", "https://nutricao.ufba.br"),
    ("ICS", "https://ics.ufba.br"),
    ("IGEO", "https://igeo.ufba.br"),
    ("FACOM", "https://facom.ufba.br"),
]

def fetch_page(url, timeout=6):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            content_type = resp.headers.get('Content-Type', '')
            if 'html' in content_type:
                return resp.read().decode('utf-8', errors='ignore')
    except Exception:
        pass
    return None

results = {}

for name, base_url in DOMAINS:
    print(f"\nScanning {name} ({base_url})...")
    html = fetch_page(base_url)
    if not html:
        print(f"Failed to fetch {base_url}")
        continue
    
    soup = BeautifulSoup(html, 'html.parser')
    all_links = set()
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        full_url = urljoin(base_url, href)
        all_links.add(full_url)
        
    # Also find subpages with keywords like graduacao, colegiado, cursos, documentos
    subpages_to_crawl = set()
    for link in all_links:
        parsed = urlparse(link)
        if parsed.netloc == urlparse(base_url).netloc:
            path_lower = parsed.path.lower()
            if any(k in path_lower for k in ['gradua', 'curso', 'colegiad', 'docum', 'ensino', 'norma', 'projeto', 'ppc', 'regimento', 'manual']):
                subpages_to_crawl.add(link)
                
    print(f"  Found {len(subpages_to_crawl)} relevant subpages to crawl")
    
    # Crawl base + first 25 relevant subpages
    pages_to_check = [base_url] + list(subpages_to_crawl)[:25]
    pdf_found = set()
    
    for page_url in pages_to_check:
        page_html = fetch_page(page_url, timeout=5)
        if not page_html:
            continue
        sub_soup = BeautifulSoup(page_html, 'html.parser')
        for a in sub_soup.find_all('a', href=True):
            href = a['href'].strip()
            full_url = urljoin(page_url, href)
            if full_url.lower().endswith('.pdf') or '.pdf?' in full_url.lower() or '/files/' in full_url.lower():
                text = a.get_text(strip=True) or href.split('/')[-1]
                pdf_found.add((text, full_url))
                
    print(f"  --> Found {len(pdf_found)} PDFs in {name}")
    results[name] = [{"text": t, "url": u} for t, u in pdf_found]

with open("scripts/scraped_unit_pdfs.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\nSaved scripts/scraped_unit_pdfs.json successfully!")

