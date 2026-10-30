from pathlib import Path
import subprocess
import sys
import pandas as pd
import streamlit as st

try:
    import plotly.express as px
    import openpyxl  # noqa: F401
except ModuleNotFoundError:
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "--quiet",
        "plotly>=5.20.0", "openpyxl>=3.1.0"
    ])
    import plotly.express as px
    import openpyxl  # noqa: F401

BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "Experimento" / "Conjunto de Testes.xlsx"

COLOR_MAP = {
    "RAG Fichamento (Emb)": "#2563EB",   # Azul
    "RAG Fichamento (JEV)": "#0EA5E9",   # Azul-celeste
    "RAG Tradicional": "#DC2626"         # Vermelho
}


@st.cache_data(ttl=30)
def load_experiment_data() -> pd.DataFrame:
    df = pd.read_excel(DATASET_PATH)
    df["prob_acerto_jev_tradicional"] = pd.to_numeric(df["prob_acerto_jev_tradicional"], errors="coerce")
    df["prob_acerto_jev_fichamento"] = pd.to_numeric(df["prob_acerto_jev_fichamento"], errors="coerce")
    df["prob_acerto_jev_fichamento_jev"] = pd.to_numeric(df["prob_acerto_jev_fichamento_jev"], errors="coerce")

    df["acerto_95_tradicional_bool"] = df["prob_acerto_jev_tradicional"] >= 0.95
    df["acerto_95_fichamento_bool"] = df["prob_acerto_jev_fichamento"] >= 0.95
    df["acerto_95_fichamento_jev_bool"] = df["prob_acerto_jev_fichamento_jev"] >= 0.95

    df["acerto_90_tradicional_bool"] = df["prob_acerto_jev_tradicional"] >= 0.90
    df["acerto_90_fichamento_bool"] = df["prob_acerto_jev_fichamento"] >= 0.90
    df["acerto_90_fichamento_jev_bool"] = df["prob_acerto_jev_fichamento_jev"] >= 0.90
    return df


