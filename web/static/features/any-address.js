// Any address, not just the 500 samples (#39). Self-contained feature module: hooks into the address search
// (home search + "/" palette), offers "Check this address" for anything that looks like a street address, then
// resolves it live (US Census), shows the jurisdiction stack, asks for the few building facts that matter and
// renders the answers. Uses window.CE.renderAnswers (app.js answer cards) when present, else a minimal renderer.
// Not legal advice. Addresses are sent to /api/resolve only; /api/evaluate sees state, city and facts.

const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const RM = matchMedia("(prefers-reduced-motion: reduce)");
const lang = () => localStorage.getItem("lang") || "en";
const asOf = () => sessionStorage.getItem("asof") || "2026-10-01";

const EN = {
  opt_t: "Check this address", opt_s: "Any address in CA, NJ or MA · live lookup",
  kicker: "Any address · live", title: "Check any address", ph: "Street, city, state", go: "Check",
  locating: "Finding the legal jurisdiction…", evaluating: "Checking the rules…",
  nla: "Not legal advice.", nla_body: "Public law with citations, for information only. Check the cited source.",
  covered: "In our corpus", not_covered: "Not in our corpus", state: "State", county: "County", city: "City",
  facts: "Building facts", facts_lead: "Only what the public data can't tell us. Nothing is stored.",
  year_built: "Year built", units: "Units", owner_occupied: "Owner lives there", certificate_of_occupancy_date: "Certificate of occupancy",
  yes: "Yes", no: "No", unsure: "Not sure",
  resolves: (n) => `resolves ${n}`, depends: (n) => `${n} depend on this`, optional: "optional",
  prompt: (f, n) => `Add the ${f.toLowerCase()} to resolve ${n} unknown answer${n === 1 ? "" : "s"}.`,
  all_clear: "Every answer is definite for these facts.",
  answers: "Answers as of", out_title: "Outside our coverage", out_body: "We cover state law in California, New Jersey and Massachusetts, and local law in these cities:",
  state_only: "Only state law was checked. Local ordinances here are not in our corpus.",
  nomatch: "We could not find this address.", busy: "Too many lookups. Please wait a minute.", down: "The US Census geocoder did not answer. Try again in a moment.",
  r_applies: "Applies", r_unknown: "Unknown", r_superseded: "Superseded", r_not_yet_effective: "Not yet in effect", r_pending: "Pending bill", r_failed: "Failed · not law",
  depends_on: "Depends on:", why_source: "Why & source", no_rule: "No rule found for this address.", proposals: "Not law: pending bills and failed proposals",
  close: "Close", matched: "Census match", source: "US Census Geocoder", eg: "e.g.",
};
const ES = {
  opt_t: "Consultar esta dirección", opt_s: "Cualquier dirección en CA, NJ o MA · consulta en vivo",
  kicker: "Cualquier dirección · en vivo", title: "Consultar cualquier dirección", ph: "Calle, ciudad, estado", go: "Consultar",
  locating: "Buscando la jurisdicción legal…", evaluating: "Revisando las normas…",
  nla: "No es asesoría legal.", nla_body: "Leyes públicas con citas, solo informativo. Verifique la fuente citada.",
  covered: "En nuestro corpus", not_covered: "Fuera de nuestro corpus", state: "Estado", county: "Condado", city: "Ciudad",
  facts: "Datos del edificio", facts_lead: "Solo lo que los datos públicos no dicen. No se guarda nada.",
  year_built: "Año de construcción", units: "Unidades", owner_occupied: "El dueño vive allí", certificate_of_occupancy_date: "Certificado de ocupación",
  yes: "Sí", no: "No", unsure: "No sé",
  resolves: (n) => `resuelve ${n}`, depends: (n) => `${n} dependen de esto`, optional: "opcional",
  prompt: (f, n) => `Indique ${f.toLowerCase()} para resolver ${n} respuesta${n === 1 ? "" : "s"} desconocida${n === 1 ? "" : "s"}.`,
  all_clear: "Todas las respuestas son definitivas con estos datos.",
  answers: "Respuestas al", out_title: "Fuera de nuestra cobertura", out_body: "Cubrimos la ley estatal de California, Nueva Jersey y Massachusetts, y la ley local de estas ciudades:",
  state_only: "Solo se revisó la ley estatal. Las ordenanzas locales de aquí no están en nuestro corpus.",
  nomatch: "No encontramos esta dirección.", busy: "Demasiadas consultas. Espere un minuto.", down: "El geocodificador del Censo no respondió. Inténtelo de nuevo.",
  r_applies: "Aplica", r_unknown: "Desconocido", r_superseded: "Reemplazada", r_not_yet_effective: "Aún no vigente", r_pending: "Proyecto de ley", r_failed: "Fallida · no es ley",
  depends_on: "Depende de:", why_source: "Por qué y fuente", no_rule: "No se encontró ninguna norma para esta dirección.", proposals: "No es ley: proyectos pendientes y propuestas fallidas",
  close: "Cerrar", matched: "Coincidencia del Censo", source: "Geocodificador del Censo de EE. UU.", eg: "p. ej.",
};
const t = (k) => (lang() === "es" && ES[k]) || EN[k] || k;
const svg = (p) => `<svg class="ico" viewBox="0 0 24 24" aria-hidden="true">${p}</svg>`;
const I = {
  globe: svg('<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18"/>'),
  building: svg('<path d="M4 21V5l8-2v18M12 8l8 2v11M8 8v.01M8 12v.01M8 16v.01M16 13v.01M16 17v.01M2 21h20"/>'),
  arrow: svg('<path d="M5 12h14M13 6l6 6-6 6"/>'),
  close: svg('<path d="M6 6l12 12M18 6 6 18"/>'),
  q: svg('<circle cx="12" cy="12" r="9.5"/><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1 .9-1 1.7M12 17v.01"/>'),
  cal: svg('<rect x="4" y="5" width="16" height="15" rx="3"/><path d="M8 3v4M16 3v4M4 10h16"/>'),
  chev: svg('<path d="m9 6 6 6-6 6"/>'),
  check: svg('<path d="m5 12 4.5 4.5L19 7"/>'),
  info: svg('<circle cx="12" cy="12" r="9.5"/><path d="M12 11v6M12 7.5v.01"/>'),
};

