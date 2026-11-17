from typing import Any
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# ==============================================================================
# CSS ESTILIZADO — ESTÉTICA MINIMALISTA INSPIRADA NO MATHLLMS
# ==============================================================================
DASHBOARD_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #0f172a;
    }

    .page-header {
        padding: 0.35rem 0 0.9rem 0;
        margin-bottom: 0.65rem;
    }
    .page-header h1 {
        margin: 0;
        font-size: 1.95rem;
        font-weight: 800;
        letter-spacing: -0.025em;
        color: #0f172a;
        line-height: 1.2;
    }
    .page-header p {
        margin: 0.4rem 0 0 0;
        font-size: 0.95rem;
        color: #64748b;
        line-height: 1.5;
    }

    .kpi-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.05rem 1.2rem;
        height: 100%;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    .kpi-card:hover {
        border-color: #cbd5e1;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06);
    }
    .kpi-label {
        font-size: 0.72rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.35rem;
    }
    .kpi-value {
        font-size: 1.7rem;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: -0.02em;
        line-height: 1.15;
    }
    .kpi-sub {
        font-size: 0.79rem;
        color: #64748b;
        margin-top: 0.32rem;
        line-height: 1.35;
    }

    .kpi-split-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.65rem;
        margin-top: 0.75rem;
        padding-top: 0.65rem;
        border-top: 1px solid #f1f5f9;
    }
    .kpi-split-label {
        font-size: 0.7rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    .kpi-split-val {
        font-size: 0.98rem;
        font-weight: 700;
        color: #1e293b;
        margin-top: 0.1rem;
    }

    .mini-stat-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 9px;
        padding: 0.75rem 0.95rem;
        height: 100%;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
    }
    .mini-stat-label {
        font-size: 0.68rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .mini-stat-val {
        font-size: 1.25rem;
        font-weight: 800;
        color: #0f172a;
        margin-top: 0.15rem;
    }
    .mini-stat-sub {
        font-size: 0.78rem;
        color: #475569;
        margin-top: 0.1rem;
        font-weight: 500;
    }

    .intro-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.35rem 1.5rem;
        height: 100%;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03);
        color: #1e293b;
        font-size: 0.92rem;
        line-height: 1.62;
    }
    .intro-card h3 {
        margin-top: 0;
        margin-bottom: 0.7rem;
        font-size: 1.08rem;
        font-weight: 700;
        color: #0f172a;
        display: flex;
        align-items: center;
        gap: 0.45rem;
    }
    .intro-card p {
        margin-bottom: 0.72rem;
        text-align: justify;
    }
    .intro-card ul {
        margin: 0.35rem 0 0 0;
        padding-left: 1.15rem;
    }
    .intro-card li {
        margin-bottom: 0.5rem;
        text-align: justify;
    }

    .callout-card {
        background: #f0f7ff;
        border: 1px solid #bfdbfe;
        border-radius: 10px;
        padding: 1.35rem 1.5rem;
        height: 100%;
        color: #1e293b;
        font-size: 0.92rem;
        line-height: 1.62;
    }
    .callout-card h3, .callout-card h4 {
        margin-top: 0;
        margin-bottom: 0.65rem;
        color: #0f172a;
        font-size: 1.08rem;
        font-weight: 700;
    }
    .formula-box {
        background: #ffffff;
        border: 1px solid #bfdbfe;
        border-radius: 8px;
        padding: 0.85rem 1rem;
        font-family: 'Cambria Math', 'Inter', monospace;
        font-size: 0.95rem;
        text-align: center;
        color: #1d4ed8;
        margin: 0.75rem 0;
        font-weight: 600;
    }

    .section-header {
        margin: 1.35rem 0 0.75rem 0;
        padding-bottom: 0.4rem;
        border-bottom: 1px solid #e2e8f0;
        color: #0f172a;
        font-weight: 700;
        font-size: 1.24rem;
        letter-spacing: -0.015em;
    }
    .subsection-header {
        margin: 1.15rem 0 0.55rem 0;
        color: #0f172a;
        font-weight: 700;
        font-size: 1.08rem;
        letter-spacing: -0.01em;
    }
    .column-question-title {
        margin: 0.25rem 0 0.55rem 0;
        color: #0f172a;
        font-weight: 700;
        font-size: 1.02rem;
        letter-spacing: -0.01em;
    }

    .interactive-weight-row {
        display: flex;
        align-items: center;
        gap: 0.65rem;
        padding: 0.42rem 0.6rem;
        border-radius: 8px;
        transition: transform 0.15s ease, background 0.15s ease;
        margin-bottom: 0.3rem;
        cursor: default;
    }
    .interactive-weight-row:hover {
        transform: translateX(3px);
        background: #f8fafc;
    }

    /* Abas minimalistas no estilo Streamlit moderno / mathllms */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1.5rem;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 0;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 0.92rem;
        font-weight: 500;
        color: #475569;
        padding: 0.55rem 0.15rem;
    }
    .stTabs [aria-selected="true"] {
        color: #0f172a !important;
        font-weight: 600 !important;
    }
