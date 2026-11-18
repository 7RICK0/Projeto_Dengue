"use strict";

const dados = globalThis.AnteceDengue;
const elemento = (id) => document.getElementById(id);
const mes = elemento("mes");
const ano = elemento("ano");
const cenario = elemento("cenario");
const bairro = elemento("bairro");
const mapa = elemento("mapa");
const camada = elemento("mapa-valor");
const svg = "http://www.w3.org/2000/svg";
const ausente = "#e2e7ef";
// Risco de surto: baixo (verde), médio (amarelo), alto (vermelho)
const limitesRisco = {mensal: [5, 15], anual: [50, 150]};
const RISCO = [
  {nome: "Risco baixo", cor: "#2e9e5b", classe: "baixo"},
  {nome: "Risco médio", cor: "#f0b429", classe: "medio"},
  {nome: "Risco alto", cor: "#d64534", classe: "alto"},
];
const nivelRisco = (v) => { const l = limitesRisco[visao]; return v >= l[1] ? 2 : v >= l[0] ? 1 : 0; };
const quantidade = new Intl.NumberFormat("pt-BR", {maximumFractionDigits: 0});
const decimal = new Intl.NumberFormat("pt-BR", {maximumFractionDigits: 1});
const formatoMes = new Intl.DateTimeFormat("pt-BR", {month: "long", year: "numeric", timeZone: "UTC"});
const formatoMesCurto = new Intl.DateTimeFormat("pt-BR", {month: "short", year: "2-digit", timeZone: "UTC"});
const dataCurta = (iso) => iso.slice(8, 10) + "/" + iso.slice(5, 7);
const dataCompleta = (iso) => dataCurta(iso) + "/" + iso.slice(0, 4);
const num = (valor) => Number.isFinite(valor) ? quantidade.format(valor) : "Indisponível";
const soma = (valores) => valores?.reduce((a, b) => a + b, 0);
const rotuloAno = (p) => p.inicio.slice(0, 4);
let visao = "mensal";
let camadaPreferida = "previsto";
let caminhos = [];

function montar() {
  dados.meses.forEach((p, i) => mes.add(new Option(formatoMes.format(new Date(p.inicio)), i)));
  dados.anos.forEach((p, i) => ano.add(new Option(rotuloAno(p) + (p.tipo === "estimativa" ? " (estimativa)" : ""), i)));
  dados.mapa.map((item, i) => ({...item, i}))
    .sort((a, b) => a.name.localeCompare(b.name, "pt-BR"))
    .forEach((item) => bairro.add(new Option(item.name, item.i)));
  bairro.value = String(Math.max(0, dados.mapa.findIndex((p) => p.name === "Ibura")));
  mes.value = String(Math.max(0, dados.meses.findIndex((p) => p.inicio === "2021-04-01")));
  ano.value = String(Math.max(0, dados.anos.findIndex((p) => rotuloAno(p) === "2025")));

  caminhos = dados.mapa.map((item, i) => {
    const path = document.createElementNS(svg, "path");
    path.setAttribute("d", item.path);
    path.setAttribute("tabindex", "0");
    path.setAttribute("role", "button");
    path.append(document.createElementNS(svg, "title"));
    function selecionar() { bairro.value = String(i); atualizar(); }
    path.addEventListener("click", selecionar);
    path.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); selecionar(); }
    });
    mapa.append(path);
    return path;
  });
  const limite = mapa.getBBox();
  mapa.setAttribute("viewBox", [limite.x - 12, limite.y - 12, limite.width + 24, limite.height + 24].join(" "));
  elemento("ver-mes").addEventListener("click", () => { visao = "mensal"; atualizar(); });
  elemento("ver-ano").addEventListener("click", () => { visao = "anual"; atualizar(); });
  camada.addEventListener("change", () => { camadaPreferida = camada.value; atualizar(); });
  [mes, ano, cenario, bairro].forEach((controle) => controle.addEventListener("change", atualizar));
  atualizar();
}