// ------------------------------------------------------------------ search integration --
const looksLikeAddress = (q) => q.length >= 6 && /\d/.test(q) && /[a-z]{2,}/i.test(q);
const hasSample = (list) => !!list.querySelector("[data-id]");
function optionHtml(q) {
  return `<li class="opt aa-opt" role="option" aria-selected="false" data-aa>
    <span class="pin">${I.globe}</span>
    <div><div class="addr">${esc(t("opt_t"))}</div><div class="sub">“${esc(q)}” · ${esc(t("opt_s"))}</div></div>
    <span class="arrow">${I.arrow}</span></li>`;
}
function decorate(input, list) {
  list.querySelector(".aa-opt")?.remove();
  const q = input.value.trim();
  if (!looksLikeAddress(q)) return;
  list.insertAdjacentHTML("beforeend", optionHtml(q));
  if (list.id === "hs") { list.hidden = false; input.setAttribute("aria-expanded", "true"); }
}
const targets = (el) => el?.id === "hq" ? [el, $("#hs")] : el?.matches?.("#cmdk input") ? [el, $("#cmdk-list")] : null;
// app.js renders the suggestions in its own listeners on the input; ours runs after (bubbling to document).
for (const ev of ["input", "focusin"]) document.addEventListener(ev, (e) => {
  const tg = targets(e.target);
  if (tg && tg[1]) setTimeout(() => decorate(...tg), 0);
});
document.addEventListener("mousedown", (e) => {
  const li = e.target.closest?.(".aa-opt");
  if (!li) return;
  e.preventDefault();
  const input = li.closest("#cmdk") ? $("#cmdk input") : $("#hq");
  pick(input?.value.trim() || "");
});
document.addEventListener("click", (e) => { if (e.target.closest?.(".aa-opt")) e.preventDefault(); });
// Enter with no sample match: run the live check instead of doing nothing.
document.addEventListener("keydown", (e) => {
  if (e.key !== "Enter" || e.isComposing) return;
  const tg = targets(e.target);
  if (!tg || !tg[1]) return;
  const q = tg[0].value.trim();
  if (looksLikeAddress(q) && !hasSample(tg[1])) { e.preventDefault(); e.stopPropagation(); pick(q); }
}, true);
document.addEventListener("submit", (e) => {
  const form = e.target.closest?.(".big-search");
  const q = $("#hq")?.value.trim() || "";
  if (form && looksLikeAddress(q) && !hasSample($("#hs"))) { e.preventDefault(); pick(q); }
}, true);
function pick(q) {
  const cmdk = $("#cmdk");
  if (cmdk && !cmdk.hidden) cmdk.hidden = true;
  open(q);
}

