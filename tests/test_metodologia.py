from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.analysis import (
    analisar_defasagens, construir_metricas, revisar_sazonalidade,
    testar_robustez as robustez, classificar_movimento,
)
from test_analysis import _base_exemplo


@pytest.mark.parametrize("corte", [45, 60, 100])
def test_prefixo_invariante_a_dados_futuros(corte):
    base = _base_exemplo(120)
    base["concessoes_milhoes"] *= 1 + 0.15 * np.sin(np.arange(120))
    esperado = construir_metricas(base.iloc[:corte], modo_limite="expanding")
    base.loc[corte:, "ipca_pct_mes"] = 25
    base.loc[corte:, "concessoes_milhoes"] *= 10
    base.loc[corte:, "inadimplencia_nao_consignado_pct"] = 80
    observado = construir_metricas(base, modo_limite="expanding").iloc[:corte]
    colunas = ["concessoes_reais_var_12m_pct", "limite_neutro_concessoes_pct",
               "limite_neutro_inadimplencia_pp", "cenario_principal"]
    pd.testing.assert_frame_equal(esperado[colunas], observado[colunas], check_exact=True)


def test_limite_exclui_mes_atual_e_respeita_aquecimento():
    base = _base_exemplo(72)
    a = construir_metricas(base, modo_limite="expanding")
    assert a.limite_neutro_concessoes_pct.iloc[:38].isna().all()
    assert pd.notna(a.limite_neutro_concessoes_pct.iloc[38])
    base.loc[50, "concessoes_milhoes"] *= 10
    base.loc[50, "inadimplencia_nao_consignado_pct"] = 70
    b = construir_metricas(base, modo_limite="expanding")
    for c in ["limite_neutro_concessoes_pct", "limite_neutro_inadimplencia_pp"]:
        assert a.loc[50, c] == b.loc[50, c]


def test_defasagem_alinha_futuro_e_remove_cauda():
    base = _base_exemplo(60)
    rng = np.random.default_rng(14)
    x = rng.normal(size=60)
    base["concessoes_reais_var_12m_pct"] = x
    base["inadimplencia_var_12m_pp"] = np.r_[np.zeros(3), x[:-3]]
    resultado = analisar_defasagens(base, (3,)).iloc[0]
    assert resultado.correlacao_pearson == pytest.approx(1)
    assert resultado.observacoes == 57
    assert resultado.fim_origem == base.data.iloc[-4]


def test_alvo_mudanca_futura_e_amostra_comum():
    base = _base_exemplo(72)
    base["inadimplencia_nao_consignado_pct"] += np.sin(np.arange(72) / 5)
    m = construir_metricas(base)
    r = analisar_defasagens(m, amostra_comum=True)
    assert r.observacoes.nunique() == 1
    assert r.fim_origem.nunique() == 1
    for linha in r.itertuples():
        h = linha.defasagem_meses
        pares = m.loc[m.data.between(linha.inicio_origem, linha.fim_origem)]
        alvo = (m.inadimplencia_nao_consignado_pct.shift(-h) - m.inadimplencia_nao_consignado_pct).loc[pares.index]
        assert linha.correlacao_mudanca_futura == pytest.approx(pares.concessoes_reais_var_12m_pct.corr(alvo))


def test_correlacao_indefinida_para_serie_constante():
    m = construir_metricas(_base_exemplo(72))
    m["concessoes_reais_var_12m_pct"] = 1.0
    assert analisar_defasagens(m).correlacao_pearson.isna().all()


@pytest.mark.parametrize("modo", ["retrospectivo", "expanding"])
def test_robustez_usa_mesma_amostra_e_referencia(modo):
    r = robustez(_base_exemplo(72), modo_limite=modo)
    assert len(r) == 6
    assert r.observacoes.nunique() == 1
    referencia = r.query("media_movel_meses == 3 and percentil_neutro == 20").iloc[0]
    assert referencia.concordancia_com_referencia_pct == 100
    assert referencia.divergencias == 0


@pytest.mark.parametrize("erro", ["mes_ausente", "data_invalida", "nan", "infinito", "ipca", "volume_zero", "vazia"])
def test_rejeita_base_que_invalida_defasagem_calendario(erro):
    base = _base_exemplo()
    if erro == "mes_ausente":
        base = base.drop(index=20)
    elif erro == "data_invalida":
        base.loc[20, "data"] = pd.NaT
    elif erro == "vazia":
        base = base.iloc[:0]
    else:
        coluna, valor = {"nan": ("concessoes_milhoes", np.nan),
                         "infinito": ("selic_pct_mes", np.inf),
                         "ipca": ("ipca_pct_mes", -100),
                         "volume_zero": ("concessoes_milhoes", 0)}[erro]
        base.loc[20, coluna] = valor
    with pytest.raises(ValueError):
        construir_metricas(base)


@pytest.mark.parametrize("h", [0, -3, 1.5, True])
def test_rejeita_horizonte_invalido(h):
    with pytest.raises(ValueError):
        analisar_defasagens(construir_metricas(_base_exemplo()), (h,))


def test_sazonalidade_padrao_anual_repetido():
    base = _base_exemplo(72)
    base["concessoes_milhoes"] = np.tile(np.arange(100, 112), 6)
    base["ipca_pct_mes"] = 0.0
    perfil = revisar_sazonalidade(construir_metricas(base))
    assert perfil.mensal_media_pct.abs().max() > 1
    assert np.allclose(perfil.anual_mm3_media_pct, 0)
    assert np.allclose(perfil.anual_mm6_media_pct, 0)
    assert perfil.observacoes.sum() == 72 - 17


def test_limites_inclusivos():
    assert classificar_movimento(2, 2) == "Estavel"
    assert classificar_movimento(-2, 2) == "Estavel"


def test_csv_versionado_corresponde_ao_codigo():
    pasta = Path(__file__).resolve().parents[1] / "data" / "processed"
    base = pd.read_csv(pasta / "base_analitica_bcb.csv", parse_dates=["data"], date_format="%Y-%m-%d")
    gravado = pd.read_csv(pasta / "base_metricas_bcb.csv", parse_dates=["data"], date_format="%Y-%m-%d")
    pd.testing.assert_frame_equal(gravado, construir_metricas(base), check_dtype=False, rtol=1e-10)
