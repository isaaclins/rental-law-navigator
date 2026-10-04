// Ask the law (#101). Self-contained feature module on window.CE (web/DESIGN.md).
// Route #/ask (and #/ask/<question>, a shareable link that asks right away). One question in plain words; POST
// /api/ask streams the real steps (rules found -> address checked by the engine -> quotes checked -> writing) and
// the validated answer: a plain line, 1-3 sentences, numbered citations with the verbatim quote, its status, the
// word-for-word check and a link to the source. Answers come only from our own rules; applicability at an address
// comes from the rules engine. Not legal advice. Nothing is stored on the server; the thread lives in this tab.
// window.CEAsk.mountDock() docks the "Ask anything…" bar on any page (submitting opens #/ask/<question>).

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const CE = window.CE;
const lang = () => CE.lang();
const reduced = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

// ------------------------------------------------------------------ i18n --
const STR = {
  en: {
    nav: "Ask", title: "Ask the law", sub: "Plain questions, answered only from the quoted sources.",
    ph_try: "Try ‘{q}’", ph_phone: "Rent, deposits, evictions…", ph_dock: "Ask anything…", ph_more: "Ask a follow-up…", send: "Ask", new_q: "New question",
    st1: "Finding the rules", st1n: "Found {n} rules", st1e: "Found {n} rules · building checked", st_eng: "Checking the building with the rules engine",
    st2: "Checking each quote in the source", st2n: "{v} of {n} quotes found word for word", st3: "Writing the answer",
    verbatim: "Found word for word in the source", not_verbatim: "Quote not found in the source text: needs review",
    read: "Read the source", open_site: "Official site", secondary: "{h} (summary, not the official text)", foot: "As of {d} · Not legal advice · from {n} quoted laws",
    foot1: "As of {d} · Not legal advice · from 1 quoted law", foot0: "As of {d} · Not legal advice",
    engine: "checked by the rules engine", closest: "Closest official source", built: "built {y}", units: "{n} units",
    units_min: "at least {n} units", built_unk: "year built unknown", units_unk: "units unknown", cached: "instant",
    err: "Something went wrong. Please try again.", offline: "You're offline. Check your connection and try again.", busy: "Many people are asking right now. Please try again in a minute.",
    statement: "Clause & Effect answers only from {a} its quoted sources, cites {b} every point of law, and says “unknown” {c} instead of guessing.",
    try_these: "Try one of these", degraded: "Quick answer from our rules engine", you: "You asked",
    show_law: "Show me the law", hide_law: "Hide the law", progress: "Progress", same_addr: "Same address", at: "Asking about", at_x: "Ask without this address",
    queued: "Waiting for the answer above…", up_next: "Up next", remove: "Remove", retry: "Try again", timeout: "That took too long. Please try again.",
    stale: "Answered for {d}.", ask_again: "Ask again for {d}", answer_as_of: "Answer as of {d}",
    source_n: "Source {n}", where: "Where do you rent?", type_addr: "Type your address", next: "What you can do",
    privacy: "Not legal advice. For audits we keep each question with e-mails, phone numbers and street addresses removed, plus the answer; the public log shows only topic, place and rules.",
    privacy_short: "Not legal advice · no personal details kept", privacy_more: "About privacy",
    help: "Get help", addr_ph: "Street and city, e.g. 6238 De Longpre Ave, Los Angeles", understood: "Following on from your question",
  },
  es: {
    nav: "Preguntar", title: "Pregunte a la ley", sub: "Preguntas sencillas, respondidas solo con las fuentes citadas.",
    ph_try: "Pruebe ‘{q}’", ph_phone: "Renta, depósitos, desalojos…", ph_dock: "Pregunte lo que quiera…", ph_more: "Haga otra pregunta…", send: "Preguntar", new_q: "Nueva pregunta",
    st1: "Buscando las normas", st1n: "{n} normas encontradas", st1e: "{n} normas · edificio revisado", st_eng: "Revisando el edificio con el motor de reglas",
    st2: "Comprobando cada cita en la fuente", st2n: "{v} de {n} citas, palabra por palabra", st3: "Redactando la respuesta",
    verbatim: "Encontrada palabra por palabra en la fuente", not_verbatim: "Cita no encontrada en el texto fuente: requiere revisión",
    read: "Leer la fuente", open_site: "Sitio oficial", secondary: "{h} (resumen, no el texto oficial)", foot: "Al {d} · No es asesoría legal · de {n} leyes citadas",
    foot1: "Al {d} · No es asesoría legal · de 1 ley citada", foot0: "Al {d} · No es asesoría legal",
    engine: "revisado por el motor de reglas", closest: "Fuente oficial más cercana", built: "construido en {y}", units: "{n} unidades",
    units_min: "al menos {n} unidades", built_unk: "año de construcción desconocido", units_unk: "unidades desconocidas", cached: "al instante",
    err: "Algo salió mal. Inténtelo de nuevo.", offline: "No tiene conexión a internet. Revise su conexión e inténtelo de nuevo.", busy: "Mucha gente pregunta ahora mismo. Inténtelo de nuevo en un minuto.",
    statement: "Clause & Effect responde solo con {a} sus fuentes citadas, cita {b} la fuente de cada punto legal y dice «desconocido» {c} en vez de adivinar.",
    try_these: "Pruebe una de estas", degraded: "Respuesta rápida de nuestro motor de reglas", you: "Usted preguntó",
    show_law: "Muéstreme la ley", hide_law: "Ocultar la ley", progress: "Progreso", same_addr: "Misma dirección", at: "Pregunta sobre", at_x: "Preguntar sin esta dirección",
    queued: "Esperando la respuesta anterior…", up_next: "A continuación", remove: "Quitar", retry: "Intentar de nuevo", timeout: "Tardó demasiado. Inténtelo de nuevo.",
    stale: "Respondido para el {d}.", ask_again: "Preguntar de nuevo para el {d}", answer_as_of: "Respuesta al {d}",
    source_n: "Fuente {n}", where: "¿Dónde alquila?", type_addr: "Escriba su dirección", next: "Lo que puede hacer",
    privacy: "No es asesoría legal. Para auditoría guardamos cada pregunta sin correos, teléfonos ni direcciones, y la respuesta; el registro público solo muestra tema, lugar y normas.",
    privacy_short: "No es asesoría legal · sin datos personales", privacy_more: "Sobre la privacidad",
    help: "Pedir ayuda", addr_ph: "Calle y ciudad, p. ej. 6238 De Longpre Ave, Los Angeles", understood: "Siguiendo su pregunta",
  },
};
const sx = (l, k, v = {}) => (STR[l]?.[k] ?? STR.en[k] ?? k).replace(/\{(\w+)\}/g, (_, x) => v[x] ?? "");
const s = (k, v = {}) => sx(lang(), k, v);
const host = (u) => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return ""; } };
// short placeholders that fit a phone's ask bar
const PH = {
  en: ["How big can the deposit be?", "Can they raise my rent 8%?", "Evicted for no reason?"],
  es: ["¿Cuánto depósito piden?", "¿Me suben la renta 8%?", "¿Desalojo sin motivo?"],
};
const narrow = () => matchMedia("(max-width: 640px)").matches;
const phText = (q) => (narrow() ? s("ph_phone") : s("ph_try", { q })); // phones: neutral, not a copy of a suggestion
const IMG = (n) => `/static/img/${n}.webp`;
const ARROW = `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>`;
const CHECK = `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>`;
const PIN = `<svg class="ask-pin" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0C18.5 15.4 12 21 12 21z"/><circle cx="12" cy="10" r="2.3"/></svg>`;
const CAL = `<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="5" width="16" height="15" rx="3"/><path d="M8 3v4M16 3v4M4 10h16"/></svg>`;
const EXT = `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/></svg>`;

