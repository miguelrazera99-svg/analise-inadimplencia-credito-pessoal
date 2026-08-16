"""Métricas e regras descritivas de cenários do case."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


ROTULO_EXPANSAO = "Expansão sem deterioração observada"

FORMULAS_INDICADORES = {
    "concessoes_reais": "concessões nominais × índice IPCA do último mês / índice IPCA do mês",
    "concessoes_reais_var_12m_pct": "variação em 12 meses da média móvel das concessões reais",
    "saldo_real_var_12m_pct": "variação em 12 meses do saldo real",
    "inadimplencia_var_12m_pp": "inadimplência do mês menos inadimplência do mesmo mês do ano anterior",
    "diferencial_inadimplencia_pp": "inadimplência não consignado menos inadimplência consignado",
    "premio_sobre_selic_pp": "taxa do crédito pessoal menos Selic mensal",
}


def validar_base(base: pd.DataFrame) -> None:
    obrigatorias = {
        "data", "concessoes_milhoes", "inadimplencia_nao_consignado_pct",
        "juros_nao_consignado_pct_mes", "saldo_nao_consignado_milhoes",
        "inadimplencia_consignado_pct", "selic_pct_mes", "ipca_pct_mes",
    }
    faltantes = obrigatorias.difference(base.columns)
    if faltantes:
        raise ValueError(f"Colunas obrigatórias ausentes: {sorted(faltantes)}")
    if base["data"].duplicated().any():
        raise ValueError("A base possui datas duplicadas.")
    if not base["data"].is_monotonic_increasing:
        raise ValueError("A base deve estar ordenada por data.")


def resumir_qualidade(base: pd.DataFrame) -> pd.DataFrame:
    """Documenta cobertura, ausências e duplicidades da base consolidada."""
    validar_base(base)
    datas = pd.DatetimeIndex(base["data"])
    calendario = pd.date_range(datas.min(), datas.max(), freq="MS")
    meses_ausentes = calendario.difference(datas)
    return pd.DataFrame(
        {
            "inicio": [base["data"].min()],
            "fim": [base["data"].max()],
            "meses": [len(base)],
            "datas_duplicadas": [int(base["data"].duplicated().sum())],
            "ausencias_total": [int(base.isna().sum().sum())],
            "meses_ausentes": [len(meses_ausentes)],
            "lista_meses_ausentes": [", ".join(meses_ausentes.strftime("%Y-%m")) or "Nenhum"],
        }
    )


def classificar_movimento(valor: float, limite: float) -> str:
    if pd.isna(valor) or pd.isna(limite):
        return "Sem historico suficiente"
    if valor > limite:
        return "Alta"
    if valor < -limite:
        return "Queda"
    return "Estavel"


def classificar_cenario(linha: pd.Series) -> str:
    concessoes = linha["movimento_concessoes_real"]
    inadimplencia = linha["movimento_inadimplencia"]
    if "Sem historico suficiente" in (concessoes, inadimplencia):
        return "Sem historico suficiente"
    if concessoes == "Alta" and inadimplencia == "Alta":
        return "Crescimento com alerta"
    if concessoes == "Alta" and inadimplencia in ("Estavel", "Queda"):
        return ROTULO_EXPANSAO
    if concessoes == "Estavel" and inadimplencia == "Alta":
        return "Deterioracao do risco"
    if concessoes == "Queda" and inadimplencia == "Alta":
        return "Aperto com deterioração"
    if concessoes in ("Estavel", "Queda") and inadimplencia == "Queda":
        return "Recuperacao do risco"
    return "Transicao/estabilidade"


def construir_metricas(
    base: pd.DataFrame,
    percentil_neutro: float = 0.20,
    janela_media_movel: int = 3,
    modo_limite: str = "retrospectivo",
    minimo_historico_expanding: int = 24,
) -> pd.DataFrame:
    """Cria indicadores e uma classificação descritiva e reproduzível.

    ``retrospectivo`` calcula um limite único com a amostra completa e serve para
    descrever o histórico. ``expanding`` usa somente observações anteriores ao mês
    classificado, evitando look-ahead e aproximando o uso em tempo real.
    """
    if percentil_neutro <= 0 or percentil_neutro >= 1:
        raise ValueError("O percentil neutro deve estar entre 0 e 1.")
    if janela_media_movel not in (3, 6):
        raise ValueError("A janela da média móvel deve ser 3 ou 6 meses.")
    if modo_limite not in {"retrospectivo", "expanding"}:
        raise ValueError("modo_limite deve ser 'retrospectivo' ou 'expanding'.")
    if minimo_historico_expanding < 12:
        raise ValueError("O histórico mínimo do expanding deve ter ao menos 12 observações.")

    tabela = base.sort_values("data").reset_index(drop=True).copy()
    validar_base(tabela)

    for janela in (3, 6):
        tabela[f"concessoes_media_movel_{janela}m"] = tabela["concessoes_milhoes"].rolling(janela).mean()
        tabela[f"concessoes_var_12m_pct_mm{janela}"] = tabela[f"concessoes_media_movel_{janela}m"].pct_change(12, fill_method=None) * 100
    tabela["concessoes_var_12m_pct"] = tabela[f"concessoes_var_12m_pct_mm{janela_media_movel}"]
    tabela["saldo_var_12m_pct"] = tabela["saldo_nao_consignado_milhoes"].pct_change(12, fill_method=None) * 100
    tabela["inadimplencia_var_12m_pp"] = tabela["inadimplencia_nao_consignado_pct"].diff(12)
    tabela["diferencial_inadimplencia_pp"] = tabela["inadimplencia_nao_consignado_pct"] - tabela["inadimplencia_consignado_pct"]
    tabela["premio_sobre_selic_pp"] = tabela["juros_nao_consignado_pct_mes"] - tabela["selic_pct_mes"]

    tabela["indice_precos_ipca"] = (1 + tabela["ipca_pct_mes"] / 100).cumprod()
    fator = tabela["indice_precos_ipca"].iloc[-1] / tabela["indice_precos_ipca"]
    tabela["concessoes_reais_milhoes"] = tabela["concessoes_milhoes"] * fator
    tabela["saldo_real_milhoes"] = tabela["saldo_nao_consignado_milhoes"] * fator
    for janela in (3, 6):
        tabela[f"concessoes_reais_media_movel_{janela}m"] = tabela["concessoes_reais_milhoes"].rolling(janela).mean()
        tabela[f"concessoes_reais_var_12m_pct_mm{janela}"] = tabela[f"concessoes_reais_media_movel_{janela}m"].pct_change(12, fill_method=None) * 100
    tabela["concessoes_reais_var_12m_pct"] = tabela[f"concessoes_reais_var_12m_pct_mm{janela_media_movel}"]
    tabela["saldo_real_var_12m_pct"] = tabela["saldo_real_milhoes"].pct_change(12, fill_method=None) * 100

    movimentos_abs = tabela[["concessoes_reais_var_12m_pct", "inadimplencia_var_12m_pp"]].abs()
    if modo_limite == "retrospectivo":
        tabela["limite_neutro_concessoes_pct"] = movimentos_abs["concessoes_reais_var_12m_pct"].quantile(percentil_neutro)
        tabela["limite_neutro_inadimplencia_pp"] = movimentos_abs["inadimplencia_var_12m_pp"].quantile(percentil_neutro)
    else:
        historico_anterior = movimentos_abs.shift(1)
        tabela["limite_neutro_concessoes_pct"] = historico_anterior["concessoes_reais_var_12m_pct"].expanding(
            min_periods=minimo_historico_expanding
        ).quantile(percentil_neutro)
        tabela["limite_neutro_inadimplencia_pp"] = historico_anterior["inadimplencia_var_12m_pp"].expanding(
            min_periods=minimo_historico_expanding
        ).quantile(percentil_neutro)
    tabela["janela_media_movel_meses"] = janela_media_movel
    tabela["percentil_neutro"] = percentil_neutro
    tabela["modo_limite"] = modo_limite
    tabela["movimento_concessoes_real"] = [
        classificar_movimento(valor, limite)
        for valor, limite in zip(tabela["concessoes_reais_var_12m_pct"], tabela["limite_neutro_concessoes_pct"])
    ]
    tabela["movimento_inadimplencia"] = [
        classificar_movimento(valor, limite)
        for valor, limite in zip(tabela["inadimplencia_var_12m_pp"], tabela["limite_neutro_inadimplencia_pp"])
    ]
    tabela["cenario_principal"] = tabela.apply(classificar_cenario, axis=1)
    return tabela


def analisar_defasagens(
    metricas: pd.DataFrame,
    defasagens: Iterable[int] = (3, 6, 9, 12),
) -> pd.DataFrame:
    """Mede associação de Pearson entre concessões atuais e inadimplência futura.

    O resultado é descritivo: correlação não demonstra causalidade.
    """
    resultados = []
    x = metricas["concessoes_reais_var_12m_pct"]
    for meses in defasagens:
        y_futuro = metricas["inadimplencia_var_12m_pp"].shift(-meses)
        pares = pd.concat([x, y_futuro], axis=1).dropna()
        resultados.append(
            {
                "defasagem_meses": meses,
                "correlacao_pearson": pares.iloc[:, 0].corr(pares.iloc[:, 1]),
                "observacoes": len(pares),
            }
        )
    return pd.DataFrame(resultados)


def testar_robustez(
    base: pd.DataFrame,
    percentis: Iterable[float] = (0.10, 0.20, 0.30),
    janelas: Iterable[int] = (3, 6),
) -> pd.DataFrame:
    """Compara cenários sob percentis 10/20/30 e médias móveis 3/6 meses."""
    referencia = construir_metricas(base, percentil_neutro=0.20, janela_media_movel=3)["cenario_principal"]
    linhas = []
    for janela in janelas:
        for percentil in percentis:
            teste = construir_metricas(base, percentil_neutro=percentil, janela_media_movel=janela)
            validos = ~referencia.eq("Sem historico suficiente") & ~teste["cenario_principal"].eq("Sem historico suficiente")
            linhas.append(
                {
                    "media_movel_meses": janela,
                    "percentil_neutro": int(round(percentil * 100)),
                    "concordancia_com_referencia_pct": (referencia[validos] == teste.loc[validos, "cenario_principal"]).mean() * 100,
                    "cenarios_distintos": teste.loc[validos, "cenario_principal"].nunique(),
                    "observacoes": int(validos.sum()),
                }
            )
    return pd.DataFrame(linhas)


def comparar_classificacao_temporal(
    base: pd.DataFrame,
    percentil_neutro: float = 0.20,
    janela_media_movel: int = 3,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compara a leitura retrospectiva com a alternativa sem look-ahead."""
    retrospectiva = construir_metricas(base, percentil_neutro, janela_media_movel, "retrospectivo")
    tempo_real = construir_metricas(base, percentil_neutro, janela_media_movel, "expanding")
    comparacao = retrospectiva[["data", "cenario_principal"]].rename(
        columns={"cenario_principal": "cenario_retrospectivo"}
    )
    comparacao["cenario_sem_lookahead"] = tempo_real["cenario_principal"]
    validos = ~comparacao[["cenario_retrospectivo", "cenario_sem_lookahead"]].eq(
        "Sem historico suficiente"
    ).any(axis=1)
    comparacao["classificacoes_concordam"] = comparacao["cenario_retrospectivo"].eq(
        comparacao["cenario_sem_lookahead"]
    ).where(validos)
    resumo = pd.DataFrame(
        {
            "observacoes_comparaveis": [int(validos.sum())],
            "concordancia_pct": [comparacao.loc[validos, "classificacoes_concordam"].mean() * 100],
            "divergencias": [int((comparacao.loc[validos, "classificacoes_concordam"] == False).sum())],  # noqa: E712
        }
    )
    return comparacao, resumo