</style>
"""

# ==============================================================================
# CONSTANTES E MAPEAMENTOS
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent
EXP_DIR = BASE_DIR / "Experimento"
RESULTADOS_PATH = EXP_DIR / "Resultados do teste.xlsx"
DATASET_200_PATH = EXP_DIR / "Conjunto de Testes 200.xlsx"

ORDEM_CONFIGS = [
    "RAG Tradicional (k=1)",
    "RAG Tradicional (k=5)",
    "RAG Tradicional (k=10)",
    "Fichamento + Embedding (k=1)",
    "Fichamento + Embedding (k=5)",
    "Fichamento + Embedding (k=10)",
    "Fichamento + JEV Top-K (k=1)",
    "Fichamento + JEV Top-K (k=5)",
    "Fichamento + JEV Top-K (k=10)",
    "Fichamento + JEV Livre",
]

CORES_DECISAO = {
    "Incorreta": "#ef4444",
    "Parcialmente incorreta": "#fca5a5",
    "Parcialmente correta": "#86efac",
    "Correta": "#10b981",
}

TEXT_CORES_DECISAO = {
    "Incorreta": "#ffffff",
    "Parcialmente incorreta": "#7f1d1d",
    "Parcialmente correta": "#064e3b",
    "Correta": "#ffffff",
}

# Sequência da legenda de Incorreta para Correta
ORDEM_DECISAO = [
    "Incorreta",
    "Parcialmente incorreta",
    "Parcialmente correta",
    "Correta",
]

ORDEM_FAIXAS_DOCS = ["1", "2", "3", "4+"]

# Padrão de cor azul da fórmula do Score Esperado (.callout-card / .formula-box)
LIGHT_BLUE_BOX = "#bfdbfe"
LIGHT_BLUE_BORDER = "#1d4ed8"
COR_COBALTO = "#2563eb"
COR_COBALTO_CLARO = "#93c5fd"
COR_AMBAR = "#f59e0b"
COR_GRID = "#f1f5f9"

FAMILIA_NOMES = {
    "rag_tradicional": "RAG Tradicional",
    "rag_fichamento_embedding": "Fichamento + Embedding",
    "rag_fichamento_jev_topk": "Fichamento + JEV Top-K",
    "rag_fichamento_jev_livre": "Fichamento + JEV Livre",
}

FAMILIA_CORES = {
    "RAG Tradicional": "#7c3aed",
    "Fichamento + Embedding": "#2563eb",
    "Fichamento + JEV Top-K": "#eab308",
    "Fichamento + JEV Livre": "#10b981",
}


def _clean_html(html_block: str) -> str:
    """Remove indentação por linha para evitar que o parser Markdown do Streamlit renderize divs como bloco de código."""
    lines = [line.lstrip() for line in html_block.strip().splitlines()]
    return "\n".join(line for line in lines if line)


def format_config_label(row: pd.Series) -> str:
    m = str(row.get("metodo_rag", "")).strip()
    k = str(row.get("top_k", "")).strip()
    if m == "rag_tradicional":
        return f"RAG Tradicional (k={k})"
    if m == "rag_fichamento_embedding":
        return f"Fichamento + Embedding (k={k})"
    if m == "rag_fichamento_jev_topk":
        return f"Fichamento + JEV Top-K (k={k})"
    if m == "rag_fichamento_jev_livre":
        return "Fichamento + JEV Livre"
    return f"{m} (k={k})"


def categorize_doc_count(n: Any) -> str:
    try:
        val = int(float(n))
    except Exception:
        val = 1
    if val <= 1:
        return "1"
    if val == 2:
        return "2"
    if val == 3:
        return "3"
    return "4+"


def normalize_classificacao(val: Any, doc_str: Any = "") -> str:
    s = str(val or "").strip().lower()
    if "híbrida" in s or "hibrida" in s or "multi" in s:
        return "híbrida"
    if "única" in s or "unica" in s:
        return "única"
    if ";" in str(doc_str or ""):
        return "híbrida"
    return "única"


@st.cache_data(ttl=15)
def load_results_data(file_path: str) -> pd.DataFrame:
    p = Path(file_path)
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_excel(p)
    if df.empty:
        return df

    df["config_label"] = df.apply(format_config_label, axis=1)
    df["familia_metodo"] = df["metodo_rag"].map(FAMILIA_NOMES).fillna(df["metodo_rag"].astype(str))

    if "Classificação" in df.columns:
        df["tipo_pergunta"] = df.apply(
            lambda r: normalize_classificacao(r.get("Classificação"), r.get("Documento")), axis=1
        )
    elif "tipo_pergunta" in df.columns:
        df["tipo_pergunta"] = df.apply(
            lambda r: normalize_classificacao(r.get("tipo_pergunta"), r.get("Documento")), axis=1
        )
    else:
        tipo_map = {}
        if DATASET_200_PATH.exists():
            try:
                df_200 = pd.read_excel(DATASET_200_PATH)
                for _, r200 in df_200.iterrows():
                    tipo_map[str(r200.get("Pergunta", "")).strip()] = normalize_classificacao(
                        r200.get("Classificação"), r200.get("Documento")
                    )
            except Exception:
                pass
        df["tipo_pergunta"] = df.apply(
            lambda r: tipo_map.get(
                str(r.get("Pergunta", "")).strip(),
                normalize_classificacao("", r.get("Documento")),
            ),
            axis=1,
        )

    c_inc = "logprob_julgador_Incorreta"
    c_pinc = "logprob_julgador_Parcialmente_incorreta"
    c_pcor = "logprob_julgador_Parcialmente_correta"
    c_cor = "logprob_julgador_Correta"

    for col in [c_inc, c_pinc, c_pcor, c_cor]:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    raw_mat = df[[c_inc, c_pinc, c_pcor, c_cor]].to_numpy(dtype=float)
    if (raw_mat < -1e-6).any():
        prob_mat = np.exp(raw_mat)
    else:
        prob_mat = np.clip(raw_mat, 0.0, 1.0)

    row_sums = prob_mat.sum(axis=1, keepdims=True)
    row_sums[row_sums <= 0] = 1.0
    prob_mat = prob_mat / row_sums

    df["peso_inc"] = prob_mat[:, 0]
    df["peso_pinc"] = prob_mat[:, 1]
    df["peso_pcor"] = prob_mat[:, 2]
    df["peso_cor"] = prob_mat[:, 3]

    # Score Esperado = Peso_inc * 0 + Peso_pinc * 0.15 + Peso_pcor * 0.55 + Peso_cor * 1.0
    df["score_esperado"] = (
        df["peso_inc"] * 0.00
        + df["peso_pinc"] * 0.15
        + df["peso_pcor"] * 0.55
        + df["peso_cor"] * 1.00
    ).clip(0.0, 1.0)

    for c_cost in ["custo_gemini", "custo_jev_consultas", "custo_jev_julgador"]:
        if c_cost not in df.columns:
            df[c_cost] = 0.0
        df[c_cost] = pd.to_numeric(df[c_cost], errors="coerce").fillna(0.0)

    df["custo_operacional"] = df["custo_gemini"] + df["custo_jev_consultas"]
    df["quantidade_documentos"] = pd.to_numeric(df["quantidade_documentos"], errors="coerce").fillna(0)
    df["faixa_documentos"] = df["quantidade_documentos"].apply(categorize_doc_count)
    return df


def compute_config_summary(df: pd.DataFrame, sort_by_score: bool = True) -> pd.DataFrame:
    """Agrega todas as métricas-chave por configuração de RAG para cards e gráficos."""
    rows = []
    for cfg in ORDEM_CONFIGS:
        sub = df[df["config_label"] == cfg]
        if sub.empty:
            continue
        dec = sub["decisao_julgador"]
        n = len(sub)
        cor_pct = float((dec == "Correta").mean() * 100.0)
        pcor_pct = float((dec == "Parcialmente correta").mean() * 100.0)
        pinc_pct = float((dec == "Parcialmente incorreta").mean() * 100.0)
        inc_pct = float((dec == "Incorreta").mean() * 100.0)
        score_mean = float(sub["score_esperado"].mean())
        score_std = float(sub["score_esperado"].std(ddof=1)) if n > 1 else 0.0
        custo_200 = float(sub["custo_operacional"].sum())
        custo_1k = float(sub["custo_operacional"].mean() * 1000.0)
        docs_mean = float(sub["quantidade_documentos"].mean())
        familia = str(sub["familia_metodo"].iloc[0])
        top_k = str(sub["top_k"].iloc[0])

        rows.append(
            {
                "config_label": cfg,
                "familia_metodo": familia,
                "top_k": top_k,
                "n": n,
                "score_mean": score_mean,
                "score_std": score_std,
                "correta_pct": cor_pct,
                "parc_correta_pct": pcor_pct,
                "parc_incorreta_pct": pinc_pct,
                "incorreta_pct": inc_pct,
                "positiva_pct": cor_pct + pcor_pct,
                "erro_grave_pct": inc_pct + pinc_pct,
                "docs_mean": docs_mean,
                "custo_200": custo_200,
                "custo_1k": custo_1k,
            }
        )
    summary = pd.DataFrame(rows)
    if not summary.empty and sort_by_score:
        summary = summary.sort_values(
            by=["score_mean", "positiva_pct"], ascending=[False, False]
        ).reset_index(drop=True)
    return summary


# ==============================================================================
# FUNÇÕES DE PLOTAGEM PLOTLY
# ==============================================================================
def build_diverging_accuracy_bar(
    df_sub: pd.DataFrame,
    title: str = "Distribuição do acerto (%) por método de RAG empregado",
    height: int = 470,
) -> go.Figure:
    """
    Barras empilhadas horizontais DIVERGENTES centradas em 0%, em ordem crescente
    da soma (Incorreta + Parcialmente incorreta) de cima para baixo:
    - Esquerda (negativo): Parcialmente incorreta + Incorreta
    - Direita (positivo): Parcialmente correta + Correta
    - Legenda ordenada de Incorreta para Correta.
    """
    summary = compute_config_summary(df_sub, sort_by_score=False)
    if summary.empty:
        fig = go.Figure()
        fig.update_layout(title=title, height=height)
        return fig

    # Ordem crescente da soma (Incorreta + Parcialmente incorreta) de cima para baixo
    summary = summary.sort_values(
        by=["erro_grave_pct", "incorreta_pct", "correta_pct"],
        ascending=[True, True, False],
    ).reset_index(drop=True)
    summary_plot = summary.iloc[::-1].reset_index(drop=True)
    configs_y = summary_plot["config_label"].tolist()

    legend_ranks = {
        "Incorreta": 1,
        "Parcialmente incorreta": 2,
        "Parcialmente correta": 3,
        "Correta": 4,
    }

    fig = go.Figure()

    # Lado positivo (direita): Parcialmente correta primeiro (perto de 0), Correta em seguida
    for cat, col_name in [("Parcialmente correta", "parc_correta_pct"), ("Correta", "correta_pct")]:
        vals = summary_plot[col_name].to_numpy()
        fig.add_trace(
            go.Bar(
                name=cat,
                legendrank=legend_ranks[cat],
                y=configs_y,
                x=vals,
                orientation="h",
                marker_color=CORES_DECISAO[cat],
                text=[f"{v:.1f}%" if v >= 6.5 else "" for v in vals],
                textposition="inside",
                insidetextanchor="middle",
                textangle=0,
                textfont=dict(color=TEXT_CORES_DECISAO[cat], size=10.5, family="Inter"),
                customdata=np.stack([vals, summary_plot["score_mean"], summary_plot["positiva_pct"]], axis=-1),
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    f"Categoria: <b>{cat}</b><br>"
                    "Proporção: <b>%{customdata[0]:.1f}%</b><br>"
                    "Parcial + Correta: <b>%{customdata[2]:.1f}%</b> | Score: <b>%{customdata[1]:.3f}</b>"
                    "<extra></extra>"
                ),
            )
        )

    # Lado negativo (esquerda): Parcialmente incorreta primeiro (perto de 0), Incorreta em seguida
    for cat, col_name in [("Parcialmente incorreta", "parc_incorreta_pct"), ("Incorreta", "incorreta_pct")]:
        vals = summary_plot[col_name].to_numpy()
        fig.add_trace(
            go.Bar(
                name=cat,
                legendrank=legend_ranks[cat],
                y=configs_y,
                x=-vals,
                orientation="h",
                marker_color=CORES_DECISAO[cat],
                text=[f"{v:.1f}%" if v >= 6.5 else "" for v in vals],
                textposition="inside",
                insidetextanchor="middle",
                textangle=0,
                textfont=dict(color=TEXT_CORES_DECISAO[cat], size=10.5, family="Inter"),
                customdata=np.stack([vals, summary_plot["score_mean"], summary_plot["erro_grave_pct"]], axis=-1),
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    f"Categoria: <b>{cat}</b><br>"
                    "Proporção: <b>%{customdata[0]:.1f}%</b><br>"
                    "Soma de erros (Inc + Parc. inc): <b>%{customdata[2]:.1f}%</b> | Score: <b>%{customdata[1]:.3f}</b>"
                    "<extra></extra>"
                ),
            )
        )

    fig.add_vline(x=0, line_width=1.4, line_color="#475569")

    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=16, color="#0f172a")),
        barmode="relative",
        xaxis=dict(
            title="← Erros (Incorreta + Parc. Incorreta)   |   Acertos (Parc. Correta + Correta) →",
            range=[-105, 105],
            tickvals=[-100, -75, -50, -25, 0, 25, 50, 75, 100],
            ticktext=["100%", "75%", "50%", "25%", "0%", "25%", "50%", "75%", "100%"],
            gridcolor=COR_GRID,
            zeroline=False,
        ),
        yaxis=dict(
            tickfont=dict(size=11.5, color="#1e293b"),
            categoryorder="array",
            categoryarray=configs_y,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            traceorder="normal",
            title=dict(text="Decisão JEV 1.14: "),
        ),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        margin=dict(l=205, r=20, t=75, b=55),
        height=height,
    )
    return fig


def build_k_sensitivity_line(
    df: pd.DataFrame,
    title: str = "Percentual de respostas classificadas como incorretas por número de chunkings",
    height: int = 410,
) -> go.Figure:
    """
    Gráfico único de linha comparando o percentual de respostas Incorretas por número de chunkings (k=1, 5, 10),
    sem o Fichamento + JEV Livre:
    - RAG Tradicional: roxo (#7c3aed)
    - Fichamento + Embedding: azul (#2563eb)
    - Fichamento + JEV Top-K: amarelo (#eab308)
    """
    summary = compute_config_summary(df, sort_by_score=False).set_index("config_label")
    x_labels = ["k = 1", "k = 5", "k = 10"]

    series_specs = [
        (
            "RAG Tradicional",
            ["RAG Tradicional (k=1)", "RAG Tradicional (k=5)", "RAG Tradicional (k=10)"],
            "#7c3aed",
            ["bottom center", "bottom center", "bottom right"],
        ),
        (
            "Fichamento + Embedding",
            ["Fichamento + Embedding (k=1)", "Fichamento + Embedding (k=5)", "Fichamento + Embedding (k=10)"],
            "#2563eb",
            ["top center", "top center", "top center"],
        ),
        (
            "Fichamento + JEV Top-K",
            ["Fichamento + JEV Top-K (k=1)", "Fichamento + JEV Top-K (k=5)", "Fichamento + JEV Top-K (k=10)"],
            "#eab308",
            ["top center", "top right", "bottom left"],
        ),
    ]

    fig = go.Figure()
    max_inc = 0.0

    for fam_name, cfg_keys, color_hex, text_positions in series_specs:
        y_vals = [
            float(summary.loc[k, "incorreta_pct"]) if k in summary.index else 0.0
            for k in cfg_keys
        ]
        scores = [
            float(summary.loc[k, "score_mean"]) if k in summary.index else 0.0
            for k in cfg_keys
        ]
        if y_vals:
            max_inc = max(max_inc, max(y_vals))

        fig.add_trace(
            go.Scatter(
                name=fam_name,
                x=x_labels,
                y=y_vals,
                mode="lines+markers+text",
                line=dict(color=color_hex, width=3),
                marker=dict(size=10, color=color_hex, line=dict(color="#ffffff", width=1.8)),
                text=[f"<b>{v:.1f}%</b>" for v in y_vals],
                textposition=text_positions,
                textfont=dict(size=11, color="#0f172a", family="Inter"),
                customdata=scores,
                hovertemplate=(
                    f"<b>{fam_name}</b> (%{{x}})<br>"
                    "Respostas Incorretas: <b>%{y:.1f}%</b><br>"
                    "Score Esperado Médio: <b>%{customdata:.3f}</b><extra></extra>"
                ),
            )
        )

    y_upper = max(50.0, float(np.ceil((max_inc + 7.0) / 10.0) * 10.0))
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=16, color="#0f172a")),
        xaxis=dict(
            title="Número de Chunkings (Top-k)",
            tickfont=dict(size=11.5, color="#1e293b"),
            gridcolor=COR_GRID,
        ),
        yaxis=dict(
            title="Respostas Incorretas (%)",
            range=[0, y_upper],
            ticksuffix="%",
            gridcolor=COR_GRID,
            zerolinecolor="#e2e8f0",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            title=dict(text="Método de RAG: "),
        ),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        height=height,
        margin=dict(l=55, r=30, t=75, b=55),
    )
    return fig


def build_positive_sum_bar(
    df_sub: pd.DataFrame,
    title: str = "Soma de respostas Parcialmente corretas e Corretas (%)",
    height: int = 440,
) -> go.Figure:
    """
    Barras empilhadas somando Correta + Parcialmente correta (%) por configuração,
    em ordem decrescente da esquerda para a direita.
    """
    summary = compute_config_summary(df_sub, sort_by_score=False)
    if summary.empty:
        fig = go.Figure()
        fig.update_layout(title=title, height=height)
        return fig

    summary = summary.sort_values(
        by=["positiva_pct", "correta_pct", "score_mean"],
        ascending=[False, False, False],
    ).reset_index(drop=True)

    configs_x = summary["config_label"].tolist()
    cor_vals = summary["correta_pct"].to_numpy()
    pcor_vals = summary["parc_correta_pct"].to_numpy()
    soma_vals = summary["positiva_pct"].to_numpy()

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Parcialmente correta",
            legendrank=1,
            x=configs_x,
            y=pcor_vals,
            marker_color=CORES_DECISAO["Parcialmente correta"],
            text=[f"{v:.0f}%" if v >= 10.0 else "" for v in pcor_vals],
            textposition="inside",
            insidetextanchor="middle",
            textangle=0,
            textfont=dict(color=TEXT_CORES_DECISAO["Parcialmente correta"], size=10, family="Inter"),
            customdata=np.stack([soma_vals, summary["score_mean"]], axis=-1),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Parcialmente correta: <b>%{y:.1f}%</b><br>"
                "Soma (Parcial + Correta): <b>%{customdata[0]:.1f}%</b><br>"
                "Score Esperado: <b>%{customdata[1]:.3f}</b><extra></extra>"
            ),
        )
    )
    fig.add_trace(
        go.Bar(
            name="Correta",
            legendrank=2,
            x=configs_x,
            y=cor_vals,
            marker_color=CORES_DECISAO["Correta"],
            text=[f"{v:.0f}%" if v >= 10.0 else "" for v in cor_vals],
            textposition="inside",
            insidetextanchor="middle",
            textangle=0,
            textfont=dict(color=TEXT_CORES_DECISAO["Correta"], size=10, family="Inter"),
            customdata=np.stack([soma_vals, summary["score_mean"]], axis=-1),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Correta: <b>%{y:.1f}%</b><br>"
                "Soma (Parcial + Correta): <b>%{customdata[0]:.1f}%</b><br>"
                "Score Esperado: <b>%{customdata[1]:.3f}</b><extra></extra>"
            ),
        )
    )

    # Rótulo com a SOMA total no topo de cada barra
    fig.add_trace(
        go.Scatter(
            x=configs_x,
            y=soma_vals + 3.0,
            mode="text",
            text=[f"<b>{v:.1f}%</b>" for v in soma_vals],
            textfont=dict(size=10.5, color="#0f172a", family="Inter"),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=14.5, color="#0f172a")),
        barmode="stack",
        xaxis=dict(
            tickangle=-30,
            tickfont=dict(size=10.5, color="#1e293b"),
            categoryorder="array",
            categoryarray=configs_x,
        ),
        yaxis=dict(
            title="Parcial + Correta (%)",
            range=[0, 110],
            tickvals=[0, 20, 40, 60, 80, 100],
            ticksuffix="%",
            gridcolor=COR_GRID,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
        ),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        margin=dict(l=48, r=15, t=68, b=115),
        height=height,
    )
    return fig


def build_general_score_boxplot(
    df_sub: pd.DataFrame,
    title: str = "Distribuição do Score Esperado por método de RAG",
    sort_by_mean: bool = True,
    compact_badge: bool = False,
    height: int = 490,
) -> go.Figure:
    """
    Boxplot do Score Esperado seguindo o padrão de cor azul da fórmula do Score,
    com o indicador do Score Médio posicionado no topo, acima de cada boxplot.
    """
    summary = compute_config_summary(df_sub, sort_by_score=sort_by_mean)
    if summary.empty:
        fig = go.Figure()
        fig.update_layout(title=title, height=height)
        return fig

    ordered_configs = summary["config_label"].tolist()
    fig = go.Figure()

    for _, row_s in summary.iterrows():
        cfg = row_s["config_label"]
        mean_val = float(row_s["score_mean"])
        d_cfg = df_sub[df_sub["config_label"] == cfg]["score_esperado"]

        fig.add_trace(
            go.Box(
                y=d_cfg,
                name=cfg,
                boxmean=True,
                marker_color=LIGHT_BLUE_BORDER,
                line=dict(color=LIGHT_BLUE_BORDER, width=1.8),
                fillcolor=LIGHT_BLUE_BOX,
                opacity=0.88,
                boxpoints="outliers",
                hovertemplate=(
                    f"<b>{cfg}</b><br>"
                    f"Score Médio: <b>{mean_val:.3f}</b><br>"
                    "Score: <b>%{y:.3f}</b><extra></extra>"
                ),
            )
        )

        badge_text = f"<b>{mean_val:.3f}</b>" if compact_badge else f"<b>Média: {mean_val:.3f}</b>"
        # Caixinha do Score Médio posicionada no topo, acima de cada boxplot
        fig.add_annotation(
            x=cfg,
            y=1.085,
            text=badge_text,
            showarrow=False,
            font=dict(size=9.5 if compact_badge else 10, color="#1d4ed8", family="Inter"),
            bgcolor="#f0f7ff",
            bordercolor="#bfdbfe",
            borderwidth=1.2,
            borderpad=2 if compact_badge else 3,
        )

    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=15 if compact_badge else 16, color="#0f172a")),
        xaxis=dict(
            title="Método e Configuração de RAG",
            tickangle=-30 if compact_badge else -25,
            tickfont=dict(size=10.5 if compact_badge else 11, color="#1e293b"),
            categoryorder="array",
            categoryarray=ordered_configs,
        ),
        yaxis=dict(
            title="Score Esperado (0 a 1)",
            range=[-0.04, 1.17],
            tickvals=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
            gridcolor=COR_GRID,
            zeroline=False,
        ),
        showlegend=False,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        margin=dict(l=52, r=18, t=65, b=115),
        height=height,
    )
    return fig


def build_grouped_type_mean_std(
    df_sub: pd.DataFrame,
    title: str = "Score Esperado médio (± DP) em perguntas únicas e híbridas",
    height: int = 470,
) -> go.Figure:
    """
    Barras agrupadas (Única vs Híbrida) mostrando Score Esperado Médio ± Desvio Padrão,
    ordenadas por ORDEM_CONFIGS (RAG Tradicional -> Fichamento + Embedding -> Fichamento + JEV Top-K -> JEV Livre).
    """
    present_order = [c for c in ORDEM_CONFIGS if c in df_sub["config_label"].unique()]
    if not present_order:
        present_order = ORDEM_CONFIGS

    fig = go.Figure()
    configs_meta = [
        ("única", "Única (1 PDF)", COR_COBALTO),
        ("híbrida", "Híbrida (>1 PDF)", COR_AMBAR),
    ]

    for t_key, t_label, color_hex in configs_meta:
        sub_t = df_sub[df_sub["tipo_pergunta"] == t_key]
        means, stds = [], []
        for cfg in present_order:
            vals = sub_t[sub_t["config_label"] == cfg]["score_esperado"]
            means.append(float(vals.mean()) if len(vals) > 0 else 0.0)
            stds.append(float(vals.std(ddof=1)) if len(vals) > 1 else 0.0)

        fig.add_trace(
            go.Bar(
                name=t_label,
                x=present_order,
                y=means,
                error_y=dict(
                    type="data",
                    array=stds,
                    visible=True,
                    color="#475569",
                    thickness=1.3,
                    width=4,
                ),
                marker_color=color_hex,
                customdata=stds,
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    f"Tipo: <b>{t_label}</b><br>"
                    "Score Médio: <b>%{y:.3f}</b> (DP: ±%{customdata:.3f})<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=16, color="#0f172a")),
        barmode="group",
        xaxis=dict(
            title="Método e Configuração de RAG",
            tickangle=-26,
            tickfont=dict(size=11, color="#1e293b"),
            categoryorder="array",
            categoryarray=present_order,
        ),
        yaxis=dict(
            title="Score Esperado Médio (± DP)",
            range=[0, 1.18],
            tickvals=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
            gridcolor=COR_GRID,
            zerolinecolor="#e2e8f0",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            title=dict(text="Classificação da Pergunta: "),
        ),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        margin=dict(l=55, r=20, t=72, b=115),
        height=height,
    )
    return fig


def _short_cost_label(cfg: str) -> str:
    if cfg == "Fichamento + JEV Livre":
        return "JEV Livre"
    if "RAG Tradicional" in cfg:
        return "Trad " + cfg.split("(")[1].replace(")", "")
    if "Embedding" in cfg:
        return "Emb " + cfg.split("(")[1].replace(")", "")
    if "JEV Top-K" in cfg:
        return "JEV " + cfg.split("(")[1].replace(")", "")
    return cfg


def build_score_vs_cost_scatter(
    df_sub: pd.DataFrame,
    title: str = "Cruzamento entre Score Esperado Médio e Custo Total em USD",
    height: int = 440,
) -> go.Figure:
    """
    Dispersão cruzando Custo Operacional do RAG em USD com o Score Esperado Médio.
    """
    summary = compute_config_summary(df_sub, sort_by_score=True)
    if summary.empty:
        fig = go.Figure()
        fig.update_layout(title=title, height=height)
        return fig

    fig = go.Figure()
    for fam in ["RAG Tradicional", "Fichamento + Embedding", "Fichamento + JEV Top-K", "Fichamento + JEV Livre"]:
        sub_f = summary[summary["familia_metodo"] == fam]
        if sub_f.empty:
            continue

        text_pos = []
        for _, r in sub_f.iterrows():
            if r["config_label"] == "RAG Tradicional (k=10)":
                text_pos.append("top right")
            elif r["config_label"] == "RAG Tradicional (k=5)":
                text_pos.append("middle right")
            elif r["config_label"] == "RAG Tradicional (k=1)":
                text_pos.append("bottom right")
            elif "JEV Top-K (k=10)" in r["config_label"]:
                text_pos.append("bottom center")
            elif "JEV Top-K (k=1)" in r["config_label"]:
                text_pos.append("bottom center")
            else:
                text_pos.append("top center")

        fig.add_trace(
            go.Scatter(
                name=fam,
                x=sub_f["custo_200"],
                y=sub_f["score_mean"],
                mode="markers+text",
                text=[_short_cost_label(c) for c in sub_f["config_label"]],
                textposition=text_pos,
                textfont=dict(size=10.5, color="#1e293b", family="Inter"),
                marker=dict(
                    size=13,
                    color=FAMILIA_CORES.get(fam, COR_COBALTO),
                    line=dict(color="#ffffff", width=1.8),
                ),
                customdata=np.stack(
                    [
                        sub_f["config_label"],
                        sub_f["custo_1k"],
                        sub_f["correta_pct"],
                        sub_f["incorreta_pct"],
                    ],
                    axis=-1,
                ),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Score Esperado Médio: <b>%{y:.3f}</b><br>"
                    "Custo Total (200 pergs): <b>$%{x:.4f} USD</b><br>"
                    "Projeção p/ 1.000 pergs: <b>$%{customdata[1]:.4f} USD</b><br>"
                    "Corretas: <b>%{customdata[2]:.1f}%</b> | Incorretas: <b>%{customdata[3]:.1f}%</b>"
                    "<extra></extra>"
                ),
            )
        )

    max_cost = float(summary["custo_200"].max()) if not summary.empty else 0.8
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=16, color="#0f172a")),
        xaxis=dict(
            title="Custo Operacional Total para 200 Perguntas (USD)",
            range=[-0.04, max_cost * 1.13],
            tickprefix="$",
            gridcolor=COR_GRID,
            zerolinecolor="#e2e8f0",
        ),
        yaxis=dict(
            title="Score Esperado Médio",
            range=[0.25, 0.84],
            gridcolor=COR_GRID,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            title=dict(text="Arquitetura: "),
        ),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        margin=dict(l=55, r=25, t=72, b=55),
        height=height,
    )
    return fig


def build_docs_freq_and_score_chart(
    df_jev_livre: pd.DataFrame,
    title: str = "Quantidade de consultas e Score Esperado médio por faixa de fatias",
    height: int = 410,
) -> go.Figure:
    """
    Gráfico combinado (Barras de Frequência n + Linha de Score Esperado Médio)
    por faixa categorizada de fatias selecionadas ('1', '2', '3', '4+'),
    com rótulos sempre na horizontal (textangle=0).
    """
    counts, means, stds, cors = [], [], [], []
    x_labels = []
    for faixa in ORDEM_FAIXAS_DOCS:
        sub = df_jev_livre[df_jev_livre["faixa_documentos"] == faixa]
        n_obs = len(sub)
        unit_label = "fatia" if faixa == "1" else "fatias"
        x_labels.append(f"{faixa} {unit_label}<br>(n={n_obs})")
        counts.append(n_obs)
        if n_obs > 0:
            means.append(float(sub["score_esperado"].mean()))
            stds.append(float(sub["score_esperado"].std(ddof=1)) if n_obs > 1 else 0.0)
            cors.append(float((sub["decisao_julgador"] == "Correta").mean() * 100.0))
        else:
            means.append(np.nan)
            stds.append(0.0)
            cors.append(0.0)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            name="Quantidade de Perguntas (n)",
            x=x_labels,
            y=counts,
            marker_color=COR_COBALTO_CLARO,
            marker_line=dict(color="#60a5fa", width=1),
            opacity=0.65,
            text=[str(c) for c in counts],
            textposition="outside",
            textangle=0,
            constraintext="none",
            cliponaxis=False,
            textfont=dict(size=11, color="#1e3a8a", family="Inter"),
            hovertemplate="<b>%{x}</b><br>Perguntas nessa faixa: <b>%{y}</b><extra></extra>",
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            name="Score Esperado Médio",
            x=x_labels,
            y=means,
            mode="lines+markers+text",
            line=dict(color="#1d4ed8", width=3),
            marker=dict(size=10, color="#1d4ed8", line=dict(color="#ffffff", width=2)),
            text=[f"<b>{m:.3f}</b>" if pd.notna(m) else "—" for m in means],
            textposition="top center",
            textfont=dict(size=11.5, color="#0f172a", family="Inter"),
            customdata=np.stack([stds, cors, counts], axis=-1),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Score Esperado Médio: <b>%{y:.3f}</b> (DP: ±%{customdata[0]:.3f})<br>"
                "Taxa Correta: <b>%{customdata[1]:.1f}%</b><br>"
                "Observações: <b>%{customdata[2]}</b><extra></extra>"
            ),
        ),
        secondary_y=True,
    )

    max_n = max(counts) if counts else 10
    fig.update_yaxes(
        title_text="Número de Perguntas (n)",
        range=[0, max(12, max_n * 1.24)],
        gridcolor=COR_GRID,
        secondary_y=False,
        tickfont=dict(size=10.5, color="#64748b"),
    )
    fig.update_yaxes(
        title_text="Score Esperado Médio (0 a 1)",
        range=[0, 1.12],
        showgrid=False,
        secondary_y=True,
        tickfont=dict(size=10.5, color="#1d4ed8"),
    )
    fig.update_xaxes(tickfont=dict(size=11.5, color="#1e293b"))

    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=15, color="#0f172a")),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
        ),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        height=height,
        margin=dict(l=55, r=55, t=72, b=50),
    )
    return fig


# ==============================================================================
# VISÃO EXECUTIVA (TOPO DO DASHBOARD)
# ==============================================================================
def _render_executive_summary(df: pd.DataFrame):
    summary = compute_config_summary(df, sort_by_score=True)
    if summary.empty:
        return

    best_overall = summary.iloc[0]

    # Melhor em híbridas
    df_hib = df[df["tipo_pergunta"] == "híbrida"]
    sum_hib = compute_config_summary(df_hib, sort_by_score=True)
    best_hib = sum_hib.iloc[0] if not sum_hib.empty else best_overall

    # Menor taxa de incorretas
    best_low_err = summary.sort_values(by=["incorreta_pct", "score_mean"], ascending=[True, False]).iloc[0]

    # Melhor custo-benefício (menor custo mantendo score >= 0.70)
    cand_roi = summary[summary["score_mean"] >= 0.70]
    if cand_roi.empty:
        cand_roi = summary
    best_roi = cand_roi.sort_values(by=["custo_200", "score_mean"], ascending=[True, False]).iloc[0]

    c1, c2, c3, c4 = st.columns(4, gap="medium")
    with c1:
        st.markdown(_clean_html(f"""
        <div class="kpi-card">
            <div class="kpi-label">Melhor RAG Geral (Score)</div>
            <div class="kpi-value">{best_overall['score_mean']:.3f}</div>
            <div class="kpi-sub"><strong>{best_overall['config_label']}</strong><br>{best_overall['correta_pct']:.1f}% corretas · ±{best_overall['score_std']:.2f} DP</div>
        </div>
        """), unsafe_allow_html=True)

    with c2:
        st.markdown(_clean_html(f"""
        <div class="kpi-card">
            <div class="kpi-label">Melhor em Híbridas</div>
            <div class="kpi-value">{best_hib['score_mean']:.3f}</div>
            <div class="kpi-sub"><strong>{best_hib['config_label']}</strong><br>{best_hib['positiva_pct']:.1f}% Parcial + Correta</div>
        </div>
        """), unsafe_allow_html=True)

    with c3:
        st.markdown(_clean_html(f"""
        <div class="kpi-card">
            <div class="kpi-label">Menor Taxa de Incorretas</div>
            <div class="kpi-value">{best_low_err['incorreta_pct']:.1f}%</div>
            <div class="kpi-sub"><strong>{best_low_err['config_label']}</strong><br>{best_low_err['positiva_pct']:.1f}% Parcial + Correta</div>
        </div>
        """), unsafe_allow_html=True)

    with c4:
        st.markdown(_clean_html(f"""
        <div class="kpi-card">
            <div class="kpi-label">Melhor Custo-Benefício</div>
            <div class="kpi-value">${best_roi['custo_200']:.4f}</div>
            <div class="kpi-sub"><strong>{best_roi['config_label']}</strong><br>Score {best_roi['score_mean']:.3f} (200 perguntas)</div>
        </div>
        """), unsafe_allow_html=True)


# ==============================================================================
# SEÇÕES DO DASHBOARD
# ==============================================================================
def _render_section_acuracia(df: pd.DataFrame):
    st.markdown('<div class="section-header">Acurácia</div>', unsafe_allow_html=True)

    col_intro_1, col_intro_2 = st.columns(2, gap="medium")

    with col_intro_1:
        st.markdown(_clean_html("""
        <div class="intro-card">
            <h3>📚 Comparação entre RAG Tradicional e RAG Fichamentos</h3>
            <p>
                Para avaliar a acurácia dos métodos, elaborou-se <strong>100 questões</strong> para os <strong>124 cursos de graduação</strong>
                (bacharelado e licenciatura) existentes atualmente na <strong>Universidade Federal da Bahia</strong>.
                As questões foram criadas a partir dos documentos encontrados nos websites dos colegiados e departamento de cada curso.
            </p>
            <p>
                Após isso, foram selecionadas <strong>200 perguntas</strong> via sorteio aleatório. De 200 questionamentos,
                <strong>100 deles</strong> possuíam respostas em PDFs únicos, enquanto na outra metade o gabarito combinou
                <strong>dois ou mais documentos</strong>.
            </p>
            <p style="margin-bottom: 0;">
                Em seguida, foi utilizado o modelo <strong>TypeSafe Jev 1.14</strong> para classificar a resposta gerada pelos RAGs
                (<strong>gemini 3.5 flash lite</strong>) em
                <span style="color:#ef4444;font-weight:700;">"Incorreta"</span>,
                <span style="color:#fca5a5;font-weight:700;">"Parcialmente incorreta"</span>,
                <span style="color:#86efac;font-weight:700;">"Parcialmente correta"</span> e
                <span style="color:#10b981;font-weight:700;">"Correta"</span>.
            </p>
        </div>
        """), unsafe_allow_html=True)

    with col_intro_2:
        st.markdown(_clean_html("""
        <div class="callout-card">
            <h3>🧪 Foram realizados quatro experimentos:</h3>
            <ul>
                <li><strong>RAG tradicional com chunking simples</strong> — FileSearchStore da API Gemini (<code>k = 1, 5, 10</code>);</li>
                <li><strong>RAG com pré-LLM para definir os chunkings (fatias de PDFs)</strong> e <strong>embeddings sobre os fichamentos</strong> dessas fatias (<code>k = 1, 5, 10</code>).</li>
                <li><strong>RAG com pré-LLM para definir os chunkings (fatias de PDFs)</strong>, mas com o modelo <strong>TypeSafe JEV 1.14</strong> determinando as fatias a serem inseridas na janela de contexto, sob uma limitação das <em>top-k</em> (<code>k = 1, 5 ou 10</code>) fatias mais relevantes.</li>
                <li><strong>RAG com o mesmo método anterior</strong>, diferenciando-se quanto à liberdade do modelo JEV em determinar as <em>k</em> fatias mais relevantes que devem entrar na janela de contexto.</li>
            </ul>
        </div>
        """), unsafe_allow_html=True)

    # 1. Qual o método que mais acerta?
    st.markdown(
        '<div class="subsection-header">Qual o método que mais acerta?</div>',
        unsafe_allow_html=True,
    )
    fig_div = build_diverging_accuracy_bar(
        df, title="Distribuição do acerto (%) por método de RAG empregado"
    )
    st.plotly_chart(fig_div, width="stretch")

    # 2. Qual o melhor k?
    st.markdown(
        '<div class="subsection-header">Qual o melhor k?</div>',
        unsafe_allow_html=True,
    )
    fig_k = build_k_sensitivity_line(
        df, title="Percentual de respostas classificadas como incorretas por número de chunkings"
    )
    st.plotly_chart(fig_k, width="stretch")

    # 3. O desempenho é afetado por perguntas multi-documento?
    st.markdown(
        '<div class="subsection-header">O desempenho é afetado por perguntas multi-documento?</div>',
        unsafe_allow_html=True,
    )

    col_acc_h, col_acc_u = st.columns(2, gap="medium")

    for col_target, tipo_key, titulo_col in [
        (col_acc_h, "híbrida", "Perguntas Híbridas / Multi-Documento"),
        (col_acc_u, "única", "Perguntas Únicas / 1 Documento"),
    ]:
        with col_target:
            df_t = df[df["tipo_pergunta"] == tipo_key]
            sum_t = compute_config_summary(df_t, sort_by_score=False)
            n_q = int(df_t["Pergunta"].nunique()) if not df_t.empty else 0

            st.markdown(
                f'<div class="column-question-title">{titulo_col} (n={n_q} perguntas)</div>',
                unsafe_allow_html=True,
            )

            if not sum_t.empty:
                best_score_row = sum_t.sort_values(by=["score_mean", "positiva_pct"], ascending=False).iloc[0]
                best_sum_row = sum_t.sort_values(by=["positiva_pct", "correta_pct"], ascending=False).iloc[0]

                m1, m2 = st.columns(2, gap="small")
                with m1:
                    st.markdown(_clean_html(f"""
                    <div class="mini-stat-card">
                        <div class="mini-stat-label">Melhor Score Esperado</div>
                        <div class="mini-stat-val">{best_score_row['score_mean']:.3f}</div>
                        <div class="mini-stat-sub">{best_score_row['config_label']}</div>
                    </div>
                    """), unsafe_allow_html=True)
                with m2:
                    st.markdown(_clean_html(f"""
                    <div class="mini-stat-card">
                        <div class="mini-stat-label">Melhor Soma (Parcial + Correta)</div>
                        <div class="mini-stat-val">{best_sum_row['positiva_pct']:.1f}%</div>
                        <div class="mini-stat-sub">{best_sum_row['config_label']}</div>
                    </div>
                    """), unsafe_allow_html=True)

            fig_sum = build_positive_sum_bar(
                df_t,
                title="Percentual de respostas Parcialmente corretas + Corretas (%)",
                height=440,
            )
            st.plotly_chart(fig_sum, width="stretch")


def _render_section_qualidade(df: pd.DataFrame):
    st.markdown('<div class="section-header">Qualidade da resposta</div>', unsafe_allow_html=True)

    col_q1, col_q2 = st.columns(2, gap="medium")

    with col_q1:
        st.markdown(_clean_html("""
        <div class="callout-card">
            <h4>📐 Fórmula do Score Esperado</h4>
            <p style="font-size: 0.91rem; color: #334155; line-height: 1.55; margin-bottom: 0.5rem;">
                O Score é calculado a partir do <strong>exponencial das log probabilidades</strong> emitidas pelo modelo
                <strong>TypeSafe JEV 1.14</strong> para cada categoria de classificação:
            </p>
            <div class="formula-box">
                Score Esperado = Peso<sub>inc</sub> × 0 + Peso<sub>pinc</sub> × 0,15 + Peso<sub>pcor</sub> × 0,55 + Peso<sub>cor</sub> × 1
            </div>
            <p style="font-size: 0.87rem; color: #475569; line-height: 1.55; margin-bottom: 0;">
                Onde cada peso corresponde a <strong>exp(logprob<sub>categoria</sub>)</strong>:
                <em>Incorreto (0)</em>, <em>Parcialmente incorreto (0,15)</em>,
                <em>Parcialmente correto (0,55)</em> e <em>Correto (1)</em>.
            </p>
        </div>
        """), unsafe_allow_html=True)

    with col_q2:
        st.markdown(_clean_html("""
        <div class="intro-card">
            <h3>💡 Interpretação do Score Esperado</h3>
            <p style="font-size: 0.9rem; margin-bottom: 0.7rem;">
                O <strong>Score Esperado</strong> captura a <strong>qualidade média das respostas</strong> dos métodos ao
                <strong>penalizar fortemente os erros</strong>:
            </p>
            <div class="interactive-weight-row" title="Peso 0,00: erro completo zera a pontuação esperada da categoria.">
                <span style="min-width: 162px; font-weight: 700; color: #ef4444; font-size: 0.86rem;">Incorreto (× 0,00)</span>
                <div style="flex:1; background:#fee2e2; height:11px; border-radius:999px; overflow:hidden;">
                    <div style="width:2%; background:#ef4444; height:100%;"></div>
                </div>
                <span style="font-size:0.82rem; color:#64748b; min-width:130px; text-align:right;">Penalização total (100%)</span>
            </div>
            <div class="interactive-weight-row" title="Peso 0,15: penalização severa de 85% para respostas predominantemente incorretas.">
                <span style="min-width: 162px; font-weight: 700; color: #fca5a5; font-size: 0.86rem;">Parc. Incorreto (× 0,15)</span>
                <div style="flex:1; background:#fee2e2; height:11px; border-radius:999px; overflow:hidden;">
                    <div style="width:15%; background:#fca5a5; height:100%;"></div>
                </div>
                <span style="font-size:0.82rem; color:#64748b; min-width:130px; text-align:right;">Penalização de 85%</span>
            </div>
            <div class="interactive-weight-row" title="Peso 0,55: penalização moderada de 45% quando faltam elementos complementares.">
                <span style="min-width: 162px; font-weight: 700; color: #86efac; font-size: 0.86rem;">Parc. Correto (× 0,55)</span>
                <div style="flex:1; background:#dcfce7; height:11px; border-radius:999px; overflow:hidden;">
                    <div style="width:55%; background:#86efac; height:100%;"></div>
                </div>
                <span style="font-size:0.82rem; color:#64748b; min-width:130px; text-align:right;">Penalização de 45%</span>
            </div>
            <div class="interactive-weight-row" style="margin-bottom: 0;" title="Peso 1,00: pontuação máxima para resposta integralmente correta.">
                <span style="min-width: 162px; font-weight: 700; color: #10b981; font-size: 0.86rem;">Correto (× 1,00)</span>
                <div style="flex:1; background:#d1fae5; height:11px; border-radius:999px; overflow:hidden;">
                    <div style="width:100%; background:#10b981; height:100%;"></div>
                </div>
                <span style="font-size:0.82rem; color:#64748b; min-width:130px; text-align:right;">Pontuação integral</span>
            </div>
        </div>
        """), unsafe_allow_html=True)

    st.markdown(
        '<div class="subsection-header">Qual a qualidade média das respostas?</div>',
        unsafe_allow_html=True,
    )
    fig_box_geral = build_general_score_boxplot(
        df,
        title="Distribuição do Score Esperado por método de RAG",
        sort_by_mean=True,
        compact_badge=False,
    )
    st.plotly_chart(fig_box_geral, width="stretch")

    st.markdown(
        '<div class="subsection-header">A qualidade média é afetada por perguntas multi-documento?</div>',
        unsafe_allow_html=True,
    )
    col_qh, col_qu = st.columns(2, gap="medium")
    for col_target, tipo_key, titulo_col in [
        (col_qh, "híbrida", "Perguntas Híbridas / Multi-Documento"),
        (col_qu, "única", "Perguntas Únicas / 1 Documento"),
    ]:
        with col_target:
            df_t = df[df["tipo_pergunta"] == tipo_key]
            n_q = int(df_t["Pergunta"].nunique()) if not df_t.empty else 0
            st.markdown(
                f'<div class="column-question-title">{titulo_col} (n={n_q} perguntas)</div>',
                unsafe_allow_html=True,
            )
            fig_box_t = build_general_score_boxplot(
                df_t,
                title="Distribuição do Score Esperado por método de RAG",
                sort_by_mean=True,
                compact_badge=True,
                height=460,
            )
            st.plotly_chart(fig_box_t, width="stretch")

    st.markdown(
        '<div class="subsection-header">Qualidade vs Custo Operacional</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Considera o custo operacional do RAG nas 200 perguntas, "
        "excluindo o custo experimental do LLM julgador."
    )
    fig_cost = build_score_vs_cost_scatter(
        df, title="Cruzamento entre Score Esperado Médio e Custo Total em USD"
    )
    st.plotly_chart(fig_cost, width="stretch")


def _render_section_documentos(df: pd.DataFrame):
    df_livre = df[df["metodo_rag"] == "rag_fichamento_jev_livre"].copy()
    if df_livre.empty:
        st.info("Ainda não há registros para o método `rag_fichamento_jev_livre` na base carregada.")
        return

    df_uni = df_livre[df_livre["tipo_pergunta"] == "única"]
    df_hib = df_livre[df_livre["tipo_pergunta"] == "híbrida"]

    def _stats(d: pd.DataFrame) -> tuple[float, float, float, int, int]:
        q = pd.to_numeric(d["quantidade_documentos"], errors="coerce").dropna()
        if q.empty:
            return 0.0, 0.0, 0.0, 0, 0
        return (
            float(q.mean()),
            float(q.median()),
            float(q.std(ddof=1)) if len(q) > 1 else 0.0,
            int(q.min()),
            int(q.max()),
        )

    g_mean, g_med, g_std, g_min, g_max = _stats(df_livre)
    u_mean, u_med, u_std, u_min, u_max = _stats(df_uni)
    h_mean, h_med, h_std, h_min, h_max = _stats(df_hib)

    st.markdown(
        '<div class="subsection-header" style="margin-top:0.2rem;">Quantidade de Fatias Utilizadas pelo JEV Livre (Seleção sob Prob &gt; 0,50)</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4, gap="medium")
    with c1:
        st.markdown(_clean_html(f"""
        <div class="kpi-card">
            <div class="kpi-label">Média de Fatias (Geral)</div>
            <div class="kpi-value">{g_mean:.2f} fatias</div>
            <div class="kpi-split-grid">
                <div>
                    <div class="kpi-split-label">Únicas</div>
                    <div class="kpi-split-val">{u_mean:.2f} fatias</div>
                </div>
                <div>
                    <div class="kpi-split-label">Híbridas</div>
                    <div class="kpi-split-val">{h_mean:.2f} fatias</div>
                </div>
            </div>
        </div>
        """), unsafe_allow_html=True)

    with c2:
        st.markdown(_clean_html(f"""
        <div class="kpi-card">
            <div class="kpi-label">Mediana de Fatias (Geral)</div>
            <div class="kpi-value">{g_med:.1f} fatia</div>
            <div class="kpi-split-grid">
                <div>
                    <div class="kpi-split-label">Únicas</div>
                    <div class="kpi-split-val">{u_med:.1f} fatia</div>
                </div>
                <div>
                    <div class="kpi-split-label">Híbridas</div>
                    <div class="kpi-split-val">{h_med:.1f} fatia</div>
                </div>
            </div>
        </div>
        """), unsafe_allow_html=True)

    with c3:
        st.markdown(_clean_html(f"""
        <div class="kpi-card">
            <div class="kpi-label">Desvio Padrão (Geral)</div>
            <div class="kpi-value">± {g_std:.2f}</div>
            <div class="kpi-split-grid">
                <div>
                    <div class="kpi-split-label">Únicas</div>
                    <div class="kpi-split-val">± {u_std:.2f}</div>
                </div>
                <div>
                    <div class="kpi-split-label">Híbridas</div>
                    <div class="kpi-split-val">± {h_std:.2f}</div>
                </div>
            </div>
        </div>
        """), unsafe_allow_html=True)

    with c4:
        st.markdown(_clean_html(f"""
        <div class="kpi-card">
            <div class="kpi-label">Amplitude (Geral: Mín – Máx)</div>
            <div class="kpi-value">{g_min} a {g_max}</div>
            <div class="kpi-split-grid">
                <div>
                    <div class="kpi-split-label">Únicas</div>
                    <div class="kpi-split-val">{u_min} a {u_max}</div>
                </div>
                <div>
                    <div class="kpi-split-label">Híbridas</div>
                    <div class="kpi-split-val">{h_min} a {h_max}</div>
                </div>
            </div>
        </div>
        """), unsafe_allow_html=True)

    # Figura da distribuição proporcional logo abaixo dos indicadores (sem os cards inferiores)
    dist_faixas = (
        df_livre["faixa_documentos"]
        .value_counts()
        .reindex(ORDEM_FAIXAS_DOCS, fill_value=0)
    )
    total_livre = max(1, len(df_livre))
    pcts = {f: dist_faixas[f] / total_livre * 100.0 for f in ORDEM_FAIXAS_DOCS}

    st.markdown(
        '<div class="subsection-header">Frequência (%) de documentos usados como contexto</div>',
        unsafe_allow_html=True,
    )
    freq_bar_html = _clean_html(f"""
    <div class="intro-card" style="padding: 1.05rem 1.35rem;">
        <div style="display:flex; height:28px; border-radius:999px; overflow:hidden; background:#f1f5f9; border:1px solid #e2e8f0; margin-bottom:0.65rem;">
            <div title="1 fatia: {int(dist_faixas['1'])} ({pcts['1']:.1f}%)" style="width:{max(pcts['1'], 0.5):.2f}%; background:#bfdbfe; display:flex; align-items:center; justify-content:center; font-size:0.78rem; font-weight:700; color:#1e3a8a;">
                {f"{pcts['1']:.1f}%" if pcts['1'] >= 7 else ""}
            </div>
            <div title="2 fatias: {int(dist_faixas['2'])} ({pcts['2']:.1f}%)" style="width:{max(pcts['2'], 0.5):.2f}%; background:#60a5fa; display:flex; align-items:center; justify-content:center; font-size:0.78rem; font-weight:700; color:#ffffff;">
                {f"{pcts['2']:.1f}%" if pcts['2'] >= 6 else ""}
            </div>
            <div title="3 fatias: {int(dist_faixas['3'])} ({pcts['3']:.1f}%)" style="width:{max(pcts['3'], 0.5):.2f}%; background:#2563eb; display:flex; align-items:center; justify-content:center; font-size:0.78rem; font-weight:700; color:#ffffff;">
                {f"{pcts['3']:.1f}%" if pcts['3'] >= 4 else ""}
            </div>
            <div title="4+ fatias: {int(dist_faixas['4+'])} ({pcts['4+']:.1f}%)" style="width:{max(pcts['4+'], 0.5):.2f}%; background:#1e3a8a; display:flex; align-items:center; justify-content:center; font-size:0.78rem; font-weight:700; color:#ffffff;">
                {f"{pcts['4+']:.1f}%" if pcts['4+'] >= 4 else ""}
            </div>
        </div>
        <div style="display:flex; flex-wrap:wrap; gap:1.35rem; font-size:0.82rem; color:#475569;">
            <span><span style="display:inline-block;width:10px;height:10px;border-radius:3px;background:#bfdbfe;margin-right:5px;"></span><strong>1 fatia:</strong> {pcts['1']:.1f}% ({int(dist_faixas['1'])})</span>
            <span><span style="display:inline-block;width:10px;height:10px;border-radius:3px;background:#60a5fa;margin-right:5px;"></span><strong>2 fatias:</strong> {pcts['2']:.1f}% ({int(dist_faixas['2'])})</span>
            <span><span style="display:inline-block;width:10px;height:10px;border-radius:3px;background:#2563eb;margin-right:5px;"></span><strong>3 fatias:</strong> {pcts['3']:.1f}% ({int(dist_faixas['3'])})</span>
            <span><span style="display:inline-block;width:10px;height:10px;border-radius:3px;background:#1e3a8a;margin-right:5px;"></span><strong>4+ fatias:</strong> {pcts['4+']:.1f}% ({int(dist_faixas['4+'])})</span>
        </div>
    </div>
    """)
    st.markdown(freq_bar_html, unsafe_allow_html=True)

    # Linha 1: Frequência + Score Médio Geral
    st.markdown(
        '<div class="subsection-header">A quantidade de documentos está relacionada com a qualidade da resposta?</div>',
        unsafe_allow_html=True,
    )
    fig_doc_geral = build_docs_freq_and_score_chart(
        df_livre,
        title="Quantidade de consultas e Score Esperado médio por faixa de fatias",
        height=420,
    )
    st.plotly_chart(fig_doc_geral, width="stretch")

    # Linha 2: Duas colunas (Híbrida e Única)
    st.markdown(
        '<div class="subsection-header">Há diferenças na relação qualidade-quantidade entre perguntas híbridas e únicas?</div>',
        unsafe_allow_html=True,
    )
    col_d1, col_d2 = st.columns(2, gap="medium")

    with col_d1:
        st.markdown(
            f'<div class="column-question-title">Perguntas Híbridas (n={len(df_hib)})</div>',
            unsafe_allow_html=True,
        )
        fig_doc_hib = build_docs_freq_and_score_chart(
            df_hib,
            title="Quantidade de consultas e Score Esperado médio por faixa",
            height=390,
        )
        st.plotly_chart(fig_doc_hib, width="stretch")

    with col_d2:
        st.markdown(
            f'<div class="column-question-title">Perguntas Únicas (n={len(df_uni)})</div>',
            unsafe_allow_html=True,
        )
        fig_doc_uni = build_docs_freq_and_score_chart(
            df_uni,
            title="Quantidade de consultas e Score Esperado médio por faixa",
            height=390,
        )
        st.plotly_chart(fig_doc_uni, width="stretch")


def render_experiment_dashboard(embedded: bool = True):
    """Renderiza o dashboard completo de avaliação dos métodos de RAG (standalone ou integrado ao app.py)."""
    st.markdown(DASHBOARD_CSS, unsafe_allow_html=True)

    df = load_results_data(str(RESULTADOS_PATH))

    with st.sidebar:
        if not embedded:
            st.markdown("### 🎓 Sinform AI — UFBA")
            st.caption("Avaliação Experimental de Arquiteturas de RAG e Seleção Contextual via JEV 1.14")
            st.divider()

        if st.button("🔄 Atualizar Dados da Planilha", width="stretch", key="btn_refresh_exp"):
            st.cache_data.clear()
            st.rerun()

        if not df.empty:
            n_perguntas_unicas = df["Pergunta"].nunique()
            n_unicas_tipo = df[df["tipo_pergunta"] == "única"]["Pergunta"].nunique()
            n_hibridas_tipo = df[df["tipo_pergunta"] == "híbrida"]["Pergunta"].nunique()
            st.markdown("#### 📌 Resumo da Base Carregada")
            st.metric("Total de Avaliações (Linhas)", f"{len(df):,}")
            st.metric("Perguntas Avaliadas", f"{n_perguntas_unicas} (Únicas: {n_unicas_tipo} | Híbridas: {n_hibridas_tipo})")

    st.markdown(_clean_html("""
    <div class="page-header">
        <h1>📊 Comparação entre RAG Tradicional e RAG Fichamentos</h1>
        <p>Avaliação comparativa através de 200 perguntas elaboradas com documentos de cursos ativos da UFBA, utilizando o modelo de classificação TypeSafe Jev 1.14 como LLM julgador</p>
    </div>
    """), unsafe_allow_html=True)

    if df.empty:
        st.warning(
            f"Nenhum resultado encontrado em `{RESULTADOS_PATH}`. "
            "Assim que o experimento iniciar a gravação das respostas, os gráficos serão populados automaticamente."
        )
        return

    _render_executive_summary(df)

    st.markdown("<div style='height: 0.45rem;'></div>", unsafe_allow_html=True)

    tab_acc, tab_qual, tab_docs = st.tabs([
        "Acurácia",
        "Qualidade da resposta",
        "A influência dos documentos",
    ])

    with tab_acc:
        _render_section_acuracia(df)

    with tab_qual:
        _render_section_qualidade(df)

    with tab_docs:
        _render_section_documentos(df)


if __name__ == "__main__":
    st.set_page_config(
        page_title="Sinform AI | Benchmark de Métodos de RAG (UFBA)",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    render_experiment_dashboard(embedded=False)
