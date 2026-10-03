// Clause & Effect · Rental Housing Law Navigator. Build-free single-page frontend.
// Views: #/ (home), #/a/<id> (address), #/changes, #/rules, #/audit. Design language: web/DESIGN.md

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const main = $("#main");
const RM = matchMedia("(prefers-reduced-motion: reduce)");

// ------------------------------------------------------------------ i18n --
const EN = {
  skip: "Skip to content", nla: "Not legal advice.", nla_more: "About this information", cancel: "Cancel",
  nla_body: "Information about public law, drawn from official sources and shown with citations. It is not a compliance check and not legal advice. For your situation, contact a tenant organisation, housing agency or attorney.",
  nla_title: "About this information",
  nav_lookup: "Lookup", nav_changes: "Changes", nav_rules: "Rules", nav_audit: "Sources",
  t_lookup: "Address lookup", t_changes: "What's changing", t_rules: "Rules", t_audit: "Sources and method",
  as_of: "As of", asof_aria: "Answers as of", asof_reset: "Back to {d}",
  footer_body: "Plain-language summaries of official texts retrieved Oct 1, 2026. They can be incomplete or wrong, so always check the cited source.",
  footer_meta: "Public data only. No customer, resident or pricing data.",
  hero_title: "Rental law, for your address.",
  hero_lead: "Rent limits, eviction rules, deposits, fees and screening, each quoted from the law. And what is about to change.",
  hero_meta: "California, New Jersey and Massachusetts · 10 cities",
  search_ph: "Street address, city or ZIP", search_go: "Look up", examples: "Examples",
  f1_t: "The mailing city is not always the legal city.", f1: "A Van Nuys address is in the City of Los Angeles. We ask the US Census which city each address is really in.", f1_l: "How addresses are resolved",
  f2_t: "Unknown, never a guess.", f2: "Building age, unit count and dates are checked in code. When the data can't tell, the answer says so.", f2_l: "Browse all rules",
  f3_t: "Every answer quotes the law.", f3: "Each rule links to the exact sentence in the official text, with the date it was retrieved.", f3_l: "Sources and method",
  r_applies: "Applies", r_unknown: "Unknown", r_superseded: "Yields", r_not_yet_effective: "Not yet in effect", r_pending: "Pending bill", r_failed: "Failed", r_in_force: "In force", r_no_rule: "No rule", r_exempt: "Exempt",
  how_resolved: "How we found this address", confidence: "Confidence", method: "Method",
  year_built: "Year built", units: "Units", use: "Use", not_in_data: "not in data", data_from: "Building data",
  built_y: "Built {y}", units_n: "{n} units", year_unknown: "Year built unknown", units_unknown: "Unit count unknown",
  mailing_legal: "Mailing city {p}, legally in {c}.", county: "County",
  rules_here: "Rules at this address", answers_note: "As of {d}. Not legal advice.",
  machine_tr: "Machine-translated. Legal text stays in English.",
  more_rules: "+{n} more", also_here: "Also at this address",
  needs: "Needs", needs_co: "The exact certificate-of-occupancy date. The data only has the year ({y}).",
  depends_on: "Depends on {f}", starts: "Starts {d}", changes_on: "Changes {d}", fig_from: "Figure shown applies from {d}",
  no_rule_short: "No state or city rule found.", exempt_line: "{t} exists, but this building is exempt.",
  exempt_body: "{t} ({c}) is in force here, but it does not cover this building:",
  sec_source: "Source", sec_why: "Why it applies", sec_why_unknown: "Why it's unknown", sec_why_not: "Why it doesn't apply", sec_changes: "Changes", sec_overrides: "Overrides", sec_review: "Open question",
  read_full: "Read in full text", low_conf: "Low extraction confidence ({n}%): check the source", quote_ok: "Quote found in source", quote_bad: "Quote not found in source", retrieved: "Retrieved {d}", secondary: "Secondary source",
  takes_precedence: "Takes precedence over {r}.", yields_to: "Yields to {r}, which governs here.",
  w_statewide: "Statewide rule: covers every rental in {s}.", w_city: "Covers rentals in {c}; no building-age or size conditions.",
  w_local_not_yet: "The stricter local rule is not in effect on this date, so this rule governs.",
  w_pending: "A bill, not law. It would cover this address if enacted.", w_failed: "The proposal failed or was withdrawn. It is not law.",
  ch_since: "In effect since {d}.", ch_starts: "Takes effect {d}.", ch_effective: "Effective {d}.",
  ch_version: "On {a}, an earlier version applied. The text and figure shown apply from {b}.",
  ch_figure_end: "The figure shown covers the period ending {d}. The law continues; check the current figure.",
  not_law: "Not law", not_law_note: "Pending bills and failed proposals. None of these is in force.",
  // changes
  changes_title: "What's changing", changes_lead: "Move the date to see which laws are in force. Pick a change to jump to it.",
  in_effect: "{n} in force", upcoming: "{n} upcoming", addresses_n: "{n} addresses", earlier: "{n} earlier rules, in force before 2024",
  in_force_on: "In force", not_yet: "Upcoming", timeline_aria: "Date",
  // rules
  rules_title: "Rules", rules_lead: "Every rule we track, by place and topic.", rules_n: "{n} rules",
  coverage: "Coverage by place and topic", none_level: "No rule", legend_nr: "Checked: no rule at this level",
  show_table: "All {n} rules", all: "All", only_conflicts: "Only open questions", category: "Topic", status: "Status", jurisdiction: "Place",
  col_rule: "Rule", col_quote: "Quote", col_addresses: "Addresses", key_value: "Key figure", effective: "Effective",
  no_rules_match: "No rules match these filters.", clear_filters: "Clear filters", conflict: "Open question",
  f_level: "Level", f_coverage: "Coverage", f_exemptions: "Exemptions", f_overrides: "Overrides / yields to", f_interaction: "Interaction", f_citation: "Citation", f_conflict_note: "Open question", sample_addresses: "Addresses covered",
  state: "State", city: "City", q_filter: "Filter",
  // audit
  audit_title: "Sources and method", audit_lead: "Where each answer comes from, and how it was checked.",
  k_docs: "source documents", k_quotes: "quotes found verbatim", k_geo: "addresses resolved", k_log: "extraction steps logged",
  method_t: "Method", p_ingest: "Collect", p_ingest_d: "{n} official documents, each with its URL and retrieval date.", p_extract: "Extract", p_extract_d: "A language model turns each text into rule records with exact quotes; every quote is then searched for verbatim in the source.", p_resolve: "Resolve", p_resolve_d: "The US Census geocoder finds each address's legal city.", p_apply: "Apply", p_apply_d: "Deterministic code checks every rule against each building's facts.", p_track: "Track", p_track_d: "Any date can be re-evaluated; changes are listed per address.",
  checks_t: "Change checks", checks_lead: "Scenarios re-run on every build: a date change, a city boundary, a pending bill, a failed proposal and a new ordinance.",
  before: "Before", after: "After", affected: "Affected addresses", rule_reach: "Where each rule applies", expected: "Expected", conflict_flags: "{n} with an open question", no_match_rule: "No matching rule",
  t_as_of: "Date change", t_boundary: "City boundary", t_pending: "Pending bill", t_negative: "Failed proposal", t_new: "New ordinance", t_new_law: "New ordinance",
  a_scale: "Adding a new city", a_files: "Output files and quote check", a_geo: "How addresses were resolved", a_docs: "All {n} source documents", a_log: "Extraction log",
  s1_t: "Add sources", s1: "Add the official text with its URL and date. No code changes.", s2_t: "Extract", s2: "Same prompts and schema; quotes checked; results cached by prompt hash.", s3_t: "Resolve", s3: "The Census covers every US address; a new city needs only its place name.", s4_t: "Re-run", s4: "Coverage and change tracking re-run in seconds for any date.",
  a_spans: "{a} of {b} quoted passages found in the source text", a_notfound: "{n} not found (flagged)", a_notext: "{n} sources have no stored text",
  col_address: "Address", col_mailing: "Mailing city", col_legal: "Legal city", col_method: "Method", col_doc: "Doc", col_source: "Source", col_type: "Type", col_rules: "Rules", col_text: "Text", l_text: "Text", l_link: "Link only", outside: "outside scope",
  log_showing: "Showing the newest {a} of {b} entries.", log_all: "Show all", log_none: "No log entries match “{q}”.",
  m_census_batch: "US Census batch geocoder", m_census_oneline: "US Census single-line geocoder", "m_osm_nominatim+census_coords": "OpenStreetMap + Census place",
  "m_osm_street_level+census_coords": "Street-level point + Census place", m_postal_city_fallback: "Postal city (fallback)",
  // misc
  toast_asof: "Answers as of {d}", toast_lang: "English", asof_range: "Pick a date between {a} and {b}.",
  g_examples: "Examples", g_results: "Addresses", g_pages: "Pages", no_match: "No matching address",
  nf_title: "We couldn't find that address", nf_page: "Page not found", nf_body: "Search for an address, or start from an example.", tagline_short: "Which rules apply here?",
  error: "Something went wrong loading this view.", loading: "Loading…", details: "Details",
  fixture: "Preview data: answers come from schema-identical fixture records.",
  cat_rent_increase_limits: "Rent increases", q_rent_increase_limits: "How much can the rent go up?",
  cat_just_cause_eviction: "Eviction protections", q_just_cause_eviction: "Does the landlord need a reason to end the tenancy?",
  cat_security_deposits: "Security deposit", q_security_deposits: "How large can the deposit be?",
  cat_application_screening_fees: "Application and move-in fees", q_application_screening_fees: "What can be charged to apply or move in?",
  cat_screening_restrictions: "Tenant screening", q_screening_restrictions: "What may a landlord ask about or consider?",
  cat_algorithmic_rent_setting: "Rent-setting software", q_algorithmic_rent_setting: "Can software be used to set the rent?",
  "Year built / certificate-of-occupancy date": "Year built or certificate-of-occupancy date", "Owner type": "Owner type", "Number of units": "Number of units",
  "Exemption filing / registration status": "Exemption filing or registration", "Length of tenancy": "Length of tenancy", "A fact not contained in the public data": "A fact the public data doesn't contain",
};
let ES = {};
let lang = localStorage.getItem("lang") || "en";
const t = (k) => (lang === "es" && ES[k]) || EN[k] || k;
const tf = (k, o) => Object.entries(o).reduce((s, [a, b]) => s.replaceAll("{" + a + "}", b), t(k));
const resLabel = (r) => t("r_" + r);
const fmtDate = (d) => {
  if (!d) return "";
  d = String(d).slice(0, 10);
  const s = d.length === 7 ? d + "-01" : d.length === 4 ? d + "-01-01" : d;
  const dt = new Date(s + "T12:00:00");
  if (isNaN(dt)) return d;
  const opts = d.length === 7 ? { month: "short", year: "numeric" } : d.length === 4 ? { year: "numeric" } : { month: "short", day: "numeric", year: "numeric" };
  return dt.toLocaleDateString(lang === "es" ? "es-US" : "en-US", opts);
};
const isoDates = (s) => String(s || "").replace(/\b(\d{4}-\d{2}-\d{2})\b/g, (m) => fmtDate(m));
const titleCase = (s) => String(s || "").toLowerCase().replace(/\b\w/g, (m) => m.toUpperCase());
const cap = (s) => String(s || "").replace(/^\s*\w/, (m) => m.toUpperCase());
const shortJ = (j) => String(j || "").replace(/, ..$/, "");
const STATE_NAMES = { CA: "California", NJ: "New Jersey", MA: "Massachusetts" };
const placeName = (r) => r.level === "state" ? t(STATE_NAMES[r.jurisdiction] || r.jurisdiction) : shortJ(r.jurisdiction);

