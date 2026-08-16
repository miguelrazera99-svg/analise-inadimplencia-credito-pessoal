from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analysis import analisar_defasagens, comparar_classificacao_temporal


ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "processed" / "base_metricas_bcb.csv"
ROBUSTEZ_FILE = ROOT / "data" / "processed" / "teste_robustez.csv"


@st.cache_data(show_spinner=False)
def carregar_base_processada(caminho: Path) -> pd.DataFrame:
    """Carrega a base mensal fechada, com datas no formato ISO."""
    return pd.read_csv(
        caminho,
        parse_dates=["data"],
        date_format="%Y-%m-%d",
    )


@st.cache_data(show_spinner=False)
def carregar_tabela_processada(caminho: Path) -> pd.DataFrame:
    """Carrega tabelas auxiliares estáticas do dashboard."""
    return pd.read_csv(caminho)


@st.cache_data(show_spinner=False)
def calcular_defasagens(base: pd.DataFrame) -> pd.DataFrame:
    """Calcula uma única vez as associações para a base completa."""
    return analisar_defasagens(base)


@st.cache_data(show_spinner=False)
def calcular_resumo_temporal(base: pd.DataFrame) -> pd.DataFrame:
    """Resume a comparação retrospectiva e sem look-ahead."""
    _, resumo = comparar_classificacao_temporal(base)
    return resumo


st.set_page_config(page_title="Análise Crédito Pessoal", page_icon="📊", layout="wide")
st.title("Análise Crédito Pessoal")
st.caption("Demanda, risco e preço do crédito pessoal não consignado — dados públicos do BCB")

if not DATA_FILE.exists():
    st.error("Base processada não encontrada. Execute: python -m src.pipeline")
    st.stop()

try:
    df_completo = carregar_base_processada(DATA_FILE)
except (OSError, ValueError, pd.errors.ParserError) as erro:
    st.error(f"Não foi possível carregar a base processada: {erro}")
    st.stop()
if df_completo.empty or "data" not in df_completo.columns:
    st.error("A base processada está vazia ou não contém a coluna de data.")
    st.stop()
inicio, fim = df_completo["data"].min().date(), df_completo["data"].max().date()
st.caption(
    f"Recorte histórico fechado: {inicio:%m/%Y} a {fim:%m/%Y}. "
    "Os resultados não são atualizados automaticamente."
)
periodo = st.sidebar.date_input("Período", value=(inicio, fim), min_value=inicio, max_value=fim)
df = df_completo.copy()
if len(periodo) == 2:
    df = df[df["data"].between(pd.Timestamp(periodo[0]), pd.Timestamp(periodo[1]))]
if df.empty or df.dropna(subset=["cenario_principal"]).empty:
    st.warning("O período selecionado não contém meses suficientes para exibir os indicadores.")
    st.stop()

ultimo = df.dropna(subset=["cenario_principal"]).iloc[-1]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Concessões", f"R$ {ultimo['concessoes_milhoes']:,.0f} mi")
c2.metric("Inadimplência", f"{ultimo['inadimplencia_nao_consignado_pct']:.2f}%")
c3.metric("Juros", f"{ultimo['juros_nao_consignado_pct_mes']:.2f}% a.m.")
c4.metric("Cenário", ultimo["cenario_principal"])

st.info(
    "Leitura descritiva, não causal. Concessões são um fluxo de novas operações; "
    "inadimplência é uma medida do estoque da carteira e pode reagir com defasagem."
)

tab_visao, tab_defasagens, tab_metodo = st.tabs(["Visão geral", "Defasagens", "Metodologia"])

