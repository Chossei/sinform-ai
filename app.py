import sys
import time
import importlib
from pathlib import Path
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

st.set_page_config(
    page_title="Sinform AI | Benchmark de Métodos de RAG (UFBA)",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def _load_dashboard_renderer():
    for attempt in range(4):
        try:
            mod = importlib.import_module("dashboard_experimento")
            return mod.render_experiment_dashboard
        except KeyError:
            if attempt == 3:
                raise
            time.sleep(0.2)


render_fn = _load_dashboard_renderer()
render_fn(embedded=False)