// ------------------------------------------------------------------ sheet --
let sheet = null, state = null, evalTimer = null, evalSeq = 0, opener = null;
function open(q) {
  opener = document.activeElement;
  state = { q, place: null, facts: {}, data: null };
  if (!sheet) {
    sheet = document.createElement("div");
    sheet.className = "aa-scrim";
    sheet.innerHTML = `<section class="aa-sheet" role="dialog" aria-modal="true" aria-labelledby="aa-title">
      <header class="aa-head">
        <div><span class="aa-kicker">${I.globe}<span data-t="kicker"></span></span><h2 id="aa-title" data-t="title"></h2></div>
        <button type="button" class="aa-x" data-aa-close>${I.close}</button>
      </header>
      <form class="aa-search" role="search" autocomplete="off">
        <input type="text" name="q" spellcheck="false" maxlength="200" required>
        <button class="pill primary" type="submit"><span data-t="go"></span>${I.arrow}</button>
      </form>
      <div class="aa-body" aria-live="polite"></div>
      <footer class="aa-nla">${I.info}<span><b data-t="nla"></b> <span data-t="nla_body"></span></span></footer>
    </section>`;
    document.body.append(sheet);
    sheet.addEventListener("mousedown", (e) => { if (e.target === sheet) close(); });
    sheet.addEventListener("click", (e) => { if (e.target.closest("[data-aa-close]")) close(); });
    $(".aa-search", sheet).addEventListener("submit", (e) => { e.preventDefault(); const v = $(".aa-search input", sheet).value.trim(); if (v) { state = { q: v, place: null, facts: {}, data: null }; resolve(); } });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && sheet && !sheet.hidden) close(); });
    // as-of date or language changed in the header: refresh the answers
    document.addEventListener("change", (e) => { if (e.target.id === "asof" && state?.place && !sheet.hidden) setTimeout(evaluate, 0); });
    document.addEventListener("click", (e) => { if (e.target.closest(".seg button") && state?.place && !sheet.hidden) setTimeout(() => { labels(); evaluate(); }, 50); });
  }
  labels();
  $(".aa-search input", sheet).value = q;
  $(".aa-x", sheet).setAttribute("aria-label", t("close"));
  sheet.hidden = false; sheet.classList.remove("closing");
  document.documentElement.classList.add("aa-lock");
  setTimeout(() => $(".aa-x", sheet).focus({ preventScroll: true }), 30);
  resolve();
}
function labels() { sheet.querySelectorAll("[data-t]").forEach((el) => { el.textContent = t(el.dataset.t); }); $(".aa-search input", sheet).placeholder = t("ph"); }
function close() {
  if (!sheet || sheet.hidden) return;
  document.documentElement.classList.remove("aa-lock");
  document.activeElement?.blur?.();
  if (opener?.isConnected && opener.offsetParent) opener.focus({ preventScroll: true });
  if (RM.matches) { sheet.hidden = true; return; }
  sheet.classList.add("closing");
  setTimeout(() => { sheet.hidden = true; sheet.classList.remove("closing"); }, 220);
}
const body = () => $(".aa-body", sheet);
const loading = (msg) => `<div class="aa-loading"><span class="aa-spin" aria-hidden="true"></span>${esc(msg)}</div>
  <div class="sk" style="height:84px;margin-top:14px;border-radius:20px"></div><div class="sk" style="height:160px;margin-top:12px;border-radius:20px"></div>`;
