// Try it with a new law (#/try): paste, upload or pick a sample ordinance; the batch pipeline (navigator/trylaw.py)
// reads it live and streams each step: read (AI), check quotes (code), consolidate + dates (AI), validate (code),
// plain answer (AI, checked by code), apply to our sample buildings (rules engine, no AI). Server: web/trylaw.py.
// Entry points: a link under "How it works" on Sources and one on the Rules page head (no extra tab).
const CE = window.CE;
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => CE.escape(s ?? "");

const T = {
  en: {
    title: "Try it with a new law", h: "Try it with a new law.",
    lead: "Paste an ordinance or a statute. The same pipeline that built our {r} rules reads it live: it pulls out the rules, checks every quote word for word, writes the plain answer and shows which of our {b} sample buildings it would change.",
    label: "The law's text", ph: "Paste the text of an ordinance or a statute here, or drop a .txt, .pdf or .html file.",
    upload: "Upload .txt, .pdf or .html", real: "real", fictional: "fictional",
    where: "Where does it apply?", found: "Found in the text. Pick another place if it's wrong.", pick: "Pick the place the law covers.",
    other: "Another US city…", other_l: "City and state", other_ph: "Austin, TX", state: "{s} (state law)",
    go: "Read this law", again: "Read it again", reading: "Reading…",
    note: "We don't keep your text: only a fingerprint of it and the result, so the same text answers instantly.",
    nla: "Not legal advice.", nla_es: "No guardamos su texto. No es asesoría legal.",
    fic_note: "Fictional: written for this demo, not a law of the City of Newark.",
    real_note: "Real: Santa Monica's security deposit rules, from santamonica.gov.",
    idle: "Paste a law or pick a sample, then press Read this law. Each step shows here as it happens.",
    s_read: "Read the law", s_quotes: "Check every quote", s_review: "Consolidate and check dates", s_check: "Validate", s_plain: "Write the plain answer", s_apply: "Apply to our buildings",
    ai: "AI", code: "code", waiting: "Waiting",
    d_read: "Found {n} in your text{c}.", d_read0: "No rule on our six topics in this text.",
    d_quotes: "{v} of {n} quotes found word for word in your text.", d_quotes0: "No quotes to check.",
    d_review: "{n} after checking against our {p} rules{e}.", d_eff: " · effective {d}",
    d_check: "Schema: {e} · {q} quotes word for word · status as of {d}.", d_err0: "0 errors", d_err: "{n} errors",
    d_plain: "EN + ES, {p} of {n} checked by code.", d_apply: "{c} of {n} {p} sample buildings change.", d_apply0: "We have no sample buildings in {p}.", d_apply_n: "No rule to apply.",
    log: "Pipeline log ({n} lines)", log1: "Pipeline log (1 line)", cached_t: "Answered from the cache in {s} s (first read took {f} s).", cold_t: "Read in {s} s, {c} model calls.",
    inj_h: "Your text has lines that talk to an AI.", inj_p: "We read them as words of the law, never as instructions: the model has no tools, its output must fit our rule schema, and every quote is checked by code. Lines found:",
    rules_h: "{n} found", rules_lead: "Rule records in our rules.json format. Each quote is searched in your text by code, not by the model.",
    n_rule: "1 rule", n_rules: "{n} rules", n_find: "1 finding without a rule", n_finds: "{n} findings without a rule",
    q_ok: "Found word for word in your text", q_bad: "Not found word for word in your text: treat this rule with care", q_other: "Quoted from our {d} source, not your text",
    sum_q: "{v}/{n} quotes word for word", sum_e0: "0 schema errors", sum_e: "{n} schema errors", sum_t: "{s} s · {c} model calls", sum_cached: "from the cache",
    c_schema: "Schema valid (rule_record.schema.json)", c_schema_bad: "Schema errors: {e}", c_date: "Starts {d}: your text says “{q}” (found word for word)", c_date_ai: "Starts {d}: date read by AI, not found word for word in your text", c_nodate: "No effective date in the text",
    c_plain: "Plain answer: numbers and dates checked by code", c_plain_rev: "Plain answer flagged for review by the checks", c_plain_tpl: "Plain answer: a fixed sentence (the model's draft failed the checks)",
    c_conf: "May conflict: {n}", sure: "{n}% sure", record: "The rule record",
    f_category: "Category", f_jurisdiction: "Jurisdiction", f_requirement: "Requirement", f_key_value: "Key value", f_coverage_conditions: "Coverage", f_exemptions: "Exemptions", f_effective_date: "Effective date", f_status: "Status", f_penalty: "Penalty", f_citation: "Citation", f_interaction: "Interaction",
    findings_h: "Checked and found no rule", none: "We found no rule on our six topics (rent increases, evictions, deposits, application fees, screening, rent-setting software) in this text.",
    dl: "Download rules.json", copy: "Copy as JSON", copied: "Copied the rules as JSON",
    ch_h: "What it changes in {p}", ch_lead: "Our rules engine (no AI) ran all {n} {p} sample buildings with and without this law, as of {d}.",
    ch_change: "{n} change", ch_unk: "{n} depend on a fact we don't have", ch_none: "{n} not covered", ch_soon: "{n} start later",
    ch_empty: "None of our sample buildings in {p} is covered by this law.", ch_noplace: "We have no sample buildings in {p}, so there's nothing to compare. The rules above are still in our format.",
    ch_more: "Show all {n} buildings", ch_from0: "No rule", built: "built {y}", units: "{n} units", units_r: "{a}–{b} units", units_x: "units not in records",
    replaces: "This text is already part of our Santa Monica rules ({d}). The comparison leaves that copy out, so you see the city without it and with it.",
    starts: "Starts {d}", foot: "An automated reading of the text you pasted. Nothing here changes the rules on the rest of the site.",
    over: "Over the limit: paste only the sections about renting.", short: "Paste at least {n} characters.",
    up_read: "Reading {f}…", up_ok: "{f}: {n} characters", net: "The connection dropped. Press Read this law again: a finished reading answers instantly.",
  },
  es: {
    title: "Pruébelo con una ley nueva", h: "Pruébelo con una ley nueva.",
    lead: "Pegue una ordenanza o una ley. El mismo proceso que creó nuestras {r} reglas la lee en vivo: extrae las reglas, comprueba cada cita palabra por palabra, escribe la respuesta sencilla y muestra cuáles de nuestros {b} edificios de muestra cambiaría.",
    label: "El texto de la ley", ph: "Pegue aquí el texto de una ordenanza o una ley, o suelte un archivo .txt, .pdf o .html.",
    upload: "Subir .txt, .pdf o .html", real: "real", fictional: "ficticia",
    where: "¿Dónde aplica?", found: "Lo encontramos en el texto. Elija otro lugar si no es correcto.", pick: "Elija el lugar que cubre la ley.",
    other: "Otra ciudad de EE. UU.…", other_l: "Ciudad y estado", other_ph: "Austin, TX", state: "{s} (ley estatal)",
    go: "Leer esta ley", again: "Leerla otra vez", reading: "Leyendo…",
    note: "No guardamos su texto: solo una huella de él y el resultado, para que el mismo texto se responda al instante.",
    nla: "No es asesoría legal.", nla_es: "We don't keep your text. Not legal advice.",
    fic_note: "Ficticia: escrita para esta demostración, no es una ley de la ciudad de Newark.",
    real_note: "Real: las reglas de depósitos de Santa Monica, de santamonica.gov.",
    idle: "Pegue una ley o elija un ejemplo y presione Leer esta ley. Cada paso aparece aquí mientras ocurre.",
    s_read: "Leer la ley", s_quotes: "Comprobar cada cita", s_review: "Consolidar y comprobar fechas", s_check: "Validar", s_plain: "Escribir la respuesta sencilla", s_apply: "Aplicar a nuestros edificios",
    ai: "IA", code: "código", waiting: "En espera",
    d_read: "Encontramos {n} en su texto{c}.", d_read0: "Ninguna regla sobre nuestros seis temas en este texto.",
    d_quotes: "{v} de {n} citas encontradas palabra por palabra en su texto.", d_quotes0: "No hay citas que comprobar.",
    d_review: "{n} tras compararlas con nuestras reglas de {p}{e}.", d_eff: " · vigente desde el {d}",
    d_check: "Esquema: {e} · {q} citas palabra por palabra · estado al {d}.", d_err0: "0 errores", d_err: "{n} errores",
    d_plain: "Inglés y español, {p} de {n} comprobadas por código.", d_apply: "Cambian {c} de {n} edificios de muestra en {p}.", d_apply0: "No tenemos edificios de muestra en {p}.", d_apply_n: "No hay reglas que aplicar.",
    log: "Registro del proceso ({n} líneas)", log1: "Registro del proceso (1 línea)", cached_t: "Respondido desde la memoria en {s} s (la primera lectura tomó {f} s).", cold_t: "Leído en {s} s, {c} llamadas al modelo.",
    inj_h: "Su texto tiene líneas que le hablan a una IA.", inj_p: "Las leemos como palabras de la ley, nunca como instrucciones: el modelo no tiene herramientas, su respuesta debe cumplir nuestro esquema de reglas y el código comprueba cada cita. Líneas encontradas:",
    rules_h: "{n}", rules_lead: "Registros de reglas en nuestro formato rules.json. El código busca cada cita en su texto; no lo hace el modelo.",
    n_rule: "1 regla encontrada", n_rules: "{n} reglas encontradas", n_find: "1 hallazgo sin regla", n_finds: "{n} hallazgos sin regla",
    q_ok: "Encontrada palabra por palabra en su texto", q_bad: "No se encontró palabra por palabra en su texto: tome esta regla con cautela", q_other: "Citada de nuestra fuente {d}, no de su texto",
    sum_q: "{v}/{n} citas palabra por palabra", sum_e0: "0 errores de esquema", sum_e: "{n} errores de esquema", sum_t: "{s} s · {c} llamadas al modelo", sum_cached: "desde la memoria",
    c_schema: "Esquema válido (rule_record.schema.json)", c_schema_bad: "Errores de esquema: {e}", c_date: "Empieza el {d}: su texto dice “{q}” (encontrado palabra por palabra)", c_date_ai: "Empieza el {d}: fecha leída por la IA, no encontrada palabra por palabra en su texto", c_nodate: "El texto no da fecha de vigencia",
    c_plain: "Respuesta sencilla: el código comprobó cifras y fechas", c_plain_rev: "Las comprobaciones marcaron la respuesta sencilla para revisión", c_plain_tpl: "Respuesta sencilla: una frase fija (el borrador del modelo no pasó las comprobaciones)",
    c_conf: "Posible conflicto: {n}", sure: "{n} % de seguridad", record: "El registro de la regla",
    f_category: "Categoría", f_jurisdiction: "Jurisdicción", f_requirement: "Requisito", f_key_value: "Valor clave", f_coverage_conditions: "Cobertura", f_exemptions: "Exenciones", f_effective_date: "Fecha de vigencia", f_status: "Estado", f_penalty: "Sanción", f_citation: "Cita", f_interaction: "Relación con otras leyes",
    findings_h: "Revisado, sin regla", none: "No encontramos ninguna regla sobre nuestros seis temas (aumentos de renta, desalojos, depósitos, cargos por solicitud, evaluación de inquilinos, software para fijar rentas) en este texto.",
    dl: "Descargar rules.json", copy: "Copiar como JSON", copied: "Reglas copiadas como JSON",
    ch_h: "Qué cambia en {p}", ch_lead: "Nuestro motor de reglas (sin IA) evaluó los {n} edificios de muestra de {p} con y sin esta ley, al {d}.",
    ch_change: "{n} cambian", ch_unk: "{n} dependen de un dato que no tenemos", ch_none: "{n} no cubiertos", ch_soon: "{n} empiezan después",
    ch_empty: "Esta ley no cubre ninguno de nuestros edificios de muestra en {p}.", ch_noplace: "No tenemos edificios de muestra en {p}, así que no hay nada que comparar. Las reglas de arriba siguen en nuestro formato.",
    ch_more: "Ver los {n} edificios", ch_from0: "Sin regla", built: "construido en {y}", units: "{n} viviendas", units_r: "{a}–{b} viviendas", units_x: "viviendas sin registro",
    replaces: "Este texto ya forma parte de nuestras reglas de Santa Monica ({d}). La comparación deja fuera esa copia, así que ve la ciudad sin ella y con ella.",
    starts: "Empieza el {d}", foot: "Una lectura automática del texto que pegó. Nada de esto cambia las reglas en el resto del sitio.",
    over: "Supera el límite: pegue solo las secciones sobre el alquiler.", short: "Pegue al menos {n} caracteres.",
    up_read: "Leyendo {f}…", up_ok: "{f}: {n} caracteres", net: "Se perdió la conexión. Presione Leer esta ley otra vez: una lectura terminada responde al instante.",
  },
};
const L = () => (CE.lang() === "es" ? "es" : "en");
const tx = (k, v = {}) => String(T[L()][k] ?? T.en[k] ?? k).replace(/\{(\w+)\}/g, (_, x) => v[x] ?? "");
const num = (n) => Number(n).toLocaleString(L() === "es" ? "es-US" : "en-US");
const STEPS = [["read", "ai"], ["quotes", "code"], ["review", "ai"], ["check", "code"], ["plain", "ai"], ["apply", "code"]];
const ico = (p) => `<svg class="ico" viewBox="0 0 24 24" aria-hidden="true">${p}</svg>`;
const IC = {
  check: ico('<path d="m5 12 4.5 4.5L19 7"/>'), up: ico('<path d="M12 16V4M7 9l5-5 5 5M5 20h14"/>'), doc: ico('<path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5M10 13h6M10 17h6"/>'),
  dl: ico('<path d="M12 4v12M7 11l5 5 5-5M5 20h14"/>'), arrow: ico('<path d="M5 12h14M13 6l6 6-6 6"/>'), alert: ico('<path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17.5v.01"/>'),
  x: ico('<path d="M6 6l12 12M18 6 6 18"/>'),
};
const shortJ = (j) => (j && j.length > 2 ? j.replace(/, [A-Z]{2}$/, "") : CE.t({ CA: "California", NJ: "New Jersey", MA: "Massachusetts" }[j] || j));
const catName = (c) => { const v = CE.t("cat_" + c); return v.startsWith("cat_") ? c.replace(/_/g, " ") : v; };
const lvl = (l) => (L() === "es" ? { city: "ciudad", state: "estado", county: "condado" }[l] || l : l);
const resLabel = (r) => { const v = CE.t("r_" + r); return v.startsWith("r_") ? r : v; };