// ------------------------------------------------------------------ state --
const THREAD = []; // {q, res, steps, status}: this tab only, never sent anywhere but /api/ask
let SUGGEST = { en: null, es: null };
let mainEl = null, phTimer = null, io = null, askY = 0;
// the same suggestions the server pre-warms (web/ask.py SUGGEST): the page paints at once, the server's list wins
const SUGGEST_DEFAULT = {
  en: ["How much deposit can my landlord ask for at 6238 De Longpre Ave?", "Can they raise my rent 8% in Hoboken?", "Can I be evicted without a reason in Berkeley?"],
  es: ["¿Cuánto depósito me pueden pedir en 6238 De Longpre Ave?", "¿Me pueden subir la renta un 8% en Hoboken?", "¿Me pueden desalojar sin motivo en Berkeley?", "¿Cuánto me pueden cobrar por la solicitud?"],
};
// dates in the answer's own language (not the page's), so an old English answer stays English after EN -> ES
const fmtD = (d, L) => (d ? new Date(d + "T12:00:00").toLocaleDateString(L === "es" ? "es-US" : "en-US", { month: "short", day: "numeric", year: "numeric" }) : "");

const suggestions = () => SUGGEST[lang()] || SUGGEST_DEFAULT[lang()] || SUGGEST_DEFAULT.en;
async function fetchSuggestions() {
  const l = lang();
  if (SUGGEST[l]) return;
  // chips are in the page's language only: the server's EN list also carries a Spanish question
  try { SUGGEST[l] = (await CE.api(`/api/ask/suggest?lang=${l}`)).questions.filter((q) => l !== "en" || !/[¿¡]/.test(q)); } catch { return; }
  const box = mainEl && $(".ask-chips", mainEl);
  if (box && l === lang() && box.dataset.qs !== JSON.stringify(SUGGEST[l])) { box.outerHTML = chipsHTML(SUGGEST[l], false); }
}
const chipsHTML = (qs, anim = true) => `<div class="ask-chips${anim ? "" : " still"}" role="list" aria-label="${esc(s("try_these"))}" data-qs="${esc(JSON.stringify(qs))}">
        ${qs.map((q, i) => `<button type="button" role="listitem" class="ask-chip" data-ask="${esc(q)}" style="--i:${i}">${esc(q)}</button>`).join("")}
      </div>`;

// the address looked up last (app.js keeps it for the session): the first question is about it, until cleared
const homeAddr = () => { try { const a = JSON.parse(sessionStorage.getItem("ce.addr") || "null"); return a && a.id ? a : null; } catch { return null; } };
const atHTML = () => { const a = homeAddr(); return a ? `<div class="ask-at" data-ask-at>${PIN}<span>${esc(s("at"))} <a href="#/a/${esc(a.id)}"><b>${esc(a.label)}</b></a></span><button type="button" class="ask-at-x" data-ask-at-x aria-label="${esc(s("at_x"))}">×</button></div>` : ""; };

// ------------------------------------------------------------------ markup --
const bar = (cls, ph, id) => `
  <form class="ask-bar ${cls}" role="search" data-ask-form>
    <label class="ask-sr" for="${id}">${esc(s("title"))}</label>
    <input id="${id}" name="q" type="text" autocomplete="off" spellcheck="true" maxlength="500" placeholder="${esc(ph)}" enterkeyhint="send">
    <button type="submit" class="ask-send" aria-label="${esc(s("send"))}">${ARROW}</button>
  </form>`;

const chip = (img, alt) => `<span class="ask-ichip" aria-hidden="true"><img src="${IMG(img)}" alt="${esc(alt)}" loading="lazy" decoding="async"></span>`;

function pageHTML(qs, { thread = THREAD.length > 0, still = false } = {}) {
  return `
  <div class="ask-page${still ? " still" : ""}" data-state="${thread ? "thread" : "home"}">
    <section class="ask-hero" aria-labelledby="ask-h1">
      <h1 id="ask-h1" class="ask-h1">${esc(s("title"))}</h1>
      <p class="ask-sub">${esc(s("sub"))}</p>
      ${atHTML()}
      <div class="ask-stage">
        ${bar("ask-bar--hero", phText((PH[lang()] || PH.en)[0]), "ask-q-hero")}
        <div class="ask-photo"><img src="${IMG("hero-justice")}" alt="" fetchpriority="high" decoding="async" data-ask-photo></div>
      </div>
      ${chipsHTML(qs)}
      <p class="ask-privacy"><span class="long">${esc(s("privacy"))}</span><span class="short"><span class="t">${esc(s("privacy_short"))}</span><button type="button" class="ask-info" data-ask-privacy aria-label="${esc(s("privacy_more"))}">ⓘ</button></span></p>
    </section>
    <div class="ask-thread-head"><h1 class="ask-h1 ask-h1--small">${esc(s("title"))}</h1><button type="button" class="linkish ask-new" data-ask-new>${esc(s("new_q"))}</button></div>
    <section class="ask-thread" aria-live="polite"></section>
    <section class="ask-statement"><p>${statementHTML()}</p></section>
  </div>`;
}

