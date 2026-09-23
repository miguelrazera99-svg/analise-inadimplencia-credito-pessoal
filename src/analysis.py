"""Métricas e regras descritivas de cenários do case."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd
import numpy as np


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
    if base.empty:
        raise ValueError("A base está vazia.")
    if not pd.api.types.is_datetime64_any_dtype(base["data"]) or base["data"].isna().any():
        raise ValueError("Datas devem ser válidas e convertidas para datetime.")
    if base["data"].duplicated().any():
        raise ValueError("A base possui datas duplicadas.")
    if not base["data"].is_monotonic_increasing:
        raise ValueError("A base deve estar ordenada por data.")
    esperado = pd.date_range(base["data"].min(), base["data"].max(), freq="MS")
    if not pd.DatetimeIndex(base["data"]).equals(esperado):
        raise ValueError("A base deve conter meses consecutivos no primeiro dia do mês.")
    valores = base[sorted(obrigatorias - {"data"})]
    if not all(pd.api.types.is_numeric_dtype(valores[c]) for c in valores) or not np.isfinite(valores.to_numpy()).all():
        raise ValueError("As séries originais devem conter apenas valores numéricos finitos.")
    if (base["ipca_pct_mes"] <= -100).any():
        raise ValueError("IPCA deve ser maior que -100%.")
    if (base[["concessoes_milhoes", "saldo_nao_consignado_milhoes"]] <= 0).any().any():
        raise ValueError("Concessões e saldo devem ser positivos.")


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
    classificado. Isso remove o look-ahead dos limites, mas não contempla revisões
    históricas ou atrasos de publicação das séries (não há vintages na base).
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
        # A unidade fixa elimina até a dependência numérica do IPCA futuro.
        reais_base_fixa = tabela["concessoes_milhoes"] / tabela["indice_precos_ipca"]
        tabela[f"concessoes_reais_var_12m_pct_mm{janela}"] = reais_base_fixa.rolling(janela).mean().pct_change(12, fill_method=None) * 100
    tabela["concessoes_reais_var_12m_pct"] = tabela[f"concessoes_reais_var_12m_pct_mm{janela_media_movel}"]
    tabela["saldo_real_var_12m_pct"] = (tabela["saldo_nao_consignado_milhoes"] / tabela["indice_precos_ipca"]).pct_change(12, fill_method=None) * 100

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
    *,
    amostra_comum: bool = False,
) -> pd.DataFrame:
    """Mede associação de Pearson entre concessões atuais e inadimplência futura.

    O resultado é descritivo: correlação não demonstra causalidade.
    """
    defasagens = tuple(defasagens)
    if not defasagens or any(not isinstance(h, int) or isinstance(h, bool) or h <= 0 for h in defasagens):
        raise ValueError("Defasagens devem ser inteiros positivos.")
    validar_base(metricas)
    resultados = []
    x = metricas["concessoes_reais_var_12m_pct"]
    alvos = {h: metricas["inadimplencia_var_12m_pp"].shift(-h) for h in defasagens}
    comum = pd.concat([x, *alvos.values()], axis=1).notna().all(axis=1)
    for meses in defasagens:
        y_futuro = alvos[meses]
        pares = pd.concat([x, y_futuro], axis=1).dropna()
        if amostra_comum:
            pares = pares.loc[comum.loc[pares.index]]
        mudanca_futura = metricas["inadimplencia_nao_consignado_pct"].shift(-meses) - metricas["inadimplencia_nao_consignado_pct"]
        def correlacao(a, b):
            return a.corr(b) if len(a) >= 3 and a.nunique() > 1 and b.nunique() > 1 else float("nan")
        resultados.append(
            {
                "defasagem_meses": meses,
                "correlacao_pearson": correlacao(pares.iloc[:, 0], pares.iloc[:, 1]),
                "correlacao_mudanca_futura": correlacao(pares.iloc[:, 0], mudanca_futura.loc[pares.index]),
                "observacoes": len(pares),
                "inicio_origem": metricas.loc[pares.index, "data"].min(),
                "fim_origem": metricas.loc[pares.index, "data"].max(),
                "amostra": "comum" if amostra_comum else "por_horizonte",
            }
        )
    return pd.DataFrame(resultados)


def testar_robustez(
    base: pd.DataFrame,
    percentis: Iterable[float] = (0.10, 0.20, 0.30),
    janelas: Iterable[int] = (3, 6),
    *,
    modo_limite: str = "retrospectivo",
) -> pd.DataFrame:
    """Compara cenários sob percentis 10/20/30 e médias móveis 3/6 meses."""
    percentis, janelas = tuple(percentis), tuple(janelas)
    referencia = construir_metricas(base, percentil_neutro=0.20, janela_media_movel=3, modo_limite=modo_limite)["cenario_principal"]
    configuracoes = {(j, p): construir_metricas(base, percentil_neutro=p, janela_media_movel=j, modo_limite=modo_limite) for j in janelas for p in percentis}
    validos = ~referencia.eq("Sem historico suficiente")
    for teste in configuracoes.values():
        validos &= ~teste["cenario_principal"].eq("Sem historico suficiente")
    linhas = []
    for janela in janelas:
        for percentil in percentis:
            teste = configuracoes[janela, percentil]
            linhas.append(
                {
                    "media_movel_meses": janela,
                    "percentil_neutro": int(round(percentil * 100)),
                    "concordancia_com_referencia_pct": (referencia[validos] == teste.loc[validos, "cenario_principal"]).mean() * 100,
                    "cenarios_distintos": teste.loc[validos, "cenario_principal"].nunique(),
                    "observacoes": int(validos.sum()),
                    "modo_limite": modo_limite,
                    "divergencias": int((referencia[validos] != teste.loc[validos, "cenario_principal"]).sum()),
                    "cenario_ultimo_mes": teste["cenario_principal"].iloc[-1],
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


def revisar_sazonalidade(metricas: pd.DataFrame) -> pd.DataFrame:
    """Perfil mensal descritivo em amostra comum; não é ajuste sazonal formal."""
    tabela = pd.DataFrame({
        "mes_calendario": metricas["data"].dt.month,
        "variacao_mensal_real_pct": metricas["concessoes_reais_milhoes"].pct_change(fill_method=None) * 100,
        "variacao_anual_mm3_pct": metricas["concessoes_reais_var_12m_pct_mm3"],
        "variacao_anual_mm6_pct": metricas["concessoes_reais_var_12m_pct_mm6"],
    }).dropna()
    return tabela.groupby("mes_calendario").agg(
        observacoes=("variacao_mensal_real_pct", "size"),
        mensal_media_pct=("variacao_mensal_real_pct", "mean"),
        anual_mm3_media_pct=("variacao_anual_mm3_pct", "mean"),
        anual_mm6_media_pct=("variacao_anual_mm6_pct", "mean"),
    ).reset_index()
