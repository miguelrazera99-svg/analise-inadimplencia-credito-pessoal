"""Figuras e conclusões geradas a partir da mesma implementação do notebook."""
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from src.analysis import analisar_defasagens, testar_robustez, comparar_classificacao_temporal, revisar_sazonalidade


def gerar_relatorio(base, metricas, destino: Path):
    destino.mkdir(parents=True, exist_ok=True)
    figuras = {
        "concessoes_inadimplencia": px.line(metricas, x="data", y="concessoes_milhoes", title="Concessões nominais — fluxo mensal (R$ milhões)"),
        "juros_selic": px.line(metricas, x="data", y=["juros_nao_consignado_pct_mes", "selic_pct_mes", "premio_sobre_selic_pp"], title="Juros e Selic (% a.m.); diferencial bruto (p.p.) — escala comum"),
        "valores_nominais_reais": px.line(metricas, x="data", y=["concessoes_milhoes", "concessoes_reais_milhoes"], title="Concessões nominais e reais — preços do último mês (R$ milhões)"),
        "crescimento_nominal_real": px.line(metricas, x="data", y=["concessoes_var_12m_pct", "concessoes_reais_var_12m_pct"], title="Variação anual da média móvel de 3 meses (%)"),
    }
    temporal = make_subplots(rows=2, cols=1, shared_xaxes=True,
                             subplot_titles=["Concessões nominais (R$ milhões)", "Inadimplência (% da carteira)"])
    temporal.add_trace(go.Scatter(x=metricas.data, y=metricas.concessoes_milhoes, name="Concessões"), row=1, col=1)
    for coluna, nome in [("inadimplencia_nao_consignado_pct", "Não consignado"), ("inadimplencia_consignado_pct", "Consignado")]:
        temporal.add_trace(go.Scatter(x=metricas.data, y=metricas[coluna], name=nome), row=2, col=1)
    temporal.update_layout(title="Concessões (fluxo) e inadimplência (estoque)", height=650)
    figuras["concessoes_inadimplencia"] = temporal
    validos = metricas.loc[metricas.cenario_principal.ne("Sem historico suficiente")]
    for nome in ("matriz_cenarios", "matriz_cenarios_reais_refinada"):
        figuras[nome] = px.scatter(validos, x="concessoes_reais_var_12m_pct", y="inadimplencia_var_12m_pp", color="cenario_principal", hover_data=["data"], title="Cenários retrospectivos — crescimento real (%) e inadimplência (p.p.)")
    for nome in ("linha_tempo_cenarios", "linha_tempo_cenarios_reais_refinada"):
        figuras[nome] = px.scatter(validos, x="data", y="cenario_principal", color="cenario_principal", title="Cenários retrospectivos — MM3 / percentil 20")
    defasagens = analisar_defasagens(metricas, amostra_comum=True)
    figuras["defasagens"] = px.bar(defasagens, x="defasagem_meses", y=["correlacao_pearson", "correlacao_mudanca_futura"], barmode="group", title="Associações descritivas — amostra comum", range_y=[-1, 1])
    sazonalidade = revisar_sazonalidade(metricas)
    figuras["sazonalidade"] = px.line(sazonalidade, x="mes_calendario", y=["mensal_media_pct", "anual_mm3_media_pct", "anual_mm6_media_pct"], markers=True, title="Perfil por mês do calendário — médias descritivas (%)")
    for nome, figura in figuras.items():
        figura.write_html(destino / f"{nome}.html", include_plotlyjs="cdn", div_id=nome)
    ultimo = metricas.iloc[-1]
    robustez = testar_robustez(base)
    _, temporal = comparar_classificacao_temporal(base)
    texto = (
        f"# Conclusões — {ultimo['data']:%m/%Y}\n\n"
        f"Concessões: R$ {ultimo['concessoes_milhoes']/1000:.2f} bilhões. "
        f"Crescimento anual da MM3: {ultimo['concessoes_var_12m_pct']:.2f}% nominal e "
        f"{ultimo['concessoes_reais_var_12m_pct']:.2f}% real. "
        f"Inadimplência: {ultimo['inadimplencia_nao_consignado_pct']:.2f}%, "
        f"variação anual de {ultimo['inadimplencia_var_12m_pp']:.2f} p.p. "
        f"Cenário retrospectivo: **{ultimo['cenario_principal']}**.\n\n"
        f"Robustez retrospectiva: concordância de {robustez.concordancia_com_referencia_pct.min():.1f}% "
        f"a {robustez.concordancia_com_referencia_pct.max():.1f}% em {int(robustez.observacoes.iloc[0])} meses comuns. "
        f"Retrospectiva × expansiva: {temporal.concordancia_pct.iloc[0]:.1f}% "
        f"em {int(temporal.observacoes_comparaveis.iloc[0])} meses.\n\n"
        "## Defasagens em amostra comum\n\n"
        "Horizonte | Correlação com variação anual futura | Correlação com mudança entre t e t+h | Pares\n"
        "---: | ---: | ---: | ---:\n"
    )
    for r in defasagens.itertuples():
        texto += f"{r.defasagem_meses} | {r.correlacao_pearson:.3f} | {r.correlacao_mudanca_futura:.3f} | {r.observacoes}\n"
    texto += (
        "\nAs concessões permaneceram ativas, mas houve piora do risco observado no estoque. "
        "A correlação varia com o horizonte e a definição do alvo; não permite atribuir essa piora às novas operações. "
        "Janelas anuais se sobrepõem, e autocorrelação e choques comuns impedem interpretar os pares como observações independentes.\n\n"
        "O perfil mensal é diagnóstico descritivo, sem ajuste sazonal formal ou comprovação de estacionariedade. "
        "Expansão sem deterioração observada descreve apenas o risco agregado contemporâneo, sem garantir qualidade futura. "
        "A versão expansiva exclui o mês atual da estimação dos limites, mas não simula vintages e atrasos de publicação.\n"
    )
    (destino.parent / "conclusoes.md").write_text(texto, encoding="utf-8")
    return figuras
