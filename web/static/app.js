// Clause & Effect · Rental Housing Law Navigator. Build-free single-page frontend.
// Views: #/ (home), #/a/<id> (address), #/changes, #/rules, #/audit.  Design language: web/DESIGN.md

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const main = $("#main");
const RM = matchMedia("(prefers-reduced-motion: reduce)");

// ------------------------------------------------------------------ i18n --
const EN = {
  skip: "Skip to content", nla: "Not legal advice.", nla_chip: "Not legal advice",
  nla_strip: "Public law, with citations.",
  nla_body: "Information about public law, drawn from official sources and shown with citations. It is not a compliance check and not legal advice. For your situation, contact a tenant organisation, housing agency or attorney.",
  nla_title: "About this information",
  nav_lookup: "Address lookup", nav_changes: "What's changing", nav_rules: "Rules explorer", nav_audit: "Audit & sources",
  search_short: "Search", as_of: "As of", k_move: "move", k_open: "open", k_scope: "500 sample addresses in 9 cities",
  footer_body: "AI summaries of official texts retrieved 2026-10-01. They can be incomplete or wrong: always check the cited source.",
  footer_meta: "Hack-Nation 2026 · RealPage challenge prototype · Public data only: no customer, resident or pricing data.",
  answers_as_of: "Answers as of",
  hero_kicker: "3 states · 10 cities · 6 kinds of rules", live_title: "What an answer looks like",
  hero_title: "Which rules apply here *today*, and what is *about to change?*",
  hero_lead: "Enter an apartment address. See rent caps, eviction protections, deposit and fee limits, screening rules and algorithmic rent-setting bans, each quoted from the law it comes from.",
  search_ph: "Search by street, city or ID", try_q: "Try", preview_for: "Live answer for", preview_open: "Open full answer",
  pause: "Pause examples", play: "Play examples", prev: "Previous example", next: "Next example",
  man_1: "Every answer quotes", man_2: "the official text, carries its date", man_3: "and says", man_4: "unknown", man_5: "when the data can't tell.",
  f1_t: "The mailing city is not the legal city.", f1: "“Van Nuys” is Los Angeles. We ask the US Census which city an address is really in.", f1_l: "How addresses were resolved",
  f2_t: "Tested, never guessed.", f2: "Building age, units and dates are checked in code. Missing data means “unknown”.", f2_l: "Explore all rules",
  f3_t: "Read the sentence behind it.", f3: "Every rule links to the exact words in the official text.", f3_l: "Open the audit trail",
  try: "Try:", stat_rules: "rules extracted by AI", stat_sources: "source documents read", stat_addr: "sample addresses", stat_cities: "cities with sample addresses",
  r_applies: "Applies", r_unknown: "Unknown", r_superseded: "Superseded", r_not_yet_effective: "Not yet in effect", r_pending: "Pending bill", r_failed: "Failed · not law", r_in_force: "In force", r_no_rule: "No rule",
  d_applies: "In force and covers this building", d_unknown: "Depends on a fact the data does not have", d_superseded: "Covered, but a stricter rule governs", d_not_yet_effective: "Enacted, starts later", d_pending: "Proposed, not law",
  jurisdiction: "Jurisdiction", how_resolved: "How we found it", confidence: "Confidence", building: "Building facts",
  year_built: "Year built", units: "Units", use: "Use", zip: "ZIP", not_in_data: "Not in data", data_from: "Building data:",
  state: "State", county: "County", city: "City", back: "New search",
  rules_here: "Rules at this address", no_rule: "No enacted rule in this category was found at the state or city level for this address in our corpus.",
  no_rule_pending: "pending, see below", key_value: "Key figure", why: "Why:", missing_fact: "Missing fact:",
  superseded_by: "A stricter rule governs here:", overrides_here: "Takes precedence over", conflict: "Flagged for human review",
  takes_effect: "Takes effect", effective: "Effective", show_source: "Show the source", retrieved: "Retrieved",
  open_doc: "Open full document", quote_ok: "Quote verified", quote_bad: "Quote not found in source", quote_from: "quote from",
  proposals: "Not law: pending bills and failed proposals", proposals_intro: "Listed so you can see what may change. None of these is in force.",
  summary: "At a glance", machine_tr: "Machine-translated. Legal text stays in English.",
  changes_kicker: "Change tracking", changes_title: "What's changing", changes_lead: "Drag the date to see which laws are in force, and which addresses each change touches.",
  timeline: "Effective-date timeline", in_effect: "in effect", not_yet: "not yet in effect", addresses: "addresses", earlier: "earlier rules, in force before 2024",
  before: "Before", after: "After", affected: "Affected addresses", conflict_flags: "with conflict flag", show_ids: "Show address IDs",
  rule_reach: "Where each rule applies", expected: "Expected", notes: "Notes", no_match_rule: "No matching extracted rule found",
  t_as_of: "Date change", t_boundary: "City boundary", t_pending: "Pending bill", t_negative: "Failed proposal", t_new: "New ordinance", t_new_law: "New ordinance",
  rules_kicker: "Module A", rules_title: "Rules explorer", rules_lead: "Every rule the AI found, by place and topic.", col_rule: "Rule", col_quote: "Quote", col_addresses: "Addresses",
  coverage: "Coverage: jurisdiction × category", none_level: "no rule", finding: "no-rule finding", all: "All", only_conflicts: "Only flagged for review", category: "Category", status: "Status", rules_n: "rules",
  audit_kicker: "Responsible AI", audit_title: "Audit & sources", audit_lead: "Where each answer comes from, and how it was checked.",
  cat_rent_increase_limits: "Rent increases", q_rent_increase_limits: "How much can the rent go up?",
  cat_just_cause_eviction: "Eviction protections", q_just_cause_eviction: "Does the landlord need a reason to end the tenancy?",
  cat_security_deposits: "Security deposit", q_security_deposits: "How large can the deposit be?",
  cat_application_screening_fees: "Application & move-in fees", q_application_screening_fees: "What can be charged to apply or move in?",
  cat_screening_restrictions: "Tenant screening", q_screening_restrictions: "What may a landlord ask about or consider?",
  cat_algorithmic_rent_setting: "Algorithmic rent-setting", q_algorithmic_rent_setting: "Can software be used to set the rent?",
  missing_note: "Rules that depend on missing facts are marked “unknown”.", no_match: "No matching sample address", secondary: "secondary source",
  mailing_to_legal: "mailing city “{p}” → legal city {c}", loading: "Loading…",
  m_census_batch: "US Census batch geocoder", m_census_oneline: "US Census single-line geocoder", "m_osm_nominatim+census_coords": "OpenStreetMap + Census place",
  "m_osm_street_level+census_coords": "Street-level point + Census place", m_postal_city_fallback: "Postal city (fallback)",
  engine_live: "Evaluated live by the deterministic rule engine", engine_precomputed: "From the precomputed lookup run", "engine_precomputed+as_of": "Precomputed lookups, shifted by effective dates",
  show_dates: "Show all {n} dates", details: "Details", show_table: "Show all {n} rules as a table", k_docs: "source documents", k_quotes: "quotes verified", k_geo: "addresses resolved", k_log: "log entries",
  a_scale: "Adding a new city", a_files: "Output files and citation check", a_geo: "How addresses were resolved", a_docs: "All {n} source documents", a_log: "Extraction log ({n} entries)",
  asof_range: "Pick a date between {a} and {b}.", nf_title: "We couldn't find that address", nf_page: "Page not found", nf_body: "Search the 500 sample addresses, or start from an example.", tagline_short: "Which rules apply here?",
  legend_nr: "documented: no rule at this level", no_rule_found: "No rule at this level", why_source: "Why & source", depends_on: "Depends on:", overridden_by: "Overridden by", no_rule_short: "No rule found for this address.", q_filter: "Filter…",
  fixture: "Preview data: the extraction pipeline output is not generated yet, so the app shows schema-identical fixture records.",
  toast_asof: "Answers now as of {d}", toast_lang: "Language: English", g_examples: "Examples", g_results: "Addresses", g_pages: "Pages",
  not_found: "Address not found.", sample_addresses: "Sample addresses", error: "Something went wrong loading this view.",
};
let ES = {};
let lang = localStorage.getItem("lang") || "en";
const t = (k) => (lang === "es" && ES[k]) || EN[k] || k;
const resLabel = (r) => t("r_" + r);
const fmtDate = (d) => {
  if (!d) return "";
  const s = d.length === 7 ? d + "-01" : d.length === 4 ? d + "-01-01" : d;
  const dt = new Date(s + "T12:00:00");
  if (isNaN(dt)) return d;
  const opts = d.length === 7 ? { month: "short", year: "numeric" } : d.length === 4 ? { year: "numeric" } : { month: "short", day: "numeric", year: "numeric" };
  return dt.toLocaleDateString(lang === "es" ? "es-US" : "en-US", opts);
};
const titleCase = (s) => String(s || "").toLowerCase().replace(/\b\w/g, (m) => m.toUpperCase());

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
  ext: svg('<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>', ' style="width:13px;height:13px"'),
  layers: svg('<path d="m12 3 9 5-9 5-9-5z"/><path d="m3 13 9 5 9-5"/>'),
  q: svg('<circle cx="12" cy="12" r="9.5"/><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1 .9-1 1.7M12 17v.01"/>'),
  pin: svg('<path d="M12 21s7-6.1 7-11.5A7 7 0 0 0 5 9.5C5 14.9 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>'),
  cal: svg('<rect x="4" y="5" width="16" height="15" rx="3"/><path d="M8 3v4M16 3v4M4 10h16"/>'),
  doc: svg('<path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5M10 13h6M10 17h6"/>'),
  pause: svg('<path d="M9 6v12M15 6v12"/>'),
  play: svg('<path d="M8 5v14l11-7z"/>'),
  building: svg('<path d="M4 21V5l8-2v18M12 8l8 2v11M8 8v.01M8 12v.01M8 16v.01M16 13v.01M16 17v.01M2 21h20"/>'),
  globe: svg('<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18"/>'),
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
const badge = (r, cls = "", i = null) => `<span class="badge ${esc(r)} ${cls}"${i != null ? ` style="--i:${i}"` : ""}>${esc(resLabel(r))}</span>`;
const levelTag = (rule) => `<span class="lvl-tag">${esc(rule.level === "state" ? rule.jurisdiction + " · " + t("state") : String(rule.jurisdiction).replace(/, ..$/, "") + " · " + t("city"))}</span>`;
const pctOf = (c) => Math.round(c * 100);
const confMeter = (c) => c == null ? "" : `<span class="conf ${c < 0.7 ? "low" : ""}" title="${t("confidence")}: ${pctOf(c)}%">${t("confidence")} <span class="meter"><i style="width:${pctOf(c)}%"></i></span> ${pctOf(c)}%</span>`;
const verified = (v) => !v ? "" : v.status === "exact" || v.status === "normalized"
  ? `<span class="verified" title="${esc(v.label)}">${I.check}${t("quote_ok")}</span>`
  : v.status === "not_found" ? `<span class="verified no" title="${esc(v.label)}">${I.alert}${t("quote_bad")}</span>` : "";

