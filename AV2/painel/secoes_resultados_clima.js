"use strict";

// Seções de resultados: gráficos alimentados por dados.js (exportar_painel.py).
(() => {
  const dados = globalThis.AnteceDengue;
  const r = dados?.resultados;
  if (!r || typeof Graficos === "undefined") return;
  const $ = (id) => document.getElementById(id);
  const G = Graficos;
  const COR = {media: "#8a8f98", sem: "#4c78a8", com: "#087d64", obs: "#173653", chuva: "#2a7fbf"};
  const f1 = G.fmt(1);
  const f3 = G.fmt(3);
  const pct = (v) => f1(v).replace(",0", "") + "%";
  const mesesNome = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

  // Números de destaque
  const teste = (s, c) => r.teste.find((t) => t.semanas === s && t.cenario === c);
  $("d-ganho-ml").textContent = pct(100 * (1 - teste(4, "com clima").MAE / teste(4, "baseline").MAE));
  const prior = r.priorizacao;
  $("d-prior").textContent = `${f1(prior.reduce((a, p) => a + p.com, 0) / prior.length)} de 10`;
  const ordem = r.total_bairro_teste.map((v, i) => [v, i]).sort((a, b) => b[0] - a[0]).slice(0, 20);
  $("d-bairros").textContent = `${ordem.filter(([, i]) => r.ganho_bairro[i] > 0).length} de 20`;

  // Erro médio por bairro, mensal ou semanal
  function desenharResultado(semanas) {
    $("h4").setAttribute("aria-pressed", String(semanas === 4));
    $("h1").setAttribute("aria-pressed", String(semanas === 1));
    const com = teste(semanas, "com clima");
    const sem = teste(semanas, "sem clima");
    G.barras($("g-mae"), {
      rotulo: "Erro médio por bairro no teste",
      formato: f3,
      itens: [
        {rotulo: "Método\nsimples", valor: teste(semanas, "baseline").MAE, cor: COR.media},
        {rotulo: "Modelo\nsem clima", valor: sem.MAE, cor: COR.sem},
        {rotulo: "Modelo\ncom clima", valor: com.MAE, cor: COR.com},
      ],
    });
    $("n-metricas").textContent = `Menor é melhor. O clima tirou mais ${pct(100 * (1 - com.MAE / sem.MAE))} do erro.`;
  }
  $("h4").addEventListener("click", () => desenharResultado(4));
  $("h1").addEventListener("click", () => desenharResultado(1));
  desenharResultado(4);

  // Curva da cidade no ano de teste
  const c = r.cidade_teste;
  const cid = G.semanal(r.datas_teste, [c.observado, c.media, c.com]);
  const seriesCidade = [
    {nome: "Real", valores: cid.colunas[0], cor: COR.obs, espessura: 3},
    {nome: "Método simples", valores: cid.colunas[1], cor: COR.media, tracejado: true, pontos: false},
    {nome: "Modelo com clima", valores: cid.colunas[2], cor: COR.com},
  ];
  G.legenda($("l-cidade"), seriesCidade.map(({nome, cor, tracejado}) => ({nome, cor, tracejado})));
  G.linhas($("g-cidade"), {rotulo: "Notificações nas próximas 4 semanas no Recife", rotulosX: cid.rotulos, series: seriesCidade, altura: 260});

  // Calendário: chuva antes, dengue depois
  G.legenda($("l-calendario"), [{nome: "Chuva (mm por semana)", cor: COR.chuva, barra: true}, {nome: "Notificações por semana", cor: COR.obs}]);
  G.linhas($("g-calendario"), {
    rotulo: "Chuva e notificações ao longo do ano",
    rotulosX: mesesNome, cadaRotulo: 1, altura: 260,
    barrasFundo: {nome: "Chuva (mm por semana)", valores: r.calendario.chuva, cor: COR.chuva},
    series: [{nome: "Notificações por semana", valores: r.calendario.notificacoes, cor: COR.obs, espessura: 3}],
  });

  // Destaca a seção visível no menu
  const links = [...document.querySelectorAll(".secoes a")];
  if ("IntersectionObserver" in window) {
    const obs = new IntersectionObserver((entradas) => entradas.forEach((e) => {
      if (e.isIntersecting) links.forEach((a) => a.toggleAttribute("aria-current", a.hash === "#" + e.target.id));
    }), {rootMargin: "-40% 0px -55% 0px"});
    document.querySelectorAll(".capitulo").forEach((s) => obs.observe(s));
  }
})();
