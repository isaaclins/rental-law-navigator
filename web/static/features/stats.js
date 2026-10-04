// Protections over time: top of "What's changing" (#/changes). Self-contained feature module on window.CE
// (web/DESIGN.md). One row per protection type, a step line of how many of the 10 covered cities have it in force,
// 2019 to the end of 2027; a state law counts for every city in that state. Data: GET /api/stats/protections
// (web/stats.py, computed from output/rules.json with the evaluator's date logic). Nothing here is hardcoded:
// the headline, the steps and the counts all come from that endpoint.
// Colour = status (in force / enacted but later / pending / failed); the as-of line is the app's as-of date.
// Motion explains: the lines draw forward through time once, when the chart scrolls into view, and the as-of line
// moves with the date. Transform/opacity/stroke only; prefers-reduced-motion shows the final state.

const CE = window.CE;
const NS = "http://www.w3.org/2000/svg";
const RM = matchMedia("(prefers-reduced-motion: reduce)");
const DRAW_MS = 1400;
const ASOF_MIN = "2020-01-01", ASOF_MAX = "2030-12-31"; // the header control's range
const esc = (s) => CE.escape(s ?? "");

// ------------------------------------------------------------------ i18n --
const EN = {
  names: {
    rent_cap: "Rent cap", just_cause: "Just-cause eviction", deposit_cap: "Deposit cap",
    fee_cap: "Application-fee cap", source_of_income: "Source-of-income protection", algorithmic_ban: "Algorithmic rent-setting ban",
  },
  plural: {
    rent_cap: "Rent caps", just_cause: "Just-cause eviction rules", deposit_cap: "Deposit caps",
    fee_cap: "Application-fee caps", source_of_income: "Source-of-income protections", algorithmic_ban: "Algorithmic rent-setting bans",
  },
  headline: (p, a, b, y1, y2) => `${p} went from ${a} to ${b} of 10 cities ${y1 === y2 ? `in ${y1}` : `between ${y1} and ${y2}`}.`,
  headline_now: (p, now, d, b, d2) => now === b ? `${p}: ${now} of 10 cities on ${d}.` : `${p}: ${now} of 10 cities on ${d}, ${b} by ${d2}.`, col: (d) => `on ${d}`,
  without: (cs, n) => `Not covered by the end of 2027: ${cs}.` + (n ? ` ${n === 1 ? "1 bill that would cover them is" : `${n} bills that would cover them are`} pending.` : ""),
  all: "All 10 cities by the end of 2027.",
  unknown: (n) => `${n} ${n === 1 ? "city" : "cities"}: we can't tell yet`,
  unknown_why: (p, cs) => `${p} in ${cs}: we can't tell yet. We couldn't read the city's own law text, so every answer there says so.`,
  and: "and",
  question: "How many of the 10 covered cities have each protection in force, 2019 to 2027",
  scheduled: "Enacted, starts later",
  if_passed: "if passed",
  of10: (n) => `${n} of 10`, of_10: "of 10",
  hint: "Tap a step for the law behind it. Tap anywhere else on a line to see the answers on that date.",
  hint_mouse: "Point at a step for the law behind it. Click anywhere else on a line to see the answers on that date.",
  source: (used, total, file) => `Source: ${used} of our ${total} rules, dated with the same logic as the address answers. A state law counts for each of its cities. In force in a city does not mean every building there is covered.`,
  before: "Before 2019", since: (y) => `since ${y}`, undated: "no start date in our sources",
  adds: (cs) => `+ ${cs}`, removes: (cs) => `− ${cs}`,
  would_add: (cs) => `would add ${cs}`, would_have: (cs) => `would have added ${cs}`, nothing_new: "no city not already covered",
  src: "Source", go: (d) => `See the answers on ${d}`,
  list: "Show as a list", th_p: "Protection", th_d: "Date", th_n: "Cities", th_l: "Law",
  step_aria: (p, d, n) => `${p}, ${d}: ${n} of 10 cities. Show the law.`,
  close: "Close",
};
const ES = {
  names: {
    rent_cap: "Tope de alquiler", just_cause: "Desalojo solo con causa justa", deposit_cap: "Tope del depósito",
    fee_cap: "Tope de la tarifa de solicitud", source_of_income: "Protección por fuente de ingresos", algorithmic_ban: "Prohibición de fijar alquileres con algoritmos",
  },
  plural: {
    rent_cap: "Los topes de alquiler", just_cause: "Las normas de desalojo con causa justa", deposit_cap: "Los topes del depósito",
    fee_cap: "Los topes de la tarifa de solicitud", source_of_income: "Las protecciones por fuente de ingresos", algorithmic_ban: "Las prohibiciones de fijar alquileres con algoritmos",
  },
  headline: (p, a, b, y1, y2) => `${p} pasaron de ${a} a ${b} de las 10 ciudades ${y1 === y2 ? `en ${y1}` : `entre ${y1} y ${y2}`}.`,
  headline_now: (p, now, d, b, d2) => now === b ? `${p}: ${now} de 10 ciudades al ${d}.` : `${p}: ${now} de 10 ciudades al ${d}, ${b} para ${d2}.`, col: (d) => `al ${d}`,
  without: (cs, n) => `Sin cobertura a finales de 2027: ${cs}.` + (n ? ` ${n === 1 ? "Hay 1 proyecto de ley pendiente que las cubriría" : `Hay ${n} proyectos de ley pendientes que las cubrirían`}.` : ""),
  all: "Las 10 ciudades a finales de 2027.",
  unknown: (n) => `${n} ${n === 1 ? "ciudad" : "ciudades"}: aún no sabemos`,
  unknown_why: (p, cs) => `${p} en ${cs}: aún no sabemos. No pudimos leer el texto de la ley de la ciudad, así que cada respuesta allí lo dice.`,
  and: "y",
  question: "En cuántas de las 10 ciudades cubiertas rige cada protección, de 2019 a 2027",
  scheduled: "Aprobada, entra en vigor más tarde",
  if_passed: "si se aprueba",
  of10: (n) => `${n} de 10`, of_10: "de 10",
  hint: "Toque un escalón para ver la ley. Toque en otro punto de una línea para ver las respuestas en esa fecha.",
  hint_mouse: "Señale un escalón para ver la ley. Haga clic en otro punto de una línea para ver las respuestas en esa fecha.",
  source: (used, total, file) => `Fuente: ${used} de nuestras ${total} normas, fechadas con la misma lógica que las respuestas por dirección. Una ley estatal cuenta para cada una de sus ciudades. Que rija en una ciudad no significa que cubra todos sus edificios.`,
  before: "Antes de 2019", since: (y) => `desde ${y}`, undated: "sin fecha de inicio en nuestras fuentes",
  adds: (cs) => `+ ${cs}`, removes: (cs) => `− ${cs}`,
  would_add: (cs) => `añadiría ${cs}`, would_have: (cs) => `habría añadido ${cs}`, nothing_new: "ninguna ciudad que no esté ya cubierta",
  src: "Fuente", go: (d) => `Ver las respuestas al ${d}`,
  list: "Ver como lista", th_p: "Protección", th_d: "Fecha", th_n: "Ciudades", th_l: "Ley",
  step_aria: (p, d, n) => `${p}, ${d}: ${n} de 10 ciudades. Ver la ley.`,
  close: "Cerrar",
};
const L = () => (CE.lang() === "es" ? ES : EN);
const joinList = (xs) => (xs.length < 2 ? xs.join("") : `${xs.slice(0, -1).join(", ")} ${L().and} ${xs[xs.length - 1]}`);

