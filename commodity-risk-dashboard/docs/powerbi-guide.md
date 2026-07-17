# Power BI — the PBIP project (and how it's built)

> The Power BI deliverable ships as a **PBIP project** (text-based, git-versioned) in
> [`../powerbi/`](../powerbi/): a **semantic model** (TMDL) with a star schema and all the
> DAX, plus a **report** and a **theme**. This guide explains the model, the DAX and the
> talking points — the same coffee/cotton risk analysis delivered through a BI tool.

## 0. Open the project (fastest path)

1. In **Power BI Desktop**, enable *File → Options → Preview features → **Power BI Project
   (.pbip) save format***, then restart.
2. Open [`../powerbi/CommodityRisk.pbip`](../powerbi/CommodityRisk.pbip).
3. In *Transform data → Manage parameters*, set **`DataFolder`** to your local
   `…/commodity-risk-dashboard/data/` path (with a trailing `\`). It defaults to the
   author's path.
4. **Refresh**. To apply the palette: *View → Themes → Browse for themes* →
   [`../powerbi/theme/CommodityRisk-theme.json`](../powerbi/theme/CommodityRisk-theme.json).

The report page ships with a title, a KPI table, a commodity slicer and a price line chart;
add the remaining visuals from §4 (drag-and-drop, a few minutes) and screenshot for the README.

> The model reads the flat **`data/*.csv`** files (`prices.csv`, `correlation.csv`,
> `kpi_snapshot.csv`) the pipeline emits — plain text refreshes cleanly and diffs well in git.

---

## 1. How the data is imported (already wired in the PBIP)

The model imports the three CSVs via a single `DataFolder` parameter, with types already set
in Power Query (`date` → Date; the numeric metric columns → Decimal; `ticker, commodity,
risk_flag` → Text). If you'd rather build it from scratch to learn the flow:

1. `Get Data` → **Text/CSV** → `data/prices.csv` (and `correlation.csv`, `kpi_snapshot.csv`).
   *(The `data/commodities_powerbi.xlsx` workbook is an equivalent single-file alternative.)*
2. Confirm the types above → `Close & Apply`.

### Calendar table (best practice — enables time intelligence)
In `Modeling` → `New Table`:
```DAX
Calendar =
ADDCOLUMNS(
    CALENDAR ( MIN(Prices[date]), MAX(Prices[date]) ),
    "Year", YEAR([Date]),
    "Month", FORMAT([Date], "MMM"),
    "MonthNum", MONTH([Date]),
    "YearMonth", FORMAT([Date], "YYYY-MM")
)
```
Relate `Calendar[Date]` → `Prices[date]` (1:N, single direction).

---

## 2. Data model (relationships)

```
Calendar[Date]   (1) ───< (N) Prices[date]
Prices[ticker]   (1) ───< (N) Correlation        (optional, if you want to cross them)
KPI_Snapshot     = supporting table (cards), no required relationship
```

Keep it simple: **one fact table (`Prices`)** + **one time dimension (`Calendar`)**. Being
able to justify a **star schema** is a strong point in a data interview.

---

## 3. DAX measures (already authored in the `_Measures` table)

> These are all defined in the PBIP model
> ([`_Measures.tmdl`](../powerbi/CommodityRisk.SemanticModel/definition/tables/_Measures.tmdl)).
> Listed here so you can read/justify each one — to rebuild by hand, create an empty
> `_Measures` table and add them with `New Measure`.

```DAX
-- Most recent closing price in context
Last Price =
CALCULATE ( LASTNONBLANKVALUE ( Prices[date], MAX ( Prices[close] ) ) )

-- Day change %
Day Change % =
VAR today = [Last Price]
VAR yesterday =
    CALCULATE (
        [Last Price],
        DATEADD ( Calendar[Date], -1, DAY )
    )
RETURN DIVIDE ( today - yesterday, yesterday )

-- Annualized volatility (last value of the window pre-computed in the pipeline)
Annual Volatility =
CALCULATE ( LASTNONBLANKVALUE ( Prices[date], MAX ( Prices[vol_21d] ) ) )

-- Current drawdown (loss from the peak)
Current Drawdown =
CALCULATE ( LASTNONBLANKVALUE ( Prices[date], MAX ( Prices[drawdown] ) ) )

-- Risk classification by volatility (governance)
Risk Flag =
VAR v = [Annual Volatility]
RETURN
    SWITCH ( TRUE (),
        v >= 0.45, "🔴 BREACH",
        v >= 0.30, "🟠 WARN",
        "🟢 OK"
    )

-- Dynamic color for the card/KPI (use in 'Conditional formatting' → 'Background color')
Risk Color =
VAR v = [Annual Volatility]
RETURN SWITCH ( TRUE (), v >= 0.45, "#DC2626", v >= 0.30, "#D97706", "#16A34A" )

-- Notional of 1 contract (¢/lb -> US$). Coffee=37,500 lb, Cotton=50,000 lb
Contract Notional US$ =
VAR lbs = IF ( SELECTEDVALUE ( Prices[ticker] ) = "KC=F", 37500, 50000 )
RETURN [Last Price] / 100 * lbs

-- 52-week high and distance from it
52-Week High =
CALCULATE ( MAX ( Prices[close] ),
    DATESINPERIOD ( Calendar[Date], MAX ( Calendar[Date] ), -52, WEEK ) )

Distance From High % =
DIVIDE ( [Last Price] - [52-Week High], [52-Week High] )

-- Days in BREACH over the period (risk control)
Days In Breach =
CALCULATE ( COUNTROWS ( Prices ), Prices[risk_flag] = "BREACH" )
```

---

## 4. Visuals (1 page, mirroring the HTML dashboard)

| Area | Visual | Fields |
|------|--------|--------|
| Top (strip) | 4–6 **Cards** | `Last Price`, `Day Change %`, `Annual Volatility`, `Current Drawdown`, `Risk Flag` |
| Filter | **Slicer** | `Prices[commodity]` (Coffee / Cotton buttons) |
| Top-left | **Line chart** | Axis `Calendar[Date]` · Values `close`, `ma50`, `ma200` |
| Top-right | **Line chart** | `vol_21d` over time + 2 **constant lines** (0.30 and 0.45) |
| Bottom-left | **Line** | `Correlation[corr_63d]` over time |
| Bottom-right | **Clustered columns** | Axis `Calendar[Month]` · Value `AVERAGE(ret_pct)` per commodity |
| Table | **Table/Matrix** | `commodity`, `Last Price`, `Annual Volatility`, `Risk Flag`, `Days In Breach` |

Impact tips:
- **Conditional formatting** on the risk column using the `Risk Color` measure.
- On the volatility chart's **limit lines**: `Analytics` → `Constant line` → 0.30 (orange)
  and 0.45 (red). That is the visual "risk control".
- Palette: a sober navy (`#1E3A8A`) for the theme; coffee in green, cotton in blue.
- `View` → `Theme` → customize for a clean, brokerage-style look.

---

## 5. Talking points (Power BI)

- **Why a star schema?** fact `Prices` + dimension `Calendar` → simpler measures,
  time intelligence (`DATEADD`, `DATESINPERIOD`) and performance.
- **Measure vs. calculated column:** a measure is computed in the visual's context
  (on demand); a column is materialized per row at load time. Volatility and drawdown are
  pre-computed in Python (ETL) and the rest are measures — be ready to justify that split
  (processing cost vs. flexibility).
- **Refresh:** how you would schedule a refresh (Power BI Service / gateway) if the source
  were a production database instead of Excel.
- **DirectQuery vs. Import:** Import (what we use) is faster; DirectQuery suits very large
  / real-time data straight from the database.
