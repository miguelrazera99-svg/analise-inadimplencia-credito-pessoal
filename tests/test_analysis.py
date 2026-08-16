import pandas as pd

from src.analysis import (
    analisar_defasagens,
    classificar_cenario,
    comparar_classificacao_temporal,
    construir_metricas,
    resumir_qualidade,
    testar_robustez as executar_teste_robustez,
)
from src.pipeline import FIM_ANALISE


def test_quadrantes_principais():
    assert classificar_cenario(pd.Series({"movimento_concessoes_real": "Alta", "movimento_inadimplencia": "Queda"})) == "Expansão sem deterioração observada"
    assert classificar_cenario(pd.Series({"movimento_concessoes_real": "Alta", "movimento_inadimplencia": "Alta"})) == "Crescimento com alerta"
    assert classificar_cenario(pd.Series({"movimento_concessoes_real": "Queda", "movimento_inadimplencia": "Alta"})) == "Aperto com deterioração"
    assert classificar_cenario(pd.Series({"movimento_concessoes_real": "Queda", "movimento_inadimplencia": "Queda"})) == "Recuperacao do risco"


def test_zona_neutra():
    resultado = classificar_cenario(pd.Series({"movimento_concessoes_real": "Estavel", "movimento_inadimplencia": "Estavel"}))
    assert resultado == "Transicao/estabilidade"


def _base_exemplo(meses=48):
    datas = pd.date_range("2020-01-01", periods=meses, freq="MS")
    sequencia = pd.Series(range(meses), dtype=float)
    return pd.DataFrame({
        "data": datas,
        "concessoes_milhoes": 1000 + sequencia * 10,
        "inadimplencia_nao_consignado_pct": 5 + sequencia * 0.02,
        "juros_nao_consignado_pct_mes": 4 + sequencia * 0.01,
        "saldo_nao_consignado_milhoes": 10000 + sequencia * 100,
        "inadimplencia_consignado_pct": 2 + sequencia * 0.005,
        "selic_pct_mes": 1 + sequencia * 0.001,
        "ipca_pct_mes": 0.4,
    })


def test_metricas_priorizam_variacao_12m_e_duas_medias_moveis():
    metricas = construir_metricas(_base_exemplo())
    assert {"concessoes_reais_var_12m_pct_mm3", "concessoes_reais_var_12m_pct_mm6"}.issubset(metricas.columns)
    assert metricas["concessoes_reais_var_12m_pct"].equals(metricas["concessoes_reais_var_12m_pct_mm3"])


def test_defasagens_e_robustez_cobrem_especificacoes():
    base = _base_exemplo(72)
    metricas = construir_metricas(base)
    defasagens = analisar_defasagens(metricas)
    robustez = executar_teste_robustez(base)
    assert defasagens["defasagem_meses"].tolist() == [3, 6, 9, 12]
    assert set(robustez["percentil_neutro"]) == {10, 20, 30}
    assert set(robustez["media_movel_meses"]) == {3, 6}


def test_expanding_nao_usa_observacao_atual_nem_futura():
    base = _base_exemplo(72)
    original = construir_metricas(base, modo_limite="expanding")
    alterada = base.copy()
    alterada.loc[alterada.index[-1], "concessoes_milhoes"] *= 100
    recalculada = construir_metricas(alterada, modo_limite="expanding")
    assert original.loc[original.index[-1], "limite_neutro_concessoes_pct"] == recalculada.loc[
        recalculada.index[-1], "limite_neutro_concessoes_pct"
    ]


def test_comparacao_temporal_e_qualidade_documentadas():
    base = _base_exemplo(72)
    comparacao, resumo = comparar_classificacao_temporal(base)
    qualidade = resumir_qualidade(base)
    assert {"cenario_retrospectivo", "cenario_sem_lookahead", "classificacoes_concordam"}.issubset(comparacao)
    assert resumo.loc[0, "observacoes_comparaveis"] > 0
    assert qualidade.loc[0, "meses_ausentes"] == 0


def test_validacao_rejeita_datas_duplicadas():
    base = pd.concat([_base_exemplo(), _base_exemplo().iloc[[0]]], ignore_index=True).sort_values("data")
    try:
        construir_metricas(base)
    except ValueError as erro:
        assert "duplicadas" in str(erro)
    else:
        raise AssertionError("Datas duplicadas deveriam ser rejeitadas.")


def test_recorte_padrao_permanece_fechado_em_dezembro_de_2025():
    assert FIM_ANALISE == "2025-12-31"
