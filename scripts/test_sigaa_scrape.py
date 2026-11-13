import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings()

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
url = 'https://sigaa.ufba.br/sigaa/public/curso/ppp.jsf?lc=pt_BR&id=1876959'

r = requests.get(url, headers=headers, verify=False, timeout=20)
print('PPP Status:', r.status_code)
soup = BeautifulSoup(r.text, 'html.parser')

print('Text length:', len(soup.get_text(strip=True)))
for a in soup.find_all('a', href=True):
    print(a.get_text(strip=True), '->', a['href'])

# Print first 500 chars of page text
print('\nPreview:\n', soup.get_text(strip=True)[:600])
