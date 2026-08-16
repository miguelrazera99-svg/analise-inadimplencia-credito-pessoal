"""Execucao reproduzivel da coleta e preparacao das bases."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from src.analysis import (
    analisar_defasagens,
    comparar_classificacao_temporal,
    construir_metricas,
    resumir_qualidade,
    testar_robustez,
)
from src.bcb import coletar_base_analitica


RAIZ = Path(__file__).resolve().parents[1]
PASTA_PROCESSADOS = RAIZ / "data" / "processed"
FIM_ANALISE = "2025-12-31"
LOGGER = logging.getLogger(__name__)


def executar(*, atualizar: bool, fim: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    PASTA_PROCESSADOS.mkdir(parents=True, exist_ok=True)
    arquivo_base = PASTA_PROCESSADOS / "base_analitica_bcb.csv"

    if atualizar:
        fim_coleta = fim or FIM_ANALISE
        LOGGER.info("Atualizando a base do BCB até %s.", fim_coleta)
        base = coletar_base_analitica(fim=fim_coleta)
        base.to_csv(arquivo_base, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    elif arquivo_base.exists():
        LOGGER.info("Usando a base local fechada em dezembro de 2025: %s", arquivo_base)
        base = pd.read_csv(
            arquivo_base,
            parse_dates=["data"],
            date_format="%Y-%m-%d",
        )
    else:
        raise FileNotFoundError("Base local ausente. Execute com --atualizar.")

    metricas = construir_metricas(base)
    LOGGER.info("Gerando métricas e saídas processadas em %s.", PASTA_PROCESSADOS)
    metricas.to_csv(
        PASTA_PROCESSADOS / "base_metricas_bcb.csv",
        index=False,
        encoding="utf-8-sig",
        date_format="%Y-%m-%d",
    )
    analisar_defasagens(metricas).to_csv(
        PASTA_PROCESSADOS / "analise_defasagens.csv", index=False, encoding="utf-8-sig"
    )
    testar_robustez(base).to_csv(
        PASTA_PROCESSADOS / "teste_robustez.csv", index=False, encoding="utf-8-sig"
    )
    comparacao_temporal, resumo_temporal = comparar_classificacao_temporal(base)
    comparacao_temporal.to_csv(
        PASTA_PROCESSADOS / "comparacao_classificacao_temporal.csv",
        index=False,
        encoding="utf-8-sig",
        date_format="%Y-%m-%d",
    )
    resumo_temporal.to_csv(
        PASTA_PROCESSADOS / "resumo_classificacao_temporal.csv", index=False, encoding="utf-8-sig"
    )
    resumir_qualidade(base).to_csv(
        PASTA_PROCESSADOS / "qualidade_dados.csv", index=False, encoding="utf-8-sig", date_format="%Y-%m-%d"
    )
    return base, metricas


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--atualizar", action="store_true", help="Consulta novamente a API SGS.")
    parser.add_argument(
        "--fim",
        help=f"Data final no formato AAAA-MM-DD. Padrão do projeto: {FIM_ANALISE}.",
    )
    argumentos = parser.parse_args()
    base, metricas = executar(atualizar=argumentos.atualizar, fim=argumentos.fim)
    print(f"Base analitica: {base.shape[0]} meses, {base.shape[1]} colunas")
    print(f"Base de metricas: {metricas.shape[0]} meses, {metricas.shape[1]} colunas")
    print(f"Ultimo periodo: {metricas['data'].max():%m/%Y}")