async function post(url, payload) {
  const r = await fetch(url, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(payload) });
  if (r.status === 429) throw new Error(t("busy"));
  if (r.status === 503) throw new Error(t("down"));
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof d.detail === "string" ? d.detail : (d.detail?.[0]?.msg || r.status));
  return d;
}

async function resolve() {
  body().innerHTML = loading(t("locating"));
  let d;
  try { d = await post("/api/resolve", { address: state.q }); }
  catch (err) { body().innerHTML = `<div class="aa-msg warn">${I.info}<div>${esc(err.message)}</div></div>`; return; }
  if (!d.match) { body().innerHTML = `<div class="aa-msg warn">${I.info}<div><b>${esc(t("nomatch"))}</b> ${esc(d.message || "")}</div></div>${coveredHtml(d.covered)}`; return; }
  state.place = d;
  if (!d.in_scope) { body().innerHTML = placeHtml(d) + `<div class="aa-msg"><div><b>${esc(t("out_title"))}.</b> ${esc(t("out_body"))}</div></div>${coveredHtml(d.covered)}`; return; }
  body().innerHTML = placeHtml(d) + `<section class="aa-facts" aria-labelledby="aa-fh"></section><div class="aa-results"></div>`;
  evaluate();
}
function coveredHtml(cov) {
  if (!cov) return "";
  const names = { CA: "California", NJ: "New Jersey", MA: "Massachusetts" };
  return `<div class="aa-covered">${Object.entries(cov).map(([st, cities]) => `<div><b>${esc(names[st] || st)}</b><div class="aa-cities">${cities.map((c) => `<span class="aa-city">${esc(c.replace(/, ..$/, ""))}</span>`).join("")}</div></div>`).join("")}</div>`;
}
function placeHtml(d) {
  const rows = d.stack.map((s) => {
    const tile = s.level === "state" ? esc(s.code || "") : s.level === "county" ? I.globe : I.building;
    const tag = s.level === "county" ? "" : `<span class="aa-tag ${s.covered ? "ok" : "no"}">${s.covered ? I.check : ""}${esc(t(s.covered ? "covered" : "not_covered"))}</span>`;
    return `<div class="trow"><span class="tile ${s.level === "city" && s.covered ? "navy" : ""}">${tile}</span><div><div class="l1">${esc(s.name)}</div><div class="l2">${esc(t(s.level))}${s.note ? " · " + esc(s.note) : ""}</div></div>${tag}</div>`;
  }).join("");
  return `<section class="aa-place">
    <div class="aa-addr"><span class="aa-eyebrow">${esc(t("matched"))}</span><h3>${esc(titleCase(d.matched_address || state.q))}</h3>
      <a class="aa-src" href="https://www.openstreetmap.org/?mlat=${d.lat}&mlon=${d.lon}#map=17/${d.lat}/${d.lon}" target="_blank" rel="noopener">${esc(t("source"))} · ${(+d.lat).toFixed(4)}, ${(+d.lon).toFixed(4)}</a></div>
    <div class="tile-rows">${rows}</div>
    ${d.scope === "state" ? `<div class="callout unknown">${I.info}<div>${esc(d.message)}</div></div>` : ""}
  </section>`;
}
const titleCase = (s) => String(s || "").toLowerCase().replace(/\b\w/g, (m) => m.toUpperCase()).replace(/\b(Ca|Nj|Ma|Dc|Nw|Ne|Sw|Se)\b/g, (m) => m.toUpperCase());

