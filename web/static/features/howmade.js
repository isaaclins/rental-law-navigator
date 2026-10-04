// How this answer was made: under "More details" of every topic, four quiet lines that say who decided what.
//   1 Read     the model read the source and pulled out the rule (confidence, source, retrieval date)   AI
//   2 Checked  code found the quoted sentence word for word in that text                               code
//   3 Decided  the rules engine (no AI) applied it to this building, with the facts and where they came from  code
//   4 Worded   the short answer: written ahead of time and checked against the quote, or by AI and checked by code
// plus "Needs a second look" (confidence under 70%) and "May conflict" when the rule says so.
// Data: the topic as app.js has it (rule record, engine result + explanation, plain_source) and GET /api/howmade
// (audit.jsonl extraction entry, plain_language.json). Hook: app.js topicRow() calls CEHowMade.html(c, d).
// Ask uses CEHowMade.askLine(citation, lang) for a one-line form under each "Show me the law" card.

const T = {
  en: {
    title: "How this answer was made", k_ai: "AI", k_code: "code",
    read_o: "AI read the official text on {h}{r} and pulled out this rule.",
    read_s: "AI read {h}{r}, a summary rather than the official text, and pulled out this rule.",
    read_f: "AI read the sources for {p} and found no rule on this.",
    r_part: " (retrieved {d})", sure: "{n}% sure.", log: "Log",
    chk_ok: "Code found the quoted sentence word for word in that text.",
    chk_ok_s: "Code found the quote word for word in that summary.",
    chk_bad: "Code could not find the quote word for word in the source, so treat it with care.",
    chk_none: "The page could not be saved, so code could not check the quote.",
    dec_ok: "The rules engine (no AI) decided it applies here: {f}.",
    dec_all: "The rules engine (no AI) decided it applies here: it covers all of {p}.",
    dec_unk: "The rules engine (no AI) couldn't decide: {f}.",
    dec_later: "The rules engine (no AI) decided it starts here on {d}.",
    dec_none: "The rules engine (no AI) found no rule on this that covers this address.",
    dec_exempt: "The rules engine (no AI) decided {t} doesn't cover this building, using {s}.", dec_exempt_n: "The rules engine (no AI) decided these {n} laws don't cover this building, using {s}.",
    yields_s: "The state rule yields to this one.", yields_o: "The other rule yields to this one.",
    built: "built {y}", units: "{n} units", units_min: "at least {n} units", said: "“{v}”", c_before: "on or before the {d} cutoff", c_after: "after the {d} cutoff", older: "over {n} years old",
    src_rec: "property records", src_use: "the land-use code in property records", src_you: "your answer",
    f_year: "the year built isn't in public records", f_yearonly: "public records have the year built, not the certificate date",
    f_units: "the number of units isn't in public records", f_owner: "whether the owner lives there isn't in public records",
    f_tenancy: "how long you've lived there isn't in public records", f_other: "it depends on a fact public records don't show",
    f_version: "on this date an older version of the law applied that our sources don't include",
    word_rev: "The short answer was written for this rule ahead of time and checked against its quote (not generated live).",
    word_gen: "AI wrote the short answer; code checked its numbers, dates and length.",
    word_flag: "AI wrote the short answer; code checked it, and it is flagged for review.",
    word_tpl: "The short answer is a fixed sentence (no AI).",
    flag_low: "Needs a second look: our reading is {n}% sure, under our 70% bar.",
    flag_conf: "May conflict with {x}: a court or the state may decide which wins.", flag_conf0: "May conflict with another law: a court or the state may decide which wins.",
    flag_data: "Needs a second look: the sources disagree or leave a detail open.",
    log_t: "Extraction log", log_meta: "{m} · prompt {v} · logged {d} · document {doc}", log_out: "What the model wrote for this rule",
    log_all: "Full audit log on Sources", log_fail: "The log could not be loaded.",
    a_found: "AI extracted it", a_found_f: "AI found no rule here", a_vb: "quote checked word for word", a_novb: "quote not found word for word",
    a_eng: "engine: {r}", a_word: "answer by AI, numbers checked by code",
  },
  es: {
    title: "Cómo se hizo esta respuesta", k_ai: "IA", k_code: "código",
    read_o: "La IA leyó el texto oficial en {h}{r} y extrajo esta regla.",
    read_s: "La IA leyó {h}{r}, un resumen y no el texto oficial, y extrajo esta regla.",
    read_f: "La IA leyó las fuentes de {p} y no encontró ninguna regla sobre esto.",
    r_part: " (consultado el {d})", sure: "{n} % de seguridad.", log: "Registro",
    chk_ok: "El código encontró la frase citada palabra por palabra en ese texto.",
    chk_ok_s: "El código encontró la cita palabra por palabra en ese resumen.",
    chk_bad: "El código no encontró la cita palabra por palabra en la fuente; tómela con cautela.",
    chk_none: "No se pudo guardar la página, así que el código no pudo comprobar la cita.",
    dec_ok: "El motor de reglas (sin IA) decidió que aplica aquí: {f}.",
    dec_all: "El motor de reglas (sin IA) decidió que aplica aquí: cubre todo {p}.",
    dec_unk: "El motor de reglas (sin IA) no pudo decidir: {f}.",
    dec_later: "El motor de reglas (sin IA) decidió que aquí empieza el {d}.",
    dec_none: "El motor de reglas (sin IA) no encontró ninguna regla sobre esto para esta dirección.",
    dec_exempt: "El motor de reglas (sin IA) decidió que {t} no cubre este edificio, con datos de {s}.", dec_exempt_n: "El motor de reglas (sin IA) decidió que estas {n} leyes no cubren este edificio, con datos de {s}.",
    yields_s: "La regla estatal cede ante esta.", yields_o: "La otra regla cede ante esta.",
    built: "construido en {y}", units: "{n} unidades", units_min: "al menos {n} unidades", said: "«{v}»", c_before: "en o antes del límite del {d}", c_after: "después del límite del {d}", older: "con más de {n} años",
    src_rec: "registros de propiedad", src_use: "el código de uso del suelo en los registros de propiedad", src_you: "su respuesta",
    f_year: "el año de construcción no está en los registros públicos", f_yearonly: "los registros públicos tienen el año de construcción, no la fecha del certificado",
    f_units: "el número de unidades no está en los registros públicos", f_owner: "si el dueño vive allí no está en los registros públicos",
    f_tenancy: "cuánto tiempo lleva viviendo allí no está en los registros públicos", f_other: "depende de un dato que los registros públicos no muestran",
    f_version: "en esta fecha aplicaba una versión anterior de la ley que nuestras fuentes no incluyen",
    word_rev: "La respuesta corta se escribió para esta regla de antemano y se comprobó con su cita (no se genera en el momento).",
    word_gen: "La IA escribió la respuesta corta; el código comprobó sus números, fechas y longitud.",
    word_flag: "La IA escribió la respuesta corta; el código la comprobó y está marcada para revisión.",
    word_tpl: "La respuesta corta es una frase fija (sin IA).",
    flag_low: "Necesita una segunda revisión: nuestra lectura tiene un {n} % de seguridad, por debajo del 70 %.",
    flag_conf: "Puede entrar en conflicto con {x}: un tribunal o el estado puede decidir cuál prevalece.", flag_conf0: "Puede entrar en conflicto con otra ley: un tribunal o el estado puede decidir cuál prevalece.",
    flag_data: "Necesita una segunda revisión: las fuentes no coinciden o dejan un detalle abierto.",
    log_t: "Registro de extracción", log_meta: "{m} · prompt {v} · registrado el {d} · documento {doc}", log_out: "Lo que escribió el modelo para esta regla",
    log_all: "Registro completo en Fuentes", log_fail: "No se pudo cargar el registro.",
    a_found: "extraída por IA", a_found_f: "la IA no encontró ninguna regla", a_vb: "cita comprobada palabra por palabra", a_novb: "cita no encontrada palabra por palabra",
    a_eng: "motor: {r}", a_word: "respuesta de IA, números comprobados por código",
  },
};
const STATES = { CA: ["California", "California"], NJ: ["New Jersey", "Nueva Jersey"], MA: ["Massachusetts", "Massachusetts"] };