// ------------------------------------------------------------------ steps card: built once, patched in place --
const STEP_IDS = ["rules", "engine", "quotes", "writing"];
function stepLabel(t, id) {
  const st = t.steps;
  if (t.state === "queued") return id === "rules" ? s("queued") : "";
  // an address: the engine's check is said in the first row (a row added later would push the others down)
  if (id === "rules") return st.rules != null && st.rules !== true ? s(st.engine ? "st1e" : "st1n", { n: st.rules }) : s("st1");
  if (id === "engine") return s("st_eng");
  if (id === "quotes") return st.quotes && st.quotes.n != null ? s("st2n", st.quotes) : s("st2");
  return s("st3");
}
function stepDone(t, id) {
  const st = t.steps;
  if (t.state === "queued") return false;
  if (id === "rules") return st.rules != null;
  if (id === "engine") return !!st.engine;
  if (id === "quotes") return !!st.quotes;
  return !!t.res;
}
const stepIds = (t) => (t.state === "queued" ? ["rules"] : STEP_IDS.filter((id) => id !== "engine"));
function stepsHTML(t, enter = false) {
  return `<ol class="ask-steps${enter ? " enter" : ""}${t.state === "queued" ? " is-queued" : ""}" aria-label="${esc(s("progress"))}">${stepIds(t).map((id) =>
    `<li class="ask-step${stepDone(t, id) ? " done" : t.steps.cur === id ? " on" : ""}" data-step="${id}"><span class="dot" aria-hidden="true">${CHECK}</span><span class="lbl">${esc(stepLabel(t, id))}</span></li>`).join("")}</ol>`;
}
function patchSteps(card, t) {
  card.classList.toggle("is-queued", t.state === "queued");
  const want = stepIds(t);
  $$(".ask-step", card).forEach((li) => { if (!want.includes(li.dataset.step)) li.remove(); });
  let prev = null;
  for (const id of want) {
    let li = $(`.ask-step[data-step="${id}"]`, card);
    if (!li) {
      li = document.createElement("li");
      li.className = "ask-step"; li.dataset.step = id;
      li.innerHTML = `<span class="dot" aria-hidden="true">${CHECK}</span><span class="lbl"></span>`;
      prev ? prev.after(li) : card.prepend(li);
    }
    const done = stepDone(t, id), on = !done && t.steps.cur === id;
    if (li.classList.contains("done") !== done) li.classList.toggle("done", done);
    if (li.classList.contains("on") !== on) li.classList.toggle("on", on);
    const lbl = $(".lbl", li), text = stepLabel(t, id);
    if (lbl.textContent !== text) lbl.textContent = text;
    prev = li;
  }
}

const statementHTML = () => esc(s("statement", { a: "\u0001", b: "\u0002", c: "\u0003" })).replace("\u0001", chip("scales-balanced", "")).replace("\u0002", chip("magnifier-over-document", "")).replace("\u0003", chip("shield-check", ""));

// inline citation chips: a tap opens "Show me the law" at that quote
const sup = (ns) => (ns || []).map((n) => `<button type="button" class="ask-sup" data-cite="${Number(n)}" aria-label="${esc(s("source_n", { n: Number(n) }))}">${Number(n)}</button>`).join("");

// The place line (Isaac 2026-10-04): an address the engine checked gets the full line with its building photo, the
// same address again a compact "Same address · …"; a city or state a small pin and "Hoboken, NJ"; a definition none.
function placeHTML(p, L = lang(), engine = false, prev = null) {
  if (!p) return "";
  const s = (k, v) => sx(L, k, v);
  if (p.kind === "address") {
    if (prev?.kind === "address" && prev.address_id === p.address_id) {
      return `<div class="ask-place is-compact">${PIN}<div><span>${esc(s("same_addr"))}</span> <span class="sep">·</span> <a href="#/a/${esc(p.address_id)}"><b>${esc(String(p.label || "").split(",")[0])}</b></a>${engine ? ` <span class="sep">·</span> <span class="ask-eng-ok">${CHECK}${esc(s("engine"))}</span>` : ""}</div></div>`;
    }
    const bits = [p.year_built ? s("built", { y: p.year_built }) : s("built_unk"),
      p.units ? s("units", { n: p.units }) : p.units_min ? s("units_min", { n: p.units_min }) : s("units_unk")];
    const img = p.image ? `<img src="${IMG(p.image + "-sm")}" alt="" loading="lazy">` : `<span class="ask-place-dot" aria-hidden="true">${PIN}</span>`;
    const eng = engine ? `<span class="ask-eng-ok">${CHECK}${esc(s("engine"))}</span>` : "";
    return `<div class="ask-place">${img}<div><a href="#/a/${esc(p.address_id)}"><b>${esc(p.label)}</b></a>${bits.map((b) => ` <span class="ask-fact"><span class="sep">·</span> ${esc(b)}</span>`).join("")}${eng}</div></div>`;
  }
  const label = p.kind === "city" && p.jurisdiction ? p.jurisdiction : p.label; // "Hoboken, NJ"
  return `<div class="ask-place is-area">${PIN}<div><b>${esc(label)}</b></div></div>`;
}

function citeHTML(c, L = lang()) {
  const s = (k, v) => sx(L, k, v);
  const eng = c.engine && c.engine.result !== "applies" ? `<span class="ask-eng st-${esc(c.engine.result)}">${esc(c.engine.label)}${c.engine.missing_fact ? `: ${esc(c.engine.missing_fact)}` : ""}</span>` : "";
  // the quote is from another document than the cited law (web/source_notes.py): amber note instead of "word for word"
  const note = c.source_note ? `<p class="src-note"><svg class="ico" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17.5v.01"/></svg><span><b>${esc(c.source_note.lead)}</b> ${esc(c.source_note.text)}</span></p>` : "";
  const vb = note ? "" : c.quoted_span ? (c.verbatim ? `<span class="ask-vb">${CHECK}${esc(s("verbatim"))}</span>` : `<span class="ask-vb no">${esc(s("not_verbatim"))}</span>`) : "";
  const src = c.doc_id ? `<button type="button" class="linkish ask-src" data-doc="${esc(c.doc_id)}" data-rule="${esc(c.id)}">${esc(s("read"))}</button>`
    : "";
  const site = c.source_url ? `<a class="ask-src" href="${esc(safeUrl(c.source_url))}" target="_blank" rel="noopener">${esc(c.secondary ? s("secondary", { h: host(c.source_url) }) : s("open_site"))}${EXT}</a>` : "";
  const quote = c.quoted_span ? `<blockquote>“${esc(c.quoted_span.replace(/\s+/g, " ").trim())}”</blockquote>` : `<p class="ask-req">${esc(c.requirement)}</p>`;
  return `<li class="ask-cite" data-n="${c.n}" style="--i:${c.n}">
    <span class="n" aria-hidden="true">${c.n}</span>
    <div class="ask-cite-body">
      ${quote}
      <div class="ask-meta"><span>${esc([c.citation || c.jurisdiction_label, c.status === "in_force" ? "" : c.status_label].filter(Boolean).join(" · "))}</span>${eng}${vb}${src}${site}</div>${note}
    </div></li>`;
}