// ------------------------------------------------------------------ state --
const DEFAULT_AS_OF = "2026-10-01";
let asOf = sessionStorage.getItem("asof") || DEFAULT_AS_OF;
let META = null;
let ADDR = [];
let cleanup = [];
const cache = new Map();
function api(path, { fresh = false } = {}) {
  if (!fresh && cache.has(path)) return cache.get(path);
  const p = fetch(path).then((r) => { if (!r.ok) throw new Error(r.status + " " + path); return r.json(); });
  cache.set(path, p);
  p.catch(() => cache.delete(path));
  return p;
}
const addrUrl = (id) => `/api/address/${id}?as_of=${asOf}&lang=${lang}`;

// ------------------------------------------------------------------ icons --
const svg = (p, extra = "") => `<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"${extra}>${p}</svg>`;
const I = {
  search: svg('<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>'),
  info: svg('<circle cx="12" cy="12" r="9.5"/><path d="M12 11v6M12 7.5v.01"/>'),
  alert: svg('<path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17.5v.01"/>'),
  check: svg('<path d="m5 12 4.5 4.5L19 7"/>'),
  chev: svg('<path d="m9 6 6 6-6 6"/>'),
  left: svg('<path d="m15 6-6 6 6 6"/>'),
  arrow: svg('<path d="M5 12h14M13 6l6 6-6 6"/>'),
  back: svg('<path d="M19 12H5M11 6l-6 6 6 6"/>'),
  ext: svg('<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>', ' style="width:12px;height:12px"'),
  layers: svg('<path d="m12 3 9 5-9 5-9-5z"/><path d="m3 13 9 5 9-5"/>'),
  q: svg('<circle cx="12" cy="12" r="9.5"/><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1 .9-1 1.7M12 17v.01"/>'),
  pin: svg('<path d="M12 21s7-6.1 7-11.5A7 7 0 0 0 5 9.5C5 14.9 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>'),
  cal: svg('<rect x="4" y="5" width="16" height="15" rx="3"/><path d="M8 3v4M16 3v4M4 10h16"/>'),
  doc: svg('<path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5M10 13h6M10 17h6"/>'),
  building: svg('<path d="M4 21V5l8-2v18M12 8l8 2v11M8 8v.01M8 12v.01M8 16v.01M16 13v.01M16 17v.01M2 21h20"/>'),
  globe: svg('<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18"/>'),
  pause: svg('<path d="M9 6v12M15 6v12"/>'),
  play: svg('<path d="M8 5v14l11-7z"/>'),
  cat: {
    rent_increase_limits: svg('<path d="M3 17l6-6 4 4 8-8"/><path d="M14 7h7v7"/>'),
    just_cause_eviction: svg('<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="m9 12 2 2 4-4"/>'),
    security_deposits: svg('<rect x="3" y="6" width="18" height="13" rx="2"/><path d="M3 10h18M16 15h2"/>'),
    application_screening_fees: svg('<path d="M6 3h12v18l-3-2-3 2-3-2-3 2z"/><path d="M9 8h6M9 12h6"/>'),
    screening_restrictions: svg('<circle cx="10" cy="8" r="4"/><path d="M3 20c.8-3.7 3.6-6 7-6"/><circle cx="17" cy="16" r="3"/><path d="m21 20-1.8-1.8"/>'),
    algorithmic_rent_setting: svg('<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>'),
  },
};
const host = (u) => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return u || ""; } };
// Status mark: the word, in the status colour. Used everywhere a result is shown (and by feature modules via CE.badge).
const badge = (r, cls = "", _i = null, label = null) => `<span class="badge st-${esc(r)} ${cls}">${esc(label ?? resLabel(r))}</span>`;
const pctOf = (c) => Math.round(c * 100);

// ------------------------------------------------------------------ small helpers --
function swap(html, after) {
  main.innerHTML = html; after?.();
  if (!RM.matches) { main.classList.remove("fade-in"); void main.offsetWidth; main.classList.add("fade-in"); }
  return Promise.resolve();
}
const prog = $("#progress");
function progress(on) {
  if (on) { prog.className = "progress"; void prog.offsetWidth; prog.className = "progress run"; }
  else if (prog.classList.contains("run")) { prog.className = "progress done"; }
}
function toast(msg) {
  let el = $("#toasts .ce-toast:not(.out)");
  if (el) { el.textContent = msg; clearTimeout(el._t); }
  else { el = document.createElement("div"); el.className = "toast ce-toast"; el.setAttribute("role", "status"); el.textContent = msg; $("#toasts").append(el); }
  el._t = setTimeout(() => { el.classList.add("out"); setTimeout(() => el.remove(), 250); }, 2400);
}