// ------------------------------------------------------------------ state --
let drawn = false;     // the chart draws itself once per visit to the site, then shows its final state
let shownAsOf = null;  // where the as-of line was last drawn, so it moves from there after a re-render
let cur = null;        // { root, data, geo } of the mounted chart

const day = (d) => Date.UTC(+d.slice(0, 4), +d.slice(5, 7) - 1, +d.slice(8, 10));
const isoOf = (ms) => new Date(ms).toISOString().slice(0, 10);
const countOn = (p, d) => p.steps.reduce((n, s) => (s.date <= d ? s.count : n), p.initial.count);
const statusOn = (date, asOf) => (date && date > asOf ? "not_yet_effective" : "in_force");

function svg(tag, attrs = {}, parent) {
  const el = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  parent?.append(el);
  return el;
}

// ------------------------------------------------------------------ mount --
async function mount() {
  if (!/^#\/changes(\/|\?|$)/.test(location.hash)) return;
  const main = document.getElementById("main");
  let host = main.querySelector('[data-slot="changes-top"]');
  if (!host) { // no slot on this build: insert right after the page head
    const head = main.querySelector(".page-head");
    if (!head) return;
    host = head.nextElementSibling?.matches("[data-pt-host]") ? head.nextElementSibling : document.createElement("div");
    host.dataset.ptHost = "";
    head.after(host);
  }
  if (host.querySelector(".pt")) return;
  const lang = CE.lang();
  let data;
  try { data = await CE.api(`/api/stats/protections?lang=${lang}`); } catch { return; } // the page works without it
  if (!host.isConnected || host.querySelector(".pt") || CE.lang() !== lang) return;
  render(host, data);
}

function headNow(h, hp, asOf) {
  const l = L(), last = hp?.steps.filter((s) => s.count === h.to).map((s) => s.date)[0];
  const month = last ? new Date(last + "T12:00:00").toLocaleDateString(CE.lang() === "es" ? "es-US" : "en-US", { month: "short", year: "numeric" }) : String(h.to_year);
  return hp ? l.headline_now(l.plural[h.protection], countOn(hp, asOf), CE.fmtDate(asOf), h.to, month) : l.headline(l.plural[h.protection], h.from, h.to, h.from_year, h.to_year);
}
function render(host, data) {
  const l = L(), h = data.headline, asOf = CE.asOf();
  const hp = h && data.protections.find((p) => p.id === h.protection);
  const rows = data.protections.map((p) => `
    <div class="pt-row" data-p="${p.id}">
      <div class="pt-name">${esc(l.names[p.id])}</div>
      <div class="pt-val" data-val></div>
      <div class="pt-plot"></div>
    </div>`).join("");
  const years = [];
  for (let y = +data.start.slice(0, 4); y <= +data.end.slice(0, 4); y++) years.push(y);
  host.innerHTML = `
    <section class="block pt" aria-labelledby="pt-h">
      <h2 id="pt-h" class="pt-h" data-pt-h>${h ? esc(headNow(h, hp, asOf)) : esc(l.question)}</h2>
      ${hp ? `<p class="pt-sub">${esc(h.without.length ? l.without(joinList(h.without), h.pending_bills) : l.all)}</p>` : ""}
      ${data.protections.filter((p) => p.unknown?.cities.length).map((p) => `<p class="pt-sub">${esc(l.unknown_why(l.names[p.id], joinList(p.unknown.cities)))}</p>`).join("")}
      <p class="pt-q">${esc(l.question)}</p>
      <ul class="pt-legend">
        <li><i class="pt-sw in"></i>${esc(CE.t("r_in_force"))}</li>
        <li><i class="pt-sw soon"></i>${esc(l.scheduled)}</li>
        <li><i class="pt-sw pend"></i>${esc(CE.t("r_pending"))} (${esc(l.if_passed)})</li>
        <li><i class="pt-sw fail"></i>${esc(CE.t("r_failed"))}</li>
        <li><i class="pt-sw asof"></i>${esc(CE.t("as_of"))} <span data-asof-legend></span></li>
      </ul>
      <div class="pt-chart">
        <div class="pt-rows"><div class="pt-row pt-headrow" aria-hidden="true"><div class="pt-name"></div><div class="pt-val pt-colh" data-colh></div><div class="pt-plot"></div></div>${rows}</div>
        <div class="pt-axis" aria-hidden="true"><div class="pt-axis-in">${years.map((y) => `<span data-y="${y}">${y}</span>`).join("")}<span class="pt-notlaw">${esc(CE.t("not_law"))}</span><span class="pt-asof-l"></span></div></div>
        <div class="pt-tip" role="dialog" aria-modal="false" hidden></div>
      </div>
      <p class="pt-hint">${esc(matchMedia("(hover: hover)").matches ? l.hint_mouse : l.hint)}</p>
      <p class="pt-src">${esc(l.source(data.source.rules_used, data.source.rules_total, data.source.rules_file || "rules.json"))}</p>
      <details class="pt-data"><summary>${esc(l.list)}</summary>${listHTML(data)}</details>
    </section>`;
  const root = host.querySelector(".pt");
  cur = { root, data };
  layout();
  update(asOf, { from: shownAsOf });
  wire(root);
  if (drawn || RM.matches) { root.classList.add("pt-drawn", "pt-static"); drawn = true; return; }
  root.classList.add("pt-armed");
  const io = new IntersectionObserver((es) => {
    if (!es.some((e) => e.isIntersecting)) return;
    io.disconnect();
    drawn = true;
    void root.offsetWidth; // commit the undrawn state before the transition starts
    root.classList.add("pt-drawn");
  }, { threshold: 0.35 });
  io.observe(root.querySelector(".pt-rows"));
}

// ------------------------------------------------------------------ geometry --
// Each row's plot is an SVG drawn in real pixels (so strokes and dots keep their size); rebuilt on resize.
const GUTTER = 44; // right column for pending bills and failed measures ("Not law")
function geometry(root) {
  const plot = root.querySelector(".pt-plot");
  const w = Math.max(160, plot.clientWidth), hgt = plot.clientHeight || 44;
  const t0 = day(cur.data.start), t1 = day(cur.data.end) + 864e5;
  const pw = w - GUTTER;
  return {
    w, h: hgt, pw, t0, t1,
    x: (d) => Math.max(0, Math.min(pw, ((day(d) - t0) / (t1 - t0)) * pw)),
    y: (n) => 20 + (1 - n / 10) * (hgt - 26), // room above the top line for the count labels
    gx: pw + GUTTER / 2,
    left: plot.offsetLeft,
  };
}

function layout() {
  const { root, data } = cur;
  const g = (cur.geo = geometry(root));
  root.querySelectorAll(".pt-row[data-p]").forEach((row) => {
    const p = data.protections.find((x) => x.id === row.dataset.p);
    row.querySelector(".pt-plot").replaceChildren(rowSVG(p, g));
  });
  // axis labels and the as-of overlay share the plot column
  const axis = root.querySelector(".pt-axis-in");
  axis.style.marginLeft = g.left + "px";
  axis.style.width = g.w + "px";
  const nl = axis.querySelector(".pt-notlaw");
  nl.style.left = g.gx + "px";
  // year labels: show only the ones that fit (no run-together years, nothing under "Not law yet")
  const stop = g.gx - nl.offsetWidth / 2 - 6;
  let edge = -Infinity;
  axis.querySelectorAll("[data-y]").forEach((s) => {
    const x = g.x(`${s.dataset.y}-01-01`);
    s.style.left = x + "px";
    const fits = x >= edge + 8 && x + s.offsetWidth <= stop;
    s.style.visibility = fits ? "visible" : "hidden";
    if (fits) edge = x + s.offsetWidth;
  });
}

function rowSVG(p, g) {
  const s = svg("svg", { width: g.w, height: g.h, viewBox: `0 0 ${g.w} ${g.h}`, class: "pt-svg", "aria-hidden": "true" });
  // recessive frame: 0 and 10 cities, one tick per year, the "Not law" column divider
  svg("line", { x1: 0, x2: g.w, y1: g.y(0), y2: g.y(0), class: "pt-base" }, s);
  svg("line", { x1: 0, x2: g.pw, y1: g.y(10), y2: g.y(10), class: "pt-grid" }, s);
  for (let y = +cur.data.start.slice(0, 4) + 1; y <= +cur.data.end.slice(0, 4); y++) {
    const x = g.x(`${y}-01-01`);
    svg("line", { x1: x, x2: x, y1: g.y(10), y2: g.y(0), class: "pt-grid" }, s);
  }
  svg("line", { x1: g.pw + 6, x2: g.pw + 6, y1: g.y(10) - 2, y2: g.y(0), class: "pt-gutter" }, s);
  // the step path, with the path length at each step (dots appear when the drawing line reaches them)
  let d = `M0 ${g.y(p.initial.count)}`, len = 0, px = 0, py = g.y(p.initial.count);
  const at = [];
  for (const st of p.steps) {
    const x = g.x(st.date), y = g.y(st.count);
    len += x - px; d += ` H${x}`;
    len += Math.abs(y - py); d += ` V${y}`;
    at.push({ st, x, y, len });
    px = x; py = y;
  }
  len += g.pw - px; d += ` H${g.pw}`;
  // two plain paths, split by update(): in force, then "starts later" (no clip-path: WebKit drops flat clipped paths)
  svg("path", { d: `${d} V${g.y(0)} H0 Z`, class: "pt-area pt-late", style: "--at:1" }, s);
  // the count at each step, where there is room (and at the start)
  let lastX = -99;
  const lab = (x, y, n) => { if (x - lastX < 26) return; lastX = x; const tx = svg("text", { x: Math.min(x + 4, g.pw - 8), y: y - 6, class: "pt-n pt-late" }, s); tx.textContent = n; };
  if (p.initial.count) lab(2, g.y(p.initial.count), p.initial.count);
  for (const a of at) lab(a.x, a.y, a.st.count);
  svg("path", { class: "pt-line in" }, s);
  svg("path", { class: "pt-line soon" }, s);
  // pending bills: a dashed continuation into the "Not law" column, up to the count if they pass
  const top = (xs) => new Map(xs.length ? [[Math.max(...xs.map((x) => x.count_if_passed)), xs]] : []);
  const pend = top(p.pending), fail = top(p.failed);
  const px2 = pend.size && fail.size ? g.gx - 9 : g.gx, fx = pend.size && fail.size ? g.gx + 9 : g.gx;
  for (const [n] of pend) {
    svg("path", { d: `M${g.pw} ${py} H${px2} V${g.y(n)}`, class: "pt-pend pt-late" }, s);
    svg("circle", { cx: px2, cy: g.y(n), r: 4, class: "pt-pend-dot pt-late" }, s);
  }
  // failed measures: a short struck marker at the count they would have reached
  for (const [n] of fail) {
    const y = g.y(n);
    svg("line", { x1: fx - 7, x2: fx + 7, y1: y, y2: y, class: "pt-fail pt-late" }, s);
    svg("line", { x1: fx - 4, x2: fx + 4, y1: y - 5, y2: y + 5, class: "pt-fail pt-late" }, s);
  }
  // the as-of line (moved by update())
  svg("line", { x1: 0, x2: 0, y1: 0, y2: g.h, class: "pt-now" }, s);
  // step dots (status by the as-of date) and hit targets, merged when closer than a finger
  const marks = [];
  if (p.initial.laws.length) marks.push({ kind: "initial", x: 0, y: g.y(p.initial.count), len: 0, items: [p.initial] });
  for (const a of at) {
    svg("circle", { cx: a.x, cy: a.y, r: 4, class: "pt-dot pt-late", "data-date": a.st.date, style: `--at:${a.len / len}` }, s);
    const last = marks[marks.length - 1];
    if (last && last.kind === "step" && a.x - last.x < 22) { last.items.push(a.st); last.x2 = a.x; }
    else marks.push({ kind: "step", x: a.x, y: a.y, items: [a.st] });
  }
  if (p.initial.laws.length) svg("circle", { cx: 2, cy: g.y(p.initial.count), r: 3, class: "pt-dot0 pt-late", style: "--at:0" }, s);
  for (const [n, xs] of pend) marks.push({ kind: "pending", x: px2, y: g.y(n), items: xs });
  for (const [n, xs] of fail) marks.push({ kind: "failed", x: fx, y: g.y(n), items: xs });
  const half = matchMedia("(pointer: coarse)").matches ? 22 : 12; // a finger-wide (44 px) target on touch
  marks.forEach((m, i) => {
    const x0 = Math.max(-2, Math.min(m.x, m.x2 ?? m.x) - half), x1 = Math.max(Math.max(m.x, m.x2 ?? m.x) + half, x0 + 2 * half);
    const r = svg("rect", { x: x0, y: 0, width: x1 - x0, height: g.h, class: "pt-hit", tabindex: 0, role: "button", "data-mark": i, ...(m.kind === "step" ? { "data-dates": m.items.map((x) => x.date).join(" ") } : { "data-kind": m.kind }) }, s);
    r.setAttribute("aria-label", markAria(p, m));
    r.addEventListener("pointerenter", (e) => { if (e.pointerType === "mouse") showTip(p, m, r, false); });
    r.addEventListener("pointerleave", (e) => { if (e.pointerType === "mouse") hideTip(false); });
    r.addEventListener("click", (e) => { e.stopPropagation(); showTip(p, m, r, true); });
    r.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); showTip(p, m, r, true); } });
  });
  // anywhere else on the line: move the app's as-of date there
  s.addEventListener("click", (e) => {
    const box = s.getBoundingClientRect(), x = e.clientX - box.left;
    if (x > g.pw) return;
    let d = isoOf(g.t0 + (x / g.pw) * (g.t1 - g.t0));
    d = d < ASOF_MIN ? ASOF_MIN : d > ASOF_MAX ? ASOF_MAX : d;
    hideTip(true);
    CE.setAsOf(d);
  });
  return s;
}

