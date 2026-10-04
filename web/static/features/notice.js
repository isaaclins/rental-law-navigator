// Rent-increase notice for a building (#96), the landlord-side twin of the renter letter (#122, features/letter.js).
// Route: #/notice/<addressId>?rent=2400&last=2026-01-01 or #/notice/p<propertyId>?rent=…&last=… (a saved property
// on My properties); optional &new=<amount>&start=<YYYY-MM-DD>&cpi=<%>. POST /api/notice fills a fixed template from
// the same engine as the rent check: the highest lawful rent, the start date (one increase a year where the rule says
// so) and the notice deadline. No AI writing. The side panel says what was checked against the rules in our sources;
// it is not a compliance certification. Names, unit and contact stay in this page (never sent, never stored).

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const CE = window.CE;

{
  const l = document.createElement("link");
  l.rel = "stylesheet"; l.href = new URL("./notice.css", import.meta.url).href;
  document.head.appendChild(l);
}

const EN = {
  back_props: "My properties", h: "Rent-increase notice", h_s: "Your notice", lang_g: "Language of the notice",
  side_h: "Checked against the law", side_p: "Drafted from the rules in our sources, as of {d}. Same engine as the rent check.",
  cur: "Current rent", last: "Last increase", new: "New rent", start: "Starts", cpi: "Local CPI change", cpi_ph: "%",
  new_hint: "Type a higher amount and the draft turns red.", quote: "quote", nla: "Not legal advice.", nla_body: "Check before sending.",
  need_rent: "Enter the current rent to draft the notice.", loading: "Drafting the notice…", err: "Something went wrong. Try again.",
  busy: "Too many checks. Wait a minute.", signin: "Open My properties (sign in or try the demo) to draft from a saved property.",
  hint: "Fill in the <mark>[yellow]</mark> parts. They stay on this device.", st_ok: "Checked", st_over: "Problem", st_info: "Note",
};
const ES = {
  back_props: "Mis propiedades", h: "Aviso de aumento de renta", h_s: "Su aviso", lang_g: "Idioma del aviso",
  side_h: "Revisado con la ley", side_p: "Redactado con las normas de nuestras fuentes, al {d}. El mismo motor que la revisión de renta.",
  cur: "Renta actual", last: "Último aumento", new: "Renta nueva", start: "Empieza", cpi: "Cambio del IPC local", cpi_ph: "%",
  new_hint: "Escriba un monto mayor y el borrador se pone en rojo.", quote: "cita", nla: "No es asesoría legal.", nla_body: "Revíselo antes de enviarlo.",
  need_rent: "Indique la renta actual para redactar el aviso.", loading: "Redactando el aviso…", err: "Algo salió mal. Inténtelo de nuevo.",
  busy: "Demasiadas consultas. Espere un minuto.", signin: "Abra Mis propiedades (inicie sesión o pruebe la demo) para redactar desde una propiedad guardada.",
  hint: "Complete las partes en <mark>[amarillo]</mark>. Se quedan en este dispositivo.", st_ok: "Revisado", st_over: "Problema", st_info: "Nota",
};
const t = (k, o = {}) => Object.entries(o).reduce((s, [a, b]) => s.replaceAll("{" + a + "}", b), (CE.lang() === "es" && ES[k]) || EN[k] || k);
const svg = (p) => `<svg class="ico" viewBox="0 0 24 24" aria-hidden="true">${p}</svg>`;
const I = {
  back: svg('<path d="m15 6-6 6 6 6"/>'), ext: svg('<path d="M14 5h5v5M19 5l-8 8M18 14v4a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h4"/>'),
  ok: svg('<path d="m5 12 4.5 4.5L19 7"/>'), over: svg('<path d="M7 7l10 10M17 7 7 17"/>'), info: svg('<path d="M12 11v6M12 7.5v.01"/>'),
};
const num = (s) => { const v = parseFloat(String(s ?? "").replace(/[$,\s%]/g, "")); return Number.isFinite(v) ? v : null; };
const money = (n) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 }).format(n);

// what the reader types into the draft: memory only
const vals = { tenant: "", unit: "", owner: "", contact: "", given: "" };