function descrever(previsto, observado, anterior, anual, periodo) {
  if (Number.isFinite(previsto) && Number.isFinite(observado)) {
    const erro = Math.round(previsto) - observado;
    return erro === 0 ? "A previsão acertou o total."
      : `A previsão ficou ${num(Math.abs(erro))} ${erro > 0 ? "acima" : "abaixo"} do real.`;
  }
  if (periodo.tipo === "estimativa") {
    const delta = Math.round(previsto) - anterior;
    const variacao = anterior > 0 && delta !== 0
      ? ` A estimativa fica ${decimal.format(100 * Math.abs(delta) / anterior)}% ${delta >= 0 ? "acima" : "abaixo"} de ${num(anterior)} notificações em 2025.`
      : "";
    return "Projeção com dados até dezembro de 2025." + variacao;
  }
  if (Number.isFinite(observado) && Number.isFinite(anterior)) {
    const delta = observado - anterior;
    return anterior > 0 && delta !== 0
      ? `${decimal.format(100 * Math.abs(delta) / anterior)}% ${delta > 0 ? "acima" : "abaixo"} do ${anual ? "ano" : "mês"} anterior.`
      : "";
  }
  return "";
}

// Lentes do mapa: cada uma colore os bairros por uma pergunta diferente
const coresGanho = ["#e07b39", "#f3c4a2", "#eef1f5", "#9ec5e8", "#2a6fb0"];
const coresPrioridade = {acerto: "#173653", falso: "#8fb3e0", perdido: "#e07b39"};

function lenteMapa(tipo, periodo, previsto) {
  const n = dados.mapa.length;
  if (tipo === "previsto" || tipo === "observado") {
    const valores = tipo === "previsto" ? previsto : periodo.observado;
    const [a, b] = limitesRisco[visao];
    const faixa = ["menos de " + a, `${a} a ${b - 1}`, `${b} ou mais`];
    return {
      valores,
      cor: (v) => RISCO[nivelRisco(v)].cor,
      rotulo: (v) => `${RISCO[nivelRisco(v)].nome.toLowerCase()} · ${num(v)} notificações`,
      legenda: RISCO.map((r, i) => [r.cor, `${r.nome} (${faixa[i]})`]).reverse(),
      nota: "",
    };
  }
  if (tipo === "prioridade") {
    if (!previsto || !periodo.observado) return {valores: null, legenda: [], unidade: "", nota: ""};
    const top = (arr) => new Set(arr.map((v, i) => [v, i]).sort((a, b) => b[0] - a[0]).slice(0, 10).map(([, i]) => i));
    const tp = top(previsto);
    const to = top(periodo.observado);
    const categoria = Array.from({length: n}, (_, i) => tp.has(i) && to.has(i) ? "acerto" : tp.has(i) ? "falso" : to.has(i) ? "perdido" : null);
    const conta = (c) => categoria.filter((x) => x === c).length;
    return {
      valores: categoria,
      cor: (c) => coresPrioridade[c] || "#e7ebf1",
      rotulo: (c) => ({acerto: "acertou", falso: "apontou, mas não era top 10", perdido: "top 10 que escapou"}[c] || "fora das duas listas"),
      legenda: [[coresPrioridade.acerto, `Acertou (${conta("acerto")})`], [coresPrioridade.falso, `Apontou errado (${conta("falso")})`], [coresPrioridade.perdido, `Escapou (${conta("perdido")})`]],
      nota: "Os 10 bairros de maior risco previsto × os 10 com mais notificações reais.",
    };
  }
  const ganho = dados.resultados?.ganho_bairro;
  const l = [-1, -0.25, 0.25, 1];
  return {
    valores: ganho,
    cor: (v) => coresGanho[[v < l[0], v < l[1], v <= l[2], v <= l[3], true].indexOf(true)],
    rotulo: (v) => v > 0 ? `clima reduziu o erro em ${decimal.format(v)}` : v < 0 ? `clima aumentou o erro em ${decimal.format(-v)}` : "sem diferença",
    legenda: [[coresGanho[4], "Ajudou muito"], [coresGanho[3], "Ajudou"], [coresGanho[2], "Igual"], [coresGanho[1], "Atrapalhou"], [coresGanho[0], "Atrapalhou muito"]],
    nota: "Ano de teste inteiro.",
  };
}

