import os
import json
from typing import Any
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# ==============================================================================
# CSS ESTILIZADO (SINFORM AI - UFBA)
# ==============================================================================
DASHBOARD_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .hero-banner {
        background: linear-gradient(135deg, #0b192c 0%, #1e3e62 55%, #004b87 100%);
        color: #ffffff;
        padding: 1.9rem 2.3rem;
        border-radius: 16px;
        margin-bottom: 1.4rem;
        box-shadow: 0 10px 28px rgba(11, 25, 44, 0.18);
        border-left: 6px solid #f59e0b;
    }
    .hero-banner h1 {
        margin: 0;
        font-size: 1.85rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: #ffffff;
    }
    .hero-banner p {
        margin: 0.45rem 0 0 0;
        font-size: 0.98rem;
        color: #e2e8f0;
        line-height: 1.55;
    }
    .hero-badge {
        display: inline-block;
        background: rgba(245, 158, 11, 0.22);
        border: 1px solid #f59e0b;
        color: #fde68a;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 0.22rem 0.7rem;
        border-radius: 999px;
        text-transform: uppercase;
        margin-bottom: 0.55rem;
        letter-spacing: 0.06em;
    }

    .intro-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-top: 4px solid #1e3e62;
        border-radius: 14px;
        padding: 1.45rem 1.6rem;
        height: 100%;
        box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05);
        color: #1e293b;
        font-size: 0.93rem;
        line-height: 1.62;
    }
    .intro-card h3 {
        margin-top: 0;
        margin-bottom: 0.75rem;
        font-size: 1.12rem;
        font-weight: 700;
        color: #0f172a;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .intro-card p {
        margin-bottom: 0.75rem;
        text-align: justify;
    }
    .intro-card ul {
        margin: 0.4rem 0 0 0;
        padding-left: 1.2rem;
    }
    .intro-card li {
        margin-bottom: 0.55rem;
        text-align: justify;
    }

    .section-header {
        margin: 1.4rem 0 0.9rem 0;
        padding-bottom: 0.45rem;
        border-bottom: 2px solid #e2e8f0;
        color: #0f172a;
        font-weight: 800;
        font-size: 1.32rem;
        letter-spacing: -0.01em;
    }

    .formula-card {
        background: linear-gradient(145deg, #0f172a 0%, #1e293b 100%);
        color: #f8fafc;
        border-radius: 14px;
        padding: 1.5rem 1.65rem;
        border: 1px solid #334155;
        box-shadow: 0 8px 22px rgba(15, 23, 42, 0.14);
        height: 100%;
    }
    .formula-card h4 {
        margin: 0 0 0.65rem 0;
        color: #38bdf8;
        font-size: 1.05rem;
        font-weight: 700;
    }
    .formula-box {
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(148, 163, 184, 0.25);
        border-radius: 10px;
        padding: 0.95rem 1rem;
        font-family: 'Cambria Math', 'Inter', monospace;
        font-size: 0.96rem;
        text-align: center;
        color: #fef08a;
        margin: 0.75rem 0;
        font-weight: 600;
    }

    .interactive-weight-row {
        display: flex;
        align-items: center;
        gap: 0.65rem;
        padding: 0.45rem 0.65rem;
        border-radius: 8px;
        transition: transform 0.15s ease, background 0.15s ease;
        margin-bottom: 0.35rem;
        cursor: default;
    }
    .interactive-weight-row:hover {
        transform: translateX(4px);
        background: #f1f5f9;
    }

    .metric-mini-card {
        background: rgba(255,255,255,0.06);
        padding: 0.95rem 1.1rem;
        border-radius: 12px;
        transition: transform 0.16s ease, background 0.16s ease;
    }
    .metric-mini-card:hover {
        transform: translateY(-2px);
        background: rgba(255,255,255,0.11);
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
    "Correta": "#10b981",
    "Parcialmente correta": "#86efac",
    "Parcialmente incorreta": "#fca5a5",
    "Incorreta": "#ef4444",
}

TEXT_CORES_DECISAO = {
    "Correta": "#ffffff",
    "Parcialmente correta": "#064e3b",
    "Parcialmente incorreta": "#7f1d1d",
    "Incorreta": "#ffffff",
}

ORDEM_DECISAO = [
    "Correta",
    "Parcialmente correta",
    "Parcialmente incorreta",
    "Incorreta",
]

ORDEM_FAIXAS_DOCS = ["1", "2", "3", "4+"]
LIGHT_BLUE_BOX = "#38bdf8"
LIGHT_BLUE_BORDER = "#0284c7"


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

    # Garantir coluna Classificação ("única" vs "híbrida")
    if "Classificação" in df.columns:
        df["tipo_pergunta"] = df.apply(
            lambda r: normalize_classificacao(r.get("Classificação"), r.get("Documento")), axis=1
        )
    elif "tipo_pergunta" in df.columns:
        df["tipo_pergunta"] = df.apply(
            lambda r: normalize_classificacao(r.get("tipo_pergunta"), r.get("Documento")), axis=1
        )
    else:
        # Se a base carregada ainda não tiver a coluna Classificação, tenta cruzar pelo texto da Pergunta com Conjunto de Testes 200.xlsx
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
                normalize_classificacao("", r.get("Documento"))
            ),
            axis=1
        )

    # Cálculo das probabilidades lineares P_c = exp(logprob) (ou uso direto se já estiverem em [0, 1])
    c_inc = "logprob_julgador_Incorreta"
    c_pinc = "logprob_julgador_Parcialmente_incorreta"
    c_pcor = "logprob_julgador_Parcialmente_correta"
    c_cor = "logprob_julgador_Correta"

    for col in [c_inc, c_pinc, c_pcor, c_cor]:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    raw_mat = df[[c_inc, c_pinc, c_pcor, c_cor]].to_numpy(dtype=float)
    # Se houver valores negativos, aplica exp(logprob); caso contrário já são probabilidades lineares
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

    df["faixa_documentos"] = df["quantidade_documentos"].apply(categorize_doc_count)
    return df


