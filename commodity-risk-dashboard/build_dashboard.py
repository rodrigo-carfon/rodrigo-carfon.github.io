# -*- coding: utf-8 -*-
"""
build_dashboard.py — render the published case study from data/dashboard_data.json.

The page is a *portfolio case study*: the search for the Markowitz efficient
frontier on two real ICE commodities — Arabica coffee (KC) and cotton (CT). It
leads with the pipeline that produces it, then walks from the two assets' realized
risk/return, through their near-zero correlation, to the risk×return frontier and
the diversification gain at the minimum-variance mix.

Output goes straight to ../projects/coffee-cotton-frontier/index.html — the public
URL, so there is a single source of truth and no copy step to forget. The page
pulls the site's shared stylesheet from /assets/css/style.css, so preview it over
an HTTP server rooted at the repo (python -m http.server), not as a file:// open.

Charts are pre-rendered as pure SVG — no JS, no chart library. Hover detail uses
native SVG <title> tooltips, and the frontier ships a <details> table twin for
anyone who can't read the colours.

Usage:
  python build_dashboard.py   (after running pipeline.py)
"""

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).parent
DATA = json.loads((HERE / "data" / "dashboard_data.json").read_text(encoding="utf-8"))

# Palette — mirrors /assets/css/style.css (the "instrument panel" system).
# One colour, one meaning:
#   teal  = the answer     (the efficient branch, the finding)
#   ink   = the one point being argued for (the min-variance marker)
#   each commodity keeps a hue of its own: coffee warm, cotton blue.
# Charts render on a light card (--chart-card) in both themes for legibility.
COL = {"KC=F": "#e0722e", "CT=F": "#2f6bed"}   # coffee, cotton
TEAL, TEAL_LT = "#0f9d8f", "#9ad9d0"           # efficient branch / dominated branch
TEAL_L, TEAL_D = "#dcf3f0", "#0b7d72"          # tints for the finding box
INK, INK_2 = "#171b24", "#4b5462"
MUTED, GRID, BG_CARD = "#79818f", "#dde1e8", "#ffffff"
SURFACE, SURFACE_2 = "#e7eaef", "#f4f6f9"

SANS_FF = "Inter, system-ui, sans-serif"
MONO_FF = "Geist Mono, ui-monospace, monospace"

SOURCE_URL = ("https://github.com/rodrigo-carfon/rodrigo-carfon.github.io"
              "/tree/master/commodity-risk-dashboard")


def _scale(vals, lo, hi, a, b):
    """Map val in [lo,hi] -> pixel in [a,b]."""
    if hi == lo:
        return [(a + b) / 2 for _ in vals]
    return [a + (v - lo) / (hi - lo) * (b - a) for v in vals]


def _fmt_date(s):
    """'2023-06-20' -> 'Jun/23'."""
    mon = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    try:
        y, m, _ = s.split("-")
        return f"{mon[int(m)-1]}/{y[2:]}"
    except Exception:
        return s