function atualizarMapa(periodo, previsto, index) {
  const disponivel = {previsto: !!previsto, observado: !!periodo.observado,
    prioridade: !!(previsto && periodo.observado), ganho: visao === "mensal" && !!dados.resultados};
  for (const opcao of camada.options) opcao.disabled = !disponivel[opcao.value];
  const tipo = disponivel[camadaPreferida] ? camadaPreferida : disponivel.previsto ? "previsto" : "observado";
  camada.value = tipo;
  const lente = lenteMapa(tipo, periodo, previsto);
  const valores = lente.valores;
  caminhos.forEach((path, i) => {
    const valor = valores?.[i];
    const existe = tipo === "prioridade" ? valores !== null : Number.isFinite(valor);
    path.style.fill = existe ? lente.cor(valor) : ausente;
    path.setAttribute("aria-pressed", String(i === index));
    const rotulo = `${dados.mapa[i].name} · ${existe ? lente.rotulo(valor) : "indisponível"}`;
    path.setAttribute("aria-label", rotulo);
    path.firstChild.textContent = rotulo;
  });
  elemento("nota-lente").textContent = lente.nota;
  const legenda = elemento("legenda");
  legenda.replaceChildren();
  lente.legenda.forEach(([corItem, nome]) => {
    const li = document.createElement("li");
    const cor = document.createElement("span");
    cor.className = "amostra";
    cor.style.backgroundColor = corItem;
    li.append(cor, nome);
    legenda.append(li);
  });
  atualizarRanking(tipo === "observado" ? "observado" : "previsto", tipo === "observado" ? periodo.observado : previsto ?? periodo.observado);
}

function atualizarRanking(tipo, valores) {
  const ranking = elemento("maiores");
  ranking.replaceChildren();
  elemento("titulo-ranking").textContent = tipo === "previsto" ? "Maior risco previsto" : "Maior risco real";
  valores?.map((valor, i) => ({valor, nome: dados.mapa[i].name}))
    .sort((a, b) => b.valor - a.valor || a.nome.localeCompare(b.nome, "pt-BR"))
    .slice(0, 10).forEach(({valor, nome}) => {
      const li = document.createElement("li");
      const nivel = RISCO[nivelRisco(valor)];
      const selo = document.createElement("span");
      selo.className = "risco mini " + nivel.classe;
      selo.textContent = nivel.nome.replace("Risco ", "");
      const numero = document.createElement("strong");
      numero.textContent = num(valor);
      li.append(nome + " ", selo, numero);
      ranking.append(li);
    });
}

// Série das janelas de 4 semanas do ano de teste para o bairro escolhido
let bairroDesenhado = -1;
function desenharSerieBairro(index) {
  const r = dados.resultados;
  if (!r || typeof Graficos === "undefined" || index === bairroDesenhado) return;
  bairroDesenhado = index;
  const s = r.serie_bairros;
  const sem = Graficos.semanal(r.datas_teste, [s.observado[index], s.media[index], s.com[index]]);
  const series = [
    {nome: "Real", valores: sem.colunas[0], cor: "#173653", espessura: 3},
    {nome: "Método simples", valores: sem.colunas[1], cor: "#8a8f98", tracejado: true, pontos: false},
    {nome: "Modelo com clima", valores: sem.colunas[2], cor: "#087d64"},
  ];
  Graficos.legenda(elemento("l-bairro"), series);
  Graficos.linhas(elemento("g-bairro"), {rotulo: "Notificações nas próximas 4 semanas no bairro", rotulosX: sem.rotulos, series, altura: 220});
}

