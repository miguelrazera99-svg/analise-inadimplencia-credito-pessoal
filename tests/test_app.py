from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_FILE = Path(__file__).resolve().parents[1] / "app.py"


def test_dashboard_inicia_sem_erros():
    app = AppTest.from_file(APP_FILE)
    app.run(timeout=30)

    assert not app.exception
    assert not app.error
    assert app.title[0].value == "Análise Crédito Pessoal"