function markAria(p, m) {
  const l = L();
  if (m.kind === "initial") return l.step_aria(l.names[p.id], l.before, p.initial.count);
  if (m.kind === "step") { const s = m.items[m.items.length - 1]; return l.step_aria(l.names[p.id], CE.fmtDate(s.date), s.count); }
  return `${l.names[p.id]}: ${CE.t(m.kind === "pending" ? "r_pending" : "r_failed")}, ${m.items.map((x) => x.title).join("; ")}`;
}

// ------------------------------------------------------------------ as-of --
function update(asOf, { from = null } = {}) {
  if (!cur) return;
  const { root, data, geo: g } = cur;
  root.querySelector("[data-asof-legend]").textContent = CE.fmtDate(asOf);
  root.querySelector("[data-colh]").textContent = L().col(CE.fmtDate(asOf));
  const hd = root.querySelector("[data-pt-h]"), h = data.headline, hp = h && data.protections.find((p) => p.id === h.protection);
  if (hd && hp) hd.textContent = headNow(h, hp, asOf);
  root.querySelectorAll(".pt-row[data-p]").forEach((row) => {
    const p = data.protections.find((x) => x.id === row.dataset.p);
    const unk = p.unknown?.cities || []; // only-unverified cities: the address answers there are "unknown"
    row.querySelector("[data-val]").innerHTML = `<b>${countOn(p, asOf)}</b> <span>${esc(L().of_10)}</span>`
      + (unk.length ? `<span class="pt-unk">${esc(L().unknown(unk.length))}</span>` : "");
    row.querySelectorAll(".pt-dot").forEach((c) => c.classList.toggle("soon", c.dataset.date > asOf));
    splitLine(row, p, g, asOf);
  });
  const label = root.querySelector(".pt-asof-l");
  root.classList.toggle("pt-out", asOf < data.start || asOf > data.end);
  label.textContent = CE.fmtDate(asOf);
  const place = (d) => {
    const x = d < data.start ? 0 : d > data.end ? g.pw : g.x(d);
    root.querySelectorAll(".pt-now").forEach((r) => { r.style.transform = `translateX(${x}px)`; });
    // keep the date label inside the chart: anchor it left or right near the edges
    const anchor = x < 48 ? "0%" : x > g.pw - 48 ? "-100%" : "-50%";
    label.style.transform = `translateX(${x}px) translateX(${anchor})`;
  };
  // first placement jumps; later ones move from where the line was
  root.classList.add("pt-still");
  place(from && !RM.matches ? from : asOf);
  void root.offsetWidth;
  root.classList.remove("pt-still");
  place(asOf);
  shownAsOf = asOf;
}

