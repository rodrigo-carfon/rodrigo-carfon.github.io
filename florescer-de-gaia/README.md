# Florescer de Gaia — proposta de e-commerce

Loja virtual proposta para a marca [@florescerdgaia](https://instagram.com/florescerdgaia)
(cosméticos artesanais, cristais e rituais de autocuidado — Campinas/SP).

**Não é uma loja em operação.** É uma proposta navegável, feita para
apresentação ao cliente.

🔗 **Demo:** https://rodrigo-carfon.github.io/florescer-de-gaia/
🔍 **Modo revisão:** https://rodrigo-carfon.github.io/florescer-de-gaia/?revisao=1

---

## De onde vieram os dados

O catálogo foi montado a partir dos **12 posts públicos** do perfil no
Instagram, em 11/08/2026. Todo texto de produto é transcrição ou adaptação
direta das legendas — nada foi inventado.

Dos 12 posts, 5 não continham produto (foto pessoal, participação em feira,
agradecimento a clientes, e um post de outra conta que marcou a marca).
Os 7 restantes renderam **7 produtos de catálogo**, alguns com variações de
cor e tamanho.

### O teto dos 12 posts

O perfil tem **112 publicações**, mas o Instagram entrega apenas as 12 mais
recentes para quem não está logado. Isso foi verificado por três caminhos:

- `api/v1/users/web_profile_info` responde **400** (endpoint fechado)
- `?__a=1&__d=dis` devolve corpo vazio
- navegador real rolando o perfil trava em 12 e **não exibe muro de login** —
  simplesmente não há paginação para visitante anônimo

Chegar às publicações mais antigas exige sessão autenticada. O caminho limpo
é a exportação de dados da própria conta (Configurações → Central de contas →
Suas informações e permissões → Baixar suas informações), que traz todas as
fotos e legendas em ZIP.

As imagens foram baixadas e versionadas em `img/` porque as URLs do CDN do
Instagram são assinadas e expiram em poucos dias.

## O que ainda falta

Nenhum post menciona preço — a venda acontece por direct. Por isso:

- todos os produtos estão com `preco: null`, exibidos como **"Sob consulta"**
- o número de WhatsApp do checkout ainda não foi informado
- alguns produtos precisam de foto própria e de dados obrigatórios de
  cosmético (peso, validade, ingredientes)

O **modo revisão** (`?revisao=1`) lista, produto a produto, exatamente o que
falta. Esse modo é invisível para o cliente final.

## Como preencher

Tudo em um arquivo só: [`assets/products.js`](assets/products.js).

```js
// antes
preco: null,          // aparece como "Sob consulta"

// depois
preco: 89.90,         // aparece como "R$ 89,90"
```

E no topo do mesmo arquivo, o contato:

```js
whatsapp: "5519912345678",   // DDI + DDD + número, só dígitos
```

Com o WhatsApp preenchido, o botão de checkout passa a abrir a conversa já
com o pedido escrito. Sem ele, o botão mostra uma prévia da mensagem.

## Estrutura

```
florescer-de-gaia/
├── index.html          página única
├── assets/
│   ├── products.js     catálogo — ÚNICO arquivo a editar
│   ├── style.css       design system (cores, tipografia, componentes)
│   └── app.js          filtros, modal, carrinho, checkout
└── img/                fotos extraídas do Instagram
```

Sem build, sem dependências, sem framework. HTML/CSS/JS puro servido pelo
GitHub Pages.

## Funcionalidades

- catálogo com filtro por categoria
- página de produto em modal, com galeria, variações e quantidade
- variações (cor, tamanho, acabamento) são versões de **um mesmo produto** —
  trocar a versão troca a foto e o preço, e cada versão vira uma linha própria
  no carrinho. Isso evita o mesmo item aparecer duplicado na vitrine.
- carrinho persistente (`localStorage`) — sobrevive ao refresh
- checkout via WhatsApp com o pedido montado automaticamente
- total que lida com preços em aberto ("A combinar")
- responsivo
- modo revisão para acompanhar pendências

## Sobre as imagens

As fotos são da marca. Estão aqui apenas para a apresentação da proposta.
Algumas imagens são recortes de fotos originais (para dar foto própria a
produtos que dividiam a mesma publicação) — estão sinalizadas no modo revisão
como pendentes de foto definitiva.