# ==============================================================================
# FUNÇÕES DE PLOTAGEM PLOTLY
# ==============================================================================
def build_vertical_stacked_bar(df_sub: pd.DataFrame, title: str, height: int = 470) -> go.Figure:
    """
    Gráfico de barras empilhadas VERTICAIS (proporção % de cada categoria por método).
    """
    if df_sub.empty:
        fig = go.Figure()
        fig.update_layout(
            title=title,
            height=height,
            annotations=[dict(text="Sem dados para este recorte", showarrow=False, font=dict(size=14))]
        )
        return fig

    present_configs = [c for c in ORDEM_CONFIGS if c in df_sub["config_label"].unique()]
    if not present_configs:
        present_configs = sorted(df_sub["config_label"].unique().tolist())

    ct = (
        df_sub.groupby(["config_label", "decisao_julgador"])
        .size()
        .unstack(fill_value=0)
        .reindex(index=present_configs, fill_value=0)
    )
    for cat in ORDEM_DECISAO:
        if cat not in ct.columns:
            ct[cat] = 0
    ct = ct[ORDEM_DECISAO]
    totals = ct.sum(axis=1).replace(0, 1)
    pct = ct.div(totals, axis=0) * 100.0

    fig = go.Figure()
    for cat in ORDEM_DECISAO:
        vals = pct[cat]
        counts = ct[cat]
        fig.add_trace(
            go.Bar(
                name=cat,
                x=present_configs,
                y=vals,
                marker_color=CORES_DECISAO[cat],
                text=[f"{v:.1f}%" if v >= 6.0 else "" for v in vals],
                textposition="inside",
                insidetextanchor="middle",
                textangle=0,
                textfont=dict(color=TEXT_CORES_DECISAO[cat], size=10.5, family="Inter"),
                customdata=np.stack([counts, totals], axis=-1),
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    f"Categoria: <b>{cat}</b><br>"
                    "Proporção: <b>%{y:.1f}%</b> (%{customdata[0]} de %{customdata[1]})"
                    "<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=17, color="#0f172a")),
        barmode="stack",
        xaxis=dict(
            title="Método e Configuração de RAG",
            tickangle=-28,
            tickfont=dict(size=11, color="#1e293b"),
            categoryorder="array",
            categoryarray=present_configs,
        ),
        yaxis=dict(
            title="Proporção de Respostas (%)",
            range=[0, 100],
            ticksuffix="%",
            gridcolor="#e2e8f0",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            title=dict(text="Decisão JEV 1.14: "),
        ),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        margin=dict(l=50, r=25, t=75, b=110),
        height=height,
    )
    return fig


def build_general_score_boxplot(df_sub: pd.DataFrame, title: str) -> go.Figure:
    """
    Boxplot geral do Score Esperado (10 caixas em um único gráfico, escala 0 a 1).
    """
    present_configs = [c for c in ORDEM_CONFIGS if c in df_sub["config_label"].unique()]
    if not present_configs:
        present_configs = sorted(df_sub["config_label"].unique().tolist())

    fig = go.Figure()
    for cfg in present_configs:
        d_cfg = df_sub[df_sub["config_label"] == cfg]["score_esperado"]
        fig.add_trace(
            go.Box(
                y=d_cfg,
                name=cfg,
                boxmean=True,
                marker_color=LIGHT_BLUE_BOX,
                line=dict(color=LIGHT_BLUE_BORDER, width=1.8),
                fillcolor=LIGHT_BLUE_BOX,
                opacity=0.80,
                boxpoints="outliers",
                hovertemplate=(
                    f"<b>{cfg}</b><br>"
                    "Score Esperado: <b>%{y:.3f}</b><extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=17, color="#0f172a")),
        xaxis=dict(
            title="Método e Configuração de RAG",
            tickangle=-25,
            tickfont=dict(size=11, color="#1e293b"),
        ),
        yaxis=dict(
            title="Score Esperado (0 a 1)",
            range=[-0.03, 1.05],
            gridcolor="#e2e8f0",
            zeroline=False,
        ),
        showlegend=False,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        margin=dict(l=55, r=25, t=65, b=110),
        height=490,
    )
    return fig


def _short_subplot_title(cfg: str) -> str:
    if " (k=" in cfg:
        base, rest = cfg.split(" (k=", 1)
        return f"<b>{base}</b><br>(k={rest}"
    return f"<b>{cfg}</b>"


def build_grid_2x5_boxplots(df_sub: pd.DataFrame, title: str) -> go.Figure:
    """
    Grid 2x5 de boxplots detalhando Score Esperado por 'híbrida' vs 'única'
    para cada uma das 10 configurações de método (2 caixas por subplot).
    """
    configs_grid = ORDEM_CONFIGS.copy()
    fig = make_subplots(
        rows=2,
        cols=5,
        subplot_titles=[_short_subplot_title(c) for c in configs_grid],
        shared_yaxes=True,
        horizontal_spacing=0.04,
        vertical_spacing=0.18,
    )

    color_map = {"única": LIGHT_BLUE_BOX, "híbrida": "#f59e0b"}
    label_map = {"única": "Única (1 PDF)", "híbrida": "Híbrida (>1 PDF)"}

    for idx, cfg in enumerate(configs_grid):
        r = (idx // 5) + 1
        c = (idx % 5) + 1
        d_cfg = df_sub[df_sub["config_label"] == cfg]

        for t_key in ["única", "híbrida"]:
            vals = d_cfg[d_cfg["tipo_pergunta"] == t_key]["score_esperado"]
            fig.add_trace(
                go.Box(
                    y=vals,
                    x=[label_map[t_key]] * len(vals) if len(vals) > 0 else [label_map[t_key]],
                    name=label_map[t_key],
                    legendgroup=t_key,
                    showlegend=(idx == 0),
                    boxmean=True,
                    marker_color=color_map[t_key],
                    line=dict(color=color_map[t_key], width=1.8),
                    boxpoints="outliers",
                    hovertemplate=(
                        f"<b>{cfg}</b><br>"
                        f"Tipo: <b>{label_map[t_key]}</b><br>"
                        "Score Esperado: <b>%{y:.3f}</b><extra></extra>"
                    ),
                ),
                row=r,
                col=c,
            )

    for annotation in fig["layout"]["annotations"]:
        annotation["font"] = dict(size=11.5, color="#0f172a", family="Inter")

    fig.update_yaxes(range=[-0.03, 1.05], gridcolor="#e2e8f0", title_text="Score Esperado", col=1)
    fig.update_yaxes(range=[-0.03, 1.05], gridcolor="#e2e8f0")
    fig.update_xaxes(tickfont=dict(size=10, color="#334155"))

    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=17, color="#0f172a")),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,
            xanchor="right",
            x=1.0,
            title=dict(text="Classificação da Pergunta: "),
        ),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        height=640,
        margin=dict(l=55, r=25, t=90, b=50),
    )
    return fig