// ------------------------------------------------------------------ facts + evaluation --
function schedule() { clearTimeout(evalTimer); evalTimer = setTimeout(evaluate, 350); }
async function evaluate() {
  const my = ++evalSeq;
  const res = $(".aa-results", sheet);
  if (!res) return;
  if (!state.data) res.innerHTML = loading(t("evaluating"));
  else res.classList.add("aa-stale");
  let d;
  try {
    d = await post("/api/evaluate", { address: { state: state.place.state, jurisdiction: state.place.jurisdiction }, as_of: asOf(), facts: state.facts, lang: lang() });
  } catch (err) {
    if (my === evalSeq) { res.classList.remove("aa-stale"); res.innerHTML = `<div class="aa-msg warn">${I.info}<div>${esc(err.message)}</div></div>`; }
    return;
  }
  if (my !== evalSeq) return;
  state.data = d;
  renderFacts(d);
  res.classList.remove("aa-stale");
  res.innerHTML = summaryHtml(d) + `<div class="aa-answers"></div>`;
  const el = $(".aa-answers", res);
  if (window.CE?.renderAnswers) window.CE.renderAnswers(el, d);
  else el.innerHTML = answersHtml(d);
}
function chipHtml(d, k) {
  const v = state.facts[k], n = d.fact_counts?.[k], dep = d.fact_depends?.[k];
  if (v != null && v !== "") return dep ? `<span class="aa-n dep">${esc(t("depends")(dep))}</span>` : "";
  if (n) return `<span class="aa-n res">${esc(t("resolves")(n))}</span>`;
  return `<span class="aa-n">${esc(t("optional"))}</span>`;
}
function renderFacts(d) {
  const box = $(".aa-facts", sheet), f = state.facts;
  if (!box.firstChild) {
    const oo = f.owner_occupied;
    const lab = (k, id = "") => `<span class="aa-lab"${id ? ` id="${id}"` : ""}>${esc(t(k))}<span data-chip="${k}"></span></span>`;
    box.innerHTML = `<header><h3 id="aa-fh">${esc(t("facts"))}</h3><p>${esc(t("facts_lead"))}</p></header>
      <div class="aa-grid">
        <label class="aa-field">${lab("year_built")}<input name="year_built" type="number" inputmode="numeric" min="1700" max="2100" placeholder="${esc(t("eg"))} 1962"></label>
        <label class="aa-field">${lab("units")}<input name="units" type="number" inputmode="numeric" min="1" max="5000" placeholder="${esc(t("eg"))} 8"></label>
        <div class="aa-field aa-wide">${lab("owner_occupied", "aa-oo")}
          <div class="aa-seg" role="radiogroup" aria-labelledby="aa-oo">
            ${[["yes", true], ["no", false], ["unsure", null]].map(([k, v]) => `<button type="button" role="radio" aria-checked="${oo === v || (v === null && oo == null)}" data-oo="${k}">${esc(t(k))}</button>`).join("")}
          </div></div>
        <label class="aa-field" data-co hidden>${lab("certificate_of_occupancy_date")}<input name="certificate_of_occupancy_date" type="date" min="1700-01-01" max="2100-12-31"></label>
      </div>`;
    box.querySelectorAll("input").forEach((inp) => inp.addEventListener("input", () => {
      const v = inp.value.trim();
      if (!v) delete f[inp.name];
      else if (!inp.checkValidity()) return;
      else f[inp.name] = inp.type === "number" ? parseInt(v, 10) : v;
      schedule();
    }));
    box.querySelectorAll("[data-oo]").forEach((b) => b.addEventListener("click", () => {
      const v = { yes: true, no: false, unsure: null }[b.dataset.oo];
      if (v === null) delete f.owner_occupied; else f.owner_occupied = v;
      box.querySelectorAll("[data-oo]").forEach((x) => x.setAttribute("aria-checked", x === b));
      evaluate();
    }));
  }
  box.querySelectorAll("[data-chip]").forEach((el) => { el.innerHTML = chipHtml(d, el.dataset.chip); });
  $("[data-co]", box).hidden = !(f.certificate_of_occupancy_date || d.fact_counts?.certificate_of_occupancy_date);
}
function summaryHtml(d) {
  const order = ["applies", "unknown", "superseded", "not_yet_effective", "pending"];
  const counts = d.fact_counts || {};
  const top = Object.entries(counts).filter(([, n]) => n > 0).sort((a, b) => b[1] - a[1])[0];
  const lbl = top ? t(top[0]) : "";
  return `<div class="aa-sum">
    <span class="asof-tag">${I.cal}${esc(t("answers"))} ${esc(fmtDate(d.as_of))}</span>
    <div class="sum-row">${order.filter((r) => d.summary[r]).map((r, i) => `<span class="badge ${r} anim" style="--i:${i}">${d.summary[r]} · ${esc(t("r_" + r))}</span>`).join("")}</div>
  </div>
  ${top ? `<p class="aa-prompt">${I.q}<span>${esc(t("prompt")(lbl, top[1]))}</span></p>` : d.unknowns ? "" : `<p class="aa-prompt ok">${I.check}<span>${esc(t("all_clear"))}</span></p>`}
  ${d.scope_note ? `<p class="aa-scope">${esc(t("state_only"))}</p>` : ""}`;
}
const fmtDate = (d) => { const x = new Date(d + "T12:00:00"); return isNaN(x) ? d : x.toLocaleDateString(lang() === "es" ? "es-US" : "en-US", { month: "short", day: "numeric", year: "numeric" }); };