function atualizarDetalhe(periodo, previstos, index, anual) {
  elemento("nome-bairro").textContent = dados.mapa[index].name;
  const selo = elemento("risco-bairro");
  const base = previstos?.[index] ?? periodo.observado?.[index];
  if (Number.isFinite(base)) {
    const nivel = RISCO[nivelRisco(base)];
    selo.className = "risco " + nivel.classe;
    selo.textContent = nivel.nome + (previstos ? " previsto" : " (dado real)");
    selo.hidden = false;
  } else selo.hidden = true;
  elemento("rotulo-previsto").textContent = "Previstas " + (anual ? "no ano" : "no mês");
  elemento("rotulo-observado").textContent = "Reais " + (anual ? "no ano" : "no mês");
  elemento("previsto").textContent = num(previstos?.[index]);
  elemento("observado").textContent = num(periodo.observado?.[index]);
  elemento("referencia").textContent = previstos
    ? anual ? `Base até ${dataCompleta(periodo.data_corte)} · ${dados.metodo_anual}` : "Emissão em " + dataCompleta(periodo.emissao)
    : "Previsão indisponível para o período selecionado.";
  desenharSerieBairro(index);
  elemento("titulo-detalhe").textContent = anual ? "Ano a ano" : "Semana a semana";
  elemento("coluna-periodo").textContent = anual ? "Ano" : "Semana";
  elemento("coluna-data").textContent = anual ? "Data de corte" : "Emissão";
  const corpo = elemento("semanas");
  corpo.replaceChildren();
  const prefixo = periodo.inicio.slice(0, 7);
  const linhas = anual ? dados.anos.slice().reverse()
    : dados.semanas.filter((item) => item.inicio.startsWith(prefixo) || item.fim.startsWith(prefixo));
  linhas.forEach((item) => {
    const linha = corpo.insertRow();
    if (anual && item.inicio === periodo.inicio) linha.setAttribute("aria-current", "true");
    const previsao = item[anual ? "sem" : cenario.value];
    [
      anual ? rotuloAno(item) : `${dataCurta(item.inicio)} a ${dataCurta(item.fim)}`,
      previsao ? (anual ? dataCompleta(item.data_corte) : dataCurta(item.emissao)) : "—",
      num(previsao?.[index]),
      num(item.observado?.[index]),
    ].forEach((valor) => { linha.insertCell().textContent = valor; });
  });
}

function atualizarGrafico(periodos, index, chave, anual) {
  const grafico = elemento("grafico");
  grafico.replaceChildren();
  elemento("titulo-serie").textContent = anual ? "Recife ano a ano" : "Recife mês a mês";
  const pontos = periodos.map((p) => [soma(p.observado), soma(p[chave])]);
  const maximo = Math.max(1, ...pontos.flat().filter(Number.isFinite));
  const passo = Math.pow(10, Math.floor(Math.log10(maximo))) / 2;
  const maior = Math.ceil(maximo / passo) * passo;
  const eixo = elemento("eixo-grafico");
  eixo.replaceChildren();
  for (const valor of [maior, maior / 2, 0]) {
    const etiqueta = document.createElement("span");
    etiqueta.textContent = num(valor);
    eixo.append(etiqueta);
  }
  pontos.forEach(([observado, previsto], i) => {
    const periodo = periodos[i];
    const botao = document.createElement("button");
    botao.type = "button";
    const curto = anual ? rotuloAno(periodo) : formatoMesCurto.format(new Date(periodo.inicio)).replace(".", "");
    const nome = anual ? curto : formatoMes.format(new Date(periodo.inicio));
    const obs = Number.isFinite(observado) ? `${num(observado)} notificações observadas` : "sem total observado";
    const prev = Number.isFinite(previsto) ? `${num(previsto)} notificações previstas` : "sem previsão";
    botao.title = `${nome} · ${obs} · ${prev}`;
    botao.setAttribute("aria-label", botao.title);
    botao.setAttribute("aria-pressed", String(i === index));
    const barras = document.createElement("span");
    barras.className = "barras";
    barras.setAttribute("aria-hidden", "true");
    for (const valor of [observado, previsto]) {
      const barra = document.createElement("span");
      barra.className = "barra";
      barra.style.setProperty("--altura", Number.isFinite(valor) ? `${100 * valor / maior}%` : "0%");
      barras.append(barra);
    }
    botao.append(barras, curto);
    botao.addEventListener("click", () => {
      (anual ? ano : mes).value = String(i);
      atualizar();
      grafico.children[i].focus();
    });
    grafico.append(botao);
  });
}

