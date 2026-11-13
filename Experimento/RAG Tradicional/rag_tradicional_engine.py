"""
Motor do RAG Tradicional (Google FileSearchStore + Top-K Chunks via Similaridade Cosseno).

Suporta:
- Perguntas únicas (1 curso / 1 FileSearchStore) e perguntas híbridas multi-curso (união de FileSearchStores).
- Criação e indexação automática sob demanda (on-the-fly) de FileSearchStore para qualquer curso
  dos 133 cursos da UFBA que ainda não possua store indexada.
- Respeito estrito aos limites de RPM e RPD de cada modelo via 'rate_limiter.py'.
"""

import os
import re
import sys
import json
import time
import shutil
import tempfile
import threading
import unicodedata
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

from google import genai
from google.genai import types

RAG_TRAD_DIR = Path(__file__).resolve().parent
EXPERIMENTO_DIR = RAG_TRAD_DIR.parent
BASE_DIR = EXPERIMENTO_DIR.parent
AREAS_DIR = EXPERIMENTO_DIR / "Áreas do conhecimento"

sys.path.append(str(EXPERIMENTO_DIR))
from rate_limiter import get_rate_limiter, RPDLimitExceededError

# Carregar variáveis de ambiente
load_dotenv(BASE_DIR / ".env")
load_dotenv(EXPERIMENTO_DIR / "chave2.env")

API_KEY_2 = os.getenv("GEMINI_PAGO_RICARDO") or os.getenv("GEMINI_API_KEY_2") or os.getenv("GEMINI_API_KEY")
if not API_KEY_2:
    raise ValueError("Chave da Gemini API não foi encontrada!")

PRIMARY_MODEL = "gemini-3.5-flash-lite"
FALLBACK_MODEL = "gemini-3.1-flash-lite"
EMBEDDING_MODEL = "models/gemini-embedding-2"
CURSO_ALVO = "Estatística (Bacharel)"
STORE_DISPLAY_NAME = "sinform-rag-tradicional-estatistica-default"
STORE_CONFIG_FILE = RAG_TRAD_DIR / "store_tradicional_config.json"

_STORE_CREATION_LOCK = threading.Lock()
_VERIFIED_STORES: Set[Tuple[str, str]] = set()
_ACTIVE_STORE_COUNTS: Dict[str, int] = {}
_STORE_LRU: Dict[str, List[str]] = {}


def _to_long_path(p: Path) -> Path:
    s = str(p.resolve())
    if os.name == "nt" and not s.startswith("\\\\?\\"):
        return Path("\\\\?\\" + s)
    return Path(s)


def _norm_str(txt: Any) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", str(txt))
        if not unicodedata.combining(c)
    ).lower().strip()


