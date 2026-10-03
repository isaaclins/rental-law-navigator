// Compare two addresses side by side (#48). Self-contained feature module on window.CE (web/DESIGN.md).
// Route: #/compare/<idA>,<idB>. A side is a known address id (A0016) or "~" + base64url JSON of a place resolved
// by the any-address feature ({a: label, s: state, j: jurisdiction, y: year built, u: units}).
// Data: GET /api/address/<id>?as_of&lang for known addresses, POST /api/resolve + /api/evaluate for any other
// US address. Deterministic: the one-line answers below are a fixed mapping of rule id to a short phrase.
// Not legal advice.

const CE = window.CE;
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => CE.escape(s);
const lang = () => CE.lang();
const asOf = () => CE.asOf();

// ------------------------------------------------------------------ i18n --
const EN = {
  title: "Compare two addresses",
  lead: "See how renter protections differ before you move.",
  example: "For example, San Francisco next to Boston",
  pick: "Search an address", change: "Change", cancel: "Cancel",
  any: (q) => `Check “${q}”`, any_sub: "Any US address",
  finding: "Finding the address…", nomatch: "We could not find this address. Add the city and state.",
  out: "This address is outside California, New Jersey and Massachusetts.",
  busy: "Too many lookups. Please wait a minute.", down: "The address service did not answer. Try again in a moment.",
  load_fail: "This address could not be loaded.",
  diff: (n, t) => n === 0 ? `Same rules in all ${t} topics` : `Different in ${n} of ${t} topics`,
  as_of: "As of", both: "Both", open: "Open address",
  state_only: "State law only", year_built: "Year built", units: "Units",
  no_rules: "No rule on file here.",
  st_unknown: "Depends on the building", st_nye: (d) => `Takes effect ${d}`, st_pending: "Pending bill, not law",
  entry: "Compare with another address",
  doc_title: "Compare",
  cats: {
    rent_increase_limits: "Rent cap", just_cause_eviction: "Eviction", security_deposits: "Deposit",
    application_screening_fees: "Fees", screening_restrictions: "Screening", algorithmic_rent_setting: "Rent-setting software",
  },
  none: {
    rent_increase_limits: "No cap found", just_cause_eviction: "No just-cause rule found", security_deposits: "No cap found",
    application_screening_fees: "No cap found", screening_restrictions: "No rule found", algorithmic_rent_setting: "No ban found",
  },
  pending_tail: "bill pending",
  depends: { year_built: "Depends on year built", units: "Depends on the number of units", owner: "Depends on whether the owner lives there", other: "Depends on the building" },
  from: (s, d) => `${s} from ${d}`, new_rule: "New rule",
};
const ES = {
  title: "Comparar dos direcciones",
  lead: "Vea cómo cambian sus derechos como inquilino antes de mudarse.",
  example: "Por ejemplo, San Francisco junto a Boston",
  pick: "Buscar una dirección", change: "Cambiar", cancel: "Cancelar",
  any: (q) => `Consultar “${q}”`, any_sub: "Cualquier dirección de EE. UU.",
  finding: "Buscando la dirección…", nomatch: "No encontramos esta dirección. Añada la ciudad y el estado.",
  out: "Esta dirección está fuera de California, Nueva Jersey y Massachusetts.",
  busy: "Demasiadas consultas. Espere un minuto.", down: "El servicio de direcciones no respondió. Inténtelo de nuevo.",
  load_fail: "No se pudo cargar esta dirección.",
  diff: (n, t) => n === 0 ? `Mismas normas en los ${t} temas` : `Distinto en ${n} de ${t} temas`,
  as_of: "Al", both: "Ambas", open: "Abrir dirección",
  state_only: "Solo ley estatal", year_built: "Año de construcción", units: "Unidades",
  no_rules: "No hay ninguna norma registrada aquí.",
  st_unknown: "Depende del edificio", st_nye: (d) => `Entra en vigor el ${d}`, st_pending: "Proyecto de ley, no es ley",
  entry: "Comparar con otra dirección",
  doc_title: "Comparar",
  cats: {
    rent_increase_limits: "Tope de alquiler", just_cause_eviction: "Desalojo", security_deposits: "Depósito",
    application_screening_fees: "Cargos", screening_restrictions: "Selección", algorithmic_rent_setting: "Software de precios",
  },
  none: {
    rent_increase_limits: "Sin tope registrado", just_cause_eviction: "Sin norma de causa justa", security_deposits: "Sin tope registrado",
    application_screening_fees: "Sin tope registrado", screening_restrictions: "Sin norma registrada", algorithmic_rent_setting: "Sin prohibición registrada",
  },
  pending_tail: "proyecto pendiente",
  depends: { year_built: "Depende del año de construcción", units: "Depende del número de unidades", owner: "Depende de si el dueño vive allí", other: "Depende del edificio" },
  from: (s, d) => `${s} desde el ${d}`, new_rule: "Nueva norma",
};
const t = (k) => (lang() === "es" ? ES : EN)[k];
const CATS = Object.keys(EN.cats);