// the last word and its citation chips stay on one line
function sentHTML(b) {
  const chips = sup(b.cites);
  if (!chips) return esc(b.text);
  const m = /^(.*?)(\S+)\s*$/s.exec(b.text || "");
  return m ? `${esc(m[1])}<span class="ask-nw">${esc(m[2])}${chips}</span>` : chips;
}
// the place of the answer before this one in the thread (for "Same address · …")
const prevPlace = (idx) => (idx > 0 ? THREAD[idx - 1]?.res?.place || null : null);
const partsHTML = (parts) => (parts || []).map((b) => `<span class="ask-sent">${sentHTML(b)}</span>`).join(" ");

function answerHTML(t, idx, { partial = false } = {}) {
  const r = partial ? t.partial : t.res;
  if (!r) return "";
  const parts = r.parts || r.body || [];
  if (partial) {
    return `<div class="ask-a is-partial">${t.general ? "" : placeHTML(t.place, lang(), false, prevPlace(idx))}${r.answer ? `<h2 class="ask-answer">${esc(r.answer)}</h2>` : ""}<p class="ask-body">${partsHTML(parts)}</p></div>`;
  }
  const n = (r.citations || []).length;
  const L = r.lang || lang(), S = (k, v) => sx(L, k, v);
  const d = fmtD(r.as_of, L);
  const foot = n > 1 ? S("foot", { d, n }) : n === 1 ? S("foot1", { d }) : S("foot0", { d });
  const official = r.official ? `<p class="ask-official">${esc(S("closest"))}: <a href="${esc(safeUrl(r.official.url))}" target="_blank" rel="noopener">${esc(r.official.label)}${EXT}</a></p>` : "";
  const note = [r.scope_note, r.note].filter(Boolean).map((x) => `<p class="ask-note">${esc(x)}</p>`).join("");
  const summary = r.summary?.length ? `<ul class="ask-summary">${r.summary.map((x) => `<li><b>${esc(x.label)}</b><span>${sentHTML({ text: x.text, cites: x.cite ? [x.cite] : [] })}</span></li>`).join("")}</ul>` : "";
  const askq = r.ask ? `<p class="ask-clarify">${esc(r.ask)}</p>` : "";
  const quick = r.quick?.length ? `<div class="ask-quick" role="group" aria-label="${esc(S("where"))}">
      ${r.quick.map((o, i) => `<button type="button" class="ask-chip${o.group === "state" ? " is-state" : ""}" data-ask="${esc(o.q)}" style="--i:${i}">${esc(o.label)}</button>`).join("")}
      <button type="button" class="ask-chip ask-chip--line" data-ask-addr style="--i:${r.quick.length}">${esc(r.address_label || S("type_addr"))}</button>
    </div>` : "";
  const steps = r.steps?.length ? `<div class="ask-steps-out"><h3>${esc(S("next"))}</h3><ol>${r.steps.map((x) => `<li>${sentHTML(x)}</li>`).join("")}</ol></div>` : "";
  const help = r.help?.length ? `<div class="ask-help"><h3>${esc(S("help"))}</h3><ul>${r.help.map((h) => `<li><a href="${esc(safeUrl(h.url))}" target="_blank" rel="noopener">${esc(h.label)}${EXT}</a></li>`).join("")}</ul></div>` : "";
  const head = !r.answer ? "" : r.quiet ? `<p class="ask-lead">${esc(r.answer)}</p>` : `<h2 class="ask-answer">${esc(r.answer)}</h2>`;
  const when = r.asked_as_of ? `<p class="ask-when">${CAL}${esc(S("answer_as_of", { d: r.asked_label || fmtD(r.asked_as_of, L) }))}</p>` : "";
  return `<div class="ask-a${r.kind === "refusal" ? " is-refusal" : ""}${r.quiet ? " is-quiet" : ""}" data-turn="${idx}">
    ${when}${placeHTML(r.place, L, r.engine_checked, prevPlace(idx))}
    ${head}
    ${parts.length ? `<p class="ask-body">${partsHTML(parts)}</p>` : ""}
    ${summary}${askq}${quick}${note}${official}${steps}${help}
    ${n ? `<div class="ask-law${t.lawOpen ? " open" : ""}">
      <button type="button" class="ask-law-btn" aria-expanded="${!!t.lawOpen}" aria-controls="ask-law-${idx}" data-ask-law><span class="lbl">${esc(S(t.lawOpen ? "hide_law" : "show_law"))}</span><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 10 5 5 5-5"/></svg></button>
      <div class="ask-law-body" id="ask-law-${idx}"${t.lawOpen ? "" : " inert"}><div><ol class="ask-cites">${r.citations.map((c) => citeHTML(c, L)).join("")}</ol></div></div>
    </div>` : ""}
    <footer class="ask-foot">${esc(foot)}${r.degraded ? ` · ${esc(S("degraded"))}` : ""}</footer>
  </div>`;
}