// small monochrome marks: a sparkle for AI, brackets for code
const svg = (d, cls) => `<svg class="hm-i ${cls}" viewBox="0 0 16 16" aria-hidden="true">${d}</svg>`;
const ICON = {
  ai: svg('<path d="M8 1.8c.4 3.2 1.8 4.6 5 5-3.2.4-4.6 1.8-5 5-.4-3.2-1.8-4.6-5-5 3.2-.4 4.6-1.8 5-5z"/>', "is-ai"),
  code: svg('<path d="M5.5 4.5 2 8l3.5 3.5M10.5 4.5 14 8l-3.5 3.5"/>', "is-code"),
  flag: svg('<path d="M8 2.2 14.3 13H1.7z"/><path d="M8 6.4v3M8 11.2v.1"/>', "is-flag"),
};

// GET /api/howmade (small): how each rule's short answer was made (template, checks); fetched once at load
let DATA = null, loading = null;
const load = () => (loading ||= fetch("/api/howmade").then((r) => (r.ok ? r.json() : null)).then((d) => { DATA = d; return d; }).catch(() => null));
if (typeof fetch === "function" && typeof location !== "undefined" && location.origin !== "null") load();

const CE = () => window.CE || {};
const L = (lang) => (lang || CE().lang?.() || "en") === "es" ? "es" : "en";
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const tf = (lg, k, v = {}) => String(T[lg][k] ?? T.en[k] ?? k).replace(/\{(\w+)\}/g, (_, x) => v[x] ?? "");
const fmt = (d) => (d ? (CE().fmtDate ? CE().fmtDate(d) : String(d).slice(0, 10)) : "");
const host = (u) => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return ""; } };
const pct = (x) => Math.round(x * 100);
const isOk = (r) => ["exact", "normalized"].includes(r?.quote_check?.status);
const secondary = (r) => !!(r?.source?.secondary || r?.verification === "secondary_source" || r?.source_verification === "secondary_source");
const placeOf = (j, lg) => STATES[j] ? STATES[j][lg === "es" ? 1 : 0] : String(j || "").replace(/,\s*[A-Z]{2}$/, "");
const order = { applies: 0, unknown: 1, not_yet_effective: 2, superseded: 3 };
const topOf = (c) => [...(c.enacted || [])].sort((a, b) => (order[a.result] ?? 9) - (order[b.result] ?? 9))[0] || null;
function answers(d) {
  const id = d?.address?.address_id;
  if (!id) return null;
  try { return JSON.parse(localStorage.getItem("ce.ans") || "{}")[id] || null; } catch { return null; }
}