def line_chart(series, w=560, h=240, pad=38, threshold=None, dates=None, yrange=None, label=None):
    """series: list of {name,color,values}. values may contain None.
    dates: list of date strings aligned to the values, for X-axis labels.
    yrange: (lo, hi) to pin the Y scale (e.g. compare 2 panels on the same scale)."""
    plot_h = h - 2 * pad
    allv = [v for s in series for v in s["values"] if v is not None]
    if threshold:
        allv += [t["y"] for t in threshold]
    if not allv:
        return f'<svg width="{w}" height="{h}"></svg>'
    if yrange:
        lo, hi = yrange
    else:
        lo, hi = min(allv), max(allv)
        span = hi - lo or 1
        lo -= span * 0.06
        hi += span * 0.06

    yspan = hi - lo
    ydec = 0 if yspan >= 10 else (1 if yspan >= 1 else 2)

    aria = f' role="img" aria-label="{label}"' if label else ""
    parts = [f'<svg viewBox="0 0 {w} {h}" width="100%"{aria} '
             f'preserveAspectRatio="xMidYMid meet" font-family="{SANS_FF}">']
    # recessive hairline grid + Y ticks
    for i in range(5):
        gy = pad + plot_h * i / 4
        val = hi - (hi - lo) * i / 4
        parts.append(f'<line x1="{pad}" y1="{gy:.1f}" x2="{w-pad}" y2="{gy:.1f}" '
                     f'stroke="{GRID}" stroke-width="1"/>')
        parts.append(f'<text x="{pad-6}" y="{gy+3:.1f}" font-size="9" fill="{MUTED}" font-family="{MONO_FF}" '
                     f'text-anchor="end">{val:,.{ydec}f}</text>')
    # reference/threshold lines (dashed = threshold semantics, not grid)
    for t in (threshold or []):
        ty = _scale([t["y"]], lo, hi, h - pad, pad)[0]
        parts.append(f'<line x1="{pad}" y1="{ty:.1f}" x2="{w-pad}" y2="{ty:.1f}" '
                     f'stroke="{t["color"]}" stroke-width="1.3" stroke-dasharray="5 3"/>')
        parts.append(f'<text x="{w-pad-2}" y="{ty-3:.1f}" font-size="9" '
                     f'fill="{t["color"]}" text-anchor="end">{t["label"]}</text>')
    # series: 2px lines, round joins
    for s in series:
        vals = s["values"]
        n = len(vals)
        xs = _scale(list(range(n)), 0, n - 1, pad, w - pad)
        ys = _scale([0 if v is None else v for v in vals], lo, hi, h - pad, pad)
        d, pen = [], False
        for x, y, v in zip(xs, ys, vals):
            if v is None:
                pen = False
                continue
            d.append(f"{'M' if not pen else 'L'}{x:.1f} {y:.1f}")
            pen = True
        parts.append(f'<path d="{" ".join(d)}" fill="none" stroke="{s["color"]}" '
                     f'stroke-width="{s.get("width",2)}" stroke-linejoin="round" '
                     f'stroke-linecap="round"/>')
    # X axis: ~6 evenly spaced date labels
    if dates:
        n = len(dates)
        ticks = 6 if n >= 6 else n
        for i in range(ticks):
            idx = round(i * (n - 1) / (ticks - 1)) if ticks > 1 else 0
            tx = _scale([idx], 0, n - 1, pad, w - pad)[0]
            anchor = "start" if i == 0 else ("end" if i == ticks - 1 else "middle")
            parts.append(f'<line x1="{tx:.1f}" y1="{h-pad:.1f}" x2="{tx:.1f}" '
                         f'y2="{h-pad+4:.1f}" stroke="{MUTED}" stroke-width="1"/>')
            parts.append(f'<text x="{tx:.1f}" y="{h-pad+15:.1f}" font-size="9" '
                         f'fill="{MUTED}" font-family="{MONO_FF}" text-anchor="{anchor}">{_fmt_date(dates[idx])}</text>')
    parts.append('</svg>')
    return "".join(parts)


