import streamlit as st
from dashboard_experimento import render_experiment_dashboard

st.set_page_config(
    page_title="Sinform AI | Benchmark de Métodos de RAG (UFBA)",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

render_experiment_dashboard(embedded=False)