// 1 Read: what the model read, how sure it was
function readLine(r, lg) {
  const url = r.source?.url || r.source_url || "", when = r.source?.retrieved_at || r.retrieved_at;
  const rp = when ? tf(lg, "r_part", { d: fmt(when) }) : "";
  const txt = tf(lg, secondary(r) ? "read_s" : "read_o", { h: host(url) || r.citation || "", r: rp });
  const sure = r.confidence != null ? " " + tf(lg, "sure", { n: pct(r.confidence) }) : "";
  const log = r.team_rule_id ? ` <button type="button" class="linkish hm-log" data-hm-log="${esc(r.team_rule_id)}">${esc(tf(lg, "log"))}</button>` : "";
  return { icon: "ai", html: esc(txt + sure) + log };
}
// 2 Checked: the verbatim quote check (code)
function checkLine(r, lg) {
  if (!r.quoted_span) return null;
  const st = r.quote_check?.status;
  if (isOk(r)) return { icon: "code", html: esc(tf(lg, secondary(r) ? "chk_ok_s" : "chk_ok")) };
  if (st === "no_text" || !r.source?.has_text) return { icon: "code", html: esc(tf(lg, "chk_none")) };
  return { icon: "flag", html: esc(tf(lg, "chk_bad")), warn: true };
}
// 3 Decided: the engine's result, the facts it used and where they came from
function factsOf(item, d, lg) {
  const r = item.rule, cov = r.coverage || {}, ex = String(item.explanation_en || item.explanation || "");
  const a = d?.address || {}, ans = answers(d), any = !a.address_id;
  const src = (k) => any || (ans && ans[k] != null) ? tf(lg, "src_you") : tf(lg, "src_rec");
  const out = [], srcs = [];
  if (cov.construction_cutoff || cov.new_construction_exemption) {
    const y = ans?.year_built != null && ans["_year_built"] ? null : (ex.match(/\bbuilt (\d{4})\b/) || [])[1] || a.year_built || d?.facts?.year_built;
    let p = y ? tf(lg, "built", { y }) : ans?.["_year_built"] ? tf(lg, "said", { v: ans["_year_built"] }) : "";
    if (p) {
      srcs.push(src("year_built"));
      const cc = cov.construction_cutoff;
      if (cc?.date) p += ", " + tf(lg, /after/.test(cc.covered_if || "") ? "c_after" : "c_before", { d: fmt(cc.date) });
      else if (cov.new_construction_exemption?.years) p += ", " + tf(lg, "older", { n: cov.new_construction_exemption.years });
      out.push(p);
    }
  }
  if (cov.min_units || cov.max_units || cov.owner_occupied_exemption_max_units) {
    // the building's count, not a rule threshold ("exemption (<= 3 units)"); a lower bound comes from the use code (#148)
    const lo = (ex.match(/\b(?:at least (\d+) units?|(\d+) or more units?)\b/) || []).slice(1).find(Boolean);
    const u = lo ? null : (ex.match(/(?:building has |: )(\d+) units?\b/) || [])[1] || a.units || d?.facts?.units;
    if (u) { out.push(tf(lg, "units", { n: u })); srcs.push(src("units")); }
    else if (lo) { out.push(tf(lg, "units_min", { n: lo })); srcs.push(ans && ans.units != null ? tf(lg, "src_you") : tf(lg, "src_use")); }
  }
  // one "(property records)" at the end when every fact has the same source, else one per fact
  if (new Set(srcs).size === 1) return out.length ? [out.join("; ") + ` (${srcs[0]})`] : [];
  return out.map((x, i) => `${x} (${srcs[i]})`);
}
function unknownFact(item, d, lg) {
  if (item.version_gap) return tf(lg, "f_version");
  const f = `${item.missing_fact || ""} ${(item.needs_fact || []).join(" ")}`;
  if (/certificate|year/i.test(f)) return tf(lg, d?.address?.year_built ? "f_yearonly" : "f_year");
  if (/unit/i.test(f)) return tf(lg, "f_units");
  if (/owner/i.test(f)) return tf(lg, "f_owner");
  if (/tenancy|moved/i.test(f)) return tf(lg, "f_tenancy");
  return tf(lg, "f_other");
}
function decideLine(c, item, d, lg) {
  const r = item.rule;
  let txt;
  if (item.result === "unknown") txt = tf(lg, "dec_unk", { f: unknownFact(item, d, lg) });
  else if (item.result === "not_yet_effective") txt = tf(lg, "dec_later", { d: fmt(r.effective_date_norm || r.effective_date) });
  else {
    const f = factsOf(item, d, lg);
    txt = f.length ? tf(lg, "dec_ok", { f: f.join("; ") }) : tf(lg, "dec_all", { p: placeOf(r.jurisdiction, lg) });
    const yielded = (c.enacted || []).filter((x) => x.result === "superseded" && (x.superseded_by || []).some((s) => s.id === r.team_rule_id));
    if (yielded.length) txt += " " + tf(lg, yielded.every((x) => x.rule.level === "state") ? "yields_s" : "yields_o");
  }
  return { icon: "code", html: esc(txt) };
}
// 4 Worded: who wrote the short answer
function wordLine(r, lg) {
  const w = DATA?.rules?.[r.team_rule_id]?.worded;
  if (r.plain_source === "generated") {
    if (w?.method === "template") return { icon: "code", html: esc(tf(lg, "word_tpl")) };
    return { icon: "ai", html: esc(tf(lg, r.plain_needs_review || w?.needs_review ? "word_flag" : "word_gen")) };
  }
  return { icon: "code", html: esc(tf(lg, "word_rev")) };
}
function flagLines(c, r, lg) {
  const out = [];
  if (r.confidence != null && r.confidence < 0.7) out.push({ icon: "flag", html: esc(tf(lg, "flag_low", { n: pct(r.confidence) })), warn: true });
  if (r.conflict_flag) {
    const note = String(r.conflict_note || "");
    if (/preempt|conflict|supersed|override/i.test(note)) {
      // name the other law when the note points at a rule of this topic, else its citation from the note
      const other = (c.enacted || []).map((x) => x.rule).find((o) => o.team_rule_id !== r.team_rule_id && (note.includes(o.team_rule_id) || (o.citation && note.includes(o.citation))));
      out.push({ icon: "flag", html: esc(other ? tf(lg, "flag_conf", { x: other.title_display || other.title }) : tf(lg, "flag_conf0")), warn: true });
    } else if (!(r.confidence != null && r.confidence < 0.7)) out.push({ icon: "flag", html: esc(tf(lg, "flag_data")), warn: true });
  }
  return out;
}

