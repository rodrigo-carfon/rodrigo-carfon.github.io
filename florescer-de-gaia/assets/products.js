/* =============================================================
   FLORESCER DE GAIA — CATÁLOGO
   =============================================================
   Este é o único arquivo que precisa ser editado para colocar
   a loja no ar. Nada aqui foi inventado: todo texto veio das
   legendas dos posts do @florescerdgaia.

   COMO PREENCHER
   --------------
   preco:      null  ->  o card mostra "Sob consulta".
                         Troque por um número, ex: 89.90
   estoque:    true / false  ->  false mostra o selo "Esgotado"
   variacoes:  [] ou lista de opções, ex: ["Dourado", "Prata"]
   pendencias: lista do que ainda falta descobrir. Aparece
               APENAS no modo revisão (link no rodapé),
               nunca para o cliente final.
   ============================================================= */

const LOJA = {
  nome: "Florescer de Gaia",
  tagline: "Ferramentas de cura para corpo, mente e espírito",
  bio: "Cantinho mágico da Isa Massaro",
  cidade: "Campinas, SP",
  instagram: "florescerdgaia",

  // PREENCHER: número com DDI e DDD, só dígitos. Ex: "5519912345678"
  whatsapp: null,

  // PREENCHER: usado no rodapé
  email: null
};

const CATEGORIAS = [
  { slug: "todos",         nome: "Todos os produtos" },
  { slug: "cristais",      nome: "Cristais e Acessórios" },
  { slug: "banho",         nome: "Banho e Corpo" },
  { slug: "rituais",       nome: "Rituais e Autocuidado" },
  { slug: "lembrancinhas", nome: "Lembrancinhas" }
];