// ------------------------------------------------------------------ one-line answers --
// rule id -> [priority, en, es, until?, en_after?, es_after?]. Priority 1 leads the line; a second phrase with
// priority <= 1.5 is appended; priority 2 is shown only when nothing else applies. Figures tied to a period end
// at `until`; after that date the general phrase is shown instead.
const S = {
  "CA-RENT-01": [1, "5% + CPI, max 10%/yr", "5% + IPC, máx. 10%/año"],
  "LA-RENT-01": [1, "Yearly % set by the city", "% anual fijado por la ciudad"],
  "SF-RENT-01": [1, "1.6%/yr", "1.6%/año", "2027-02-28", "Yearly % set by the city", "% anual fijado por la ciudad"],
  "BER-RENT-01": [1, "1.0%/yr", "1.0%/año", "2026-12-31", "65% of CPI, max 5%/yr", "65% del IPC, máx. 5%/año"],
  "SA-RENT-01": [1, "Max 3%/yr", "Máx. 3%/año"],
  "JC-RENT-01": [1, "City rent control", "Control de alquiler municipal"],
  "HOB-RENT-01": [1, "City rent control", "Control de alquiler municipal"],
  "NWK-RENT-01": [1, "City rent control", "Control de alquiler municipal"],
  "MA-RENT-01": [1, "No cap (rent control banned)", "Sin tope (control prohibido)"],
  "CA-EVIC-01": [1, "Just cause after 12 months", "Causa justa tras 12 meses"],
  "LA-EVIC-01": [1, "Just cause required", "Se exige causa justa"],
  "LA-EVIC-02": [1, "Just cause required", "Se exige causa justa"],
  "LA-EVIC-03": [2, "Relocation pay on demolition", "Pago de reubicación por demolición"],
  "LA-EVIC-04": [2, "Relocation pay for no-fault", "Pago de reubicación sin culpa"],
  "SF-EVIC-01": [1, "Just cause required", "Se exige causa justa"],
  "SF-EVIC-02": [2, "Relocation pay for no-fault", "Pago de reubicación sin culpa"],
  "SD-EVIC-01": [1, "Just cause required", "Se exige causa justa"],
  "BER-EVIC-01": [1, "Just cause required", "Se exige causa justa"],
  "SA-EVIC-01": [1, "Just cause after 30 days", "Causa justa tras 30 días"],
  "NJ-EVIC-03": [1, "Just cause required", "Se exige causa justa"],
  "NJ-EVIC-01": [2, "No retaliation", "Sin represalias"],
  "NJ-EVIC-02": [2, "90 days' notice after a sale", "90 días de aviso tras una venta"],
  "MA-EVIC-02": [1, "No just cause; 3 months' notice", "Sin causa justa; 3 meses de aviso"],
  "MA-EVIC-01": [2, "14 days' notice for unpaid rent", "14 días de aviso por impago"],
  "MA-EVIC-03": [2, "No retaliation", "Sin represalias"],
  "MA-EVIC-04": [2, "State form with the notice", "Formulario estatal con el aviso"],
  "BOS-EVIC-01": [2, "Rights notice required", "Aviso de derechos obligatorio"],
  "CAM-EVIC-01": [2, "Rights notice required", "Aviso de derechos obligatorio"],
  "CA-DEP-01": [1, "Max 1 month's rent", "Máx. 1 mes de alquiler"],
  "LA-DEP-01": [1.5, "Earns interest", "Genera intereses"],
  "SF-DEP-01": [1.5, "4.2% interest", "4.2% de interés", "2027-02-28", "Earns interest", "Genera intereses"],
  "BER-DEP-01": [1.5, "Earns interest", "Genera intereses"],
  "NJ-DEP-01": [1, "Max 1.5 months' rent", "Máx. 1.5 meses de alquiler"],
  "MA-DEP-01": [1, "Max 1 month's rent", "Máx. 1 mes de alquiler"],
  "CA-FEE-01": [1, "Max $68.96 per applicant", "Máx. $68.96 por solicitante", "2026-12-31", "Max $30 + CPI per applicant", "Máx. $30 + IPC por solicitante"],
  "BER-FEE-01": [1.5, "No renewal fees", "Sin cargos por renovación"],
  "NJ-FEE-01": [1, "Max $50 + CPI per application", "Máx. $50 + IPC por solicitud"],
  "MA-FEE-02": [1, "No application fee", "Sin cargo de solicitud"],
  "MA-FEE-01": [2, "Broker fee paid by who hired", "Comisión a cargo de quien contrató"],
  "CA-SCR-01": [1, "Vouchers protected", "Vales protegidos"],
  "CA-SCR-02": [1.5, "Criminal-history limits", "Límites a antecedentes penales"],
  "SF-SCR-01": [2, "Fair chance in affordable housing", "Oportunidad justa en vivienda asequible"],
  "SD-SCR-01": [1, "Vouchers protected", "Vales protegidos"],
  "BER-SCR-01": [1.2, "No criminal-history checks", "Sin revisar antecedentes penales"],
  "NJ-SCR-01": [1, "Vouchers protected", "Vales protegidos"],
  "NJ-SCR-02": [1.5, "Criminal-history limits", "Límites a antecedentes penales"],
  "MA-SCR-01": [1, "Vouchers protected", "Vales protegidos"],
  "BOS-SCR-01": [1, "Vouchers protected", "Vales protegidos"],
  "BOS-SCR-02": [2, "No credit scores", "Sin puntaje de crédito"],
  "CAM-SCR-01": [1, "Vouchers protected", "Vales protegidos"],
  "CA-ALG-01": [1.8, "Collusive pricing banned", "Precios colusorios prohibidos"],
  "SF-ALG-01": [1, "Banned", "Prohibido"],
  "SD-ALG-01": [1, "Banned", "Prohibido"],
  "BER-ALG-01": [1, "Banned", "Prohibido"],
  "SA-ALG-01": [1, "Banned", "Prohibido"],
  "NJ-ALG-01": [1, "Banned", "Prohibido"],
  "JC-ALG-01": [1, "Banned", "Prohibido"],
  "HOB-ALG-01": [1, "Banned", "Prohibido"],
};
const firstClause = (s) => String(s || "").split(/[;(]/)[0].trim();
function short(item) {
  const r = item.rule, e = S[r.team_rule_id], es = lang() === "es";
  if (!e) return { p: 1.9, s: firstClause(r.key_value_display || r.key_value) || r.title_display || r.title };
  const after = e[3] && asOf() > e[3];
  return { p: e[0], s: after ? e[es ? 5 : 4] : e[es ? 2 : 1] };
}
function dependsOn(item) {
  const need = item.needs_fact || [];
  const m = String(item.missing_fact || "").toLowerCase();
  const k = need.includes("year_built") || /year|año/.test(m) ? "year_built" : need.includes("units") || /unit/.test(m) ? "units"
    : need.includes("owner_occupied") || /owner/.test(m) ? "owner" : "other";
  return t("depends")[k];
}
const enactedOf = (c) => c.enacted || [];
function answer(cat) {
  const en = enactedOf(cat);
  const applies = en.filter((i) => i.result === "applies").map(short).sort((a, b) => a.p - b.p);
  const uniq = applies.filter((x, i) => applies.findIndex((y) => y.s === x.s) === i);
  if (uniq.length) {
    const parts = [uniq[0].s];
    if (uniq[1] && uniq[1].p <= 1.5) parts.push(uniq[1].s);
    return parts.join(" · ");
  }
  const unk = en.find((i) => i.result === "unknown");
  if (unk) return dependsOn(unk);
  const nye = en.filter((i) => i.result === "not_yet_effective")
    .sort((a, b) => String(a.rule.effective_date_norm || a.rule.effective_date).localeCompare(String(b.rule.effective_date_norm || b.rule.effective_date)))[0];
  if (nye) {
    const s = S[nye.rule.team_rule_id] ? short(nye).s : t("new_rule");
    return t("from")(s, CE.fmtDate(nye.rule.effective_date_norm || nye.rule.effective_date));
  }
  const none = t("none")[cat.id];
  return (cat.pending || []).length ? `${none} · ${t("pending_tail")}` : none;
}

// ------------------------------------------------------------------ sides --
const b64e = (o) => btoa(String.fromCharCode(...new TextEncoder().encode(JSON.stringify(o)))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const b64d = (s) => JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0))));
const titleCase = (s) => String(s || "").toLowerCase().replace(/\b\w/g, (m) => m.toUpperCase()).replace(/\b(Ca|Nj|Ma)\b/g, (m) => m.toUpperCase());
const STATE = { CA: "California", NJ: "New Jersey", MA: "Massachusetts" };
let ADDR = [];
const addrList = async () => (ADDR.length ? ADDR : (ADDR = await CE.api("/api/addresses").catch(() => [])));

