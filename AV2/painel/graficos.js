"use strict";

// Gráficos em SVG puro, sem bibliotecas: o painel abre direto do arquivo, sem internet.
// Cada gráfico é redesenhado na largura real do contêiner, para o texto manter o tamanho legível.

const Graficos = (() => {
  const NS = "http://www.w3.org/2000/svg";
  const fmt = (casas = 0) => {
    const nf = new Intl.NumberFormat("pt-BR", {minimumFractionDigits: casas, maximumFractionDigits: casas});
    return (v) => nf.format(v);
  };

  function el(tag, attrs = {}, pai) {
    const no = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) if (v !== undefined && v !== null) no.setAttribute(k, v);
    if (pai) pai.append(no);
    return no;
  }

  function texto(pai, x, y, conteudo, attrs = {}) {
    const t = el("text", {x, y, ...attrs}, pai);
    t.textContent = conteudo;
    return t;
  }

  function dica(no, conteudo) {
    el("title", {}, no).textContent = conteudo;
  }

  // Escala "bonita" para o eixo: arredonda o máximo e escolhe 4 a 5 marcas
  function marcas(min, max, n = 4) {
    if (min === max) return [min, min + 1];
    const amplitude = max - min;
    const bruto = amplitude / n;
    const potencia = Math.pow(10, Math.floor(Math.log10(bruto)));
    const passo = [1, 2, 2.5, 5, 10].map((m) => m * potencia).find((p) => amplitude / p <= n) || potencia * 10;
    const inicio = Math.floor(min / passo) * passo;
    const fim = Math.ceil(max / passo) * passo;
    const lista = [];
    for (let v = inicio; v <= fim + passo / 2; v += passo) lista.push(Math.round(v * 1e6) / 1e6);
    return lista;
  }

  // Registra um gráfico para ser redesenhado quando o contêiner mudar de largura
  const registros = new Map();
  const observador = typeof ResizeObserver === "function"
    ? new ResizeObserver((entradas) => entradas.forEach((e) => {
      const r = registros.get(e.target);
      if (r && Math.abs(e.contentRect.width - r.largura) > 4) desenhar(e.target, r.fn);
    }))
    : null;

  function desenhar(contenedor, fn) {
    const largura = Math.max(300, Math.round(contenedor.clientWidth || 600));
    registros.set(contenedor, {fn, largura});
    contenedor.replaceChildren();
    fn(largura);
  }

  function montar(contenedor, fn) {
    desenhar(contenedor, fn);
    if (observador) observador.observe(contenedor);
  }

  function base(contenedor, largura, altura, rotulo) {
    return el("svg", {viewBox: `0 0 ${largura} ${altura}`, width: largura, height: altura, role: "img", "aria-label": rotulo, class: "svg-grafico"}, contenedor);
  }

  function eixoY(svg, m, escala, x0, x1, formato) {
    m.forEach((v) => {
      const y = escala(v);
      el("line", {x1: x0, x2: x1, y1: y, y2: y, class: v === 0 ? "eixo-zero" : "grade"}, svg);
      texto(svg, x0 - 6, y + 4, formato(v), {class: "rotulo-eixo", "text-anchor": "end"});
    });
  }

  // Barras verticais com o valor escrito em cima
  function barras(contenedor, {itens, formato = fmt(0), rotulo = "", altura = 250}) {
    montar(contenedor, (largura) => {
      const svg = base(contenedor, largura, altura, rotulo);
      const margem = {t: 26, r: 10, b: 46, l: 46};
      const max = Math.max(...itens.map((i) => i.valor));
      const m = marcas(0, max);
      const topo = m.at(-1);
      const y = (v) => margem.t + (altura - margem.t - margem.b) * (1 - v / topo);
      eixoY(svg, m, y, margem.l, largura - margem.r, formato);
      const faixa = (largura - margem.l - margem.r) / itens.length;
      const larguraBarra = Math.min(90, faixa * 0.62);
      const compacto = faixa < 52;
      itens.forEach((item, i) => {
        const cx = margem.l + faixa * (i + 0.5);
        const r = el("rect", {x: cx - larguraBarra / 2, y: y(item.valor), width: larguraBarra, height: y(0) - y(item.valor), rx: 4, fill: item.cor}, svg);
        dica(r, `${String(item.rotulo).replace("\n", " ")}: ${formato(item.valor)}`);
        const valor = formato(item.valor);
        texto(svg, cx, y(item.valor) - 7, valor, {class: compacto ? "valor-barra compacto" : "valor-barra", "text-anchor": "middle"});
        const linhas = String(item.rotulo).split("\n");
        linhas.forEach((l, k) => texto(svg, cx, altura - margem.b + 18 + k * 14, l, {class: "rotulo-eixo forte", "text-anchor": "middle"}));
      });
    });
  }

  // Linhas no tempo ou em categorias; series: [{nome, valores, cor, tracejado, espessura}]
  function linhas(contenedor, {rotulosX, series, formato = fmt(0), rotulo = "", altura = 270, cadaRotulo, barrasFundo}) {
    montar(contenedor, (largura) => {
      const svg = base(contenedor, largura, altura, rotulo);
      const margem = {t: 16, r: barrasFundo ? 46 : 26, b: 34, l: 50};
      const todos = series.flatMap((s) => s.valores).filter(Number.isFinite);
      const m = marcas(Math.min(0, ...todos), Math.max(...todos));
      const y = (v) => margem.t + (altura - margem.t - margem.b) * (1 - (v - m[0]) / (m.at(-1) - m[0]));
      const n = rotulosX.length;
      const passoX = (largura - margem.l - margem.r) / Math.max(1, n - (barrasFundo ? 0 : 1));
      const x = (i) => margem.l + (barrasFundo ? passoX * (i + 0.5) : passoX * i);
      if (barrasFundo) {
        const mb = marcas(0, Math.max(...barrasFundo.valores));
        const yb = (v) => margem.t + (altura - margem.t - margem.b) * (1 - v / mb.at(-1));
        barrasFundo.valores.forEach((v, i) => {
          const r = el("rect", {x: x(i) - passoX * 0.32, y: yb(v), width: passoX * 0.64, height: yb(0) - yb(v), rx: 3, fill: barrasFundo.cor, opacity: 0.45}, svg);
          dica(r, `${rotulosX[i]} · ${barrasFundo.nome}: ${fmt(0)(v)}`);
        });
        mb.forEach((v) => texto(svg, largura - margem.r + 6, yb(v) + 4, fmt(0)(v), {class: "rotulo-eixo", "text-anchor": "start", fill: barrasFundo.cor}));
      }
      eixoY(svg, m, y, margem.l, largura - margem.r, formato);
      const intervalo = cadaRotulo ?? Math.max(1, Math.ceil(n / Math.max(4, Math.floor(largura / 70))));
      rotulosX.forEach((r, i) => {
        if (i % intervalo === 0) texto(svg, x(i), altura - 12, r, {class: "rotulo-eixo", "text-anchor": "middle"});
      });
      series.forEach((s) => {
        let caminho = "";
        s.valores.forEach((v, i) => {
          if (!Number.isFinite(v)) return;
          caminho += `${caminho && Number.isFinite(s.valores[i - 1]) ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`;
        });
        el("path", {d: caminho, fill: "none", stroke: s.cor, "stroke-width": s.espessura ?? 2.4, "stroke-dasharray": s.tracejado ? "6 5" : null, "stroke-linejoin": "round"}, svg);
        if (s.pontos !== false) s.valores.forEach((v, i) => {
          if (!Number.isFinite(v)) return;
          const c = el("circle", {cx: x(i), cy: y(v), r: s.raio ?? 3.2, fill: s.cor}, svg);
          dica(c, `${rotulosX[i]} · ${s.nome}: ${formato(v)}`);
        });
      });
    });
  }

  function legenda(contenedor, itens) {
    contenedor.replaceChildren();
    itens.forEach(({nome, cor, tracejado, barra}) => {
      const li = document.createElement("li");
      const amostra = document.createElement("span");
      amostra.className = barra ? "amostra-barra" : tracejado ? "amostra-linha tracejada" : "amostra-linha";
      amostra.style.setProperty("--cor", cor);
      li.append(amostra, nome);
      contenedor.append(li);
    });
  }

  // Completa as semanas que faltam com null, para o gráfico mostrar a lacuna em vez de ligar os pontos
  function semanal(datasIso, colunas) {
    const dia = 864e5;
    const inicio = Date.parse(datasIso[0]);
    const fim = Date.parse(datasIso.at(-1));
    const posicao = new Map(datasIso.map((d, i) => [d, i]));
    const rotulos = [];
    const saida = colunas.map(() => []);
    for (let t = inicio; t <= fim; t += 7 * dia) {
      const iso = new Date(t).toISOString().slice(0, 10);
      rotulos.push(`${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(2, 4)}`);
      const i = posicao.get(iso);
      colunas.forEach((c, k) => saida[k].push(i === undefined ? null : c[i]));
    }
    return {rotulos, colunas: saida};
  }

  return {barras, linhas, legenda, semanal, fmt};
})();