function atualizar() {
  const anual = visao === "anual";
  const periodos = anual ? dados.anos : dados.meses;
  const indexPeriodo = Number((anual ? ano : mes).value);
  const periodo = periodos[indexPeriodo];
  const chave = anual ? "sem" : cenario.value;
  const previsto = periodo[chave];
  const totalPrev = soma(previsto);
  const totalObs = soma(periodo.observado);
  const anterior = soma(periodos[indexPeriodo - 1]?.observado);
  const indexBairro = Number(bairro.value);
  elemento("ver-mes").setAttribute("aria-pressed", String(!anual));
  elemento("ver-ano").setAttribute("aria-pressed", String(anual));
  elemento("filtro-mes").hidden = anual;
  elemento("filtro-ano").hidden = !anual;
  elemento("filtro-cenario").hidden = anual;
  elemento("titulo-total").textContent = anual ? "Recife no ano" : "Recife no mês";
  elemento("titulo-mapa").textContent = anual ? "Risco no ano" : "Risco no mês";
  elemento("rotulo-periodo").textContent = anual ? rotuloAno(periodo) : formatoMes.format(new Date(periodo.inicio));
  elemento("situacao").textContent = anual
    ? (periodo.tipo === "estimativa" ? "Estimativa para 2026" : periodo.tipo === "teste" ? "Previsão anual (sem clima)" : "Só dados reais neste ano")
    : previsto ? "" : "Sem previsão neste mês: faltam dados de clima.";

  elemento("total-previsto").textContent = num(totalPrev);
  elemento("total-observado").textContent = num(totalObs);
  let diferenca;
  if (Number.isFinite(totalPrev) && Number.isFinite(totalObs)) {
    elemento("rotulo-diferenca").textContent = "Diferença";
    diferenca = Math.round(totalPrev) - totalObs;
  } else {
    elemento("rotulo-diferenca").textContent = anual ? "Vs. ano anterior" : "Vs. mês anterior";
    diferenca = (Number.isFinite(totalObs) ? totalObs : Math.round(totalPrev)) - anterior;
  }
  elemento("total-diferenca").textContent = diferenca > 0 ? "+" + num(diferenca) : num(diferenca);
  elemento("analise").textContent = descrever(totalPrev, totalObs, anterior, anual, periodo);
  const nota = elemento("nota-metodo");
  nota.hidden = !anual || !previsto || periodo.tipo !== "teste";
  if (!nota.hidden) {
    const anosTeste = periodos.filter((p) => p.tipo === "teste");
    const erros = anosTeste.map((p) => `${rotuloAno(p)}: ${num(Math.abs(soma(p.sem) - soma(p.observado)))}`);
    nota.textContent = `Erro no total do ano: ${erros.join(" · ")}.`;
  }
  atualizarMapa(periodo, previsto, indexBairro);
  atualizarDetalhe(periodo, previsto, indexBairro, anual);
  atualizarGrafico(periodos, indexPeriodo, chave, anual);
}

if (dados?.anos?.length) montar();
else elemento("situacao").textContent = "Os dados do painel não foram carregados.";