// The line is in force up to the first step that starts after the as-of date and rises above the count in force
// then; from that corner on it is "enacted, starts later". Each part draws for its share of the drawing time.
function splitLine(row, p, g, asOf) {
  const c0 = countOn(p, asOf);
  const pts = [[0, g.y(p.initial.count)]];
  let cut = null, prev = p.initial.count;
  for (const st of p.steps) {
    const x = g.x(st.date);
    if (cut === null && st.date > asOf && st.count > c0) cut = pts.length;
    pts.push([x, g.y(prev)], [x, g.y(st.count)]);
    prev = st.count;
  }
  pts.push([g.pw, g.y(prev)]);
  const a = cut === null ? pts : pts.slice(0, cut + 1), b = cut === null ? [] : pts.slice(cut);
  const length = (ps) => ps.slice(1).reduce((n, q, i) => n + Math.abs(q[0] - ps[i][0]) + Math.abs(q[1] - ps[i][1]), 0);
  const la = length(a), lb = length(b), total = la + lb || 1;
  const set = (el, ps, len, start) => {
    el.setAttribute("d", ps.length > 1 ? "M" + ps.map((q) => q.join(" ")).join(" L") : "");
    el.style.strokeDasharray = `${len + 1}px ${len + 1}px`;
    el.style.setProperty("--len", `${len + 1}px`);
    el.style.setProperty("--dur", `${(DRAW_MS * len) / total}ms`);
    el.style.setProperty("--del", `${(DRAW_MS * start) / total}ms`);
  };
  set(row.querySelector(".pt-line.in"), a, la, 0);
  set(row.querySelector(".pt-line.soon"), b, lb, la);
}

