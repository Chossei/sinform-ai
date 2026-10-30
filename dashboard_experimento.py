from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "Experimento" / "Conjunto de Testes.xlsx"

COLOR_MAP = {
    "RAG Fichamento": "#2563EB",   # Azul
    "RAG Tradicional": "#DC2626"   # Vermelho
}


@st.cache_data(ttl=30)
def load_experiment_data() -> pd.DataFrame:
    df = pd.read_excel(DATASET_PATH)
    df["prob_acerto_jev_tradicional"] = pd.to_numeric(df["prob_acerto_jev_tradicional"], errors="coerce")
    df["prob_acerto_jev_fichamento"] = pd.to_numeric(df["prob_acerto_jev_fichamento"], errors="coerce")
    df["acerto_95_tradicional_bool"] = df["prob_acerto_jev_tradicional"] >= 0.95
    df["acerto_95_fichamento_bool"] = df["prob_acerto_jev_fichamento"] >= 0.95
    df["acerto_90_tradicional_bool"] = df["prob_acerto_jev_tradicional"] >= 0.90
    df["acerto_90_fichamento_bool"] = df["prob_acerto_jev_fichamento"] >= 0.90
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
            font-size: 1.75rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin-bottom: 0.65rem;
            line-height: 1.25;
        }
        .exp-desc {
            font-size: 0.96rem;
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
        .kpi-grid-top {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 12px;
        }
        .kpi-grid-bottom {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
        }
        .stat-card {
            background: linear-gradient(180deg, rgba(128, 128, 128, 0.06) 0%, rgba(128, 128, 128, 0.02) 100%);
            border: 1px solid rgba(128, 128, 128, 0.18);
            border-radius: 10px;
            padding: 14px 18px;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
            transition: transform 0.15s ease, border-color 0.15s ease;
        }
        .stat-card:hover {
            transform: translateY(-2px);
            border-color: rgba(128, 128, 128, 0.32);
        }
        .stat-card.fichamento {
            border-top: 3px solid #2563EB;
        }
        .stat-card.tradicional {
            border-top: 3px solid #DC2626;
        }
        .stat-card.variacao {
            border-top: 3px solid #64748B;
        }
        .stat-label {
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            opacity: 0.72;
            margin-bottom: 6px;
        }
        .stat-value {
            font-size: 1.6rem;
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
    ac95_fich = df["acerto_95_fichamento_bool"].mean() * 100.0
    ac95_trad = df["acerto_95_tradicional_bool"].mean() * 100.0

    prob_mean_fich = df["prob_acerto_jev_fichamento"].mean() * 100.0
    prob_mean_trad = df["prob_acerto_jev_tradicional"].mean() * 100.0
    variacao_pp = prob_mean_fich - prob_mean_trad

    ac90_fich = df["acerto_90_fichamento_bool"].mean() * 100.0
    ac90_trad = df["acerto_90_tradicional_bool"].mean() * 100.0

    # Topo dividido em duas colunas: esquerda (título + texto) e direita (indicadores)
    col_header, col_kpis = st.columns([1, 1.15], gap="large")

    with col_header:
        st.markdown("""
        <div class="exp-header">
            <div class="exp-title">Comparação entre RAG Tradicional e RAG Fichamento</div>
            <p class="exp-desc">
                Para avaliar a acurácia dos métodos, elaboramos 100 perguntas distribuídas proporcionalmente à extensão dos documentos oficiais do Colegiado de Estatística. Em seguida, utilizamos o modelo TypeSafe JEV 1.14 para calcular a probabilidade de acerto de cada resposta gerada.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col_kpis:
        st.markdown(f"""
        <div class="kpi-grid-top">
            <div class="stat-card fichamento">
                <div class="stat-label">Prob. Média · Fichamento</div>
                <div class="stat-value">{prob_mean_fich:.2f}%</div>
            </div>
            <div class="stat-card tradicional">
                <div class="stat-label">Prob. Média · Tradicional</div>
                <div class="stat-value">{prob_mean_trad:.2f}%</div>
            </div>
            <div class="stat-card variacao">
                <div class="stat-label">Variação Prob. Média</div>
                <div class="stat-value">{variacao_pp:+.2f} p.p. (fichamento)</div>
            </div>
        </div>
        <div class="kpi-grid-bottom">
            <div class="stat-card fichamento">
                <div class="stat-label">Acurácia (Prob ≥ 0,95) · Fichamento</div>
                <div class="stat-value">{ac95_fich:.1f}%</div>
            </div>
            <div class="stat-card tradicional">
                <div class="stat-label">Acurácia (Prob ≥ 0,95) · Tradicional</div>
                <div class="stat-value">{ac95_trad:.1f}%</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 1.4rem;'></div>", unsafe_allow_html=True)

    # 2. Os 3 gráficos na mesma linha, cada um com uma borda cinza leve
    col_box, col_bar, col_tornado = st.columns([1, 1, 1.35])

    with col_box:
        with st.container(border=True):
            st.markdown('<div class="exp-subtitle">Boxplot da Probabilidade (100 Perguntas)</div>', unsafe_allow_html=True)
            df_long = pd.DataFrame({
                "Modelo": ["RAG Fichamento"] * len(df) + ["RAG Tradicional"] * len(df),
                "Probabilidade": pd.concat([
                    df["prob_acerto_jev_fichamento"],
                    df["prob_acerto_jev_tradicional"]
                ], ignore_index=True)
            })

            fig_box = px.box(
                df_long,
                x="Modelo",
                y="Probabilidade",
                color="Modelo",
                color_discrete_map=COLOR_MAP,
                height=430
            )
            fig_box.update_traces(boxmean=True)
            fig_box.update_layout(
                margin=dict(l=10, r=10, t=20, b=20),
                showlegend=False,
                xaxis_title=None
            )
            st.plotly_chart(fig_box, use_container_width=True)

    with col_bar:
        with st.container(border=True):
            st.markdown('<div class="exp-subtitle">Acurácia com Limiar ≥ 0,9</div>', unsafe_allow_html=True)
            df_acc90 = pd.DataFrame({
                "Modelo": ["RAG Fichamento", "RAG Tradicional"],
                "Acurácia (%)": [ac90_fich, ac90_trad]
            })

            fig_bar = px.bar(
                df_acc90,
                x="Modelo",
                y="Acurácia (%)",
                color="Modelo",
                color_discrete_map=COLOR_MAP,
                text_auto=".1f",
                height=430
            )
            fig_bar.update_yaxes(range=[0, 100])
            fig_bar.update_layout(
                margin=dict(l=10, r=10, t=20, b=20),
                showlegend=False,
                xaxis_title=None
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    with col_tornado:
        with st.container(border=True):
            st.markdown('<div class="exp-subtitle">Acurácia ≥ 0,9 por Documento</div>', unsafe_allow_html=True)

            doc_group = (
                df.groupby("documento", as_index=False)
                .agg(
                    n=("pergunta", "count"),
                    ac90_fich=("acerto_90_fichamento_bool", lambda s: s.mean() * 100.0),
                    ac90_trad=("acerto_90_tradicional_bool", lambda s: s.mean() * 100.0)
                )
                .sort_values(by="ac90_fich", ascending=True)
            )
            doc_group["doc_com_n"] = doc_group.apply(
                lambda r: f"{r['documento']} (n={r['n']})", axis=1
            )

            df_tornado = pd.concat([
                pd.DataFrame({
                    "Documento": doc_group["doc_com_n"],
                    "Modelo": "RAG Fichamento",
                    "Acurácia (%)": -doc_group["ac90_fich"],
                    "Rótulo": doc_group["ac90_fich"].map(lambda v: f"{v:.1f}%"),
                    "n": doc_group["n"]
                }),
                pd.DataFrame({
                    "Documento": doc_group["doc_com_n"],
                    "Modelo": "RAG Tradicional",
                    "Acurácia (%)": doc_group["ac90_trad"],
                    "Rótulo": doc_group["ac90_trad"].map(lambda v: f"{v:.1f}%"),
                    "n": doc_group["n"]
                })
            ], ignore_index=True)

            fig_tornado = px.bar(
                df_tornado,
                x="Acurácia (%)",
                y="Documento",
                color="Modelo",
                orientation="h",
                barmode="relative",
                color_discrete_map=COLOR_MAP,
                text="Rótulo",
                hover_data={"n": True, "Rótulo": True, "Acurácia (%)": False},
                height=430
            )
            fig_tornado.update_xaxes(
                range=[-108, 108],
                tickvals=[-100, -50, 0, 50, 100],
                ticktext=["100%", "50%", "0%", "50%", "100%"]
            )
            fig_tornado.update_layout(
                margin=dict(l=10, r=10, t=20, b=20),
                yaxis_title=None,
                legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1, title=None)
            )
            st.plotly_chart(fig_tornado, use_container_width=True)