// state kept across re-renders (language switch, Back)
const S = { text: "", place: "", other: "", sample: "", placeFound: false, manual: false, run: null, meta: null, busy: false, ctl: null };

async function meta() { if (!S.meta) S.meta = await CE.api("/api/try/meta"); return S.meta; }

function placeOptions(m) {
  const st = { CA: "California", NJ: "New Jersey", MA: "Massachusetts" };
  const all = [...m.places.cities, ...m.places.extension];
  return ["CA", "NJ", "MA"].map((s) => `<optgroup label="${esc(CE.t(st[s]))}"><option value="${s}">${esc(tx("state", { s: CE.t(st[s]) }))}</option>${all.filter((j) => j.endsWith(", " + s)).sort().map((j) => `<option value="${esc(j)}">${esc(shortJ(j))}</option>`).join("")}</optgroup>`).join("")
    + `<option value="__other">${esc(tx("other"))}</option>`;
}

// the place named first in the text: one of our cities or states, else "City of X, <State>" (a new city)
function guessPlace(text, m) {
  const head = text.slice(0, 4000);
  const st = { CA: "California", NJ: "New Jersey", MA: "Massachusetts" };
  const at = (re) => { const x = head.search(re); return x < 0 ? Infinity : x; };
  const hits = [
    ...[...m.places.extension, ...m.places.cities].map((j) => [j, at(new RegExp(`\\b${j.replace(/, [A-Z]{2}$/, "").replace(/ /g, "\\s+")}\\b`, "i"))]),
    ...Object.entries(st).map(([k, v]) => [k, at(new RegExp(`\\b${v.replace(" ", "\\s+")}\\b`, "i")) + 0.5]), // a city named as early wins
  ];
  const o = head.match(/\b(?:City|Town|Village) of ([A-Z][A-Za-z .'-]{1,30}?),?\s+(Alabama|Alaska|Arizona|Arkansas|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming)\b/i);
  if (o) hits.push([`${o[1].trim().replace(/\b\w/g, (c) => c.toUpperCase()).replace(/\B\w+/g, (w) => w.toLowerCase())}, ${o[2].replace(/\b\w/g, (c) => c.toUpperCase()).replace(/\B\w+/g, (w) => w.toLowerCase())}`, o.index]);
  const best = hits.filter((h) => h[1] !== Infinity).sort((x, y) => x[1] - y[1])[0];
  return best ? best[0] : "";
}

function stepsHTML() {
  return `<ol class="lsteps">${STEPS.map(([id, who]) => `<li class="lstep" data-step="${id}"><span class="lk" aria-hidden="true">${IC.check}</span><span class="lt"><b>${esc(tx("s_" + id))}<span class="tl-who${who === "ai" ? " ai" : ""}">${esc(tx(who))}</span><span class="tl-time"></span></b><small></small></span></li>`).join("")}</ol>`;
}

async function view(main) {
  document.title = `${tx("title")} · Clause & Effect`;
  $$(".tabs a").forEach((a) => (a.dataset.route === "audit" ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current")));
  const m = await meta();
  const c = m.counts || {};
  const sample = (s) => `<button type="button" class="tl-chip" data-sample="${esc(s.id)}" aria-pressed="${S.sample === s.id}">${IC.doc}${esc(s["title_" + L()])} <span class="tag${s.kind === "fictional" ? " fic" : ""}">${esc(tx(s.kind))}</span></button>`;
  main.innerHTML = `<div class="tl">
<header class="page-head"><h1>${esc(tx("h"))}</h1><p>${esc(tx("lead", { r: c.rules ?? 62, b: num(c.buildings ?? 540) }))}</p></header>
<div class="tl-grid">
<section class="tl-card" aria-labelledby="tl-lbl">
  <div class="tl-label"><label id="tl-lbl" for="tl-text">${esc(tx("label"))}</label><span class="tl-count" id="tl-count" aria-live="polite"></span></div>
  <textarea class="tl-text" id="tl-text" spellcheck="false" autocapitalize="off" autocomplete="off" placeholder="${esc(tx("ph"))}" aria-describedby="tl-note"></textarea>
  <p class="tl-over" id="tl-over" hidden></p>
  <div class="tl-samples"><button type="button" class="tl-chip" id="tl-up">${IC.up}${esc(tx("upload"))}</button><input type="file" id="tl-file" accept=".txt,.pdf,.html,.htm,text/plain,application/pdf,text/html" hidden>${m.samples.map(sample).join("")}</div>
  <p class="tl-src" id="tl-src" hidden></p>
  <div class="tl-row"><label class="tl-field"><span>${esc(tx("where"))}</span><select id="tl-place">${placeOptions(m)}</select><small id="tl-found">${esc(tx("pick"))}</small></label>
    <label class="tl-field" id="tl-other-f" hidden><span>${esc(tx("other_l"))}</span><input id="tl-other" type="text" autocomplete="off" placeholder="${esc(tx("other_ph"))}"></label>
    <button type="button" class="btn primary tl-go" id="tl-go">${esc(tx("go"))} ${IC.arrow.replace('class="ico"', 'class="ico arrow-i"')}</button></div>
  <p class="tl-err" id="tl-err" role="alert" hidden></p>
  <p class="tl-note" id="tl-note">${esc(tx("note"))} <strong>${esc(tx("nla"))}</strong> · <span lang="${L() === "es" ? "en" : "es"}">${esc(tx("nla_es"))}</span></p>
</section>
<section class="steps-card tl-steps" id="tl-steps" role="status" aria-live="polite">${stepsHTML()}<p class="tl-idle" id="tl-idle">${esc(tx("idle"))}</p><p class="tl-took" id="tl-took" hidden></p><details class="tl-log" id="tl-log" hidden><summary></summary><pre></pre></details></section>
</div>
<div id="tl-out"></div>
</div>`;
  const ta = $("#tl-text"), sel = $("#tl-place");
  ta.value = S.text;
  const setPlace = (p, found) => {
    S.place = p; S.placeFound = !!found;
    if ([...sel.options].some((o) => o.value === p)) { sel.value = p; $("#tl-other-f").hidden = true; }
    else if (p) { sel.value = "__other"; $("#tl-other-f").hidden = false; $("#tl-other").value = S.other = p; }
    $("#tl-found").textContent = tx(found ? "found" : "pick");
  };
  const count = () => {
    const n = ta.value.length, el = $("#tl-count");
    el.textContent = `${num(n)} / ${num(m.limits.max_chars)}`;
    el.classList.toggle("over", n > m.limits.max_chars);
    const o = $("#tl-over"); o.hidden = n <= m.limits.max_chars; o.textContent = o.hidden ? "" : tx("over");
  };
  const srcNote = () => { const s = m.samples.find((x) => x.id === S.sample), el = $("#tl-src"); el.hidden = !s; if (s) { el.className = `tl-src${s.kind === "fictional" ? " fic" : ""}`; el.textContent = tx(s.kind === "fictional" ? "fic_note" : "real_note"); } };
  const fresh = (text, sampleId = "") => {
    ta.value = S.text = text; S.sample = sampleId; count(); srcNote();
    $$("[data-sample]", main).forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.sample === sampleId)));
    S.manual = false;
    const g = guessPlace(text, m); if (g) setPlace(g, true);
    err("");
  };
  setPlace(S.place || "", S.placeFound); if (!S.place) sel.value = "CA";
  count(); srcNote();
  ta.addEventListener("input", () => {
    S.text = ta.value; count();
    if (S.sample) { S.sample = ""; srcNote(); $$("[data-sample]", main).forEach((b) => b.setAttribute("aria-pressed", "false")); }
    if (!ta.value.trim()) S.manual = false;
    if (!S.manual) { const g = guessPlace(ta.value, m); if (g && g !== S.place) setPlace(g, true); }
  });
  sel.addEventListener("change", () => { S.manual = true; const o = sel.value === "__other"; $("#tl-other-f").hidden = !o; S.place = o ? S.other : sel.value; S.placeFound = false; $("#tl-found").textContent = tx("pick"); if (o) $("#tl-other").focus(); });
  $("#tl-other").addEventListener("input", (e) => { S.manual = true; S.other = S.place = e.target.value.trim(); });
  $$("[data-sample]", main).forEach((b) => b.addEventListener("click", async () => {
    const d = await CE.api(`/api/try/sample/${b.dataset.sample}`);
    fresh(d.text, d.id); setPlace(d.jurisdiction, true);
    if (!matchMedia("(max-width: 1000px)").matches) ta.scrollTop = 0;
    run();
  }));
  // upload: the file goes to the server once to become text (PDFs via pdftotext), then it is just the text above
  const file = $("#tl-file");
  $("#tl-up").addEventListener("click", () => file.click());
  const takeFile = async (f) => {
    if (!f) return;
    err(""); $("#tl-count").textContent = tx("up_read", { f: f.name });
    try {
      if (f.size > m.limits.max_file) throw new Error(tx("over"));
      const r = await fetch(`/api/try/file?name=${encodeURIComponent(f.name)}`, { method: "POST", body: f, headers: { "content-type": "application/octet-stream" } });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail?.[L()] || d.detail || r.statusText);
      fresh(d.text);
      CE.toast(tx("up_ok", { f: f.name, n: num(d.chars) }));
    } catch (e) { count(); err(e.message); }
    file.value = "";
  };
  file.addEventListener("change", () => takeFile(file.files[0]));
  ta.addEventListener("dragover", (e) => { e.preventDefault(); ta.classList.add("drag"); });
  ta.addEventListener("dragleave", () => ta.classList.remove("drag"));
  ta.addEventListener("drop", (e) => { ta.classList.remove("drag"); if (e.dataTransfer?.files?.length) { e.preventDefault(); takeFile(e.dataTransfer.files[0]); } });
  $("#tl-go").addEventListener("click", () => run());
  if (S.run) paint(S.run, true);
}

function err(text) { const el = $("#tl-err"); if (!el) return; el.hidden = !text; el.textContent = text || ""; }

// ------------------------------------------------------------------------------------------- the run --
async function run() {
  const m = S.meta, text = $("#tl-text").value;
  const place = $("#tl-place").value === "__other" ? $("#tl-other").value.trim() : $("#tl-place").value;
  err("");
  if (text.length > m.limits.max_chars) { err(`${tx("over")} (${num(text.length)} / ${num(m.limits.max_chars)})`); return; }
  if (text.trim().length < m.limits.min_chars) { err(tx("short", { n: num(m.limits.min_chars) })); return; }
  S.ctl?.abort();
  const ctl = (S.ctl = new AbortController());
  const st = (S.run = { place, events: [], steps: {}, log: [], result: null, start: null, error: null, t0: performance.now() });
  paint(st);
  if (matchMedia("(max-width: 1000px)").matches) $("#tl-steps")?.scrollIntoView({ block: "start", behavior: RM() ? "auto" : "smooth" });
  let r;
  try {
    r = await fetch("/api/try", { method: "POST", signal: ctl.signal, headers: { "content-type": "application/json", accept: "text/event-stream" }, body: JSON.stringify({ text, jurisdiction: place, sample: S.sample }) });
  } catch (e) { if (ctl.signal.aborted) return; st.error = { [L()]: tx("net") }; paint(st); return; }
  if (!r.ok) {
    const d = await r.json().catch(() => ({}));
    st.error = typeof d.detail === "object" ? d.detail : { en: d.detail || r.statusText };
    paint(st); return;
  }
  const rd = r.body.getReader(), dec = new TextDecoder();
  let buf = "";
  try {
    for (;;) {
      const { value, done } = await rd.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let i;
      while ((i = buf.indexOf("\n\n")) >= 0) {
        const block = buf.slice(0, i); buf = buf.slice(i + 2);
        const data = block.split("\n").filter((l) => l.startsWith("data: ")).map((l) => l.slice(6)).join("\n");
        if (!data) continue;
        const ev = JSON.parse(data);
        if (S.run !== st) return;
        if (ev.event === "start") st.start = ev;
        else if (ev.event === "step") st.steps[ev.id] = { ...(st.steps[ev.id] || {}), ...ev };
        else if (ev.event === "log") st.log.push(ev.line);
        else if (ev.event === "result") st.result = ev.result;
        else if (ev.event === "error") st.error = ev;
        paint(st);
      }
    }
  } catch (e) { if (ctl.signal.aborted) return; }
  if (S.run === st && !st.result && !st.error) { st.error = { [L()]: tx("net") }; paint(st); }
}

function stepLine(id, s, res) {
  const d = s || {};
  if (id === "read") {
    const n = d.rules || 0;
    return n ? tx("d_read", { n: tx(n === 1 ? "n_rule" : "n_rules", { n }).replace(/ found$| encontradas?$/, ""), c: d.categories?.length ? ": " + d.categories.map(catName).join(", ").toLowerCase() : "" }) : tx("d_read0");
  }
  if (id === "quotes") return d.total ? tx("d_quotes", { v: d.verbatim, n: d.total }) : tx("d_quotes0");
  if (id === "review") return tx("d_review", { n: tx(d.rules === 1 ? "n_rule" : "n_rules", { n: d.rules ?? 0 }).replace(/ found$| encontradas?$/, ""), p: shortJ(res?.jurisdiction || S.run?.start?.jurisdiction || ""), e: d.effective?.length ? tx("d_eff", { d: d.effective.map((x) => CE.fmtDate(x)).join(", ") }) : "" });
  if (id === "check") {
    const sc = (d.checks || []).find((c) => c.id === "schema") || {}, q = (d.checks || []).find((c) => c.id === "quotes_verbatim") || {};
    return tx("d_check", { e: sc.n ? tx("d_err", { n: sc.n }) : tx("d_err0"), q: `${q.n ?? 0}/${q.of ?? 0}`, d: CE.fmtDate("2026-10-01") });
  }
  if (id === "plain") return tx("d_plain", { p: d.passed ?? 0, n: d.n ?? 0 });
  if (id === "apply" && res && !res.rules.length) return tx("d_apply_n");
  if (id === "apply") return d.sample ? tx("d_apply", { c: d.changed, n: d.sample, p: shortJ(res?.jurisdiction || S.run?.start?.jurisdiction || "") }) : tx("d_apply0", { p: shortJ(S.run?.start?.jurisdiction || "") });
  return "";
}

function paint(st, restore = false) {
  const box = $("#tl-steps");
  if (!box) return;
  const go = $("#tl-go"), running = !st.result && !st.error;
  go.disabled = running && !restore;
  go.firstChild.textContent = running && !restore ? tx("reading") + " " : (st.result ? tx("again") : tx("go")) + " ";
  $("#tl-idle").hidden = true;
  if (st.error) err(st.error[L()] || st.error.en || "");
  let seen = false;
  for (const [id] of STEPS) {
    const li = $(`.lstep[data-step="${id}"]`, box), s = st.steps[id];
    li.classList.remove("run", "done", "fail");
    if (s?.state === "done") { li.classList.add("done"); $(".tl-time", li).textContent = `${s.seconds ?? 0} s`; $("small", li).textContent = stepLine(id, s, st.result); }
    else if (s?.state === "run" && !st.error) { li.classList.add("run"); $(".tl-time", li).textContent = ""; $("small", li).textContent = ""; seen = true; }
    else if (s?.state === "run" && st.error) { li.classList.add("fail"); }
    else { $(".tl-time", li).textContent = ""; $("small", li).textContent = !seen && !st.start && running ? "" : ""; }
  }
  if (!st.start && running) $(`.lstep[data-step="read"]`, box).classList.add("run");
  const took = $("#tl-took"), res = st.result;
  took.hidden = !res;
  if (res) {
    const calls = res.llm?.calls ?? 0;
    took.textContent = res.cached ? tx("cached_t", { s: res.replay_seconds ?? 0, f: st.start?.first_seconds ?? res.wall_seconds }) : tx("cold_t", { s: res.wall_seconds, c: calls });
  }
  const lg = $("#tl-log");
  lg.hidden = !st.log.length;
  if (st.log.length) { $("summary", lg).textContent = tx(st.log.length === 1 ? "log1" : "log", { n: st.log.length }); $("pre", lg).textContent = st.log.join("\n"); }
  const out = $("#tl-out");
  const inj = st.start?.injection?.length ? `<section class="tl-inj" role="note"><p class="tl-qh warn">${IC.alert}${esc(tx("inj_h"))}</p><p>${esc(tx("inj_p"))}</p><ul>${st.start.injection.map((x) => `<li><code>${esc(x)}</code></li>`).join("")}</ul></section>` : "";
  if (!res) { out.innerHTML = inj; return; }
  if (out.dataset.key === `${st.start?.key}:${L()}` && !restore) return;
  out.dataset.key = `${st.start?.key}:${L()}`;
  out.innerHTML = inj + resultHTML(res);
  $("#tl-dl", out)?.addEventListener("click", () => {
    const blob = new Blob([JSON.stringify(res.rules_json, null, 2) + "\n"], { type: "application/json" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "rules.json"; document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  });
  $("#tl-copy", out)?.addEventListener("click", async () => { try { await navigator.clipboard.writeText(JSON.stringify(res.rules_json, null, 2)); CE.toast(tx("copied")); } catch { /* clipboard blocked */ } });
  $("#tl-more", out)?.addEventListener("click", (e) => { $$(".tl-bl li[hidden]", out).forEach((li) => (li.hidden = false)); e.target.closest("p").remove(); });
  if (!restore && !RM()) out.firstElementChild?.scrollIntoView({ block: "start", behavior: "smooth" });
}
const inText = (q) => !!q && (S.text || "").replace(/\s+/g, " ").includes(q.replace(/\s+/g, " "));
const RM = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

function statusBadge(r) {
  if (r.status === "not_yet_effective" && r.effective_date) return `<span class="tl-b not_yet_effective">${esc(tx("starts", { d: CE.fmtDate(r.effective_date) }))}</span>`;
  return `<span class="tl-b ${esc(r.status)}">${esc(resLabel(r.status))}</span>`;
}

function ruleHTML(r, res) {
  const p = res.plain?.[r.team_rule_id] || {}, q = res.quotes?.[r.team_rule_id] || {};
  const es = L() === "es";
  const ans = (es ? p.answer_es : p.answer_en) || r.key_value || r.title;
  const why = (es ? p.why_es : p.why_en) || r.requirement;
  const other = es ? p.answer_en : p.answer_es;
  const quote = q.found
    ? `<blockquote class="quote"><span class="ctx">…${esc(q.before.replace(/^\S*\s/, " ").replace(/\s+/g, " "))}</span><mark>${esc(r.quoted_span.replace(/\s+/g, " "))}</mark><span class="ctx">${esc(q.after.replace(/\s\S*$/, " ").replace(/\s+/g, " "))}…</span></blockquote>`
    : r.quoted_span ? `<blockquote class="quote">${esc(r.quoted_span)}</blockquote>` : "";
  const qh = q.verbatim ? `<p class="tl-qh ok">${IC.check}${esc(tx("q_ok"))}</p>` : q.doc && q.doc !== "your text" ? `<p class="tl-qh">${IC.doc}${esc(tx("q_other", { d: q.doc }))}</p>` : `<p class="tl-qh bad">${IC.alert}${esc(tx("q_bad"))}</p>`;
  const errs = (res.checks?.find((c) => c.id === "schema")?.errors || []).filter((e) => e.startsWith(r.team_rule_id + ":"));
  const checks = [
    errs.length ? ["bad", tx("c_schema_bad", { e: errs.join("; ") })] : ["ok", tx("c_schema")],
    r.effective_date ? (inText(r.in_force_since_evidence?.quoted_span) ? ["ok", tx("c_date", { d: CE.fmtDate(r.effective_date), q: r.in_force_since_evidence.quoted_span.replace(/\s+/g, " ") })] : ["warn", tx("c_date_ai", { d: CE.fmtDate(r.effective_date) })]) : ["warn", tx("c_nodate")],
    p.method === "template" ? ["warn", tx("c_plain_tpl")] : p.needs_review || !p.passed ? ["warn", tx("c_plain_rev")] : ["ok", tx("c_plain")],
    ...(r.conflict_flag && r.conflict_note ? [["warn", tx("c_conf", { n: r.conflict_note })]] : []),
  ];
  const kv = ["category", "jurisdiction", "requirement", "key_value", "coverage_conditions", "exemptions", "effective_date", "status", "penalty", "citation", "interaction"]
    .filter((k) => r[k]).map((k) => `<dt>${esc(tx("f_" + k))}</dt><dd>${esc(k === "jurisdiction" ? `${r[k]} (${lvl(r.level)})` : r[k])}</dd>`).join("");
  return `<article class="tl-rule">${p[es ? "question_es" : "question_en"] ? `<p class="tl-rq">${esc(p[es ? "question_es" : "question_en"])}</p>` : ""}<p class="tl-ra">${esc(ans)}</p><p class="tl-rwhy">${esc(why)}</p>
${other ? `<p class="tl-es" lang="${es ? "en" : "es"}"><b>${es ? "EN" : "ES"}</b> · ${esc(other)}</p>` : ""}
<div class="tl-badges">${statusBadge(r)}<span class="tl-b">${esc(r.jurisdiction)} · ${esc(lvl(r.level))}</span>${r.citation ? `<span class="tl-b">${esc(r.citation)}</span>` : ""}${r.confidence != null ? `<span class="tl-b">${esc(tx("sure", { n: Math.round(r.confidence * 100) }))}</span>` : ""}</div>
<div class="tl-q">${qh}${quote}</div>
<ul class="tl-checks">${checks.map(([c, s]) => `<li class="${c}">${c === "ok" ? IC.check : IC.alert}<span>${esc(s)}</span></li>`).join("")}</ul>
<details class="tl-more"><summary>${esc(tx("record"))}</summary><dl class="tl-kv">${kv}</dl></details></article>`;
}

function buildingsHTML(res) {
  const b = res.buildings || {}, p = shortJ(res.jurisdiction);
  if (!res.rules.length) return "";
  const head = `<div class="tl-head"><h2>${esc(tx("ch_h", { p }))}</h2>`;
  if (!b.sample_in_place) return `<section class="tl-sec">${head}</div><p class="tl-none">${esc(tx("ch_noplace", { p }))}</p></section>`;
  const by = b.by_result || {};
  const chips = [`<span class="ok">${esc(tx("ch_change", { n: b.changed }))}</span>`];
  if (by.unknown) chips.push(`<span class="warn">${esc(tx("ch_unk", { n: by.unknown }))}</span>`);
  if (b.not_covered) chips.push(`<span>${esc(tx("ch_none", { n: b.not_covered }))}</span>`);
  const units = (x) => x.units_lo != null && x.units_hi != null ? (x.units_lo === x.units_hi ? tx("units", { n: x.units_lo }) : tx("units_r", { a: x.units_lo, b: x.units_hi }))
    : x.units_lo != null ? tx("units", { n: `${x.units_lo}+` }) : tx("units_x");
  const short = (rid) => { const p = res.plain?.[rid] || {}; return String((L() === "es" ? p.answer_es : p.answer_en) || rules[rid]?.key_value || "").replace(/\.$/, ""); };
  const to = (a, rule) => a.result === "not_yet_effective" && rule?.effective_date ? `<span class="to not_yet_effective">${esc(tx("starts", { d: CE.fmtDate(rule.effective_date) }))}</span>`
    : a.result === "applies" && short(a.rule) ? `<span class="to applies">${esc(short(a.rule))}</span>` : `<span class="to ${esc(a.result)}">${esc(resLabel(a.result))}</span>`;
  const rules = Object.fromEntries(res.rules.map((r) => [r.team_rule_id, r]));
  const from = (x, a) => {
    const bf = x.before.filter((e) => e.category === a.category).sort((p, q) => (p.result === "applies" ? -1 : 0) - (q.result === "applies" ? -1 : 0));
    if (!bf.length) return tx("ch_from0");
    const e = bf[0], tag = e.rule.split("-")[0];
    return e.result === "applies" && e.key_value ? `${tag}: ${e.key_value}` : `${tag}: ${resLabel(e.result)}`;
  };
  const linkable = (id) => /^A\d+$/.test(id);
  const row = (x, i) => {
    const inner = `<span><span class="tl-bn">${esc(x.street.replace(/\b([A-Z])([A-Z]+)\b/g, (_, a, b2) => a + b2.toLowerCase()))}</span><br><span class="tl-bs">${esc([shortJ(x.city), x.year_built ? tx("built", { y: x.year_built }) : "", units(x)].filter(Boolean).join(" · "))}</span></span>
<span class="tl-bcs">${x.after.map((a) => `<span class="tl-bc"><span class="tl-bt">${esc(catName(a.category))}</span><span class="tl-bft"><span class="from" title="${esc(from(x, a))}">${esc(from(x, a))}</span><span class="tl-ar" aria-hidden="true">→</span>${to(a, rules[a.rule])}</span></span>`).join("")}</span>`;
    return `<li${i >= 6 ? " hidden" : ""}>${linkable(x.address_id) ? `<a href="#/a/${esc(x.address_id)}">${inner}</a>` : `<div class="tl-brow">${inner}</div>`}</li>`;
  };
  const list = b.list?.length ? `<div class="tl-bl"><ul>${b.list.map(row).join("")}</ul>${b.list.length > 6 ? `<p class="tl-bmore"><button type="button" class="linkish" id="tl-more">${esc(tx("ch_more", { n: b.list.length }))}</button></p>` : ""}</div>` : `<p class="tl-none">${esc(tx("ch_empty", { p }))}</p>`;
  return `<section class="tl-sec">${head}<p>${esc(tx("ch_lead", { n: b.sample_in_place, p, d: CE.fmtDate(b.as_of) }))}</p><div class="tl-sum">${chips.join("")}</div></div>
${res.replaces ? `<p class="tl-src">${esc(tx("replaces", { d: res.replaces }))}</p>` : ""}${list}</section>`;
}

function resultHTML(res) {
  const n = res.rules.length, nf = res.no_rule_findings.length;
  const q = res.checks.find((c) => c.id === "quotes_verbatim") || {}, sc = res.checks.find((c) => c.id === "schema") || {};
  const title = [n ? tx(n === 1 ? "n_rule" : "n_rules", { n }) : "", nf ? tx(nf === 1 ? "n_find" : "n_finds", { n: nf }) : ""].filter(Boolean).join(" · ") || tx("n_rules", { n: 0 });
  const h = L() === "es" ? title : tx("rules_h", { n: title });
  const sum = [
    q.of ? `<span class="${q.n === q.of ? "ok" : "warn"}">${q.n === q.of ? IC.check : IC.alert}${esc(tx("sum_q", { v: q.n, n: q.of }))}</span>` : "",
    `<span class="${sc.n ? "warn" : "ok"}">${sc.n ? IC.alert : IC.check}${esc(sc.n ? tx("sum_e", { n: sc.n }) : tx("sum_e0"))}</span>`,
    `<span>${esc(tx("sum_t", { s: res.wall_seconds, c: res.llm?.calls ?? 0 }))}${res.cached ? ` · ${esc(tx("sum_cached"))}` : ""}</span>`,
  ].join("");
  const findings = nf ? `<div class="tl-find"><h3>${esc(tx("findings_h"))}</h3><ul>${res.no_rule_findings.map((f) => `<li><b>${esc(catName(f.category))}</b> · ${esc(f.finding || f.note || f.summary || f.reason || "")}</li>`).join("")}</ul></div>` : "";
  return `<section class="tl-sec"><div class="tl-head"><h2>${esc(h)}</h2><div class="tl-sum">${sum}</div><p>${esc(tx("rules_lead"))}</p></div>
${n ? `<div class="tl-rules">${res.rules.map((r) => ruleHTML(r, res)).join("")}</div>` : `<p class="tl-none">${esc(tx("none"))}</p>`}${findings}
<div class="tl-acts"><button type="button" class="btn primary" id="tl-dl">${IC.dl}${esc(tx("dl"))}</button><button type="button" class="btn" id="tl-copy">${esc(tx("copy"))}</button></div></section>
${buildingsHTML(res)}
<p class="tl-foot"><strong>${esc(tx("nla"))}</strong> ${esc(tx("foot"))} · <span lang="${L() === "es" ? "en" : "es"}">${esc(L() === "es" ? "Not legal advice. An automated reading of the text you pasted." : "No es asesoría legal. Lectura automática del texto que pegó.")}</span></p>`;
}

// ------------------------------------------------------------------------------------------ entries --
function entryLinks(view) {
  const main = $("#main");
  if (view === "audit") {
    const how = $(".how3", main);
    if (how && !$(".tl-entry", how)) how.insertAdjacentHTML("beforeend", `<p class="tl-entry"><a class="btn" href="#/try">${IC.doc}<span>${esc(tx("title"))}</span>${IC.arrow.replace('class="ico"', 'class="ico arrow-i"')}</a></p>`);
  } else if (view === "rules") {
    const head = $(".page-head", main);
    if (head && !$(".tl-entry", head)) head.insertAdjacentHTML("beforeend", `<p class="tl-entry tl-entry-s"><a href="#/try">${esc(tx("title"))}${IC.arrow.replace('class="ico"', 'class="ico arrow-i"')}</a></p>`);
  }
}
document.addEventListener("ce:route", (e) => entryLinks(e.detail?.view));
CE.addRoute("try", view);
entryLinks((location.hash.slice(2).split(/[/?]/)[0]) || "");
