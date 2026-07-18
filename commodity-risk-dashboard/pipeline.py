# -*- coding: utf-8 -*-
"""
pipeline.py — Market-risk ETL for Coffee (KC) and Cotton (CT) ICE futures.

A compact, end-to-end data project on real soft-commodity prices: it extracts
daily futures prices, derives market-risk metrics, and loads them into a SQLite
database, a Power BI-ready Excel workbook, and a JSON payload for the dashboard.

Flow (Extract -> Transform -> Load):
  1. EXTRACT  — pull real ICE futures prices via yfinance
                (KC=F = Arabica coffee, CT=F = Cotton No.2), ~3 years of daily bars.
  2. TRANSFORM— compute returns, annualized volatility (rolling 21d), drawdown,
                distance from the 52-week high, coffee-vs-cotton correlation and
                "risk limit" flags (volatility regime) — all derived from REAL data.
  3. LOAD     — write to SQLite (data/commodities.db), export to Power BI
                (data/commodities_powerbi.xlsx) and to the dashboard
                (data/dashboard_data.json).

Usage:
  python pipeline.py
"""

import json
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).parent
DATA_DIR = HERE / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "commodities.db"
XLSX_PATH = DATA_DIR / "commodities_powerbi.xlsx"
JSON_PATH = DATA_DIR / "dashboard_data.json"
# CSV exports consumed by the Power BI (PBIP) model — plain text, git-diffable.
CSV_PRICES = DATA_DIR / "prices.csv"
CSV_CORR = DATA_DIR / "correlation.csv"
CSV_KPI = DATA_DIR / "kpi_snapshot.csv"

# ICE-traded soft commodities (physical commodities: coffee and cotton).
COMMODITIES = {
    "KC=F": {"name": "Coffee (Arabica)", "pt": "Coffee", "unit": "US¢/lb",
             "contract_lbs": 37500, "exchange": "ICE"},
    "CT=F": {"name": "Cotton No.2", "pt": "Cotton", "unit": "US¢/lb",
             "contract_lbs": 50000, "exchange": "ICE"},
}

# Risk limits (governance). Annualized-volatility bands used to classify each
# commodity's risk regime — the basis for the alert flags.
VOL_WARN = 0.30   # 30% p.a. -> warning
VOL_BREACH = 0.45  # 45% p.a. -> limit breached

TRADING_DAYS = 252


# ----------------------------------------------------------------------------
# 1. EXTRACT
# ----------------------------------------------------------------------------
def _download(tickers: list[str], period: str, retries: int = 4) -> pd.DataFrame:
    """yf.download with a light retry — Yahoo Finance is intermittent in CI.

    Serialised with ``threads=False``: yfinance keeps an on-disk cache and,
    when tickers download concurrently on the runner, one of them hits
    ``OperationalError('database is locked')`` and comes back empty. Downloading
    one ticker at a time sidesteps that contention.

    A frame is only accepted once EVERY ticker has at least one real close — a
    non-empty frame that is missing a ticker (all-NaN column) is a *partial*
    download, which we retry and, if it never heals, raise on. That guarantees
    the pipeline never emits a half-populated payload.
    """
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            raw = yf.download(tickers, period=period, progress=False,
                              auto_adjust=False, threads=False)
            if raw is None or raw.empty:
                last_err = RuntimeError("empty frame returned by yfinance")
            else:
                missing = [t for t in tickers
                           if ("Close", t) not in raw.columns
                           or raw[("Close", t)].dropna().empty]
                if not missing:
                    return raw
                last_err = RuntimeError(f"partial download — no data for {missing}")
        except Exception as err:  # noqa: BLE001 — retry any transient download error
            last_err = err
        wait = 3 * attempt
        print(f"          attempt {attempt}/{retries} failed ({last_err}); retrying in {wait}s…")
        time.sleep(wait)
    raise RuntimeError(f"yfinance download failed after {retries} attempts: {last_err}")


