from pathlib import Path
from datetime import date
import shutil
import os
import pandas as pd

from streamlit.testing.v1 import AppTest


APP_FILE = Path(__file__).resolve().parents[1] / "app.py"


def test_dashboard_inicia_sem_erros():
    app = AppTest.from_file(APP_FILE)
    app.run(timeout=30)

    assert not app.exception
    assert not app.error
    assert app.title[0].value == "Análise Crédito Pessoal"


def test_filtro_nao_recalibra_analises_tecnicas():
    app = AppTest.from_file(APP_FILE).run(timeout=30)
    defasagens = app.dataframe[0].value.copy()
    app.sidebar.date_input[0].set_value((date(2025, 1, 1), date(2025, 12, 1))).run(timeout=30)
    assert not app.exception
    pd.testing.assert_frame_equal(defasagens, app.dataframe[0].value)


def test_cache_recarrega_csv_modificado(tmp_path):
    dados = tmp_path / "data" / "processed"
    shutil.copytree(APP_FILE.parent / "data" / "processed", dados)
    fonte = APP_FILE.read_text(encoding="utf-8").replace(
        'ROOT = Path(__file__).resolve().parent', f'ROOT = Path({str(tmp_path)!r})'
    )
    app = AppTest.from_string(fonte).run(timeout=30)
    assert not app.exception
    antes = app.metric[0].value
    arquivo = dados / "base_metricas_bcb.csv"
    tabela = pd.read_csv(arquivo)
    tabela.loc[tabela.index[-1], "concessoes_milhoes"] += 1000
    instante = arquivo.stat().st_mtime_ns
    tabela.to_csv(arquivo, index=False)
    os.utime(arquivo, ns=(instante + 2_000_000_000, instante + 2_000_000_000))
    app.run(timeout=30)
    assert not app.exception
    assert app.metric[0].value != antes
