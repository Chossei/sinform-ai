"""
Fatiador Regulamentar Calibrado pelo Pré-LLM Multimodal
Aplica os parâmetros dinâmicos de cada documento retornados pelo Pré-LLM (Gemini 3.5 Flash Lite):
- header estrito: | Curso | Documento (Nome do documento) |
- max_tokens_per_chunk (calibrado pela densidade visual)
- max_tokens_overlap (sobreposição regulamentar)
Gera os arquivos físicos em: [Curso]/[Nome_do_documento]/fatia_XXX.txt
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import pymupdf
import tiktoken

BASE_DIR = Path(__file__).resolve().parent.parent

class PreLLMDocumentChunker:
    def __init__(self, encoding_name: str = "cl100k_base"):
        self.encoder = tiktoken.get_encoding(encoding_name)

    def count_tokens(self, text: str) -> int:
        return len(self.encoder.encode(text))

    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        doc = pymupdf.open(pdf_path)
        pages_text = []
        for page in doc:
            t = page.get_text()
            if t:
                pages_text.append(t)
        return "\n".join(pages_text)

    def chunk_pdf_with_config(self, pdf_path: Path, curso: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fatia o PDF respeitando o cabeçalho oficial e as cotas de tokens do Pré-LLM.
        """
        doc_raw_name = pdf_path.stem
        header = config.get("header") or f"| {curso} | Documento ({doc_raw_name.replace('_', ' ')}) |"
        max_tokens = int(config.get("max_tokens_per_chunk", 600))
        overlap_tokens = int(config.get("max_tokens_overlap", 80))

        raw_text = self.extract_text_from_pdf(pdf_path)
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

        # Regexes de estrutura legal
        cap_regex = re.compile(r'^(CAP[ÍI]TULO\s+[IVXLCDM\d]+)', re.IGNORECASE)
        sec_regex = re.compile(r'^(SE[ÇC][ÃA]O\s+[IVXLCDM\d]+)', re.IGNORECASE)
        art_regex = re.compile(r'^(Art(?:igo)?\.?\s*\d+º?)', re.IGNORECASE)
        par_regex = re.compile(r'^(§\s*\d+º?|Par[áa]grafo\s+[úu]nico)', re.IGNORECASE)

        raw_articles = []
        current_cap = "Capítulo Geral"
        current_sec = "Seção Geral"
        current_art = None
        current_lines = []

        for line in lines:
            m_cap = cap_regex.match(line)
            if m_cap:
                current_cap = m_cap.group(1).title()
                continue

            m_sec = sec_regex.match(line)
            if m_sec:
                current_sec = m_sec.group(1).title()
                continue

            m_art = art_regex.match(line)
            if m_art:
                if current_art and current_lines:
                    raw_articles.append({
                        "capitulo": current_cap,
                        "secao": current_sec,
                        "artigo": current_art,
                        "lines": list(current_lines)
                    })
                    current_lines = []
                
                raw_art_label = m_art.group(1).strip().rstrip(".:")
                art_num_match = re.search(r'\d+º?', raw_art_label)
                if art_num_match:
                    current_art = f"Artigo {art_num_match.group(0)}"
                else:
                    current_art = raw_art_label
                current_lines.append(line)
            else:
                current_lines.append(line)

        if current_lines:
            raw_articles.append({
                "capitulo": current_cap,
                "secao": current_sec,
                "artigo": current_art if current_art else "Artigo Geral",
                "lines": current_lines
            })

        # Se não houver artigos explícitos, agrupa por parágrafos
        if len(raw_articles) == 1 and raw_articles[0]["artigo"] == "Artigo Geral":
            raw_articles = []
            paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
            for p_idx, p_text in enumerate(paragraphs, 1):
                raw_articles.append({
                    "capitulo": "Geral",
                    "secao": "Geral",
                    "artigo": f"Tópico {p_idx}",
                    "lines": [p_text]
                })

        # Montagem dos Chunks respeitando max_tokens_per_chunk e max_tokens_overlap
        chunks = []
        curr_chunk_lines = []
        curr_cap = ""
        curr_sec = ""
        curr_arts = []
        last_overlap_lines = []

        for item in raw_articles:
            item_text = "\n".join(item["lines"])
            item_tokens = self.count_tokens(item_text)

            # Se o item sozinho for maior que max_tokens, particiona por linhas
            if item_tokens > max_tokens:
                sub_lines = []
                for l in item["lines"]:
                    tentative = "\n".join(sub_lines + [l])
                    if self.count_tokens(tentative) > max_tokens and sub_lines:
                        body_content = "\n".join(sub_lines)
                        full_content = f"{header}\n{body_content}"
                        chunks.append({
                            "curso": curso,
                            "documento": pdf_path.name,
                            "header": header,
                            "capitulo": item["capitulo"],
                            "secao": item["secao"],
                            "artigo": item["artigo"],
                            "content": body_content,
                            "full_chunk": full_content,
                            "tokens": self.count_tokens(full_content)
                        })
                        # Guardar overlap
                        sub_lines = sub_lines[-3:] + [l]
                    else:
                        sub_lines.append(l)

                if sub_lines:
                    body_content = "\n".join(sub_lines)
                    full_content = f"{header}\n{body_content}"
                    chunks.append({
                        "curso": curso,
                        "documento": pdf_path.name,
                        "header": header,
                        "capitulo": item["capitulo"],
                        "secao": item["secao"],
                        "artigo": item["artigo"],
                        "content": body_content,
                        "full_chunk": full_content,
                        "tokens": self.count_tokens(full_content)
                    })
                continue

            # Tenta agrupar com o chunk em andamento
            tentative_lines = curr_chunk_lines + item["lines"]
            tentative_text = "\n".join(tentative_lines)
            tentative_tokens = self.count_tokens(tentative_text)

            if tentative_tokens <= max_tokens:
                curr_chunk_lines.extend(item["lines"])
                if not curr_cap: curr_cap = item["capitulo"]
                if not curr_sec: curr_sec = item["secao"]
                if item["artigo"] not in curr_arts: curr_arts.append(item["artigo"])
            else:
                # Fecha o chunk anterior
                if curr_chunk_lines:
                    body_content = "\n".join(curr_chunk_lines)
                    full_content = f"{header}\n{body_content}"
                    art_label = " e ".join(curr_arts) if curr_arts else "Artigo Normativo"
                    chunks.append({
                        "curso": curso,
                        "documento": pdf_path.name,
                        "header": header,
                        "capitulo": curr_cap or "Geral",
                        "secao": curr_sec or "Geral",
                        "artigo": art_label,
                        "content": body_content,
                        "full_chunk": full_content,
                        "tokens": self.count_tokens(full_content)
                    })

                    # Calcular sobreposição (overlap)
                    overlap_accum = []
                    for l in reversed(curr_chunk_lines):
                        overlap_accum.insert(0, l)
                        if self.count_tokens("\n".join(overlap_accum)) >= overlap_tokens:
                            break
                    last_overlap_lines = overlap_accum

                curr_chunk_lines = last_overlap_lines + item["lines"]
                curr_cap = item["capitulo"]
                curr_sec = item["secao"]
                curr_arts = [item["artigo"]]

        # Fechar o último chunk pendente
        if curr_chunk_lines:
            body_content = "\n".join(curr_chunk_lines)
            full_content = f"{header}\n{body_content}"
            art_label = " e ".join(curr_arts) if curr_arts else "Artigo Normativo"
            chunks.append({
                "curso": curso,
                "documento": pdf_path.name,
                "header": header,
                "capitulo": curr_cap or "Geral",
                "secao": curr_sec or "Geral",
                "artigo": art_label,
                "content": body_content,
                "full_chunk": full_content,
                "tokens": self.count_tokens(full_content)
            })

        # Salvar fatias físicas em .txt
        doc_folder = pdf_path.parent / pdf_path.stem
        doc_folder.mkdir(parents=True, exist_ok=True)

        for idx, ch in enumerate(chunks, 1):
            ch["fatia_id"] = f"fatia_{idx:03d}"
            txt_path = doc_folder / f"fatia_{idx:03d}.txt"
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(ch["full_chunk"])

        print(f"[Chunker Pre-LLM] {pdf_path.name}: {len(chunks)} fatias geradas (Max configurado: {max_tokens} tokens)")
        return chunks

    def process_all_courses(self, base_dir: Path = BASE_DIR) -> Dict[str, List[Dict[str, Any]]]:
        courses = ["Estatística (Bacharel)", "Matemática (Bacharel)", "Matemática (Licenciatura)"]
        all_chunks = {}

        for course in courses:
            course_dir = base_dir / course
            if not course_dir.exists(): continue
            pdf_files = sorted(list(course_dir.glob("*.pdf")))
            course_chunks = []

            for pdf_file in pdf_files:
                doc_subfolder = course_dir / pdf_file.stem
                config_file = doc_subfolder / "pre_llm_config.json"
                config = {}
                if config_file.exists():
                    try:
                        with open(config_file, "r", encoding="utf-8") as f:
                            config = json.load(f)
                    except Exception:
                        pass
                
                chunks = self.chunk_pdf_with_config(pdf_file, course, config)
                course_chunks.extend(chunks)

            all_chunks[course] = course_chunks

        return all_chunks

if __name__ == "__main__":
    chunker = PreLLMDocumentChunker()
    chunker.process_all_courses()