def extract(period: str = "3y") -> pd.DataFrame:
    """Download daily OHLCV for the futures and return it in long (tidy) form."""
    print(f"[EXTRACT] downloading {list(COMMODITIES)} ({period}) from ICE via Yahoo Finance…")
    raw = _download(list(COMMODITIES), period)

    frames = []
    for ticker, meta in COMMODITIES.items():
        sub = pd.DataFrame({
            "date": raw.index,
            "ticker": ticker,
            "commodity": meta["name"],
            "open": raw[("Open", ticker)].values,
            "high": raw[("High", ticker)].values,
            "low": raw[("Low", ticker)].values,
            "close": raw[("Close", ticker)].values,
            "volume": raw[("Volume", ticker)].values,
        })
        frames.append(sub)

    df = pd.concat(frames, ignore_index=True)
    df = df.dropna(subset=["close"]).sort_values(["ticker", "date"]).reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"]).dt.date

    # Both commodities are required — the study is a two-asset frontier. Refuse to
    # continue on a one-sided dataset rather than write a payload the dashboard
    # can't build (belt-and-suspenders behind _download's own check).
    counts = df.groupby("ticker").size()
    empty = [t for t in COMMODITIES if int(counts.get(t, 0)) == 0]
    if empty:
        raise RuntimeError(f"no price rows for {empty} — refusing to build a partial payload")

    print(f"          {len(df)} real price rows "
          f"({df['date'].min()} → {df['date'].max()})")
    return df