const followupsHTML = (list) => `<div class="ask-next">${list.map((f, i) => `<button type="button" class="ask-chip ask-chip--line" data-ask="${esc(f)}" style="--i:${i}">${esc(f)}</button>`).join("")}</div>`;
// links come from our own data; never let anything but http(s) through
const safeUrl = (u) => (/^https?:\/\//i.test(String(u || "")) ? String(u) : "#");


// ------------------------------------------------------------------ rendering --
function turnHTML(t, idx, { fresh = false } = {}) {
  const view = t.state === "error" ? errorHTML(t, idx) : t.res ? answerHTML(t, idx) : t.partial ? answerHTML(t, idx, { partial: true }) : stepsHTML(t, fresh);
  return `<article class="ask-turn${t.res ? " is-done" : ""}${fresh ? " fresh" : ""}" data-idx="${idx}">
    <div class="ask-q"><span class="ask-sr">${esc(s("you"))}: </span><p>${esc(t.q)}</p></div>
    <div class="ask-work">${view}</div>
    ${t.res?.followups?.length && idx === THREAD.length - 1 ? followupsHTML(t.res.followups) : ""}
  </article>`;
}
const errKey = (t) => (["busy", "timeout", "offline"].includes(t.err) ? t.err : "err");
function errorHTML(t, idx) {
  return `<div class="ask-a ask-err" role="alert"><p class="ask-err-msg">${esc(s(errKey(t)))}</p>
    <button type="button" class="ask-retry" data-ask-retry="${idx}">${esc(s("retry"))}</button></div>`;
}
function drawThread() {
  const th = $(".ask-thread", mainEl);
  if (!th) return;
  th.innerHTML = THREAD.map((t, i) => turnHTML(t, i)).join("");
  markStale();
}
const turnEl = (idx) => mainEl && $(`.ask-turn[data-idx="${idx}"]`, mainEl);
const workEl = (idx) => turnEl(idx)?.querySelector(".ask-work");

// Crossfade in one grid cell: the new view fades in while the old one fades out, so there is never an empty frame
// and the turn keeps its height until the old view is gone.
// an element's entrance runs once: the class goes when its own animation ends (or after a safe delay)
function entered(el, ms = 520) {
  if (!el) return;
  const off = () => el.classList.remove("enter");
  el.addEventListener("animationend", function h(e) { if (e.target === el) { off(); el.removeEventListener("animationend", h); } });
  setTimeout(off, ms);
}
function swapView(work, html, { enter = true } = {}) {
  const old = [...work.children].filter((c) => !c.classList.contains("leaving"));
  work.insertAdjacentHTML("beforeend", html);
  const neu = work.lastElementChild;
  if (reduced()) { old.forEach((o) => o.remove()); return neu; }
  if (enter) { neu.classList.add("enter"); entered(neu); }
  old.forEach((o) => {
    o.classList.remove("enter");
    o.classList.add("leaving");
    const gone = () => o.isConnected && o.remove();
    o.addEventListener("animationend", (e) => { if (e.target === o) gone(); });
    setTimeout(gone, 400);
  });
  return neu;
}

function updateTurn(idx, { reveal = false } = {}) {
  const t = THREAD[idx];
  const work = workEl(idx);
  if (!t || !work) return;
  const cur = [...work.children].filter((c) => !c.classList.contains("leaving")).pop();
  if (t.state === "error") {
    if (cur?.classList.contains("ask-err")) { $(".ask-err-msg", cur).textContent = s(errKey(t)); return; }
    swapView(work, errorHTML(t, idx));
    return;
  }
  if (!t.res && !t.partial) {
    if (cur?.classList.contains("ask-steps")) patchSteps(cur, t);
    else swapView(work, stepsHTML(t));
    return;
  }
  if (!t.res) { // a streaming answer: the answer line rises once, finished sentences fade in after it
    const pparts = t.partial.parts || [];
    if (!cur?.classList.contains("is-partial") || cur.dataset.answer !== (t.partial.answer || "")) {
      const na = swapView(work, answerHTML(t, idx, { partial: true }));
      na.dataset.answer = t.partial.answer || "";
      na.dataset.sents = String(pparts.length);
      if (!reduced()) animateWords($(".ask-answer", na));
      return;
    }
    const p = $(".ask-body", cur);
    const have = Number(cur.dataset.sents || 0);
    pparts.slice(have).forEach((b, k) => p.insertAdjacentHTML("beforeend", `${have + k ? " " : ""}<span class="ask-sent new">${sentHTML(b)}</span>`));
    cur.dataset.sents = String(pparts.length);
    return;
  }
  turnEl(idx)?.classList.add("is-done");
  if (cur?.classList.contains("is-partial") && cur.dataset.answer === (t.res.answer || "")) {
    // same answer line: the finished card replaces the streaming one in place, only the rest fades in
    cur.insertAdjacentHTML("afterend", answerHTML(t, idx));
    const a = cur.nextElementSibling;
    cur.remove();
    if (reveal && !reduced()) a.classList.add("reveal-rest");
  } else {
    const a = swapView(work, answerHTML(t, idx), { enter: reveal });
    if (reveal && !reduced()) animateWords($(".ask-answer", a));
  }
  markStale();
  if (reveal) setTimeout(() => keepClear(workEl(idx)?.querySelector(".ask-a:not(.leaving)"), idx), reduced() ? 0 : 520);
}

// The plain answer rises in word by word (opacity/transform only).
function animateWords(h) {
  if (!h) return;
  const words = h.textContent.trim().split(/\s+/);
  h.innerHTML = words.map((w, i) => `<span class="w" style="--w:${i}">${esc(w)}</span>`).join(" ");
  h.classList.add("words");
}

function setState(state) {
  const page = $(".ask-page", mainEl);
  if (page) page.dataset.state = state;
  dock(state === "thread" ? "on" : "auto");
}

// On a phone the docked bar covers the bottom of the screen: bring a finished answer (or the opened law) clear of
// it, unless the reader has scrolled on their own since asking. Never past the top of the element.
let userScrolled = false;
["wheel", "touchmove", "keydown"].forEach((ev) => addEventListener(ev, (e) => {
  if (ev === "keydown" && !["ArrowDown", "ArrowUp", "PageDown", "PageUp", "Home", "End", " "].includes(e.key)) return;
  if (!e.target.closest?.("input, textarea")) userScrolled = true;
}, { passive: true }));
function keepClear(el, idx = null, { force = false } = {}) {
  if (!el || (!force && userScrolled) || (idx != null && idx !== THREAD.length - 1)) return;
  const r = el.getBoundingClientRect();
  const bar = dockEl?.classList.contains("on") ? $(".ask-bar", dockEl).getBoundingClientRect().top : innerHeight;
  const top = (parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--nav-h")) || 76) + 12;
  const need = Math.min(r.bottom - (bar - 14), r.top - top);
  if (need > 4) scrollBy({ top: need, behavior: reduced() ? "auto" : "smooth" });
}

// As-of changed after an answer: say which date it answered for, with a one-tap re-ask for the new date.
function markStale() {
  THREAD.forEach((t, i) => {
    const foot = turnEl(i)?.querySelector(".ask-a:not(.leaving) .ask-foot");
    if (!foot) return;
    const old = $(".ask-stale", foot);
    const stale = t.res && t.res.as_of && !t.res.asked_as_of && t.res.as_of !== CE.asOf(); // a date the question named is not stale
    if (!stale) { old?.remove(); return; }
    const html = `${esc(s("stale", { d: fmtD(t.res.as_of, lang()) }))} <button type="button" class="linkish" data-ask-again="${i}">${esc(s("ask_again", { d: fmtD(CE.asOf(), lang()) }))}</button>`;
    if (old) old.innerHTML = html; else foot.insertAdjacentHTML("beforeend", `<span class="ask-stale">${html}</span>`);
  });
}

// ------------------------------------------------------------------ asking: one question at a time, the rest wait --
// A question asked while another is being answered waits in a small "Up next" list above the docked bar (fixed, so
// nothing on the page moves) and becomes a turn when the answer above is done.
const QUEUE = [];
let active = 0, seq = 0, lastSubmit = { q: "", at: 0 };
function ask(q) {
  q = String(q || "").replace(/\s+/g, " ").trim();
  if (!q) return;
  if (!mainEl || !document.body.contains(mainEl) || !$(".ask-page", mainEl)) { CE.navigate("ask/" + encodeURIComponent(q)); return; }
  const now = performance.now();
  if (q === lastSubmit.q && now - lastSubmit.at < 1200) return; // a double Enter or double tap
  lastSubmit = { q, at: now };
  $$("[data-ask-form] input").forEach((i) => { i.value = ""; i.blur(); });
  if (active) { QUEUE.push({ q }); drawQueue(); return; }
  start(q);
}
function start(q) {
  const idx = THREAD.push({ q, res: null, partial: null, steps: { cur: "rules" }, state: "running", asOf: CE.asOf() }) - 1;
  const first = $(".ask-page", mainEl).dataset.state === "home";
  setState("thread");
  const th = $(".ask-thread", mainEl);
  turnEl(idx - 1)?.querySelector(".ask-next")?.remove(); // chips belong to the latest answer only
  th.insertAdjacentHTML("beforeend", turnHTML(THREAD[idx], idx, { fresh: true }));
  const turn = turnEl(idx);
  turn.classList.add("is-pending");
  entered($(".ask-steps.enter", turn));
  userScrolled = false;
  requestAnimationFrame(() => turn.scrollIntoView({ block: "start", behavior: first || reduced() ? "auto" : "smooth" }));
  run(idx);
}
function next() {
  const it = QUEUE.shift();
  drawQueue();
  if (!it) return;
  if (it.retry != null) retry(it.retry); else start(it.q);
}
function drawQueue() {
  const d = dockEl && $(".ask-queue", dockEl);
  if (!d) return;
  d.hidden = !QUEUE.length;
  d.innerHTML = QUEUE.length ? `<span class="lbl">${esc(s("up_next"))}</span>${QUEUE.map((it, i) =>
    `<span class="ask-qitem"><span>${esc(it.q || THREAD[it.retry]?.q || "")}</span><button type="button" class="ask-qx" data-ask-unqueue="${i}" aria-label="${esc(s("remove"))}">×</button></span>`).join("")}` : "";
}

async function run(idx) {
  const my = ++seq;
  active = my;
  const t = THREAD[idx];
  const done = () => { if (active === my) { active = 0; next(); } };
  history.replaceState(history.state, "", "#/ask/" + encodeURIComponent(t.q));
  // the steps are the server's real progress; keep each one on screen long enough to read
  let lastStep = 0;
  const paced = (fn) => { const wait = Math.max(0, lastStep + 140 - performance.now()); lastStep = performance.now() + wait; setTimeout(fn, wait); };
  const ctrl = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; ctrl.abort(); }, 45000);
  let final = null;
  try {
    const resp = await fetch("/api/ask", {
      method: "POST", signal: ctrl.signal,
      headers: { "content-type": "application/json", accept: "text/event-stream" },
      body: JSON.stringify({ q: t.q, lang: lang(), as_of: CE.asOf(), history: historyFor(idx), place: placeFor(idx) }),
    });
    if (resp.status === 429) throw Object.assign(new Error("busy"), { kind: "busy" });
    if (!resp.ok || !resp.body) throw new Error("http");
    const reader = resp.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    for (;;) {
      const { value, done: end } = await reader.read();
      if (end) break;
      buf += dec.decode(value, { stream: true });
      let i;
      while ((i = buf.indexOf("\n\n")) >= 0) {
        const block = buf.slice(0, i); buf = buf.slice(i + 2);
        const ev = /^event: (.+)$/m.exec(block)?.[1];
        const data = /^data: (.+)$/m.exec(block)?.[1];
        if (!ev || !data) continue;
        const d = JSON.parse(data);
        if (ev === "step") {
          paced(() => {
            if (t.res) return;
            if (d.id === "rules" && d.n != null) { t.steps.rules = d.n; t.steps.cur = "quotes"; }
            else if (d.id === "rules" && d.cached) { t.steps.rules = true; t.steps.cur = "quotes"; }
            if (d.id === "engine") t.steps.engine = true;
            if (d.id === "quotes") { t.steps.quotes = d.n != null ? { n: d.n, v: d.verbatim ?? d.n } : { n: null }; t.steps.cur = "writing"; }
            if (d.id === "writing") t.steps.cur = "writing";
            if (d.id === "partial") t.partial = d;
            if (d.id === "place") t.place = d.place;
            if (d.id === "general") t.general = true;
            updateTurn(idx);
          });
        } else if (ev === "answer") {
          final = d;
          t.place = d.place;
          clearTimeout(timer);
          paced(() => {
            t.res = final; t.state = "done"; updateTurn(idx, { reveal: true }); if (final.followups?.length) addChips(idx);
            // focus stays in the thread (not on <body>), without scrolling and without opening the phone keyboard
            setTimeout(() => keepFocus(idx), 0);
          });
          paced(done); // the next question can go while the follow-up chips are still being checked
        } else if (ev === "followups") {
          paced(() => { if (t.res) { t.res.followups = d.followups; addChips(idx); } });
        } else if (ev === "error") throw Object.assign(new Error("server"), { kind: d.status === 429 ? "busy" : "err" });
      }
    }
    if (!final) throw new Error("no answer");
  } catch (e) {
    if (!final) {
      t.state = "error";
      t.err = e.kind || (navigator.onLine === false ? "offline" : timedOut ? "timeout" : "err");
      paced(() => updateTurn(idx));
      if (location.hash.startsWith("#/ask/")) history.replaceState(history.state, "", "#/ask");
      paced(done);
    }
  } finally {
    clearTimeout(timer);
    paced(() => turnEl(idx)?.classList.remove("is-pending")); // chips are in (or never coming): no blank screen below
  }
}
function retry(idx) {
  const t = THREAD[idx];
  if (!t || t.state !== "error") return;
  if (active) { QUEUE.push({ retry: idx }); drawQueue(); return; }
  Object.assign(t, { state: "running", res: null, partial: null, err: null, steps: { cur: "rules" } });
  updateTurn(idx);
  userScrolled = false;
  run(idx);
}

