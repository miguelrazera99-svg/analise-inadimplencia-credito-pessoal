"""Coleta robusta de series temporais da API SGS do Banco Central."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import logging
from time import sleep

import pandas as pd
import requests


SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SerieBCB:
    codigo: int
    coluna: str
    descricao: str


SERIES = (
    SerieBCB(20666, "concessoes_milhoes", "Concessoes - nao consignado PF"),
    SerieBCB(21114, "inadimplencia_nao_consignado_pct", "Inadimplencia - nao consignado PF"),
    SerieBCB(25464, "juros_nao_consignado_pct_mes", "Juros mensais - nao consignado PF"),
    SerieBCB(20574, "saldo_nao_consignado_milhoes", "Saldo - nao consignado PF"),
    SerieBCB(21119, "inadimplencia_consignado_pct", "Inadimplencia - consignado PF"),
    SerieBCB(4390, "selic_pct_mes", "Selic acumulada no mes"),
    SerieBCB(433, "ipca_pct_mes", "IPCA mensal"),
)


def _formatar_data(valor: str | date | pd.Timestamp) -> str:
    return pd.Timestamp(valor).strftime("%d/%m/%Y")


def buscar_intervalo(
    serie: SerieBCB,
    inicio: str | date | pd.Timestamp,
    fim: str | date | pd.Timestamp,
    *,
    timeout: int = 30,
    tentativas: int = 3,
) -> pd.DataFrame:
    """Busca um intervalo da SGS, com repeticao para falhas temporarias."""
    parametros = {
        "formato": "json",
        "dataInicial": _formatar_data(inicio),
        "dataFinal": _formatar_data(fim),
    }
    ultimo_erro: Exception | None = None

    for tentativa in range(1, tentativas + 1):
        try:
            LOGGER.debug(
                "Coletando série %s entre %s e %s (tentativa %s/%s).",
                serie.codigo,
                parametros["dataInicial"],
                parametros["dataFinal"],
                tentativa,
                tentativas,
            )
            resposta = requests.get(
                SGS_URL.format(codigo=serie.codigo),
                params=parametros,
                timeout=timeout,
            )
            resposta.raise_for_status()
            dados = resposta.json()
            if not dados:
                raise ValueError(f"Serie {serie.codigo} sem dados no intervalo solicitado.")

            tabela = pd.DataFrame(dados).rename(columns={"valor": serie.coluna})
            tabela["data"] = pd.to_datetime(tabela["data"], format="%d/%m/%Y")
            tabela[serie.coluna] = pd.to_numeric(tabela[serie.coluna], errors="coerce")
            LOGGER.info(
                "Série %s coletada: %s observações entre %s e %s.",
                serie.codigo,
                len(tabela),
                tabela["data"].min().date(),
                tabela["data"].max().date(),
            )
            return tabela[["data", serie.coluna]]
        except (requests.RequestException, ValueError) as erro:
            ultimo_erro = erro
            LOGGER.warning(
                "Falha temporária na série %s (tentativa %s/%s): %s",
                serie.codigo,
                tentativa,
                tentativas,
                erro,
            )
            if tentativa < tentativas:
                sleep(2 ** (tentativa - 1))

    raise RuntimeError(f"Falha ao coletar a serie {serie.codigo}: {ultimo_erro}")


def buscar_serie_em_blocos(
    serie: SerieBCB,
    inicio: str | date | pd.Timestamp,
    fim: str | date | pd.Timestamp,
    *,
    anos_por_bloco: int = 9,
) -> pd.DataFrame:
    """Busca historico em blocos menores que dez anos e consolida o resultado."""
    inicio_total = pd.Timestamp(inicio)
    fim_total = pd.Timestamp(fim)
    if inicio_total > fim_total:
        raise ValueError("A data inicial deve ser anterior a data final.")

    blocos: list[pd.DataFrame] = []
    inicio_bloco = inicio_total
    LOGGER.info(
        "Iniciando coleta em blocos da série %s (%s).",
        serie.codigo,
        serie.descricao,
    )
    while inicio_bloco <= fim_total:
        fim_bloco = min(
            inicio_bloco + pd.DateOffset(years=anos_por_bloco) - pd.Timedelta(days=1),
            fim_total,
        )
        blocos.append(buscar_intervalo(serie, inicio_bloco, fim_bloco))
        inicio_bloco = fim_bloco + pd.Timedelta(days=1)

    return (
        pd.concat(blocos, ignore_index=True)
        .drop_duplicates(subset="data", keep="last")
        .sort_values("data")
        .reset_index(drop=True)
    )


def coletar_base_analitica(
    inicio: str | date | pd.Timestamp = "2011-01-01",
    fim: str | date | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Coleta todas as series e preserva apenas meses comuns a elas."""
    fim = fim or pd.Timestamp.today().normalize()
    LOGGER.info("Coletando %s séries entre %s e %s.", len(SERIES), inicio, fim)
    tabelas = [buscar_serie_em_blocos(serie, inicio, fim) for serie in SERIES]
    base = tabelas[0]
    for tabela in tabelas[1:]:
        base = base.merge(tabela, on="data", how="inner", validate="one_to_one")
    base = base.sort_values("data").reset_index(drop=True)
    LOGGER.info(
        "Base consolidada: %s meses entre %s e %s.",
        len(base),
        base["data"].min().date(),
        base["data"].max().date(),
    )
    return base
