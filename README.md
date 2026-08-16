# Análise Crédito Pessoal

Case de Business Analytics que acompanha demanda, risco e preço do crédito pessoal não consignado para pessoas físicas no Brasil.

> **Recorte histórico fechado:** março de 2011 a dezembro de 2025. O projeto não representa um painel em tempo real e seus resultados não são atualizados automaticamente.

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

Para tratar explicitamente o risco de vazamento temporal, o projeto também calcula uma alternativa **sem look-ahead**, com janela expansiva (*expanding window*). Para cada mês, os limites são estimados exclusivamente com observações anteriores, com mínimo de 24 observações válidas. O arquivo `comparacao_classificacao_temporal.csv` compara as duas leituras; a alternativa expansiva é a apropriada para simular monitoramento em tempo real, enquanto a classificação principal permanece útil para descrição retrospectiva homogênea.

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

- concessões: aproximadamente **R$ 21,8 bilhões**, crescimento nominal de cerca de **6,0%** em 12 meses;
- saldo da carteira: aproximadamente **R$ 388,4 bilhões**, crescimento nominal de cerca de **18,9%** em 12 meses;
- inadimplência não consignada: **9,16%**, alta de **2,70 p.p.** em 12 meses;
- inadimplência consignada: **2,81%**, diferencial de **6,35 p.p.**;
- taxa média mensal: **6,65%**, Selic mensal de **1,22%** e prêmio bruto sobre a Selic de **5,43 p.p.**;
- cenário principal: **Deterioração do risco**.

Os volumes cresceram nominalmente, mas a piora relevante da inadimplência sustenta a leitura de deterioração do risco na regra principal, que considera as concessões em termos reais. Isso não significa que as novas concessões tenham causado a piora: o fluxo de originação e o risco do estoque podem se relacionar com defasagem.

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

O arquivo `requirements.txt` contém apenas as dependências necessárias para executar o pipeline e publicar o dashboard. O arquivo `requirements-dev.txt` acrescenta Jupyter e Pytest para desenvolvimento e validação.

## Reprodutibilidade e desempenho

- o pipeline registra coleta, tentativas e geração das saídas por meio de *logging*;
- datas da API e dos CSVs são convertidas com formatos explícitos;
- o dashboard usa `st.cache_data` para evitar releituras e recálculos desnecessários a cada interação;
- o recorte padrão do pipeline permanece fixado em **31 de dezembro de 2025**;
- testes automatizados validam cenários, robustez, defasagens, qualidade, ausência de look-ahead e inicialização do dashboard;
- o workflow em `.github/workflows/tests.yml` executa a suíte automaticamente em *pushes* e *pull requests* no GitHub.

## Limitações

- análise descritiva, sem inferência causal;
- dados agregados, não representativos de uma instituição específica;
- concessões são fluxo e inadimplência é estoque;
- correlações defasadas não identificam causa e efeito;
- resultados dependem das faixas neutras e da janela de suavização;
- a classificação retrospectiva usa a amostra completa; para uso temporal, deve-se preferir a versão expansiva sem look-ahead;
- o prêmio bruto sobre a Selic não incorpora todos os componentes do spread oficial;
- pandemia e outros choques podem produzir rupturas estruturais.
- o recorte termina em dezembro de 2025 e não deve ser interpretado como monitoramento corrente do mercado.

## Aviso

Projeto educacional de portfólio. Não constitui recomendação de crédito, investimento ou política comercial.
