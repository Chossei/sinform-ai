import requests
import urllib3
import re
from pathlib import Path
from bs4 import BeautifulSoup

urllib3.disable_warnings()

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# Testar Direito
print('--- BUSCANDO DOCUMENTOS DE DIREITO ---')
urls_direito = [
    'https://direito.ufba.br/grade-curricular',
    'https://direito.ufba.br/ementas-e-programas-de-disciplinas-da-graduacao',
    'https://direito.ufba.br/resolucoes',
    'https://direito.ufba.br/colegiado'
]

pdf_links = set()
for u in urls_direito:
    try:
        r = requests.get(u, headers=headers, verify=False, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '.pdf' in href.lower() or 'sites/direito.ufba.br/files' in href.lower():
                full_url = href if href.startswith('http') else f'https://direito.ufba.br{href}'
                pdf_links.add((a.get_text(strip=True), full_url))
    except Exception as e:
        print(f'Erro em {u}: {e}')

print(f'Total de PDFs específicos encontrados para Direito: {len(pdf_links)}')
for text, l in sorted(pdf_links)[:10]:
    print(f' -> {text}: {l}')