// ------------------------------------------------------------------ motion helpers --
let firstPaint = true;
const io = "IntersectionObserver" in window ? new IntersectionObserver((entries) => {
  for (const e of entries) if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
}, { rootMargin: "0px 0px -6% 0px", threshold: 0 }) : null;
function swap(html, after) {
  // Plain cross-fade of <main> (no View Transitions API: a stalled transition froze old snapshots on screen).
  main.innerHTML = html; after?.(); armReveals();
  if (firstPaint) { firstPaint = false; return Promise.resolve(); }
  if (!RM.matches) { main.classList.remove("fade-in"); void main.offsetWidth; main.classList.add("fade-in"); }
  return Promise.resolve();
}
function armReveals(root = main) {
  const els = $$(".reveal:not(.in)", root);
  els.forEach((el) => { if (RM.matches || !io) el.classList.add("in"); else io.observe(el); });
  // Safety net: never leave content hidden if the observer does not fire (background tab, odd layouts).
  clearTimeout(armReveals.t);
  armReveals.t = setTimeout(() => $$(".reveal:not(.in)").forEach((el) => {
    const r = el.getBoundingClientRect();
    if (r.top < innerHeight * 1.5) el.classList.add("in");
  }), 1600);
}
addEventListener("scroll", () => { clearTimeout(armReveals.s); armReveals.s = setTimeout(() => $$(".reveal:not(.in)").forEach((el) => { if (el.getBoundingClientRect().top < innerHeight) el.classList.add("in"); }), 250); }, { passive: true });
const prog = $("#progress");
function progress(on) {
  if (on) { prog.className = "progress"; void prog.offsetWidth; prog.className = "progress run"; }
  else if (prog.classList.contains("run")) { prog.className = "progress done"; }
}
function toast(msg) {
  // One toast at a time: a new message updates the visible pill in place (no stack on repeated changes).
  let el = $("#toasts .toast:not(.out)");
  if (el) { $("span", el).textContent = msg; clearTimeout(el._t); }
  else { el = document.createElement("div"); el.className = "toast"; el.innerHTML = `${I.check}<span>${esc(msg)}</span>`; $("#toasts").append(el); }
  el._t = setTimeout(() => { el.classList.add("out"); el.addEventListener("animationend", () => el.remove(), { once: true }); }, 2600);
}
function countUp(el, to) {
  if (RM.matches) { el.textContent = to; return; }
  const t0 = performance.now(), dur = 1200;
  const step = (now) => { const p = Math.min(1, (now - t0) / dur); const e = 1 - Math.pow(1 - p, 4); el.textContent = Math.round(to * e); if (p < 1) requestAnimationFrame(step); };
  requestAnimationFrame(step);
}