const PRODUTOS = [
  {
    id: "colar-cascalho-cristais",
    nome: "Colar de Cascalho de Cristais",
    categoria: "cristais",
    preco: null,
    estoque: true,
    destaque: true,
    imagem: "img/colar-cascalho.jpg",
    resumo: "Choker de cristais naturais variados, montado à mão.",
    descricao: "Colar estilo choker montado com cascalhos de cristais naturais — ametista, quartzo rosa, quartzo transparente, ágata, aventurina e cornalina se alternam ao longo da peça, cada um com sua cor e sua textura.\n\nAlém de completar o look, os acessórios em cristais têm o poder de proteger e revitalizar a energia ao nosso redor.",
    variacoes: [],
    origem: "https://www.instagram.com/p/DUs7WIVkTE4/",
    pendencias: ["preço", "comprimento", "tipo de fecho", "o mix de cristais é fixo ou varia a cada peça?"]
  },
  {
    id: "anel-cristal-bruto",
    nome: "Anel de Cristal Bruto",
    categoria: "cristais",
    preco: null,
    estoque: true,
    destaque: false,
    imagem: "img/anel-cristal.jpg",
    resumo: "Pedra bruta em base dourada. Cada anel é único.",
    descricao: "Anel com pedra bruta de quartzo engastada em base metálica dourada.\n\nPor ser cristal bruto, cada peça tem formato, tamanho e tonalidade próprios — não existem dois anéis iguais.",
    variacoes: [],
    origem: "https://www.instagram.com/p/DUs7WIVkTE4/",
    pendencias: ["preço", "aro ajustável ou numerado?", "quais cristais estão disponíveis", "FOTO PRÓPRIA — a atual é um recorte da foto do colar", "confirmar se é item à venda"]
  },
  {
    id: "bracelete-cristal-dourado",
    nome: "Bracelete de Cristal Bruto — Dourado",
    categoria: "cristais",
    preco: null,
    estoque: true,
    destaque: true,
    imagem: "img/bracelete-a.jpg",
    imagensExtras: ["img/braceletes-cristal.jpg"],
    resumo: "Bracelete aberto com acabamento dourado e cristal bruto.",
    descricao: "Bracelete aberto de haste martelada com acabamento dourado e cristal bruto engastado.\n\nNa foto aparecem versões com quartzo rosa, ametista e uma pedra verde musgo. O acabamento dourado aquece o tom das pedras claras.",
    variacoes: [],
    origem: "https://www.instagram.com/p/DL3XvguxKUO/",
    pendencias: ["preço", "quais cristais podem ser escolhidos", "tamanho único ou ajustável?"]
  },
  {
    id: "bracelete-cristal-prata",
    nome: "Bracelete de Cristal Bruto — Prata",
    categoria: "cristais",
    preco: null,
    estoque: true,
    destaque: false,
    imagem: "img/bracelete-b.jpg",
    imagensExtras: ["img/braceletes-cristal.jpg"],
    resumo: "Mesmo modelo, acabamento prateado.",
    descricao: "Bracelete aberto de haste martelada com acabamento prata e cristal bruto engastado.\n\nMesma linha do modelo dourado, com acabamento mais frio — combina especialmente com quartzos transparentes e ametista.",
    variacoes: [],
    origem: "https://www.instagram.com/p/DL3XvguxKUO/",
    pendencias: ["preço", "quais cristais podem ser escolhidos", "FOTO PRÓPRIA — a foto do post destaca o modelo dourado"]
  },
  {
    id: "sabonete-lavanda-anil",
    nome: "Sabonete Glicerinado de Lavanda e Anil",
    categoria: "banho",
    preco: null,
    estoque: true,
    destaque: true,
    imagem: "img/sabonete-lavanda-anil.jpg",
    resumo: "Artesanal. Relaxa a pele e limpa a energia do ambiente.",
    descricao: "Sabonete glicerinado artesanal com extrato de lavanda e anil em pó.\n\nA lavanda oferece propriedades anti-inflamatórias e relaxantes, hidratando e acalmando a pele. Enquanto o anil em pó traz a limpeza energética pra sua aura e também pro ambiente.\n\nTrazendo harmonia e bem-estar para sua vida.",
    variacoes: [],
    origem: "https://www.instagram.com/p/DUa4hedjQep/",
    pendencias: ["preço", "peso da barra", "validade", "lista completa de ingredientes (exigida para cosmético)"]
  },
  {
    id: "gel-glitter-dourado-60g",
    nome: "Gel Corporal com Glitter — Dourado 60g",
    categoria: "banho",
    preco: null,
    estoque: true,
    destaque: true,
    imagem: "img/gel-glitter-dourado.jpg",
    imagensExtras: ["img/gel-glitter.jpg", "img/campanha-carnaval.jpg"],
    resumo: "Brilho dourado para cabelo, corpo, roupa e maquiagem.",
    descricao: "Gel corporal com glitter dourado, cheirinho delicioso e super brilhante.\n\nA gente usa glitter no cabelo, na roupa, na maquiagem E NO CORPINHO! Bisnaga de 60g, prática de levar na bolsa e reaplicar durante a festa.",
    variacoes: [],
    origem: "https://www.instagram.com/p/DUTMxxPDd7x/",
    pendencias: ["preço", "qual é a fragrância", "CONFERIR ESTOQUE — post de Carnaval avisava 'tempo contado nos estoques'"]
  },
  {
    id: "gel-glitter-pink-60g",
    nome: "Gel Corporal com Glitter — Pink 60g",
    categoria: "banho",
    preco: null,
    estoque: true,
    destaque: false,
    imagem: "img/gel-glitter-pink.jpg",
    imagensExtras: ["img/gel-glitter.jpg", "img/campanha-carnaval.jpg"],
    resumo: "Mesma fórmula, brilho pink intenso.",
    descricao: "Gel corporal com glitter pink, cheirinho delicioso e super brilhante.\n\nMesma fórmula do dourado, em rosa vibrante. Bisnaga de 60g.",
    variacoes: [],
    origem: "https://www.instagram.com/p/DUTMxxPDd7x/",
    pendencias: ["preço", "qual é a fragrância", "CONFERIR ESTOQUE"]
  },
  {
    id: "gel-glitter-150g",
    nome: "Gel Corporal com Glitter — 150g",
    categoria: "banho",
    preco: null,
    estoque: true,
    destaque: false,
    imagem: "img/gel-glitter.jpg",
    resumo: "Versão grande, para o bloco inteiro.",
    descricao: "A versão família do gel corporal com glitter, em embalagem de 150g — para dividir com as amigas e atravessar o Carnaval inteiro.\n\nA legenda do post confirma os dois tamanhos: disponível nos tamanhos de 60g e 150g.",
    variacoes: [],
    origem: "https://www.instagram.com/p/DUTMxxPDd7x/",
    pendencias: ["preço", "quais cores saem no 150g", "FOTO PRÓPRIA — a foto mostra só bisnagas de 60g"]
  },
  {
    id: "spa-jelly-pes",
    nome: "Spa Jelly para os Pés",
    categoria: "rituais",
    preco: null,
    estoque: true,
    destaque: true,
    imagem: "img/spa-jelly.jpg",
    imagensExtras: ["img/spa-jelly-detalhe.jpg"],
    resumo: "A água vira gel, o gel vira água. Esfolia, hidrata e desacelera.",
    descricao: "Uma experiência sensorial que te desacelera e te traz pro presente.\n\nAlém de retirar a pele morta e hidratar os pés, o Spa Jelly também nos ajuda a desacelerar da rotina corrida que temos. Nos faz estar mais presentes ao momento e aos nossos sentidos.\n\nObservar a água se transformando em gel, e depois o gel se transformando em água, é realmente hipnotizante. Uma alquimia que é impossível não se apaixonar.",
    variacoes: ["Azul", "Branco"],
    origem: "https://www.instagram.com/p/DYnStQgsBKs/",
    pendencias: ["preço", "NOME REAL DE CADA VERSÃO — o rótulo não está legível na foto", "peso do sachê", "modo de uso escrito", "rende quantas aplicações?"]
  },
  {
    id: "lembrancinhas-personalizadas",
    nome: "Lembrancinhas Artesanais Personalizadas",
    categoria: "lembrancinhas",
    preco: null,
    estoque: true,
    destaque: false,
    sobEncomenda: true,
    imagem: "img/lembrancinhas.jpg",
    resumo: "Sob encomenda para casamentos e eventos.",
    descricao: "Lembrancinhas feitas à mão sob encomenda para casamentos e eventos.\n\nComo é mágico fazer parte de momentos únicos na vida das pessoas! Cada pedido é preparado com muito amor e luz, personalizado para o momento do cliente.\n\nPara orçamento, conte a data do evento, a quantidade e a ideia que você tem em mente.",
    variacoes: [],
    origem: "https://www.instagram.com/p/Db0pPmjMr74/",
    pendencias: ["faixa de preço", "QUAL É O PRODUTO — o vídeo mostra a produção, não a lembrancinha pronta", "quantidade mínima", "prazo de produção", "FOTO do produto finalizado"]
  }
];