// ------------------------------------------------------------------ header --
function syncHeader(route) {
  $$(".tabs a").forEach((a) => { if (a.dataset.route === route) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
  $("#asof").value = asOf;
  const changed = asOf !== DEFAULT_AS_OF;
  $("#asof-label").textContent = (innerWidth > 640 ? t("as_of") + " " : "") + fmtDate(asOf);
  $("#asof-ctl").classList.toggle("changed", changed);
  $("#asof").setAttribute("aria-label", t("asof_aria"));
  const rs = $("#asof-reset");
  rs.hidden = !changed;
  rs.textContent = "×";
  rs.setAttribute("aria-label", tf("asof_reset", { d: fmtDate(DEFAULT_AS_OF) }));
  rs.title = tf("asof_reset", { d: fmtDate(DEFAULT_AS_OF) });
  $$(".seg button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.lang === lang));
  document.documentElement.lang = lang;
  $$("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  $("#cmdk input").placeholder = t("search_ph");
  $(".search-trigger").setAttribute("aria-label", t("search_ph"));
  const fb = $("#fixture-banner");
  fb.hidden = META?.sources?.["rules.json"]?.kind !== "fixture";
  fb.textContent = t("fixture");
}
addEventListener("resize", () => { $("#asof-label").textContent = (innerWidth > 640 ? t("as_of") + " " : "") + fmtDate(asOf); }, { passive: true });
const ASOF_MIN = "2020-01-01", ASOF_MAX = "2030-12-31";
function setAsOf(v, { silent = false } = {}) {
  if (!v || v === asOf) return;
  if (v < ASOF_MIN || v > ASOF_MAX) { $("#asof").value = asOf; toast(tf("asof_range", { a: fmtDate(ASOF_MIN), b: fmtDate(ASOF_MAX) })); return; }
  asOf = v; sessionStorage.setItem("asof", asOf);
  if (!silent) { toast(tf("toast_asof", { d: fmtDate(asOf) })); route({ keepScroll: true, soft: true }); }
  else syncHeader(currentView());
  document.dispatchEvent(new CustomEvent("ce:asof", { detail: { asOf } }));
}
$("#asof").addEventListener("change", (e) => { if (!e.target.value) { e.target.value = asOf; return; } setAsOf(e.target.value); });
$("#asof").addEventListener("blur", (e) => { if (!e.target.value) e.target.value = asOf; });
$("#asof").addEventListener("click", (e) => { try { e.target.showPicker?.(); } catch { /* not allowed: the native control opens anyway */ } });
$("#asof-reset").addEventListener("click", () => { $("#asof").value = DEFAULT_AS_OF; setAsOf(DEFAULT_AS_OF); });
$$(".seg button").forEach((b) => b.addEventListener("click", async () => {
  if (lang === b.dataset.lang) return;
  lang = b.dataset.lang; localStorage.setItem("lang", lang);
  if (lang === "es" && !Object.keys(ES).length) ES = await api("/api/i18n/es").catch(() => ({}));
  toast(t("toast_lang")); route({ keepScroll: true, soft: true });
  document.dispatchEvent(new CustomEvent("ce:lang", { detail: { lang } }));
}));
document.addEventListener("click", (e) => { if (e.target.closest("[data-nla-open]")) openNla(); });
function openNla() {
  openModal(t("nla_title"), `<p class="lead-p"><strong>${t("nla")}</strong> ${esc(t("nla_body"))}</p><p class="muted">${esc(t("footer_body"))}</p>`);
}
const currentView = () => { const v = location.hash.replace(/^#\/?/, "").split("/")[0]; return v === "a" || !v ? "lookup" : v; };

// ------------------------------------------------------------------ search --
function scoreAddr(a, q) {
  const s = `${a.id} ${a.street} ${a.postal_city} ${a.city} ${a.state} ${a.zip}`.toLowerCase();
  let score = 0;
  for (const term of q.toLowerCase().split(/\s+/).filter(Boolean)) {
    const i = s.indexOf(term);
    if (i < 0) return -1;
    score += i === 0 ? 3 : s[i - 1] === " " ? 2 : 1;
  }
  return score;
}
const findAddr = (q, n = 8) => ADDR.map((a) => [scoreAddr(a, q), a]).filter((x) => x[0] >= 0).sort((a, b) => b[0] - a[0]).slice(0, n).map((x) => x[1]);
function hl(text, q) {
  let out = esc(text);
  for (const term of q.split(/\s+/).filter((x) => x.length > 1)) out = out.replace(new RegExp("(" + term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "ig"), "<mark>$1</mark>");
  return out;
}
const optHtml = (a, i, sel, q = "") => `<li class="opt" role="option" id="o-${i}" aria-selected="${i === sel}" data-id="${a.id}">
  <div><div class="addr">${hl(titleCase(a.street), q)}</div><div class="sub">${hl(a.postal_city, q)}${a.city && a.city !== a.postal_city ? ` · ${hl(a.city, q)}` : ""}, ${a.state} ${esc(a.zip)}</div></div>
  <span class="arrow">${I.chev}</span></li>`;
const go = (id) => { location.hash = "#/a/" + id; };

// search sheet (⌘K or /)
const cmdk = $("#cmdk"), cIn = $("#cmdk input"), cList = $("#cmdk-list");
let cItems = [], cSel = 0;
function cmdkRender() {
  const q = cIn.value.trim();
  const pages = [["#/", "t_lookup"], ["#/changes", "t_changes"], ["#/rules", "t_rules"], ["#/audit", "t_audit"]];
  cItems = q ? findAddr(q, 9).map((a) => ({ id: a.id, a })) : examplePicks().slice(0, 4).map((a) => ({ id: a.id, a }));
  const pg = q ? [] : pages.map(([h, k]) => ({ href: h, label: t(k) }));
  cItems = cItems.concat(pg);
  cSel = 0;
  let html = cItems.length ? `<li class="grp" role="presentation">${q ? t("g_results") : t("g_examples")}</li>` : `<li class="grp">${t("no_match")}</li>`;
  html += cItems.map((it, i) => it.a ? optHtml(it.a, i, cSel, q) : `${i === cItems.length - pg.length ? `<li class="grp" role="presentation">${t("g_pages")}</li>` : ""}<li class="opt" role="option" id="o-${i}" aria-selected="${i === cSel}" data-href="${it.href}"><div class="addr">${esc(it.label)}</div><span class="arrow">${I.chev}</span></li>`).join("");
  cList.innerHTML = html;
}
function cmdkMove(d) {
  if (!cItems.length) return;
  cSel = (cSel + d + cItems.length) % cItems.length;
  $$(".opt", cList).forEach((li, i) => li.setAttribute("aria-selected", i === cSel));
  $(`#o-${cSel}`, cList)?.scrollIntoView({ block: "nearest" });
  cIn.setAttribute("aria-activedescendant", "o-" + cSel);
}
function cmdkPick(i) { const it = cItems[i]; if (!it) return; closeCmdk(); if (it.a) go(it.id); else location.hash = it.href; }
function openCmdk() { if (cmdk.hidden) lastFocus = document.activeElement; cmdk.hidden = false; cmdk.classList.remove("closing"); lockScroll(true); cIn.value = ""; cmdkRender(); setTimeout(() => cIn.focus(), 10); }
function closeCmdk() { if (cmdk.hidden) return; closeLayer(cmdk); }
let lastFocus = null;
function trapFocus(e) {
  const layer = [$("#cmdk"), $("#modal")].find((l) => !l.hidden);
  if (!layer || e.key !== "Tab") return;
  const f = $$('a[href], button:not([disabled]), input, select, textarea, summary, [tabindex]:not([tabindex="-1"])', layer).filter((x) => x.offsetParent !== null);
  if (!f.length) return;
  const first = f[0], last = f[f.length - 1];
  if (!layer.contains(document.activeElement)) { e.preventDefault(); first.focus(); }
  else if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
}
document.addEventListener("keydown", trapFocus);
function lockScroll(on) { document.documentElement.classList.toggle("locked", on); }
function closeLayer(el) {
  const back = lastFocus; lastFocus = null;
  if (back && document.contains(back)) setTimeout(() => back.focus({ preventScroll: true }), 0);
  const done = () => { el.hidden = true; el.classList.remove("closing"); if ($("#cmdk").hidden && $("#modal").hidden) lockScroll(false); };
  if (RM.matches) { done(); return; }
  el.classList.add("closing");
  clearTimeout(el._closeT); el._closeT = setTimeout(done, 160);
}
cIn.addEventListener("input", cmdkRender);
cIn.addEventListener("keydown", (e) => {
  if (e.key === "ArrowDown") { e.preventDefault(); cmdkMove(1); }
  else if (e.key === "ArrowUp") { e.preventDefault(); cmdkMove(-1); }
  else if (e.key === "Enter") { e.preventDefault(); cmdkPick(cSel); }
});
cList.addEventListener("click", (e) => { const li = e.target.closest(".opt"); if (li) cmdkPick($$(".opt", cList).indexOf(li)); });
cList.addEventListener("mousemove", (e) => { const li = e.target.closest(".opt"); if (li) { const i = $$(".opt", cList).indexOf(li); if (i !== cSel) { cSel = i; $$(".opt", cList).forEach((x, k) => x.setAttribute("aria-selected", k === cSel)); } } });
cmdk.addEventListener("click", (e) => { if (e.target === cmdk || e.target.closest("[data-cmdk-close]")) closeCmdk(); });
document.addEventListener("click", (e) => { if (e.target.closest("[data-cmdk]")) openCmdk(); });
document.addEventListener("keydown", (e) => {
  const ae = document.activeElement;
  const typing = ae && (ae.tagName === "TEXTAREA" || ae.tagName === "SELECT" || ae.isContentEditable || (ae.tagName === "INPUT" && !["range", "checkbox", "radio", "button"].includes(ae.type)));
  if ((e.key === "k" && (e.metaKey || e.ctrlKey)) || (e.key === "/" && !typing)) { e.preventDefault(); openCmdk(); }
  else if (e.key === "Escape") { closeCmdk(); closeModal(); }
});

// ------------------------------------------------------------------ home --
function examplePicks() {
  const pick = (f) => ADDR.find(f);
  const yr = (a) => parseInt(a.year_built || "0", 10);
  return [
    pick((a) => a.city === "Los Angeles" && yr(a) && yr(a) < 1978 && a.postal_city !== a.city) || pick((a) => a.city === "Los Angeles" && yr(a) && yr(a) < 1978),
    pick((a) => a.city === "San Francisco" && yr(a) && yr(a) < 1979 && +a.units >= 10),
    pick((a) => a.postal_city === "Dorchester"),
    pick((a) => a.city === "Hoboken"),
    pick((a) => a.city === "Jersey City"),
    pick((a) => a.city === "Cambridge"),
    pick((a) => a.city === "Berkeley"),
    pick((a) => a.city === "San Diego"),
    pick((a) => a.city === "Newark"),
  ].filter(Boolean);
}
function viewHome() {
  const ex = examplePicks().slice(0, 4);
  const row = (a) => `<li><a href="#/a/${a.id}"><span class="ex-a">${esc(titleCase(a.street))}</span><span class="ex-c">${esc(a.postal_city)}${a.city && a.city !== a.postal_city ? ` · ${esc(a.city)}` : ""}, ${esc(a.state)}</span>${I.chev}</a></li>`;
  const html = `
  <section class="hero">
    <h1>${esc(t("hero_title"))}</h1>
    <p class="lead">${esc(t("hero_lead"))}</p>
    <form class="big-search" role="search" autocomplete="off" data-tour="search">
      <div class="box">
        ${I.search}
        <input id="hq" type="text" role="combobox" aria-expanded="false" aria-controls="hs" aria-autocomplete="list" spellcheck="false" placeholder="${esc(t("search_ph"))}" aria-label="${esc(t("search_ph"))}">
        <button class="go" type="submit">${esc(t("search_go"))}</button>
      </div>
      <ul class="suggest" id="hs" role="listbox" hidden></ul>
    </form>
    <p class="hero-meta">${esc(t("hero_meta"))}</p>
    <div class="ex-block">
      <h2 class="list-h">${esc(t("examples"))}</h2>
      <ul class="chips group">${ex.map(row).join("")}</ul>
      <div class="tour-slot" data-tour-slot="home"></div>
    </div>
  </section>
  <section class="features">
    <div><h2>${esc(t("f1_t"))}</h2><p>${esc(t("f1"))}</p><a href="#/audit">${esc(t("f1_l"))}</a></div>
    <div><h2>${esc(t("f2_t"))}</h2><p>${esc(t("f2"))}</p><a href="#/rules">${esc(t("f2_l"))}</a></div>
    <div><h2>${esc(t("f3_t"))}</h2><p>${esc(t("f3"))}</p><a href="#/audit">${esc(t("f3_l"))}</a></div>
  </section>`;
  return swap(html, () => initHome(ex));
}
function initHome(ex) {
  const form = $(".big-search"), input = $("#hq"), list = $("#hs");
  let items = [], sel = 0;
  const close = () => { list.hidden = true; input.setAttribute("aria-expanded", "false"); };
  const render = () => {
    const q = input.value.trim();
    if (!q) { close(); return; }
    items = findAddr(q, 6); sel = 0;
    list.innerHTML = items.length ? items.map((a, i) => optHtml(a, i, sel, q)).join("") : `<li class="opt empty" aria-disabled="true"><span class="sub">${esc(t("no_match"))}</span></li>`;
    list.hidden = false; input.setAttribute("aria-expanded", "true");
  };
  input.addEventListener("input", render);
  input.addEventListener("focus", render);
  input.addEventListener("blur", () => setTimeout(close, 120));
  input.addEventListener("keydown", (e) => {
    if (list.hidden || !items.length) return;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault(); sel = (sel + (e.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
      $$(".opt", list).forEach((li, i) => li.setAttribute("aria-selected", i === sel));
      input.setAttribute("aria-activedescendant", "o-" + sel);
    } else if (e.key === "Escape") close();
  });
  list.addEventListener("mousedown", (e) => { const li = e.target.closest("[data-id]"); if (li) { e.preventDefault(); go(li.dataset.id); } });
  list.addEventListener("mousemove", (e) => { const li = e.target.closest("[data-id]"); if (!li) return; const i = $$(".opt", list).indexOf(li); if (i !== sel) { sel = i; $$(".opt", list).forEach((x, k) => x.setAttribute("aria-selected", k === sel)); input.setAttribute("aria-activedescendant", "o-" + sel); } });
  form.addEventListener("submit", (e) => { e.preventDefault(); const q = input.value.trim(); if (!q) return input.focus(); if (items[sel]) go(items[sel].id); });
  ex.forEach((a) => api(addrUrl(a.id)).catch(() => {})); // warm the cache for the examples
}

// ------------------------------------------------------------------ answers (address page, My properties, any-address) --
// Order inside a topic: the governing rule first. A rule that takes precedence over another comes first, then
// statewide rules (a city rule that does not override them usually adds to them), then the rest.
const RANK = { applies: 0, unknown: 1, not_yet_effective: 2, superseded: 3, pending: 4, failed: 5 };
const ordered = (items) => [...items].sort((x, y) => (RANK[x.result] ?? 9) - (RANK[y.result] ?? 9)
  || (y.overrides_here?.length ? 1 : 0) - (x.overrides_here?.length ? 1 : 0)
  || (x.rule.level === "state" ? 0 : 1) - (y.rule.level === "state" ? 0 : 1));

// The engine's explanation is one English sentence chain. Split it into facts, changes and notes so that each
// piece is shown once, in its own section, and the key figure (already in the answer line) is not repeated.
function parseWhy(item) {
  const r = item.rule;
  const out = { facts: [], changes: [], notes: [], rest: "", version: null, figureEnd: null };
  let s = String(item.explanation_en || item.explanation || "").trim();
  let m;
  if ((m = s.match(/\s*Note:\s*([\s\S]+)$/))) {
    s = s.slice(0, m.index);
    m[1].split(/\s+(?=possible conflict|state law |open question:)/).forEach((n) => {
      const x = n.replace(/^open question:\s*/i, "").replace(/\s*-\s*flagged for human review\.?$/i, "").trim();
      if (x) out.notes.push(cap(x));
    });
  }
  if ((m = s.match(/\s*The figure above covers the period ending ([\d-]+);[\s\S]*$/))) { s = s.slice(0, m.index); out.figureEnd = m[1]; }
  if ((m = s.match(/\s*Earlier version in force on ([\d-]+)(?: \(since [^)]+\))?; current version\/figure from ([\d-]+)\.\s*([\s\S]*)$/))) {
    s = s.slice(0, m.index); out.version = { on: m[1], from: m[2], note: m[3].trim() };
  }
  if ((m = s.match(/^In effect since ([\d-]+)\.\s*/))) { s = s.slice(m[0].length); out.changes.push(tf("ch_since", { d: fmtDate(m[1]) })); }
  if ((m = s.match(/^Enacted, but takes effect on [\d-]+ \(after [\d-]+\)\.\s*/))) s = s.slice(m[0].length);
  if ((m = s.match(/^The stricter local rule is not in effect on [\d-]+, so this rule governs\.\s*/))) { s = s.slice(m[0].length); out.facts.push(t("w_local_not_yet")); }
  if (r.key_value) s = s.replace(` Rule: ${r.key_value}.`, "");
  s = s.replace(/\s*Rule: [\s\S]*?\.(?=\s+This state law|\s*$)/, "");
  if ((m = s.match(/^[\s\S]+? (?:applies|may apply) in (.+?)(?: \(([A-Z]{2}) statewide rule\))?(?::\s*([\s\S]+?))?\.(\s[\s\S]*)?$/))) {
    if (m[3]) out.facts.push(...m[3].split(/;\s+/).map((x) => cap(isoDates(x.replace(/^coverage depends on facts not in the data:\s*/i, "")))));
    else if (m[2]) out.facts.push(tf("w_statewide", { s: t(STATE_NAMES[m[2]] || m[2]) }));
    else out.facts.push(tf("w_city", { c: shortJ(m[1]) }));
    if (m[4]?.trim()) out.facts.push(m[4].trim());
  } else if (/would cover this address, but|covers this address unless local/.test(s)) {
    if (/covers this address unless local/.test(s)) out.facts.push(s);
  } else if (/is a pending bill, not law/.test(s)) out.facts.push(t("w_pending"));
  else if ((m = s.match(/is enacted but takes effect .+?; it will cover this address in [^.]+\.(?:\s*Coverage then depends on facts not in the data:\s*([\s\S]+))?/))) {
    if (m[1]) out.facts.push(...m[1].replace(/\.$/, "").split(/;\s+/).map((x) => cap(isoDates(x))));
  } else if (/^Proposal failed/.test(s)) out.facts.push(t("w_failed"));
  else if (s) out.rest = s;
  // Spanish: show the translated explanation when one exists (the parsed English pieces would mix languages).
  if (lang !== "en" && item.explanation && item.explanation_en && item.explanation !== item.explanation_en) {
    const kv = r.key_value_display || "";
    out.facts = []; out.rest = item.explanation.replace(kv ? new RegExp(`\\s*Regla:\\s*${kv.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\.?`) : /$^/, "");
  }
  return out;
}
const missingLabel = (item, d) => {
  const f = item.missing_fact || "";
  const y = d?.address?.year_built;
  if (/certificate|year built/i.test(f) && y) return tf("needs_co", { y });
  return t(f || "A fact not contained in the public data");
};
function sourceHtml(src) {
  // src: {quote, citation, url, retrieved, doc, rule, check, confidence, id, secondary}
  const chk = src.check?.status;
  const verified = chk === "exact" || chk === "normalized" ? `<span class="ok">${I.check}${t("quote_ok")}</span>` : chk === "not_found" ? `<span class="warn">${I.alert}${t("quote_bad")}</span>` : "";
  const meta = [verified, src.retrieved ? esc(tf("retrieved", { d: fmtDate(src.retrieved) })) : "", src.confidence != null && src.confidence < 0.7 ? `<span class="warn">${esc(tf("low_conf", { n: pctOf(src.confidence) }))}</span>` : "", src.secondary ? esc(t("secondary")) : ""].filter(Boolean);
  return `<section class="rd-sec" data-tour="source"><h5>${t("sec_source")}</h5>
    ${src.quote ? `<blockquote class="quote">${esc(src.quote)}</blockquote>` : ""}
    <p class="rd-cite">${src.citation ? `<span>${esc(src.citation)}</span>` : ""}${src.url ? `<a href="${esc(src.url)}" target="_blank" rel="noopener">${esc(host(src.url))}${I.ext}</a>` : ""}${src.doc ? `<a href="#" data-doc="${esc(src.doc)}" data-rule="${esc(src.rule || "")}">${t("read_full")}</a>` : ""}</p>
    ${meta.length ? `<p class="rd-meta">${meta.join("<span class=\"sep\" aria-hidden=\"true\">·</span>")}</p>` : ""}
  </section>`;
}
const ruleSource = (r) => ({ quote: r.quoted_span, citation: r.citation, url: r.source_url, retrieved: r.source?.retrieved_at || r.retrieved_at, doc: r.source?.has_text ? (r.span_doc_id || r.quoted_span_doc_id || r.source_doc_id) : null, rule: r.team_rule_id, check: r.quote_check, confidence: r.confidence, id: r.team_rule_id, secondary: r.source?.secondary });
function ruleDetail(item, d, { withTitle = true, needs = true } = {}) {
  const r = item.rule, res = item.result, w = parseWhy(item);
  const list = (xs) => xs.length > 1 ? `<ul>${xs.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : `<p>${esc(xs[0])}</p>`;
  const changes = [...w.changes];
  if (res === "not_yet_effective" || res === "pending") { /* the status line says it */ }
  if (res === "not_yet_effective" && r.effective_date) changes.push(tf("ch_starts", { d: fmtDate(r.effective_date_norm || r.effective_date) }));
  if (w.version && asOf < w.version.from) changes.push(tf("ch_version", { a: fmtDate(asOf), b: fmtDate(w.version.from) }) + (w.version.note ? " " + w.version.note : ""));
  if (w.figureEnd) changes.push(tf("ch_figure_end", { d: fmtDate(w.figureEnd) }));
  if (!changes.length && r.effective_date && res === "applies" && !w.changes.length && /^\d{4}-\d{2}/.test(r.effective_date_norm || "") && (r.effective_date_norm || "") > "2023-12-31") changes.push(tf("ch_effective", { d: fmtDate(r.effective_date_norm) }));
  const over = [];
  if (item.overrides_here?.length) over.push(tf("takes_precedence", { r: item.overrides_here.map((x) => x.title).join(", ") }));
  if (res === "superseded" && item.superseded_by?.length) over.push(tf("yields_to", { r: item.superseded_by.map((x) => x.title).join(", ") }));
  const whyHead = res === "unknown" ? "sec_why_unknown" : "sec_why";
  return `<div class="rd">
    ${withTitle ? `<h4 class="rd-title">${esc(r.title_display || r.title)}</h4>` : ""}
    <p class="rd-plain">${esc(r.requirement_display || r.requirement || "")}</p>
    ${res === "unknown" && needs ? `<p class="rd-needs"><b>${t("needs")}:</b> ${esc(missingLabel(item, d))}</p>` : ""}
    ${sourceHtml(ruleSource(r))}
    ${w.facts.length || w.rest ? `<section class="rd-sec"><h5>${t(whyHead)}</h5>${w.facts.length ? list(w.facts) : `<p>${esc(isoDates(w.rest))}</p>`}</section>` : ""}
    ${changes.length ? `<section class="rd-sec"><h5>${t("sec_changes")}</h5>${list(changes)}</section>` : ""}
    ${over.length ? `<section class="rd-sec"><h5>${t("sec_overrides")}</h5>${list(over)}</section>` : ""}
    ${item.conflict_flag && (w.notes.length || r.conflict_note) ? `<section class="rd-sec"><h5>${t("sec_review")}</h5>${list(w.notes.length ? w.notes.map(isoDates) : [r.conflict_note_display || r.conflict_note])}</section>` : ""}
  </div>`;
}
// One line that answers the topic's question for this address.
function topicSummary(c, d) {
  const items = ordered(c.enacted || []);
  const top = items[0];
  if (top) {
    const r = top.rule, w = parseWhy(top);
    let line, status = top.result, next = "";
    if (top.result === "unknown") line = tf("depends_on", { f: missingLabel(top, d).replace(/\.$/, "").replace(/^\w/, (m) => m.toLowerCase()) });
    else line = r.key_value_display || r.key_value || r.title_display || r.title;
    if (top.result === "not_yet_effective") next = tf("starts", { d: fmtDate(r.effective_date_norm || r.effective_date) });
    else if (w.version && asOf < w.version.from) next = tf("fig_from", { d: fmtDate(w.version.from) });
    else {
      const soon = items.find((x) => x !== top && x.result === "not_yet_effective");
      if (soon) next = tf("changes_on", { d: fmtDate(soon.rule.effective_date_norm || soon.rule.effective_date) });
    }
    return { line: cap(line), where: placeName(r), status, next, extra: items.length - 1 };
  }
  const ex = c.excluded?.[0];
  if (ex) return { line: tf("exempt_line", { t: ex.title }), where: "", status: "exempt", next: "", extra: 0 };
  const f = c.no_rule_findings?.[0];
  const first = (s) => (String(s || "").match(/^.{20,}?[.!?](?=\s|$)/) || [s])[0];
  return { line: f ? first(f.finding_display || f.finding) : t("no_rule_short"), where: f ? (STATE_NAMES[f.jurisdiction] ? t(STATE_NAMES[f.jurisdiction]) : shortJ(f.jurisdiction)) : "", status: "no_rule", next: "", extra: 0 };
}
function subRule(item, d) {
  const r = item.rule;
  return `<details class="subrule"><summary data-tour="rule" data-rule="${esc(r.team_rule_id)}"><span class="sub-main"><span class="sub-t">${esc(r.title_display || r.title)}</span><span class="sub-a">${esc(r.key_value_display || r.key_value || "")}${r.key_value ? " · " : ""}${esc(placeName(r))}</span></span>${badge(item.result)}<span class="chev">${I.chev}</span></summary>
    ${ruleDetail(item, d, { withTitle: false })}</details>`;
}
// Feature modules (compare, check, tour) may append quiet links into these slots; see web/DESIGN.md.
const slot = (c) => `<div class="topic-actions" data-slot="topic-actions" data-cat="${c.id}"></div>`;
function topicBody(c, d) {
  const items = ordered(c.enacted || []);
  if (items.length) {
    const [top, ...rest] = items;
    return ruleDetail(top, d, { needs: false }) + (rest.length ? `<div class="also"><h5>${t("also_here")}</h5>${rest.map((x) => subRule(x, d)).join("")}</div>` : "") + slot(c);
  }
  let html = "";
  for (const ex of c.excluded || []) {
    html += `<div class="rd"><p class="rd-plain">${esc(tf("exempt_body", { t: ex.title, c: ex.citation || ex.id }))}</p>
      <section class="rd-sec"><h5>${t("sec_why_not")}</h5>${ex.reasons.length > 1 ? `<ul>${ex.reasons.map((x) => `<li>${esc(cap(isoDates(x)))}</li>`).join("")}</ul>` : `<p>${esc(cap(isoDates(ex.reasons[0] || "")))}</p>`}</section></div>`;
  }
  for (const f of c.no_rule_findings || []) {
    html += `<div class="rd"><p class="rd-plain">${esc(f.finding_display || f.finding)}</p>
      ${f.quoted_span || f.citation ? sourceHtml({ quote: f.quoted_span, citation: f.citation, url: f.source_url, retrieved: f.source?.retrieved_at, doc: f.source?.has_text ? (f.quoted_span_doc_id || f.source_doc_id) : null, check: f.quote_check, confidence: f.confidence, id: f.finding_id }) : ""}</div>`;
  }
  return (html || `<div class="rd"><p class="rd-plain">${esc(t("no_rule_short"))}</p></div>`) + slot(c);
}
function topicRow(c, d) {
  const s = topicSummary(c, d);
  const top = ordered(c.enacted || [])[0];
  return `<details class="topic" id="t-${c.id}" data-cat="${c.id}" data-tour="answer">
    <summary${top ? ` data-tour="rule" data-rule="${esc(top.rule.team_rule_id)}"` : ""}>
      <span class="topic-main">
        <span class="topic-q">${esc(t("cat_" + c.id))}</span>
        <span class="topic-a">${esc(s.line)}${s.where ? `<span class="topic-w"> · ${esc(s.where)}</span>` : ""}</span>
        ${s.next || s.extra ? `<span class="topic-x">${s.next ? `<span class="soon">${esc(s.next)}</span>` : ""}${s.extra ? `<span>${esc(tf("more_rules", { n: s.extra }))}</span>` : ""}</span>` : ""}
      </span>
      ${badge(s.status)}
      <span class="chev">${I.chev}</span>
    </summary>
    <div class="topic-body">${topicBody(c, d)}</div>
  </details>`;
}
function answersHTML(d) {
  const proposals = d.categories.flatMap((c) => [...(c.pending || []), ...(c.not_law || [])]);
  return `
    <div class="answers-head">
      <h2>${t("rules_here")}</h2>
      <p class="note">${esc(tf("answers_note", { d: fmtDate(d.as_of) }))}${lang !== "en" ? ` ${esc(t("machine_tr"))}` : ""}</p>
    </div>
    <div class="topics group">${d.categories.map((c) => topicRow(c, d)).join("")}</div>
    ${proposals.length ? `<div class="answers-head sub-head"><h2>${t("not_law")}</h2><p class="note">${t("not_law_note")}</p></div>
      <div class="topics group">${proposals.map((it) => `<details class="topic"><summary><span class="topic-main"><span class="topic-q">${esc(it.rule.title_display || it.rule.title)}</span><span class="topic-a">${esc(t("cat_" + it.rule.category))} · ${esc(placeName(it.rule))}</span></span>${badge(it.result)}<span class="chev">${I.chev}</span></summary><div class="topic-body">${ruleDetail(it, d, { withTitle: false })}</div></details>`).join("")}</div>` : ""}`;
}

// ------------------------------------------------------------------ address --
function addressSkeleton() {
  const line = (w, h = 14, m = 10) => `<div class="sk" style="width:${w};height:${h}px;margin-top:${m}px"></div>`;
  return `<div class="addr">${line("60%", 36, 0)}${line("40%", 16, 12)}${line("50%", 14, 8)}${line("100%", 360, 40)}</div>`;
}
function viewNotFound(kind) {
  const ex = examplePicks().slice(0, 3);
  document.title = `${t("nf_title")} · Clause & Effect`;
  return swap(`<section class="notfound"><h1>${esc(t(kind === "address" ? "nf_title" : "nf_page"))}</h1><p>${esc(t("nf_body"))}</p>
    <button class="btn primary" type="button" data-cmdk>${esc(t("search_ph"))}</button>
    <ul class="group chips">${ex.map((a) => `<li><a href="#/a/${a.id}"><span class="ex-a">${esc(titleCase(a.street))}</span><span class="ex-c">${esc(a.city || a.postal_city)}</span>${I.chev}</a></li>`).join("")}</ul></section>`);
}
async function viewAddress(id) {
  if (ADDR.length && !ADDR.some((a) => a.id === id)) return viewNotFound("address");
  const url = addrUrl(id);
  let d = null;
  const p = api(url);
  const quick = await Promise.race([p.then((x) => x, () => null), new Promise((r) => setTimeout(() => r(null), 140))]);
  if (quick) d = quick;
  const same = main.dataset.addr === id && !!$(".addr", main); // as-of / language change on this address: update in place
  const open = same ? $$(".topic[open]", main).map((x) => x.id) : [];
  if (!quick) {
    if (!same) await swap(addressSkeleton());
    progress(true);
    try { d = await p; } catch { progress(false); return viewNotFound("address"); }
    progress(false);
  }
  const a = d.address, j = d.jurisdiction;
  const methodLabel = t("m_" + j.method).startsWith("m_") ? j.method : t("m_" + j.method);
  const stack = [...j.stack].reverse().map((s) => esc(t(s.name))).join(" · ");
  const facts = [a.year_built ? tf("built_y", { y: a.year_built }) : t("year_unknown"), a.units ? tf("units_n", { n: a.units }) : t("units_unknown")];
  const row = (k, v) => v ? `<div><dt>${esc(k)}</dt><dd>${v}</dd></div>` : "";
  const html = `
  <article class="addr">
    <header class="addr-head">
      <h1>${esc(titleCase(a.street_address))}</h1>
      <p class="addr-sub">${esc(a.postal_city)}, ${esc(a.state)} ${esc(a.zip || "")}</p>
      <p class="addr-meta">${stack}</p>
      <p class="addr-meta">${facts.map(esc).join(" · ")}</p>
      ${j.postal_differs ? `<p class="addr-meta strong">${esc(tf("mailing_legal", { p: a.postal_city, c: j.city }))}</p>` : ""}
      <details class="how"><summary>${t("how_resolved")}<span class="chev">${I.chev}</span></summary>
        <dl class="kv">
          ${row(t("method"), esc(methodLabel))}
          ${row(t("confidence"), `${pctOf(j.confidence)}%`)}
          ${row("", j.note ? esc(j.note) : "")}
          ${row(t("county"), j.county ? esc(j.county) : "")}
          ${row("", j.lat ? `<a href="https://www.openstreetmap.org/?mlat=${j.lat}&mlon=${j.lon}#map=17/${j.lat}/${j.lon}" target="_blank" rel="noopener">${(+j.lat).toFixed(4)}, ${(+j.lon).toFixed(4)}${I.ext}</a>` : "")}
          ${row(t("use"), a.use_description ? esc(a.use_description) : "")}
          ${row(t("data_from"), esc(a.source_dataset || ""))}
          ${row("ID", `<span class="mono">${esc(a.address_id)}</span>`)}
        </dl>
      </details>
      <div class="addr-actions" data-slot="address-actions"></div>
    </header>
    <section class="answers">${answersHTML(d)}</section>
  </article>`;
  if (same) { main.innerHTML = html; open.forEach((x) => { const el = document.getElementById(x); if (el) el.open = true; }); }
  else await swap(html);
  main.dataset.addr = id;
  document.title = `${titleCase(a.street_address)}, ${a.postal_city} · Clause & Effect`;
}

// ------------------------------------------------------------------ modal --
function openModal(title, body) {
  const m = $("#modal");
  $("#modal-title").textContent = title;
  $(".modal-body", m).innerHTML = body;
  if (m.hidden || m.classList.contains("closing")) lastFocus = document.activeElement;
  clearTimeout(m._closeT); m.classList.remove("closing"); m.hidden = false;
  lockScroll(true);
  $(".modal-body", m).scrollTop = 0;
  $("[data-close]", m).focus();
}
function closeModal() { const m = $("#modal"); if (!m.hidden) closeLayer(m); }
async function openSource(doc, rule) {
  openModal(doc, `<div class="sk" style="height:18px;width:60%"></div><div class="sk" style="height:320px;margin-top:14px"></div>`);
  const d = await api(`/api/source/${doc}?rule_id=${encodeURIComponent(rule || "")}`);
  const txt = d.text;
  let body = esc(txt);
  if (d.highlight) body = esc(txt.slice(0, d.highlight[0])) + `<mark id="hlm">${esc(txt.slice(d.highlight[0], d.highlight[1]))}</mark>` + esc(txt.slice(d.highlight[1]));
  $("#modal-title").textContent = host(d.meta.url) || doc;
  $(".modal-body").innerHTML = `<p class="rd-meta">${d.meta.url ? `<a href="${esc(d.meta.url)}" target="_blank" rel="noopener">${esc(d.meta.url)}${I.ext}</a>` : ""}<span class="sep">·</span>${esc(tf("retrieved", { d: fmtDate(d.meta.retrieved_at) }))}${d.meta.sha256 ? `<span class="sep">·</span><span class="mono">sha256 ${esc(d.meta.sha256.slice(0, 12))}…</span>` : ""}</p><div class="doc-text">${body}</div>`;
  $("#hlm")?.scrollIntoView({ block: "center", behavior: "auto" });
}
document.addEventListener("click", (e) => {
  const a = e.target.closest("[data-doc]");
  if (a) { e.preventDefault(); openSource(a.dataset.doc, a.dataset.rule); }
  if (e.target.closest("[data-close]") || e.target.id === "modal") closeModal();
});

// ------------------------------------------------------------------ changes --
const TL_START = new Date("2024-01-01T12:00:00");
const dayIdx = (d) => Math.round((new Date(d + "T12:00:00") - TL_START) / 864e5);
const idxDay = (i) => new Date(TL_START.getTime() + i * 864e5).toISOString().slice(0, 10);
const TL_MAX = dayIdx("2028-01-01");
const pct = (d) => Math.max(0, Math.min(100, (dayIdx(d) / TL_MAX) * 100));
async function viewChanges() {
  progress(true);
  const tl = await api("/api/timeline");
  progress(false);
  const shown = tl.filter((e) => e.date >= "2024-01-01"), older = tl.filter((e) => e.date < "2024-01-01");
  const html = `
    <header class="page-head"><h1>${t("changes_title")}</h1><p>${t("changes_lead")}</p></header>
    <section class="tl" aria-label="${t("timeline_aria")}">
      <div class="tl-top"><b id="tl-date"></b><span id="tl-sum"></span></div>
      <div class="tl-track"><div class="tl-line"></div><div class="tl-fill" id="tl-fill"></div>
        ${[...new Set(shown.map((e) => e.date))].map((d) => `<i class="tl-tick" data-date="${d}" style="left:${pct(d)}%" aria-hidden="true"></i>`).join("")}
        <input type="range" class="tl-range" id="tl-range" min="0" max="${TL_MAX}" value="${dayIdx(asOf)}" aria-label="${t("asof_aria")}">
      </div>
      <div class="tl-years" aria-hidden="true">${[2024, 2025, 2026, 2027, 2028].map((y) => `<span style="left:${pct(y + "-01-01")}%">${y}</span>`).join("")}</div>
    </section>
    <ul class="group events" id="events">
      ${shown.map((e) => `<li><button type="button" class="ev" data-date="${e.date}"><span class="ev-d">${esc(fmtDate(e.date))}</span><span class="ev-main"><span class="ev-t">${esc(e.title)}</span><span class="ev-s">${esc(shortJ(e.jurisdiction))} · ${esc(tf("addresses_n", { n: e.addresses }))}</span></span><span class="ev-st"></span></button></li>`).join("")}
      ${older.length ? `<li><details class="ev-older"><summary class="ev"><span class="ev-d">${esc(older[0].date.slice(0, 4))}–${esc(older[older.length - 1].date.slice(0, 4))}</span><span class="ev-main"><span class="ev-t">${esc(tf("earlier", { n: older.length }))}</span></span><span class="chev">${I.chev}</span></summary>
        <ul>${older.map((e) => `<li><span class="ev-d">${esc(fmtDate(e.date))}</span><span>${esc(e.title)} · ${esc(shortJ(e.jurisdiction))}</span></li>`).join("")}</ul></details></li>` : ""}
    </ul>`;
  await swap(html, () => {
    const range = $("#tl-range"), dateEl = $("#tl-date");
    let last = null, raf = 0;
    const paint = (d) => {
      if (d === last) return;
      last = d;
      dateEl.textContent = fmtDate(d);
      $("#tl-fill").style.transform = `scaleX(${pct(d) / 100})`;
      $$(".tl-tick").forEach((b) => b.classList.toggle("past", b.dataset.date <= d));
      $$("#events .ev[data-date]").forEach((r) => {
        const now = r.dataset.date <= d;
        r.classList.toggle("past", now);
        r.querySelector(".ev-st").innerHTML = badge(now ? "in_force" : "not_yet_effective", "", null, t(now ? "in_force_on" : "not_yet"));
      });
      const live = tl.filter((e) => e.date <= d).length;
      $("#tl-sum").textContent = `${tf("in_effect", { n: live })} · ${tf("upcoming", { n: tl.length - live })}`;
    };
    paint(asOf);
    range.addEventListener("input", () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(() => paint(idxDay(+range.value))); });
    range.addEventListener("change", () => { $("#asof").value = idxDay(+range.value); setAsOf(idxDay(+range.value), { silent: true }); toast(tf("toast_asof", { d: fmtDate(asOf) })); });
    $$("#events .ev[data-date]").forEach((b) => b.addEventListener("click", () => {
      const target = dayIdx(b.dataset.date), from = +range.value;
      const done = () => { range.value = target; paint(b.dataset.date); $("#asof").value = b.dataset.date; setAsOf(b.dataset.date, { silent: true }); toast(tf("toast_asof", { d: fmtDate(asOf) })); };
      if (RM.matches) return done();
      const t0 = performance.now(), dur = 500;
      const step = (now) => { const p = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - p, 4); const v = Math.round(from + (target - from) * e); range.value = v; paint(idxDay(v)); if (p < 1) requestAnimationFrame(step); else done(); };
      requestAnimationFrame(step);
    }));
  });
}

// ------------------------------------------------------------------ rules explorer --
let RF = { jur: "", cat: "", status: "", q: "", conflicts: false }, RT_OPEN = false;
async function viewRules() {
  progress(true);
  const [rules, cov] = await Promise.all([api(`/api/rules?lang=${lang}&as_of=${asOf}`), api(`/api/coverage?as_of=${asOf}`)]);
  progress(false);
  const catLabel = Object.fromEntries(cov.categories.map((c) => [c.id, t("cat_" + c.id)]));
  const count = (s) => rules.filter((r) => r.status === s).length;
  const html = `
    <header class="page-head"><h1>${t("rules_title")}</h1><p>${t("rules_lead")}</p></header>
    <dl class="stats">
      <div><dt>${t("rules_title")}</dt><dd>${rules.length}</dd></div>
      <div><dt>${resLabel("in_force")}</dt><dd>${count("in_force")}</dd></div>
      <div><dt>${resLabel("not_yet_effective")}</dt><dd>${count("not_yet_effective")}</dd></div>
      <div><dt>${resLabel("pending")}</dt><dd>${count("pending")}</dd></div>
      <div><dt>${t("conflict")}</dt><dd>${rules.filter((r) => r.conflict_flag).length}</dd></div>
    </dl>
    <section class="block"><h2>${t("coverage")}</h2>
      <div class="table-wrap"><table class="matrix"><thead><tr><th><span class="sr">${t("jurisdiction")}</span></th>${cov.categories.map((c) => `<th>${esc(catLabel[c.id])}</th>`).join("")}</tr></thead>
      <tbody>${cov.jurisdictions.map((j) => `<tr class="${j.length === 2 ? "state" : "city"}"><th>${esc(j.length === 2 ? t(STATE_NAMES[j] || j) : shortJ(j))}</th>${cov.categories.map((c) => {
        const cell = cov.cells[j]?.[c.id] || [];
        const nr = cov.no_rule_cells?.[j]?.[c.id];
        return `<td>${cell.length ? `<button type="button" data-j="${esc(j)}" data-c="${c.id}" title="${esc(cell.map((x) => x.id + ": " + x.title).join("\n"))}">${cell.map((x) => `<i class="dot st-${x.status}"></i>`).join("")}<span>${cell.length}</span></button>` : nr ? `<button type="button" class="none finding" data-nr="${esc(nr.id)}" aria-label="${esc(t("legend_nr") + ": " + nr.finding)}">∅</button>` : `<span class="none">–<span class="sr"> ${t("none_level")}</span></span>`}</td>`;
      }).join("")}</tr>`).join("")}</tbody></table></div>
      <p class="legend">${["in_force", "not_yet_effective", "pending", "failed"].map((s) => `<span><i class="dot st-${s}"></i>${esc(resLabel(s))}</span>`).join("")}<span><b>∅</b> ${esc(t("legend_nr"))}</span><span><b>–</b> ${esc(t("none_level"))}</span></p>
    </section>
    <details class="block disclose" id="rules-table"${RT_OPEN ? " open" : ""}><summary><h2>${tf("show_table", { n: rules.length })}</h2><span class="chev">${I.chev}</span></summary>
      <div class="filters">
        <select id="f-j" aria-label="${t("jurisdiction")}"><option value="">${t("jurisdiction")}: ${t("all")}</option>${cov.jurisdictions.map((j) => `<option value="${esc(j)}">${esc(j)}</option>`).join("")}</select>
        <select id="f-c" aria-label="${t("category")}"><option value="">${t("category")}: ${t("all")}</option>${cov.categories.map((c) => `<option value="${c.id}">${esc(catLabel[c.id])}</option>`).join("")}</select>
        <select id="f-s" aria-label="${t("status")}"><option value="">${t("status")}: ${t("all")}</option>${["in_force", "not_yet_effective", "pending", "failed"].map((s) => `<option value="${s}">${esc(resLabel(s))}</option>`).join("")}</select>
        <input type="search" id="f-q" placeholder="${t("q_filter")}" aria-label="${t("q_filter")}">
        <label class="chk"><input type="checkbox" id="f-x"> ${t("only_conflicts")}</label>
      </div>
      <p class="count-note" id="rc"></p>
      <div class="table-wrap"><table class="rtable"><thead><tr><th>${t("col_rule")}</th><th>${t("key_value")}</th><th>${t("status")}</th><th>${t("effective")}</th><th>${t("col_addresses")}</th></tr></thead><tbody id="rt"></tbody></table></div>
    </details>`;
  await swap(html, () => {
    const draw = () => {
      const q = RF.q.trim().toLowerCase();
      const list = rules.filter((r) => (!RF.jur || r.jurisdiction === RF.jur) && (!RF.cat || r.category === RF.cat) && (!RF.status || r.status === RF.status) && (!RF.conflicts || r.conflict_flag) && (!q || JSON.stringify([r.team_rule_id, r.title, r.title_display, r.requirement, r.citation, r.key_value]).toLowerCase().includes(q)));
      $("#rc").textContent = `${list.length} / ${tf("rules_n", { n: rules.length })}`;
      $("#rt").innerHTML = list.map((r) => `<tr class="clickable" data-rule="${esc(r.team_rule_id)}" tabindex="0">
        <td><div class="t">${esc(r.title_display || r.title)}</div><div class="s">${esc(r.jurisdiction)} · ${esc(catLabel[r.category] || r.category)} · <span class="mono">${esc(r.team_rule_id)}</span></div></td>
        <td class="kvc">${esc(r.key_value_display || r.key_value || "–")}</td><td>${badge(r.status)}${r.conflict_flag ? `<div class="s">${t("conflict")}</div>` : ""}</td><td class="s nw">${esc(r.effective_date ? fmtDate(r.effective_date_norm || r.effective_date) : "–")}</td><td class="num">${r.addresses_count}</td></tr>`).join("")
        || `<tr><td colspan="5" class="empty">${t("no_rules_match")} <button type="button" class="linkish" id="f-clear">${t("clear_filters")}</button></td></tr>`;
      $("#f-clear")?.addEventListener("click", () => { RF = { jur: "", cat: "", status: "", q: "", conflicts: false }; sync(); });
    };
    const sync = () => { $("#f-j").value = RF.jur; $("#f-c").value = RF.cat; $("#f-s").value = RF.status; $("#f-q").value = RF.q; $("#f-x").checked = RF.conflicts; draw(); };
    $("#rules-table").addEventListener("toggle", (e) => { RT_OPEN = e.target.open; });
    $("#f-j").onchange = (e) => { RF.jur = e.target.value; draw(); };
    $("#f-c").onchange = (e) => { RF.cat = e.target.value; draw(); };
    $("#f-s").onchange = (e) => { RF.status = e.target.value; draw(); };
    $("#f-q").oninput = (e) => { RF.q = e.target.value; draw(); };
    $("#f-x").onchange = (e) => { RF.conflicts = e.target.checked; draw(); };
    $$(".matrix button[data-nr]").forEach((b) => b.onclick = () => {
      const f = cov.no_rule_findings.find((x) => x.finding_id === b.dataset.nr);
      openModal(`${f.jurisdiction} · ${catLabel[f.category] || f.category}`, `<div class="rd"><p class="rd-plain">${esc(f.finding)}</p>${sourceHtml({ quote: f.quoted_span, citation: f.citation, url: f.source_url, id: f.finding_id })}</div>`);
    });
    $$(".matrix button[data-j]").forEach((b) => b.onclick = () => { RF = { ...RF, jur: b.dataset.j, cat: b.dataset.c }; sync(); $("#rules-table").open = true; $("#rules-table").scrollIntoView({ behavior: RM.matches ? "auto" : "smooth", block: "start" }); });
    const openRule = (id) => {
      const r = rules.find((x) => x.team_rule_id === id);
      const cc = r.coverage_conditions && typeof r.coverage_conditions === "object" ? JSON.stringify(r.coverage_conditions) : r.coverage_conditions;
      const fields = [[t("jurisdiction"), r.jurisdiction], [t("f_level"), r.level === "state" ? t("state") : r.level === "city" ? t("city") : r.level], [t("category"), catLabel[r.category]], [t("status"), resLabel(r.status)], [t("effective"), r.effective_date], [t("key_value"), r.key_value_display || r.key_value], [t("f_coverage"), cc], [t("f_exemptions"), r.exemptions], [t("f_overrides"), (r.overrides || []).join(", ")], [t("f_interaction"), r.interaction_display || r.interaction], [t("f_conflict_note"), r.conflict_note_display || r.conflict_note], [t("sample_addresses"), r.addresses_count]];
      openModal(r.title_display || r.title, `<div class="rd"><p class="rd-plain">${esc(r.requirement_display || r.requirement)}</p>
        ${sourceHtml(ruleSource(r))}
        <section class="rd-sec"><h5>${t("details")}</h5><dl class="kv">${fields.filter((f) => f[1] != null && f[1] !== "").map((f) => `<div><dt>${esc(f[0])}</dt><dd>${esc(f[1])}</dd></div>`).join("")}</dl></section></div>`);
    };
    $("#rt").addEventListener("click", (e) => { const tr = e.target.closest("tr[data-rule]"); if (tr && !e.target.closest("a")) openRule(tr.dataset.rule); });
    $("#rt").addEventListener("keydown", (e) => { const tr = e.target.closest("tr[data-rule]"); if (tr && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); openRule(tr.dataset.rule); } });
    sync();
  });
}

// ------------------------------------------------------------------ audit --
function bars(counts, label) {
  const order = ["applies", "unknown", "superseded", "not_yet_effective", "pending"];
  const total = Object.values(counts || {}).reduce((a, b) => a + b, 0);
  return `<div class="rr-row"><div class="nm"><span class="mono">${esc(label)}</span><span class="muted">${esc(tf("addresses_n", { n: total }))}</span></div>
    <div class="bar">${order.filter((r) => counts?.[r]).map((r) => `<i class="st-${r}" style="width:${(counts[r] / total) * 100}%" title="${esc(resLabel(r))}: ${counts[r]}"></i>`).join("")}</div>
    <div class="cnt">${order.filter((r) => counts?.[r]).map((r) => `<span><i class="dot st-${r}"></i>${esc(resLabel(r))} ${counts[r]}</span>`).join("") || `<span>${t("none_level")}</span>`}</div></div>`;
}
function checkRow(x) {
  const dated = x.type === "as_of" || x.type === "new_law";
  const rulesLine = x.rules.map((r) => `${esc(r.title_display || r.title)}`).join(" · ") || t("no_match_rule");
  const ba = dated
    ? `<div class="ba"><div><h5>${t("before")} · ${esc(fmtDate(x.before_date))}</h5>${x.our_rule_ids.map((r) => bars(x.before[r], r)).join("")}</div>
       <div><h5>${t("after")} · ${esc(fmtDate(x.after_date))}</h5>${x.our_rule_ids.map((r) => bars(x.after[r], r)).join("")}</div></div>`
    : `<div class="ba one"><div><h5>${t("rule_reach")} · ${esc(fmtDate(x.after_date))}</h5>${x.our_rule_ids.map((r) => bars(x.after[r], r)).join("") || `<p class="muted">${t("none_level")}</p>`}</div></div>`;
  const ids = x.affected_address_ids;
  return `<details class="topic" id="check-${esc(x.test_id)}"><summary><span class="topic-main"><span class="topic-q">${esc(x.title_display || x.title)}</span><span class="topic-a">${esc(t("t_" + x.type))} · ${rulesLine}</span></span><span class="num-b">${esc(tf("addresses_n", { n: x.affected_count }))}</span><span class="chev">${I.chev}</span></summary>
    <div class="topic-body"><div class="rd">
      <p class="rd-plain">${esc(isoDates(x.expected_display || x.expected_behavior))}</p>
      ${ba}
      <section class="rd-sec"><h5>${t("affected")}${x.conflict_flag_address_ids.length ? ` · ${esc(tf("conflict_flags", { n: x.conflict_flag_address_ids.length }))}` : ""}</h5>
        <p class="citylist">${Object.entries(x.affected_by_city).map(([c, n]) => `${esc(c)} <b>${n}</b>`).join("<span class=\"sep\">·</span>")}</p>
        ${ids.length ? `<p class="idlist">${ids.map((id) => `<a href="#/a/${id}" class="mono">${id}</a>`).join(" ")}</p>` : ""}</section>
    </div></div></details>`;
}
const shortUrl = (u) => {
  const s = String(u || "").replace(/^https?:\/\/(www\.)?/, "");
  let host = s.split("/")[0], path = s.slice(host.length);
  try { path = decodeURIComponent(path); } catch { /* keep encoded */ }
  if (path.length <= 34) return host + path;
  const segs = path.split("/").filter(Boolean);
  return `${host}/…/${segs[segs.length - 1].slice(0, 40)}${segs[segs.length - 1].length > 40 ? "…" : ""}`;
};
async function viewAudit() {
  progress(true);
  const [d, tests] = await Promise.all([api("/api/audit", { fresh: true }), api(`/api/changes?lang=${lang}&as_of=${asOf}`)]);
  progress(false);
  const ver = d.verification, vt = Object.values(ver).reduce((a, b) => a + b, 0);
  const steps = ["ingest", "extract", "resolve", "apply", "track"].map((k) => [t("p_" + k), tf(`p_${k}_d`, { n: d.documents.length })]);
  const geoTotal = Object.values(d.geocoding).reduce((a, b) => a + b, 0);
  const verifiedN = (ver.exact || 0) + (ver.normalized || 0);
  const sec = (id, title, body) => `<details class="topic" id="${id}"><summary><span class="topic-main"><span class="topic-q">${title}</span></span><span class="chev">${I.chev}</span></summary><div class="topic-body">${body}</div></details>`;
  const html = `
    <header class="page-head"><h1>${t("audit_title")}</h1><p>${t("audit_lead")}</p></header>
    <dl class="stats">
      <div><dt>${esc(t("k_docs"))}</dt><dd>${d.documents.length}</dd></div>
      <div><dt>${esc(t("k_quotes"))}</dt><dd>${verifiedN}/${vt}</dd></div>
      <div><dt>${esc(t("k_geo"))}</dt><dd>${geoTotal}</dd></div>
      <div><dt>${esc(t("k_log"))}</dt><dd>${d.audit_total}</dd></div>
    </dl>
    <section class="block"><h2>${t("method_t")}</h2>
      <ol class="steps">${steps.map((x) => `<li><b>${esc(x[0])}</b><span>${esc(x[1])}</span></li>`).join("")}</ol></section>
    <section class="block"><h2>${t("checks_t")}</h2><p class="block-lead">${t("checks_lead")}</p>
      <div class="topics group">${tests.map(checkRow).join("")}</div></section>
    <section class="block"><div class="topics group">
      ${sec("a-scale", t("a_scale"), `<ol class="steps">${[1, 2, 3, 4].map((n) => `<li><b>${esc(t(`s${n}_t`))}</b><span>${esc(t("s" + n))}</span></li>`).join("")}</ol>`)}
      ${sec("a-files", t("a_files"), `<dl class="kv">${Object.entries(d.sources).map(([n, src]) => `<div><dt class="mono">${esc(n)}</dt><dd>${esc(src.kind)}${src.modified ? ` · ${esc(src.modified.replace("T", " "))}` : ""}</dd></div>`).join("")}</dl>
        <p class="block-lead">${esc(tf("a_spans", { a: verifiedN, b: vt }))}${ver.not_found ? `; ${esc(tf("a_notfound", { n: ver.not_found }))}` : ""}${ver.no_text ? `; ${esc(tf("a_notext", { n: ver.no_text }))}` : ""}.</p>`)}
      ${sec("a-geo", t("a_geo"), `<dl class="kv">${Object.entries(d.geocoding).map(([k, v]) => `<div><dt>${esc(t("m_" + k).startsWith("m_") ? k : t("m_" + k))}</dt><dd>${v}</dd></div>`).join("")}</dl>
        <div class="table-wrap tall"><table class="rtable"><thead><tr><th>${t("col_address")}</th><th>${t("col_mailing")}</th><th>${t("col_legal")}</th><th>${t("col_method")}</th></tr></thead><tbody>${d.geocoding_notes.map((g) => `<tr><td><a href="#/a/${g.id}">${esc(titleCase(g.street))}</a></td><td>${esc(g.postal_city)}</td><td>${esc(g.city || t("outside"))}</td><td class="s" title="${esc(g.note)}">${esc(t("m_" + g.method).startsWith("m_") ? g.method : t("m_" + g.method))}</td></tr>`).join("")}</tbody></table></div>`)}
      ${sec("a-docs", tf("a_docs", { n: d.documents.length }), `<div class="table-wrap tall"><table class="rtable"><thead><tr><th>${t("col_source")}</th><th>${t("jurisdiction")}</th><th>${t("col_type")}</th><th>${t("col_rules")}</th><th><span class="sr">${t("col_text")}</span></th></tr></thead><tbody>
        ${d.documents.map((x) => `<tr><td><a href="${esc(x.url)}" target="_blank" rel="noopener" title="${esc(x.url)}">${esc(shortUrl(x.url))}</a><div class="s"><span class="mono">${esc(x.doc_id)}</span> · ${esc(tf("retrieved", { d: x.retrieved_at ? fmtDate(x.retrieved_at) : "–" }))}</div></td><td class="nw">${esc(x.jurisdictions)}</td><td class="s">${esc(x.source_type)}${x.capture !== "yes" ? ` · ${esc(x.capture)}` : ""}</td><td class="num">${x.rules_extracted || 0}</td><td>${x.text_available ? `<a href="#" data-doc="${esc(x.doc_id)}">${t("l_text")}</a>` : `<span class="s">${t("l_link")}</span>`}</td></tr>`).join("")}
        </tbody></table></div>`)}
      ${sec("a-log", `${t("a_log")} · ${d.audit_total}`, `<div class="filters"><input type="search" id="lq" placeholder="${t("q_filter")}" aria-label="${t("q_filter")}"></div><p class="count-note" id="lc"></p><div class="log" id="log"></div>`)}
    </div></section>`;
  await swap(html, () => {
    const LOG_MAIN = ["ts", "stage", "doc_id", "chunk", "n_chunks", "model", "prompt_version", "cached", "n_rules", "doc_summary", "idx", "raw_chars", "validation_items", "prompt_hash"];
    let q = "";
    const drawLog = (res) => {
      const entries = res.audit;
      const total = res.audit_total ?? d.audit_total;
      $("#lc").innerHTML = entries.length < total && !q ? `${esc(tf("log_showing", { a: entries.length, b: total }))} <button type="button" class="linkish" id="log-all">${t("log_all")}</button>` : "";
      $("#log-all")?.addEventListener("click", async () => drawLog(await api(`/api/audit?limit=5000`, { fresh: true })));
      $("#log").innerHTML = entries.map((e) => {
        const extra = Object.entries(e).filter(([k]) => !LOG_MAIN.includes(k));
        return `<details class="log-row"><summary>
          <span class="lt">${esc((e.ts || "").replace("T", " ").slice(0, 19))}</span><span class="ls">${esc(e.stage || e.event || "")}</span>
          <span class="ld">${esc(e.doc_id || "")}${e.n_chunks > 1 ? ` ${+e.chunk + 1}/${e.n_chunks}` : ""}</span>
          <span class="lx">${esc(e.doc_summary || extra.map(([k, v]) => `${k}=${typeof v === "object" ? JSON.stringify(v) : v}`).join("  "))}</span></summary>
          <pre class="log-raw" data-idx="${e.idx}">${t("loading")}</pre></details>`;
      }).join("") || `<p class="empty">${esc(tf("log_none", { q }))}</p>`;
      $$("#log details").forEach((dEl) => dEl.addEventListener("toggle", async () => {
        const pre = $("pre", dEl);
        if (!dEl.open || pre.dataset.loaded) return;
        const full = await api(`/api/audit/entry/${pre.dataset.idx}`);
        if (typeof full.raw_output === "string") { try { full.raw_output = JSON.parse(full.raw_output); } catch { /* keep raw */ } }
        pre.textContent = JSON.stringify(full, null, 2); pre.dataset.loaded = 1;
      }));
    };
    drawLog(d);
    let tmr;
    $("#lq").addEventListener("input", (e) => { clearTimeout(tmr); tmr = setTimeout(async () => { q = e.target.value.trim(); drawLog(await api(`/api/audit?q=${encodeURIComponent(q)}`, { fresh: true })); }, 200); });
  });
}

// ------------------------------------------------------------------ router --
let routing = 0;
const ROUTES = new Map();
async function route({ keepScroll = false, soft = false } = {}) {
  const my = ++routing;
  cleanup.forEach((f) => f()); cleanup = [];
  const [view, arg] = location.hash.replace(/^#\/?/, "").split("/");
  const name = view === "a" ? "lookup" : view || "lookup";
  syncHeader(name);
  closeModal(); closeCmdk();
  const titles = { changes: "t_changes", rules: "t_rules", audit: "t_audit" };
  document.title = titles[view] ? `${t(titles[view])} · Clause & Effect` : `Clause & Effect · ${t("tagline_short")}`;
  const y = scrollY;
  const back = !soft && history.state?.ce ? history.state.ce : null; // returning to an entry we left (Back): restore it (#63)
  if (!soft && view !== "a") delete main.dataset.addr;
  try {
    if (ROUTES.has(view)) await ROUTES.get(view)(main, arg ? decodeURIComponent(arg) : undefined);
    else if (view === "a" && arg) await viewAddress(arg.toUpperCase());
    else if (view === "changes") await viewChanges();
    else if (view === "rules") await viewRules();
    else if (view === "audit") await viewAudit();
    else if (!view) await viewHome();
    else { location.replace("#/"); return; }
  } catch (e) {
    progress(false);
    if (my === routing) main.innerHTML = `<div class="empty">${t("error")} ${esc(e.message)}</div>`;
    console.error(e);
  }
  if (my !== routing) return;
  document.dispatchEvent(new CustomEvent("ce:route", { detail: { view: name, arg } }));
  if (back) {
    back.open.forEach((id) => { const el = document.getElementById(id); if (el) el.open = true; });
    scrollTo({ top: back.y, behavior: "instant" });
  } else if (keepScroll) scrollTo({ top: y, behavior: "instant" });
  else scrollTo({ top: 0, behavior: "instant" });
  if (!firstRoute && !soft) main.focus({ preventScroll: true });
  firstRoute = false;
}
let firstRoute = true;
// Before following an in-app link, remember where we were on this entry, so Back returns to the same place (#63).
document.addEventListener("click", (e) => {
  const a = e.target.closest('a[href^="#/"]');
  if (!a || e.defaultPrevented || e.metaKey || e.ctrlKey) return;
  history.replaceState({ ...(history.state || {}), ce: { y: scrollY, open: $$("details[open][id]", main).map((x) => x.id) } }, "");
}, true);
addEventListener("hashchange", () => route());
document.addEventListener("click", (e) => { const a = e.target.closest(".tabs a, .footer-links a"); if (a) setTimeout(() => a.blur(), 0); });

// ------------------------------------------------------------------ public API for feature modules --
// Documented in web/DESIGN.md ("window.CE"). Keep these signatures stable.
const CATS = ["rent_increase_limits", "just_cause_eviction", "security_deposits", "application_screening_fees", "screening_restrictions", "algorithmic_rent_setting"];
function normalizeLookup(res) {
  if (res && Array.isArray(res.categories)) return res; // /api/address/<id> shape
  const results = res?.results || res?.lookups || (Array.isArray(res) ? res : []);
  const cats = CATS.map((id) => ({ id, enacted: [], pending: [], not_law: [], no_rule_findings: [] }));
  const byId = Object.fromEntries(cats.map((c) => [c.id, c]));
  for (const e of results) {
    const rule = e.rule || { ...e, title_display: e.title, requirement_display: e.requirement, key_value_display: e.key_value,
      quote_check: typeof e.verification === "object" ? e.verification : null, source: { retrieved_at: e.retrieved_at, has_text: !!e.source_doc_id } };
    const item = { result: e.result, explanation: e.explanation, explanation_en: e.explanation_en, conflict_flag: !!e.conflict_flag, missing_fact: e.missing_fact, superseded_by: e.superseded_by, overrides_here: e.overrides_here, rule };
    const c = byId[rule.category] || byId[e.category];
    if (!c) continue;
    (e.result === "pending" ? c.pending : e.result === "failed" ? c.not_law : c.enacted).push(item);
  }
  for (const f of res?.no_rule_findings || []) byId[f.category]?.no_rule_findings.push(f);
  return { as_of: res?.as_of || asOf, engine: res?.engine || "live", categories: cats };
}
window.CE = Object.freeze({
  version: 1,
  /** Render the answers (as-of note, one row per topic with its detail, then pending/failed bills) into `container`. */
  renderAnswers(container, lookupResult) {
    const el = typeof container === "string" ? $(container) : container;
    el.innerHTML = answersHTML(normalizeLookup(lookupResult));
    return el;
  },
  navigate(routeOrHash) { location.hash = routeOrHash.startsWith("#") ? routeOrHash : "#/" + String(routeOrHash).replace(/^\/+/, ""); },
  /** Register a view at #/<name>[/<arg>]: render(mainEl, arg) may be async. */
  addRoute(name, render) { ROUTES.set(name, render); if (location.hash.replace(/^#\/?/, "").split("/")[0] === name) route(); },
  toast,
  t,
  api,
  asOf: () => asOf,
  lang: () => lang,
  badge: (result, label) => badge(result, "", null, label),
  icons: I,
  escape: esc,
  openModal,
  openSearch: () => openCmdk(),
  /** Set the as-of date (YYYY-MM-DD) like the header control does: re-renders the view and fires ce:asof. */
  setAsOf: (d) => { $("#asof").value = d; setAsOf(d); },
  fmtDate,
});

(async function init() {
  syncHeader(currentView());
  [META, ADDR] = await Promise.all([api("/api/meta"), api("/api/addresses")]);
  if (lang === "es") ES = await api("/api/i18n/es").catch(() => ({}));
  await route();
  document.dispatchEvent(new CustomEvent("ce:ready", { detail: { version: 1 } }));
})();
