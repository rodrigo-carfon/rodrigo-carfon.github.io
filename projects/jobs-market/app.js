/* Job-Market Explorer — client-side dashboard over the columnar data.json.
   No framework, no chart library. Decodes the dictionary-encoded payload once,
   filters by walking an integer index array, and redraws KPIs + hand-drawn bar/
   line charts + a paginated list on every filter change. */
(function () {
  "use strict";
  var D, J, N, GEN;                 // dict, columns, count, generated date
  var searchable = [];             // per-row lowercased "title company"
  var FACETS = ["source", "area", "seniority", "work_model", "market"];
  var filters = { q: "", recency: null };
  FACETS.forEach(function (f) { filters[f] = new Set(); });   // sets of dict indices
  var sortKey = "recent";
  var page = 0, PAGE = 40;
  var filtered = [];

  var $ = function (id) { return document.getElementById(id); };
  var esc = function (s) { return (s || "").replace(/[&<>"]/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
  var daysAgo = function (n) { var d = new Date(GEN); d.setDate(d.getDate() - n);
    return d.toISOString().slice(0, 10); };

  // ── boot ──────────────────────────────────────────────────────────────
  fetch("data.json").then(function (r) { return r.json(); }).then(function (data) {
    D = data.dict; J = data.jobs; N = data.count; GEN = data.generated;
    for (var i = 0; i < N; i++) {
      searchable[i] = (J.title[i] + " " + D.company[J.cmp[i]]).toLowerCase();
    }
    buildFacetChips();
    buildRecencyChips();
    wire();
    var base = data.total_base || N, win = data.total_window || N;
    var shown = (N < win)
      ? N.toLocaleString("pt-BR") + " mais recentes de " + win.toLocaleString("pt-BR") + " na janela de " + data.window_days + " dias"
      : N.toLocaleString("pt-BR") + " vagas na janela de " + data.window_days + " dias";
    $("meta").textContent = "atualizado em " + GEN + " · " + shown +
      " · base de " + base.toLocaleString("pt-BR") + " vagas · pipeline diário (GitHub Actions)";
    $("loading").style.display = "none";
    $("app").style.display = "block";
    apply();
  }).catch(function (e) {
    $("loading").textContent = "Não foi possível carregar a base (data.json). " + e;
  });

  // ── facet chips (static counts over the full dataset) ─────────────────
  var COLKEY = { source: "src", area: "area", seniority: "sen", work_model: "wm", market: "mk" };
  function buildFacetChips() {
    FACETS.forEach(function (facet) {
      var col = J[COLKEY[facet]], counts = {};
      for (var i = 0; i < N; i++) counts[col[i]] = (counts[col[i]] || 0) + 1;
      var order = Object.keys(counts).map(Number).sort(function (a, b) { return counts[b] - counts[a]; });
      var host = $("f-" + facet);
      order.forEach(function (di) {
        var label = D[facet][di] || "n/d";
        var chip = document.createElement("span");
        chip.className = "fchip";
        chip.innerHTML = esc(label) + '<span class="c">' + counts[di] + "</span>";
        chip.onclick = function () {
          if (filters[facet].has(di)) { filters[facet].delete(di); chip.classList.remove("on"); }
          else { filters[facet].add(di); chip.classList.add("on"); }
          page = 0; apply();
        };
        host.appendChild(chip);
      });
    });
  }

  function buildRecencyChips() {
    var opts = [["Todas", null], ["Hoje", 0], ["7 dias", 7], ["30 dias", 30]];
    var host = $("f-recency");
    opts.forEach(function (o, idx) {
      var chip = document.createElement("span");
      chip.className = "fchip" + (idx === 0 ? " on" : "");
      chip.textContent = o[0];
      chip.onclick = function () {
        filters.recency = o[1];
        [].forEach.call(host.children, function (c) { c.classList.remove("on"); });
        chip.classList.add("on"); page = 0; apply();
      };
      host.appendChild(chip);
    });
  }

  function wire() {
    var t;
    $("q").addEventListener("input", function (e) {
      clearTimeout(t); t = setTimeout(function () {
        filters.q = e.target.value.trim().toLowerCase(); page = 0; apply();
      }, 150);
    });
    $("sort").addEventListener("change", function (e) { sortKey = e.target.value; page = 0; render(); });
    $("clear").addEventListener("click", function () {
      filters.q = ""; filters.recency = null; $("q").value = "";
      FACETS.forEach(function (f) { filters[f].clear(); });
      document.querySelectorAll(".fchips .fchip.on").forEach(function (c) { c.classList.remove("on"); });
      [].forEach.call($("f-recency").children, function (c, i) { c.classList.toggle("on", i === 0); });
      page = 0; apply();
    });
    $("prev").addEventListener("click", function () { if (page > 0) { page--; render(); scrollTop(); } });
    $("next").addEventListener("click", function () {
      if ((page + 1) * PAGE < filtered.length) { page++; render(); scrollTop(); } });
  }
  function scrollTop() { $("results").scrollIntoView({ behavior: "smooth", block: "start" }); }

  // ── filter → filtered index array ─────────────────────────────────────
  function apply() {
    var cutoff = filters.recency == null ? null : daysAgo(filters.recency);
    var q = filters.q, fs = filters;
    filtered = [];
    for (var i = 0; i < N; i++) {
      if (fs.source.size && !fs.source.has(J.src[i])) continue;
      if (fs.area.size && !fs.area.has(J.area[i])) continue;
      if (fs.seniority.size && !fs.seniority.has(J.sen[i])) continue;
      if (fs.work_model.size && !fs.work_model.has(J.wm[i])) continue;
      if (fs.market.size && !fs.market.has(J.mk[i])) continue;
      if (cutoff && (J.pub[i] || J.seen[i]) < cutoff) continue;   // by publication date
      if (q && searchable[i].indexOf(q) === -1) continue;
      filtered.push(i);
    }
    $("fcount").textContent = filtered.length.toLocaleString("pt-BR");
    renderKpis(); renderCharts(); render();
  }

  // ── KPIs ──────────────────────────────────────────────────────────────
  function renderKpis() {
    var d7 = daysAgo(7), comp = new Set(), area = new Set(), src = new Set(), n1 = 0, n7 = 0;
    for (var k = 0; k < filtered.length; k++) {
      var i = filtered[k];
      comp.add(J.cmp[i]); area.add(J.area[i]); src.add(J.src[i]);
      if (J.seen[i] === GEN) n1++;
      if (J.seen[i] >= d7) n7++;
    }
    $("k-total").textContent = filtered.length.toLocaleString("pt-BR");
    $("k-new1").textContent = n1.toLocaleString("pt-BR");
    $("k-new7").textContent = n7.toLocaleString("pt-BR");
    $("k-portals").textContent = src.size;
    $("k-companies").textContent = comp.size.toLocaleString("pt-BR");
    $("k-areas").textContent = area.size;
  }

  // ── charts (aggregate over the filtered set) ──────────────────────────
  function tally(colKey, dictKey) {
    var col = J[colKey], m = {};
    for (var k = 0; k < filtered.length; k++) { var v = col[filtered[k]]; m[v] = (m[v] || 0) + 1; }
    return Object.keys(m).map(function (di) { return [D[dictKey][+di] || "n/d", m[di]]; })
      .sort(function (a, b) { return b[1] - a[1]; });
  }
  function renderCharts() {
    bars($("c-area"), tally("area", "area"), 11);
    bars($("c-seniority"), tally("sen", "seniority"), 8, true);
    bars($("c-source"), tally("src", "source"), 9);
    companyBars();
    timeline();
    salary();
  }
  function bars(host, entries, topN, teal) {
    entries = entries.slice(0, topN);
    if (!entries.length) { host.innerHTML = '<div class="chart-empty">sem dados</div>'; return; }
    var max = entries[0][1];
    host.innerHTML = entries.map(function (e) {
      var pct = Math.max(2, e[1] / max * 100);
      return '<div class="bar-row"><span class="lab" title="' + esc(e[0]) + '">' + esc(e[0]) +
        '</span><div class="bar-track"><div class="bar-fill' + (teal ? " teal" : "") +
        '" style="width:' + pct + '%"></div></div><span class="val">' +
        e[1].toLocaleString("pt-BR") + "</span></div>";
    }).join("");
  }
  function companyBars() {
    var m = {};
    for (var k = 0; k < filtered.length; k++) { var c = J.cmp[filtered[k]]; m[c] = (m[c] || 0) + 1; }
    var entries = Object.keys(m).map(function (di) { return [D.company[+di] || "?", m[di]]; })
      .filter(function (e) { return e[0] && e[0] !== "?"; })
      .sort(function (a, b) { return b[1] - a[1]; });
    bars($("c-company"), entries, 15);
  }

  function timeline() {
    var host = $("c-timeline"), m = {};
    for (var k = 0; k < filtered.length; k++) { var d = J.seen[filtered[k]]; if (d) m[d] = (m[d] || 0) + 1; }
    var days = Object.keys(m).sort();
    if (days.length < 2) { host.innerHTML = '<div class="chart-empty">poucos dias para uma série</div>'; return; }
    var W = 300, H = 120, P = 22, max = Math.max.apply(null, days.map(function (d) { return m[d]; }));
    var X = function (i) { return P + i / (days.length - 1) * (W - 2 * P); };
    var Y = function (v) { return H - P - v / max * (H - 2 * P); };
    var pts = days.map(function (d, i) { return X(i).toFixed(1) + "," + Y(m[d]).toFixed(1); });
    var area = "M" + X(0).toFixed(1) + "," + (H - P) + " L" + pts.join(" L") + " L" + X(days.length - 1).toFixed(1) + "," + (H - P) + " Z";
    host.innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '" width="100%" font-family="Geist Mono, monospace">' +
      '<path d="' + area + '" fill="var(--blue)" fill-opacity="0.10"/>' +
      '<polyline points="' + pts.join(" ") + '" fill="none" stroke="var(--blue)" stroke-width="2" stroke-linejoin="round"/>' +
      '<text x="' + P + '" y="' + (H - 4) + '" font-size="9" fill="var(--ink-3)">' + days[0].slice(5) + '</text>' +
      '<text x="' + (W - P) + '" y="' + (H - 4) + '" font-size="9" fill="var(--ink-3)" text-anchor="end">' + days[days.length - 1].slice(5) + '</text>' +
      '<text x="' + P + '" y="14" font-size="9" fill="var(--ink-3)">pico ' + max + '/dia</text></svg>';
  }

  function salary() {
    var host = $("c-salary"), vals = [];
    for (var k = 0; k < filtered.length; k++) {
      var i = filtered[k], v = J.smax[i] || J.smin[i];
      if (v && v > 0) vals.push(v);
    }
    if (vals.length < 8) { host.innerHTML = '<div class="chart-empty">salário informado em ' + vals.length + ' vaga(s) do recorte — poucos para um histograma</div>'; return; }
    vals.sort(function (a, b) { return a - b; });
    var lo = vals[0], hi = vals[Math.floor(vals.length * 0.95)], nb = 8, step = (hi - lo) / nb || 1;
    var buckets = new Array(nb).fill(0);
    vals.forEach(function (v) { var b = Math.min(nb - 1, Math.floor((v - lo) / step)); buckets[b]++; });
    var fmt = function (n) { return n >= 1000 ? (n / 1000).toFixed(0) + "k" : n.toFixed(0); };
    var entries = buckets.map(function (c, b) { return [fmt(lo + b * step) + "–" + fmt(lo + (b + 1) * step), c]; });
    bars(host, entries, nb, true);
  }

  // ── results list ──────────────────────────────────────────────────────
  function sortIdx(arr) {
    var a = arr.slice();
    if (sortKey === "salary") a.sort(function (x, y) { return (J.smax[y] || J.smin[y] || 0) - (J.smax[x] || J.smin[x] || 0); });
    else if (sortKey === "portals") a.sort(function (x, y) { return J.np[y] - J.np[x]; });
    else if (sortKey === "company") a.sort(function (x, y) { return (D.company[J.cmp[x]] || "").localeCompare(D.company[J.cmp[y]] || ""); });
    // "recent" keeps the data's first_seen-desc order
    return a;
  }
  function render() {
    var idx = sortIdx(filtered);
    var start = page * PAGE, slice = idx.slice(start, start + PAGE);
    $("list").innerHTML = slice.map(row).join("") ||
      '<div class="chart-empty">nenhuma vaga corresponde aos filtros.</div>';
    var pages = Math.max(1, Math.ceil(filtered.length / PAGE));
    $("pinfo").textContent = "página " + (page + 1) + " de " + pages.toLocaleString("pt-BR");
    $("prev").disabled = page === 0;
    $("next").disabled = (page + 1) * PAGE >= filtered.length;
  }
  function row(i) {
    var sal = "";
    if (J.smax[i] || J.smin[i]) {
      var cur = "US$"; // remoteok salaries are USD
      sal = '<div class="sal">' + cur + " " + (J.smin[i] || 0).toLocaleString("pt-BR") +
        (J.smax[i] ? "–" + J.smax[i].toLocaleString("pt-BR") : "") + "</div>";
    }
    var loc = J.city[i] ? esc(J.city[i]) : (D.country[J.co[i]] ? esc(D.country[J.co[i]].slice(0, 22)) : "");
    var np = J.np[i] > 1 ? '<span class="badge np">' + J.np[i] + " portais</span>" : "";
    return '<div class="job"><div class="job-main">' +
      '<div class="t"><a href="' + esc(J.url[i]) + '" target="_blank" rel="noopener">' + esc(J.title[i]) + "</a></div>" +
      '<div class="co">' + esc(D.company[J.cmp[i]]) + (loc ? " · " + loc : "") + "</div>" +
      '<div class="job-meta"><span class="badge src">' + esc(D.source[J.src[i]]) + "</span>" +
      '<span class="badge">' + esc(D.area[J.area[i]]) + "</span>" +
      '<span class="badge">' + esc(D.seniority[J.sen[i]]) + "</span>" +
      (D.work_model[J.wm[i]] ? '<span class="badge">' + esc(D.work_model[J.wm[i]]) + "</span>" : "") + np + "</div></div>" +
      '<div class="job-side">' + (J.pub[i] || J.seen[i]) + sal + "</div></div>";
  }
})();
