# Análise Crédito Pessoal

Case de Business Analytics que acompanha demanda, risco e preço do crédito pessoal não consignado para pessoas físicas no Brasil.

> **Recorte histórico fechado:** março de 2011 a dezembro de 2025. O projeto não representa um painel em tempo real e seus resultados não são atualizados automaticamente.

**Dashboard online:** [explore a análise interativa no Streamlit](https://credito-inadimplencia-bcb.streamlit.app/).

## English summary

This portfolio project provides a descriptive analysis of non-payroll-deducted personal loans in Brazil, combining credit originations, portfolio delinquency, interest rates, outstanding balances, the Selic rate and inflation data from the Central Bank of Brazil.

- **Coverage:** March 2011 to December 2025, with 178 monthly observations and no missing or duplicated months in the consolidated source series.
- **Approach:** inflation adjustment, 12-month changes, rolling averages, scenario classification, robustness checks and descriptive lead-lag associations at 3, 6, 9 and 12 months.
- **Interpretation:** credit originations are a monthly **flow**, whereas delinquency describes the accumulated portfolio **stock**. All relationships are descriptive and must not be interpreted as causal.
- **Reproducibility:** the repository includes the executed notebook, modular Python pipeline, processed datasets, Streamlit dashboard, automated tests and a GitHub Actions workflow.
- **Live dashboard:** [open the interactive Streamlit app](https://credito-inadimplencia-bcb.streamlit.app/).

The complete methodological documentation and economic interpretation are presented below in Portuguese.

## Pergunta de negócio

Em quais períodos o crédito pessoal não consignado apresentou expansão sem deterioração observada, crescimento acompanhado de piora do risco, aperto ou recuperação — e como essa dinâmica se relacionou com a Selic e com o consignado?

## Escopo e interpretação

O projeto analisa o mercado agregado com dados públicos. Ele **não** estima risco individual, aprovação de clientes, LGD ou perda esperada. A classificação de cenários é uma regra analítica descritiva e reproduzível; não é uma classificação oficial do Banco Central nem um modelo causal.

Concessões representam um **fluxo mensal de novas operações**. Inadimplência representa uma característica do **estoque da carteira acumulada**. Por isso, mudanças nas concessões podem se associar à inadimplência apenas meses depois. O projeto examina defasagens de 3, 6, 9 e 12 meses como associações descritivas; correlação não demonstra causalidade.

## Dados e qualidade

Fonte: API SGS do Banco Central do Brasil. A base processada cobre **março de 2011 a dezembro de 2025**, com 178 observações mensais. O encerramento em dezembro de 2025 é uma decisão de escopo para manter uma análise histórica estável e reproduzível. Na versão validada não há datas duplicadas nem ausências nas séries originais consolidadas. Ausências iniciais em indicadores derivados são esperadas quando a fórmula exige média móvel ou comparação com 12 meses anteriores.

| Código | Indicador | Papel |
|---:|---|---|
| 20666 | Concessões de crédito pessoal não consignado PF | Demanda/fluxo |
| 21114 | Inadimplência do não consignado PF | Risco do estoque |
| 25464 | Taxa média mensal do não consignado PF | Preço |
| 20574 | Saldo da carteira do não consignado PF | Estoque |
| 21119 | Inadimplência do consignado PF | Benchmark |
| 4390 | Selic acumulada no mês | Contexto monetário |
| 433 | IPCA mensal | Ajuste dos valores nominais |

## Método

1. Coleta da API em blocos de nove anos, com timeout, repetição, validação HTTP e registros de execução (*logging*).
2. Conversão de datas e valores, remoção de duplicidades e consolidação mensal.
3. Correção monetária pelo IPCA e cálculo de médias móveis de 3 e 6 meses.
4. Priorização de variações em 12 meses para reduzir efeitos sazonais.
5. Comparação da inadimplência do não consignado com o consignado.
6. Cálculo do **prêmio bruto sobre a Selic**. Esse indicador nunca é tratado como spread bancário oficial.
7. Classificação dos meses pela combinação entre crescimento real das concessões e variação da inadimplência.
8. Análise descritiva de defasagens de 3, 6, 9 e 12 meses.
9. Teste de robustez com percentis neutros de 10%, 20% e 30% e médias móveis de 3 e 6 meses.

As variações em 12 meses ajudam a reduzir a influência de tendência e sazonalidade nas séries em nível, mas não garantem estacionariedade por si só. Como o projeto não executa testes formais de raiz unitária, como ADF ou KPSS, as correlações de Pearson são apresentadas apenas como associações descritivas e não como evidência causal ou validação econométrica definitiva.

### Fórmulas dos principais indicadores

| Indicador | Fórmula |
|---|---|
| Concessões reais | concessões nominais × índice IPCA do último mês ÷ índice IPCA do mês |
| Crescimento real das concessões | variação em 12 meses da média móvel das concessões reais |
| Crescimento real do saldo | variação em 12 meses do saldo corrigido pelo IPCA |
| Variação da inadimplência | inadimplência do mês − inadimplência do mesmo mês do ano anterior |
| Diferencial de inadimplência | inadimplência não consignado − inadimplência consignado |
| Prêmio bruto sobre a Selic | taxa mensal do crédito pessoal − Selic acumulada no mês |

### Regra de cenários

A classificação principal usa o percentil 20 dos movimentos absolutos históricos como faixa neutra e uma média móvel de 3 meses. Os demais parâmetros são usados no teste de robustez. Essa leitura principal é **retrospectiva**: o limite único é estimado com toda a amostra e, portanto, não deve ser aplicado diretamente como se estivesse disponível em cada data histórica.

Para tratar o vazamento na calibração dos limites, o projeto calcula uma alternativa com janela expansiva (*expanding window*). Cada limite usa exclusivamente observações anteriores, com mínimo de 24 valores válidos. `comparacao_classificacao_temporal.csv` compara as leituras e `base_metricas_expanding.csv` permite auditar os limites por mês. Isso remove look-ahead dos **limites**, mas não constitui backtest em tempo real: a base não contém vintages nem datas de divulgação, e os indicadores de t só estão disponíveis após publicação. Revisões históricas do BCB continuam sendo uma limitação.

| Concessões reais | Inadimplência | Cenário |
|---|---|---|
| Alta | Alta | Crescimento com alerta |
| Alta | Estável ou queda | Expansão sem deterioração observada |
| Estável | Alta | Deterioração do risco |
| Queda | Alta | Aperto com deterioração |
| Estável ou queda | Queda | Recuperação do risco |
| Demais combinações | — | Transição/estabilidade |

O período de março de 2020 a dezembro de 2021 é destacado como choque extraordinário da pandemia, sem atribuição causal.

## Resultado mais recente — dezembro de 2025

- concessões: aproximadamente **R$ 21,8 bilhões**; crescimento anual da média móvel de três meses de **8,22% nominal** e **3,59% real**;
- saldo da carteira: aproximadamente **R$ 388,4 bilhões**, crescimento nominal de cerca de **18,9%** em 12 meses;
- inadimplência não consignada: **9,16%**, alta de **2,70 p.p.** em 12 meses;
- inadimplência consignada: **2,81%**, diferencial de **6,35 p.p.**;
- taxa média mensal: **6,65%**, Selic mensal de **1,22%** e prêmio bruto sobre a Selic de **5,43 p.p.**;
- cenário principal: **Deterioração do risco**.

Os volumes cresceram nominalmente, mas a piora relevante da inadimplência sustenta a leitura de deterioração do risco na regra principal, que considera as concessões em termos reais. Isso não significa que as novas concessões tenham causado a piora: o fluxo de originação e o risco do estoque podem se relacionar com defasagem.

### Validação técnica e conclusões

| Horizonte | Correlação com variação anual futura | Correlação com mudança de t até t+h | Pares comuns |
|---:|---:|---:|---:|
| 3 meses | -0,081 | 0,181 | 152 |
| 6 meses | 0,135 | 0,287 | 152 |
| 9 meses | 0,314 | 0,362 | 152 |
| 12 meses | 0,385 | 0,385 | 152 |

O primeiro alvo é `D(t+h) − D(t+h−12)`; o segundo é `D(t+h) − D(t)`.
Para h menor que 12, a janela anual futura inclui meses anteriores a t. Os dois
alvos respondem perguntas diferentes. Os meses finais sem alvo observado são
excluídos. O arquivo `analise_defasagens.csv` conserva a amostra disponível por
horizonte; `analise_defasagens_amostra_comum.csv` fixa as mesmas 152 origens.
Autocorrelação e janelas sobrepostas impedem tratar os pares como independentes.
Não há inferência causal, p-valores ou escolha de horizonte por desempenho.

As seis combinações de percentis 10/20/30 e MM3/MM6 concordam entre **82,0% e
100,0%** em **161 meses comuns** na classificação retrospectiva. Na expansiva,
a concordância vai de **82,5% a 100,0%** em **137 meses comuns**. A referência é
MM3/P20 dentro de cada modo. A leitura retrospectiva e a expansiva concordam em
**95,7% dos 140 meses comparáveis**. Concordância não é acurácia preditiva; algumas
configurações classificam dezembro como crescimento com alerta, embora todas
registrem aumento do risco. Consulte [as conclusões geradas](outputs/conclusoes.md).

O diagnóstico por mês do calendário compara crescimento mensal real e anual
das MM3/MM6 em amostra comum. Ele mostra menor dispersão do perfil anual entre
meses, mas não prova remoção de sazonalidade. Médias móveis usam apenas o mês
atual e os anteriores; não são centradas. Não há dessazonalização formal nem
garantia de estacionariedade. Choques e composição da amostra afetam esse perfil.

**Expansão sem deterioração observada** descreve somente a combinação
contemporânea dos indicadores agregados, sem garantir qualidade das novas safras
ou ausência de deterioração futura. O consignado é referência descritiva, não
contrafactual. Veja [a documentação metodológica](docs/metodologia.md).

## Estrutura

```text
analise-credito-pessoal/
├── data/processed/       # Bases, defasagens e robustez
├── notebooks/            # Análise exploratória e narrativa
├── outputs/figures/      # Gráficos Plotly em HTML
├── src/
│   ├── bcb.py            # Coleta da API SGS
│   ├── analysis.py       # Métricas, cenários e análises
│   └── pipeline.py       # Execução reproduzível
├── tests/                # Testes automatizados
├── app.py                # Dashboard Streamlit
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## Como executar

No Windows, a partir da raiz do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m src.pipeline
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m streamlit run app.py
```

O comando sem `--atualizar` usa a base local validada. Para reproduzir a coleta do mesmo recorte histórico diretamente na API:

```powershell
.\.venv\Scripts\python.exe -m src.pipeline --atualizar --fim 2025-12-31
```

Abra `notebooks/01_coleta_bcb.ipynb` para acompanhar a análise completa.

Para executar o notebook e atualizar sua versão HTML, sem consultar a API:

```powershell
.\.venv\Scripts\python.exe -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=180 notebooks/01_coleta_bcb.ipynb
.\.venv\Scripts\python.exe -m jupyter nbconvert --to html notebooks/01_coleta_bcb.ipynb
```

O notebook e o pipeline usam as mesmas funções de `src/`. Ambos regeneram CSVs,
figuras e `outputs/conclusoes.md`; o notebook não mantém regras paralelas.
As figuras HTML usam Plotly via CDN e precisam de conexão para exibição.

O arquivo `requirements.txt` contém apenas as dependências necessárias para executar o pipeline e publicar o dashboard. O arquivo `requirements-dev.txt` acrescenta Jupyter e Pytest para desenvolvimento e validação.

## Reprodutibilidade e desempenho

- o pipeline registra coleta, tentativas e geração das saídas por meio de *logging*;
- datas da API e dos CSVs são convertidas com formatos explícitos;
- o dashboard usa `st.cache_data`, com invalidação pela data de modificação dos arquivos e limite de entradas;
- o recorte padrão do pipeline permanece fixado em **31 de dezembro de 2025**;
- testes automatizados validam cenários, robustez, defasagens, qualidade, ausência de look-ahead e inicialização do dashboard;
- o workflow em `.github/workflows/tests.yml` executa a suíte automaticamente em *pushes* e *pull requests* no GitHub.

## Limitações

- análise descritiva, sem inferência causal;
- dados agregados, não representativos de uma instituição específica;
- concessões são fluxo e inadimplência é estoque;
- correlações defasadas não identificam causa e efeito;
- resultados dependem das faixas neutras e da janela de suavização;
- a classificação retrospectiva usa a amostra completa; a versão expansiva protege a calibração, mas não contempla vintages ou atrasos de publicação;
- o prêmio bruto sobre a Selic não incorpora todos os componentes do spread oficial;
- pandemia e outros choques podem produzir rupturas estruturais.
- as variações em 12 meses mitigam tendência e sazonalidade, mas a estacionariedade não foi comprovada por testes formais;
- o recorte termina em dezembro de 2025 e não deve ser interpretado como monitoramento corrente do mercado.

## Aviso

Projeto educacional de portfólio. Não constitui recomendação de crédito, investimento ou política comercial.