async function view(main, arg) {
  const LT = await import("./letter.js");
  const m = location.hash.match(/^#\/notice\/([^?]+)(?:\?(.*))?$/);
  if (!m) { CE.navigate("properties"); return; }
  const id = decodeURIComponent(m[1]);
  const q = new URLSearchParams(m[2] || "");
  const inp = { rent: q.get("rent") || "", last: q.get("last") || "", new: q.get("new") || "", start: q.get("start") || "", cpi: q.get("cpi") || "" };
  const ui = CE.lang();
  let docs = null, letterLang = null, seq = 0;

  // the building: a known address or a saved property
  let base, back, backLabel;
  if (/^p\d+$/i.test(id)) {
    let p = null;
    try {
      const r = await fetch("/api/properties", { credentials: "same-origin" });
      if (r.ok) p = (await r.json()).properties.find((x) => String(x.id) === id.slice(1));
    } catch { p = null; }
    if (!p) { main.innerHTML = `<article class="lt-view"><div class="empty">${esc(t("signin"))} <a href="#/properties">${esc(t("back_props"))}</a></div></article>`; return; }
    const facts = Object.fromEntries(Object.entries(p.facts || {}).filter(([k, v]) => v != null && k !== "certificate_of_occupancy_date"));
    base = { place: { state: p.state, jurisdiction: p.jurisdiction }, facts, address_text: p.matched_address || p.address };
    back = "#/properties"; backLabel = p.label || t("back_props");
  } else {
    const aid = id.toUpperCase();
    const a = (await CE.api("/api/addresses").catch(() => [])).find((x) => x.id === aid);
    if (!a) { CE.navigate("properties"); return; }
    base = { address_id: aid };
    back = `#/a/${aid}`; backLabel = a.street.toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
  }

  document.title = `${t("h")} · Clause & Effect`;
  const row = (k, type, extra = "") => `<label class="nt-row" data-k="${k}"><span>${esc(t(k === "rent" ? "cur" : k))}</span><input name="${k}" ${type} ${extra} value="${esc(inp[k])}" autocomplete="off"></label>`;
  main.innerHTML = `<article class="lt-view nt-view">
    <header class="lt-head">
      <a class="ck-back" href="${esc(back)}">${I.back}${esc(backLabel)}</a>
      <div class="lt-title"><h1><span class="lt-h-l">${esc(t("h"))}</span><span class="lt-h-s">${esc(t("h_s"))}</span></h1>
        <div class="lt-seg" role="group" aria-label="${esc(t("lang_g"))}"><button type="button" data-ll="en" lang="en"><span class="lt-ll">English</span><span class="lt-ls">EN</span></button><button type="button" data-ll="es" lang="es"><span class="lt-ll">Español</span><span class="lt-ls">ES</span></button></div></div>
    </header>
    <div class="lt-grid">
      <div class="lt-col"><div class="lt-sheet" aria-live="polite"><p class="lt-wait">${esc(t("loading"))}</p></div>
        ${LT.actsHtml("lt-acts-m")}<p class="lt-hint">${t("hint")}</p></div>
      <aside class="lt-side nt-side">
        <h2>${esc(t("side_h"))}</h2><p class="lt-side-p">${esc(t("side_p", { d: CE.fmtDate(CE.asOf()) }))}</p>
        <form class="nt-form" novalidate autocomplete="off">
          ${row("rent", 'inputmode="decimal" placeholder="$"')}
          ${row("last", 'type="date" min="2000-01-01" max="2035-12-31"')}
          ${row("new", 'inputmode="decimal" placeholder="$"')}
          ${row("start", 'type="date" min="2000-01-01" max="2035-12-31"')}
          ${row("cpi", `inputmode="decimal" placeholder="${esc(t("cpi_ph"))}"`, "")}
        </form>
        <p class="nt-hint">${esc(t("new_hint"))}</p>
        <ul class="lt-checks nt-checks"></ul>
        ${LT.actsHtml("lt-acts-d")}
        <p class="lt-nla"><strong>${esc(t("nla"))}</strong> ${esc(t("nla_body"))} <a class="nt-help" href="#" target="_blank" rel="noopener" hidden></a></p>
      </aside>
    </div></article>`;
  const art = $(".nt-view", main), sheet = $(".lt-sheet", main), side = $(".nt-side", main), form = $(".nt-form", main);
  const lang = () => letterLang || ui;
  const cpiRow = $('.nt-row[data-k="cpi"]', form);
  cpiRow.hidden = !inp.cpi;

  const draw = (animate) => {
    if (!docs) return;
    const d = docs[lang()];
    sheet.lang = d.lang;
    sheet.innerHTML = LT.letterHtml(d, vals);
    sheet.classList.toggle("lt-anim", !!animate);
    sheet.classList.toggle("is-over", !!d.over);
    $$(".lt-seg button", main).forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.ll === d.lang)));
    $$(".lt-f", sheet).forEach(LT.fit);
  };
  const drawSide = (animate) => {
    const d = docs[ui];
    const ul = $(".nt-checks", side);
    ul.innerHTML = d.checks.map((c, i) => `<li style="--i:${i}" class="nt-${c.st}"><span class="lt-ok nt-ic" title="${esc(t("st_" + c.st))}">${I[c.st]}</span><span><b>${esc(c.t)}</b><span>${esc(c.s)}</span>
      ${c.quote ? `<details class="nt-q"><summary>${esc(c.cite || "")} · ${esc(t("quote"))}</summary><blockquote>“${esc(c.quote)}”</blockquote>${c.url ? `<a href="${esc(c.url)}" target="_blank" rel="noopener">${esc(new URL(c.url).hostname.replace(/^www\./, ""))}${I.ext}</a>` : ""}</details>`
        : c.url ? `<a class="nt-src" href="${esc(c.url)}" target="_blank" rel="noopener">${esc(new URL(c.url).hostname.replace(/^www\./, ""))}${I.ext}</a>` : ""}</span></li>`).join("");
    side.classList.toggle("lt-anim", !!animate);
    const help = $(".nt-help", side);
    help.hidden = !d.help?.url; help.href = d.help?.url || "#"; help.innerHTML = `${esc(d.help?.name || "")}${I.ext}`;
    if (d.checks.some((c) => c.need === "cpi")) cpiRow.hidden = false;
    const n = $('input[name="new"]', form), s = $('input[name="start"]', form);
    if (!inp.new) { n.value = ""; n.placeholder = d.new_rent ? money(d.new_rent) : "$"; }
    if (!inp.start) { s.value = d.start; s.dataset.auto = "1"; }
    form.querySelector('.nt-row[data-k="new"]').classList.toggle("is-over", !!d.over && !!d.new_rent);
  };

  async function load(animate) {
    const my = ++seq;
    const rent = num(inp.rent);
    if (!rent) { sheet.innerHTML = `<p class="lt-wait">${esc(t("need_rent"))}</p>`; $(".nt-checks", side).innerHTML = ""; return; }
    const body = { ...base, current_rent: rent, as_of: CE.asOf() };
    if (/^\d{4}-\d\d-\d\d$/.test(inp.last)) body.last_increase = inp.last;
    if (num(inp.new)) body.new_rent = num(inp.new);
    if (/^\d{4}-\d\d-\d\d$/.test(inp.start)) body.start = inp.start;
    if (inp.cpi !== "" && num(inp.cpi) != null) body.cpi = num(inp.cpi);
    try {
      const [en, es] = await Promise.all(["en", "es"].map((l) => LT.post("/api/notice", { ...body, lang: l })));
      if (my !== seq || !main.contains(sheet)) return;
      docs = { en, es };
      draw(animate); drawSide(animate);
    } catch (e) {
      if (my !== seq) return;
      sheet.innerHTML = `<p class="lt-wait">${esc(e.status === 429 ? t("busy") : t("err"))}</p>`;
    }
  }
  const syncUrl = () => {
    const p = new URLSearchParams();
    for (const k of ["rent", "last", "new", "start", "cpi"]) if (inp[k]) p.set(k, inp[k]);
    history.replaceState(history.state, "", `#/notice/${encodeURIComponent(id)}${p.toString() ? "?" + p : ""}`);
  };
  let timer;
  form.addEventListener("input", (e) => {
    const el = e.target;
    if (!el.name) return;
    inp[el.name] = el.value.trim();
    if (el.name === "start") delete el.dataset.auto;
    clearTimeout(timer);
    timer = setTimeout(() => { syncUrl(); load(false); }, el.type === "date" ? 50 : 380);
  });
  form.addEventListener("submit", (e) => e.preventDefault());
  $(".lt-seg", main).addEventListener("click", (e) => {
    const b = e.target.closest("button[data-ll]");
    if (!b || !docs || b.dataset.ll === lang()) return;
    letterLang = b.dataset.ll; draw(true);
  });
  sheet.addEventListener("input", (e) => {
    const el = e.target.closest(".lt-f");
    if (!el) return;
    vals[el.dataset.f] = el.value;
    $$(`.lt-f[data-f="${el.dataset.f}"]`, sheet).forEach((x) => { if (x !== el) x.value = el.value; LT.fit(x); });
    $$(`.lt-fp[data-fp="${el.dataset.f}"]`, sheet).forEach((x) => (x.textContent = el.value.trim()));
  });
  sheet.addEventListener("keydown", (e) => { if (e.key === "Enter" && e.target.closest(".lt-f")) { e.preventDefault(); e.target.blur(); } });
  $$(".lt-share", art).forEach((b) => (b.hidden = !LT.canShare()));
  art.classList.toggle("lt-can-share", LT.canShare());
  LT.bindActions(art, () => docs[lang()], vals);
  await load(true);
  if (document.fonts?.ready) document.fonts.ready.then(() => $$(".lt-f", sheet).forEach(LT.fit));
}
CE.addRoute("notice", view);