// ------------------------------------------------------------------ header --
const nav = $("#nav");
addEventListener("scroll", () => nav.classList.toggle("scrolled", scrollY > 24), { passive: true });
function moveTabInk() {
  const ink = $(".tab-ink"), cur = $(".tabs a[aria-current='page']");
  if (!cur) { ink.style.opacity = 0; return; }
  ink.style.opacity = 1; ink.style.width = cur.offsetWidth + "px"; ink.style.transform = `translateX(${cur.offsetLeft}px)`;
  const tabs = cur.parentElement;
  if (tabs.scrollWidth > tabs.clientWidth) tabs.scrollTo({ left: cur.offsetLeft - (tabs.clientWidth - cur.offsetWidth) / 2, behavior: RM.matches ? "auto" : "smooth" });
}
addEventListener("resize", moveTabInk);
function syncHeader(route) {
  $$(".tabs a").forEach((a) => { if (a.dataset.route === route) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
  $("#asof").value = asOf;
  $$(".seg button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.lang === lang));
  $(".seg").dataset.active = lang;
  document.documentElement.lang = lang;
  $$("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  $("#cmdk input").placeholder = t("search_ph");
  $(".nav-inner").dataset.nla = t("nla_chip");
  const fb = $("#fixture-banner");
  fb.hidden = META?.sources?.["rules.json"]?.kind !== "fixture";
  fb.textContent = t("fixture");
  requestAnimationFrame(moveTabInk);
}
const ASOF_MIN = "2020-01-01", ASOF_MAX = "2030-12-31";
$("#asof").addEventListener("blur", (e) => { if (!e.target.value) e.target.value = asOf; });
$("#asof").addEventListener("change", (e) => {
  const v = e.target.value;
  if (!v) { e.target.value = asOf; return; }
  if (v < ASOF_MIN || v > ASOF_MAX) { e.target.value = asOf; toast(t("asof_range").replace("{a}", fmtDate(ASOF_MIN)).replace("{b}", fmtDate(ASOF_MAX))); return; }
  if (v === asOf) return;
  asOf = e.target.value; sessionStorage.setItem("asof", asOf);
  toast(t("toast_asof").replace("{d}", fmtDate(asOf))); route({ keepScroll: true });
  document.dispatchEvent(new CustomEvent("ce:asof", { detail: { asOf } }));
});
$$(".seg button").forEach((b) => b.addEventListener("click", async () => {
  if (lang === b.dataset.lang) return;
  lang = b.dataset.lang; localStorage.setItem("lang", lang);
  if (lang === "es" && !Object.keys(ES).length) ES = await api("/api/i18n/es").catch(() => ({}));
  toast(t("toast_lang")); route({ keepScroll: true });
  document.dispatchEvent(new CustomEvent("ce:lang", { detail: { lang } }));
}));
document.addEventListener("click", (e) => {
  if (e.target.closest("[data-nla-open]")) openNla();
});
function openNla() {
  openModal(t("nla_title"), `<p class="req" style="font-size:17px"><strong>${t("nla")}</strong> ${esc(t("nla_body"))}</p><p class="muted" style="margin-top:14px;font-size:14px">${esc(t("footer_body"))}</p>`);
}

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
  <span class="pin">${I.pin}</span>
  <div><div class="addr">${hl(titleCase(a.street), q)}</div><div class="sub">${hl(a.postal_city, q)}${a.city && a.city !== a.postal_city ? ` → ${hl(a.city, q)}` : ""}, ${a.state} ${esc(a.zip)}</div></div>
  <span class="aid">${hl(a.id, q)}</span><span class="arrow">${I.arrow}</span></li>`;
const go = (id) => { location.hash = "#/a/" + id; };

// ⌘K command palette
const cmdk = $("#cmdk"), cIn = $("#cmdk input"), cList = $("#cmdk-list");
let cItems = [], cSel = 0;
function cmdkRender() {
  const q = cIn.value.trim();
  const pages = [["#/", "nav_lookup"], ["#/changes", "nav_changes"], ["#/rules", "nav_rules"], ["#/audit", "nav_audit"]];
  cItems = q ? findAddr(q, 9).map((a) => ({ id: a.id, a })) : examplePicks().slice(0, 5).map((a) => ({ id: a.id, a }));
  const pg = q ? [] : pages.map(([h, k]) => ({ href: h, label: t(k) }));
  cItems = cItems.concat(pg);
  cSel = 0;
  let html = cItems.length ? `<li class="grp" role="presentation">${q ? t("g_results") : t("g_examples")}</li>` : `<li class="grp">${t("no_match")}</li>`;
  html += cItems.map((it, i) => it.a ? optHtml(it.a, i, cSel, q) : `${i === cItems.length - pg.length ? `<li class="grp" role="presentation">${t("g_pages")}</li>` : ""}<li class="opt" role="option" id="o-${i}" aria-selected="${i === cSel}" data-href="${it.href}"><span class="pin">${I.arrow}</span><div class="addr">${esc(it.label)}</div></li>`).join("");
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
function openCmdk() { if (cmdk.hidden) lastFocus = document.activeElement; cmdk.hidden = false; cmdk.classList.remove("closing"); cIn.value = ""; cmdkRender(); setTimeout(() => cIn.focus(), 10); }
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
function closeLayer(el) {
  const back = lastFocus; lastFocus = null;
  if (back && document.contains(back)) setTimeout(() => back.focus({ preventScroll: true }), 0);
  if (RM.matches) { el.hidden = true; return; }
  el.classList.add("closing");
  setTimeout(() => { el.hidden = true; el.classList.remove("closing"); }, 190);
}
cIn.addEventListener("input", cmdkRender);
cIn.addEventListener("keydown", (e) => {
  if (e.key === "ArrowDown") { e.preventDefault(); cmdkMove(1); }
  else if (e.key === "ArrowUp") { e.preventDefault(); cmdkMove(-1); }
  else if (e.key === "Enter") { e.preventDefault(); cmdkPick(cSel); }
});
cList.addEventListener("click", (e) => { const li = e.target.closest(".opt"); if (li) cmdkPick($$(".opt", cList).indexOf(li)); });
cList.addEventListener("mousemove", (e) => { const li = e.target.closest(".opt"); if (li) { const i = $$(".opt", cList).indexOf(li); if (i !== cSel) { cSel = i; $$(".opt", cList).forEach((x, k) => x.setAttribute("aria-selected", k === cSel)); } } });
cmdk.addEventListener("click", (e) => { if (e.target === cmdk) closeCmdk(); });
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
    pick((a) => a.city === "San Francisco" && yr(a) && yr(a) < 1979 && +a.units >= 10),
    pick((a) => a.city === "Los Angeles" && yr(a) && yr(a) < 1978 && a.postal_city !== a.city) || pick((a) => a.city === "Los Angeles" && yr(a) && yr(a) < 1978),
    pick((a) => a.postal_city === "Dorchester"),
    pick((a) => a.city === "Hoboken"),
    pick((a) => a.city === "Jersey City"),
    pick((a) => a.city === "Cambridge"),
    pick((a) => a.city === "Berkeley"),
    pick((a) => a.city === "San Diego"),
    pick((a) => a.city === "Newark"),
  ].filter(Boolean);
}
const RANK = { applies: 0, unknown: 1, not_yet_effective: 2, superseded: 3, pending: 4 };
function heroTitle() {
  let i = 0;
  const words = (str) => str.split(/\s+/).filter(Boolean).map((w) => `<span class="w" style="--i:${i++}">${esc(w)}</span>`).join(" ");
  return t("hero_title").split(/(\*[^*]+\*)/).filter(Boolean).map((part) => {
    if (part.startsWith("*")) return `<em>${words(part.slice(1, -1))}</em>`;
    return (/^\s/.test(part) ? " " : "") + words(part) + (/\s$/.test(part) ? " " : "");
  }).join("");
}
function viewHome() {
  const c = META.counts, ex = examplePicks();
  const cities = Object.keys(c.cities).filter((x) => x !== "(outside)").length;
  const chip = (a) => `<a class="chip" href="#/a/${a.id}">${I.pin}${esc(titleCase(a.street))}<span class="k">${esc(a.city || a.postal_city)}</span></a>`;
  const html = `
  <section class="hero">
    <h1>${heroTitle()}</h1>
    <div class="hero-stage">
      <form class="big-search rise" style="--d:560ms" role="search" autocomplete="off">
        <div class="box">
          <div class="field">
            <input id="hq" type="text" role="combobox" aria-expanded="false" aria-controls="hs" aria-autocomplete="list" spellcheck="false" aria-label="${esc(t("search_ph"))}">
            <div class="ph" aria-hidden="true"><span></span></div>
          </div>
          <button class="go" type="submit" aria-label="${esc(t("preview_open"))}">${I.arrow}</button>
        </div>
        <ul class="suggest" id="hs" role="listbox" hidden></ul>
      </form>
      <div class="chips rise" style="--d:760ms">${ex.slice(0, 3).map(chip).join("")}</div>
    </div>
  </section>
  <section class="live-demo reveal">
    <h2 class="sec-title">${esc(t("live_title"))}</h2>
    <a class="preview" id="pv" href="#/a/${ex[0]?.id}" aria-live="polite">
      <div class="preview-head swap"><div class="t"></div><div class="s"></div></div>
      <div class="preview-grid swap"></div>
    </a>
    <div class="hero-controls">
      <button class="circle-btn" type="button" data-pv="-1" aria-label="${esc(t("prev"))}">${I.left}</button>
      <button class="circle-btn" type="button" id="pv-pause" aria-label="${esc(t("pause"))}">${I.pause}</button>
      <button class="circle-btn" type="button" data-pv="1" aria-label="${esc(t("next"))}">${I.chev}</button>
    </div>
    <div class="dots">${ex.map((a, i) => `<button type="button" data-dot="${i}" aria-label="${esc(titleCase(a.street))}"></button>`).join("")}</div>
  </section>
  <p class="manifesto reveal">${esc(t("man_1"))} <span class="ic">${'<svg viewBox="0 0 24 24"><path d="M7 4h10M7 20h10M12 4v16"/></svg>'}</span> ${esc(t("man_2"))} <span class="ic">${'<svg viewBox="0 0 24 24"><rect x="4" y="5" width="16" height="15" rx="3"/><path d="M4 10h16"/></svg>'}</span> ${esc(t("man_3"))} <span class="ic u"><svg viewBox="0 0 24 24"><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1 .9-1 1.7M12 17v.01"/></svg></span> <span class="soft">“${esc(t("man_4"))}”</span> ${esc(t("man_5"))}</p>
  <section class="features">
    <div class="feature reveal">
      <div class="art"><div class="stackart">
        <div style="--k:0"><b>California</b><span>${t("state")}</span></div>
        <div style="--k:1"><b>Los Angeles County</b><span>${t("county")}</span></div>
        <div style="--k:2"><b>Los Angeles</b><span>${t("city")}</span></div></div></div>
      <div><h2>${esc(t("f1_t"))}</h2><p>${esc(t("f1"))}</p><a class="more" href="#/audit">${esc(t("f1_l"))} ${I.arrow}</a></div>
    </div>
    <div class="feature reveal">
      <div class="art navy"><div class="badgeart">${["applies", "unknown", "superseded", "not_yet_effective"].map((r, k) => `<span class="badge ${r}" style="--k:${k}">${esc(resLabel(r))}</span>`).join("")}</div></div>
      <div><h2>${esc(t("f2_t"))}</h2><p>${esc(t("f2"))}</p><a class="more" href="#/rules">${esc(t("f2_l"))} ${I.arrow}</a></div>
    </div>
    <div class="feature reveal">
      <div class="art"><div class="quoteart">… shall not … increase the gross rental rate <mark>more than 5 percent plus the percentage change in the cost of living, or 10 percent, whichever is lower</mark> …
        <div class="src">Cal. Civ. Code § 1947.12 <span class="verified">${I.check}${t("quote_ok")}</span></div></div></div>
      <div><h2>${esc(t("f3_t"))}</h2><p>${esc(t("f3"))}</p><a class="more" href="#/audit">${esc(t("f3_l"))} ${I.arrow}</a></div>
    </div>
  </section>
  <section class="stats">
    ${[[c.rules, "stat_rules"], [c.documents, "stat_sources"], [c.addresses, "stat_addr"], [cities, "stat_cities"]].map(([n, k], i) => `<div class="stat reveal" style="--i:${i}"><b data-count="${n}">${n}</b><span>${esc(t(k))}</span></div>`).join("")}
  </section>`;
  return swap(html, () => initHome(ex));
}
function initHome(ex) {
  // staggered pieces need indices
  // count-up stats when revealed
  $$(".stat b[data-count]").forEach((b) => {
    const st = b.closest(".stat");
    const obs = new MutationObserver(() => { if (st.classList.contains("in")) { countUp(b, +b.dataset.count); obs.disconnect(); } });
    obs.observe(st, { attributes: true, attributeFilter: ["class"] });
  });
  const form = $(".big-search"), input = $("#hq"), list = $("#hs"), ph = $(".ph span"), pv = $("#pv");
  let idx = 0, timer = null, paused = false, items = [], sel = 0;
  const setPh = (a, first) => {
    const text = `${t("try_q")} ‘${titleCase(a.street)}, ${a.postal_city}’`;
    if (first || RM.matches) { ph.textContent = text; return; }
    ph.classList.add("out");
    setTimeout(() => { ph.classList.remove("out"); ph.classList.add("pre"); ph.textContent = text; void ph.offsetWidth; ph.classList.remove("pre"); }, 380);
  };
  const paint = async (first = false) => {
    const a = ex[idx];
    setPh(a, first);
    $$(".dots button").forEach((b, i) => b.setAttribute("aria-current", i === idx));
    pv.href = "#/a/" + a.id;
    if (!first) pv.classList.add("switching");
    const [d] = await Promise.all([api(addrUrl(a.id)).catch(() => null), new Promise((r) => setTimeout(r, first || RM.matches ? 0 : 420))]);
    if (!d || ex[idx] !== a) return;
    $(".preview-head .t", pv).textContent = `${titleCase(a.street)}, ${d.jurisdiction.city || a.postal_city}`;
    $(".preview-head .s", pv).innerHTML = `${esc(t("answers_as_of"))} ${esc(fmtDate(d.as_of))} · <b style="color:var(--navy)">${esc(t("preview_open"))} →</b>`;
    $(".preview-grid", pv).innerHTML = d.categories.map((c, i) => {
      const top = [...c.enacted].sort((x, y) => (RANK[x.result] ?? 9) - (RANK[y.result] ?? 9))[0];
      const r = top ? top.result : c.no_rule_findings?.length ? "no_rule" : c.pending.length ? "pending" : null;
      const v = top ? (top.rule.key_value_display || top.rule.key_value || top.rule.title_display || top.rule.title) : (c.no_rule_findings?.[0]?.finding_display || c.no_rule_findings?.[0]?.finding || t("no_rule_found"));
      return `<div class="pv"><div class="c">${I.cat[c.id]}${esc(t("cat_" + c.id))}</div>${r ? badge(r, "anim", i) : `<span class="badge failed anim" style="--i:${i}">${esc(t("none_level"))}</span>`}<div class="v">${esc(v)}</div></div>`;
    }).join("");
    pv.classList.remove("switching");
  };
  const next = (d = 1) => { idx = (idx + d + ex.length) % ex.length; paint(); };
  const schedule = () => { clearInterval(timer); if (!paused && !RM.matches) timer = setInterval(() => { if (!document.hidden && !form.matches(":focus-within") && !pv.matches(":hover")) next(1); }, 5200); };
  cleanup.push(() => clearInterval(timer));
  paint(true); schedule();
  ex.slice(1).forEach((a) => api(addrUrl(a.id)).catch(() => {})); // warm cache
  $$("[data-pv]").forEach((b) => b.addEventListener("click", () => { next(+b.dataset.pv); schedule(); }));
  $$("[data-dot]").forEach((b) => b.addEventListener("click", () => { idx = +b.dataset.dot; paint(); schedule(); }));
  const pb = $("#pv-pause");
  pb.addEventListener("click", () => { paused = !paused; pb.innerHTML = paused ? I.play : I.pause; pb.setAttribute("aria-label", t(paused ? "play" : "pause")); schedule(); });
  // typing + suggestions
  const close = () => { list.hidden = true; input.setAttribute("aria-expanded", "false"); };
  const render = () => {
    const q = input.value.trim();
    form.classList.toggle("typing", !!input.value);
    if (!q) { close(); return; }
    items = findAddr(q); sel = 0;
    list.innerHTML = items.length ? items.map((a, i) => optHtml(a, i, sel, q)).join("") : `<li class="opt" aria-disabled="true"><span class="sub">${esc(t("no_match"))}</span></li>`;
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
  form.addEventListener("submit", (e) => { e.preventDefault(); const q = input.value.trim(); if (!q) return go(ex[idx].id); if (items[sel]) go(items[sel].id); });
}

// ------------------------------------------------------------------ address --
function srcBlock(r, extraMeta = "") {
  const src = r.source || {};
  return `<details class="src"><summary>${I.chev}${t("show_source")}</summary><div class="src-body">
      <blockquote class="quote">${esc(r.quoted_span)}</blockquote>
      <div class="src-meta">
        ${r.source_url ? `<a href="${esc(r.source_url)}" target="_blank" rel="noopener">${esc(host(r.source_url))} ${I.ext}</a>` : ""}
        <span>${t("retrieved")} ${esc(src.retrieved_at || r.retrieved_at || "n/a")}</span>
        <span class="mono">${esc(r.source_doc_id || "")}${r.span_doc_id && r.span_doc_id !== r.source_doc_id ? ` · ${t("quote_from")} ${esc(r.span_doc_id)}` : ""}</span>
        ${src.secondary ? `<span class="badge unknown">${t("secondary")}</span>` : ""}
        ${src.has_text ? `<a href="#" data-doc="${esc(r.span_doc_id || r.quoted_span_doc_id || r.source_doc_id)}" data-rule="${esc(r.team_rule_id || "")}">${t("open_doc")} →</a>` : ""}
        ${extraMeta}
      </div></div></details>`;
}
const firstSentence = (txt) => {
  const m = String(txt || "").match(/^(.{20,}?[.!?])(\s+[A-Z(“"]|$)/s);
  return m ? m[1] : String(txt || "");
};
function hintChip(item) {
  const r = item.rule;
  if (item.result === "unknown") return `<span class="hint unknown">${I.q}${t("depends_on")} ${esc(item.missing_fact || t("not_in_data"))}</span>`;
  if (item.result === "superseded" && item.superseded_by?.length) return `<span class="hint superseded">${I.layers}${t("overridden_by")} ${esc(item.superseded_by[0].title)}</span>`;
  if (item.result === "not_yet_effective") return `<span class="hint nye">${I.cal}${t("takes_effect")} ${esc(fmtDate(r.effective_date_norm || r.effective_date))}</span>`;
  return "";
}
function ruleBlock(item, i = 0) {
  const r = item.rule, res = item.result;
  const full = r.requirement_display || r.requirement || "";
  const short = firstSentence(full);
  let callouts = "";
  if (res === "unknown") callouts += `<div class="callout unknown">${I.q}<div><b>${t("missing_fact")}</b> ${esc(item.missing_fact || "")}. ${esc(item.explanation || "")}</div></div>`;
  if (res === "superseded" && item.superseded_by?.length) callouts += `<div class="callout superseded">${I.layers}<div><b>${t("superseded_by")}</b> ${item.superseded_by.map((x) => `${esc(x.title)} <span class="mono">${esc(x.id)}</span>`).join(", ")}. ${esc(r.interaction_display || r.interaction || "")}</div></div>`;
  if (item.overrides_here?.length) callouts += `<div class="callout superseded">${I.layers}<div>${t("overrides_here")} ${item.overrides_here.map((x) => `${esc(x.title)} <span class="mono">${esc(x.id)}</span>`).join(", ")}.</div></div>`;
  if (res === "not_yet_effective" && item.explanation) callouts += `<div class="callout nye">${I.cal}<div>${esc(item.explanation)}</div></div>`;
  if (item.conflict_flag) callouts += `<div class="callout conflict">${I.alert}<div><b>${t("conflict")}.</b> ${esc(r.conflict_note_display || r.conflict_note || "Possible conflict between rules or sources.")}</div></div>`;
  const why = ["applies", "superseded", "pending", "failed"].includes(res) && item.explanation ? `<p class="why"><b>${t("why")}</b> ${esc(item.explanation)}</p>` : "";
  const live = res === "applies" || res === "pending" ? " live" : "";
  const src = r.source || {};
  return `<article class="rule ${esc(res)}">
    <div class="rule-top">${badge(res, "anim" + live, i)}${item.conflict_flag ? `<span class="flag" title="${esc(t("conflict"))}">${I.alert}<span class="sr">${esc(t("conflict"))}</span></span>` : ""}<span class="lvl-tag">${esc(r.level === "state" ? r.jurisdiction : String(r.jurisdiction).replace(/, ..$/, ""))}</span></div>
    <h4 class="rule-title">${esc(r.title_display || r.title)}</h4>
    <p class="req">${esc(short)}</p>
    ${r.key_value ? `<p class="kfig">${esc(r.key_value_display || r.key_value)}</p>` : ""}
    ${hintChip(item)}
    <details class="src more"><summary>${I.chev}${t("why_source")}</summary><div class="src-body">
      ${short !== full ? `<p class="req-full">${esc(full)}</p>` : ""}
      ${why}${callouts}
      <blockquote class="quote">${esc(r.quoted_span)}</blockquote>
      <div class="src-meta">
        <span class="cite">${esc(r.citation)}</span>
        ${r.effective_date ? `<span>${t("effective")} ${esc(fmtDate(r.effective_date))}</span>` : ""}
        ${confMeter(r.confidence)}${verified(r.quote_check)}
      </div>
      <div class="src-meta">
        ${r.source_url ? `<a href="${esc(r.source_url)}" target="_blank" rel="noopener">${esc(host(r.source_url))} ${I.ext}</a>` : ""}
        <span>${t("retrieved")} ${esc(src.retrieved_at || r.retrieved_at || "n/a")}</span>
        ${src.secondary ? `<span class="badge unknown">${t("secondary")}</span>` : ""}
        ${src.has_text ? `<a href="#" data-doc="${esc(r.span_doc_id || r.quoted_span_doc_id || r.source_doc_id)}" data-rule="${esc(r.team_rule_id || "")}">${t("open_doc")} →</a>` : ""}
        <span class="mono">${esc(r.team_rule_id)} · ${esc(r.source_doc_id || "")}</span>
      </div>
    </div></details>
  </article>`;
}
function noRuleBlock(f) {
  return `<article class="rule"><div class="rule-top">${badge("no_rule")}<span class="lvl-tag">${esc(f.jurisdiction)}</span></div>
    <p class="req">${esc(firstSentence(f.finding_display || f.finding))}</p>
    ${f.quoted_span ? `<details class="src more"><summary>${I.chev}${t("why_source")}</summary><div class="src-body">
      <p class="req-full">${esc(f.finding_display || f.finding)}</p>
      <blockquote class="quote">${esc(f.quoted_span)}</blockquote>
      <div class="src-meta">${f.citation ? `<span class="cite">${esc(f.citation)}</span>` : ""}${confMeter(f.confidence)}${verified(f.quote_check)}</div>
      <div class="src-meta">${f.source_url ? `<a href="${esc(f.source_url)}" target="_blank" rel="noopener">${esc(host(f.source_url))} ${I.ext}</a>` : ""}<span>${t("retrieved")} ${esc(f.source?.retrieved_at || "n/a")}</span><span class="mono">${esc(f.finding_id || "")} · ${esc(f.quoted_span_doc_id || f.source_doc_id || "")}</span></div>
    </div></details>` : ""}
  </article>`;
}
function addressSkeleton() {
  const line = (w, h = 14, m = 10) => `<div class="sk" style="width:${w};height:${h}px;margin-top:${m}px"></div>`;
  return `<div class="crumbs">${line("140px", 36, 0)}</div><div class="addr-layout"><aside class="addr-side">
    ${line("40%", 12, 0)}${line("90%", 44)}${line("60%", 16)}${line("100%", 150, 22)}${line("100%", 120, 14)}</aside>
    <section>${line("50%", 36, 0)}${[0, 1, 2].map(() => line("100%", 190, 16)).join("")}</section></div>`;
}
function answersHTML(d) {
  let k = 0;
  const proposals = d.categories.flatMap((c) => [...(c.pending || []), ...(c.not_law || [])]);
  return `
      <div class="answer-head">
        <div><h2>${t("rules_here")}</h2></div>
        <div><span class="asof-tag" title="${esc(t("engine_" + d.engine))}">${I.cal}${t("answers_as_of")} ${esc(fmtDate(d.as_of))}</span></div>
      </div>
      <nav class="jump" aria-label="${t("summary")}">${d.categories.map((c) => `<a href="#h-${c.id}" data-jump="h-${c.id}">${I.cat[c.id]}<span>${esc(t("cat_" + c.id))}</span><span class="dots-mini">${(c.enacted.length ? c.enacted.map((i) => i.result) : c.no_rule_findings?.length ? ["superseded"] : []).slice(0, 4).map((r) => `<i class="dot ${r}"></i>`).join("")}</span></a>`).join("")}</nav>
      ${lang !== "en" ? `<p class="tr-note">${I.globe}${t("machine_tr")}</p>` : ""}
      <div class="cats">
        ${d.categories.map((c, ci) => `<section class="cat reveal" style="--i:${Math.min(ci, 3)}" aria-labelledby="h-${c.id}">
          <header class="cat-head"><span class="cat-ico">${I.cat[c.id]}</span><div><h3 id="h-${c.id}">${esc(t("q_" + c.id))}</h3><p class="q">${esc(t("cat_" + c.id))}</p></div>
            <div class="count">${c.enacted.map((i) => `<span class="dot ${i.result}" title="${esc(resLabel(i.result))}"></span>`).join("")}</div></header>
          <div class="rules-list">${c.enacted.length ? c.enacted.map((it) => ruleBlock(it, k++ % 4)).join("") : c.no_rule_findings?.length ? c.no_rule_findings.map(noRuleBlock).join("") : `<div class="norule">${I.info}<span>${t("no_rule_short")}${c.pending.length ? ` · ${c.pending.length} ${t("no_rule_pending")}` : ""}</span></div>`}</div>
        </section>`).join("")}
      </div>
      ${proposals.length ? `<section class="proposals reveal"><div class="inner">
        <header class="cat-head"><span class="cat-ico">${I.info}</span><div><h3>${t("proposals")}</h3><p class="q">${t("proposals_intro")}</p></div></header>
        <div class="rules-list">${proposals.map((i, n) => ruleBlock(i, n)).join("")}</div>
      </div></section>` : ""}`;
}

function viewNotFound(kind) {
  const ex = examplePicks().slice(0, 3);
  document.title = `${t("nf_title")} · Clause & Effect`;
  return swap(`<section class="notfound"><h1>${esc(t(kind === "address" ? "nf_title" : "nf_page"))}</h1><p>${esc(t("nf_body"))}</p>
    <button class="pill primary" type="button" data-cmdk>${I.search}${esc(t("search_ph"))}</button>
    <div class="chips">${ex.map((a) => `<a class="chip" href="#/a/${a.id}">${I.pin}${esc(titleCase(a.street))}<span class="k">${esc(a.city || a.postal_city)}</span></a>`).join("")}</div></section>`);
}
async function viewAddress(id) {
  if (ADDR.length && !ADDR.some((a) => a.id === id)) return viewNotFound("address");
  const url = addrUrl(id);
  let d = null;
  const p = api(url);
  const quick = await Promise.race([p.then((x) => x, () => null), new Promise((r) => setTimeout(() => r(null), 140))]);
  if (quick) d = quick;
  else { await swap(addressSkeleton()); progress(true); try { d = await p; } catch { progress(false); return viewNotFound("address"); } progress(false); }
  const a = d.address, j = d.jurisdiction;
  const fact = (k, label) => `<dt>${label}</dt><dd>${a[k] ? esc(a[k]) : `<span class="missing">${t("not_in_data")}</span>`}</dd>`;
  const methodLabel = t("m_" + j.method).startsWith("m_") ? j.method : t("m_" + j.method);
  const sumOrder = ["applies", "unknown", "superseded", "not_yet_effective", "pending"];
  const tiles = j.stack.map((s) => {
    const code = s.level === "state" ? s.code : s.level === "county" ? I.globe : I.building;
    return `<div class="trow"${s.note ? ` title="${esc(t(s.note))}"` : ""}><span class="tile ${s.level === "city" ? "navy" : ""}">${code}</span><div><div class="l1">${esc(t(s.name))}</div><div class="l2">${esc(t(s.level))}</div></div></div>`;
  }).join("");
  const factPill = (ico, label, v) => `<div class="fact ${v ? "" : "miss"}">${ico}<div><b>${v ? esc(v) : esc(t("not_in_data"))}</b><span>${esc(label)}</span></div></div>`;
  const html = `
  <div class="crumbs"><a class="pill line back" href="#/">${I.back}${t("back")}</a><button class="pill ghost" type="button" data-cmdk>${I.search}<span>${t("search_ph")}</span><kbd>/</kbd></button></div>
  <div class="addr-layout">
    <aside class="addr-side stagger" style="--step:70ms">
      <div class="addr-title"><h1>${esc(titleCase(a.street_address))}</h1><p>${esc(a.postal_city)}, ${esc(a.state)} ${esc(a.zip || "")}</p></div>
      <div class="tile-rows" aria-label="${t("jurisdiction")}">${tiles}</div>
      <div class="factrow">${factPill(I.cal, t("year_built"), a.year_built)}${factPill(I.building, t("units"), a.units)}</div>
      ${a.missing.includes("year_built") || a.missing.includes("units") ? `<p class="src-line">${esc(t("missing_note"))}</p>` : ""}
      <details class="src more side-more"><summary>${I.chev}${t("how_resolved")}</summary><div class="src-body">
        <div class="resolve-note"><b>${esc(methodLabel)}</b>${j.postal_differs ? ` · ${esc(t("mailing_to_legal").replace("{p}", a.postal_city).replace("{c}", j.city))}` : ""}</div>
        <div class="resolve-note muted" style="margin-top:6px;font-size:12.5px">${esc(j.note)}</div>
        <div class="src-meta"><span class="conf">${t("confidence")} <span class="meter"><i style="width:${pctOf(j.confidence)}%"></i></span> ${pctOf(j.confidence)}%</span>
        ${j.lat ? `<a href="https://www.openstreetmap.org/?mlat=${j.lat}&mlon=${j.lon}#map=17/${j.lat}/${j.lon}" target="_blank" rel="noopener">${(+j.lat).toFixed(4)}, ${(+j.lon).toFixed(4)} ${I.ext}</a>` : ""}</div>
        <dl class="facts" style="margin-top:12px"><dt>${t("use")}</dt><dd>${esc(a.use_description || "—")}</dd><dt>ID</dt><dd class="mono">${esc(a.address_id)}</dd><dt>${t("data_from")}</dt><dd>${esc(a.source_dataset || "")}</dd></dl>
      </div></details>
    </aside>
    <section>
      ${answersHTML(d)}
    </section>
  </div>`;
  const render = () => { main.innerHTML = html; armReveals(); $$(".addr-side.stagger > *").forEach((el, i) => el.style.setProperty("--i", i)); };
  if (quick) await swap(html, () => $$(".addr-side.stagger > *").forEach((el, i) => el.style.setProperty("--i", i)));
  else render();
  document.title = `${titleCase(a.street_address)}, ${a.postal_city} · Clause & Effect`;
}

// ------------------------------------------------------------------ modal --
function openModal(title, body) {
  const m = $("#modal");
  $("#modal-title").textContent = title;
  $(".modal-body", m).innerHTML = body;
  if (m.hidden) lastFocus = document.activeElement;
  m.classList.remove("closing"); m.hidden = false;
  $("[data-close]", m).focus();
}
function closeModal() { const m = $("#modal"); if (!m.hidden) closeLayer(m); }
async function openSource(doc, rule) {
  openModal(doc, `<div class="sk" style="height:18px;width:60%"></div><div class="sk" style="height:320px;margin-top:14px"></div>`);
  const d = await api(`/api/source/${doc}?rule_id=${encodeURIComponent(rule || "")}`);
  const txt = d.text;
  let body = esc(txt);
  if (d.highlight) body = esc(txt.slice(0, d.highlight[0])) + `<mark id="hlm">${esc(txt.slice(d.highlight[0], d.highlight[1]))}</mark>` + esc(txt.slice(d.highlight[1]));
  $("#modal-title").textContent = `${doc} · ${host(d.meta.url)}`;
  $(".modal-body").innerHTML = `<div class="src-meta" style="margin:0 0 12px">${d.meta.url ? `<a href="${esc(d.meta.url)}" target="_blank" rel="noopener">${esc(d.meta.url)} ${I.ext}</a>` : ""}<span>${t("retrieved")} ${esc(d.meta.retrieved_at)}</span>${d.meta.sha256 ? `<span class="mono">sha256 ${esc(d.meta.sha256.slice(0, 16))}…</span>` : ""}</div><div class="doc-text">${body}</div>`;
  $("#hlm")?.scrollIntoView({ block: "center", behavior: RM.matches ? "auto" : "smooth" });
}
document.addEventListener("click", (e) => {
  const j = e.target.closest("[data-jump]");
  if (j) { e.preventDefault(); const el = document.getElementById(j.dataset.jump)?.closest(".cat"); el?.scrollIntoView({ behavior: RM.matches ? "auto" : "smooth", block: "start" }); el?.classList.remove("flash"); void el?.offsetWidth; el?.classList.add("flash"); return; }
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
const RES_ORDER = ["applies", "unknown", "superseded", "not_yet_effective", "pending"];
function bars(counts, label) {
  const total = Object.values(counts || {}).reduce((a, b) => a + b, 0);
  return `<div class="rr-row"><div class="nm"><span class="mono">${esc(label)}</span><span class="muted">${total} ${t("addresses")}</span></div>
    <div class="bar">${RES_ORDER.filter((r) => counts?.[r]).map((r) => `<i class="${r}" style="width:${(counts[r] / total) * 100}%" title="${esc(resLabel(r))}: ${counts[r]}"></i>`).join("")}</div>
    <div class="cnt">${RES_ORDER.filter((r) => counts?.[r]).map((r) => `<span><span class="dot ${r}"></span> ${esc(resLabel(r))} ${counts[r]}</span>`).join("") || `<span>${t("none_level")}</span>`}</div></div>`;
}
function cityBars(obj) {
  const max = Math.max(1, ...Object.values(obj));
  return `<div class="citybars">${Object.entries(obj).map(([c, n]) => `<div><span>${esc(c)}</span><span class="b" style="width:${(n / max) * 100}%"></span><span class="n">${n}</span></div>`).join("")}</div>`;
}
function testCard(x, i) {
  const dated = x.type === "as_of" || x.type === "new_law";
  const chips = x.rules.map((r) => `<span class="rchip">${badge(r.status)}<span class="mono">${esc(r.team_rule_id)}</span> ${esc(r.title)}</span>`).join("") || `<span class="muted">${t("no_match_rule")}</span>`;
  const left = dated
    ? `<div><h3>${t("before")} <b>${esc(fmtDate(x.before_date))}</b></h3><div class="rr">${x.our_rule_ids.map((r) => bars(x.before[r], r)).join("")}</div></div>
       <div><h3>${t("after")} <b>${esc(fmtDate(x.after_date))}</b></h3><div class="rr">${x.our_rule_ids.map((r) => bars(x.after[r], r)).join("")}</div></div>`
    : `<div style="grid-column: span 2"><h3>${t("rule_reach")} <b>${esc(fmtDate(x.after_date))}</b></h3><div class="rr">${x.our_rule_ids.map((r) => bars(x.after[r], r)).join("") || `<p class="muted">${t("none_level")}</p>`}</div></div>`;
  const ids = x.affected_address_ids;
  return `<article class="test reveal" style="--i:${Math.min(i, 2)}" id="test-${esc(x.test_id)}">
    <div class="test-head"><div class="test-id">${esc(x.test_id)}</div><div><div class="type-tag">${esc(t("t_" + x.type))}</div><h2>${esc(x.title)}</h2></div></div>
    <div class="rchips">${chips}</div>
    <div class="ba">${left}
      <div><h3>${t("affected")}</h3><div class="big-num" data-count="${x.affected_count}">${x.affected_count}</div>
        ${x.conflict_flag_address_ids.length ? `<div style="margin-top:8px"><span class="badge conflict">${x.conflict_flag_address_ids.length} ${t("conflict_flags")}</span></div>` : ""}
        ${cityBars(x.affected_by_city)}</div>
    </div>
    <details class="src more" style="margin-top:14px"><summary>${I.chev}${t("details")}</summary><div class="src-body">
      <p class="test-foot"><b>${t("expected")}:</b> ${esc(x.expected_behavior)}</p>
      ${x.notes ? `<p class="test-foot">${esc(x.notes)}</p>` : ""}
      ${ids.length ? `<div class="idlist">${ids.map((id) => `<a class="chip" href="#/a/${id}">${id}</a>`).join("")}</div>` : ""}
    </div></details>
  </article>`;
}
async function viewChanges() {
  progress(true);
  const [tests, tl] = await Promise.all([api(`/api/changes?lang=${lang}`), api("/api/timeline")]);
  progress(false);
  const shown = tl.filter((e) => e.date >= "2024-01-01"), older = tl.filter((e) => e.date < "2024-01-01");
  const html = `
    <div class="page-head stagger"><span class="kicker">${t("changes_kicker")}</span><h1>${t("changes_title")}</h1><p>${t("changes_lead")}</p></div>
    <section class="tl-card reveal" aria-label="${t("timeline")}">
      <div class="tl-top"><div><div class="panel-title">${t("timeline")}</div><div class="tl-date"><span id="tl-date"></span></div></div><div class="tl-sum" id="tl-sum"></div></div>
      <div class="tl-track"><div class="tl-line"></div><div class="tl-fill" id="tl-fill"></div>
        ${shown.map((e) => `<button type="button" class="tl-ev ${pct(e.date) > 62 ? "r" : pct(e.date) < 18 ? "l" : ""}" data-date="${e.date}" style="left:${pct(e.date)}%" aria-label="${esc(fmtDate(e.date))}: ${esc(e.title)}"><span class="tip">${esc(fmtDate(e.date))} · ${esc(e.title)}</span></button>`).join("")}
        <input type="range" class="tl-range" id="tl-range" min="0" max="${TL_MAX}" value="${dayIdx(asOf)}" aria-label="${t("as_of")}">
        <div class="tl-years">${[2024, 2025, 2026, 2027, 2028].map((y) => `<span style="left:${pct(y + "-01-01")}%">${y}</span>`).join("")}</div>
      </div>
      <details class="src rail-more"><summary>${I.chev}${t("show_dates").replace("{n}", tl.length)}</summary><div class="src-body"><div class="rail" id="rail">
        ${older.length ? `<div class="rail-item past" data-date="${older[older.length - 1].date}"><span class="d">${esc(older[0].date.slice(0, 4))}–${esc(older[older.length - 1].date.slice(0, 4))}</span><div><div class="t">${older.length} ${t("earlier")}</div><div class="j">${older.map((e) => esc(e.title)).join(" · ")}</div></div><span></span></div>` : ""}
        ${shown.map((e) => `<div class="rail-item" data-date="${e.date}"><span class="d">${esc(fmtDate(e.date))}</span><div><div class="t">${esc(e.title)}</div><div class="j">${esc(e.jurisdiction)} · ${e.addresses} ${t("addresses")} · <span class="mono">${esc(e.id)}</span></div></div><span class="st"></span></div>`).join("")}
      </div></div></details>
    </section>
    <div class="tests">${tests.map(testCard).join("")}</div>`;
  await swap(html, () => {
    $$(".page-head.stagger > *").forEach((el, i) => el.style.setProperty("--i", i));
    const range = $("#tl-range"), dateEl = $("#tl-date");
    let last = null, raf = 0;
    const paint = (d, animateDate = true) => {
      if (d === last) return;
      const prev = last; last = d;
      const label = fmtDate(d);
      if (animateDate && prev && !RM.matches && dateEl.textContent !== label) {
        dateEl.classList.add("flip");
        setTimeout(() => { dateEl.textContent = label; dateEl.classList.remove("flip"); }, 120);
      } else dateEl.textContent = label;
      $("#tl-fill").style.transform = `scaleX(${pct(d) / 100})`;
      $$(".tl-ev").forEach((b) => {
        const was = b.classList.contains("past"), now = b.dataset.date <= d;
        b.classList.toggle("past", now);
        if (now && !was && prev) { b.classList.remove("just"); void b.offsetWidth; b.classList.add("just"); }
      });
      $$(".rail-item").forEach((r) => {
        const now = r.dataset.date <= d;
        r.classList.toggle("past", now);
        const st = $(".st", r);
        if (st) st.innerHTML = badge(now ? "in_force" : "not_yet_effective");
      });
      const live = tl.filter((e) => e.date <= d).length;
      $("#tl-sum").innerHTML = `<span class="badge in_force">${live} ${t("in_effect")}</span><span class="badge not_yet_effective">${tl.length - live} ${t("not_yet")}</span>`;
    };
    paint(asOf, false);
    range.addEventListener("input", () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(() => paint(idxDay(+range.value), false)); });
    const commit = (d) => { if (d === asOf) return; asOf = d; sessionStorage.setItem("asof", asOf); $("#asof").value = asOf; toast(t("toast_asof").replace("{d}", fmtDate(asOf))); };
    range.addEventListener("change", () => commit(idxDay(+range.value)));
    $$(".tl-ev").forEach((b) => b.addEventListener("click", () => {
      const target = dayIdx(b.dataset.date), from = +range.value;
      if (RM.matches) { range.value = target; paint(b.dataset.date); commit(b.dataset.date); return; }
      const t0 = performance.now(), dur = 700;
      const step = (now) => { const p = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - p, 5); const v = Math.round(from + (target - from) * e); range.value = v; paint(idxDay(v), false); if (p < 1) requestAnimationFrame(step); else { paint(b.dataset.date, false); commit(b.dataset.date); } };
      requestAnimationFrame(step);
    }));
  });
}

// ------------------------------------------------------------------ rules explorer --
let RF = { jur: "", cat: "", status: "", q: "", conflicts: false };
async function viewRules() {
  progress(true);
  const [rules, cov] = await Promise.all([api(`/api/rules?lang=${lang}`), api("/api/coverage")]);
  progress(false);
  const catLabel = Object.fromEntries(cov.categories.map((c) => [c.id, t("cat_" + c.id)]));
  const html = `
    <div class="page-head stagger"><span class="kicker">${t("rules_kicker")}</span><h1>${t("rules_title")}</h1><p>${t("rules_lead")}</p></div>
    <section class="kpis reveal">${[[rules.length, t("rules_n"), ""], [rules.filter((r) => r.status === "in_force").length, resLabel("in_force"), "in_force"], [rules.filter((r) => r.status === "not_yet_effective").length, resLabel("not_yet_effective"), "not_yet_effective"], [rules.filter((r) => r.status === "pending").length, resLabel("pending"), "pending"], [rules.filter((r) => r.conflict_flag).length, t("conflict"), "conflict"]].map(([n, l, c]) => `<div class="kpi"><b>${n}</b><span>${c ? `<i class="dot ${c === "conflict" ? "unknown" : c}"></i>` : ""}${esc(l)}</span></div>`).join("")}</section>
    <section class="card matrix-wrap reveal"><h2>${t("coverage")}</h2>
      <table class="matrix"><thead><tr><th><span class="sr">${t("jurisdiction")}</span></th>${cov.categories.map((c) => `<th>${esc(catLabel[c.id])}</th>`).join("")}</tr></thead>
      <tbody>${cov.jurisdictions.map((j) => `<tr class="${j.length === 2 ? "state" : "city"}"><th>${esc(j)}</th>${cov.categories.map((c) => {
        const cell = cov.cells[j]?.[c.id] || [];
        const nr = cov.no_rule_cells?.[j]?.[c.id];
        return `<td>${cell.length ? `<button type="button" data-j="${esc(j)}" data-c="${c.id}" title="${esc(cell.map((x) => x.id + ": " + x.title).join("\n"))}">${cell.map((x) => `<span class="dot ${x.status}"></span>`).join("")} ${cell.length}</button>` : nr ? `<span class="none finding" title="${esc(t("finding") + ": " + nr.finding + " (" + (nr.citation || "") + ")")}">∅<span class="sr"> ${t("finding")}</span></span>` : `<span class="none" title="${esc(t("none_level"))}">·<span class="sr"> ${t("none_level")}</span></span>`}</td>`;
      }).join("")}</tr>`).join("")}</tbody></table>
      <div class="legend" style="justify-content:flex-start;padding:12px 16px 8px;margin:0">${["in_force", "not_yet_effective", "pending", "failed"].map((s) => `<span><span class="dot ${s}"></span>${esc(resLabel(s))}</span>`).join("")}<span><span class="none finding">∅</span>${esc(t("legend_nr"))}</span><span>·&nbsp;${esc(t("none_level"))}</span></div>
    </section>
    <details class="card table-card reveal" id="rules-table"><summary class="table-sum">${I.chev}<span>${t("show_table").replace("{n}", rules.length)}</span></summary>
    <div style="padding:4px 18px 8px">
      <div class="filters">
        <select id="f-j" aria-label="${t("jurisdiction")}"><option value="">${t("jurisdiction")}: ${t("all")}</option>${cov.jurisdictions.map((j) => `<option>${esc(j)}</option>`).join("")}</select>
        <select id="f-c" aria-label="${t("category")}"><option value="">${t("category")}: ${t("all")}</option>${cov.categories.map((c) => `<option value="${c.id}">${esc(catLabel[c.id])}</option>`).join("")}</select>
        <select id="f-s" aria-label="${t("status")}"><option value="">${t("status")}: ${t("all")}</option>${["in_force", "not_yet_effective", "pending", "failed"].map((s) => `<option value="${s}">${esc(resLabel(s))}</option>`).join("")}</select>
        <input type="search" id="f-q" placeholder="${t("q_filter")}" aria-label="${t("q_filter")}">
        <label class="chk"><input type="checkbox" id="f-x"> ${t("only_conflicts")}</label>
      </div>
      <p class="count-note" id="rc"></p>
      <div class="table-wrap"><table class="rtable"><thead><tr><th>ID</th><th>${t("jurisdiction")}</th><th>${t("category")}</th><th>${t("col_rule")}</th><th>${t("key_value")}</th><th>${t("status")}</th><th>${t("effective")}</th><th>${t("confidence")}</th><th>${t("col_quote")}</th><th>${t("col_addresses")}</th></tr></thead><tbody id="rt"></tbody></table></div>
    </div></details>`;
  await swap(html, () => {
    $$(".page-head.stagger > *").forEach((el, i) => el.style.setProperty("--i", i));
    const draw = () => {
      const q = RF.q.toLowerCase();
      const list = rules.filter((r) => (!RF.jur || r.jurisdiction === RF.jur) && (!RF.cat || r.category === RF.cat) && (!RF.status || r.status === RF.status) && (!RF.conflicts || r.conflict_flag) && (!q || JSON.stringify([r.team_rule_id, r.title, r.requirement, r.citation, r.key_value]).toLowerCase().includes(q)));
      $("#rc").textContent = `${list.length} / ${rules.length} ${t("rules_n")}`;
      $("#rt").innerHTML = list.map((r) => `<tr class="clickable" data-rule="${esc(r.team_rule_id)}" tabindex="0">
        <td class="mono nw">${esc(r.team_rule_id)}</td><td class="nw">${esc(r.jurisdiction)}</td><td class="s">${esc(catLabel[r.category] || r.category)}</td>
        <td><div class="t">${esc(r.title_display || r.title)}</div><div class="s">${esc(r.citation)}</div>${r.conflict_flag ? `<span class="badge conflict" style="margin-top:6px">${t("conflict")}</span>` : ""}</td>
        <td>${esc(r.key_value_display || r.key_value || "—").replace(/\//g, "/<wbr>")}</td><td>${badge(r.status)}</td><td class="s nw">${esc(r.effective_date || "—")}</td>
        <td>${r.confidence != null ? pctOf(r.confidence) + "%" : "—"}</td><td>${r.quote_check?.status === "exact" || r.quote_check?.status === "normalized" ? `<span class="verified" title="${esc(r.quote_check.label)}">${I.check}</span>` : r.quote_check?.status === "not_found" ? `<span class="verified no" title="${esc(r.quote_check.label)}">${I.alert}</span>` : '<span class="s">n/a</span>'}</td><td>${r.addresses_count}</td></tr>`).join("") || `<tr><td colspan="10" class="empty">—</td></tr>`;
    };
    const sync = () => { $("#f-j").value = RF.jur; $("#f-c").value = RF.cat; $("#f-s").value = RF.status; $("#f-q").value = RF.q; $("#f-x").checked = RF.conflicts; draw(); };
    $("#f-j").onchange = (e) => { RF.jur = e.target.value; draw(); };
    $("#f-c").onchange = (e) => { RF.cat = e.target.value; draw(); };
    $("#f-s").onchange = (e) => { RF.status = e.target.value; draw(); };
    $("#f-q").oninput = (e) => { RF.q = e.target.value; draw(); };
    $("#f-x").onchange = (e) => { RF.conflicts = e.target.checked; draw(); };
    $$(".matrix button").forEach((b) => b.onclick = () => { RF.jur = b.dataset.j; RF.cat = b.dataset.c; sync(); $("#rules-table").open = true; $("#rules-table").scrollIntoView({ behavior: RM.matches ? "auto" : "smooth", block: "start" }); });
    const openRule = (id) => {
      const r = rules.find((x) => x.team_rule_id === id);
      const cc = r.coverage_conditions && typeof r.coverage_conditions === "object" ? JSON.stringify(r.coverage_conditions) : r.coverage_conditions;
      const fields = [[t("jurisdiction"), r.jurisdiction], ["Level", r.level], [t("category"), catLabel[r.category]], [t("status"), resLabel(r.status)], [t("effective"), r.effective_date], [t("key_value"), r.key_value_display || r.key_value], ["Coverage", cc], ["Exemptions", r.exemptions], ["Overrides / yields to", (r.overrides || []).join(", ")], ["Interaction", r.interaction_display || r.interaction], ["Citation", r.citation], [t("confidence"), r.confidence != null ? pctOf(r.confidence) + "%" : null], ["Conflict note", r.conflict_note_display || r.conflict_note], [t("sample_addresses"), r.addresses_count]];
      openModal(`${r.team_rule_id} · ${r.title_display || r.title}`, `<div class="rule-top">${badge(r.status)}${r.conflict_flag ? `<span class="badge conflict">${t("conflict")}</span>` : ""}${levelTag(r)}</div>
        <p class="req" style="margin:6px 0 18px;font-size:17px">${esc(r.requirement_display || r.requirement)}</p>
        <dl class="kv">${fields.filter((f) => f[1] != null && f[1] !== "").map((f) => `<dt>${esc(f[0])}</dt><dd>${esc(f[1])}</dd>`).join("")}</dl>
        <blockquote class="quote">${esc(r.quoted_span)}</blockquote>
        <div class="src-meta">${r.source_url ? `<a href="${esc(r.source_url)}" target="_blank" rel="noopener">${esc(host(r.source_url))} ${I.ext}</a>` : ""}<span>${t("retrieved")} ${esc(r.source?.retrieved_at || "n/a")}</span><span class="mono">${esc(r.source_doc_id || "")}</span>${verified(r.quote_check)}${r.source?.has_text ? `<a href="#" data-doc="${esc(r.span_doc_id || r.source_doc_id)}" data-rule="${esc(r.team_rule_id)}">${t("open_doc")} →</a>` : ""}</div>`);
    };
    $("#rt").addEventListener("click", (e) => { const tr = e.target.closest("tr[data-rule]"); if (tr && !e.target.closest("a")) openRule(tr.dataset.rule); });
    $("#rt").addEventListener("keydown", (e) => { const tr = e.target.closest("tr[data-rule]"); if (tr && e.key === "Enter") openRule(tr.dataset.rule); });
    sync();
  });
}

// ------------------------------------------------------------------ audit --
async function viewAudit() {
  progress(true);
  const d = await api("/api/audit", { fresh: true });
  progress(false);
  const ver = d.verification, vt = Object.values(ver).reduce((a, b) => a + b, 0);
  const steps = [
    ["Ingest", `${d.documents.length} official documents, each with URL and date.`],
    ["Extract", "AI turns each text into rule records with exact quotes."],
    ["Resolve", "US Census finds each address's legal city."],
    ["Apply", "Code checks every rule against each building."],
    ["Track", "Any date re-evaluated; changes listed per address."],
  ];
  const geoTotal = Object.values(d.geocoding).reduce((a, b) => a + b, 0);
  const verifiedN = (ver.exact || 0) + (ver.normalized || 0);
  const html = `
    <div class="page-head stagger"><span class="kicker">${t("audit_kicker")}</span><h1>${t("audit_title")}</h1><p>${t("audit_lead")}</p></div>
    <section class="kpis reveal">
      <div class="kpi"><b>${d.documents.length}</b><span>${esc(t("k_docs"))}</span></div>
      <div class="kpi"><b>${verifiedN}/${vt}</b><span><i class="dot applies"></i>${esc(t("k_quotes"))}</span></div>
      <div class="kpi"><b>${geoTotal}</b><span>${esc(t("k_geo"))}</span></div>
      <div class="kpi"><b>${d.audit_total}</b><span>${esc(t("k_log"))}</span></div>
    </section>
    <section class="pipeline stagger" style="--step:80ms;--start:200ms">${steps.map((x, i) => `<div class="step" style="--i:${i}"><div class="n">0${i + 1}</div><h2>${esc(x[0])}</h2><p>${esc(x[1])}</p></div>`).join("")}</section>
    <div class="stack-details">
    <details class="card table-card reveal"><summary class="table-sum">${I.chev}<span>${t("a_scale")}</span></summary><div class="apanel" style="padding-top:4px">
      <div class="scal">
        <div><h3>1 · Add sources</h3><p>Drop official text into the corpus with its URL and date. No code changes.</p></div>
        <div><h3>2 · Extract</h3><p>Same prompts and schema; quotes checked; results cached by prompt hash.</p></div>
        <div><h3>3 · Resolve</h3><p>The Census covers every US address; a new city needs only its place name.</p></div>
        <div><h3>4 · Re-run</h3><p>Coverage and change tracking re-run in seconds for any date.</p></div>
      </div></div></details>
    <details class="card table-card reveal"><summary class="table-sum">${I.chev}<span>${t("a_files")}</span></summary><div class="apanel" style="padding-top:4px"><div class="files">${Object.entries(d.sources).map(([n, src]) => `<div><span class="mono">${esc(n)}</span><span>${src.kind === "pipeline" ? `<span class="badge applies">pipeline</span>` : src.kind === "fixture" ? `<span class="badge unknown">fixture</span>` : `<span class="badge failed">missing</span>`} <span class="muted" style="font-size:12px">${esc(src.modified || "")}</span></span></div>`).join("")}</div>
      <p style="font-size:14px;margin-top:14px">${verifiedN} / ${vt} quoted spans found in the source text${ver.not_found ? `; <b style="color:var(--wrn)">${ver.not_found} not found (flagged)</b>` : ""}${ver.no_text ? `; ${ver.no_text} sources have no offline text` : ""}.</p></div></details>
    <details class="card table-card reveal"><summary class="table-sum">${I.chev}<span>${t("a_geo")}</span></summary><div class="apanel" style="padding-top:4px"><div class="files">${Object.entries(d.geocoding).map(([k, v]) => `<div><span>${esc(t("m_" + k).startsWith("m_") ? k : t("m_" + k))}</span><b>${v}</b></div>`).join("")}</div>
        <div class="table-wrap" style="max-height:320px;overflow:auto;margin-top:12px"><table class="rtable"><thead><tr><th>ID</th><th>Address</th><th>Mailing</th><th>Legal city</th><th>Method</th></tr></thead><tbody>${d.geocoding_notes.map((g) => `<tr><td class="mono"><a href="#/a/${g.id}">${g.id}</a></td><td>${esc(g.street)}</td><td>${esc(g.postal_city)}</td><td><b>${esc(g.city || "outside scope")}</b></td><td class="s" title="${esc(g.note)}">${esc(g.method)}</td></tr>`).join("")}</tbody></table></div></div></details>
    <details class="card table-card reveal"><summary class="table-sum">${I.chev}<span>${t("a_docs").replace("{n}", d.documents.length)}</span></summary><div class="apanel" style="padding-top:4px">
      <div class="table-wrap" style="max-height:440px;overflow:auto"><table class="rtable"><thead><tr><th>Doc</th><th>${t("jurisdiction")}</th><th>Source</th><th>Type</th><th>${t("retrieved")}</th><th>Rules</th><th><span class="sr">Text</span></th></tr></thead><tbody>
      ${d.documents.map((x) => `<tr><td class="mono">${esc(x.doc_id)}</td><td class="nw">${esc(x.jurisdictions)}</td><td style="max-width:380px;word-break:break-all"><a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.url.replace(/^https?:\/\/(www\.)?/, "").slice(0, 64))}</a></td><td class="s">${esc(x.source_type)}${x.capture !== "yes" ? ` · ${esc(x.capture)}` : ""}</td><td class="s nw">${esc(x.retrieved_at || "—")}</td><td>${x.rules_extracted || ""}</td><td>${x.text_available ? `<a href="#" data-doc="${esc(x.doc_id)}">text</a>` : `<span class="s">link only</span>`}</td></tr>`).join("")}
      </tbody></table></div></div></details>
    <details class="card table-card reveal"><summary class="table-sum">${I.chev}<span>${t("a_log").replace("{n}", d.audit_total)}</span></summary><div class="apanel" style="padding-top:4px">
      <div class="filters"><input type="search" id="lq" placeholder="${t("q_filter")}" aria-label="${t("q_filter")}"></div>
      <div class="log" id="log"></div></div></details>
    </div>`;
  await swap(html, () => {
    $$(".page-head.stagger > *").forEach((el, i) => el.style.setProperty("--i", i));
    const LOG_MAIN = ["ts", "stage", "doc_id", "chunk", "n_chunks", "model", "prompt_version", "cached", "n_rules", "doc_summary", "idx", "raw_chars", "validation_items", "prompt_hash"];
    const drawLog = (entries) => {
      $("#log").innerHTML = entries.map((e) => {
        const extra = Object.entries(e).filter(([k]) => !LOG_MAIN.includes(k));
        return `<details class="log-row"><summary>
          <span class="lt">${esc(e.ts || "")}</span><span class="ls">${esc(e.stage || e.event || "")}</span>
          <span class="ld">${esc(e.doc_id || "")}${e.n_chunks > 1 ? ` <span class="muted">${+e.chunk + 1}/${e.n_chunks}</span>` : ""}</span>
          <span class="lm">${esc(e.model || "")}${e.prompt_version ? ` · ${esc(e.prompt_version)}` : ""}${e.cached === true ? " · cached" : ""}</span>
          <span class="ln">${e.n_rules != null ? `${e.n_rules} rule${e.n_rules === 1 ? "" : "s"}` : ""}${e.validation_items != null ? ` · ${e.validation_items} checked` : ""}</span>
          <span class="lx">${esc(e.doc_summary || extra.map(([k, v]) => `${k}=${typeof v === "object" ? JSON.stringify(v) : v}`).join("  "))}</span></summary>
          <pre class="log-raw" data-idx="${e.idx}">${e.prompt_hash ? `prompt_hash ${esc(e.prompt_hash)}\n` : ""}${t("loading")}</pre></details>`;
      }).join("") || `<p class="muted">—</p>`;
      $$("#log details").forEach((dEl) => dEl.addEventListener("toggle", async () => {
        const pre = $("pre", dEl);
        if (!dEl.open || pre.dataset.loaded) return;
        const full = await api(`/api/audit/entry/${pre.dataset.idx}`);
        if (typeof full.raw_output === "string") { try { full.raw_output = JSON.parse(full.raw_output); } catch { /* keep raw */ } }
        pre.textContent = JSON.stringify(full, null, 2); pre.dataset.loaded = 1;
      }));
    };
    drawLog(d.audit);
    let tmr;
    $("#lq").addEventListener("input", (e) => { clearTimeout(tmr); tmr = setTimeout(async () => drawLog((await api(`/api/audit?q=${encodeURIComponent(e.target.value)}`, { fresh: true })).audit), 200); });
  });
}

// ------------------------------------------------------------------ router --
let routing = 0;
const ROUTES = new Map();
async function route({ keepScroll = false } = {}) {
  const my = ++routing;
  cleanup.forEach((f) => f()); cleanup = [];
  const [view, arg] = location.hash.replace(/^#\/?/, "").split("/");
  const name = view === "a" ? "lookup" : view || "lookup";
  syncHeader(name);
  closeModal(); closeCmdk();
  const titles = { changes: "nav_changes", rules: "nav_rules", audit: "nav_audit" };
  document.title = titles[view] ? `${t(titles[view])} · Clause & Effect` : `Clause & Effect · ${t("tagline_short")}`;
  const y = scrollY;
  try {
    if (ROUTES.has(view)) { await ROUTES.get(view)(main, arg ? decodeURIComponent(arg) : undefined); armReveals(); }
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
  if (keepScroll) scrollTo({ top: y, behavior: "instant" }); else scrollTo({ top: 0, behavior: "instant" });
  if (!firstRoute) main.focus({ preventScroll: true });
  firstRoute = false;
}
let firstRoute = true;
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
    const item = { result: e.result, explanation: e.explanation, conflict_flag: !!e.conflict_flag, missing_fact: e.missing_fact, superseded_by: e.superseded_by, overrides_here: e.overrides_here, rule };
    const c = byId[rule.category] || byId[e.category];
    if (!c) continue;
    (e.result === "pending" ? c.pending : e.result === "failed" ? c.not_law : c.enacted).push(item);
  }
  for (const f of res?.no_rule_findings || []) byId[f.category]?.no_rule_findings.push(f);
  return { as_of: res?.as_of || asOf, engine: res?.engine || "live", categories: cats };
}
window.CE = Object.freeze({
  version: 1,
  /** Render the answer cards (as-of tag, category chips, cards, pending/failed panel) into `container`. */
  renderAnswers(container, lookupResult) {
    const el = typeof container === "string" ? $(container) : container;
    el.innerHTML = answersHTML(normalizeLookup(lookupResult));
    armReveals(el);
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
  badge: (result) => badge(result),
  icons: I,
  escape: esc,
  openModal,
  openSearch: () => openCmdk(),
  fmtDate,
});

(async function init() {
  [META, ADDR] = await Promise.all([api("/api/meta"), api("/api/addresses")]);
  if (lang === "es") ES = await api("/api/i18n/es").catch(() => ({}));
  await route();
  document.dispatchEvent(new CustomEvent("ce:ready", { detail: { version: 1 } }));
})();
