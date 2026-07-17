# rodrigo-carfon.github.io

Source for my portfolio — **[rodrigo-carfon.github.io](https://rodrigo-carfon.github.io)**.

A Jekyll home page plus two standalone case studies, all sharing one stylesheet.

## Layout

```
_config.yml                       # Jekyll config (jekyll-seo-tag only)
_layouts/default.html             # shell for the home: nav, fonts, footer
index.html                        # the home page
assets/css/style.css              # the design system — every page links this one file

projects/
├── maplead/index.html            # case study — hand-written
└── coffee-cotton-frontier/       # case study — GENERATED, do not hand-edit
    └── index.html                #   rendered by commodity-risk-dashboard/build_dashboard.py

commodity-risk-dashboard/         # the ETL behind the coffee & cotton study
.github/workflows/                # the cron that reruns it after each ICE close
pdf/                              # redirect stubs for the old URLs
```

Two things worth knowing before editing:

- **`projects/coffee-cotton-frontier/index.html` is generated.** Hand-edits are overwritten the
  next time the pipeline runs. Change [`commodity-risk-dashboard/build_dashboard.py`](commodity-risk-dashboard/build_dashboard.py)
  instead — including the chart colours, which are constants at the top of that file.
- **The project pages carry no Jekyll front matter**, deliberately: they contain zero Liquid, so
  a plain static server renders them byte-identically to production, and previewing needs no Ruby.

## Running it locally

The project pages and the stylesheet need nothing but a static server:

```bash
python -m http.server 8000      # from the repo root
# → localhost:8000/projects/maplead/
# → localhost:8000/projects/coffee-cotton-frontier/
```

The home page is the only file with Liquid in it, so it needs Jekyll to render. There is no
Gemfile here — GitHub Pages builds it on push. To preview it locally, install Ruby 3.1 with
DevKit and add a Gemfile with `github-pages` and `webrick`.

To rebuild the coffee & cotton study, see
[`commodity-risk-dashboard/README.md`](commodity-risk-dashboard/README.md).

## The stack

Jekyll on GitHub Pages · plain CSS, no framework · DM Sans / DM Mono · charts pre-rendered as
pure SVG from Python, no chart library.

---

The home page started from [evanca/quick-portfolio](https://github.com/evanca/quick-portfolio)
(Minimal theme, CC0); none of its markup or styling remains.