/** The trail for one topic: c = a category of /api/address or /api/evaluate, d = the whole response,
 *  top = the item app.js answers with (its ordered()[0]; without it, the first by result). */
function html(c, d, { top, lang } = {}) {
  const lg = L(lang);
  const item = top || topOf(c);
  let lines;
  if (item) {
    const r = item.rule;
    lines = [readLine(r, lg), checkLine(r, lg), decideLine(c, item, d, lg), wordLine(r, lg), ...flagLines(c, r, lg)];
  } else if (c.excluded?.length) {
    const ex = c.excluded, ans = answers(d), src = !d?.address?.address_id || (ans && Object.keys(ans).length) ? tf(lg, "src_you") : tf(lg, "src_rec");
    lines = [{ icon: "code", html: esc(ex.length > 1 ? tf(lg, "dec_exempt_n", { n: ex.length, s: src }) : tf(lg, "dec_exempt", { t: ex[0].citation || ex[0].title, s: src })) }, { icon: "code", html: esc(tf(lg, "word_tpl")) }];
  } else {
    const f = (c.no_rule_findings || [])[0];
    lines = [
      f ? { icon: "ai", html: esc(tf(lg, "read_f", { p: placeOf(f.jurisdiction, lg) }) + (f.confidence != null ? " " + tf(lg, "sure", { n: pct(f.confidence) }) : "")) } : null,
      f?.quoted_span ? checkLine({ ...f, source: f.source }, lg) : null,
      { icon: "code", html: esc(tf(lg, "dec_none")) },
      { icon: "code", html: esc(tf(lg, "word_tpl")) },
    ];
  }
  lines = lines.filter(Boolean);
  const key = `<span class="hm-key" aria-hidden="true">${ICON.ai}${esc(tf(lg, "k_ai"))}<span class="hm-dot">·</span>${ICON.code}${esc(tf(lg, "k_code"))}</span>`;
  return `<section class="hm" data-hm="${esc(c.id)}"><h5 class="hm-h"><span>${esc(tf(lg, "title"))}</span>${key}</h5>
    <ol class="hm-l">${lines.map((x) => `<li class="hm-${x.icon}${x.warn ? " is-warn" : ""}">${ICON[x.icon]}<span>${x.html}</span></li>`).join("")}</ol></section>`;
}