def build_docs_vs_score_boxplot(df_jev_livre: pd.DataFrame, title: str, color_hex: str = LIGHT_BLUE_BOX) -> go.Figure:
    """
    Boxplot cruzando Score Esperado pela quantidade categorizada de documentos ('1', '2', '3', '4+').
    """
    fig = go.Figure()

    for faixa in ORDEM_FAIXAS_DOCS:
        d_f = df_jev_livre[df_jev_livre["faixa_documentos"] == faixa]["score_esperado"]
        n_obs = len(d_f)
        doc_unit = "doc" if faixa == "1" else "docs"
        fig.add_trace(
            go.Box(
                y=d_f,
                name=f"{faixa} {doc_unit} (n={n_obs})",
                boxmean=True,
                marker_color=color_hex,
                line=dict(color=LIGHT_BLUE_BORDER, width=1.8),
                fillcolor=color_hex,
                opacity=0.80,
                boxpoints="outliers",
                hovertemplate=(
                    f"Faixa: <b>{faixa} {doc_unit} (n={n_obs})</b><br>"
                    "Score Esperado: <b>%{y:.3f}</b><extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=16.5, color="#0f172a")),
        xaxis=dict(
            title="Quantidade Categorizada de Fatias/Documentos Utilizados (JEV Livre)",
            tickfont=dict(size=12, color="#1e293b"),
        ),
        yaxis=dict(
            title="Score Esperado (0 a 1)",
            range=[-0.03, 1.05],
            gridcolor="#e2e8f0",
        ),
        showlegend=False,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        height=440,
        margin=dict(l=55, r=25, t=65, b=65),
    )
    return fig


# ==============================================================================
# RENDERIZAÇÃO PRINCIPAL DO DASHBOARD (MODO STANDALONE E EMBUTIDO NO APP.PY)
# ==============================================================================
def _render_section_acuracia(df: pd.DataFrame):
    st.markdown('<div class="section-header">Acurácia</div>', unsafe_allow_html=True)

    # Texto Inicial exato separado em duas colunas com cards estilizados
    col_intro_1, col_intro_2 = st.columns(2, gap="medium")

    with col_intro_1:
        st.markdown(_clean_html("""
        <div class="intro-card">
            <h3>📚 Comparação entre RAG Tradicional e RAG Fichamentos</h3>
            <p>
                Para avaliar a acurácia dos métodos, elaboramos <strong>100 questões</strong> para os <strong>133 cursos de graduação</strong>
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
                <span style="color:#f87171;font-weight:700;">"Parcialmente incorreta"</span>,
                <span style="color:#4ade80;font-weight:700;">"Parcialmente correta"</span> e
                <span style="color:#10b981;font-weight:700;">"Correta"</span>.
            </p>
        </div>
        """), unsafe_allow_html=True)

    with col_intro_2:
        st.markdown(_clean_html("""
        <div class="intro-card" style="border-top-color: #f59e0b;">
            <h3>🧪 Foram realizados quatro experimentos:</h3>
            <ul>
                <li><strong>RAG tradicional com chunking simples</strong> — FileSearchStore da API Gemini (<code>k = 1, 5, 10</code>);</li>
                <li><strong>RAG com pré-LLM para definir os chunkings (fatias de PDFs)</strong> e <strong>embeddings sobre os fichamentos</strong> dessas fatias (<code>k = 1, 5, 10</code>).</li>
                <li><strong>RAG com pré-LLM para definir os chunkings (fatias de PDFs)</strong>, mas com o modelo <strong>TypeSafe JEV 1.14</strong> determinando as fatias a serem inseridas na janela de contexto, sob uma limitação das <em>top-k</em> (<code>k = 1, 5 ou 10</code>) fatias mais relevantes.</li>
                <li><strong>RAG com o mesmo pipeline anterior</strong>, diferenciando-se quanto à <strong>liberdade do modelo TypeSafe</strong>: sem restrições de <em>k</em> fatias mais relevantes, o modelo seleciona a quantidade de fatias que devem entrar no contexto.</li>
            </ul>
        </div>
        """), unsafe_allow_html=True)

    st.markdown("<div style='height: 1.1rem;'></div>", unsafe_allow_html=True)

    fig_acc_geral = build_vertical_stacked_bar(df, title="Qual o método que mais acerta?", height=490)
    st.plotly_chart(fig_acc_geral, width="stretch")

    st.markdown("<div style='height: 0.6rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div class="section-header" style="font-size:1.18rem;">O desempenho é afetado por perguntas multi-documento?</div>',
        unsafe_allow_html=True,
    )

    col_acc_h, col_acc_u = st.columns(2, gap="medium")
    with col_acc_h:
        df_hib = df[df["tipo_pergunta"] == "híbrida"]
        fig_hib = build_vertical_stacked_bar(
            df_hib,
            title=f"Perguntas Híbridas / Multi-Documento (n={df_hib['Pergunta'].nunique()} perguntas)",
            height=460,
        )
        st.plotly_chart(fig_hib, width="stretch")

    with col_acc_u:
        df_uni = df[df["tipo_pergunta"] == "única"]
        fig_uni = build_vertical_stacked_bar(
            df_uni,
            title=f"Perguntas Únicas / 1 Documento (n={df_uni['Pergunta'].nunique()} perguntas)",
            height=460,
        )
        st.plotly_chart(fig_uni, width="stretch")


def _render_section_qualidade(df: pd.DataFrame):
    st.markdown('<div class="section-header">Qualidade da resposta</div>', unsafe_allow_html=True)

    col_q1, col_q2 = st.columns(2, gap="medium")

    with col_q1:
        st.markdown(_clean_html("""
        <div class="formula-card">
            <h4>📐 Fórmula do Score Esperado</h4>
            <p style="font-size: 0.91rem; color: #cbd5e1; line-height: 1.55; margin-bottom: 0.5rem;">
                O Score é calculado a partir do <strong>exponencial das log probabilidades</strong> emitidas pelo modelo
                <strong>TypeSafe JEV 1.14</strong> para cada categoria de classificação, combinadas linearmente em [0, 1]:
            </p>
            <div class="formula-box">
                Score Esperado = Peso<sub>inc</sub> × 0 + Peso<sub>pinc</sub> × 0,15 + Peso<sub>pcor</sub> × 0,55 + Peso<sub>cor</sub> × 1
            </div>
            <p style="font-size: 0.88rem; color: #94a3b8; line-height: 1.55; margin-bottom: 0;">
                Onde cada peso corresponde a <strong>exp(logprob<sub>categoria</sub>)</strong>:
                <em>Incorreto (0)</em>, <em>Parcialmente incorreto (0,15)</em>,
                <em>Parcialmente correto (0,55)</em> e <em>Correto (1)</em>.
            </p>
        </div>
        """), unsafe_allow_html=True)

    with col_q2:
        st.markdown(_clean_html("""
        <div class="intro-card" style="border-top-color: #10b981;">
            <h3>💡 Interpretação Interativa do Score Esperado</h3>
            <p style="font-size: 0.9rem; margin-bottom: 0.7rem;">
                O <strong>Score Esperado</strong> capta a <strong>qualidade média da resposta</strong> dos métodos levando em consideração a
                <strong>incerteza do LLM julgador</strong> e <strong>penalizando severamente os erros dos métodos</strong>:
            </p>
            <div class="interactive-weight-row" title="Peso 0,00: erro completo zera a pontuação esperada da categoria.">
                <span style="min-width: 162px; font-weight: 700; color: #ef4444; font-size: 0.86rem;">Incorreto (× 0,00)</span>
                <div style="flex:1; background:#fee2e2; height:12px; border-radius:999px; overflow:hidden;">
                    <div style="width:2%; background:#ef4444; height:100%;"></div>
                </div>
                <span style="font-size:0.82rem; color:#64748b; min-width:130px; text-align:right;">Penalização total (100%)</span>
            </div>
            <div class="interactive-weight-row" title="Peso 0,15: penalização severa de 85% para respostas predominantemente incorretas.">
                <span style="min-width: 162px; font-weight: 700; color: #f87171; font-size: 0.86rem;">Parc. Incorreto (× 0,15)</span>
                <div style="flex:1; background:#fee2e2; height:12px; border-radius:999px; overflow:hidden;">
                    <div style="width:15%; background:#fca5a5; height:100%;"></div>
                </div>
                <span style="font-size:0.82rem; color:#64748b; min-width:130px; text-align:right;">Penalização de 85%</span>
            </div>
            <div class="interactive-weight-row" title="Peso 0,55: penalização moderada de 45% quando faltam elementos complementares.">
                <span style="min-width: 162px; font-weight: 700; color: #22c55e; font-size: 0.86rem;">Parc. Correto (× 0,55)</span>
                <div style="flex:1; background:#dcfce7; height:12px; border-radius:999px; overflow:hidden;">
                    <div style="width:55%; background:#86efac; height:100%;"></div>
                </div>
                <span style="font-size:0.82rem; color:#64748b; min-width:130px; text-align:right;">Penalização de 45%</span>
            </div>
            <div class="interactive-weight-row" style="margin-bottom: 0;" title="Peso 1,00: pontuação máxima para resposta integralmente correta.">
                <span style="min-width: 162px; font-weight: 700; color: #10b981; font-size: 0.86rem;">Correto (× 1,00)</span>
                <div style="flex:1; background:#d1fae5; height:12px; border-radius:999px; overflow:hidden;">
                    <div style="width:100%; background:#10b981; height:100%;"></div>
                </div>
                <span style="font-size:0.82rem; color:#64748b; min-width:130px; text-align:right;">Pontuação integral</span>
            </div>
        </div>
        """), unsafe_allow_html=True)

    st.markdown("<div style='height: 1.1rem;'></div>", unsafe_allow_html=True)
    fig_box_geral = build_general_score_boxplot(df, title="Qual a qualidade média das respostas?")
    st.plotly_chart(fig_box_geral, width="stretch")

    st.markdown("<div style='height: 0.6rem;'></div>", unsafe_allow_html=True)
    fig_grid_2x5 = build_grid_2x5_boxplots(
        df, title="A qualidade média é afetada por perguntas multi-documento?"
    )
    st.plotly_chart(fig_grid_2x5, width="stretch")


def _render_section_documentos(df: pd.DataFrame):
    st.markdown('<div class="section-header">Documentos e Qualidade</div>', unsafe_allow_html=True)

    df_livre = df[df["metodo_rag"] == "rag_fichamento_jev_livre"].copy()
    if df_livre.empty:
        st.info("Ainda não há registros para o método `rag_fichamento_jev_livre` na base carregada.")
        return

    # Linha 1: Boxplot geral
    fig_doc_geral = build_docs_vs_score_boxplot(
        df_livre,
        title="A quantidade de documentos está relacionada com a qualidade da resposta?",
    )
    st.plotly_chart(fig_doc_geral, width="stretch")

    # Linha 2: Duas colunas (Híbrida e Única)
    st.markdown(
        '<div class="section-header" style="font-size:1.18rem;">Há diferenças na relação qualidade-quantidade entre perguntas híbridas e únicas?</div>',
        unsafe_allow_html=True,
    )
    col_d1, col_d2 = st.columns(2, gap="medium")

    with col_d1:
        df_livre_hib = df_livre[df_livre["tipo_pergunta"] == "híbrida"]
        fig_doc_hib = build_docs_vs_score_boxplot(
            df_livre_hib,
            title=f"Perguntas Híbridas (n={len(df_livre_hib)})",
        )
        st.plotly_chart(fig_doc_hib, width="stretch")

    with col_d2:
        df_livre_uni = df_livre[df_livre["tipo_pergunta"] == "única"]
        fig_doc_uni = build_docs_vs_score_boxplot(
            df_livre_uni,
            title=f"Perguntas Únicas (n={len(df_livre_uni)})",
        )
        st.plotly_chart(fig_doc_uni, width="stretch")

    # Linha 3: Sumário descritivo geral dos documentos usados em HTML estilizado interativo
    st.markdown(
        '<div class="section-header" style="font-size:1.18rem;">Métricas adicionais</div>',
        unsafe_allow_html=True,
    )

    q_docs = pd.to_numeric(df_livre["quantidade_documentos"], errors="coerce").fillna(0)
    media_docs = float(q_docs.mean()) if len(q_docs) else 0.0
    mediana_docs = float(q_docs.median()) if len(q_docs) else 0.0
    dp_docs = float(q_docs.std()) if len(q_docs) > 1 else 0.0
    min_docs = int(q_docs.min()) if len(q_docs) else 0
    max_docs = int(q_docs.max()) if len(q_docs) else 0
    q25_docs = float(q_docs.quantile(0.25)) if len(q_docs) else 0.0
    q75_docs = float(q_docs.quantile(0.75)) if len(q_docs) else 0.0

    df_uni_l = df_livre[df_livre["tipo_pergunta"] == "única"]
    df_hib_l = df_livre[df_livre["tipo_pergunta"] == "híbrida"]
    media_uni = float(pd.to_numeric(df_uni_l["quantidade_documentos"], errors="coerce").mean()) if not df_uni_l.empty else 0.0
    media_hib = float(pd.to_numeric(df_hib_l["quantidade_documentos"], errors="coerce").mean()) if not df_hib_l.empty else 0.0

    dist_faixas = (
        df_livre["faixa_documentos"]
        .value_counts()
        .reindex(ORDEM_FAIXAS_DOCS, fill_value=0)
    )
    total_livre = max(1, len(df_livre))
    pct_1 = dist_faixas["1"] / total_livre * 100.0
    pct_2 = dist_faixas["2"] / total_livre * 100.0
    pct_3 = dist_faixas["3"] / total_livre * 100.0
    pct_4_plus = dist_faixas["4+"] / total_livre * 100.0

    score_medio_livre = float(df_livre["score_esperado"].mean()) if len(df_livre) else 0.0
    score_by_bin = {
        f: (float(df_livre[df_livre["faixa_documentos"] == f]["score_esperado"].mean()) if dist_faixas[f] > 0 else 0.0)
        for f in ORDEM_FAIXAS_DOCS
    }

    metrics_html = _clean_html(f"""
    <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border-radius: 16px; padding: 1.6rem 2rem; color: #f8fafc; box-shadow: 0 10px 25px rgba(15,23,42,0.16); border: 1px solid #334155;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem; margin-bottom:1.2rem;">
            <div>
                <span style="background:rgba(56,189,248,0.2); border:1px solid #38bdf8; color:#bae6fd; padding:0.2rem 0.65rem; border-radius:999px; font-size:0.75rem; font-weight:700; text-transform:uppercase;">
                    Seleção Autônoma JEV 1.14 (Prob &gt; 0,50)
                </span>
                <h3 style="margin:0.45rem 0 0 0; color:#ffffff; font-size:1.25rem;">Sumário Descritivo dos Documentos Utilizados (JEV Livre)</h3>
            </div>
            <div style="text-align:right;">
                <span style="font-size:0.82rem; color:#94a3b8;">Score Esperado Médio (JEV Livre)</span>
                <div style="font-size:1.65rem; font-weight:800; color:#38bdf8;">{score_medio_livre:.3f}</div>
            </div>
        </div>
        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(155px, 1fr)); gap: 0.9rem; margin-bottom: 1.35rem;">
            <div class="metric-mini-card" style="border-left:4px solid #38bdf8;" title="Média aritmética de documentos enviados ao gerador">
                <div style="font-size:0.78rem; color:#94a3b8; text-transform:uppercase; font-weight:600;">Média Geral</div>
                <div style="font-size:1.5rem; font-weight:800; color:#f8fafc; margin-top:0.2rem;">{media_docs:.2f} <span style="font-size:0.85rem; font-weight:500; color:#cbd5e1;">docs</span></div>
            </div>
            <div class="metric-mini-card" style="border-left:4px solid #3b82f6;" title="Mediana, desvio padrão e intervalo interquartil (Q1–Q3)">
                <div style="font-size:0.78rem; color:#94a3b8; text-transform:uppercase; font-weight:600;">Mediana ± DP (IIQ)</div>
                <div style="font-size:1.5rem; font-weight:800; color:#f8fafc; margin-top:0.2rem;">{mediana_docs:.1f} <span style="font-size:0.86rem; font-weight:500; color:#94a3b8;">± {dp_docs:.2f} (Q1={q25_docs:.0f}, Q3={q75_docs:.0f})</span></div>
            </div>
            <div class="metric-mini-card" style="border-left:4px solid #a855f7;" title="Menor e maior quantidade de documentos selecionados em uma consulta">
                <div style="font-size:0.78rem; color:#94a3b8; text-transform:uppercase; font-weight:600;">Amplitude (Mín – Máx)</div>
                <div style="font-size:1.5rem; font-weight:800; color:#f8fafc; margin-top:0.2rem;">{min_docs} a {max_docs} <span style="font-size:0.85rem; font-weight:500; color:#cbd5e1;">docs</span></div>
            </div>
            <div class="metric-mini-card" style="border-left:4px solid #0284c7;" title="Média de documentos selecionados em perguntas únicas">
                <div style="font-size:0.78rem; color:#94a3b8; text-transform:uppercase; font-weight:600;">Média (Únicas)</div>
                <div style="font-size:1.5rem; font-weight:800; color:#38bdf8; margin-top:0.2rem;">{media_uni:.2f} <span style="font-size:0.85rem; font-weight:500; color:#cbd5e1;">docs</span></div>
            </div>
            <div class="metric-mini-card" style="border-left:4px solid #f59e0b;" title="Média de documentos selecionados em perguntas híbridas multi-documento">
                <div style="font-size:0.78rem; color:#94a3b8; text-transform:uppercase; font-weight:600;">Média (Híbridas)</div>
                <div style="font-size:1.5rem; font-weight:800; color:#fbbf24; margin-top:0.2rem;">{media_hib:.2f} <span style="font-size:0.85rem; font-weight:500; color:#cbd5e1;">docs</span></div>
            </div>
        </div>
        <div style="font-size:0.85rem; color:#cbd5e1; margin-bottom:0.45rem; font-weight:600;">
            Distribuição Proporcional e Score Médio por Faixa de Documentos Selecionados:
        </div>
        <div style="display:flex; height:26px; border-radius:999px; overflow:hidden; background:#0b1324; border:1px solid #475569; margin-bottom:0.85rem;">
            <div title="1 doc: {int(dist_faixas['1'])} ({pct_1:.1f}%) | Score médio: {score_by_bin['1']:.3f}" style="width:{max(pct_1, 0.5):.2f}%; background:#38bdf8; display:flex; align-items:center; justify-content:center; font-size:0.75rem; font-weight:700; color:#0f172a;">
                {f"{pct_1:.0f}%" if pct_1 >= 8 else ""}
            </div>
            <div title="2 docs: {int(dist_faixas['2'])} ({pct_2:.1f}%) | Score médio: {score_by_bin['2']:.3f}" style="width:{max(pct_2, 0.5):.2f}%; background:#3b82f6; display:flex; align-items:center; justify-content:center; font-size:0.75rem; font-weight:700; color:#ffffff;">
                {f"{pct_2:.0f}%" if pct_2 >= 6 else ""}
            </div>
            <div title="3 docs: {int(dist_faixas['3'])} ({pct_3:.1f}%) | Score médio: {score_by_bin['3']:.3f}" style="width:{max(pct_3, 0.5):.2f}%; background:#6366f1; display:flex; align-items:center; justify-content:center; font-size:0.75rem; font-weight:700; color:#ffffff;">
                {f"{pct_3:.0f}%" if pct_3 >= 6 else ""}
            </div>
            <div title="4+ docs: {int(dist_faixas['4+'])} ({pct_4_plus:.1f}%) | Score médio: {score_by_bin['4+']:.3f}" style="width:{max(pct_4_plus, 0.5):.2f}%; background:#8b5cf6; display:flex; align-items:center; justify-content:center; font-size:0.75rem; font-weight:700; color:#ffffff;">
                {f"{pct_4_plus:.0f}%" if pct_4_plus >= 6 else ""}
            </div>
        </div>
        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(175px, 1fr)); gap:0.65rem; font-size:0.82rem; color:#cbd5e1;">
            <div class="metric-mini-card" style="padding:0.65rem 0.85rem; border-top:3px solid #38bdf8;">
                <strong>🔹 1 doc:</strong> {int(dist_faixas['1'])} ({pct_1:.1f}%)<br>
                <span style="color:#94a3b8;">Score médio: <strong style="color:#f8fafc;">{score_by_bin['1']:.3f}</strong></span>
            </div>
            <div class="metric-mini-card" style="padding:0.65rem 0.85rem; border-top:3px solid #3b82f6;">
                <strong>🔵 2 docs:</strong> {int(dist_faixas['2'])} ({pct_2:.1f}%)<br>
                <span style="color:#94a3b8;">Score médio: <strong style="color:#f8fafc;">{score_by_bin['2']:.3f}</strong></span>
            </div>
            <div class="metric-mini-card" style="padding:0.65rem 0.85rem; border-top:3px solid #6366f1;">
                <strong>🟣 3 docs:</strong> {int(dist_faixas['3'])} ({pct_3:.1f}%)<br>
                <span style="color:#94a3b8;">Score médio: <strong style="color:#f8fafc;">{score_by_bin['3']:.3f}</strong></span>
            </div>
            <div class="metric-mini-card" style="padding:0.65rem 0.85rem; border-top:3px solid #8b5cf6;">
                <strong>🔮 4+ docs:</strong> {int(dist_faixas['4+'])} ({pct_4_plus:.1f}%)<br>
                <span style="color:#94a3b8;">Score médio: <strong style="color:#f8fafc;">{score_by_bin['4+']:.3f}</strong></span>
            </div>
        </div>
    </div>
    """)
    st.markdown(metrics_html, unsafe_allow_html=True)


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
    <div class="hero-banner">
        <div class="hero-badge">Experimento Científico • Sinform AI UFBA</div>
        <h1>Comparação entre RAG Tradicional e RAG Fichamentos</h1>
        <p>Avaliação comparativa em 200 perguntas regulamentares da UFBA (100 únicas e 100 híbridas multi-documento), com julgamento probabilístico via TypeSafe JEV 1.14.</p>
    </div>
    """), unsafe_allow_html=True)

    if df.empty:
        st.warning(
            f"Nenhum resultado encontrado em `{RESULTADOS_PATH}`. "
            "Assim que o experimento iniciar a gravação das respostas, os gráficos serão populados automaticamente."
        )
        return

    tab_acc, tab_qual, tab_docs = st.tabs([
        "Acurácia",
        "Qualidade da resposta",
        "Documentos e Qualidade",
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