class RAGTradicional:
    """
    Motor de RAG Tradicional baseado em Google FileSearchStore (chunking default, top_k=k).
    """

    def __init__(
        self,
        api_key: str = API_KEY_2,
        key_id: str = "GEMINI_PAGO_RICARDO",
        use_two_step_function_call: bool = False
    ):
        self.api_key = api_key
        self.key_id = key_id
        self.is_paid = ("pago" in str(key_id).lower() or "ricardo" in str(key_id).lower())
        self.use_two_step_function_call = use_two_step_function_call
        self.client = genai.Client(api_key=self.api_key)

        self.llm_limiter = get_rate_limiter(PRIMARY_MODEL, key_id=self.key_id)
        self.emb_limiter = get_rate_limiter(EMBEDDING_MODEL, key_id=self.key_id)

        self.store_name = self._load_or_find_store()

    def _get_mapping_file(self) -> Path:
        if self.key_id == "GEMINI_API_KEY":
            map_name = "google_file_search_stores_free.json"
        elif self.is_paid:
            map_name = "google_file_search_stores.json"
        else:
            safe_id = re.sub(r"[^a-zA-Z0-9_]", "_", str(self.key_id).lower())
            map_name = f"google_file_search_stores_{safe_id}.json"
        return BASE_DIR / map_name

    def _load_or_find_store(self) -> str:
        """Carrega o nome da FileSearchStore padrão do arquivo de configuração ou busca na API."""
        if STORE_CONFIG_FILE.exists():
            try:
                with open(STORE_CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                st_name = cfg.get("store_name")
                if st_name:
                    return st_name
            except Exception:
                pass

        try:
            stores = list(self.client.file_search_stores.list())
            for s in stores:
                if s.display_name == STORE_DISPLAY_NAME:
                    return s.name
            for s in stores:
                if "estatistica" in (s.display_name or "").lower():
                    return s.name
        except Exception:
            pass

        return ""

    def _find_course_dir(self, course_name: str) -> Optional[Path]:
        """Localiza a pasta do curso em Experimento/Áreas do conhecimento (inclui UFBA - Geral)."""
        if not AREAS_DIR.exists():
            return None
        target_norm = _norm_str(course_name)
        for area_dir in AREAS_DIR.iterdir():
            if not area_dir.is_dir():
                continue
            if area_dir.name.strip() == course_name.strip() or _norm_str(area_dir.name) == target_norm:
                return area_dir
            for c_dir in area_dir.iterdir():
                if not c_dir.is_dir():
                    continue
                if c_dir.name.strip() == course_name.strip() or _norm_str(c_dir.name) == target_norm:
                    return c_dir
        return None

    def _upload_pdfs_to_store(self, store_name: str, pdf_files: List[Path]) -> int:
        """Faz upload paralelo de PDFs para uma FileSearchStore com retentativas e espera."""
        if not pdf_files:
            return 0

        def _build_clean_pdf(src_pdf: Path, out_pdf: Path, mode: str) -> bool:
            """Reconstroi PDF problemático (ex: 500 INTERNAL) via PyMuPDF ou ReportLab texto limpo."""
            try:
                import fitz
                src_doc = fitz.open(str(_to_long_path(src_pdf)))
                if mode == "fitz_rewrite":
                    src_doc.save(str(out_pdf), garbage=4, deflate=True, clean=True)
                    src_doc.close()
                    return out_pdf.exists() and out_pdf.stat().st_size > 0
                pages_text = [pg.get_text("text") or "" for pg in src_doc]
                src_doc.close()
                full_txt = "\n\n".join(t.strip() for t in pages_text if t.strip())
                if not full_txt:
                    return False
                from xml.sax.saxutils import escape as xml_escape
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                from reportlab.lib.styles import getSampleStyleSheet
                from reportlab.lib.pagesizes import A4
                doc_rl = SimpleDocTemplate(str(out_pdf), pagesize=A4)
                style = getSampleStyleSheet()["Normal"]
                story = []
                for block in full_txt.split("\n"):
                    line_clean = block.strip()
                    if line_clean:
                        story.append(Paragraph(xml_escape(line_clean), style))
                    else:
                        story.append(Spacer(1, 6))
                if not story:
                    return False
                doc_rl.build(story)
                return out_pdf.exists() and out_pdf.stat().st_size > 0
            except Exception:
                return False

        def _upload_one(pdf_path: Path) -> Tuple[Optional[Any], bool, Optional[Exception]]:
            doc_name = pdf_path.name
            clean_stem = _norm_str(pdf_path.stem)
            last_was_internal = False
            for attempt in range(1, 5):
                safe_ascii = f"fs_{int(time.time()*1000)%100000}_{attempt}_{re.sub(r'[^a-zA-Z0-9_.-]', '_', clean_stem)[:40]}.pdf"
                tmp_pdf = Path(tempfile.gettempdir()) / safe_ascii
                try:
                    if last_was_internal and attempt == 2:
                        ok_fb = _build_clean_pdf(pdf_path, tmp_pdf, "fitz_rewrite")
                        if not ok_fb:
                            shutil.copy2(_to_long_path(pdf_path), tmp_pdf)
                    elif last_was_internal and attempt >= 3:
                        ok_fb = _build_clean_pdf(pdf_path, tmp_pdf, "reportlab_text")
                        if not ok_fb:
                            shutil.copy2(_to_long_path(pdf_path), tmp_pdf)
                    else:
                        shutil.copy2(_to_long_path(pdf_path), tmp_pdf)
                    self.emb_limiter.acquire()
                    op = self.client.file_search_stores.upload_to_file_search_store(
                        file_search_store_name=store_name,
                        file=str(tmp_pdf),
                        config=types.UploadToFileSearchStoreConfig(
                            display_name=doc_name
                        )
                    )
                    return op, True, None
                except RPDLimitExceededError as rpd_e:
                    return None, False, rpd_e
                except Exception as e:
                    err_s = str(e)
                    is_quota = ("429" in err_s or "RESOURCE_EXHAUSTED" in err_s or "RPD EXCEDIDO" in err_s.upper())
                    is_internal = ("500" in err_s or "INTERNAL" in err_s or "503" in err_s or "UNAVAILABLE" in err_s)
                    if is_internal:
                        last_was_internal = True
                    if is_quota and attempt >= 4:
                        return None, False, e
                    if attempt < 4:
                        time.sleep((4 * attempt) if is_quota else (2 * attempt))
                    else:
                        print(f"      [Aviso Upload FileSearchStore '{doc_name}']: {e}", flush=True)
                        return None, False, e
                finally:
                    try:
                        tmp_pdf.unlink(missing_ok=True)
                    except Exception:
                        pass
            return None, False, None

        pending_ops = []
        failed_errors: List[Exception] = []
        uploaded_ok = 0

        with ThreadPoolExecutor(max_workers=6) as up_exec:
            futs = [up_exec.submit(_upload_one, p) for p in pdf_files]
            for fut in as_completed(futs):
                op, ok, err = fut.result()
                if ok:
                    uploaded_ok += 1
                    if op is not None and not getattr(op, "done", True):
                        pending_ops.append(op)
                elif err is not None:
                    failed_errors.append(err)

        for op in pending_ops:
            wait_loops = 0
            try:
                while not op.done and wait_loops < 40:
                    time.sleep(1.5)
                    op = self.client.operations.get(op)
                    wait_loops += 1
            except Exception:
                pass

        for err in failed_errors:
            if isinstance(err, RPDLimitExceededError):
                raise err
            es = str(err)
            if "429" in es or "RESOURCE_EXHAUSTED" in es or "RPD EXCEDIDO" in es.upper():
                raise RuntimeError(f"429 RESOURCE_EXHAUSTED ao indexar FileSearchStore ({self.key_id}): {es[:120]}")

        if failed_errors:
            raise RuntimeError(f"Falha ao enviar {len(failed_errors)} PDF(s) para FileSearchStore {store_name}: {failed_errors[0]}")

        return uploaded_ok

    def _mark_store_used(self, store_name: str):
        lru = _STORE_LRU.setdefault(self.key_id, [])
        if store_name in lru:
            lru.remove(store_name)
        lru.append(store_name)

    def _evict_old_stores(
        self,
        mapping_file: Path,
        stores_map: Dict[str, str],
        protected_stores: Optional[Set[str]] = None,
        target_count: int = 5,
    ) -> int:
        """Libera espaço na FileSearchStore removendo stores ociosas/antigas não em uso ativo."""
        protected = set(protected_stores or set())
        try:
            all_stores = list(self.client.file_search_stores.list())
        except Exception as e:
            print(f"      [Aviso Eviction List]: {e}", flush=True)
            return 0

        lru = _STORE_LRU.get(self.key_id, [])
        lru_rank = {st: idx for idx, st in enumerate(lru)}

        candidates = []
        for s in all_stores:
            if s.name in protected or _ACTIVE_STORE_COUNTS.get(s.name, 0) > 0:
                continue
            sz = int(getattr(s, "size_bytes", 0) or 0)
            # Prioridade: stores órfãs (não usadas nesta execução) ordenadas por maior tamanho; depois mais antigas no LRU
            rank = (0, -sz) if s.name not in lru_rank else (1, lru_rank[s.name])
            candidates.append((rank, s))

        candidates.sort(key=lambda x: x[0])
        deleted = 0
        freed_bytes = 0
        for _, s in candidates[:target_count]:
            try:
                sz = int(getattr(s, "size_bytes", 0) or 0)
                self.client.file_search_stores.delete(
                    name=s.name,
                    config=types.DeleteFileSearchStoreConfig(force=True),
                )
                deleted += 1
                freed_bytes += sz
                if s.name in lru:
                    lru.remove(s.name)
                dead_keys = [k for k, v in stores_map.items() if v == s.name]
                for dk in dead_keys:
                    stores_map.pop(dk, None)
                    _VERIFIED_STORES.discard((self.key_id, _norm_str(dk)))
            except Exception as del_e:
                print(f"      [Aviso Delete Store '{s.name}']: {del_e}", flush=True)

        if deleted:
            print(
                f"    [FileSearchStore Eviction] Liberadas {deleted} stores ({freed_bytes/(1024**2):.1f} MB) na chave '{self.key_id}'.",
                flush=True,
            )
            try:
                with open(mapping_file, "w", encoding="utf-8") as f:
                    json.dump(stores_map, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
        return deleted

    def _upload_pdfs_with_auto_evict(
        self,
        store_name: str,
        disk_by_norm: Dict[str, Path],
        pdfs_to_upload: List[Path],
        mapping_file: Path,
        stores_map: Dict[str, str],
    ) -> None:
        remaining = list(pdfs_to_upload)
        for evict_round in range(5):
            try:
                if remaining:
                    self._upload_pdfs_to_store(store_name, remaining)
                return
            except Exception as e:
                es = str(e).lower()
                is_storage = ("storage limit" in es or "1000000000" in es or "exceeded" in es and "storage" in es)
                if not is_storage or evict_round >= 4:
                    raise
                freed = self._evict_old_stores(mapping_file, stores_map, protected_stores={store_name}, target_count=6)
                if freed == 0:
                    raise
                time.sleep(1.5)
                try:
                    remote_docs = list(self.client.file_search_stores.documents.list(parent=store_name))
                    active_norms = {
                        _norm_str(getattr(d, "display_name", "") or "")
                        for d in remote_docs
                        if "FAILED" not in str(getattr(d, "state", "") or "").upper()
                    }
                    remaining = [p for n, p in disk_by_norm.items() if n not in active_norms]
                except Exception:
                    pass

    def ensure_course_store(self, course_name: str) -> Optional[str]:
        """
        Retorna o store_name da FileSearchStore do curso, garantindo sincronia real 1:1
        entre os PDFs da pasta do curso em disco e os documentos ativos na FileSearchStore.
        """
        mapping_file = self._get_mapping_file()
        c_norm = _norm_str(course_name)
        verify_key = (self.key_id, c_norm)

        # 1. Consulta rápida se já verificada nesta execução
        if verify_key in _VERIFIED_STORES and mapping_file.exists():
            try:
                with open(mapping_file, "r", encoding="utf-8") as f:
                    stores_map = json.load(f)
                for k_name, st_val in stores_map.items():
                    if _norm_str(k_name) == c_norm and st_val:
                        with _STORE_CREATION_LOCK:
                            self._mark_store_used(st_val)
                        return st_val
            except Exception:
                pass

        # 2. Aquisição de lock para verificar/sincronizar ou criar na API
        with _STORE_CREATION_LOCK:
            stores_map: Dict[str, str] = {}
            if mapping_file.exists():
                try:
                    with open(mapping_file, "r", encoding="utf-8") as f:
                        stores_map = json.load(f)
                except Exception:
                    stores_map = {}

            existing_st: Optional[str] = None
            for k_name, st_val in stores_map.items():
                if _norm_str(k_name) == c_norm and st_val:
                    existing_st = st_val
                    break

            if verify_key in _VERIFIED_STORES and existing_st:
                self._mark_store_used(existing_st)
                return existing_st

            course_dir = self._find_course_dir(course_name)
            if not course_dir:
                raise RuntimeError(f"Pasta do curso '{course_name}' não encontrada em {AREAS_DIR}.")

            pdf_files = sorted([p for p in _to_long_path(course_dir).glob("*.pdf") if _to_long_path(p).is_file()])
            if not pdf_files:
                return None

            slug = re.sub(r"[^a-z0-9]+", "", c_norm)[:26]
            display_name = f"sinform-ufba-{slug}"

            # Se não está no JSON local, verificar se já existe no servidor com esse display_name
            if not existing_st:
                try:
                    for s in self.client.file_search_stores.list():
                        if (s.display_name or "") == display_name:
                            existing_st = s.name
                            break
                except Exception as e:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        raise RuntimeError(f"429 RESOURCE_EXHAUSTED ao listar FileSearchStores ({self.key_id}): {e}")

            disk_by_norm: Dict[str, Path] = {_norm_str(p.name): p for p in pdf_files}

            if existing_st:
                try:
                    remote_docs = list(self.client.file_search_stores.documents.list(parent=existing_st))
                except Exception as e:
                    err_s = str(e)
                    if "429" in err_s or "RESOURCE_EXHAUSTED" in err_s:
                        raise RuntimeError(f"429 RESOURCE_EXHAUSTED ao listar documentos da store {existing_st}: {err_s[:120]}")
                    # Store inexistente/removida na API -> recriar do zero
                    existing_st = None
                    remote_docs = []

                if existing_st:
                    seen_active_norms: Set[str] = set()
                    stale_doc_names: List[str] = []

                    for d in remote_docs:
                        d_norm = _norm_str(getattr(d, "display_name", "") or "")
                        state_str = str(getattr(d, "state", "") or "").upper()
                        is_failed = ("FAILED" in state_str)
                        if is_failed or d_norm not in disk_by_norm or d_norm in seen_active_norms:
                            stale_doc_names.append(d.name)
                        else:
                            seen_active_norms.add(d_norm)

                    missing_pdfs = [p for n, p in disk_by_norm.items() if n not in seen_active_norms]

                    if stale_doc_names or missing_pdfs:
                        print(
                            f"    [FileSearchStore Sync] '{course_name}' ({existing_st}): "
                            f"removendo {len(stale_doc_names)} obsoleto(s), enviando {len(missing_pdfs)}/{len(pdf_files)} PDF(s)...",
                            flush=True,
                        )
                        for d_name in stale_doc_names:
                            try:
                                self.client.file_search_stores.documents.delete(
                                    name=d_name,
                                    config=types.DeleteDocumentConfig(force=True),
                                )
                            except Exception as del_e:
                                print(f"      [Aviso Delete doc '{d_name}']: {del_e}", flush=True)

                        if missing_pdfs:
                            self._upload_pdfs_with_auto_evict(
                                existing_st, disk_by_norm, missing_pdfs, mapping_file, stores_map
                            )

                    stores_map[course_name] = existing_st
                    try:
                        with open(mapping_file, "w", encoding="utf-8") as f:
                            json.dump(stores_map, f, ensure_ascii=False, indent=2)
                    except Exception:
                        pass
                    self._mark_store_used(existing_st)
                    _VERIFIED_STORES.add(verify_key)
                    return existing_st

            # Criar nova FileSearchStore e indexar todos os PDFs (com auto-eviction caso atinja 1GB)
            print(f"    [FileSearchStore On-Demand] Criando store '{display_name}' para '{course_name}' ({len(pdf_files)} PDFs, paralelo)...", flush=True)
            store = None
            for cr_attempt in range(3):
                try:
                    self.emb_limiter.acquire()
                    store = self.client.file_search_stores.create(
                        config=types.CreateFileSearchStoreConfig(
                            display_name=display_name
                        )
                    )
                    break
                except Exception as e:
                    err_s = str(e)
                    es_low = err_s.lower()
                    if ("storage" in es_low or "store" in es_low or "limit" in es_low) and cr_attempt < 2:
                        freed = self._evict_old_stores(mapping_file, stores_map, target_count=5)
                        if freed > 0:
                            continue
                    if "429" in err_s or "RESOURCE_EXHAUSTED" in err_s or "RPD EXCEDIDO" in err_s.upper():
                        raise RuntimeError(f"429 RESOURCE_EXHAUSTED no FileSearchStore Create ({self.key_id}): {err_s[:120]}")
                    raise RuntimeError(f"Erro ao criar FileSearchStore para '{course_name}': {e}")

            self._upload_pdfs_with_auto_evict(
                store.name, disk_by_norm, pdf_files, mapping_file, stores_map
            )

            stores_map[course_name] = store.name
            try:
                with open(mapping_file, "w", encoding="utf-8") as f:
                    json.dump(stores_map, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            self._mark_store_used(store.name)
            _VERIFIED_STORES.add(verify_key)
            return store.name

    def _build_system_instruction(self, curso: str = CURSO_ALVO) -> str:
        return f"""Você é o Sinform AI, o assistente consultor especializado nas normas, resoluções e regulamentos acadêmicos da UFBA (Universidade Federal da Bahia).

SEU PAPEL E CONTEXTO:
- Você está prestando atendimento oficial a um(a) discente da UFBA vinculado ao(s) curso(s): {curso}.
- Perguntas sobre normas do curso, resoluções de colegiado, departamentos, núcleos acadêmicos, institutos/unidades universitárias ou regulamentos gerais da UFBA fazem parte do seu escopo. Consulte SEMPRE os documentos da FileSearchStore antes de responder.

BUSCA E USO OBRIGATÓRIO DO FILESEARCH:
- Utilize sempre a ferramenta FileSearch para recuperar os top chunks mais relevantes dos documentos indexados na FileSearchStore antes de formular sua resposta.
- Nunca recuse uma pergunta com "Desculpe, não posso te ajudar com isso" alegando incompatibilidade de curso sem antes consultar e verificar os documentos da FileSearchStore.

RESTRIÇÕES DE RESPOSTA (GROUNDEDNESS):
- Responda UNICAMENTE com base nos fragmentos normativos recuperados do banco vetorial (FileSearchStore).
- Sempre cite expressamente o documento/resolução de origem e os artigos/parágrafos que respondem à pergunta (exemplo: "De acordo com o Art. 4º da Resolução nº 03/2025...").
- Caso a informação solicitada realmente não conste nos fragmentos recuperados após a busca, declare explicitamente: "Esta informação não consta nos documentos consultados."
"""

    def _extract_grounding_chunks(self, response: Any) -> List[Dict[str, Any]]:
        """Extrai os chunks recuperados do grounding_metadata da resposta do FileSearch."""
        chunks_info = []
        if not response or not getattr(response, "candidates", None):
            return chunks_info

        cand = response.candidates[0]
        gm = getattr(cand, "grounding_metadata", None)
        if not gm:
            return chunks_info

        g_chunks = getattr(gm, "grounding_chunks", []) or []
        for idx, gc in enumerate(g_chunks, 1):
            rc = getattr(gc, "retrieved_context", None)
            title = (getattr(rc, "title", "") if rc else "") or f"Chunk {idx}"
            text = (getattr(rc, "text", "") if rc else "") or ""
            chunks_info.append({
                "rank": idx,
                "documento": title,
                "content": text
            })
        return chunks_info

    def ask(
        self,
        query: str,
        curso: str = CURSO_ALVO,
        top_k: int = 10,
        max_retries: int = 6
    ) -> Tuple[str, List[Dict[str, Any]], str, Dict[str, Any]]:
        """
        Executa uma pergunta no RAG Tradicional (suporta 1 ou múltiplos cursos separados por ';'):
        1. O modelo recebe a pergunta do usuário.
        2. Aciona a function calling de embeddings (consultar_normas_academicas -> FileSearch top_k=top_k).
        3. Recebe na janela de contexto os top_k chunks via similaridade seno-cosseno da(s) FileSearchStore(s).
        4. Gera e retorna a resposta fundamentada.
        """
        cursos_list = [c.strip() for c in str(curso).split(";") if c.strip()]
        if not cursos_list:
            cursos_list = [CURSO_ALVO]

        stores_to_use: List[str] = []
        needs_ufba_geral = False
        try:
            for c_single in cursos_list:
                c_dir = self._find_course_dir(c_single)
                if c_dir and len([p for p in _to_long_path(c_dir).glob("*.pdf") if _to_long_path(p).is_file()]) < 3:
                    needs_ufba_geral = True
                st = self.ensure_course_store(c_single)
                if st and st not in stores_to_use:
                    with _STORE_CREATION_LOCK:
                        _ACTIVE_STORE_COUNTS[st] = _ACTIVE_STORE_COUNTS.get(st, 0) + 1
                    stores_to_use.append(st)

            if needs_ufba_geral:
                st_ug = self.ensure_course_store("UFBA - Geral")
                if st_ug and st_ug not in stores_to_use:
                    with _STORE_CREATION_LOCK:
                        _ACTIVE_STORE_COUNTS[st_ug] = _ACTIVE_STORE_COUNTS.get(st_ug, 0) + 1
                    stores_to_use.append(st_ug)

            if not stores_to_use:
                raise RuntimeError(f"Nenhuma FileSearchStore encontrada para o(s) curso(s): {curso}")

            return self._execute_ask(query, curso, top_k, max_retries, stores_to_use)
        finally:
            if stores_to_use:
                with _STORE_CREATION_LOCK:
                    for st in stores_to_use:
                        _ACTIVE_STORE_COUNTS[st] = max(0, _ACTIVE_STORE_COUNTS.get(st, 0) - 1)

    def _execute_ask(
        self,
        query: str,
        curso: str,
        top_k: int,
        max_retries: int,
        stores_to_use: List[str],
    ) -> Tuple[str, List[Dict[str, Any]], str, Dict[str, Any]]:
        system_instruction = self._build_system_instruction(curso)
        models_chain = [PRIMARY_MODEL]

        # Declaração da Function Call de embeddings
        tool_declaration = types.Tool(function_declarations=[
            types.FunctionDeclaration(
                name="consultar_normas_academicas",
                description=(
                    "Realiza busca por embeddings na FileSearchStore do(s) curso(s) para recuperar "
                    f"os top {top_k} chunks mais similares via similaridade de cosseno."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "duvida_especifica": types.Schema(
                            type=types.Type.STRING,
                            description="Consulta otimizada para busca de embeddings por similaridade de cosseno nos documentos do(s) curso(s)."
                        )
                    },
                    required=["duvida_especifica"]
                )
            )
        ])

        file_search_tool = types.Tool(
            file_search=types.FileSearch(
                file_search_store_names=stores_to_use,
                top_k=top_k
            )
        )

        total_in_tokens = 0
        total_out_tokens = 0

        for m_tag in models_chain:
            recitation_hit = False
            for attempt in range(1, max_retries + 1):
                try:
                    if self.use_two_step_function_call:
                        rate_1 = self.llm_limiter.acquire()
                        cfg1 = {
                            "system_instruction": system_instruction,
                            "tools": [tool_declaration],
                            "temperature": 0.15
                        }
                        if self.is_paid:
                            cfg1["service_tier"] = "flex"
                        resp1 = self.client.models.generate_content(
                            model=m_tag,
                            contents=query,
                            config=types.GenerateContentConfig(**cfg1)
                        )
                        total_in_tokens += getattr(resp1.usage_metadata, "prompt_token_count", 0) or 0
                        total_out_tokens += getattr(resp1.usage_metadata, "candidates_token_count", 0) or 0

                        fcalls = getattr(resp1, "function_calls", None) or []
                        if not fcalls and resp1.text:
                            return (
                                resp1.text.strip(),
                                [],
                                f"{m_tag} (Resposta Direta)",
                                {
                                    "input_tokens": total_in_tokens,
                                    "output_tokens": total_out_tokens,
                                    "rpm_last": rate_1["rpm_current"],
                                    "rpd_last": rate_1["rpd_current"]
                                }
                            )

                        search_query = query
                        if fcalls and fcalls[0].args:
                            search_query = fcalls[0].args.get("duvida_especifica", query) or query

                        self.emb_limiter.acquire()
                        rate_2 = self.llm_limiter.acquire()

                        grounded_prompt = (
                            f"Pergunta do discente: {query}\n"
                            f"Termo de busca normativa (function call): {search_query}\n\n"
                            f"Utilize os fragmentos recuperados da FileSearchStore (top {top_k} chunks via similaridade cosseno) "
                            f"para responder de forma completa, precisa e fiel às normas do(s) curso(s) de {curso}."
                        )

                        cfg2 = {
                            "system_instruction": system_instruction,
                            "tools": [file_search_tool],
                            "temperature": 0.15
                        }
                        if self.is_paid:
                            cfg2["service_tier"] = "flex"
                        resp2 = self.client.models.generate_content(
                            model=m_tag,
                            contents=grounded_prompt,
                            config=types.GenerateContentConfig(**cfg2)
                        )
                        total_in_tokens += getattr(resp2.usage_metadata, "prompt_token_count", 0) or 0
                        total_out_tokens += getattr(resp2.usage_metadata, "candidates_token_count", 0) or 0

                        if resp2 and resp2.text:
                            chunks = self._extract_grounding_chunks(resp2)
                            return (
                                resp2.text.strip(),
                                chunks,
                                f"{m_tag} (Function Call + FileSearch top_k={top_k})",
                                {
                                    "search_query": search_query,
                                    "input_tokens": total_in_tokens,
                                    "output_tokens": total_out_tokens,
                                    "chunks_returned": len(chunks),
                                    "rpm_last": rate_2["rpm_current"],
                                    "rpd_last": rate_2["rpd_current"]
                                }
                            )
                    else:
                        self.emb_limiter.acquire()
                        rate_1 = self.llm_limiter.acquire()
                        sys_inst_cur = system_instruction
                        temp_cur = 0.15
                        if recitation_hit:
                            sys_inst_cur = (
                                f"{system_instruction}\n\n"
                                "[INSTRUÇÃO ADICIONAL]: Responda sintetizando e parafraseando as informações "
                                "com suas próprias palavras, de forma clara e objetiva, sem reproduzir "
                                "literalmente parágrafos ou frases inteiras dos documentos."
                            )
                            temp_cur = 0.35
                        cfg_direct = {
                            "system_instruction": sys_inst_cur,
                            "tools": [file_search_tool],
                            "temperature": temp_cur,
                        }
                        if self.is_paid:
                            cfg_direct["service_tier"] = "flex"
                        resp = self.client.models.generate_content(
                            model=m_tag,
                            contents=query,
                            config=types.GenerateContentConfig(**cfg_direct)
                        )
                        total_in_tokens += getattr(resp.usage_metadata, "prompt_token_count", 0) or 0
                        total_out_tokens += getattr(resp.usage_metadata, "candidates_token_count", 0) or 0

                        resp_text = getattr(resp, "text", None) if resp else None
                        if resp and resp_text and resp_text.strip():
                            chunks = self._extract_grounding_chunks(resp)
                            return (
                                resp_text.strip(),
                                chunks,
                                f"{m_tag} (Native FileSearch top_k={top_k})",
                                {
                                    "input_tokens": total_in_tokens,
                                    "output_tokens": total_out_tokens,
                                    "chunks_returned": len(chunks),
                                    "rpm_last": rate_1["rpm_current"],
                                    "rpd_last": rate_1["rpd_current"]
                                }
                            )
                        cands = getattr(resp, "candidates", None) or []
                        fr = getattr(cands[0], "finish_reason", "UNKNOWN") if cands else "NO_CANDIDATES"
                        if "RECITATION" in str(fr).upper():
                            recitation_hit = True
                        raise RuntimeError(f"Resposta vazia do modelo {m_tag} (finish_reason={fr})")

                except RPDLimitExceededError:
                    raise
                except Exception as e:
                    err_str = str(e)
                    if "RPD EXCEDIDO" in err_str.upper() or "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                        if "RPD EXCEDIDO" in err_str.upper() or attempt >= 2:
                            raise RuntimeError(f"429 RESOURCE_EXHAUSTED no RAGTradicional ({self.key_id}): {err_str[:120]}")
                        time.sleep(5)
                    elif "403" in err_str or "PERMISSION_DENIED" in err_str:
                        raise RuntimeError(f"403 PERMISSION_DENIED no RAGTradicional ({self.key_id}): {err_str[:120]}")
                    else:
                        time.sleep(min(15, 3 * attempt))
                    if attempt == max_retries:
                        print(f"[RAGTradicional Error] Modelo {m_tag} falhou após {max_retries} tentativas: {e}", flush=True)

        raise RuntimeError(f"Falha ao obter resposta do RAG Tradicional para a pergunta: {query[:80]}...")
