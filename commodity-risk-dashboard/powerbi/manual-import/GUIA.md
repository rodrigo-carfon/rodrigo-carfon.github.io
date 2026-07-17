# Guia — Montar o dashboard no Power BI (importação manual)

Você tem 3 arquivos nesta pasta para importar:

- **Prices.csv** — 1 linha por commodity por dia, com preços e as métricas de risco (fato).
- **Correlation.csv** — correlação móvel 63d café × algodão ao longo do tempo.
- **KPI_Snapshot.csv** — foto do último pregão, 1 linha por commodity (para cartões).

> Estes CSVs são gerados por `pipeline.py`. Para atualizar os dados depois: rode
> `python pipeline.py` e, no Power BI, clique **Atualizar**.

---

## Passo 1 — Importar os 3 CSVs

1. Power BI Desktop → **Página Inicial → Obter dados → Texto/CSV**.
2. Selecione **Prices.csv** → em *Delimitador* deixe **Vírgula** → **Transformar Dados**.
3. Repita para **Correlation.csv** e **KPI_Snapshot.csv** (Obter dados → Texto/CSV).
   - As consultas devem ficar com os nomes **Prices**, **Correlation**, **KPI_Snapshot**
     (se não ficarem, renomeie no painel *Consultas* à esquerda — importante para o DAX bater).

## Passo 2 — Conferir os tipos (no Editor do Power Query)

Clique em cada consulta e confirme os tipos das colunas (ícone no cabeçalho):

- **Prices:** `date` = Data · `ticker, commodity, risk_flag` = Texto · todas as outras
  (`open, high, low, close, ret_pct, vol_21d, drawdown, pct_from_high, ma50, ma200`) = Número Decimal · `volume` = Número Inteiro.
- **Correlation:** `date` = Data · `corr_63d` = Número Decimal.
- **KPI_Snapshot:** `last_date` = Data · textos (`ticker, commodity, commodity_pt, unit, exchange, risk_flag`) = Texto · `contract_lbs` = Inteiro · o resto = Número Decimal.

Depois: **Página Inicial → Fechar e Aplicar**.

## Passo 3 — Criar a tabela Calendário

**Modelagem → Nova tabela**, cole e Enter:

```DAX
Calendar =
ADDCOLUMNS (
    CALENDAR ( MIN ( Prices[date] ), MAX ( Prices[date] ) ),
    "Year", YEAR ( [Date] ),
    "Month", FORMAT ( [Date], "MMM" ),
    "MonthNum", MONTH ( [Date] ),
    "YearMonth", FORMAT ( [Date], "YYYY-MM" )
)
```

Selecione a coluna **Month** → *Ferramentas de coluna → Classificar por coluna → MonthNum*
(para os meses saírem em ordem, não alfabética).

## Passo 4 — Relacionamento (star schema)

Vá em **Modelo** (ícone à esquerda) e arraste **Calendar[Date] → Prices[date]**
(1 para muitos, direção única). É isso que liga a dimensão de tempo ao fato.

## Passo 5 — Criar as medidas (DAX)

Crie uma tabela vazia para organizar: **Página Inicial → Inserir dados → Criar** (nomeie
`_Measures`). Depois **Nova medida** e cole cada uma (o *Formato* está indicado ao lado):

```DAX
Last Price = CALCULATE ( LASTNONBLANKVALUE ( Prices[date], MAX ( Prices[close] ) ) )
```
*Formato: 0,00*

```DAX
Day Change % =
VAR today = [Last Price]
VAR yesterday = CALCULATE ( [Last Price], DATEADD ( 'Calendar'[Date], -1, DAY ) )
RETURN DIVIDE ( today - yesterday, yesterday )
```
*Formato: Porcentagem, 2 casas*

```DAX
Annual Volatility = CALCULATE ( LASTNONBLANKVALUE ( Prices[date], MAX ( Prices[vol_21d] ) ) )
```
*Formato: Porcentagem, 1 casa*

```DAX
Current Drawdown = CALCULATE ( LASTNONBLANKVALUE ( Prices[date], MAX ( Prices[drawdown] ) ) )
```
*Formato: Porcentagem, 1 casa*

```DAX
Risk Flag =
VAR v = [Annual Volatility]
RETURN
    SWITCH ( TRUE (),
        v >= 0.45, "🔴 BREACH",
        v >= 0.30, "🟠 WARN",
        "🟢 OK" )
```

```DAX
Risk Color =
VAR v = [Annual Volatility]
RETURN SWITCH ( TRUE (), v >= 0.45, "#DC2626", v >= 0.30, "#D97706", "#16A34A" )
```

```DAX
Contract Notional US$ =
VAR lbs = IF ( SELECTEDVALUE ( Prices[ticker] ) = "KC=F", 37500, 50000 )
RETURN [Last Price] / 100 * lbs
```
*Formato: Moeda, 0 casas*

```DAX
52-Week High =
CALCULATE ( MAX ( Prices[close] ),
    DATESINPERIOD ( 'Calendar'[Date], MAX ( 'Calendar'[Date] ), -52, WEEK ) )
```
*Formato: 0,00*

```DAX
Distance From High % = DIVIDE ( [Last Price] - [52-Week High], [52-Week High] )
```
*Formato: Porcentagem, 1 casa*

```DAX
Days In Breach = CALCULATE ( COUNTROWS ( Prices ), Prices[risk_flag] = "BREACH" )
```
*Formato: Número inteiro*

## Passo 6 — Montar os visuais (1 página)

Insira e arraste os campos:

| Área | Visual | Campos |
|---|---|---|
| Topo (faixa) | 4 **Cartões** | `Last Price`, `Day Change %`, `Annual Volatility`, `Current Drawdown` |
| Filtro | **Segmentação de dados** | `Prices[commodity]` |
| Cima-esq. | **Gráfico de linhas** | Eixo X `Calendar[Date]` · Eixo Y `close`, `ma50`, `ma200` |
| Cima-dir. | **Gráfico de linhas** | Eixo X `Calendar[Date]` · Eixo Y `vol_21d` + **2 linhas de constante** (0,30 e 0,45, aba *Análise*) |
| Baixo-esq. | **Gráfico de linhas** | Eixo X `Correlation[date]` · Eixo Y `corr_63d` |
| Baixo-dir. | **Tabela** | `commodity`, `Last Price`, `Annual Volatility`, `Risk Flag`, `Days In Breach` |

**Colorir o risco na tabela:** selecione a tabela → formatação → *Cor de fundo* da coluna →
**Formatação condicional → Estilo: Valor do campo → campo `Risk Color`**.

## Passo 7 — Tema (opcional)

**Exibição → Temas → Procurar temas** → selecione
`..\theme\CommodityRisk-theme.json` (café = verde, algodão = azul, navy). Pronto.

---

Salve como **`.pbix`** normalmente. Qualquer passo que travar, me diga qual e eu detalho.