// ------------------------------------------------------------------ minimal answer renderer (fallback) --
const firstSentence = (s) => { const m = String(s || "").match(/^.{20,}?[.;](\s|$)/); return m ? m[0].trim() : String(s || ""); };
function card(item, i) {
  const r = item.rule, res = item.result;
  const hint = res === "unknown" ? `<span class="hint unknown">${I.q}${esc(t("depends_on"))} ${esc(item.missing_fact || "")}</span>`
    : res === "not_yet_effective" ? `<span class="hint nye">${I.cal}${esc(fmtDate(r.effective_date_norm || r.effective_date))}</span>` : "";
  const juris = r.level === "state" ? r.jurisdiction : String(r.jurisdiction).replace(/, ..$/, "");
  return `<article class="rule ${esc(res)}">
    <div class="rule-top"><span class="badge ${esc(res)} anim" style="--i:${i % 4}">${esc(t("r_" + res))}</span><span class="lvl-tag">${esc(juris)}</span></div>
    <h4 class="rule-title">${esc(r.title_display || r.title)}</h4>
    <p class="req">${esc(firstSentence(r.requirement_display || r.requirement))}</p>
    ${r.key_value ? `<p class="kfig">${esc(r.key_value_display || r.key_value)}</p>` : ""}
    ${hint}
    <details class="src more"><summary>${I.chev}${esc(t("why_source"))}</summary><div class="src-body">
      ${item.explanation ? `<p class="why">${esc(item.explanation)}</p>` : ""}
      <blockquote class="quote">${esc(r.quoted_span)}</blockquote>
      <div class="src-meta"><span class="cite">${esc(r.citation)}</span>
        ${r.source_url ? `<a href="${esc(r.source_url)}" target="_blank" rel="noopener">${esc(hostOf(r.source_url))}</a>` : ""}
        <span class="mono">${esc(r.team_rule_id)}</span></div>
    </div></details>
  </article>`;
}
const hostOf = (u) => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return u; } };
function answersHtml(d) {
  let k = 0;
  const cats = d.categories.map((c) => `<section class="cat aa-cat">
      <header class="cat-head"><div><h3>${esc(c.label)}</h3><p class="q">${esc(c.question)}</p></div>
        <div class="count">${c.enacted.map((i) => `<span class="dot ${esc(i.result)}"></span>`).join("")}</div></header>
      <div class="rules-list">${c.enacted.length ? c.enacted.map((it) => card(it, k++)).join("")
        : c.no_rule_findings?.length ? c.no_rule_findings.map((f) => `<div class="norule">${I.info}<span>${esc(f.finding_display || f.finding)}</span></div>`).join("")
        : `<div class="norule">${I.info}<span>${esc(t("no_rule"))}</span></div>`}</div>
    </section>`).join("");
  const props = d.categories.flatMap((c) => [...c.pending, ...c.not_law]);
  return `<div class="cats">${cats}</div>${props.length ? `<section class="proposals aa-props"><div class="inner"><header class="cat-head"><div><h3>${esc(t("proposals"))}</h3></div></header>
    <div class="rules-list">${props.map((it, n) => card(it, n)).join("")}</div></div></section>` : ""}`;
}