/** One line for an Ask citation (features/ask.js "Show me the law" card): c = one entry of res.citations. */
function askLine(c, lang) {
  const lg = L(lang), parts = [];
  parts.push(["ai", tf(lg, c.kind === "finding" ? "a_found_f" : "a_found")]);
  if (c.quoted_span) parts.push(c.verbatim ? ["code", tf(lg, "a_vb") + " ✓"] : ["flag", tf(lg, "a_novb")]);
  if (c.engine?.label) parts.push(["code", tf(lg, "a_eng", { r: String(c.engine.label).replace(/^\p{Lu}(?!\p{Lu})/u, (m) => m.toLowerCase()) })]);
  parts.push(["ai", tf(lg, "a_word")]);
  return `<p class="hm-ask">${parts.map(([i, s]) => `<span class="hm-${i}">${ICON[i]}${esc(s)}</span>`).join('<span class="hm-dot" aria-hidden="true">·</span>')}</p>`;
}

// "Log": the extraction entry from the audit log, the model's own words for this rule
async function openLog(id) {
  const lg = L();
  let x;
  try { const r = await fetch(`/api/howmade/${encodeURIComponent(id)}`); if (!r.ok) throw 0; x = await r.json(); } catch { CE().toast?.(tf(lg, "log_fail")); return; }
  const e = x.log_entry;
  if (!e) { CE().toast?.(tf(lg, "log_fail")); return; }
  const body = `<div class="hm-modal"><p class="rd-meta">${esc(tf(lg, "log_meta", { m: e.model || "", v: e.prompt_version || "", d: fmt(x.read?.at || e.ts), doc: e.doc_id || "" }))}</p>
    ${e.model_output ? `<h5>${esc(tf(lg, "log_out"))}</h5><pre class="hm-pre">${esc(JSON.stringify(e.model_output, null, 2))}</pre>` : ""}
    <p class="rd-meta"><a href="#/audit">${esc(tf(lg, "log_all"))}</a></p></div>`;
  CE().openModal?.(tf(lg, "log_t"), body);
}
if (typeof document !== "undefined" && document.addEventListener) {
  document.addEventListener("click", (ev) => {
    const b = ev.target?.closest?.("[data-hm-log]");
    if (!b) return;
    ev.preventDefault();
    openLog(b.dataset.hmLog);
  });
}

window.CEHowMade = Object.freeze({ html, askLine, load });