# ----------------------------------------------------------------------------
# 2. TRANSFORM
# ----------------------------------------------------------------------------
def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Add per-commodity risk metrics (all computed on real data)."""
    print("[TRANSFORM] computing returns, volatility, drawdown and risk flags…")
    out = []
    for ticker, g in df.groupby("ticker", sort=False):
        g = g.sort_values("date").copy()
        g["ret"] = g["close"].pct_change()
        g["ret_pct"] = g["ret"] * 100
        # Annualized volatility (21-session window ≈ 1 month).
        g["vol_21d"] = g["ret"].rolling(21).std() * np.sqrt(TRADING_DAYS)
        # Drawdown from the running peak over the period.
        running_max = g["close"].cummax()
        g["drawdown"] = g["close"] / running_max - 1
        # Distance from the 52-week high/low (≈252 sessions).
        g["high_52w"] = g["close"].rolling(252, min_periods=20).max()
        g["low_52w"] = g["close"].rolling(252, min_periods=20).min()
        g["pct_from_high"] = g["close"] / g["high_52w"] - 1
        # 50/200-session moving averages (classic trend signal).
        g["ma50"] = g["close"].rolling(50).mean()
        g["ma200"] = g["close"].rolling(200).mean()
        # Classify the risk regime by volatility.
        g["risk_flag"] = np.where(
            g["vol_21d"] >= VOL_BREACH, "BREACH",
            np.where(g["vol_21d"] >= VOL_WARN, "WARN", "OK"))
        out.append(g)
    res = pd.concat(out, ignore_index=True)
    return res


def correlation_series(df: pd.DataFrame, window: int = 63) -> pd.DataFrame:
    """Rolling correlation (≈3 months) of coffee vs cotton daily returns."""
    piv = df.pivot(index="date", columns="ticker", values="ret")
    if not {"KC=F", "CT=F"}.issubset(piv.columns):
        return pd.DataFrame(columns=["date", "corr_63d"])
    corr = piv["KC=F"].rolling(window).corr(piv["CT=F"])
    return pd.DataFrame({"date": corr.index, "corr_63d": corr.values}).dropna()


def build_kpis(df: pd.DataFrame, corr: pd.DataFrame) -> list[dict]:
    """KPIs for the most recent snapshot, per commodity."""
    kpis = []
    last_corr = float(corr["corr_63d"].iloc[-1]) if len(corr) else None
    for ticker, meta in COMMODITIES.items():
        g = df[df["ticker"] == ticker].sort_values("date")
        if g.empty:
            continue
        last = g.iloc[-1]
        prev = g.iloc[-2] if len(g) > 1 else last
        kpis.append({
            "ticker": ticker,
            "commodity": meta["name"],
            "commodity_pt": meta["pt"],
            "unit": meta["unit"],
            "exchange": meta["exchange"],
            "contract_lbs": meta["contract_lbs"],
            "last_date": str(last["date"]),
            "last_close": round(float(last["close"]), 2),
            "day_change_pct": round(float((last["close"] / prev["close"] - 1) * 100), 2),
            "vol_21d_annual_pct": round(float(last["vol_21d"]) * 100, 1)
                if pd.notna(last["vol_21d"]) else None,
            "drawdown_pct": round(float(last["drawdown"]) * 100, 1),
            "pct_from_high_pct": round(float(last["pct_from_high"]) * 100, 1)
                if pd.notna(last["pct_from_high"]) else None,
            "high_52w": round(float(last["high_52w"]), 2) if pd.notna(last["high_52w"]) else None,
            "low_52w": round(float(last["low_52w"]), 2) if pd.notna(last["low_52w"]) else None,
            "risk_flag": str(last["risk_flag"]),
            # Notional of 1 contract at the market price (¢/lb -> US$).
            "contract_notional_usd": round(float(last["close"]) / 100 * meta["contract_lbs"], 0),
            "corr_coffee_cotton_63d": round(last_corr, 2) if last_corr is not None else None,
        })
    return kpis


def build_frontier(df: pd.DataFrame) -> dict:
    """Risk × return frontier (Markowitz) for a coffee + cotton portfolio.

    Uses REALIZED annualized return (daily mean × 252) and annualized vol
    (std × √252), with the real correlation between the two. For each weight w in
    coffee, it computes the portfolio return and risk — plus the minimum-variance
    point.
    """
    piv = df.pivot(index="date", columns="ticker", values="ret").dropna()
    if not {"KC=F", "CT=F"}.issubset(piv.columns):
        return {}
    mu = piv.mean() * TRADING_DAYS
    sig = piv.std() * np.sqrt(TRADING_DAYS)
    rho = float(piv["KC=F"].corr(piv["CT=F"]))
    sc, st = float(sig["KC=F"]), float(sig["CT=F"])
    mc, mt = float(mu["KC=F"]), float(mu["CT=F"])

    def port(w):  # w = weight in coffee
        rp = w * mc + (1 - w) * mt
        vp = (w**2 * sc**2 + (1 - w)**2 * st**2 + 2 * w * (1 - w) * sc * st * rho) ** 0.5
        return round(rp * 100, 2), round(vp * 100, 2)

    points = []
    for i in range(0, 101, 5):
        w = i / 100
        ret, risk = port(w)
        points.append({"w_coffee": i, "ret": ret, "risk": risk})

    # minimum-variance weight (closed form for 2 assets)
    denom = sc**2 + st**2 - 2 * sc * st * rho
    w_mv = (st**2 - sc * st * rho) / denom if denom else 0.5
    w_mv = max(0.0, min(1.0, w_mv))
    mv_ret, mv_risk = port(w_mv)

    return {
        "corr": round(rho, 3),
        "assets": {
            "KC=F": {"ret": round(mc * 100, 2), "risk": round(sc * 100, 2)},
            "CT=F": {"ret": round(mt * 100, 2), "risk": round(st * 100, 2)},
        },
        "points": points,
        "min_var": {"w_coffee": round(w_mv * 100, 1), "ret": mv_ret, "risk": mv_risk},
    }


# ----------------------------------------------------------------------------
# 3. LOAD
# ----------------------------------------------------------------------------
def load_sqlite(df: pd.DataFrame, corr: pd.DataFrame, kpis: list[dict]):
    """Write the tables to SQLite and create an example VIEW."""
    print(f"[LOAD] writing SQLite → {DB_PATH.name}")
    con = sqlite3.connect(DB_PATH)
    price_cols = ["date", "ticker", "commodity", "open", "high", "low", "close", "volume"]
    df_db = df.copy()
    df_db["date"] = df_db["date"].astype(str)
    df_db[price_cols].to_sql("prices", con, if_exists="replace", index=False)

    metric_cols = ["date", "ticker", "ret_pct", "vol_21d", "drawdown",
                   "pct_from_high", "ma50", "ma200", "risk_flag"]
    df_db[metric_cols].to_sql("daily_metrics", con, if_exists="replace", index=False)

    corr_db = corr.copy()
    if len(corr_db):
        corr_db["date"] = corr_db["date"].astype(str)
    corr_db.to_sql("correlation", con, if_exists="replace", index=False)

    pd.DataFrame(kpis).to_sql("kpi_snapshot", con, if_exists="replace", index=False)

    # VIEW: latest-session risk summary for each commodity.
    con.executescript("""
        DROP VIEW IF EXISTS v_latest_risk;
        CREATE VIEW v_latest_risk AS
        SELECT p.ticker, p.commodity, p.date, p.close,
               m.vol_21d, m.drawdown, m.risk_flag
        FROM prices p
        JOIN daily_metrics m ON m.ticker = p.ticker AND m.date = p.date
        WHERE p.date = (SELECT MAX(date) FROM prices p2 WHERE p2.ticker = p.ticker);
    """)
    con.commit()
    con.close()


def load_excel(df: pd.DataFrame, corr: pd.DataFrame, kpis: list[dict]):
    """Export a clean .xlsx, ready to import into Power BI."""
    print(f"[LOAD] exporting for Power BI → {XLSX_PATH.name}")
    with pd.ExcelWriter(XLSX_PATH, engine="openpyxl") as xl:
        cols = ["date", "ticker", "commodity", "open", "high", "low", "close",
                "volume", "ret_pct", "vol_21d", "drawdown", "pct_from_high",
                "ma50", "ma200", "risk_flag"]
        df[cols].to_excel(xl, sheet_name="Prices", index=False)
        corr.to_excel(xl, sheet_name="Correlation", index=False)
        pd.DataFrame(kpis).to_excel(xl, sheet_name="KPI_Snapshot", index=False)


def load_csv(df: pd.DataFrame, corr: pd.DataFrame, kpis: list[dict]):
    """Export flat CSVs consumed by the Power BI (PBIP) model.

    Plain text (unlike .xlsx) so the git diff is readable and Power Query can
    import each table with a simple Csv.Document step. Same columns as the
    Power BI sheets in load_excel.
    """
    print(f"[LOAD] exporting CSVs for Power BI → {CSV_PRICES.name}, "
          f"{CSV_CORR.name}, {CSV_KPI.name}")
    cols = ["date", "ticker", "commodity", "open", "high", "low", "close",
            "volume", "ret_pct", "vol_21d", "drawdown", "pct_from_high",
            "ma50", "ma200", "risk_flag"]
    df[cols].to_csv(CSV_PRICES, index=False, encoding="utf-8")
    corr.to_csv(CSV_CORR, index=False, encoding="utf-8")
    pd.DataFrame(kpis).to_csv(CSV_KPI, index=False, encoding="utf-8")


def load_json(df: pd.DataFrame, corr: pd.DataFrame, kpis: list[dict], frontier: dict):
    """Serialize the data consumed by the dashboard (SVG charts)."""
    print(f"[LOAD] exporting dashboard data → {JSON_PATH.name}")
    series = {}
    for ticker in COMMODITIES:
        g = df[df["ticker"] == ticker].sort_values("date")
        series[ticker] = {
            "dates": [str(d) for d in g["date"]],
            "close": [round(float(x), 2) for x in g["close"]],
            "vol_21d": [None if pd.isna(x) else round(float(x) * 100, 1) for x in g["vol_21d"]],
            "ma50": [None if pd.isna(x) else round(float(x), 2) for x in g["ma50"]],
            "ma200": [None if pd.isna(x) else round(float(x), 2) for x in g["ma200"]],
        }

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "vol_warn": VOL_WARN, "vol_breach": VOL_BREACH,
        "commodities": COMMODITIES,
        "kpis": kpis,
        "series": series,
        "frontier": frontier,
        "corr": {
            "dates": [str(d) for d in corr["date"]] if len(corr) else [],
            "values": [round(float(x), 3) for x in corr["corr_63d"]] if len(corr) else [],
        },
    }
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def main():
    print("=" * 64)
    print("  Market-risk pipeline — Coffee (KC) & Cotton (CT) ICE futures")
    print("=" * 64)
    df = extract("3y")
    df = transform(df)
    corr = correlation_series(df)
    kpis = build_kpis(df, corr)
    frontier = build_frontier(df)

    load_sqlite(df, corr, kpis)
    load_excel(df, corr, kpis)
    load_csv(df, corr, kpis)
    load_json(df, corr, kpis, frontier)

    print("\n" + "-" * 64)
    print("  SNAPSHOT (latest real session):")
    for k in kpis:
        print(f"   {k['commodity']:<18} {k['last_close']:>8.2f} {k['unit']:<7} "
              f"| Δday {k['day_change_pct']:+5.2f}% "
              f"| vol {k['vol_21d_annual_pct']}% p.a. "
              f"| risk {k['risk_flag']}")
    print("-" * 64)
    print("  Files written: data/commodities.db · data/commodities_powerbi.xlsx · "
          "data/*.csv · data/dashboard_data.json")
    print("  Next: python build_dashboard.py")
    print("=" * 64)


if __name__ == "__main__":
    main()
