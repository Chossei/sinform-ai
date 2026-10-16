import re
from pathlib import Path
from typing import List, Dict, Any
import pymupdf
import tiktoken

class DocumentChunker:
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

    def parse_document(self, curso: str, doc_name: str, raw_text: str) -> List[Dict[str, Any]]:
        """
        Analisa o texto do documento identificando Capítulo, Seção, Artigo e Parágrafo.
        Fatia por Artigo, aplica regras de tokens (< 400 mescla, > 1200 fatia por parágrafo)
        e gera os cabeçalhos rigorosamente no padrão:
        | Curso | Documento (Nome do documento) | Capítulo xx | Seção xx | Artigo xx |
        """
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        
        # Regexes precisas
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
                        "curso": curso,
                        "documento": doc_name,
                        "capitulo": current_cap,
                        "secao": current_sec,
                        "artigo": current_art,
                        "lines": list(current_lines)
                    })
                    current_lines = []
                
                # Normalizar rótulo do artigo (ex: "Art. 1º" -> "Artigo 1º")
                raw_art_label = m_art.group(1).strip().rstrip(".:")
                art_num_match = re.search(r'\d+º?', raw_art_label)
                if art_num_match:
                    current_art = f"Artigo {art_num_match.group(0)}"
                else:
                    current_art = raw_art_label
                current_lines.append(line)
            else:
                if current_art:
                    current_lines.append(line)
                else:
                    # Linhas pré-artigos
                    current_lines.append(line)

        if current_lines:
            raw_articles.append({
                "curso": curso,
                "documento": doc_name,
                "capitulo": current_cap,
                "secao": current_sec,
                "artigo": current_art if current_art else "Artigo Geral",
                "lines": current_lines
            })

        # Caso o documento não possua artigos formais
        if len(raw_articles) == 1 and raw_articles[0]["artigo"] == "Artigo Geral":
            raw_articles = self._fallback_slice(curso, doc_name, raw_text)

        # Regras de Tokens (< 400 mescla, > 1200 divide por parágrafos)
        processed_chunks = []
        i = 0
        while i < len(raw_articles):
            art = raw_articles[i]
            content = "\n".join(art["lines"])
            tokens = self.count_tokens(content)

            # Caso > 1200 tokens: fatiar por parágrafos
            if tokens > 1200:
                sub_chunks = self._split_by_paragraphs(art, par_regex)
                processed_chunks.extend(sub_chunks)
                i += 1
                continue

            # Caso < 400 tokens: agrupar com artigo(s) anterior ou subsequente
            if tokens < 400:
                merged_art_names = [art["artigo"]]
                merged_lines = list(art["lines"])
                cap = art["capitulo"]
                sec = art["secao"]

                while i + 1 < len(raw_articles):
                    next_art = raw_articles[i + 1]
                    next_content = "\n".join(next_art["lines"])
                    if self.count_tokens("\n".join(merged_lines + next_art["lines"])) <= 1200:
                        merged_art_names.append(next_art["artigo"])
                        merged_lines.extend(next_art["lines"])
                        i += 1
                        if self.count_tokens("\n".join(merged_lines)) >= 400:
                            break
                    else:
                        break

                # Formatar cabeçalho com Artigo X e Artigo Y
                if len(merged_art_names) == 1:
                    art_label = merged_art_names[0]
                elif len(merged_art_names) == 2:
                    art_label = f"{merged_art_names[0]} e {merged_art_names[1]}"
                else:
                    art_label = f"{', '.join(merged_art_names[:-1])} e {merged_art_names[-1]}"

                header = f"| {curso} | {doc_name} | {cap} | {sec} | {art_label} |"
                merged_content = "\n".join(merged_lines)
                processed_chunks.append({
                    "curso": curso,
                    "documento": doc_name,
                    "capitulo": cap,
                    "secao": sec,
                    "artigo": art_label,
                    "header": header,
                    "content": merged_content,
                    "tokens": self.count_tokens(merged_content)
                })
                i += 1
                continue

            # Caso entre 400 e 1200 tokens
            header = f"| {curso} | {doc_name} | {art['capitulo']} | {art['secao']} | {art['artigo']} |"
            processed_chunks.append({
                "curso": curso,
                "documento": doc_name,
                "capitulo": art["capitulo"],
                "secao": art["secao"],
                "artigo": art["artigo"],
                "header": header,
                "content": content,
                "tokens": tokens
            })
            i += 1

        return processed_chunks

    def _split_by_paragraphs(self, art_dict: Dict[str, Any], par_regex: re.Pattern) -> List[Dict[str, Any]]:
        """Divide artigos com mais de 1200 tokens por intervalos de parágrafos."""
        lines = art_dict["lines"]
        paragraphs = []
        curr_par_lines = []
        par_counter = 1

        for line in lines:
            m = par_regex.match(line)
            if m:
                if curr_par_lines:
                    paragraphs.append({
                        "idx": par_counter,
                        "lines": list(curr_par_lines)
                    })
                    curr_par_lines = []
                    par_counter += 1
                curr_par_lines.append(line)
            else:
                curr_par_lines.append(line)

        if curr_par_lines:
            paragraphs.append({
                "idx": par_counter,
                "lines": curr_par_lines
            })

        if len(paragraphs) <= 1:
            return self._split_by_token_blocks(art_dict, 600)

        chunks = []
        curr_group = []
        start_idx = 1
        
        for p in paragraphs:
            curr_group.extend(p["lines"])
            current_tokens = self.count_tokens("\n".join(curr_group))
            if current_tokens >= 400:
                end_idx = p["idx"]
                if start_idx == end_idx:
                    par_range = f"Parágrafo {start_idx}"
                else:
                    par_range = f"Parágrafos {start_idx}-{end_idx}"
                
                header = f"| {art_dict['curso']} | {art_dict['documento']} | {art_dict['capitulo']} | {art_dict['secao']} | {art_dict['artigo']} ({par_range}) |"
                content = "\n".join(curr_group)
                chunks.append({
                    "curso": art_dict["curso"],
                    "documento": art_dict["documento"],
                    "capitulo": art_dict["capitulo"],
                    "secao": art_dict["secao"],
                    "artigo": f"{art_dict['artigo']} ({par_range})",
                    "header": header,
                    "content": content,
                    "tokens": current_tokens
                })
                curr_group = []
                start_idx = end_idx + 1

        if curr_group:
            end_idx = paragraphs[-1]["idx"]
            if start_idx <= end_idx:
                par_range = f"Parágrafos {start_idx}-{end_idx}" if start_idx != end_idx else f"Parágrafo {start_idx}"
            else:
                par_range = f"Parágrafos Finais"
            header = f"| {art_dict['curso']} | {art_dict['documento']} | {art_dict['capitulo']} | {art_dict['secao']} | {art_dict['artigo']} ({par_range}) |"
            content = "\n".join(curr_group)
            chunks.append({
                "curso": art_dict["curso"],
                "documento": art_dict["documento"],
                "capitulo": art_dict["capitulo"],
                "secao": art_dict["secao"],
                "artigo": f"{art_dict['artigo']} ({par_range})",
                "header": header,
                "content": content,
                "tokens": self.count_tokens(content)
            })

        return chunks

    def _split_by_token_blocks(self, art_dict: Dict[str, Any], block_tokens: int) -> List[Dict[str, Any]]:
        lines = art_dict["lines"]
        chunks = []
        curr = []
        part = 1
        for line in lines:
            curr.append(line)
            if self.count_tokens("\n".join(curr)) >= block_tokens:
                header = f"| {art_dict['curso']} | {art_dict['documento']} | {art_dict['capitulo']} | {art_dict['secao']} | {art_dict['artigo']} (Parte {part}) |"
                content = "\n".join(curr)
                chunks.append({
                    "curso": art_dict["curso"],
                    "documento": art_dict["documento"],
                    "capitulo": art_dict["capitulo"],
                    "secao": art_dict["secao"],
                    "artigo": f"{art_dict['artigo']} (Parte {part})",
                    "header": header,
                    "content": content,
                    "tokens": self.count_tokens(content)
                })
                curr = []
                part += 1
        if curr:
            header = f"| {art_dict['curso']} | {art_dict['documento']} | {art_dict['capitulo']} | {art_dict['secao']} | {art_dict['artigo']} (Parte {part}) |"
            content = "\n".join(curr)
            chunks.append({
                "curso": art_dict["curso"],
                "documento": art_dict["documento"],
                "capitulo": art_dict["capitulo"],
                "secao": art_dict["secao"],
                "artigo": f"{art_dict['artigo']} (Parte {part})",
                "header": header,
                "content": content,
                "tokens": self.count_tokens(content)
            })
        return chunks

    def _fallback_slice(self, curso: str, doc_name: str, raw_text: str) -> List[Dict[str, Any]]:
        paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
        slices = []
        curr_lines = []
        sec_num = 1
        
        for p in paragraphs:
            curr_lines.append(p)
            if self.count_tokens("\n\n".join(curr_lines)) >= 450:
                slices.append({
                    "curso": curso,
                    "documento": doc_name,
                    "capitulo": "Normas e Diretrizes Gerais",
                    "secao": f"Seção {sec_num}",
                    "artigo": f"Diretriz Normativa {sec_num}",
                    "lines": list(curr_lines)
                })
                curr_lines = []
                sec_num += 1
        if curr_lines:
            slices.append({
                "curso": curso,
                "documento": doc_name,
                "capitulo": "Normas e Diretrizes Gerais",
                "secao": f"Seção {sec_num}",
                "artigo": f"Diretriz Normativa {sec_num}",
                "lines": curr_lines
            })
        return slices