with tab_visao:
    left, right = st.columns(2)
    with left:
        fig_concessoes = px.line(
            df, x="data", y="concessoes_milhoes", title="Concessões mensais",
            labels={"concessoes_milhoes": "R$ milhões", "data": "Data"},
        )
        fig_concessoes.add_vrect(x0="2020-03-01", x1="2021-12-31", fillcolor="gray", opacity=0.15, line_width=0, annotation_text="Pandemia")
        st.plotly_chart(fig_concessoes, width="stretch")
    with right:
        fig_saldo = px.line(
            df, x="data", y="saldo_nao_consignado_milhoes", title="Saldo da carteira",
            labels={"saldo_nao_consignado_milhoes": "R$ milhões", "data": "Data"},
        )
        fig_saldo.add_vrect(x0="2020-03-01", x1="2021-12-31", fillcolor="gray", opacity=0.15, line_width=0, annotation_text="Pandemia")
        st.plotly_chart(fig_saldo, width="stretch")

    left, right = st.columns(2)
    with left:
        risco = df.rename(columns={
            "inadimplencia_nao_consignado_pct": "Não consignado",
            "inadimplencia_consignado_pct": "Consignado",
        })
        fig_risco = px.line(risco, x="data", y=["Não consignado", "Consignado"], title="Inadimplência: não consignado × consignado", labels={"value": "% da carteira", "data": "Data", "variable": "Modalidade"})
        st.plotly_chart(fig_risco, width="stretch")
    with right:
        preco = df.rename(columns={
            "juros_nao_consignado_pct_mes": "Juros do crédito",
            "selic_pct_mes": "Selic mensal",
            "premio_sobre_selic_pp": "Prêmio bruto sobre a Selic",
        })
        fig_preco = px.line(preco, x="data", y=["Juros do crédito", "Selic mensal", "Prêmio bruto sobre a Selic"], title="Preço do crédito e Selic", labels={"value": "% ao mês / p.p.", "data": "Data", "variable": "Indicador"})
        st.plotly_chart(fig_preco, width="stretch")
        st.caption("O prêmio bruto sobre a Selic não é o spread bancário oficial.")

    st.subheader("Distribuição dos cenários")
    contagem = df.dropna(subset=["cenario_principal"]).groupby("cenario_principal", as_index=False).size().sort_values("size", ascending=False)
    st.plotly_chart(px.bar(contagem, x="cenario_principal", y="size", labels={"size": "Meses", "cenario_principal": "Cenário"}), width="stretch")

with tab_defasagens:
    st.subheader("Concessões atuais × inadimplência futura")
    st.write(
        "Associação de Pearson entre a variação em 12 meses das concessões reais atuais e "
        "a variação da inadimplência 3, 6, 9 e 12 meses à frente. Correlação não demonstra causalidade."
    )
    defasagens = calcular_defasagens(df_completo)
    if defasagens.empty or defasagens["correlacao_pearson"].isna().all():
        st.warning("Não há pares válidos suficientes para calcular as defasagens.")
    else:
        st.plotly_chart(px.bar(defasagens, x="defasagem_meses", y="correlacao_pearson", text_auto=".2f", labels={"defasagem_meses": "Defasagem (meses)", "correlacao_pearson": "Correlação de Pearson"}), width="stretch")
        st.dataframe(defasagens.style.format({"correlacao_pearson": "{:.3f}"}), width="stretch")

with tab_metodo:
    st.subheader("Metodologia e robustez")
    st.markdown(
        """
        - Variações de volume e risco são comparadas em 12 meses para reduzir efeitos sazonais.
        - A classificação principal usa média móvel de 3 meses e percentil neutro de 20%.
        - A robustez compara percentis 10%, 20% e 30% e médias móveis de 3 e 6 meses.
        - A classificação exibida é **retrospectiva**: seus limites usam a amostra completa.
        - Para simular uma leitura em tempo real, a alternativa *expanding window* usa apenas dados anteriores a cada mês e elimina look-ahead.
        - A matriz é uma regra descritiva de monitoramento agregado, não um modelo causal ou de risco individual.
        """
    )
    if ROBUSTEZ_FILE.exists():
        robustez = carregar_tabela_processada(ROBUSTEZ_FILE)
        if not robustez.empty:
            st.dataframe(robustez.style.format({"concordancia_com_referencia_pct": "{:.1f}%"}), width="stretch")
    st.subheader("Retrospectiva × alternativa sem look-ahead")
    resumo_temporal = calcular_resumo_temporal(
        df_completo[[
            "data", "concessoes_milhoes", "inadimplencia_nao_consignado_pct",
            "juros_nao_consignado_pct_mes", "saldo_nao_consignado_milhoes",
            "inadimplencia_consignado_pct", "selic_pct_mes", "ipca_pct_mes",
        ]]
    )
    st.dataframe(resumo_temporal.style.format({"concordancia_pct": "{:.1f}%"}), width="stretch")

st.caption(
    "Projeto educacional. A classificação não é oficial do BCB. "
    "Concessões (fluxo) e inadimplência (estoque) podem se relacionar com defasagens de 3, 6, 9 ou 12 meses."
)
