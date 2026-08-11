/* Florescer de Gaia — comportamento da loja
   Depende de products.js (LOJA, CATEGORIAS, PRODUTOS). */

(function () {
  "use strict";

  var $  = function (sel, ctx) { return (ctx || document).querySelector(sel); };
  var $$ = function (sel, ctx) { return Array.prototype.slice.call((ctx || document).querySelectorAll(sel)); };

  var STORAGE = "fdg-carrinho";
  var carrinho = carregarCarrinho();
  var filtroAtual = "todos";
  var produtoAberto = null;
  var variacaoEscolhida = null;
  var quantidade = 1;

  /* ---------- utilidades ---------- */

  function formatarPreco(valor) {
    if (valor === null || valor === undefined) return null;
    return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }

  function precoHTML(valor) {
    var f = formatarPreco(valor);
    return f
      ? '<span class="price">' + f + "</span>"
      : '<span class="price-open">Sob consulta</span>';
  }

  function acharProduto(id) {
    return PRODUTOS.filter(function (p) { return p.id === id; })[0];
  }

  function nomeCategoria(slug) {
    var c = CATEGORIAS.filter(function (x) { return x.slug === slug; })[0];
    return c ? c.nome : slug;
  }

  function escapar(txt) {
    return String(txt).replace(/[&<>"]/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch];
    });
  }

  /* ---------- carrinho ---------- */

  function carregarCarrinho() {
    try {
      var bruto = localStorage.getItem(STORAGE);
      return bruto ? JSON.parse(bruto) : [];
    } catch (e) { return []; }
  }

  function salvarCarrinho() {
    try { localStorage.setItem(STORAGE, JSON.stringify(carrinho)); } catch (e) {}
  }

  function chaveItem(id, variacao) { return id + "::" + (variacao || ""); }

  function adicionar(id, variacao, qtd) {
    var chave = chaveItem(id, variacao);
    var existente = carrinho.filter(function (i) { return i.chave === chave; })[0];
    if (existente) {
      existente.qtd += qtd;
    } else {
      carrinho.push({ chave: chave, id: id, variacao: variacao || null, qtd: qtd });
    }
    salvarCarrinho();
    renderCarrinho();
    abrirDrawer();
  }

  function remover(chave) {
    carrinho = carrinho.filter(function (i) { return i.chave !== chave; });
    salvarCarrinho();
    renderCarrinho();
  }

  function totalItens() {
    return carrinho.reduce(function (s, i) { return s + i.qtd; }, 0);
  }

  function totalizar() {
    var soma = 0;
    var temAberto = false;
    carrinho.forEach(function (item) {
      var p = acharProduto(item.id);
      if (!p) return;
      if (p.preco === null || p.preco === undefined) temAberto = true;
      else soma += p.preco * item.qtd;
    });
    return { soma: soma, temAberto: temAberto };
  }

  /* ---------- render: filtros e grade ---------- */

  function renderFiltros() {
    var alvo = $("#filtros");
    alvo.innerHTML = CATEGORIAS.map(function (c) {
      var ativo = c.slug === filtroAtual;
      return '<button class="chip" data-cat="' + c.slug + '" aria-pressed="' + ativo + '">' +
             escapar(c.nome) + "</button>";
    }).join("") + '<span class="filters-count" id="contador"></span>';

    $$("#filtros .chip").forEach(function (btn) {
      btn.addEventListener("click", function () {
        filtroAtual = btn.dataset.cat;
        renderFiltros();
        renderGrade();
      });
    });
  }

  function renderGrade() {
    var lista = filtroAtual === "todos"
      ? PRODUTOS
      : PRODUTOS.filter(function (p) { return p.categoria === filtroAtual; });

    $("#contador").textContent = lista.length + (lista.length === 1 ? " produto" : " produtos");

    $("#grade").innerHTML = lista.map(function (p) {
      var selos = [];
      if (p.destaque) selos.push('<span class="badge badge-gold">Destaque</span>');
      if (p.sobEncomenda) selos.push('<span class="badge badge-rose">Sob encomenda</span>');
      if (p.estoque === false) selos.push('<span class="badge">Esgotado</span>');

      var pend = (p.pendencias || []).length;

      return '' +
        '<article class="card">' +
          '<button class="card-media" data-abrir="' + p.id + '" data-pend="' + pend + '" aria-label="Ver ' + escapar(p.nome) + '">' +
            '<img src="' + p.imagem + '" alt="' + escapar(p.nome) + '" loading="lazy">' +
            (selos.length ? '<span class="card-badges">' + selos.join("") + "</span>" : "") +
            '<span class="card-view">Ver produto</span>' +
          "</button>" +
          '<p class="card-cat">' + escapar(nomeCategoria(p.categoria)) + "</p>" +
          '<h3 class="card-name">' + escapar(p.nome) + "</h3>" +
          '<p class="card-resumo">' + escapar(p.resumo) + "</p>" +
          '<div class="card-foot">' +
            precoHTML(p.preco) +
            '<button class="card-add" data-abrir="' + p.id + '">' +
              (p.sobEncomenda ? "Orçar" : "Adicionar") +
            "</button>" +
          "</div>" +
        "</article>";
    }).join("");

    $$("[data-abrir]").forEach(function (el) {
      el.addEventListener("click", function () { abrirProduto(el.dataset.abrir); });
    });
  }

  /* ---------- modal de produto ---------- */

  function abrirProduto(id) {
    var p = acharProduto(id);
    if (!p) return;

    produtoAberto = p;
    quantidade = 1;
    variacaoEscolhida = (p.variacoes && p.variacoes.length) ? p.variacoes[0] : null;

    var galeria = [p.imagem].concat(p.imagensExtras || []);

    var htmlVariacoes = (p.variacoes && p.variacoes.length)
      ? '<div class="field">' +
          '<span class="field-label">Versão</span>' +
          '<div class="opts" id="opcoes">' +
            p.variacoes.map(function (v, i) {
              return '<button class="opt" data-var="' + escapar(v) + '" aria-pressed="' + (i === 0) + '">' + escapar(v) + "</button>";
            }).join("") +
          "</div>" +
        "</div>"
      : "";

    var htmlPendencias = (p.pendencias && p.pendencias.length)
      ? '<div class="rev-box rev-only"><strong>Falta definir</strong><ul>' +
          p.pendencias.map(function (x) { return "<li>" + escapar(x) + "</li>"; }).join("") +
        "</ul></div>"
      : "";

    $("#modal").innerHTML = '' +
      '<button class="modal-close" data-fechar aria-label="Fechar">&times;</button>' +
      '<div class="modal-grid">' +
        '<div class="modal-media">' +
          '<img id="modal-img" src="' + galeria[0] + '" alt="' + escapar(p.nome) + '">' +
          (galeria.length > 1
            ? '<div class="modal-thumbs">' + galeria.map(function (src, i) {
                return '<img src="' + src + '" alt="" data-thumb="' + src + '" aria-current="' + (i === 0) + '">';
              }).join("") + "</div>"
            : "") +
        "</div>" +
        '<div class="modal-body">' +
          '<p class="eyebrow">' + escapar(nomeCategoria(p.categoria)) + "</p>" +
          "<h3>" + escapar(p.nome) + "</h3>" +
          '<div class="modal-price">' + precoHTML(p.preco) + "</div>" +
          '<p class="modal-desc">' + escapar(p.descricao) + "</p>" +
          htmlVariacoes +
          '<div class="field">' +
            '<span class="field-label">Quantidade</span>' +
            '<div class="qty">' +
              '<button data-qtd="-1" aria-label="Diminuir">&minus;</button>' +
              '<span id="qtd">1</span>' +
              '<button data-qtd="1" aria-label="Aumentar">+</button>' +
            "</div>" +
          "</div>" +
          '<button class="btn btn-plum" id="add-carrinho"' + (p.estoque === false ? " disabled" : "") + ">" +
            (p.estoque === false ? "Esgotado" : (p.sobEncomenda ? "Pedir orçamento" : "Adicionar à sacola")) +
          "</button>" +
          (p.preco === null
            ? '<p class="modal-note">Preço a combinar no atendimento. Você fecha o pedido pelo WhatsApp e recebe o valor final com o frete.</p>'
            : "") +
          '<p class="modal-note"><a href="' + p.origem + '" target="_blank" rel="noopener">Ver publicação original no Instagram &rarr;</a></p>' +
          htmlPendencias +
        "</div>" +
      "</div>";

    $$("#modal [data-thumb]").forEach(function (t) {
      t.addEventListener("click", function () {
        $("#modal-img").src = t.dataset.thumb;
        $$("#modal [data-thumb]").forEach(function (o) { o.setAttribute("aria-current", o === t); });
      });
    });

    $$("#modal [data-var]").forEach(function (b) {
      b.addEventListener("click", function () {
        variacaoEscolhida = b.dataset.var;
        $$("#modal [data-var]").forEach(function (o) { o.setAttribute("aria-pressed", o === b); });
      });
    });

    $$("#modal [data-qtd]").forEach(function (b) {
      b.addEventListener("click", function () {
        quantidade = Math.max(1, quantidade + Number(b.dataset.qtd));
        $("#qtd").textContent = quantidade;
      });
    });

    var botao = $("#add-carrinho");
    if (botao) {
      botao.addEventListener("click", function () {
        adicionar(p.id, variacaoEscolhida, quantidade);
        fecharModal();
      });
    }

    $("#modal [data-fechar]").addEventListener("click", fecharModal);

    $("#modal").setAttribute("data-open", "true");
    $("#overlay").setAttribute("data-open", "true");
    document.body.style.overflow = "hidden";
  }

  function fecharModal() {
    $("#modal").setAttribute("data-open", "false");
    if ($("#drawer").getAttribute("data-open") !== "true") {
      $("#overlay").setAttribute("data-open", "false");
      document.body.style.overflow = "";
    }
    produtoAberto = null;
  }

  /* ---------- carrinho: render ---------- */

  function renderCarrinho() {
    var contador = $("#cart-count");
    contador.textContent = totalItens();
    contador.setAttribute("data-empty", totalItens() === 0);

    var corpo = $("#drawer-body");

    if (!carrinho.length) {
      corpo.innerHTML = '<p class="cart-empty">Sua sacola está vazia.<br>Os cristais esperam por você.</p>';
    } else {
      corpo.innerHTML = carrinho.map(function (item) {
        var p = acharProduto(item.id);
        if (!p) return "";
        var subtotal = p.preco !== null && p.preco !== undefined
          ? formatarPreco(p.preco * item.qtd)
          : "Sob consulta";
        return '' +
          '<div class="cart-line">' +
            '<img src="' + p.imagem + '" alt="">' +
            "<div style=\"flex:1\">" +
              '<p class="cart-line-name">' + escapar(p.nome) + "</p>" +
              (item.variacao ? '<p class="cart-line-var">Versão: ' + escapar(item.variacao) + "</p>" : "") +
              '<p class="cart-line-var">Qtd: ' + item.qtd + "</p>" +
              '<div class="cart-line-meta">' +
                '<span class="cart-line-price">' + subtotal + "</span>" +
                '<button class="cart-remove" data-remover="' + item.chave + '">Remover</button>' +
              "</div>" +
            "</div>" +
          "</div>";
      }).join("");

      $$("#drawer-body [data-remover]").forEach(function (b) {
        b.addEventListener("click", function () { remover(b.dataset.remover); });
      });
    }

    var t = totalizar();
    var rotulo;
    if (!carrinho.length) rotulo = "—";
    else if (t.temAberto && t.soma === 0) rotulo = "A combinar";
    else if (t.temAberto) rotulo = formatarPreco(t.soma) + " + a combinar";
    else rotulo = formatarPreco(t.soma);
    $("#cart-total").textContent = rotulo;

    $("#finalizar").disabled = carrinho.length === 0;
  }

  /* ---------- checkout WhatsApp ---------- */

  function montarMensagem() {
    var linhas = ["Olá! Vim pelo site da Florescer de Gaia e gostaria de fazer um pedido:", ""];
    carrinho.forEach(function (item) {
      var p = acharProduto(item.id);
      if (!p) return;
      var linha = "• " + item.qtd + "x " + p.nome;
      if (item.variacao) linha += " (" + item.variacao + ")";
      if (p.preco !== null && p.preco !== undefined) linha += " — " + formatarPreco(p.preco * item.qtd);
      linhas.push(linha);
    });
    var t = totalizar();
    linhas.push("");
    if (!t.temAberto) linhas.push("Total: " + formatarPreco(t.soma));
    else linhas.push("Aguardo o valor total e o frete. Obrigada!");
    return linhas.join("\n");
  }

  function finalizar() {
    if (!carrinho.length) return;

    if (!LOJA.whatsapp) {
      $("#drawer-body").insertAdjacentHTML("afterbegin",
        '<div class="rev-box" style="display:block;margin-bottom:16px">' +
          "<strong>Checkout não configurado</strong>" +
          "O número de WhatsApp ainda não foi preenchido. Assim que ele for informado, este botão abre a conversa já com o pedido escrito. Prévia da mensagem:" +
          '<pre style="white-space:pre-wrap;margin:10px 0 0;font-family:inherit">' + escapar(montarMensagem()) + "</pre>" +
        "</div>");
      return;
    }

    var url = "https://wa.me/" + LOJA.whatsapp + "?text=" + encodeURIComponent(montarMensagem());
    window.open(url, "_blank", "noopener");
  }

  /* ---------- drawer ---------- */

  function abrirDrawer() {
    $("#drawer").setAttribute("data-open", "true");
    $("#overlay").setAttribute("data-open", "true");
    document.body.style.overflow = "hidden";
  }

  function fecharDrawer() {
    $("#drawer").setAttribute("data-open", "false");
    if ($("#modal").getAttribute("data-open") !== "true") {
      $("#overlay").setAttribute("data-open", "false");
      document.body.style.overflow = "";
    }
  }

  /* ---------- textos vindos de LOJA ---------- */

  function aplicarDadosLoja() {
    $$("[data-loja]").forEach(function (el) {
      var valor = LOJA[el.dataset.loja];
      if (valor) el.textContent = valor;
    });
    $$("[data-instagram]").forEach(function (el) {
      el.href = "https://instagram.com/" + LOJA.instagram;
    });

    var pendentes = [];
    if (!LOJA.whatsapp) pendentes.push("WhatsApp");
    if (!LOJA.email) pendentes.push("e-mail");
    var semPreco = PRODUTOS.filter(function (p) { return p.preco === null; }).length;
    if (semPreco) pendentes.push(semPreco + " preços");

    if (pendentes.length) {
      $("#pendencias-geral").innerHTML =
        "Aguardando: " + pendentes.join(", ") + ". " +
        '<button class="pending-flag" id="toggle-revisao">ver todas as pendências</button>';
    }
  }

  /* ---------- modo revisão ---------- */

  function alternarRevisao() {
    var ativo = document.body.dataset.revisao === "true";
    document.body.dataset.revisao = ativo ? "false" : "true";
    renderGrade();
  }

  /* ---------- início ---------- */

  function iniciar() {
    aplicarDadosLoja();
    renderFiltros();
    renderGrade();
    renderCarrinho();

    $("#abrir-carrinho").addEventListener("click", abrirDrawer);
    $("#fechar-carrinho").addEventListener("click", fecharDrawer);
    $("#finalizar").addEventListener("click", finalizar);
    $("#overlay").addEventListener("click", function () { fecharModal(); fecharDrawer(); });

    document.addEventListener("click", function (e) {
      if (e.target && e.target.id === "toggle-revisao") alternarRevisao();
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { fecharModal(); fecharDrawer(); }
    });

    if (location.search.indexOf("revisao") > -1) document.body.dataset.revisao = "true";
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
