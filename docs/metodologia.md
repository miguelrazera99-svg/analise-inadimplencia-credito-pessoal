# Metodologia e revisão técnica

## Escopo e integridade

Dados mensais agregados do SGS/BCB, março de 2011 a dezembro de 2025. O arquivo
`data/processed/base_analitica_bcb.csv` é o snapshot versionado usado na reprodução.
Ele é preservado nesta revisão. A coleta opcional pode devolver valores revisados.
Não há dados de clientes, contratos ou safras de originação.

Antes de calcular deslocamentos por linha, a validação exige calendário mensal
contínuo, uma data por mês no primeiro dia, séries numéricas finitas, volumes
positivos e IPCA maior que −100%. Meses ausentes não são interpolados nem
ignorados silenciosamente: o pipeline falha. As ausências de aquecimento nos
indicadores derivados são legítimas e não são preenchidas.

## Inflação, suavização e limites

Se P(t) é o produto acumulado de `1 + IPCA(t)/100`, o volume real exibido é
`C(t) × P(T)/P(t)`, em preços do último mês T. Para crescimento, calcula-se a
média móvel de `C(t)/P(t)` e sua variação em 12 meses. P(T) cancela nessa razão;
usar a unidade fixa também evita dependência numérica do IPCA futuro.

As janelas 3 e 6 são móveis para trás, com todos os meses exigidos. Crescimento
real e nominal têm o mesmo conceito: variação anual da média móvel, e não a
variação do fluxo bruto de um único mês. A inadimplência usa diferenças anuais em
pontos percentuais, não variações percentuais.

A faixa neutra é ±quantil(q) dos movimentos absolutos de cada indicador,
separadamente. Igualdade com o limite pertence à faixa neutra. Percentil 20 não
significa uma tolerância fixa de 20% de crescimento nem 20 p.p. de inadimplência.

O modo retrospectivo usa toda a amostra e não pode ser apresentado como regra
disponível no passado. O expansivo usa `abs(variacao).shift(1).expanding(24)`:
24 valores anteriores válidos de cada indicador, excluindo t. Com MM3, a primeira
classificação expansiva ocorre na 39ª observação; com MM6, na 42ª. Não se elimina
o aquecimento para melhorar artificialmente o tamanho da amostra.

## Associação defasada

X(t) é o crescimento anual da MM3 real. Para h em {3, 6, 9, 12}, são calculadas
correlações de Pearson com dois alvos:

- variação anual futura: `D(t+h) − D(t+h−12)`;
- mudança futura a partir de t: `D(t+h) − D(t)`.

O primeiro alvo sobrepõe o passado de t quando h < 12. Não é o mesmo que medir
exclusivamente a deterioração após a concessão. As últimas h linhas são excluídas.
São publicados os números de pares e as datas de origem. Uma tabela usa todos os
pares disponíveis por horizonte, e outra usa a interseção das origens válidas.
Correlação fica indefinida quando há menos de três pares ou série constante.
Alvos futuros nunca são usados para construir cenários contemporâneos.

Janelas anuais sobrepostas, autocorrelação, tendências e choques comuns limitam
interpretações. Não há inferência de significância, teste de causalidade, modelo
preditivo ou seleção otimizada de horizonte. Fluxo e estoque não identificam
qualidade de uma safra de crédito.

## Robustez e sazonalidade

São seis combinações de q = 0,10/0,20/0,30 e MM3/MM6 em cada modo de limite.
Todas são comparadas à referência MM3/P20 do mesmo modo, em interseção dos meses
válidos das seis configurações e da referência. Publicam-se concordância,
divergências, número de observações e cenário do último mês. A referência tem
100% por construção. Robustez é sensibilidade da regra, não precisão preditiva.

O perfil sazonal agrupa por mês do calendário as médias de três transformações:
variação mensal real, anual da MM3 e anual da MM6. Usa origens comuns e informa
contagens por mês. O padrão anual é atenuado, mas a dispersão entre esses perfis
não é teste formal de sazonalidade. Crescimento, choques, calendário e mudanças
de composição podem afetá-los. Não há ajuste X-13/STL ou testes ADF/KPSS, nem
afirmação de estacionariedade. O diagnóstico não usa médias centradas.

## Disponibilidade da informação

A expansão histórica dos limites elimina uso de observações futuras **na
calibração**, mas o indicador do próprio mês depende de publicação posterior.
A base não contém versões históricas (vintages), datas de divulgação ou revisões.
Um backtest operacional exigiria reconstruir o conjunto de dados efetivamente
disponível em cada decisão. A denominação legada `cenario_sem_lookahead` no CSV
de comparação refere-se estritamente aos limites, não a essa garantia mais ampla.

## Reprodutibilidade e apresentação

O notebook importa `src.analysis`, `src.pipeline` e `src.report`. Não há regras
locais divergentes. As conclusões são geradas dos resultados; a revisão corrige
a referência de 6,0% no README para 8,22% de crescimento nominal da MM3.
Juros, Selic e diferencial bruto usam escala comum; o diferencial não é spread
bancário oficial. O cache inclui modificação do arquivo na chave.

Os nomes antigos `matriz_cenarios.html` e `linha_tempo_cenarios.html` são mantidos
como aliases da classificação real principal, para não expor versões antigas
com regras distintas. As figuras usam Plotly via CDN. A base fonte não é coletada
automaticamente no notebook nem na integração contínua.

## Cobertura da avaliação

| Item | Implementação verificável |
|---|---|
| Defasagens 3/6/9/12 | Duas definições de alvo, pares por horizonte e amostra comum |
| Percentis 10/20/30, MM3/MM6 | Robustez retrospectiva e expansiva, denominador comum |
| Look-ahead | Limites até t−1; testes de truncamento e perturbação do futuro |
| Sazonalidade | Perfil mensal exportado e limites de interpretação explícitos |
| Terminologia | Expansão sem deterioração observada; nenhuma garantia sobre safras futuras |
| Notebook, app e README | Mesmas funções, fórmulas e conclusões reproduzíveis |
| Qualidade, cache e logs | Validação estrita, chave por modificação, logs no pipeline |
| Outputs e CI | CSVs, HTML e conclusões regenerados; testes e notebook executados |
