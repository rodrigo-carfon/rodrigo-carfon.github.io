<style>
  .intro {
    color: #555;
    font-size: 15px;
    max-width: 620px;
    margin-bottom: 2.2rem;
    line-height: 1.65;
  }
  .section-label {
    font-size: 12px;
    font-weight: 600;
    letter-spacing: .1em;
    text-transform: uppercase;
    color: #888;
    margin: 0 0 1.2rem;
  }
  .project-card {
    border: 1px solid #e4e2dc;
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 2.2rem;
    background: #fff;
    box-shadow: 0 1px 3px rgba(0,0,0,.05);
    transition: box-shadow .2s ease, transform .2s ease;
  }
  .project-card:hover {
    box-shadow: 0 6px 18px rgba(0,0,0,.09);
    transform: translateY(-2px);
  }
  .project-card a.thumb { display: block; line-height: 0; }
  .project-card img {
    width: 100%;
    height: auto;
    display: block;
    border-bottom: 1px solid #eee;
  }
  .project-body { padding: 1.1rem 1.25rem 1.25rem; }
  .project-body h3 {
    margin: 0 0 .45rem;
    font-size: 18px;
  }
  .project-body h3 a { color: #222; text-decoration: none; }
  .project-body h3 a:hover { color: #267CB9; }
  .project-body p {
    margin: 0 0 .8rem;
    color: #555;
    font-size: 14px;
    line-height: 1.6;
  }
  .tags { margin: 0 0 .9rem; }
  .tag {
    display: inline-block;
    font-size: 11px;
    font-weight: 600;
    color: #444;
    background: #f2f1ee;
    border: 1px solid #e4e2dc;
    border-radius: 6px;
    padding: 2px 8px;
    margin: 0 4px 4px 0;
  }
  .view-link {
    font-size: 13px;
    font-weight: 600;
    text-decoration: none;
  }
</style>

<p class="intro">
  Selected projects combining data engineering, automation, and analytics —
  from web scraping pipelines to quantitative finance studies. Each one is a
  live, clickable case study.
</p>

<p class="section-label">Crawlers &amp; Automation</p>

<div class="project-card">
  <a class="thumb" href="/pdf/maplead_en.html">
    <img src="images/maplead.png?raw=true" alt="MapLead — local business scraper dashboard" />
  </a>
  <div class="project-body">
    <h3><a href="/pdf/maplead_en.html">MapLead — Local Business Scraper</a></h3>
    <p>
      Turns a plain search — a business category and a city — into a scored, enriched
      prospect list. Queries Google Maps, scores each business's digital presence, and
      detects the marketing pixels they run (Meta, Google, TikTok and more).
    </p>
    <div class="tags">
      <span class="tag">Python</span>
      <span class="tag">Web Scraping</span>
      <span class="tag">n8n</span>
      <span class="tag">Lead Generation</span>
    </div>
    <a class="view-link" href="/pdf/maplead_en.html">View project →</a>
  </div>
</div>

<p class="section-label">Data Science &amp; Finance</p>

<div class="project-card">
  <a class="thumb" href="/pdf/index.html">
    <img src="images/COFFE.png?raw=true" alt="Efficient frontier study of coffee and cotton" />
  </a>
  <div class="project-body">
    <h3><a href="/pdf/index.html">Portfolio Optimization — Coffee &amp; Cotton</a></h3>
    <p>
      A Markowitz efficient-frontier case study on two real ICE commodities — Arabica
      coffee and cotton — finding the minimum-variance mix, built end to end on an
      automated Python → SQL → Power BI data pipeline.
    </p>
    <div class="tags">
      <span class="tag">Python</span>
      <span class="tag">SQL</span>
      <span class="tag">Power BI</span>
      <span class="tag">Quant Finance</span>
    </div>
    <a class="view-link" href="/pdf/index.html">View project →</a>
  </div>
</div>