// ------------------------------------------------------------------ tooltip --
let pinned = false;
function showTip(p, m, target, pin) {
  if (!cur) return;
  if (!pin && pinned) return;
  pinned = pin;
  const l = L(), asOf = CE.asOf(), tip = cur.root.querySelector(".pt-tip");
  const link = (u) => (u ? ` · <a href="${esc(u)}" target="_blank" rel="noopener">${esc(l.src)}</a>` : "");
  const jur = (j) => (j && j.length === 2 ? j : (j || "").replace(/, [A-Z]{2}$/, ""));
  let html = "";
  if (m.kind === "initial") {
    html = `<p class="pt-tip-h"><b>${esc(l.before)}</b> · ${esc(l.of10(p.initial.count))}</p>` + p.initial.laws.map((x) =>
      `<p>${CE.badge("in_force")} ${esc(jur(x.jurisdiction))}: ${esc(x.title)} (${esc(x.date ? l.since(x.date.slice(0, 4)) : l.undated)})${link(x.source_url)}</p>`).join("");
  } else if (m.kind === "step") {
    const go = (d) => (d >= ASOF_MIN && d <= ASOF_MAX && d !== asOf ? `<p class="pt-tip-go"><button type="button" class="linkish" data-go="${d}">${esc(l.go(CE.fmtDate(d)))}</button></p>` : "");
    html = m.items.map((s) => `<p class="pt-tip-h"><b>${esc(CE.fmtDate(s.date))}</b> · ${esc(l.of10(s.count))}</p>` + s.laws.map((x) =>
      `<p>${CE.badge(x.change === "ends" ? "failed" : statusOn(s.date, asOf))} ${esc(jur(x.jurisdiction))}: ${esc(x.title)} · ${esc(x.change === "ends" ? l.removes(joinList(x.cities)) : l.adds(joinList(x.cities)))}${link(x.source_url)}</p>`).join("") + go(s.date)).join("");
  } else {
    const pend = m.kind === "pending";
    html = m.items.map((x) => `<p>${CE.badge(m.kind)} ${esc(jur(x.jurisdiction))}: ${esc(x.title)} · ${esc(x.cities.length ? (pend ? l.would_add : l.would_have)(joinList(x.cities)) : l.nothing_new)}${link(x.source_url)}</p>`).join("");
  }
  tip.innerHTML = `<button type="button" class="pt-tip-x" aria-label="${esc(l.close)}">×</button>${html}`;
  tip.hidden = false;
  tip.setAttribute("aria-label", target.getAttribute("aria-label") || "");
  // place it under the row, centred on the mark, inside the chart
  const chart = cur.root.querySelector(".pt-chart"), cb = chart.getBoundingClientRect();
  const row = target.closest(".pt-row"), rb = row.getBoundingClientRect(), tb = target.getBoundingClientRect();
  const w = Math.min(380, cb.width);
  tip.style.width = w + "px";
  const cx = tb.left + tb.width / 2 - cb.left;
  tip.style.left = Math.max(0, Math.min(cb.width - w, cx - w / 2)) + "px";
  tip.style.top = rb.bottom - cb.top + 4 + "px";
  tip.querySelector(".pt-tip-x").addEventListener("click", () => { hideTip(true); target.focus({ preventScroll: true }); });
  tip.querySelectorAll("[data-go]").forEach((b) => b.addEventListener("click", () => { hideTip(true); CE.setAsOf(b.dataset.go); }));
  cur.root.querySelectorAll(".pt-hit.on").forEach((h) => h.classList.remove("on"));
  target.classList.add("on");
}
function hideTip(force) {
  if (!cur || (pinned && !force)) return;
  pinned = false;
  const tip = cur.root.querySelector(".pt-tip");
  tip.hidden = true;
  cur.root.querySelectorAll(".pt-hit.on").forEach((h) => h.classList.remove("on"));
}