function parseSide(key) {
  if (!key) return null;
  if (key.startsWith("~")) {
    try {
      const o = b64d(key.slice(1));
      if (!/^[A-Z]{2}$/.test(o.s)) return null;
      const [street, ...rest] = String(o.a || "").split(",");
      return { key, custom: o, street: titleCase(street), place: o.j || STATE[o.s] || o.s };
    } catch { return null; }
  }
  const id = key.toUpperCase();
  if (!/^A\d{3,}$/.test(id)) return null;
  const a = ADDR.find((x) => x.id === id);
  return { key: id, id, street: a ? titleCase(a.street) : id, place: a ? `${a.city || a.postal_city}, ${a.state}` : "" };
}
const evalCache = new Map();
async function post(url, body) {
  const r = await fetch(url, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
  if (r.status === 429) throw new Error(t("busy"));
  if (r.status === 503) throw new Error(t("down"));
  if (!r.ok) throw new Error(t("load_fail"));
  return r.json();
}
function load(side) {
  if (side.id) return CE.api(`/api/address/${side.id}?as_of=${asOf()}&lang=${lang()}`);
  const o = side.custom, facts = {};
  if (o.y) facts.year_built = o.y;
  if (o.u) facts.units = o.u;
  const body = { address: { state: o.s, jurisdiction: o.j || null }, as_of: asOf(), facts, lang: lang() };
  const k = JSON.stringify(body);
  if (!evalCache.has(k)) evalCache.set(k, post("/api/evaluate", body).catch((e) => { evalCache.delete(k); throw e; }));
  return evalCache.get(k);
}

// ------------------------------------------------------------------ render --
const I = CE.icons || {};
const chev = I.chev || "";
let seq = 0, keys = [null, null], editing = [false, false], focusSlot = null;

function slotHtml(i, side) {
  if (side && !editing[i]) {
    const name = side.id ? `<a href="#/a/${esc(side.id)}">${esc(side.street)}</a>` : esc(side.street);
    const scope = side.custom && !side.custom.j ? ` · ${esc(t("state_only"))}` : "";
    const facts = side.custom && side.custom.j ? `<div class="cmp-facts" data-facts="${i}" hidden>
        <label><span>${esc(t("year_built"))}</span><input type="number" inputmode="numeric" name="y" min="1700" max="2100" value="${esc(side.custom.y || "")}"></label>
        <label><span>${esc(t("units"))}</span><input type="number" inputmode="numeric" name="u" min="1" max="5000" value="${esc(side.custom.u || "")}"></label>
      </div>` : "";
    return `<div class="cmp-slot" data-side="${i}">
      <p class="cmp-street">${name}</p>
      <p class="cmp-place">${esc(side.place)}${scope} <button type="button" class="linkish cmp-link" data-change="${i}">${esc(t("change"))}</button></p>
      ${facts}
    </div>`;
  }
  return `<div class="cmp-slot" data-side="${i}">
    <div class="cmp-pick">
      <input type="search" enterkeyhint="search" autocomplete="off" spellcheck="false" placeholder="${esc(t("pick"))}" aria-label="${esc(t("pick"))}" data-pick="${i}">
      ${editing[i] ? `<button type="button" class="linkish cmp-link" data-cancel="${i}">${esc(t("cancel"))}</button>` : ""}
    </div>
    <ul class="cmp-sug" role="listbox" hidden></ul>
    <p class="cmp-msg" aria-live="polite" hidden></p>
  </div>`;
}

function shellHtml(sides) {
  const both = sides[0] && sides[1];
  const empty = !sides[0] && !sides[1];
  return `<section class="cmp${both ? " full" : ""}">
    <header class="page-head"><h1 class="cmp-h1">${esc(t("title"))}</h1>${empty ? `<p>${esc(t("lead"))}</p>` : ""}</header>
    <div class="cmp-head"><span class="cmp-meta" aria-live="polite"></span>${slotHtml(0, sides[0])}${slotHtml(1, sides[1])}<span></span></div>
    ${both ? `<div class="group cmp-body" aria-busy="true">${CATS.map(() => `<div class="cmp-skel"><i></i><i></i><i></i></div>`).join("")}</div>`
      : empty ? `<p class="cmp-ex"><a href="#/compare/A0016,A0006">${esc(t("example"))}</a></p>` : ""}
  </section>`;
}

function ruleHtml(item) {
  const r = item.rule;
  const st = item.result === "unknown" ? dependsOn(item)
    : item.result === "not_yet_effective" ? t("st_nye")(CE.fmtDate(r.effective_date_norm || r.effective_date))
    : item.result === "pending" ? t("st_pending") : "";
  return `<li>
    <p class="cmp-rt">${esc(r.title_display || r.title)}</p>
    ${st ? `<p class="cmp-rs">${esc(st)}</p>` : ""}
    ${r.quoted_span ? `<blockquote class="quote">“${esc(r.quoted_span)}”</blockquote>` : ""}
    <p class="rd-cite">${r.source_url ? `<a href="${esc(r.source_url)}" target="_blank" rel="noopener">${esc(r.citation || r.source_url)}</a>` : esc(r.citation || "")}</p>
  </li>`;
}
function sideRulesHtml(cat, side) {
  const order = { applies: 0, unknown: 1, not_yet_effective: 2 };
  const items = enactedOf(cat).filter((i) => i.result in order).sort((a, b) => order[a.result] - order[b.result]).concat(cat.pending || []);
  return `<div class="cmp-side"><p class="cmp-who">${esc(side.street)}</p>
    ${items.length ? `<ul class="cmp-rules">${items.map(ruleHtml).join("")}</ul>` : `<p class="cmp-none">${esc(t("no_rules"))}</p>`}</div>`;
}

function bodyHtml(sides, data, open) {
  let diff = 0;
  const rows = CATS.map((id) => {
    const cA = data[0].categories.find((c) => c.id === id) || { id, enacted: [] };
    const cB = data[1].categories.find((c) => c.id === id) || { id, enacted: [] };
    const a = answer(cA), b = answer(cB), same = a === b;
    if (!same) diff++;
    const isOpen = open.has(id);
    const ans = same
      ? `<span class="cmp-a both"><span class="cmp-who">${esc(t("both"))}</span><span class="cmp-v">${esc(a)}</span></span>`
      : `<span class="cmp-a"><span class="cmp-who">${esc(sides[0].street)}</span><span class="cmp-v">${esc(a)}</span></span>
         <span class="cmp-a"><span class="cmp-who">${esc(sides[1].street)}</span><span class="cmp-v">${esc(b)}</span></span>`;
    return `<details class="topic cmp-row${same ? " same" : ""}" data-cat="${id}"${isOpen ? " open" : ""}>
      <summary class="cmp-sum"><span class="cmp-l">${esc(t("cats")[id])}</span>${ans}<span class="chev cmp-chev" aria-hidden="true">${chev}</span></summary>
      <div class="cmp-detail"><span></span>${sideRulesHtml(cA, sides[0])}${sideRulesHtml(cB, sides[1])}</div>
    </details>`;
  }).join("");
  return { rows, diff };
}

async function fillBody(my, sides) {
  const root = $(".cmp", document);
  const body = $(".cmp-body", root);
  if (!body) return;
  const open = new Set($$("details.cmp-row[open]", body).map((d) => d.dataset.cat));
  let data;
  try { data = await Promise.all(sides.map(load)); }
  catch (e) {
    if (my !== seq) return;
    body.removeAttribute("aria-busy");
    body.innerHTML = `<p class="cmp-err">${esc(e.message && !/^\d/.test(e.message) ? e.message : t("load_fail"))}</p>`;
    return;
  }
  if (my !== seq || !body.isConnected) return;
  const { rows, diff } = bodyHtml(sides, data, open);
  body.innerHTML = rows;
  body.removeAttribute("aria-busy");
  $(".cmp-meta", root).innerHTML = `<b>${esc(t("diff")(diff, CATS.length))}</b>${esc(t("as_of"))} ${esc(CE.fmtDate(data[0].as_of || asOf()))}`;
  // building facts for a place resolved by the any-address feature: only offered when an answer depends on them
  data.forEach((d, i) => {
    const box = $(`[data-facts="${i}"]`, root);
    if (!box) return;
    const fc = d.fact_counts || {}, o = sides[i].custom;
    box.hidden = !(fc.year_built || fc.units || o.y || o.u);
  });
}

async function render(main, arg) {
  const my = ++seq;
  await addrList();
  const parts = String(arg || "").split(",");
  const next = [parts[0] || null, parts[1] || null];
  const sides = next.map(parseSide);
  const sameView = !!$(".cmp", main) && next[0] === keys[0] && next[1] === keys[1];
  if (!sameView) editing = [false, false];
  keys = next;
  document.title = `${sides[0] && sides[1] ? `${sides[0].street} · ${sides[1].street}` : t("doc_title")} · Clause & Effect`;
  if (sameView && sides[0] && sides[1] && !editing[0] && !editing[1]) {
    // as-of or language changed: update in place, keep open rows
    $(".cmp-h1", main).textContent = t("title");
    $$("[data-side]", main).forEach((el) => { el.outerHTML = slotHtml(+el.dataset.side, sides[+el.dataset.side]); });
    return fillBody(my, sides);
  }
  main.innerHTML = shellHtml(sides);
  wire(main);
  const f = focusSlot ?? (sides[0] && !sides[1] ? 1 : !sides[0] && sides[1] ? 0 : null);
  focusSlot = null;
  if (f != null) requestAnimationFrame(() => $(`[data-pick="${f}"]`, main)?.focus({ preventScroll: true }));
  if (sides[0] && sides[1]) fillBody(my, sides);
}
function rerender() { render($("#main"), keys.map((k) => k || "").join(",").replace(/,$/, "")); }

// ------------------------------------------------------------------ picker --
const looksLikeAddress = (q) => q.length >= 6 && /\d/.test(q) && /[a-z]{2,}/i.test(q);
function setSide(i, key) {
  const next = [...keys];
  next[i] = key;
  editing[i] = false;
  focusSlot = next[i ? 0 : 1] ? null : i ? 0 : 1;
  const arg = next.map((k) => k || "").join(",").replace(/,$/, "");
  const target = `#/compare/${arg}`;
  if (location.hash === target) rerender(); else CE.navigate(target);
}
function suggest(input) {
  const i = +input.dataset.pick, slot = input.closest(".cmp-slot"), list = $(".cmp-sug", slot);
  const q = input.value.trim().toLowerCase();
  if (!q) { list.hidden = true; list.innerHTML = ""; return; }
  const words = q.split(/\s+/);
  const other = keys[i ? 0 : 1];
  const hits = ADDR.filter((a) => a.id !== other && words.every((w) => `${a.street} ${a.city} ${a.postal_city} ${a.state} ${a.zip}`.toLowerCase().includes(w))).slice(0, 6);
  const raw = input.value.trim();
  list.innerHTML = hits.map((a) => `<li role="option" aria-selected="false" data-id="${esc(a.id)}"><span class="cmp-o1">${esc(titleCase(a.street))}</span><span class="cmp-o2">${esc(a.city || a.postal_city)}, ${esc(a.state)}</span></li>`).join("")
    + (looksLikeAddress(raw) ? `<li role="option" aria-selected="false" data-q="${esc(raw)}"><span class="cmp-o1">${esc(t("any")(raw))}</span><span class="cmp-o2">${esc(t("any_sub"))}</span></li>` : "");
  list.hidden = !list.children.length;
  if (list.children.length) list.children[0].setAttribute("aria-selected", "true");
}
async function resolveAny(i, q, slot) {
  const msg = $(".cmp-msg", slot), list = $(".cmp-sug", slot);
  list.hidden = true;
  msg.hidden = false; msg.textContent = t("finding");
  let d;
  try { d = await post("/api/resolve", { address: q }); }
  catch (e) { msg.textContent = e.message; return; }
  if (!d.match) { msg.textContent = t("nomatch"); return; }
  if (!d.in_scope) { msg.textContent = t("out"); return; }
  const o = { a: titleCase(d.matched_address || q).replace(/,\s*\d{5}(-\d{4})?$/, ""), s: d.state };
  if (d.jurisdiction) o.j = d.jurisdiction;
  setSide(i, "~" + b64e(o));
}
function choose(li) {
  const slot = li.closest(".cmp-slot"), i = +slot.dataset.side;
  if (li.dataset.id) setSide(i, li.dataset.id);
  else if (li.dataset.q) resolveAny(i, li.dataset.q, slot);
}
let factTimer = null;
function wire(root) {
  root.addEventListener("input", (e) => {
    if (e.target.matches("[data-pick]")) { $(".cmp-msg", e.target.closest(".cmp-slot")).hidden = true; suggest(e.target); }
    const box = e.target.closest("[data-facts]");
    if (box) {
      clearTimeout(factTimer);
      factTimer = setTimeout(() => {
        const i = +box.dataset.facts, o = { ...parseSide(keys[i]).custom };
        for (const inp of $$("input", box)) {
          const v = parseInt(inp.value, 10);
          if (inp.value && (!inp.checkValidity() || isNaN(v))) return;
          if (inp.value) o[inp.name] = v; else delete o[inp.name];
        }
        keys[i] = "~" + b64e(o);
        history.replaceState(null, "", `#/compare/${keys.join(",")}`);
        fillBody(++seq, keys.map(parseSide));
      }, 450);
    }
  });
  root.addEventListener("keydown", (e) => {
    const input = e.target.closest?.("[data-pick]");
    if (!input) return;
    const list = $(".cmp-sug", input.closest(".cmp-slot")), opts = $$("li", list);
    const cur = opts.findIndex((o) => o.getAttribute("aria-selected") === "true");
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (!opts.length) return;
      const n = (cur + (e.key === "ArrowDown" ? 1 : -1) + opts.length) % opts.length;
      opts.forEach((o, k) => o.setAttribute("aria-selected", k === n));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (opts[cur]) choose(opts[cur]);
      else if (looksLikeAddress(input.value.trim())) resolveAny(+input.dataset.pick, input.value.trim(), input.closest(".cmp-slot"));
    } else if (e.key === "Escape" && editing[+input.dataset.pick]) {
      editing[+input.dataset.pick] = false; rerender();
    }
  });
  root.addEventListener("click", (e) => {
    const li = e.target.closest(".cmp-sug li");
    if (li) return choose(li);
    const ch = e.target.closest("[data-change]");
    if (ch) { editing[+ch.dataset.change] = true; focusSlot = +ch.dataset.change; return rerender(); }
    const ca = e.target.closest("[data-cancel]");
    if (ca) { editing[+ca.dataset.cancel] = false; return rerender(); }
  });
}

CE.addRoute("compare", render);

// ------------------------------------------------------------------ entry point on the address page --
function addEntry(e) {
  const { view, arg } = e.detail || {};
  if (view !== "lookup" || !arg || !location.hash.startsWith("#/a/")) return;
  const main = $("#main"), id = String(arg).toUpperCase();
  if ($(".cmp-entry", main)) return;
  $('[data-slot="address-actions"]', main)?.insertAdjacentHTML("beforeend", `<a class="cmp-entry" href="#/compare/${esc(id)}">${esc(t("entry"))}</a>`);
}
document.addEventListener("ce:route", addEntry);