// the conversation so far, as the server returned it (nothing else leaves the tab)
// after an answer, focus is never left on <body>: the follow-up box with a mouse or keyboard, the answer card on touch
// screens (focusing an input there would open the keyboard over the answer)
function keepFocus(idx) {
  const ae = document.activeElement;
  if (ae && ae !== document.body && document.body.contains(ae)) return;
  const input = dockEl && $("input", dockEl);
  if (input && matchMedia("(pointer: fine)").matches) { input.focus({ preventScroll: true }); return; }
  const a = turnEl(idx)?.querySelector(".ask-a");
  if (a) { a.tabIndex = -1; a.focus({ preventScroll: true }); }
}
function placeFor(idx) { // only the first question of a conversation; later turns carry the place themselves
  const a = homeAddr();
  return a && !historyFor(idx).length ? { kind: "address", address_id: a.id } : null;
}
function historyFor(idx) {
  return THREAD.slice(0, idx).filter((x) => x.res).slice(-5).map((x) => ({
    q: x.q, resolved_q: x.res.resolved_q || null, lang: x.res.lang || null, memo: x.res.memo || null, context: x.res.context || null,
  }));
}

// Checked follow-up chips arrive after the answer. They go under the latest answer card only (the latest turn is at
// least a screen tall, so nothing below moves); a newer question makes them pointless, so they are dropped then.
function addChips(idx) {
  const t = THREAD[idx];
  const turn = turnEl(idx);
  if (!turn || idx !== THREAD.length - 1 || !t.res.followups?.length || $(".ask-next", turn)) return;
  turn.insertAdjacentHTML("beforeend", followupsHTML(t.res.followups));
}