function wire(root) {
  let w = root.querySelector(".pt-plot").clientWidth;
  const ro = new ResizeObserver(() => {
    if (!root.isConnected) { ro.disconnect(); return; }
    const nw = root.querySelector(".pt-plot").clientWidth;
    if (nw === w) return;
    w = nw; hideTip(true);
    root.classList.add("pt-static");
    layout(); update(CE.asOf());
  });
  ro.observe(root.querySelector(".pt-rows"));
}
document.addEventListener("click", (e) => { if (cur && !e.target.closest(".pt-tip, .pt-hit")) hideTip(true); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") hideTip(true); });

// ------------------------------------------------------------------ list view --
function listHTML(data) {
  const l = L();
  const rows = [];
  for (const p of data.protections) {
    rows.push(`<tr><th scope="row">${esc(l.names[p.id])}</th><td>${esc(l.before)}</td><td>${p.initial.count}</td><td>${esc(p.initial.laws.map((x) => `${x.title} (${x.date ? l.since(x.date.slice(0, 4)) : l.undated})`).join("; ")) || "–"}</td></tr>`);
    for (const s of p.steps) rows.push(`<tr><th scope="row"><span class="sr">${esc(l.names[p.id])}</span></th><td>${esc(CE.fmtDate(s.date))}</td><td>${s.count}</td><td>${esc(s.laws.map((x) => `${x.title} (${l.adds(joinList(x.cities))})`).join("; "))}</td></tr>`);
    if (p.unknown?.cities.length) rows.push(`<tr><th scope="row"><span class="sr">${esc(l.names[p.id])}</span></th><td>${esc(l.unknown(p.unknown.cities.length))}</td><td>${p.unknown.cities.length}</td><td>${esc(joinList(p.unknown.cities))}</td></tr>`);
    for (const x of [...p.pending, ...p.failed]) rows.push(`<tr><th scope="row"><span class="sr">${esc(l.names[p.id])}</span></th><td>${esc(CE.t(p.pending.includes(x) ? "r_pending" : "r_failed"))}</td><td>${x.count_if_passed}</td><td>${esc(x.title)}</td></tr>`);
  }
  return `<div class="table-wrap"><table class="pt-table"><thead><tr><th>${esc(l.th_p)}</th><th>${esc(l.th_d)}</th><th>${esc(l.th_n)}</th><th>${esc(l.th_l)}</th></tr></thead><tbody>${rows.join("")}</tbody></table></div>`;
}

// ------------------------------------------------------------------ events --
document.addEventListener("ce:route", (e) => { cur = null; pinned = false; if (e.detail?.view === "changes") mount(); });
// CE.setAsOf re-renders the view right after ce:asof; wait a tick so the new chart moves the line from the old date.
document.addEventListener("ce:asof", (e) => setTimeout(() => { if (cur?.root.isConnected) update(e.detail.asOf, { from: shownAsOf }); }, 0));
if (document.getElementById("main")?.querySelector(".page-head")) mount(); // loaded after the first render