def frontier_chart(fr, w=1060, h=440, pad=60):
    """The centerpiece: risk × return frontier for a coffee+cotton portfolio.

    Highlights the *efficient frontier* (upper branch from the minimum-variance
    point) versus the dominated lower branch — the core Markowitz distinction.
    Every mix carries a native <title> tooltip (weights, risk, return).
    fr = DATA['frontier'] (assets, points, min_var, corr).
    """
    pts = fr["points"]
    mv = fr["min_var"]
    a = fr["assets"]
    xs_v = [p["risk"] for p in pts]
    ys_v = [p["ret"] for p in pts]
    xlo, xhi = min(xs_v), max(xs_v)
    ylo, yhi = min(ys_v + [0]), max(ys_v)
    xpad, ypad = (xhi - xlo) * 0.14 or 1, (yhi - ylo) * 0.16 or 1
    xlo, xhi = xlo - xpad, xhi + xpad
    ylo, yhi = ylo - ypad, yhi + ypad

    def X(v): return _scale([v], xlo, xhi, pad, w - pad)[0]
    def Y(v): return _scale([v], ylo, yhi, h - pad, pad)[0]

    parts = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" '
             f'aria-label="Risk-return frontier of coffee and cotton portfolios, '
             f'highlighting the efficient frontier and the minimum-variance mix" '
             f'preserveAspectRatio="xMidYMid meet" font-family="{SANS_FF}">']
    # recessive grid + axis ticks
    for i in range(5):
        gy = pad + (h - 2 * pad) * i / 4
        val = yhi - (yhi - ylo) * i / 4
        parts.append(f'<line x1="{pad}" y1="{gy:.1f}" x2="{w-pad}" y2="{gy:.1f}" stroke="{GRID}"/>')
        parts.append(f'<text x="{pad-8}" y="{gy+3:.1f}" font-size="10" fill="{MUTED}" font-family="{MONO_FF}" '
                     f'text-anchor="end">{val:.0f}%</text>')
        gx = pad + (w - 2 * pad) * i / 4
        xval = xlo + (xhi - xlo) * i / 4
        parts.append(f'<text x="{gx:.1f}" y="{h-pad+16:.1f}" font-size="10" fill="{MUTED}" font-family="{MONO_FF}" '
                     f'text-anchor="middle">{xval:.0f}%</text>')
    parts.append(f'<text x="{w/2:.0f}" y="{h-10}" font-size="11.5" fill="{INK}" '
                 f'text-anchor="middle" font-weight="600">Risk — annualized volatility (%)</text>')
    parts.append(f'<text x="16" y="{h/2:.0f}" font-size="11.5" fill="{INK}" font-weight="600" '
                 f'text-anchor="middle" transform="rotate(-90 16 {h/2:.0f})">Annualized return (%)</text>')

    # dominated (lower) branch — de-emphasized
    d_all = " ".join(f"{'M' if i==0 else 'L'}{X(p['risk']):.1f} {Y(p['ret']):.1f}"
                     for i, p in enumerate(pts))
    parts.append(f'<path d="{d_all}" fill="none" stroke="{TEAL_LT}" stroke-width="2" '
                 f'stroke-linejoin="round" stroke-linecap="round"/>')
    # efficient frontier — upper branch from the minimum-variance point
    eff = [mv] + [p for p in pts if p["ret"] > mv["ret"] + 1e-6]
    d_eff = " ".join(f"{'M' if i==0 else 'L'}{X(p['risk']):.1f} {Y(p['ret']):.1f}"
                     for i, p in enumerate(eff))
    parts.append(f'<path d="{d_eff}" fill="none" stroke="{TEAL}" stroke-width="3" '
                 f'stroke-linejoin="round" stroke-linecap="round"/>')

    # invisible wide hover targets along the curve → native tooltips, no JS
    for p in pts:
        tip = (f"{p['w_coffee']}% coffee / {100-p['w_coffee']}% cotton — "
               f"risk {p['risk']:.1f}% · return {p['ret']:.1f}%")
        parts.append(f'<circle cx="{X(p["risk"]):.1f}" cy="{Y(p["ret"]):.1f}" r="11" '
                     f'fill="#fff" fill-opacity="0"><title>{tip}</title></circle>')

    # annotation: "Efficient frontier" — ink text with a purple line-key beside it
    mid = eff[max(1, len(eff) // 2)]
    lx, ly = X(mid["risk"]) + 16, Y(mid["ret"])
    parts.append(f'<line x1="{lx:.1f}" y1="{ly-4:.1f}" x2="{lx+16:.1f}" y2="{ly-4:.1f}" '
                 f'stroke="{TEAL}" stroke-width="3" stroke-linecap="round"/>')
    parts.append(f'<text x="{lx+22:.1f}" y="{ly:.1f}" font-size="12" '
                 f'fill="{INK}" font-weight="700">Efficient frontier</text>')
    lowmid = pts[len(pts) // 10]
    parts.append(f'<text x="{X(lowmid["risk"])-8:.1f}" y="{Y(lowmid["ret"])+16:.1f}" font-size="10" '
                 f'fill="{MUTED}" text-anchor="end">dominated — same risk, less return</text>')

    # pure assets: ≥8px markers with a 2px surface ring; labels in ink/muted
    def dot(x, y, color, label, sub, tip, dy=-14, anchor="middle"):
        parts.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="7.5" fill="{color}" '
                     f'stroke="#fff" stroke-width="2"><title>{tip}</title></circle>')
        parts.append(f'<text x="{X(x):.1f}" y="{Y(y)+dy:.1f}" font-size="11.5" '
                     f'fill="{INK}" text-anchor="{anchor}" font-weight="700">{label}</text>')
        ody = dy + (13 if dy > 0 else -13)
        parts.append(f'<text x="{X(x):.1f}" y="{Y(y)+ody:.1f}" font-size="9.5" '
                     f'fill="{MUTED}" font-family="{MONO_FF}" text-anchor="{anchor}">{sub}</text>')
    dot(a["CT=F"]["risk"], a["CT=F"]["ret"], COL["CT=F"], "100% Cotton",
        f'{a["CT=F"]["ret"]:.1f}% ret · {a["CT=F"]["risk"]:.1f}% risk',
        f'Cotton alone — risk {a["CT=F"]["risk"]:.1f}% · return {a["CT=F"]["ret"]:.1f}%', dy=22)
    dot(a["KC=F"]["risk"], a["KC=F"]["ret"], COL["KC=F"], "100% Coffee",
        f'{a["KC=F"]["ret"]:.1f}% ret · {a["KC=F"]["risk"]:.1f}% risk',
        f'Coffee alone — risk {a["KC=F"]["risk"]:.1f}% · return {a["KC=F"]["ret"]:.1f}%', dy=-16)

    # minimum-variance portfolio (diamond) + guide to cotton's risk level
    mx, my = X(mv["risk"]), Y(mv["ret"])
    parts.append(f'<line x1="{X(a["CT=F"]["risk"]):.1f}" y1="{my:.1f}" x2="{mx:.1f}" y2="{my:.1f}" '
                 f'stroke="{INK}" stroke-width="1.2" stroke-dasharray="4 3" opacity="0.55"/>')
    tip_mv = (f"Minimum-variance mix — {mv['w_coffee']:.0f}% coffee / "
              f"{100-mv['w_coffee']:.0f}% cotton · risk {mv['risk']:.1f}% · return {mv['ret']:.1f}%")
    parts.append(f'<path d="M{mx:.1f} {my-9:.1f} L{mx+9:.1f} {my:.1f} '
                 f'L{mx:.1f} {my+9:.1f} L{mx-9:.1f} {my:.1f} Z" fill="{INK}" '
                 f'stroke="#fff" stroke-width="2"><title>{tip_mv}</title></path>')
    parts.append(f'<text x="{mx-14:.1f}" y="{my-14:.1f}" font-size="11.5" fill="{INK}" '
                 f'text-anchor="end" font-weight="700">Minimum-variance mix</text>')
    parts.append(f'<text x="{mx-14:.1f}" y="{my-1:.1f}" font-size="9.5" fill="{MUTED}" font-family="{MONO_FF}" '
                 f'text-anchor="end">{mv["w_coffee"]:.0f}% coffee · {mv["risk"]:.1f}% risk</text>')
    parts.append('</svg>')
    return "".join(parts)


def frontier_table(fr):
    """Collapsed table-view twin of the frontier chart (accessibility)."""
    rows = "".join(
        f"<tr><td>{p['w_coffee']}%</td><td>{100-p['w_coffee']}%</td>"
        f"<td>{p['risk']:.1f}%</td><td>{p['ret']:.1f}%</td></tr>"
        for p in fr["points"])
    return f"""
    <details class="tbl">
      <summary>View the frontier as a table</summary>
      <table>
        <thead><tr><th>Coffee</th><th>Cotton</th><th>Risk (vol p.a.)</th><th>Return p.a.</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </details>"""


def latest_sessions(n=10):
    """The last n trading sessions, straight from the series the pipeline just
    wrote. This is the freshness signal on the page: it changes on every run
    that picks up a new close, and it is read from the same source as every
    other number here, so it cannot disagree with them.

    Daily change is computed from consecutive closes (needs one extra prior
    close, so we slice n+1 and drop the oldest after differencing)."""
    kc, ct = DATA["series"]["KC=F"], DATA["series"]["CT=F"]
    dates = kc["dates"][-(n + 1):]
    kc_c = kc["close"][-(n + 1):]
    ct_c = ct["close"][-(n + 1):]

    def chg(cur, prev):
        if prev in (None, 0) or cur is None:
            return ""
        pct = (cur - prev) / prev * 100
        cls = "up" if pct >= 0 else "dn"
        return f'<span class="chg {cls}">{pct:+.2f}%</span>'

    rows = []
    for i in range(len(dates) - 1, 0, -1):   # newest first, skip the padding row
        rows.append(
            f"<tr><td class='dt'>{dates[i]}</td>"
            f"<td>{kc_c[i]:,.2f}</td><td>{chg(kc_c[i], kc_c[i-1])}</td>"
            f"<td>{ct_c[i]:,.2f}</td><td>{chg(ct_c[i], ct_c[i-1])}</td></tr>")

    return f"""
    <div>
      <div class="sessions-head">
        <h3>Latest {n} sessions</h3>
        <span class="sessions-note">closing prices in US¢/lb · regenerated on every pipeline run</span>
      </div>
      <div class="table-wrap">
        <table class="sessions-tbl">
          <thead><tr>
            <th class='dt'>date</th>
            <th>coffee (KC)</th><th>Δ</th>
            <th>cotton (CT)</th><th>Δ</th>
          </tr></thead>
          <tbody>{"".join(rows)}</tbody>
        </table>
      </div>
    </div>"""


def legend(items):
    sp = "".join(
        f'<span class="lg"><i style="background:{c}"></i>{n}</span>' for n, c in items)
    return f'<div class="legend">{sp}</div>'


def asset_tiles(fr):
    """The two ingredients + their correlation — the inputs to the frontier."""
    a = fr["assets"]
    kc, ct = a["KC=F"], a["CT=F"]
    return f"""
      <div class="atile">
        <div class="atile-h"><span class="dot" style="background:{COL['KC=F']}"></span>
          <b>Coffee (Arabica)</b><small>KC · ICE</small></div>
        <div class="atile-nums">
          <div><span>Return p.a.</span><b>{kc['ret']:.1f}%</b></div>
          <div><span>Risk (vol) p.a.</span><b>{kc['risk']:.1f}%</b></div>
        </div>
        <p class="atile-note">The higher-return, higher-risk asset — a sustained rally over the window, with the widest daily swings.</p>
      </div>
      <div class="atile">
        <div class="atile-h"><span class="dot" style="background:{COL['CT=F']}"></span>
          <b>Cotton (No.2)</b><small>CT · ICE</small></div>
        <div class="atile-nums">
          <div><span>Return p.a.</span><b>{ct['ret']:.1f}%</b></div>
          <div><span>Risk (vol) p.a.</span><b>{ct['risk']:.1f}%</b></div>
        </div>
        <p class="atile-note">Traded sideways: minimal return over the period, but the lower-volatility series.</p>
      </div>
      <div class="atile accent">
        <div class="atile-h"><span class="dot" style="background:{TEAL}"></span>
          <b>Correlation</b><small>daily returns</small></div>
        <div class="atile-big">{fr['corr']:.2f}</div>
        <p class="atile-note">Effectively zero — the two markets move independently. This is the
          condition under which diversification reduces portfolio risk.</p>
      </div>"""


def flow_strip():
    """The pipeline, compressed to one strip. Sits in the hero: the pipeline is the
    subject of this case study, and the frontier is what it produces."""
    return """
      <div class="flow">
        <span class="fbox">Yahoo Finance<small>ICE futures · KC=F / CT=F</small></span><span class="farr">→</span>
        <span class="fbox">Python ETL<small>extract · transform · load</small></span><span class="farr">→</span>
        <span class="fbox">SQLite · CSV · JSON<small>analytical store + exports</small></span><span class="farr">→</span>
        <span class="fbox">Power BI + this page<small>two delivery front-ends</small></span>
      </div>
      <div class="flow-note">Orchestrated by a scheduled GitHub Actions workflow — rerun after each ICE close, auto-commit, auto-deploy.</div>"""


def tools_section():
    """The toolchain behind the study — each tool with its concrete role here."""
    tools = [
        ("Python", "pandas · numpy · yfinance",
         "End-to-end ETL (<code>pipeline.py</code>): extracts 3 years of daily ICE futures, "
         "computes returns, annualized volatility, drawdown, rolling correlation and the "
         "closed-form minimum-variance weights; renders this page as pure SVG "
         "(<code>build_dashboard.py</code>)."),
        ("SQL · SQLite", "analytical store",
         "The pipeline loads prices, daily metrics and correlation into a relational store "
         "with an analytical view; <code>queries.sql</code> documents 10 production-style "
         "queries — joins, window functions, time aggregations, CASE logic."),
        ("Power BI", "star schema · DAX",
         "A versioned semantic model (PBIP/TMDL): <i>Prices</i> fact + <i>Calendar</i> "
         "dimension, fed by pipeline-generated CSVs, with the risk KPIs re-expressed as "
         "DAX measures — the same study, delivered through a BI tool."),
        ("GitHub Actions", "scheduled automation",
         "A cron workflow runs the pipeline after every ICE close (weekdays), commits the "
         "refreshed data and redeploys this page via GitHub Pages — the study refreshes with "
         "no server to maintain."),
    ]
    cards = "".join(
        f"""<div class="tool">
          <div class="tool-h"><b>{name}</b><small>{tag}</small></div>
          <p>{desc}</p>
        </div>""" for name, tag, desc in tools)
    return f'<div class="toolgrid">{cards}</div>'


def build():
    s = DATA["series"]
    fr = DATA["frontier"]
    a, mv = fr["assets"], fr["min_var"]
    ct_risk = a["CT=F"]["risk"]
    risk_cut = (ct_risk - mv["risk"]) / ct_risk * 100      # % risk reduction vs cotton alone
    ret_gain = mv["ret"] - a["CT=F"]["ret"]                 # extra return vs cotton alone (pp)

    # Supporting context: both prices on a shared ¢/lb scale — this is *why*
    # coffee shows high return+risk and cotton low+low on the frontier.
    price_vals = [v for t in ("KC=F", "CT=F") for v in s[t]["close"] if v is not None]
    p_lo, p_hi = min(price_vals), max(price_vals)
    p_span = p_hi - p_lo
    price_range = (max(0, p_lo - p_span * 0.06), p_hi + p_span * 0.06)
    price = line_chart([
        {"name": "Coffee", "color": COL["KC=F"], "values": s["KC=F"]["close"]},
        {"name": "Cotton", "color": COL["CT=F"], "values": s["CT=F"]["close"]},
    ], dates=s["KC=F"]["dates"], yrange=price_range,
       label="Coffee and cotton price paths on a shared cents-per-pound scale")
    corr = line_chart([
        {"name": "Correlation 63d", "color": TEAL, "values": DATA["corr"]["values"]},
    ], threshold=[{"y": 0, "color": MUTED, "label": "0"}], dates=DATA["corr"]["dates"],
       label="Rolling 63-day correlation of coffee and cotton daily returns, hovering near zero")

    frontier_svg = frontier_chart(fr)
    tiles = asset_tiles(fr)
    tools = tools_section()
    flow = flow_strip()
    table = frontier_table(fr)
    sessions = latest_sessions(10)
    d0, d1 = s["KC=F"]["dates"][0], s["KC=F"]["dates"][-1]
    leg_price = legend([("Coffee", COL["KC=F"]), ("Cotton", COL["CT=F"])])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Coffee &amp; Cotton — a market-risk pipeline that updates itself</title>
<meta name="author" content="Rodrigo Carvalho">
<meta name="description" content="A scheduled ETL pipeline — Yahoo Finance to Python to SQLite to Power BI — carrying a Markowitz efficient-frontier study on two real ICE commodities: Arabica coffee and cotton.">
<meta property="og:type" content="article">
<meta property="og:title" content="Coffee &amp; Cotton — a market-risk pipeline that updates itself">
<meta property="og:description" content="Two barely-correlated commodities, and the minimum-variance mix that beats the safe asset on both risk and return — on a pipeline that reruns itself after every ICE close.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Geist+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/css/style.css">
<style>
  /* Page-local only. Tokens, nav, footer, chips and type come from the shared sheet. */
  section {{ padding: 1.7rem 0; }}
  .hero {{ padding: 2.6rem 0 1.3rem; }}
  .container.wide {{ max-width: 1080px; }}
  h1 em {{ font-style: normal; color: var(--blue); }}
  .meta-line {{ font-family: var(--mono); font-size: 11.5px; color: var(--ink-3); letter-spacing: .02em; margin-top: 1.4rem; line-height: 1.7; }}

  /* numbered steps */
  .step {{ margin-bottom: 1.1rem; }}
  .step .n {{ display: inline-flex; align-items: center; justify-content: center; background: var(--blue); color: #fff; font-family: var(--mono); font-size: 11px; font-weight: 500; width: 21px; height: 21px; border-radius: 6px; margin-right: 10px; vertical-align: 2px; }}
  .step h2 {{ display: inline; }}
  .step .sub {{ color: var(--ink-3); font-size: 13.5px; line-height: 1.6; margin: .6rem 0 0 31px; max-width: 660px; }}

  /* asset tiles */
  .tiles {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: var(--gap); margin-top: 1rem; }}
  .atile {{ background: var(--tile); border: 1px solid var(--line); border-radius: var(--radius); padding: 1.1rem 1.2rem; box-shadow: var(--shadow); }}
  .atile.accent {{ background: var(--teal-l); border-color: color-mix(in srgb, var(--teal) 30%, var(--line)); }}
  .atile-h {{ display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 600; }}
  .atile-h small {{ color: var(--ink-3); font-size: 11px; font-weight: 400; margin-left: auto; font-family: var(--mono); }}
  .dot {{ width: 11px; height: 11px; border-radius: 50%; flex: none; }}
  .atile-nums {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px 14px; margin: 12px 0 8px; }}
  .atile-nums div {{ display: flex; flex-direction: column; }}
  .atile-nums span {{ color: var(--ink-3); font-size: 11px; }}
  .atile-nums b {{ font-family: var(--mono); font-size: 19px; font-weight: 500; font-variant-numeric: tabular-nums; }}
  .atile-big {{ font-family: var(--mono); font-size: 2.1rem; font-weight: 500; color: var(--teal); margin: 8px 0 4px; font-variant-numeric: tabular-nums; }}
  .atile-note {{ color: var(--ink-3); font-size: 11.5px; line-height: 1.45; }}

  /* chart panels — always a light card so the fixed-colour SVGs stay legible in dark mode */
  .panel {{ background: var(--chart-card); border: 1px solid var(--line); border-radius: var(--radius); padding: 1.1rem 1.2rem; box-shadow: var(--shadow); }}
  .panel.hero-panel {{ border-color: color-mix(in srgb, var(--teal) 28%, var(--line)); }}
  .panel h3.pt {{ font-size: 13.5px; margin-bottom: 2px; color: #171b24; }}
  .panel .cap {{ color: #79818f; font-size: 11.5px; margin-bottom: 8px; }}
  .panel table {{ color: #171b24; }}
  .panel th {{ background: #f4f6f9; color: #79818f; }}
  .panel th, .panel td {{ border-bottom-color: #eaedf1; }}
  .grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: var(--gap); }}
  .legend {{ display: flex; gap: 14px; margin: 2px 0 4px; flex-wrap: wrap; }}
  .lg {{ display: flex; align-items: center; gap: 5px; font-size: 11px; color: #79818f; font-family: var(--mono); }}
  .lg i {{ width: 12px; height: 3px; border-radius: 2px; display: inline-block; }}

  /* finding */
  .finding {{ background: var(--teal-l); border: 1px solid color-mix(in srgb, var(--teal) 30%, var(--line)); border-left: 4px solid var(--teal); border-radius: var(--radius); padding: 1.1rem 1.3rem; margin-top: var(--gap); }}
  .finding h3 {{ font-size: 15px; color: var(--teal-d); margin-bottom: 6px; }}
  .finding p {{ font-size: 13.5px; color: var(--ink-2); }}
  .finding .kpis {{ display: flex; gap: 22px; margin: 12px 0 2px; flex-wrap: wrap; }}
  .finding .kpis div {{ display: flex; flex-direction: column; }}
  .finding .kpis b {{ font-family: var(--mono); font-size: 22px; font-weight: 500; color: var(--teal-d); font-variant-numeric: tabular-nums; }}
  .finding .kpis span {{ font-size: 11px; color: var(--ink-3); }}

  /* frontier table */
  .tbl {{ margin-top: 10px; }}
  .tbl summary {{ cursor: pointer; color: var(--blue); font-family: var(--mono); font-size: 12px; }}
  .tbl table {{ margin-top: 8px; }}

  /* latest sessions */
  .sessions-head {{ display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }}
  .sessions-head h3 {{ font-size: 15px; margin: 0; }}
  .sessions-note {{ font-family: var(--mono); font-size: 11px; color: var(--ink-3); }}
  .sessions-tbl td {{ font-family: var(--mono); }}
  .sessions-tbl th.dt, .sessions-tbl td.dt {{ text-align: left; }}
  .sessions-tbl tbody tr:first-child td {{ font-weight: 500; background: var(--blue-l); }}
  .sessions-tbl .chg {{ font-size: 11.5px; }}
  .sessions-tbl .chg.up {{ color: var(--teal); }}
  .sessions-tbl .chg.dn {{ color: var(--chart-coffee); }}

  /* architecture strip */
  .flow {{ display: flex; align-items: stretch; gap: 8px; flex-wrap: wrap; margin: 1.6rem 0 0; }}
  .fbox {{ background: var(--tile); border: 1px solid var(--line); border-radius: 10px; padding: 9px 13px; font-size: 12.5px; font-weight: 600; display: flex; flex-direction: column; justify-content: center; box-shadow: var(--shadow); }}
  .fbox small {{ color: var(--ink-3); font-weight: 400; font-size: 10.5px; margin-top: 2px; font-family: var(--mono); }}
  .farr {{ align-self: center; color: var(--ink-3); font-size: 15px; }}
  .flow-note {{ color: var(--ink-3); font-size: 11.5px; margin-top: 10px; font-family: var(--mono); }}

  /* toolchain */
  .toolgrid {{ display: grid; grid-template-columns: 1fr 1fr; gap: var(--gap); margin-top: 1.4rem; }}
  .tool {{ background: var(--tile); border: 1px solid var(--line); border-radius: var(--radius); padding: 1rem 1.1rem; box-shadow: var(--shadow); }}
  .tool-h {{ display: flex; align-items: baseline; gap: 8px; margin-bottom: 6px; }}
  .tool-h b {{ font-size: 14px; font-weight: 600; color: var(--ink); }}
  .tool-h small {{ color: var(--ink-3); font-size: 11px; font-family: var(--mono); }}
  .tool p {{ font-size: 12.5px; color: var(--ink-2); line-height: 1.55; margin: 0; }}
  .tool code {{ font-family: var(--mono); background: var(--tile-2); border: 1px solid var(--line); border-radius: 4px; padding: 1px 5px; font-size: 11.5px; }}

  .method {{ background: var(--tile-2); border: 1px dashed var(--line); border-radius: var(--radius-sm); padding: 14px 16px; margin-top: 1.6rem; font-size: 12px; color: var(--ink-2); line-height: 1.6; }}
  .method b {{ color: var(--ink); }}

  @media (max-width: 820px) {{
    .tiles, .grid2, .toolgrid {{ grid-template-columns: 1fr; }}
    .flow {{ flex-direction: column; }}
    .farr {{ transform: rotate(90deg); align-self: flex-start; }}
  }}
</style>
</head>
<body>

<nav class="nav">
  <div class="nav-inner">
    <a class="nav-logo" href="/"><span>~/</span>rodrigo-carfon</a>
    <ul class="nav-links">
      <li><a href="#frontier">frontier</a></li>
      <li><a href="#build">how it's built</a></li>
      <li><a href="{SOURCE_URL}" class="nav-cta">source ↗</a></li>
    </ul>
  </div>
</nav>

<section class="hero">
  <div class="container">
    <div class="eyebrow">case study · scheduled etl pipeline</div>
    <h1>The efficient frontier of <em>coffee &amp; cotton</em>.</h1>
    <p class="lead" style="max-width:64ch">Harry Markowitz's insight (1952): a portfolio's risk is not the average of its
      parts — when assets barely move together, blending them cancels risk out. This study applies
      that lens to two real ICE commodities and locates the mix that minimizes risk. It runs on a
      pipeline built end to end for the study, which reruns after every market close.</p>
    {flow}
    <div class="chips" style="margin-top:1.6rem">
      <span class="chip">Python</span><span class="chip">pandas · numpy</span><span class="chip">SQL · SQLite</span><span class="chip">Power BI · DAX</span><span class="chip">GitHub Actions</span><span class="chip">pure-SVG dataviz</span>
    </div>
    <div class="meta-line">
      real data · ICE futures &nbsp;·&nbsp; coffee KC=F · cotton CT=F &nbsp;·&nbsp; {d0} → {d1}
      &nbsp;·&nbsp; last refresh {DATA['generated_at']}
    </div>
  </div>
</section>

<section id="latest">
  <div class="container">
    <div class="tile">{sessions}</div>
  </div>
</section>

<section>
  <div class="container">
    <div class="step"><span class="n">1</span><h2>The two assets</h2>
      <div class="sub">Realized over the period — annualized return and risk (volatility), plus how much they co-move.</div>
    </div>
    <div class="tiles">{tiles}</div>
  </div>
</section>

<section id="frontier">
  <div class="container wide">
    <div class="step"><span class="n">2</span><h2>Every possible mix — the risk × return frontier</h2>
      <div class="sub">Each point on the curve is a coffee/cotton blend, from 0% to 100% coffee
        (hover any point for its exact mix). The curve bends left: combining the two reaches lower
        risk than either asset alone.</div>
    </div>
    <div class="panel hero-panel">
      {frontier_svg}
      {table}
    </div>

    <div class="finding">
      <h3>Finding — the diversification gain</h3>
      <div class="kpis">
        <div><b>{mv['w_coffee']:.0f}% / {100-mv['w_coffee']:.0f}%</b><span>coffee / cotton (min-variance mix)</span></div>
        <div><b>{mv['risk']:.1f}%</b><span>portfolio risk (vs {ct_risk:.1f}% cotton alone)</span></div>
        <div><b>−{risk_cut:.0f}%</b><span>lower risk than cotton alone</span></div>
        <div><b>+{ret_gain:.1f} pp</b><span>more return than cotton alone</span></div>
      </div>
      <p>Holding <b>{mv['w_coffee']:.0f}% coffee and {100-mv['w_coffee']:.0f}% cotton</b> carries
        <b>{mv['risk']:.1f}%</b> risk — <b>below cotton on its own ({ct_risk:.1f}%)</b> — while returning
        <b>{mv['ret']:.1f}%</b> versus cotton's {a['CT=F']['ret']:.1f}%. Adding a slice of the <i>riskier</i>
        asset made the portfolio both safer and more profitable than the safe asset alone: because the two
        barely correlate ({fr['corr']:.2f}), their day-to-day shocks offset. That is diversification,
        quantified on real market data.</p>
    </div>
  </div>
</section>

<section>
  <div class="container">
    <div class="step"><span class="n">3</span><h2>Why the inputs look the way they do</h2>
      <div class="sub">The two series behind the frontier: the price paths that set each asset's
        return &amp; risk, and the rolling correlation that keeps them independent.</div>
    </div>
    <div class="grid2">
      <div class="panel">
        <h3 class="pt">Price paths — coffee vs cotton (shared US¢/lb scale)</h3>
        <div class="cap">Coffee's rally drives its high return and high risk; cotton stays flat and low-volatility.</div>
        {leg_price}{price}
      </div>
      <div class="panel">
        <h3 class="pt">Rolling 63-day correlation of daily returns</h3>
        <div class="cap">Hovers near zero throughout — the diversification assumption holds over time.</div>
        {corr}
      </div>
    </div>
  </div>
</section>

<section id="build">
  <div class="container">
    <div class="step"><span class="n">4</span><h2>How this study was built</h2>
      <div class="sub">A production-shaped data pipeline: automated capture, a relational store, and
        two delivery front-ends from the same data.</div>
    </div>
    {tools}

    <div class="method">
      <b>Method.</b> Annualized return = mean daily return × 252; risk = standard deviation of daily
      returns × √252; ρ = realized correlation of the two daily-return series. The frontier sweeps the
      coffee weight from 0→100% using the two-asset portfolio variance with the real ρ; the
      <b>minimum-variance weight</b> is the closed-form two-asset solution. The <b>efficient frontier</b>
      is the branch above that point — every mix below it is dominated (same risk, less return).
      All figures computed from real ICE futures prices (Yahoo Finance). Educational study — not
      investment advice.
    </div>
  </div>
</section>

<footer class="footer">
  <div class="footer-inner">
    <p>Rodrigo Carvalho · Data &amp; Analytics Engineering</p>
    <p>
      <a href="/">← back to portfolio</a> ·
      <a href="{SOURCE_URL}">source code</a>
    </p>
  </div>
</footer>

</body>
</html>"""

    out = HERE.parent / "projects" / "coffee-cotton-frontier" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"  ✓ {out.relative_to(HERE.parent)} generated ({len(html):,} bytes)")


if __name__ == "__main__":
    build()