// "Type your address": the bar at the bottom takes it; the server finds the place (our 500 or the Census geocoder)
function typeAddress() {
  dock("on");
  const inp = $("#ask-q-dock");
  if (!inp) return;
  inp.placeholder = s("addr_ph");
  setTimeout(() => inp.focus(), 60);
}

// "Show me the law": the quote cards, one tap away
function toggleLaw(law, open = !law.classList.contains("open")) {
  const btn = $("[data-ask-law]", law), body = $(".ask-law-body", law);
  law.classList.toggle("open", open);
  btn.setAttribute("aria-expanded", String(open));
  const idx = Number(law.closest(".ask-turn")?.dataset.idx);
  const t = THREAD[idx];
  if (t) t.lawOpen = open;
  $(".lbl", btn).textContent = sx(t?.res?.lang || lang(), open ? "hide_law" : "show_law");
  body.inert = !open;
  if (open) setTimeout(() => keepClear(body, null, { force: true }), reduced() ? 0 : 470);
}

// ------------------------------------------------------------------ dock (the "Ask anything…" bar) --
let dockEl = null, dockMode = "off", dockExternal = false, dockPhones = true;
function ensureDock() {
  if (dockEl && document.body.contains(dockEl)) return dockEl;
  const wrap = document.createElement("div");
  wrap.className = "ask-dock";
  wrap.innerHTML = `<div class="ask-queue" hidden aria-live="polite"></div>` + bar("ask-bar--dock", s("ph_dock"), "ask-q-dock") + `<p class="ask-dock-note">${esc(s("privacy_short"))}</p>`;
  document.body.append(wrap);
  dockEl = wrap;
  return wrap;
}
function dock(mode) {
  dockMode = mode;
  const onAsk = !!(mainEl && $(".ask-page", mainEl) && document.body.contains(mainEl));
  const external = dockExternal && !(narrow() && !dockPhones && !onAsk); // other pages: phones only if asked to
  if ((mode === "off" || mode === "ext") && !external) { dockEl?.classList.remove("on"); document.documentElement.classList.remove("ask-docked"); return; }
  const d = ensureDock();
  $("input", d).placeholder = THREAD.length && mainEl && $(".ask-page", mainEl) ? s("ph_more") : s("ph_dock");
  $(".ask-dock-note", d).textContent = s("privacy_short");
  d.classList.toggle("on-ask", onAsk); // the privacy line only under the Ask page's own input
  const show = (on) => { d.classList.toggle("on", on); document.documentElement.classList.toggle("ask-docked", on); };
  io?.disconnect(); io = null;
  if (mode === "on" || external && mode !== "auto") { show(true); return; }
  const hero = mainEl && $(".ask-bar--hero", mainEl);
  if (!hero) { show(external); return; }
  io = new IntersectionObserver(([e]) => show(!e.isIntersecting && e.boundingClientRect.top < 0), { threshold: 0 });
  io.observe(hero);
}

// ------------------------------------------------------------------ placeholder: the suggestions take turns --
function rotatePlaceholder() {
  const qs = PH[lang()] || PH.en;
  if (narrow()) { clearInterval(phTimer); return; } // phones keep the neutral placeholder
  clearInterval(phTimer);
  const inp = $("#ask-q-hero", mainEl);
  if (!inp || qs.length < 2 || reduced()) return;
  let i = 0;
  phTimer = setInterval(() => {
    if (!document.body.contains(inp)) { clearInterval(phTimer); return; }
    if (document.activeElement === inp || inp.value) return;
    i = (i + 1) % qs.length;
    inp.classList.add("ph-out");
    setTimeout(() => { inp.placeholder = phText(qs[i]); inp.classList.remove("ph-out"); }, 220);
  }, 4200);
}

// ------------------------------------------------------------------ route + events --
function render(main, arg) {
  const mounted = mainEl === main && $(".ask-page", main);
  mainEl = main;
  navLink();
  if (mounted) { relabel(); } // a language or as-of switch, or the second route() of a cold load: no re-render
  else {
    const restoring = THREAD.length > 0; // back from another page: the thread as it was, no entrance animations
    const sharing = !!arg && !THREAD.some((t) => t.q === arg); // a shared #/ask/<question> link: straight to the thread
    main.innerHTML = pageHTML(suggestions(), { thread: restoring || sharing, still: restoring });
    drawThread();
    setState(restoring || sharing ? "thread" : "home");
    photo();
    if (restoring) restoreScroll();
  }
  fetchSuggestions();
  rotatePlaceholder();
  document.title = `${s("title")} · Clause & Effect`;
  if (arg && !THREAD.some((t) => t.q === arg)) ask(arg);
}