def render_experiment_dashboard():
    # CSS elegante e minimalista para o cabeçalho, subtítulos e cards de indicadores
    st.markdown("""
    <style>
        .exp-header {
            background-color: rgba(128, 128, 128, 0.04);
            border: 1px solid rgba(128, 128, 128, 0.16);
            border-left: 4px solid #2563EB;
            border-radius: 10px;
            padding: 24px 26px;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        .exp-title {
            font-size: 1.7rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin-bottom: 0.65rem;
            line-height: 1.25;
        }
        .exp-desc {
            font-size: 0.95rem;
            line-height: 1.55;
            opacity: 0.85;
            margin: 0;
        }
        .exp-subtitle {
            font-size: 1.02rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
            opacity: 0.9;
        }
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 12px;
        }
        .kpi-grid:last-child {
            margin-bottom: 0;
        }
        .stat-card {
            background: linear-gradient(180deg, rgba(128, 128, 128, 0.06) 0%, rgba(128, 128, 128, 0.02) 100%);
            border: 1px solid rgba(128, 128, 128, 0.18);
            border-radius: 10px;
            padding: 13px 16px;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
            transition: transform 0.15s ease, border-color 0.15s ease;
        }
        .stat-card:hover {
            transform: translateY(-2px);
            border-color: rgba(128, 128, 128, 0.32);
        }
        .stat-card.fichamento-emb {
            border-top: 3px solid #2563EB;
        }
        .stat-card.fichamento-jev {
            border-top: 3px solid #0EA5E9;
        }
        .stat-card.tradicional {
            border-top: 3px solid #DC2626;
        }
        .stat-label {
            font-size: 0.72rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            opacity: 0.72;
            margin-bottom: 5px;
        }
        .stat-value {
            font-size: 1.5rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            line-height: 1.15;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border: 1px solid rgba(128, 128, 128, 0.22) !important;
            border-radius: 10px !important;
            background-color: rgba(128, 128, 128, 0.02);
        }
    </style>
    """, unsafe_allow_html=True)

    df = load_experiment_data()

    # Cálculo dos indicadores principais
    prob_mean_fich_emb = df["prob_acerto_jev_fichamento"].mean() * 100.0
    prob_mean_fich_jev = df["prob_acerto_jev_fichamento_jev"].mean() * 100.0
    prob_mean_trad = df["prob_acerto_jev_tradicional"].mean() * 100.0

    ac95_fich_emb = df["acerto_95_fichamento_bool"].mean() * 100.0
    ac95_fich_jev = df["acerto_95_fichamento_jev_bool"].mean() * 100.0
    ac95_trad = df["acerto_95_tradicional_bool"].mean() * 100.0

    ac90_fich_emb = df["acerto_90_fichamento_bool"].mean() * 100.0
    ac90_fich_jev = df["acerto_90_fichamento_jev_bool"].mean() * 100.0
    ac90_trad = df["acerto_90_tradicional_bool"].mean() * 100.0

    # Topo dividido em duas colunas: esquerda (título + texto) e direita (6 cards compactos em grade 2x3)
    col_header, col_kpis = st.columns([1, 1.15], gap="large")

    with col_header:
        st.markdown("""
        <div class="exp-header">
            <div class="exp-title">Comparação entre RAG Tradicional e RAG Fichamento</div>
            <p class="exp-desc">
                Para avaliar a acurácia dos métodos, elaboramos 100 perguntas distribuídas proporcionalmente à extensão dos documentos oficiais do Colegiado de Estatística. Em seguida, utilizamos o modelo TypeSafe JEV 1.14 tanto na seleção de contexto quanto para calcular a probabilidade de acerto de cada resposta gerada.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col_kpis:
        st.markdown(f"""
        <div class="kpi-grid">
            <div class="stat-card fichamento-emb">
                <div class="stat-label">Prob. Média · Fich. Emb</div>
                <div class="stat-value">{prob_mean_fich_emb:.2f}%</div>
            </div>
            <div class="stat-card fichamento-jev">
                <div class="stat-label">Prob. Média · Fich. JEV</div>
                <div class="stat-value">{prob_mean_fich_jev:.2f}%</div>
            </div>
            <div class="stat-card tradicional">
                <div class="stat-label">Prob. Média · Tradicional</div>
                <div class="stat-value">{prob_mean_trad:.2f}%</div>
            </div>
        </div>
        <div class="kpi-grid">
            <div class="stat-card fichamento-emb">
                <div class="stat-label">Acurácia (≥ 0,95) · Fich. Emb</div>
                <div class="stat-value">{ac95_fich_emb:.1f}%</div>
            </div>
            <div class="stat-card fichamento-jev">
                <div class="stat-label">Acurácia (≥ 0,95) · Fich. JEV</div>
                <div class="stat-value">{ac95_fich_jev:.1f}%</div>
            </div>
            <div class="stat-card tradicional">
                <div class="stat-label">Acurácia (≥ 0,95) · Tradicional</div>
                <div class="stat-value">{ac95_trad:.1f}%</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 1.4rem;'></div>", unsafe_allow_html=True)

    # Linha 1: Dois gráficos em cima (Boxplot da Probabilidade + Acurácia Global >= 0,9)
    col_top_left, col_top_right = st.columns(2, gap="medium")

    with col_top_left:
        with st.container(border=True):
            st.markdown('<div class="exp-subtitle">Boxplot da Probabilidade (100 Perguntas)</div>', unsafe_allow_html=True)
            df_long = pd.DataFrame({
                "Modelo": (
                    ["RAG Fichamento (Emb)"] * len(df)
                    + ["RAG Fichamento (JEV)"] * len(df)
                    + ["RAG Tradicional"] * len(df)
                ),
                "Probabilidade": pd.concat([
                    df["prob_acerto_jev_fichamento"],
                    df["prob_acerto_jev_fichamento_jev"],
                    df["prob_acerto_jev_tradicional"]
                ], ignore_index=True)
            })

            fig_box = px.box(
                df_long,
                x="Modelo",
                y="Probabilidade",
                color="Modelo",
                color_discrete_map=COLOR_MAP,
                height=400
            )
            fig_box.update_traces(boxmean=True)
            fig_box.update_layout(
                margin=dict(l=10, r=10, t=20, b=20),
                showlegend=False,
                xaxis_title=None
            )
            st.plotly_chart(fig_box, use_container_width=True)

    with col_top_right:
        with st.container(border=True):
            st.markdown('<div class="exp-subtitle">Acurácia com Limiar ≥ 0,9</div>', unsafe_allow_html=True)
            df_acc90 = pd.DataFrame({
                "Modelo": ["RAG Fichamento (Emb)", "RAG Fichamento (JEV)", "RAG Tradicional"],
                "Acurácia (%)": [ac90_fich_emb, ac90_fich_jev, ac90_trad]
            })

            fig_bar = px.bar(
                df_acc90,
                x="Modelo",
                y="Acurácia (%)",
                color="Modelo",
                color_discrete_map=COLOR_MAP,
                text_auto=".1f",
                height=400
            )
            fig_bar.update_yaxes(range=[0, 100])
            fig_bar.update_layout(
                margin=dict(l=10, r=10, t=20, b=20),
                showlegend=False,
                xaxis_title=None
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    # Preparação do agrupamento por documento para a Linha 2
    doc_group = (
        df.groupby("documento", as_index=False)
        .agg(
            n=("pergunta", "count"),
            prob_emb=("prob_acerto_jev_fichamento", lambda s: s.mean() * 100.0),
            prob_jev=("prob_acerto_jev_fichamento_jev", lambda s: s.mean() * 100.0),
            prob_trad=("prob_acerto_jev_tradicional", lambda s: s.mean() * 100.0),
            ac90_emb=("acerto_90_fichamento_bool", lambda s: s.mean() * 100.0),
            ac90_jev=("acerto_90_fichamento_jev_bool", lambda s: s.mean() * 100.0),
            ac90_trad=("acerto_90_tradicional_bool", lambda s: s.mean() * 100.0),
        )
        .sort_values(by="ac90_emb", ascending=True)
    )
    doc_group["doc_com_n"] = doc_group.apply(
        lambda r: f"{r['documento']} (n={r['n']})", axis=1
    )

    # Linha 2: Gráfico de Acurácia >= 0,9 por Documento (3 modelos agrupados, altura expandida)
    with st.container(border=True):
        st.markdown('<div class="exp-subtitle">Acurácia ≥ 0,9 por Documento (%)</div>', unsafe_allow_html=True)

        df_doc_acc = pd.concat([
            pd.DataFrame({
                "Documento": doc_group["doc_com_n"],
                "Modelo": "RAG Fichamento (Emb)",
                "Acurácia (%)": doc_group["ac90_emb"],
                "n": doc_group["n"]
            }),
            pd.DataFrame({
                "Documento": doc_group["doc_com_n"],
                "Modelo": "RAG Fichamento (JEV)",
                "Acurácia (%)": doc_group["ac90_jev"],
                "n": doc_group["n"]
            }),
            pd.DataFrame({
                "Documento": doc_group["doc_com_n"],
                "Modelo": "RAG Tradicional",
                "Acurácia (%)": doc_group["ac90_trad"],
                "n": doc_group["n"]
            }),
        ], ignore_index=True)

        fig_doc_acc = px.bar(
            df_doc_acc,
            x="Acurácia (%)",
            y="Documento",
            color="Modelo",
            orientation="h",
            barmode="group",
            color_discrete_map=COLOR_MAP,
            text_auto=".1f",
            hover_data={"n": True},
            height=680
        )
        fig_doc_acc.update_xaxes(range=[0, 108])
        fig_doc_acc.update_layout(
            margin=dict(l=10, r=10, t=20, b=20),
            yaxis_title=None,
            legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1, title=None)
        )
        st.plotly_chart(fig_doc_acc, use_container_width=True)
