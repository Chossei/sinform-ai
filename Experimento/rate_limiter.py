"""
Controle Centralizado e Thread-Safe de Rate Limiting (RPM e RPD) para o Experimento Sinform AI.

Limites estritos do nível gratuito (conforme 'instrucoes adicionais.md'):
- gemini-3.5-flash-lite: 15 RPM (requisições por minuto) | 500 RPD (requisições por dia)
- gemini-embedding-2:   100 RPM (requisições por minuto) | 1000 RPD (requisições por dia)

Funciona com chamadas paralelas (ThreadPoolExecutor) garantindo:
1. Janela deslizante de 60 segundos (Sliding Window) + espaçamento mínimo seguro para evitar bursts 429.
2. Persistência do contador diário (RPD) em disco ('Experimento/logs/rpd_state.json') por chave de API e modelo.
"""

import json
import time
import threading
from datetime import datetime
from pathlib import Path
from collections import deque
from typing import Dict, Optional

EXPERIMENTO_DIR = Path(__file__).resolve().parent
LOGS_DIR = EXPERIMENTO_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
RPD_STATE_FILE = LOGS_DIR / "rpd_state.json"


class RPDLimitExceededError(RuntimeError):
    """Exceção lançada quando o limite diário (RPD) de um modelo é atingido."""
    pass


class ModelRateLimiter:
    """
    Controlador thread-safe de RPM (Sliding Window de 60s + intervalo mínimo) e RPD (contador diário persistido).
    """

    def __init__(
        self,
        model_name: str,
        rpm_limit: int,
        rpd_limit: int,
        key_id: str = "default",
        safety_margin_sec: float = 0.25
    ):
        self.model_name = model_name
        self.rpm_limit = rpm_limit
        self.rpd_limit = rpd_limit
        self.key_id = key_id
        self.bucket_key = f"{key_id}::{model_name}"

        # Espaçamento mínimo entre requisições consecutivas para evitar rajadas (bursts) na API gratuita
        self.min_interval = (60.0 / float(rpm_limit)) + safety_margin_sec

        self._lock = threading.Lock()
        self._timestamps = deque()
        self._last_request_ts = 0.0

    def _get_today_str(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _load_and_increment_rpd(self) -> int:
        """Lê e incrementa atomicamente o contador diário (RPD) no arquivo JSON."""
        today = self._get_today_str()
        data = {}
        if RPD_STATE_FILE.exists():
            try:
                with open(RPD_STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}

        if data.get("date") != today:
            data = {"date": today, "counts": {}}

        counts = data.setdefault("counts", {})
        current_count = int(counts.get(self.bucket_key, 0))

        if current_count >= self.rpd_limit:
            raise RPDLimitExceededError(
                f"[RPD EXCEDIDO] Modelo '{self.model_name}' (chave '{self.key_id}') "
                f"atingiu o limite diário de {self.rpd_limit} RPD em {today}."
            )

        new_count = current_count + 1
        counts[self.bucket_key] = new_count

        try:
            with open(RPD_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        return new_count

    def get_current_rpd(self) -> int:
        """Retorna o consumo acumulado de RPD no dia atual."""
        with self._lock:
            today = self._get_today_str()
            if not RPD_STATE_FILE.exists():
                return 0
            try:
                with open(RPD_STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("date") != today:
                    return 0
                return int(data.get("counts", {}).get(self.bucket_key, 0))
            except Exception:
                return 0

    def acquire(self) -> Dict[str, int]:
        """
        Bloqueia a thread atual até que haja slot disponível tanto na janela de 60s (RPM)
        quanto no espaçamento mínimo e no limite diário (RPD).
        Retorna dicionário com {'rpm_current': ..., 'rpd_current': ...}.
        """
        while True:
            with self._lock:
                now = time.monotonic()

                # Remove timestamps com mais de 60 segundos
                while self._timestamps and (now - self._timestamps[0]) >= 60.0:
                    self._timestamps.popleft()

                # Verifica se a janela de 60s está cheia
                wait_window = 0.0
                if len(self._timestamps) >= self.rpm_limit:
                    wait_window = 60.05 - (now - self._timestamps[0])

                # Verifica espaçamento mínimo entre chamadas para evitar 429 por burst
                wait_pacing = 0.0
                if self._last_request_ts > 0:
                    elapsed = now - self._last_request_ts
                    if elapsed < self.min_interval:
                        wait_pacing = self.min_interval - elapsed

                wait_time = max(wait_window, wait_pacing)

                if wait_time <= 0:
                    # Verifica e incrementa RPD
                    rpd_count = self._load_and_increment_rpd()
                    now_final = time.monotonic()
                    self._timestamps.append(now_final)
                    self._last_request_ts = now_final
                    return {
                        "rpm_current": len(self._timestamps),
                        "rpd_current": rpd_count
                    }

            # Dorme fora do lock pelo tempo necessário (em fatias curtas para responsividade)
            time.sleep(min(wait_time, 0.5))


# Registro global de limiters por (key_id, model_name)
_REGISTRY_LOCK = threading.Lock()
_LIMITERS: Dict[str, ModelRateLimiter] = {}


def get_rate_limiter(model_name: str, key_id: str = "default") -> ModelRateLimiter:
    """
    Obtém ou instancia o limitador oficial para o modelo e chave informados:
    - gemini-3.5-flash-lite / gemini-3.1-flash-lite: 15 RPM, 500 RPD
    - gemini-embedding-2: 100 RPM, 1000 RPD
    - typesafe/jev-1.14: 60 RPM, 10000 RPD
    """
    clean_model = model_name.replace("models/", "").lower()
    if "embedding-2" in clean_model:
        canonical = "gemini-embedding-2"
        rpm, rpd = 100, 1000
        margin = 0.05
    elif "flash-lite" in clean_model:
        canonical = "gemini-3.5-flash-lite"
        rpm, rpd = 15, 500
        margin = 0.25
    elif "jev" in clean_model:
        canonical = "typesafe/jev-1.14"
        rpm, rpd = 60, 10000
        margin = 0.05
    else:
        canonical = clean_model
        rpm, rpd = 15, 500
        margin = 0.25

    reg_key = f"{key_id}::{canonical}"
    with _REGISTRY_LOCK:
        if reg_key not in _LIMITERS:
            _LIMITERS[reg_key] = ModelRateLimiter(
                model_name=canonical,
                rpm_limit=rpm,
                rpd_limit=rpd,
                key_id=key_id,
                safety_margin_sec=margin
            )
        return _LIMITERS[reg_key]