// language switch: every label in place; old answers keep their own language, the open laws stay open
function relabel() {
  const pg = $(".ask-page", mainEl);
  if (!pg) return;
  const set = (sel, text) => $$(sel, pg).forEach((el) => { if (el.textContent !== text) el.textContent = text; });
  set(".ask-h1", s("title"));
  set(".ask-sub", s("sub"));
  set(".ask-new", s("new_q"));
  set(".ask-privacy .long", s("privacy"));
  set(".ask-privacy .short .t", s("privacy_short"));
  $$(".ask-sr", pg).forEach((el) => { el.textContent = el.closest(".ask-q") ? `${s("you")}: ` : s("title"); });
  const st = $(".ask-statement p", pg);
  if (st) st.innerHTML = statementHTML();
  const box = $(".ask-chips", pg);
  if (box && box.dataset.qs !== JSON.stringify(suggestions())) box.outerHTML = chipsHTML(suggestions(), false);
  const hero = $("#ask-q-hero", pg);
  if (hero) hero.placeholder = phText((PH[lang()] || PH.en)[0]);
  $$(".ask-send", document).forEach((b) => b.setAttribute("aria-label", s("send")));
  if (dockEl) dock(dockMode);
  THREAD.forEach((t, i) => { const c = turnEl(i)?.querySelector(".ask-steps:not(.leaving)"); if (c) patchSteps(c, t); });
  markStale();
}

// the hero photo fades in once it is decoded (no half-painted image)
function photo() {
  const img = mainEl && $("[data-ask-photo]", mainEl);
  if (!img) return;
  const show = () => img.closest(".ask-photo")?.classList.add("ready");
  if (img.complete && img.naturalWidth) show();
  else (img.decode ? img.decode().catch(() => {}) : Promise.resolve()).then(show);
}

// back to Ask from another page: where the reader left the thread
addEventListener("scroll", () => { if (mainEl && $(".ask-page[data-state='thread']", mainEl)) askY = scrollY; }, { passive: true });
function restoreScroll() {
  const y = askY;
  const go = () => scrollTo({ top: y || document.documentElement.scrollHeight, behavior: "instant" });
  document.addEventListener("ce:route", () => requestAnimationFrame(go), { once: true });
}

document.addEventListener("submit", (e) => {
  const f = e.target.closest("[data-ask-form]");
  if (!f) return;
  e.preventDefault();
  const q = f.q.value.trim();
  if (q) ask(q);
});
document.addEventListener("click", (e) => {
  const c = e.target.closest("[data-ask]");
  if (c && (c.closest(".ask-page") || c.closest(".ask-dock"))) { ask(c.dataset.ask); return; }
  if (e.target.closest("[data-ask-addr]")) { typeAddress(); return; }
  if (e.target.closest("[data-ask-at-x]")) {
    try { sessionStorage.removeItem("ce.addr"); } catch { /* private mode */ }
    $$("[data-ask-at]").forEach((el) => el.remove());
    $("#ask-q-hero", mainEl)?.focus();
    return;
  }
  if (e.target.closest("[data-ask-privacy]")) { CE.openModal(s("privacy_more"), `<p class="lead-p">${esc(s("privacy"))}</p>`); return; }
  const uq = e.target.closest("[data-ask-unqueue]");
  if (uq) { QUEUE.splice(Number(uq.dataset.askUnqueue), 1); drawQueue(); return; }
  const rt = e.target.closest("[data-ask-retry]");
  if (rt) { retry(Number(rt.dataset.askRetry)); return; }
  const ag = e.target.closest("[data-ask-again]");
  if (ag) { const t = THREAD[Number(ag.dataset.askAgain)]; if (t) { lastSubmit = { q: "", at: 0 }; ask(t.q); } return; }
  const lb = e.target.closest("[data-ask-law]");
  if (lb) { toggleLaw(lb.closest(".ask-law")); return; }
  const n = e.target.closest(".ask-sup");
  if (n) {
    const turn = n.closest(".ask-turn");
    const law = turn && $(".ask-law", turn);
    if (law && !law.classList.contains("open")) toggleLaw(law, true);
    const el = turn && $(`.ask-cite[data-n="${n.dataset.cite}"]`, turn);
    if (el) setTimeout(() => { el.scrollIntoView({ block: "center", behavior: reduced() ? "auto" : "smooth" }); el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash"); }, law ? 180 : 0);
    return;
  }
  if (e.target.closest("[data-ask-new]")) {
    THREAD.length = 0; QUEUE.length = 0; drawQueue();
    history.replaceState(history.state, "", "#/ask");
    const m = mainEl; mainEl = null;
    render(m);
    scrollTo({ top: 0, behavior: "auto" });
    setTimeout(() => $("#ask-q-hero", mainEl)?.focus(), 50);
  }
});
document.addEventListener("ce:route", (e) => {
  if (e.detail.view !== "ask") { clearInterval(phTimer); io?.disconnect(); io = null; dock(dockExternal ? "ext" : "off"); }
});
document.addEventListener("ce:lang", () => navLink());

function navLink() {
  const tabs = $(".tabs");
  if (tabs && !$('a[data-route="ask"]', tabs)) {
    const a = document.createElement("a");
    a.href = "#/ask"; a.dataset.route = "ask";
    const first = $('a[data-route="lookup"]', tabs);
    first ? first.after(a) : tabs.prepend(a);
  }
  const foot = $(".footer-links");
  if (foot && !$('a[href="#/ask"]', foot)) {
    const a = document.createElement("a");
    a.href = "#/ask";
    const first = $('a[href="#/"]', foot);
    first ? first.after(a) : foot.prepend(a);
  }
  $$('.tabs a[data-route="ask"], .footer-links a[href="#/ask"]').forEach((a) => { a.textContent = s("nav"); });
  $$('.tabs a[data-route="ask"]').forEach((a) => { a.dataset.short = s("nav"); });
  if (location.hash.replace(/^#\/?/, "").split(/[/?]/)[0] === "ask") $$('.tabs a[data-route="ask"]').forEach((a) => a.setAttribute("aria-current", "page"));
}

window.CEAsk = Object.freeze({
  /** Ask a question: on the Ask page it joins the thread, elsewhere it opens #/ask/<question>. */
  ask,
  /** Dock the "Ask anything…" bar at the bottom of the viewport on the current and following pages. */
  mountDock({ phones = true } = {}) { dockExternal = true; dockPhones = phones; dock("ext"); },
  unmountDock() { dockExternal = false; dock(dockMode === "on" ? "on" : "off"); },
  /** Sources > For reviewers shows its "Audit log" link (/ask/audit) when this is set. */
  audit: true,
  /** For tests: the answer card markup for a server response (everything from the server is escaped). */
  _answerHTML: (res) => answerHTML({ res, place: res.place }, 0),
});

navLink();
CE.addRoute("ask", (main, arg) => render(main, arg));
