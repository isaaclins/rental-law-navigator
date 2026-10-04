// Clause & Effect · Rental Housing Law Navigator. Build-free single-page frontend.
// Views: #/ (home), #/a/<id> (address), #/changes, #/rules, #/audit. Design language: web/DESIGN.md

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const main = $("#main");
const RM = matchMedia("(prefers-reduced-motion: reduce)");

// ------------------------------------------------------------------ i18n --
const EN = {
  skip: "Skip to content", strip: "Housing law from official sources, quoted word for word. Not legal advice.", strip_more: "About this information", strip_s: "Official sources, quoted. Not legal advice.", nla: "Not legal advice.", nla_more: "About this information", cancel: "Cancel",
  nla_body: "Information about public law, drawn from official sources and shown with citations. It is not a compliance check and not legal advice. For your situation, contact a tenant organisation, housing agency or attorney.",
  nla_title: "About this information",
  nav_more: "More", nav_lookup: "Lookup", nav_changes: "Changes", nav_rules: "Rules", nav_audit: "Sources",
  t_lookup: "Address lookup", t_changes: "What's changing", t_rules: "Rules", t_audit: "Sources and method",
  as_of: "As of", asof_aria: "Answers as of", asof_reset: "Back to {d}",
  footer_body: "Plain-language summaries of official texts retrieved Oct 1, 2026. They can be incomplete or wrong, so always check the cited source.",
  footer_meta: "Public data only. No customer, resident or pricing data.",
  hero_title: "Rental law, for your address.",
  hero_lead: "Rent limits, eviction rules, deposits, fees and screening, each quoted from the law. And what is about to change.",
  hero_meta: "California, New Jersey and Massachusetts · 10 cities",
  search_ph: "Address, city or ZIP", search_go: "Look up", examples: "Examples",
  f1_t: "The mailing city is not always the legal city.", f1: "A Van Nuys address is in the City of Los Angeles. We ask the US Census which city each address is really in.", f1_l: "How addresses are resolved",
  f2_t: "Unknown, never a guess.", f2: "Building age, unit count and dates are checked in code. When the data can't tell, the answer says so.", f2_l: "Browse all rules",
  f3_t: "Every answer quotes the law.", f3: "Each rule links to the exact sentence in the official text, with the date it was retrieved.", f3_l: "Sources and method",
  // home (look 3)
  hero_nla: "Official sources, quoted word for word.", hero_a: "Rental law,", hero_b: "for your address.", search_try: "Try ‘3515 Fillmore St’ or 07030",
  car_aria: "Buildings in the covered cities", car_prev: "Previous building", car_next: "Next building", car_pause: "Pause", car_play: "Play",
  st_html: "Clause & Effect {chip0} reads {chip1} the housing law of {s} states and {c} cities {chip2}, answers for {a} sample addresses, and quotes {chip3} each of its {r} rules word for word {chip5} from {d} official sources. When the data can’t tell, it says {chip4} unknown instead of guessing.",
  b_check_l: "Check a rent increase", b_cmp_l: "Compare two addresses", b_chg_l: "See what's changing", b_src_l: "See how it works", hero_chip: "{c} cities in {s} states", hero_chip_b: "{n} rules",
  bs_addr: "Address", bs_asof: "Answers as of",
  map_h: "Pick a city", map_aria: "Map of the covered cities", city_addr: "sample addresses", city_rules: "city rules", state_rules: "{s} rules",
  city_rent: "Rent increases at {a}:", city_go: "Open {a}", city_none: "No sample address here yet.", city_rules_go: "See the {c} rules", city_state_only: "State rules only",
  st_addr: "addresses resolved to their legal city", st_cities: "cities in California, New Jersey and Massachusetts", st_rules: "rules, each with a verbatim quote", st_docs: "official source documents",
  b_h: "Everything the law says about one address.", b_p: "One plain answer per topic. The exact sentence from the law is one tap away.", b_go: "Try an example",
  b_check: "Check a rent increase", b_check_p: "Enter the old and new rent. See whether it is within the cap, by how much, and which law decides.",
  b_cmp: "Compare two addresses", b_cmp_p: "Two places side by side, topic by topic, before you sign a lease.",
  b_chg: "What's changing", b_chg_p: "Laws taking effect, and the addresses each one reaches.",
  b_src: "Sources and method", b_src_p: "{n} official texts. Every quote is checked word for word.",
  b_rules: "All rules", b_rules_p: "Every rule by place and topic, with open questions flagged.",
  // address (look 3)
  f_built: "Built", f_units: "Units", f_city: "Legal city", built_l: "built {y}", units_l: "{n} units", f_rules: "Rules in {n} topics", f_quotes: "Quotes checked",
  cu_h: "Coming up here", cu_none: "No new law on file for this address.", cu_all: "All changes", nl_n: "bills and proposals that are not law", f_na: "Unknown", check_cta: "Check a rent increase",
  ls_title: "Looking up this address", ls_1: "Finding the legal city", ls_2: "Applying the rules", ls_3: "Checking the quotes",
  ls_1d: "Found: {c}", ls_2d: "{n} rules apply on {d}", ls_3d: "{a} of {b} quotes found word for word", ls_3n: "Quotes linked to their sources",
  r_applies: "Applies", r_unknown: "Unknown", r_superseded: "Replaced", r_not_yet_effective: "Not yet in effect", r_pending: "Pending bill", r_failed: "Failed", r_in_force: "In force", r_no_rule: "No rule", r_exempt: "Exempt",
  how_resolved: "How we found this address", confidence: "Confidence", method: "Method", note_en: "Geocoder note (English)",
  year_built: "Year built", units: "Units", use: "Use", not_in_data: "not in data", data_from: "Building data",
  built_y: "Built {y}", units_n: "{n} units", units_min: "{n}+ units (from the use code)", year_unknown: "Year built unknown", units_unknown: "Unit count unknown",
  mailing_legal: "Mailing city {p}, legally in {c}.", county: "County",
  rules_here: "Rules at this address", answers_note: "As of {d}. Not legal advice.",
  machine_tr: "Machine-translated. Legal text stays in English.",
  also_here: "Also at this address", r_no_limit: "No limit",
  also_apply1: "1 more rule applies", also_applyN: "{n} more rules apply", also_unk1: "1 more depends on missing data", also_unkN: "{n} more depend on missing data", also_nye1: "1 more starts later", also_nyeN: "{n} more start later", also_rep1: "1 state rule replaced", also_repN: "{n} state rules replaced",
  needs: "Needs", needs_co: "The exact certificate-of-occupancy date. The data only has the year ({y}).",
  depends_on: "It depends on {f}", starts: "Starts {d}", changes_on: "Changes {d}", fig_from: "Figure shown applies from {d}",
  no_rule_short: "No state or city rule found.", exempt_line: "{t} exists, but this building is exempt.",
  exempt_body: "{t} ({c}) is in force here, but it does not cover this building:",
  sec_why: "Why it applies", sec_why_unknown: "Why it's unknown", sec_why_not: "Why it doesn't apply", sec_changes: "Changes", sec_review: "Open question",
  read_full: "Read in full text", doc_all: "Show the whole document", src_missing: "The full text of this source is not stored here. Use the source link instead.", src_error: "The source could not be loaded. Please try again in a moment.", low_conf: "Low extraction confidence ({n}%): check the source", quote_ok: "Quote found in source", quote_bad: "Quote not found in source", retrieved: "Retrieved {d}", secondary: "Secondary source",
  yields_to: "Yields to {r}, which governs here.",
  w_statewide: "Statewide rule: covers every rental in {s}.", w_city: "Covers rentals in {c}; no building-age or size conditions.",
  w_local_not_yet: "The stricter local rule is not in effect on this date, so this rule governs.",
  w_pending: "A bill, not law. It would cover this address if enacted.", w_failed: "The proposal failed or was withdrawn. It is not law.",
  ch_since: "In effect since {d}.", ch_starts: "Takes effect {d}.", ch_effective: "Effective {d}.",
  ch_version: "On {a}, an earlier version applied. The text and figure shown apply from {b}.",
  ch_figure_end: "The figure shown covers the period ending {d}. The law continues; check the current figure.",
  not_law: "Not law yet", not_law_note: "Pending bills and failed proposals. None of these is in force.",
  // changes
  ch_h: "What's changing for you, and when?", ch_lead: "New laws by date, in plain words. Pick your place.", ch_next: "In the next 12 months", ch_later: "Later", ch_recent: "In the last 12 months", ch_earlier: "Earlier",
  ch_none: "No dated change here.", ch_reach: "Reaches {n} of our sample addresses.", ch_big: "The bigger picture", ch_big_s: "How protections spread across the 10 cities, and a slider to move through time.",
  changes_title: "What's changing", changes_lead: "New laws by date, in plain words. Pick your place; open a change to read it.", ch_place: "Place", ch_see: "See answers on {d}",
  in_effect: "{n} dated laws in force", upcoming: "{n} upcoming", addresses_n: "{n} addresses", earlier: "{n} earlier rules, in force before 2024",
  in_force_on: "In force", not_yet: "Upcoming", timeline_aria: "Date",
  // rules
  rp_h: "What are the rules where you live?", rp_lead: "Pick your place. Each answer comes from the law there.", rp_in: "Rules in {p}", rp_all: "Compare all places", pc_state: "Statewide",
  rules_title: "Rules", rules_lead: "Every rule we track, by place and topic.", rules_n: "{n} rules", rules_sentence: "{all}: {a}, {b}, {c}, {e}; {d}.", n_fail1: "1 failed proposal", n_failN: "{n} failed proposals", n_force1: "1 in force", n_forceN: "{n} in force", n_later1: "1 not yet in effect", n_laterN: "{n} not yet in effect", n_rule1: "1 rule", n_ruleN: "{n} rules", n_bill1: "1 pending bill", n_billN: "{n} pending bills", n_open1: "1 has an open question", n_openN: "{n} have an open question",
  coverage: "Coverage by place and topic", none_level: "No rule", matrix_note: "Number of rules per place and topic. – means no rule; an underlined – opens the official statement that there is none.", legend_nr: "Checked: no rule at this level",
  show_table: "All {n} rules", all: "All", only_conflicts: "Only open questions", category: "Topic", status: "Status", jurisdiction: "Place",
  col_rule: "Rule", col_quote: "Quote", col_addresses: "Addresses", key_value: "Key figure", effective: "Effective",
  no_rules_match: "No rules match these filters.", clear_filters: "Clear filters", conflict: "Open question",
  f_level: "Level", f_coverage: "Coverage", f_exemptions: "Exemptions", f_overrides: "Overrides / yields to", f_interaction: "Interaction", f_citation: "Citation", f_conflict_note: "Open question", sample_addresses: "Addresses covered",
  state: "State", city: "City", q_filter: "Filter",
  // audit
  src_h: "Every answer comes from the law itself.", src_lead: "Official texts, quoted word for word, with the date we read them. Here is where each one comes from.",
  f3_docs: "source texts, {n} of them official", f3_quotes: "quotes checked word for word in the source", f3_when: "when we read them",
  how_h: "How it works", how_read: "Read the law", how_read_d: "We collect {n} texts, {o} from official sites, and turn each into plain rules, keeping the exact sentence.",
  how_check: "Check every quote", how_check_d: "Code searches each of the {q} quotes in the official text, word for word. A miss is flagged.",
  how_apply: "Apply to your building", how_apply_d: "Fixed rules decide what covers your building on any date. No guessing: unknown stays unknown.",
  srcs_h: "The sources", srcs_find: "Find a source, a city or a website", srcs_none: "No source matches.", srcs_n: "{n} sources · {k} with a checked quote", state_law: "{s} state law", page_on: "Page on {h}",
  sb_checked: "Quote checked", sb_text: "Text on file", sb_link: "Link only", sb_secondary: "secondary source",
  rev_h: "For reviewers", rev_s: "Flags, confidence, change checks, files and the extraction log", rev_flags: "Flagged for review ({n})", rev_ask: "Audit log: every Ask answer, its sources and what the checks removed",
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
  g_examples: "Examples", g_results: "Addresses", g_pages: "Pages", no_match: "No matching address", no_match_q: "No address matches “{q}”", no_match_hint: "Try a street and number, a city or a ZIP code in California, New Jersey or Massachusetts.",
  nf_title: "We couldn't find that address", nf_page: "Page not found", nf_body: "Search for an address, or start from an example.", tagline_short: "Which rules apply here?",
  error: "Something went wrong loading this view.", loading: "Loading…", details: "Details",
  fixture: "Preview data: answers come from schema-identical fixture records.",
  pq_rent_increase_limits: "Can they raise my rent?", pq_just_cause_eviction: "Can they make me move out?", pq_security_deposits: "How big can the deposit be?",
  pq_application_screening_fees: "What can they charge me to apply?", pq_screening_restrictions: "Can they turn me down for a voucher?", pq_algorithmic_rent_setting: "Can a computer set my rent?",
  why_city: "{p} has its own law for this, and it covers your building.", why_state: "A {p} law covers your building.", why_replaces: "It is stricter than the state rule, so it wins.",
  why_later: "A new law starts on {d}.", why_nolimit: "{p} law sets no limit here.", why_exempt: "There is a rule, but your building does not fall under it.", why_none: "We found no state or city law on this.",
  why_unknown: "It depends on {f}. Public records don't say.", why_unknown_other: "It depends on a fact we can't see in public records.", why_place: "Whether it covers you depends on {f}.", why_else: "If it doesn't, state law: {o}", why_new: "Your building is too new for the cap (built {y}).",
  also_rules: "Also here", tr_note: "Translated by machine. The law's words stay in English.", why_ask: "Answer one question and you'll know.", pf_year: "when your building was built", pf_units: "how many homes are in your building", pf_owner: "whether the owner lives there", pf_tenancy: "how long you have lived there", pf_other: "a fact we can't see in public records",
  ask_year: "Was your building built before {y}?", ask_units: "Does your building have {n} or more homes?", ask_owner: "Does the owner live in the building?",
  ask_other: "Ask your landlord or your city's housing office. They can tell you.", ask_unsure_year: "Ask your manager or check your lease.", ask_unsure_units: "Count the mailboxes or doorbells, or ask your landlord.",
  l1_unknown: "We can't tell yet.", l1_later: "Not yet. Starts {d}.", l1_exempt_rent: "No limit for your building.", l1_exempt: "This rule doesn't cover your building.",
  auto_sum: "Auto-summary: the short answer above was written by software from this law and checked by code, not yet by a person.",
  auto_sum_review: "Auto-summary, flagged for review: a person should still check the short answer above against this law.",
  l1_none_rent: "We found no rent cap here.", l1_none: "No special rule here.", law_more: "More details", l3_ok: "Word for word on {h} · Retrieved {d}",
  flag_conflict: "These laws may conflict: a court or the state may decide which wins.", flag_unsure: "Double-check this one: our reading of this law is uncertain.", flag_why: "Why?",
  conf_l: "Our confidence in this reading: {n}%.", note_unread: "We couldn't read this law's own text yet, so the details may be off.", flag_l: "Flagged for review: {n}", flag_none: "No conflict flagged.", official_site: "Official site", src_secondary: "Source: {h} (summary, not the official text)", checked_on: "Quote found word for word in this source (retrieved {d}).",
  sd_ok: "There is a limit or protection", sd_check: "Double-check this one", sd_dep: "Depends on your building", sd_ask: "We need one answer from you", sd_none: "No limit or rule", sd_later: "Starts later",
  kw_pick: "Pick your city to see: {q}", kw_ex: "Example: {a}", ex_banner: "Example address in {q}. Your building may differ.", ex_enter: "Enter your street",
  calc_rent: "My rent now", calc_max: "Most they can ask: {v} a month.", calc_upto: "Up to {v} ({p}%), likely less.", calc_dep: "Most deposit they can ask: {v}.",
  ask_when: "When was your building built?", ask_b_before: "Before {y}", ask_b_after: "{y} or later", ask_year_f: "If it was built during {y}, choose Not sure.",
  ask_units2: "How many homes are in your building?", ask_5plus: "5 or more", ask_pre: "If yes: {y}. If no: {n}.", open_page: "Open the official page",
  ans_upd1: "1 answer updated", ans_updN: "{n} answers updated", said: "You said: {s}", said_year_built: "built {v}", said_units: "{v} homes", said_owner_occupied: "owner lives there: {v}", change: "Change",
  ask_unsure_owner: "Ask your landlord whether they live in the building.",
  ask_fail: "That didn't work. Please try again.", yes: "Yes", no: "No", unsure: "Not sure", law_show: "Show me the law",
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
// a Spanish browser starts in Spanish; the EN/ES switch remembers the choice
let lang = localStorage.getItem("lang") || (/^es\b/i.test(navigator.language || "") ? "es" : "en");
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
// sentence splitting lives in sentences.js (unit-tested in tests/test_sentences.py, #163)
const splitSentences = (s) => (window.CE_TEXT?.splitSentences || ((x) => [String(x || "")]))(s);
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
function swap(html, after, { quick = false } = {}) {
  main.innerHTML = html; after?.();
  if (!RM.matches) { main.classList.remove("fade-in", "fade-quick"); void main.offsetWidth; main.classList.add(quick ? "fade-quick" : "fade-in"); }
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
  placeInd();
  $("#asof").value = asOf;
  const changed = asOf !== DEFAULT_AS_OF;
  $("#asof-label").textContent = asofLabel();
  $("#asof-ctl").classList.toggle("changed", changed);
  document.documentElement.classList.toggle("asof-changed", changed);
  $("#asof").setAttribute("aria-label", t("asof_aria"));
  const rs = $("#asof-reset");
  rs.classList.toggle("off", !changed); // keeps its space: the tools never jump (#134)
  rs.tabIndex = changed ? 0 : -1;
  rs.setAttribute("aria-hidden", String(!changed));
  rs.textContent = "×";
  rs.setAttribute("aria-label", tf("asof_reset", { d: fmtDate(DEFAULT_AS_OF) }));
  rs.title = tf("asof_reset", { d: fmtDate(DEFAULT_AS_OF) });
  $$(".seg button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.lang === lang));
  document.documentElement.lang = lang;
  $$("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  $("#cmdk input").placeholder = t("search_ph");
  $(".search-trigger").setAttribute("aria-label", t("search_ph"));
  fitSoon();
  const fb = $("#fixture-banner");
  fb.hidden = META?.sources?.["rules.json"]?.kind !== "fixture";
  fb.textContent = t("fixture");
}
// The black pill under the active nav item slides from tab to tab (tabs are links; the pill is decoration only).
const tabInd = (() => { const el = document.createElement("span"); el.className = "tab-ind still"; el.setAttribute("aria-hidden", "true"); $(".tabs").prepend(el); return el; })();
function placeInd() {
  const a = $('.tabs a[aria-current="page"]'), bar = $(".tabs");
  const ra = a?.getBoundingClientRect(), rb = bar.getBoundingClientRect();
  if (!a || !ra.width) { tabInd.classList.remove("on"); tabInd.dataset.w = 0; return; }
  if (!+tabInd.dataset.w) tabInd.classList.add("still"); // never grow from width 0
  tabInd.style.setProperty("--x", ra.left - rb.left - bar.clientLeft + "px");
  tabInd.style.setProperty("--w", ra.width + "px");
  tabInd.dataset.w = ra.width;
  tabInd.classList.add("on");
  if (tabInd.classList.contains("still")) requestAnimationFrame(() => requestAnimationFrame(() => tabInd.classList.remove("still")));
}
new MutationObserver(() => {
  const tabs = $(".tabs"), more = $(".tab-more", tabs);
  if (more && tabs.lastElementChild !== more) tabs.append(more); // links added later (My properties, Ask) stay before "More"
  placeInd(); if (typeof fitSoon === "function") fitSoon();
}).observe($(".tabs"), { childList: true });
new ResizeObserver(() => { tabInd.classList.add("still"); placeInd(); }).observe($(".tabs"));
addEventListener("resize", () => { tabInd.classList.add("still"); placeInd(); }, { passive: true });
document.fonts?.ready.then(() => { tabInd.classList.add("still"); placeInd(); });
addEventListener("scroll", () => document.documentElement.classList.toggle("scrolled", scrollY > 8), { passive: true });
if (window.visualViewport) {
  const kb = () => { const v = visualViewport, h = Math.max(0, Math.round(innerHeight - v.height - v.offsetTop)); document.documentElement.style.setProperty("--kb", h + "px"); document.documentElement.classList.toggle("kb-open", h > 80); };
  visualViewport.addEventListener("resize", kb); visualViewport.addEventListener("scroll", kb); kb();
}
// Header fit (container-aware): when the row is too tight, collapse step by step: the as-of pill becomes an icon,
// the language switch shows one button, then nav items move into "More" from the end. Below 900 px the nav is
// the bottom tab bar (mobile.css) and nothing collapses here.
const moreBox = (() => {
  const box = document.createElement("div"); box.className = "tab-more";
  box.innerHTML = `<button type="button" class="tab-more-b" aria-expanded="false" aria-haspopup="true"><span data-i18n="nav_more">More</span><svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="m7 10 5 5 5-5"/></svg></button><div class="tab-pop" hidden></div>`;
  $(".tabs").append(box);
  const b = $("button", box), pop = $(".tab-pop", box);
  const set = (on) => { pop.hidden = !on; b.setAttribute("aria-expanded", String(on)); };
  b.addEventListener("click", (e) => { e.stopPropagation(); set(pop.hidden); });
  document.addEventListener("click", (e) => { if (!box.contains(e.target)) set(false); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") set(false); });
  pop.addEventListener("click", (e) => { if (e.target.closest("a")) set(false); });
  return box;
})();
function fitHeader() {
  const html = document.documentElement, tabs = $(".tabs"), inner = $(".nav-inner");
  html.classList.remove("hf-1", "hf-2");
  const links = $$(":scope > a", tabs);
  links.forEach((a) => a.classList.remove("in-more"));
  const pop = $(".tab-pop", moreBox); pop.innerHTML = ""; moreBox.hidden = true;
  if (getComputedStyle(tabs).position === "fixed") { placeInd(); return; }
  const tight = () => {
    const kids = [...inner.children].filter((k) => k.offsetParent !== null);
    let need = 0; kids.forEach((k) => { need += k.getBoundingClientRect().width; });
    need += parseFloat(getComputedStyle(inner).columnGap || 24) * (kids.length - 1) + 16;
    const cs = getComputedStyle(inner);
    return need > inner.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
  };
  if (tight()) html.classList.add("hf-1");
  if (tight()) html.classList.add("hf-2");
  if (tight()) {
    moreBox.hidden = false;
    for (let i = links.length - 1; i > 0 && tight(); i--) {
      if (links[i].getAttribute("aria-current") === "page" && i > 1) { continue; }
      links[i].classList.add("in-more");
      pop.prepend(links[i].cloneNode(true));
    }
    $$("a", pop).forEach((a) => { a.removeAttribute("data-tour"); a.classList.remove("in-more"); });
    moreBox.classList.toggle("has-current", !!$('a[aria-current="page"]', pop));
  }
  placeInd();
}
const fitSoon = () => { cancelAnimationFrame(fitSoon.r); fitSoon.r = requestAnimationFrame(fitHeader); };
new ResizeObserver(fitSoon).observe($(".nav-inner"));
document.fonts?.ready.then(fitSoon);
// Phones: "As of Oct 1" while the year is the default one, else the full date; desktop always "As of Oct 1, 2026".
function asofLabel() {
  if (innerWidth > 640) return t("as_of") + " " + fmtDate(asOf);
  if (asOf !== DEFAULT_AS_OF) return new Date(asOf + "T12:00:00").toLocaleDateString(lang === "es" ? "es-US" : "en-US", { month: "short", day: "numeric", year: "2-digit" }); // phones: a small badge next to the calendar
  return (innerWidth < 380 ? "" : t("as_of") + " ") + new Date(asOf + "T12:00:00").toLocaleDateString(lang === "es" ? "es-US" : "en-US", { month: "short", day: "numeric" });
}
addEventListener("resize", () => { $("#asof-label").textContent = asofLabel(); }, { passive: true });
const ASOF_MIN = "2020-01-01", ASOF_MAX = "2030-12-31";
function setAsOf(v, { silent = false } = {}) {
  if (!v || v === asOf) return;
  if (v < ASOF_MIN || v > ASOF_MAX) { $("#asof").value = asOf; toast(tf("asof_range", { a: fmtDate(ASOF_MIN), b: fmtDate(ASOF_MAX) })); return; }
  asOf = v; sessionStorage.setItem("asof", asOf);
  if (!silent) { toast(tf("toast_asof", { d: fmtDate(asOf) })); route({ keepScroll: true, soft: true }); }
  else syncHeader(currentView());
  document.dispatchEvent(new CustomEvent("ce:asof", { detail: { asOf } }));
}
// #140: typing a date fires "change" for every partial value (year 0002, 0020, ...). Commit only a complete date in
// range, after a short pause or on blur, so typing is never interrupted or reset half-way.
let asofT = 0;
const asofCommit = (input, final) => {
  clearTimeout(asofT);
  const v = input.value;
  if (v && v >= ASOF_MIN && v <= ASOF_MAX) { setAsOf(v); return; }
  if (final) { if (v) toast(tf("asof_range", { a: fmtDate(ASOF_MIN), b: fmtDate(ASOF_MAX) })); input.value = asOf; }
};
$("#asof").addEventListener("change", (e) => { clearTimeout(asofT); asofT = setTimeout(() => asofCommit(e.target, document.activeElement !== e.target), 700); });
$("#asof").addEventListener("blur", (e) => asofCommit(e.target, true));
$("#asof").addEventListener("keydown", (e) => { if (e.key === "Enter") asofCommit(e.target, true); });
$("#asof").addEventListener("click", (e) => { try { e.target.showPicker?.(); } catch { /* not allowed: the native control opens anyway */ } });
$("#asof-reset").addEventListener("click", () => { $("#asof").value = DEFAULT_AS_OF; setAsOf(DEFAULT_AS_OF); $("#asof").focus({ preventScroll: true }); });
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
const currentView = () => { const v = location.hash.replace(/^#\/?/, "").split("/")[0]; return v === "a" || v === "check" || v === "compare" || !v ? "lookup" : v; };

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
  const pages = [["#/", "nav_lookup"], ["#/changes", "nav_changes"], ["#/rules", "nav_rules"], ["#/audit", "nav_audit"]];
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
// The ten cities on the home map. Anchor = the city's projected point on /static/img/us-map.svg (Albers USA, the
// us-atlas 975x610 frame); d = where its photo marker sits relative to the anchor on a wide map (px at 1180 px),
// m = the same on a phone-width map. Images: /static/img/<slug>.webp, -sm for markers; a missing image shows the
// city's initials.
const CITIES = [
  { c: "San Francisco", s: "CA", slug: "san-francisco", p: [34.8, 261.4], d: [70, 44], m: [40, 8] },
  { c: "Berkeley", s: "CA", slug: "berkeley", op: "60% 70%", p: [37.9, 260.0], d: [66, -50], m: [36, -28] },
  { c: "Los Angeles", s: "CA", slug: "los-angeles", op: "50% 75%", p: [86.8, 363.1], d: [96, -30], m: [60, -8] },
  { c: "Santa Ana", s: "CA", slug: "hero-building", generic: true, p: [92.0, 371.6], d: [120, 44], m: [52, 30] },
  { c: "San Diego", s: "CA", slug: "san-diego", p: [99.7, 397.5], d: [64, 100], m: [10, 52] },
  { c: "Boston", s: "MA", slug: "boston", p: [908.7, 167.1], d: [44, -62], m: [6, -34] },
  { c: "Cambridge", s: "MA", slug: "cambridge", p: [907.8, 167.0], d: [-46, -82], m: [-30, -34] },
  { c: "Newark", s: "NJ", slug: "newark", p: [866.8, 215.9], d: [-102, -14], m: [-50, 4] },
  { c: "Jersey City", s: "NJ", slug: "jersey-city", p: [869.1, 215.8], d: [-60, 64], m: [-30, 40] },
  { c: "Hoboken", s: "NJ", slug: "hoboken", p: [869.1, 215.1], d: [22, 80], m: [10, 46] },
];
const initials = (c) => c.split(/\s+/).map((w) => w[0]).join("").slice(0, 2);
// Street photo of a covered city (full-bleed, sized per viewport); a missing one falls back to the cut-out building.
const streetTag = (slug, eager = false, cls = "") => `<img${cls ? ` class="${cls}"` : ""} src="/static/img/street/${slug}.webp" srcset="/static/img/street/${slug}-m.webp 800w, /static/img/street/${slug}.webp 1600w" sizes="(max-width: 640px) 100vw, 760px" alt="" loading="${eager ? "eager" : "lazy"}" decoding="async" data-street onerror="if(!this.dataset.f){this.dataset.f=1;this.removeAttribute('srcset');this.src='/static/img/${slug}.webp';this.classList.add('cutout')}else this.remove()">`;
const imgTag = (src, alt, cls = "", eager = false) => `<img src="${src}" alt="${esc(alt)}"${cls ? ` class="${cls}"` : ""} loading="${eager ? "eager" : "lazy"}" decoding="async" onerror="this.remove()">`;
const cityExample = (c) => examplePicks().find((a) => a.city === c) || ADDR.find((a) => a.city === c);
let homeCity = "San Francisco";
// Hero carousel: real buildings from the covered cities, each slide opens that city's example address.
const SLIDES = ["San Francisco", "Boston", "Los Angeles", "Hoboken", "San Diego", "Cambridge"];
let slideTimer = 0, slidePaused = false;
function viewHome() {
  const ex = examplePicks();
  const sf = ex[1] || ex[0];
  const n = META?.counts || {};
  const cityN = CITIES.length, stateN = new Set(CITIES.map((x) => x.s)).size;
  const markers = CITIES.map((x, i) => `<button type="button" class="mk" data-city="${esc(x.c)}" style="--i:${i}" aria-pressed="${x.c === homeCity}" aria-label="${esc(x.c)}, ${x.s}"><span aria-hidden="true">${esc(initials(x.c))}</span>${imgTag(`/static/img/${x.slug}-sm.webp`, "")}</button>`).join("");
  const slides = SLIDES.map((c, i) => {
    const x = CITIES.find((y) => y.c === c), a = cityExample(c);
    return `<a class="slide${i === 0 ? " on" : ""}" href="${a ? `#/a/${a.id}` : "#/"}" data-i="${i}" style="--op:${x.op || "50% 60%"}"${i ? ' aria-hidden="true" tabindex="-1"' : ""}>${streetTag(x.slug, i < 2)}
      <span class="slide-cap"><b>${esc(c)}</b>${a ? esc(titleCase(a.street)) : ""}${I.arrow}</span></a>`;
  }).join("");
  const chip = (src, cls = "") => `<span class="s-chip ${cls}" aria-hidden="true">${imgTag(src, "").replace("<img ", "<img data-spring ")}</span>`;
  const row = (href, art, h, p, link, flip) => `<section class="frow${flip ? " flip" : ""}" data-reveal>
      <a class="frow-m" href="${href}" tabindex="-1" aria-hidden="true">${imgTag(`/static/img/${art}.webp`, "")}</a>
      <div class="frow-t"><h2>${esc(h)}</h2><p>${esc(p)}</p><a class="frow-l" href="${href}">${esc(link)}${I.arrow}</a></div></section>`;
  const html = `
  <div class="home">
  <section class="hero">
    <h1>${esc(t("hero_a"))} <span class="l2">${esc(t("hero_b"))}</span></h1>
    <p class="lead">${esc(t("hero_lead"))}</p>
    <div class="hero-media">
      <form class="big-search" role="search" autocomplete="off" data-tour="search">
        <div class="box">
          <label class="bs-f bs-addr" for="hq"><span class="sr">${esc(t("bs_addr"))}</span>
            <input id="hq" type="text" role="combobox" aria-expanded="false" aria-controls="hs" aria-autocomplete="list" spellcheck="false" placeholder="${esc(t("search_try"))}"></label>
          <label class="bs-f bs-date"><span class="bs-l">${esc(t("bs_asof"))}</span><span class="bs-v" id="bs-v">${esc(fmtDate(asOf))}</span>
            <input type="date" id="bs-asof" min="${ASOF_MIN}" max="${ASOF_MAX}" value="${asOf}" aria-label="${esc(t("asof_aria"))}"></label>
          <button class="go" type="submit" aria-label="${esc(t("search_go"))}">${I.arrow}</button>
        </div>
        <ul class="suggest" id="hs" role="listbox" hidden></ul>
      </form>
      <div class="slides" aria-roledescription="carousel" aria-label="${esc(t("car_aria"))}">${slides}</div>
      <div class="car-ctl"><button type="button" class="car-b" data-car="-1" aria-label="${esc(t("car_prev"))}">${I.left}</button><button type="button" class="car-b" data-car="pause" aria-label="${esc(t("car_pause"))}">${I.pause}</button><button type="button" class="car-b" data-car="1" aria-label="${esc(t("car_next"))}">${I.chev}</button></div>
    </div>
    <p class="hero-nla"><strong>${esc(t("nla"))}</strong> ${esc(t("hero_nla"))} <button type="button" class="linkish" data-nla-open>${esc(t("nla_more"))}</button></p>
    <div class="tour-slot" data-tour-slot="home"></div>
  </section>
  <section class="statement" data-words>
    <p>${tf("st_html", {
      chip1: chip("/static/img/scales-balanced.webp"), chip2: `<span class="s-chips">${chip("/static/img/san-francisco-sm.webp", "photo")}${chip("/static/img/boston-sm.webp", "photo")}</span>`,
      chip3: chip("/static/img/magnifier-over-document.webp"), chip4: chip("/static/img/shield-check.webp"),
      chip0: `<span class="s-chip s-nav w" aria-hidden="true">${I.arrow}</span>`, chip5: `<span class="s-chip s-ok w" aria-hidden="true">${I.check}</span>`,
      s: stateN, c: cityN, a: n.addresses ?? ADDR.length, r: n.rules ?? "", d: n.documents ?? "" })}</p>
  </section>
  <section class="map-stage" aria-label="${esc(t("map_aria"))}" data-reveal>
    <h2 class="map-h"><span class="dot" aria-hidden="true"></span>${esc(t("map_h"))}</h2>
    <div class="map" id="map">
      <img class="map-us" src="/static/img/us-map.svg" alt="" width="975" height="610" decoding="async">
      <div class="mk-lines" aria-hidden="true"></div>
      ${markers}
      <span class="mk-name" aria-hidden="true"></span>
    </div>
    <div class="city-card" id="city-card" aria-live="polite"></div>
  </section>
  ${row("#/check", "keys-on-ring", t("b_check"), t("b_check_p"), t("b_check_l"), false)}
  ${row(sf && ex[2] ? `#/compare/${sf.id},${ex[2].id}` : "#/compare", "house-with-checkmark", t("b_cmp"), t("b_cmp_p"), t("b_cmp_l"), true)}
  ${row("#/changes", "calendar-with-clock", t("b_chg"), t("b_chg_p"), t("b_chg_l"), false)}
  ${row("#/audit", "magnifier-over-document", t("b_src"), tf("b_src_p", { n: n.documents ?? "" }), t("b_src_l"), true)}
  </div>`;
  return swap(html, () => initHome(ex.slice(0, 4)));
}
// Scroll reveal: sections rise in once; the statement's words brighten in reading order. Reduced motion: no motion.
function reveal(root) {
  const words = $("[data-words] p", root);
  if (words && !words.dataset.split) {
    words.dataset.split = 1;
    const walk = (node) => [...node.childNodes].forEach((ch) => {
      if (ch.nodeType === 3) {
        const frag = document.createDocumentFragment();
        ch.textContent.split(/(\s+)/).forEach((w) => { if (!w) return; if (/^\s+$/.test(w)) frag.append(w); else { const sp = document.createElement("span"); sp.className = "w"; sp.textContent = w; frag.append(sp); } });
        ch.replaceWith(frag);
      } else if (ch.nodeType === 1 && !ch.matches(".s-chip, .s-chips")) walk(ch);
      else if (ch.nodeType === 1) ch.classList.add("w");
    });
    walk(words);
    $$(".w", words).forEach((w, i) => w.style.setProperty("--d", i * 28 + "ms"));
  }
  const els = $$("[data-reveal], [data-words]", root);
  if (RM.matches || !("IntersectionObserver" in window)) { els.forEach((e) => e.classList.add("in")); return; }
  const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }), { rootMargin: "0px 0px -12% 0px", threshold: .12 });
  els.forEach((e) => io.observe(e));
  cleanup.push(() => io.disconnect());
}
function initCarousel() {
  const box = $(".slides"), sl = $$(".slide", box), pauseB = $('[data-car="pause"]');
  if (!sl.length) return;
  let i = 0;
  const show = (k) => {
    i = (k + sl.length) % sl.length;
    sl.forEach((s, j) => { const on = j === i; s.classList.toggle("on", on); s.setAttribute("aria-hidden", String(!on)); s.tabIndex = on ? 0 : -1; if (on) s.querySelector("img")?.setAttribute("loading", "eager"); });
  };
  const tick = () => { clearTimeout(slideTimer); if (!slidePaused && !RM.matches) slideTimer = setTimeout(() => { if (!box.isConnected) return; show(i + 1); tick(); }, 6000); };
  const paint = () => { pauseB.innerHTML = slidePaused || RM.matches ? I.play : I.pause; pauseB.setAttribute("aria-label", t(slidePaused || RM.matches ? "car_play" : "car_pause")); };
  $(".car-ctl").addEventListener("click", (e) => {
    const b = e.target.closest("[data-car]");
    if (!b) return;
    if (b.dataset.car === "pause") { slidePaused = !slidePaused; paint(); tick(); return; }
    show(i + +b.dataset.car); tick();
  });
  box.addEventListener("pointerenter", () => clearTimeout(slideTimer));
  box.addEventListener("pointerleave", tick);
  paint(); tick();
  cleanup.push(() => clearTimeout(slideTimer));
}
// Marker layout: each city's anchor dot sits at its projected point; the photo markers line up in two tidy columns
// in the Pacific and the Atlantic, in north-to-south order, each tied to its anchor by a hairline.
function layoutMap() {
  const map = $("#map");
  if (!map) return;
  const us = $(".map-us", map);
  const mr = map.getBoundingClientRect(), ur = us.getBoundingClientRect();
  const W = mr.width, H = mr.height, iw = ur.width, ih = ur.height, il = ur.left - mr.left, it = ur.top - mr.top;
  if (!iw) return;
  const phone = W < 600, size = phone ? 38 : 60, gap = phone ? 8 : 16;
  const colX = { W: phone ? 22 : Math.max(48, il * .55), E: phone ? W - 22 : W - Math.max(48, il * .55) };
  let lines = "";
  for (const side of ["W", "E"]) {
    const group = CITIES.filter((x) => (x.p[0] < 487) === (side === "W")).map((x) => ({ x, ax: il + (x.p[0] / 975) * iw, ay: it + (x.p[1] / 610) * ih }))
      .sort((m, n) => m.ay - n.ay || m.ax - n.ax);
    const step = size + gap, span = step * (group.length - 1);
    const mid = group.reduce((t, g) => t + g.ay, 0) / group.length;
    const top = Math.max(size / 2 + 8, Math.min(H - size / 2 - 8 - span, mid - span / 2));
    group.forEach((g, i) => {
      const mx = colX[side], my = top + i * step;
      const mk = $(`.mk[data-city="${CSS.escape(g.x.c)}"]`, map);
      mk.style.left = mx + "px"; mk.style.top = my + "px";
      const dx = mx - g.ax, dy = my - g.ay, len = Math.hypot(dx, dy);
      lines += `<i class="mk-line" data-for="${esc(g.x.c)}" style="left:${g.ax}px;top:${g.ay}px;width:${len}px;transform:rotate(${Math.atan2(dy, dx)}rad)"></i>`;
    });
    group.forEach((g) => { lines += `<i class="mk-anchor" data-for="${esc(g.x.c)}" style="left:${g.ax}px;top:${g.ay}px"></i>`; });
  }
  $(".mk-lines", map).innerHTML = lines;
  placeMkName();
}
function placeMkName() {
  const mk = $(`.mk[aria-pressed="true"]`), nm = $(".mk-name");
  if (!mk || !nm) return;
  $$(".mk-line, .mk-anchor").forEach((l) => l.classList.toggle("on", l.dataset.for === mk.dataset.city));
  nm.textContent = mk.dataset.city;
  nm.style.left = mk.style.left; nm.style.top = mk.style.top;
  nm.classList.remove("on"); void nm.offsetWidth; nm.classList.add("on");
}
let COV = null;
async function cityCard(c, { animate = true } = {}) {
  const card = $("#city-card");
  if (!card) return;
  const x = CITIES.find((y) => y.c === c);
  const a = cityExample(c);
  const nAddr = META?.counts?.cities?.[c] || 0;
  if (!COV) COV = await api(`/api/coverage?as_of=${DEFAULT_AS_OF}`).catch(() => null);
  if (!$("#city-card")) return;
  const sum = (j) => Object.values(COV?.cells?.[j] || {}).reduce((s, v) => s + v.length, 0);
  const stateName = t(STATE_NAMES[x.s]);
  const fact = (b, s) => `<span><b>${b}</b>${esc(s)}</span>`;
  card.innerHTML = `
    <div class="cc-img">${imgTag(`/static/img/${x.generic ? "hero-building-card" : x.slug}.webp`, "", "", true)}<span class="cc-st">${esc(stateName)}</span></div>
    <div class="cc-body">
      <h3>${esc(c)}</h3>
      <p class="cc-sub">${a ? esc(titleCase(a.street)) + (a.postal_city !== a.city ? ` · ${esc(a.postal_city)}` : "") : esc(t("city_none"))}</p>
      <p class="cc-facts">${fact(nAddr, t("city_addr"))}${fact(COV ? sum(`${c}, ${x.s}`) : "–", t("city_rules"))}${fact(COV ? sum(x.s) : "–", tf("state_rules", { s: stateName }))}</p>
      ${a ? `<p class="cc-rent" id="cc-rent"></p><a class="btn primary cc-go" href="#/a/${a.id}">${esc(tf("city_go", { a: titleCase(a.street) }))}${I.arrow.replace('class="ico"', 'class="ico arrow-i"')}</a>`
        : `<a class="btn cc-go" href="#/rules/${encodeURIComponent(`${c}, ${x.s}`)}">${esc(tf("city_rules_go", { c }))}</a>`}
    </div>`;
  if (animate && !RM.matches) { card.classList.remove("swap"); void card.offsetWidth; card.classList.add("swap"); }
  if (a) api(addrUrl(a.id)).then((d) => {
    const cat = d.categories.find((y) => y.id === "rent_increase_limits");
    const el = $("#cc-rent");
    if (!cat || !el) return;
    el.innerHTML = `${esc(tf("city_rent", { a: titleCase(a.street) }))} <b>${esc(topicSummary(cat, d).line)}</b>`;
  }).catch(() => {});
}
function initHome(ex) {
  const form = $(".big-search"), input = $("#hq"), list = $("#hs");
  let items = [], sel = 0;
  const close = () => { list.hidden = true; input.setAttribute("aria-expanded", "false"); };
  const render = () => {
    const q = input.value.trim();
    if (!q) { close(); return; }
    items = findAddr(q, 6); sel = 0;
    const topic = !items.length && topicFor(q);
    if (topic) { // a worry, not an address: pick a city, then that topic opens
      items = CITIES.map((x) => cityExample(x.c)).filter(Boolean).map((a) => ({ ...a, _topic: topic }));
      list.innerHTML = `<li class="grp" role="presentation">${esc(tf("kw_pick", { q: t("pq_" + topic) }))}</li>` + items.map((a, i) => `<li class="opt kw" role="option" id="o-${i}" aria-selected="${i === sel}" data-id="${a.id}" data-topic="${topic}"><div><div class="addr">${esc(a.city)}, ${esc(a.state)}</div><div class="sub">${esc(tf("kw_ex", { a: titleCase(a.street) }))}</div></div><span class="arrow">${I.chev}</span></li>`).join("");
      list.hidden = false; input.setAttribute("aria-expanded", "true"); return;
    }
    if (!items.length && q.length >= 6 && /\d/.test(q) && /[a-z]{2,}/i.test(q)) { list.innerHTML = ""; list.hidden = true; return; }
    list.innerHTML = items.length ? items.map((a, i) => optHtml(a, i, sel, q)).join("") : `<li class="opt empty" aria-disabled="true"><div><div class="addr">${esc(tf("no_match_q", { q }))}</div><div class="sub">${esc(t("no_match_hint"))}</div></div></li>`;
    list.hidden = false; input.setAttribute("aria-expanded", "true");
  };
  input.addEventListener("input", render);
  input.addEventListener("focus", () => { render(); if (matchMedia("(pointer: coarse)").matches) setTimeout(() => form.scrollIntoView({ block: "start", behavior: RM.matches ? "auto" : "smooth" }), 300); });
  input.addEventListener("blur", () => setTimeout(close, 120));
  input.addEventListener("keydown", (e) => {
    if (list.hidden || !items.length) return;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault(); sel = (sel + (e.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
      $$(".opt", list).forEach((li, i) => li.setAttribute("aria-selected", i === sel));
      input.setAttribute("aria-activedescendant", "o-" + sel);
    } else if (e.key === "Escape") close();
  });
  const pick = (id, topic) => {
    const q = input.value.trim();
    if (topic) sessionStorage.setItem("ce.open", topic);
    else if (/^\d{5}$/.test(q) || !/\d/.test(q)) sessionStorage.setItem("ce.example", q); // a city or ZIP opened someone else's address
    go(id);
  };
  list.addEventListener("mousedown", (e) => { const li = e.target.closest("[data-id]"); if (li) { e.preventDefault(); pick(li.dataset.id, li.dataset.topic); } });
  list.addEventListener("mousemove", (e) => { const li = e.target.closest("[data-id]"); if (!li) return; const i = $$(".opt", list).indexOf(li); if (i !== sel) { sel = i; $$(".opt", list).forEach((x, k) => x.setAttribute("aria-selected", k === sel)); input.setAttribute("aria-activedescendant", "o-" + sel); } });
  form.addEventListener("submit", (e) => { e.preventDefault(); const q = input.value.trim(); if (!q) return input.focus(); if (items[sel]) pick(items[sel].id, items[sel]._topic); });
  // the as-of field in the search pill is the header control, closer to hand
  const d = $("#bs-asof");
  d.addEventListener("click", (e) => { try { e.target.showPicker?.(); } catch { /* native control opens anyway */ } });
  d.addEventListener("change", () => { const v = d.value; if (v && v >= ASOF_MIN && v <= ASOF_MAX) { $("#asof").value = v; setAsOf(v); } });
  // map
  const map = $("#map");
  layoutMap();
  const ro = new ResizeObserver(() => layoutMap()); ro.observe(map); cleanup.push(() => ro.disconnect());
  map.addEventListener("click", (e) => {
    const mk = e.target.closest(".mk");
    if (!mk || mk.getAttribute("aria-pressed") === "true") return;
    homeCity = mk.dataset.city;
    $$(".mk", map).forEach((m) => m.setAttribute("aria-pressed", String(m === mk)));
    placeMkName(); cityCard(homeCity);
  });
  cityCard(homeCity, { animate: false });
  initCarousel();
  reveal(main);
  ex.forEach((a) => api(addrUrl(a.id)).catch(() => {})); // warm the cache for the examples
}

// page-head object (a single <img> with a stable wrapper, so features/spring.js can attach to it)
const HEAD_ART = { changes: "calendar-with-clock", rules: "scales-balanced", compare: "house-with-checkmark", properties: "keys-on-ring" };
function headArt() {
  const view = location.hash.replace(/^#\/?/, "").split("/")[0];
  const head = $(".page-head", main), src = HEAD_ART[view];
  if (!head || !src || $(".ph-art", head) || head.closest(".src-hero")) return;
  head.classList.add("has-art");
  head.insertAdjacentHTML("beforeend", `<span class="ph-art" aria-hidden="true"><img src="/static/img/${src}.webp" alt="" width="152" height="152" decoding="async" data-spring onerror="this.parentNode.remove()"></span>`);
}
// words people type instead of an address (persona test): map them to the topic they are asking about
const KW = [["security_deposits", /deposit|dep[oó]sito|fianza/i], ["just_cause_eviction", /evict|kick|echar|desalo|complain|queja|heat|calefacc|repair|repara|retalia|represal/i],
  ["application_screening_fees", /\bfees?\b|cargo|cobr|solicitud|application/i], ["screening_restrictions", /voucher|\bvales?\b|section 8|secci[oó]n 8|record|antecedente|criminal/i],
  ["algorithmic_rent_setting", /software|algorithm|algoritmo|realpage|programa/i], ["rent_increase_limits", /raise|increase|subir|aumento|rent ?cap|tope|control/i]];
const topicFor = (q) => (KW.find(([, re]) => re.test(q)) || [])[0] || null;
// ------------------------------------------------------------------ answers (address page, My properties, any-address) --
// Order inside a topic: the governing rule first. A rule that takes precedence over another comes first, then
// statewide rules (a city rule that does not override them usually adds to them), then the rest.
const RANK = { applies: 0, unknown: 1, not_yet_effective: 2, superseded: 3, pending: 4, failed: 5 };
// PV: a place view (Rules page, no building): a rule that covers the place unless the building is exempt ranks with
// the ones that apply, so the main protection still leads.
let PV = false;
const rankOf = (x) => PV && x.result === "unknown" ? 0 : RANK[x.result] ?? 9;
const localFirst = (x, y) => y.rule.level === "state" && x.rule.level !== "state" && (x.rule.overrides || []).includes(y.rule.team_rule_id) ? -1 : 0;
const ordered = (items) => [...items].sort((x, y) => rankOf(x) - rankOf(y)
  || (PV ? localFirst(x, y) : 0) - (PV ? localFirst(y, x) : 0) // a place: a local rule that replaces the state one leads
  || (y.overrides_here?.length ? 1 : 0) - (x.overrides_here?.length ? 1 : 0)
  || (x.rule.headline_priority ?? 1.5) - (y.rule.headline_priority ?? 1.5) // the main protection leads (good cause before retaliation)
  || (x.rule.level === "state" ? 0 : 1) - (y.rule.level === "state" ? 0 : 1));
// Plain answer and why line (web/headlines.py PLAIN), while their period lasts; the headline is the fallback.
const plainOk = (r) => r.answer_display && !(r.plain_until && asOf > r.plain_until);
const answerOf = (item) => plainOk(item.rule) ? item.rule.answer_display : headlineOf(item);
// Internal wording never reaches a reader: corpus notes, document ids, extraction confidence, <=, (assessor).
const DEBUG = /corpus|link-only|not captured|unverified|believed to|captured documents|ecode360|\bD0\d\d\b|confidence|flagged|extraction|human review|use description|source_doc/i;
const clean = (txt) => splitSentences(String(txt || "")).filter((x) => !DEBUG.test(x)).join(" ")
  .replace(/\(\s*<=\s*(\d+)\s*units?\s*\)/gi, (m, n) => `(${n} ${lang === "es" ? "unidades o menos" : "units or fewer"})`).replace(/<=\s*/g, lang === "es" ? "como máximo " : "at most ")
  .replace(/\s*\((?:assessor|from the assessor|tasador)\)/gi, "").replace(/\s*\(from use description '[^']*'\)/gi, "").replace(/\s{2,}/g, " ").trim();

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
    if (m[3]) out.facts.push(...m[3].split(/;\s+/).map((x) => cap(isoDates(x.replace(/^coverage depends on facts not in the data:\s*/i, "")
      // #142: the year is known; what is missing is the exact certificate date
      .replace(/^the year built date is not in the data \(year built on or before ([\d-]+)\)$/i, "the data has only the year, not the exact certificate-of-occupancy date (cutoff $1)")))));
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
  if (lang !== "en" && item.explanation && item.explanation_en && (item.explanation_translated ?? item.explanation !== item.explanation_en)) {
    const kv = r.key_value_display || "";
    let rest = item.explanation.replace(kv ? new RegExp(`\\s*Regla:\\s*${kv.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\.?`) : /$^/, "");
    // rule ids are internal: "LA-RENT-01 (L.A. Mun. Code ...)" reads as the citation alone (#151)
    rest = rest.replace(/\b[A-Z]{2,4}-[A-Z]{2,5}-[A-Z0-9]{1,3}\s*\(([^)]*)\)/g, "$1").replace(/\s*\b[A-Z]{2,4}-[A-Z]{2,5}-[A-Z0-9]{1,3}\b,?/g, "");
    const nota = rest.match(/\s*Nota:\s*([\s\S]+)$/); // the translated note replaces the English one
    out.notes = nota ? [cap(nota[1].replace(/^pregunta abierta:\s*/i, "").replace(/\s*-\s*marcad[oa] para revisión humana\.?$/i, "").trim())] : [];
    out.facts = []; out.rest = nota ? rest.slice(0, nota.index) : rest;
  }
  return out;
}
const missingLabel = (item, d) => {
  const f = item.missing_fact || "";
  const y = d?.address?.year_built;
  if (/certificate|year built/i.test(f) && y) return tf("needs_co", { y });
  return t(f || "A fact not contained in the public data");
};
// The span stays verbatim in the data; on screen a scraped tail ("(click here to", a cut-off clause) is trimmed back
// to the last complete clause and the cut is marked with "…".
function shownQuote(q) {
  let s = String(q || "").trim();
  const open = s.lastIndexOf("("), close = s.lastIndexOf(")");
  if (open > close) s = s.slice(0, open).trim();
  if (/[.;:!?"”)\]]$/.test(s) && s === String(q).trim()) return s;
  const cut = Math.max(s.lastIndexOf(". "), s.lastIndexOf("; "), s.lastIndexOf(": "));
  if (!/[.;:!?"”)\]]$/.test(s) && cut > s.length * 0.5) s = s.slice(0, cut + 1);
  return s.replace(/[\s,;:–-]+$/, "") + " …";
}
function sourceHtml(src, effective = "") {
  // src: {quote, citation, url, retrieved, doc, rule, check, confidence, id, secondary}. One block: quote, one citation line, one meta line.
  const chk = src.check?.status;
  const verified = chk === "exact" || chk === "normalized" ? `<span class="ok">${I.check}${t("quote_ok")}</span>` : chk === "not_found" ? `<span class="warn">${I.alert}${t("quote_bad")}</span>` : "";
  const meta = [verified, src.retrieved ? esc(tf("retrieved", { d: fmtDate(src.retrieved) })) : "", src.secondary ? esc(t("secondary")) : ""].filter(Boolean);
  const cite = [src.citation ? `<span>${esc(src.citation)}</span>` : "", effective ? `<span>${esc(effective)}</span>` : "", src.url ? `<a href="${esc(src.url)}" target="_blank" rel="noopener">${esc(host(src.url))}${I.ext}</a>` : "", src.doc ? `<a href="#" data-doc="${esc(src.doc)}" data-rule="${esc(src.rule || "")}">${t("read_full")}</a>` : ""].filter(Boolean);
  return `<div class="rd-src" data-tour="source">
    ${src.quote ? `<blockquote class="quote">${esc(shownQuote(src.quote))}</blockquote>` : ""}
    ${cite.length ? `<p class="rd-cite">${cite.join("")}</p>` : ""}
    ${meta.length ? `<p class="rd-meta">${meta.join("<span class=\"sep\" aria-hidden=\"true\">·</span>")}</p>` : ""}
  </div>`;
}
// The source link's label: a law-firm or news page is a summary, never the "Official site"
const isSecondary = (r) => !!(r?.source?.secondary || r?.verification === "secondary_source" || r?.source_verification === "secondary_source");
const srcLabel = (r) => isSecondary(r) ? tf("src_secondary", { h: host(r.source?.url || r.source_url || "") }) : t("official_site");
const ruleSource = (r) => ({ quote: r.quoted_span, citation: r.citation, url: r.source_url, retrieved: r.source?.retrieved_at || r.retrieved_at, doc: r.source?.has_text ? (r.span_doc_id || r.quoted_span_doc_id || r.source_doc_id) : null, rule: r.team_rule_id, check: r.quote_check, confidence: r.confidence, id: r.team_rule_id, secondary: r.source?.secondary });
// Plain words for the abbreviations the rule summaries use (English only; the Spanish text is translated already).
const GLOSSARY = [[/\bfirst CO\b/g, "first certificate of occupancy"], [/\bCO\b/g, "certificate of occupancy"], [/\bAGA\b/g, "annual general adjustment"],
  [/Costa-Hawkins-eligible tenancies/g, "single-family homes and condos (exempt under the state Costa-Hawkins Act)"], [/\bFMR\b/g, "fair market rent"],
  [/\bRSO units\b/g, "rent-stabilized units"], [/\bRSO tenants\b/g, "tenants in rent-stabilized units"], [/\bset by LAHD\b/g, "set by the LA Housing Department"]];
const plain = (txt) => lang === "en" ? GLOSSARY.reduce((s, [re, to]) => s.replace(re, to), String(txt || "")) : String(txt || "");
// True when the summary mostly repeats the quoted text: then the quote alone says it.
const words = (s) => String(s || "").toLowerCase().match(/[a-z0-9%$.]{3,}/g) || [];
function sameAsQuote(a, b) {
  const A = words(a), B = new Set(words(b));
  if (!A.length || !B.size) return false;
  const hit = A.filter((x) => B.has(x)).length / A.length;
  return hit >= 0.6;
}
// L4 line for a rule whose quote is shown above (L3): when it took effect and how the quote was checked, in words
function checkedLine(r, eff) {
  const ok = ["exact", "normalized"].includes(r.quote_check?.status), when = r.source?.retrieved_at || r.retrieved_at;
  const parts = [eff ? eff + "." : "", ok && when ? tf("checked_on", { d: fmtDate(when) }) : ""].filter(Boolean);
  return parts.length ? `<p class="rd-meta">${esc(parts.join(" "))}</p>` : "";
}
function ruleDetail(item, d, { withTitle = true, needs = true, quote = true } = {}) {
  const r = item.rule, res = item.result, w = parseWhy(item);
  const list = (xs) => xs.length > 1 ? `<ul>${xs.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : `<p>${esc(xs[0])}</p>`;
  const why = [...(w.facts.length ? w.facts.map(plain) : w.rest ? [isoDates(w.rest)] : [])].map(clean).filter(Boolean);
  if (res === "superseded" && item.superseded_by?.length) why.push(tf("yields_to", { r: item.superseded_by.map((x) => x.title).join(", ") }));
  const changes = [...w.changes];
  if (res === "not_yet_effective" && r.effective_date) changes.push(tf("ch_starts", { d: fmtDate(r.effective_date_norm || r.effective_date) }));
  if (w.version && asOf < w.version.from) changes.push(tf("ch_version", { a: fmtDate(asOf), b: fmtDate(w.version.from) }) + (w.version.note ? " " + w.version.note : ""));
  const figEnd = w.figureEnd || (r.headline_until && asOf > r.headline_until ? r.headline_until : null); // #142: expired period figures say so
  if (figEnd) changes.push(tf("ch_figure_end", { d: fmtDate(figEnd) }));
  const notes = []; // open questions are for reviewers (Rules, Sources), not for the answer
  // open questions join "Changes" when there are changes, else they get their own heading
  const later = changes.length ? [...changes, ...notes.map((n) => `${t("sec_review")}: ${n}`)] : notes;
  const laterHead = changes.length ? "sec_changes" : "sec_review";
  const eff = /^\d{4}-\d{2}/.test(r.effective_date_norm || "") && res !== "not_yet_effective" ? tf("ch_effective", { d: fmtDate(r.effective_date_norm) }).replace(/\.$/, "") : "";
  const req = r.requirement_display || r.requirement || "";
  // plain text only for what the quote doesn't already say (exceptions, conditions)
  const extra = clean(splitSentences(req).filter((x) => !sameAsQuote(x, r.quoted_span)).join(" ").trim());
  return `<div class="rd">
    ${withTitle ? `<h4 class="rd-title">${esc(r.title_display || r.title)}</h4>` : ""}
    ${extra ? `<p class="rd-plain">${esc(cap(plain(extra)))}</p>` : ""}
    ${res === "unknown" && needs ? `<p class="rd-needs"><b>${t("needs")}:</b> ${esc(missingLabel(item, d))}</p>` : ""}
    ${quote ? sourceHtml(ruleSource(r), eff) : checkedLine(r, eff)}
    <p class="rd-meta">${esc([r.confidence != null ? tf("conf_l", { n: pctOf(r.confidence) }) : "", r.conflict_flag ? tf("flag_l", { n: plainNote(r) }) : t("flag_none")].filter(Boolean).join(" "))}</p>
    ${why.length ? `<section class="rd-sec"><h5>${t(res === "unknown" ? "sec_why_unknown" : "sec_why")}</h5>${list(why)}</section>` : ""}
    ${later.length ? `<section class="rd-sec"><h5>${t(laterHead)}</h5>${list(later)}</section>` : ""}
  </div>`;
}
// One line that answers the topic's question for this address.
// The row answer (web/headlines.py): the API sends it per item for its as-of date; otherwise pick by our own date.
const headlineOf = (item) => item.headline || (item.rule.headline_until && asOf > item.rule.headline_until ? item.rule.headline_after : item.rule.headline_display);
function alsoLine(rest) {
  const n = (r) => rest.filter((x) => x.result === r).length;
  const part = (r, k) => n(r) ? tf(n(r) === 1 ? k + "1" : k + "N", { n: n(r) }) : "";
  return [part("applies", "also_apply"), part("unknown", "also_unk"), part("not_yet_effective", "also_nye"), part("superseded", "also_rep")].filter(Boolean).join(" · ");
}
// One line that answers the topic's question for this address. The status word shows only when it is not the norm
// ("applies" is the norm and stays silent; a rule that removes a protection gets a grey "No limit").
function topicSummary(c, d) {
  const items = ordered(c.enacted || []);
  const top = items[0];
  if (top) {
    const r = top.rule, w = parseWhy(top);
    let line, status = top.result, next = "";
    if (top.result === "unknown") line = PV && plainOk(r) ? answerOf(top) : t("l1_unknown");
    else if (top.result === "not_yet_effective" && !plainOk(r)) line = tf("l1_later", { d: fmtDate(r.effective_date_norm || r.effective_date) });
    else line = answerOf(top) || r.key_value_display || r.key_value || r.title_display || r.title;
    if (top.result === "applies") status = r.removes_protection ? "no_limit" : "";
    if (top.result === "not_yet_effective") next = tf("starts", { d: fmtDate(r.effective_date_norm || r.effective_date) });
    else if (w.version && asOf < w.version.from) next = tf("fig_from", { d: fmtDate(w.version.from) });
    else {
      const soon = items.find((x) => x !== top && x.result === "not_yet_effective");
      if (soon) next = tf("changes_on", { d: fmtDate(soon.rule.effective_date_norm || soon.rule.effective_date) });
    }
    return { line: cap(line), where: placeName(r), status, next, extra: alsoLine(items.slice(1)) };
  }
  const ex = c.excluded?.[0];
  if (ex) return { line: t(c.id === "rent_increase_limits" ? "l1_exempt_rent" : "l1_exempt"), where: "", status: "exempt", next: "", extra: "" };
  const f = c.no_rule_findings?.[0];
  const first = (s) => splitSentences(s)[0] || String(s || "");
  return { line: t(c.id === "rent_increase_limits" ? "l1_none_rent" : "l1_none"), where: f ? (STATE_NAMES[f.jurisdiction] ? t(STATE_NAMES[f.jurisdiction]) : shortJ(f.jurisdiction)) : "", status: "no_rule", next: "", extra: "" };
}
function subRule(item, d) {
  const r = item.rule;
  return `<details class="subrule"><summary data-tour="rule" data-rule="${esc(r.team_rule_id)}"><span class="sub-main"><span class="sub-t">${esc(r.title_display || r.title)}</span><span class="sub-a">${esc(cap(headlineOf(item) || r.key_value_display || r.key_value || ""))}${headlineOf(item) || r.key_value ? " · " : ""}${esc(placeName(r))}</span></span><span class="st-word st-${esc(item.result)}">${esc(resLabel(item.result))}</span><span class="chev">${I.chev}</span></summary>
    ${ruleDetail(item, d, { withTitle: false })}</details>`;
}
// Feature modules (compare, check, tour) may append quiet links into these slots; see web/DESIGN.md.
const slot = (c) => `<div class="topic-actions" data-slot="topic-actions" data-cat="${c.id}"></div>`;
function topicBody(c, d, { slot: withSlot = true, quote = true } = {}) {
  const slot2 = (x) => withSlot ? slot(x) : "";
  const items = ordered(c.enacted || []);
  if (items.length) {
    const [top, ...rest] = items;
    return ruleDetail(top, d, { needs: false, quote }) + (rest.length ? `<div class="also"><h5>${t("also_here")}</h5>${rest.map((x) => subRule(x, d)).join("")}</div>` : "") + slot2(c);
  }
  let html = "";
  for (const ex of c.excluded || []) {
    html += `<div class="rd"><p class="rd-plain">${esc(tf("exempt_body", { t: ex.title, c: ex.citation || ex.id }))}</p>
      <section class="rd-sec"><h5>${t("sec_why_not")}</h5>${ex.reasons.length > 1 ? `<ul>${ex.reasons.map((x) => `<li>${esc(cap(isoDates(x)))}</li>`).join("")}</ul>` : `<p>${esc(cap(isoDates(ex.reasons[0] || "")))}</p>`}</section></div>`;
  }
  for (const f of c.no_rule_findings || []) {
    html += `<div class="rd"><p class="rd-plain">${esc(f.finding_display || f.finding)}</p>
      ${f.quoted_span || f.citation ? sourceHtml({ quote: f.quoted_span, citation: f.citation, url: f.source_url, retrieved: f.source?.retrieved_at, doc: f.source?.has_text ? (f.quoted_span_doc_id || f.source_doc_id) : null, check: f.quote_check, confidence: f.confidence, id: f.finding_id, rule: f.finding_id }) : ""}</div>`;
  }
  return (html || `<div class="rd"><p class="rd-plain">${esc(t("no_rule_short"))}</p></div>`) + slot2(c);
}
// Plain words first (persona "David": low attention, not legally literate). A topic opens to one "why" line in
// 5th-grade words, a question when the answer depends on a fact he knows, the actions, and one "Show me the law" tap
// that holds every legal detail (rules, quotes, citations, conditions).
function whyLine(c, d) {
  const items = ordered(c.enacted || []), top = items[0];
  if (!top) {
    const ex = c.excluded?.[0];
    if (ex) {
      const y = ANS[main.dataset.addr]?.year_built || d?.address?.year_built;
      return /new|construct|certificate|built|year/i.test((ex.reasons || []).join(" ")) && y ? tf("why_new", { y }) : t("why_exempt");
    }
    return t("why_none");
  }
  const r = top.rule, place = placeName(r);
  if (top.result === "applies" && plainOk(r) && r.why_display) return r.why_display;
  if (top.result === "unknown" && PV) {
    const other = items.find((x) => x !== top && x.rule.level === "state" && (x.result === "applies" || x.result === "unknown") && answerOf(x));
    const base = factKind(top) ? tf("why_place", { f: plainFact(top) }) : t("why_unknown_other");
    return other && top.rule.level !== "state" ? `${base} ${tf("why_else", { o: answerOf(other) })}` : base;
  }
  if (top.result === "unknown") return factKind(top) ? tf("why_unknown", { f: plainFact(top) }) : t("why_unknown_other");
  if (top.result === "not_yet_effective") return tf("why_later", { d: fmtDate(r.effective_date_norm || r.effective_date) });
  if (r.removes_protection) return tf("why_nolimit", { p: place });
  const replaced = items.some((x) => x.result === "superseded");
  return tf(r.level === "state" ? "why_state" : "why_city", { p: place }) + (replaced ? " " + t("why_replaces") : "");
}
const plainFact = (item) => {
  const f = `${item.missing_fact || ""} ${(item.needs_fact || []).join(" ")}`;
  if (/certificate|year/i.test(f)) return t("pf_year");
  if (/unit/i.test(f)) return t("pf_units");
  if (/owner/i.test(f)) return t("pf_owner");
  if (/tenancy|moved/i.test(f)) return t("pf_tenancy");
  return t("pf_other");
};
// An unknown answer becomes a question the reader can answer. The cutoffs come from the rules' own coverage
// (construction_cutoff, new_construction_exemption); the answer is sent as a year away from the boundary.
function factKind(item) {
  const f = `${item.missing_fact || ""} ${(item.needs_fact || []).join(" ")}`;
  return /certificate|year/i.test(f) ? "year" : /unit/i.test(f) ? "units" : /owner/i.test(f) ? "owner" : null;
}
function yearCuts(d) {
  const ys = new Set(), now = new Date(d.as_of + "T12:00:00");
  for (const c of d.categories) for (const it of c.enacted || []) {
    if (it.result !== "unknown" || factKind(it) !== "year") continue;
    const cov = it.rule.coverage || {};
    if (cov.construction_cutoff?.date) ys.add(+cov.construction_cutoff.date.slice(0, 4));
    if (cov.new_construction_exemption?.years) ys.add(now.getFullYear() - cov.new_construction_exemption.years);
  }
  return [...ys].sort((x, y) => x - y);
}
function askHtml(c, d) {
  const top = ordered(c.enacted || [])[0];
  if (!top || top.result !== "unknown" || !(d?.address?.address_id || d?.ask)) return "";
  const k = factKind(top);
  const opt = (v, label, said = label) => `<button type="button" class="btn" data-val="${v}" data-said="${esc(said)}">${esc(label)}</button>`;
  let q = "", btns = "", foot = "", preview = "";
  if (k === "year") {
    const ys = yearCuts(d);
    if (ys.length === 1) {
      const y = ys[0];
      q = tf("ask_year", { y }); btns = opt(y - 1, t("yes"), tf("ask_b_before", { y })) + opt(y + 1, t("no"), tf("ask_b_after", { y })); foot = tf("ask_year_f", { y }); preview = `${y - 1},${y + 1}`;
    } else if (ys.length > 1) {
      q = t("ask_when");
      btns = opt(ys[0] - 1, tf("ask_b_before", { y: ys[0] }));
      for (let i = 1; i < ys.length; i++) btns += opt(Math.round((ys[i - 1] + ys[i]) / 2), `${ys[i - 1]}–${ys[i] - 1}`);
      btns += opt(ys[ys.length - 1] + 1, tf("ask_b_after", { y: ys[ys.length - 1] }));
    }
  } else if (k === "units") {
    q = t("ask_units2"); btns = opt(1, "1") + opt(2, "2") + opt(4, "3–4") + opt(5, t("ask_5plus"));
  } else if (k === "owner") {
    q = t("ask_owner"); btns = opt("true", t("yes")) + opt("false", t("no")); preview = "true,false";
  }
  if (!q) {
    const url = top.rule.source_url;
    return `<p class="fq-note">${esc(t("ask_other"))}</p>${url ? `<p class="fq-note"><a class="btn" href="${esc(url)}" target="_blank" rel="noopener">${esc(t("open_page"))}${I.ext}</a></p>` : ""}`;
  }
  return `<div class="fq" data-ask="${k}" data-cat="${c.id}"${preview && d.address?.address_id ? ` data-preview="${preview}"` : ""}><p class="fq-q">${esc(q)}</p>
    <div class="fq-b">${btns}<button type="button" class="btn ghost-b" data-val="unsure">${esc(t("unsure"))}</button></div>
    <p class="fq-pre" aria-live="polite"></p>${foot ? `<p class="fq-f">${esc(foot)}</p>` : ""}</div>`;
}
// Responsible design (brief): an uncertain reading or a possible conflict is flagged for a human to double-check,
// in plain words, with the confidence and the reason one tap away.
const isConflict = (r) => r.conflict_flag && /preempt|conflict|supersed|override/i.test(r.conflict_note || "");
function plainNote(r) {
  const n = String(r.conflict_note_display || r.conflict_note || "");
  if (/could not be read|not confirmed|not verified|unverified|link-only|not captured/i.test(r.conflict_note || "")) return t("note_unread");
  return n.replace(/\s*\((?:D\d{3}[^)]*)\)/g, "").replace(/\bD\d{3}(?:-D\d{3})?\b/g, "").replace(/\s{2,}/g, " ").trim();
}
function flagHtml(c) {
  const items = ordered(c.enacted || []).filter((x) => x.result === "applies" || x.result === "unknown" || x.result === "not_yet_effective");
  const top = items[0];
  if (!top) return "";
  const r = top.rule, low = r.confidence != null && r.confidence < 0.7;
  const conflict = items.map((x) => x.rule).find(isConflict);
  const unsure = low || (r.conflict_flag && !isConflict(r));
  if (!conflict && !unsure) return "";
  const out = [];
  if (conflict) out.push(`<details class="flag"><summary>${I.alert}<span>${esc(t("flag_conflict"))}</span><span class="flag-why">${esc(t("flag_why"))}</span></summary><p>${esc(plainNote(conflict))}</p></details>`);
  if (unsure) out.push(`<details class="flag"><summary>${I.alert}<span>${esc(t("flag_unsure"))}</span><span class="flag-why">${esc(t("flag_why"))}</span></summary><p>${esc([r.confidence != null ? tf("conf_l", { n: pctOf(r.confidence) }) : "", r.conflict_flag ? plainNote(r) : ""].filter(Boolean).join(" "))}</p></details>`);
  return out.join("");
}
// the other rules that apply here, as plain one-liners (a specific worry is often one of these: retaliation, notice)
function alsoHtml(c) {
  const [top, ...rest] = ordered(c.enacted || []);
  if (!top || (top.result === "unknown" && !PV)) return "";
  const seen = new Set([answerOf(top)]);
  const lines = rest.filter((x) => x.result === "applies" || (PV && x.result === "unknown")).map(answerOf).filter((x) => x && !seen.has(x) && seen.add(x));
  return lines.length ? `<ul class="also-l" aria-label="${esc(t("also_rules"))}">${lines.map((x) => `<li>${esc(cap(x))}</li>`).join("")}</ul>` : "";
}
// Inline calculator for rent and deposit: the reader's rent in, the most they can ask out (POST /api/check, the same
// deterministic verdict as Check a rent increase; nothing stored).
function calcHtml(c, d) {
  const top = ordered(c.enacted || [])[0];
  if (!d?.address?.address_id || !top || top.result !== "applies" || top.rule.removes_protection) return "";
  if (c.id !== "rent_increase_limits" && c.id !== "security_deposits") return "";
  return `<form class="calc" data-calc="${c.id}" onsubmit="return false"><label><span>${esc(t("calc_rent"))}</span>
    <span class="calc-in"><b aria-hidden="true">$</b><input type="text" inputmode="decimal" autocomplete="off" placeholder="2,000" aria-label="${esc(t("calc_rent"))}"></span></label>
    <output class="calc-out" aria-live="polite"></output></form>`;
}
const money = (n) => new Intl.NumberFormat(lang === "es" ? "es-US" : "en-US", { style: "currency", currency: "USD", maximumFractionDigits: n % 1 ? 2 : 0 }).format(n);
let calcT = 0;
document.addEventListener("input", (e) => {
  const inp = e.target.closest?.("#main .calc input");
  if (!inp) return;
  clearTimeout(calcT);
  calcT = setTimeout(async () => {
    const form = inp.closest(".calc"), out = $(".calc-out", form), rent = parseFloat(inp.value.replace(/[^0-9.]/g, ""));
    if (!(rent > 0)) { out.textContent = ""; form.classList.remove("has"); return; }
    const id = main.dataset.addr, facts = Object.fromEntries(Object.entries(ANS[id] || {}).filter(([k]) => !k.startsWith("_")));
    const rentQ = form.dataset.calc === "rent_increase_limits";
    const body = { address_id: id, as_of: asOf, lang, current_rent: rent, ...(rentQ ? { increase_pct: 0.01 } : { deposit: 1 }), ...(Object.keys(facts).length ? { facts } : {}) };
    let v;
    try { const r = await fetch("/api/check", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); if (!r.ok) throw 0; v = (await r.json()).verdicts.find((x) => x.id === (rentQ ? "rent" : "deposit")); } catch { return; }
    const x = v?.values || {};
    let txt = "";
    if (rentQ && v?.code === "within" && x.max_rent) txt = tf("calc_max", { v: money(x.max_rent) });
    else if (rentQ && v?.code === "need_cpi" && x.cap_max) txt = tf("calc_upto", { v: money(Math.round(rent * (1 + x.cap_max / 100))), p: x.cap_max });
    else if (!rentQ && v?.code === "within" && x.max) txt = tf("calc_dep", { v: money(x.max) });
    if (inp.isConnected) { out.textContent = txt; form.classList.toggle("has", !!txt); form.classList.remove("pulse"); void form.offsetWidth; form.classList.add("pulse"); }
  }, 280);
});
// L3: only the sentence of the law that carries the answer, with one source line
const lawTop = (c) => { const top = ordered(c.enacted || [])[0]; return top?.rule.quoted_span ? top : null; };
function lawQuote(c) {
  const top = lawTop(c);
  if (!top) return "";
  const r = top.rule, src = ruleSource(r);
  const ok = ["exact", "normalized"].includes(r.quote_check?.status), when = r.source?.retrieved_at || r.retrieved_at;
  const badgeL = ok ? `<p class="l3-ok">${I.check}<span>${esc(tf("l3_ok", { h: host(r.source?.url || r.source_url || ""), d: fmtDate(when) }))}</span></p>` : when ? `<p class="rd-meta">${esc(tf("retrieved", { d: fmtDate(when) }))}</p>` : "";
  return `<div class="rd-src l3" data-tour="source">${lang !== "en" ? `<p class="l3-tr">${esc(t("tr_note"))}</p>` : ""}<blockquote class="quote" lang="en">${esc(shownQuote(r.quoted_span))}</blockquote>${badgeL}
    <p class="rd-cite">${r.citation ? `<span>${esc(r.citation)}</span>` : ""}${r.source_url ? `<a href="${esc(r.source_url)}" target="_blank" rel="noopener">${esc(srcLabel(r))}${I.ext}</a>` : ""}${src.doc ? `<a href="#" data-doc="${esc(src.doc)}" data-rule="${esc(r.team_rule_id)}">${t("read_full")}</a>` : ""}</p></div>`;
}
// the closed row's status: one coloured dot (green limit or protection, amber needs an answer, grey none, blue later)
// a flagged answer (low confidence or a conflict at this address, the same test as flagHtml) is never green: amber
function dotOf(c, s, top) {
  let k = !top ? "none" : top.result === "unknown" ? "ask" : top.result === "not_yet_effective" ? "later" : s.status === "no_limit" || s.status === "exempt" || s.status === "no_rule" ? "none" : "ok";
  if (k === "ok" && flagHtml(c)) k = "check";
  if (k === "ask" && PV && plainOk(top.rule)) k = "dep"; // a place: the answer is real, it may not cover every building
  return `<span class="sdot sd-${k === "check" ? "ask sd-check" : k === "dep" ? "ask sd-check" : k}" role="img" aria-label="${esc(t("sd_" + k))}"></span>`;
}
// generated plain copy (navigator/plain.py) not yet read by a person: say so, in the details only
const autoSum = (top) => top?.rule.plain_source === "generated" ? `<p class="rd-meta auto-sum">${esc(t(top.rule.plain_needs_review ? "auto_sum_review" : "auto_sum"))}</p>` : "";
function topicRow(c, d, { asked = false } = {}) {
  const s = topicSummary(c, d);
  const top = ordered(c.enacted || [])[0];
  return `<details class="topic${asked ? " resolved" : ""}" id="t-${c.id}" data-cat="${c.id}" data-tour="answer">
    <summary${top ? ` data-tour="rule" data-rule="${esc(top.rule.team_rule_id)}"` : ""}>
      <span class="topic-main">
        <span class="topic-q">${esc(t("pq_" + c.id))}</span>
        <span class="topic-a">${esc(s.line)}</span>
        ${s.next ? `<span class="topic-x"><span class="soon">${esc(s.next)}</span></span>` : ""}
      </span>
      ${dotOf(c, s, top)}
      <span class="chev">${I.chev}</span>
    </summary>
    <div class="topic-body">
      <p class="why">${esc(whyLine(c, d))}</p>
      ${flagHtml(c)}
      ${alsoHtml(c)}
      ${askHtml(c, d)}${calcHtml(c, d)}
      ${slot(c)}
      <details class="law"><summary><span>${esc(t("law_show"))}</span><span class="chev">${I.chev}</span></summary>
        <div class="law-in">${lawQuote(c)}
          <details class="more"><summary><span>${esc(t("law_more"))}</span><span class="chev">${I.chev}</span></summary>
            <div class="more-in">${s.extra ? `<p class="law-x">${esc(s.extra)}</p>` : ""}${topicBody(c, d, { slot: false, quote: !lawTop(c) })}${autoSum(top)}</div></details>
        </div></details>
    </div>
  </details>`;
}
function answersHTML(d, { actions = false } = {}) {
  const proposals = d.categories.flatMap((c) => [...(c.pending || []), ...(c.not_law || [])]);
  return `
    <div class="answers-head">
      <h2>${d.heading ? esc(d.heading) : t("rules_here")}</h2>
      ${actions ? `<div class="addr-actions" data-slot="address-actions"></div>` : ""}
      <p class="note">${esc(tf("answers_note", { d: fmtDate(d.as_of) }))}</p>
    </div>
    <div class="topics group">${d.categories.map((c) => topicRow(c, d)).join("")}</div>
    ${proposals.length ? `<div class="answers-head sub-head" id="nl-h"><h2>${t("not_law")}</h2><p class="note">${t("not_law_note")}</p></div>
      <div class="topics group">${proposals.map((it) => `<details class="topic plain"><summary><span class="topic-main"><span class="topic-q">${esc(it.rule.title_display || it.rule.title)}</span><span class="topic-a">${esc(t("cat_" + it.rule.category))} · ${esc(placeName(it.rule))}</span></span>${badge(it.result)}<span class="chev">${I.chev}</span></summary><div class="topic-body">${ruleDetail(it, d, { withTitle: false })}</div></details>`).join("")}</div>` : ""}`;
}

// ------------------------------------------------------------------ address --
const citySlug = (c) => CITIES.find((x) => x.c === c && !x.generic)?.slug;
function addressSkeleton() {
  const line = (w, h = 14, m = 10) => `<div class="sk" style="width:${w};height:${h}px;margin-top:${m}px"></div>`;
  return `<article class="addr"><section class="ahero"><div class="gal"></div><div class="addr-head">${line("80%", 40, 24)}${line("50%", 16, 12)}${line("100%", 80, 24)}</div></section>
    <div class="adetail"><section class="answers">${line("40%", 26, 8)}${line("100%", 420, 20)}</section></div></article>`;
}
// The lookup, step by step: each step shows what the server actually found for this address (no invented progress).
const SEEN = new Set();
const lstep = (n, title) => `<li class="lstep" data-step="${n}"><span class="lk" aria-hidden="true">${I.check}</span><span class="lt"><b>${esc(title)}</b><small></small></span></li>`;
function stepsShell(id) {
  const a = ADDR.find((x) => x.id === id);
  const slug = citySlug(a?.city);
  return `<article class="addr is-loading"><section class="ahero"><div class="gal${slug ? " street" : ""}">${slug ? streetTag(slug, true) : ""}</div>
      <div class="addr-head"><h1>${esc(titleCase(a?.street || ""))}</h1><p class="addr-sub">${esc(a?.postal_city || "")}, ${esc(a?.state || "")} ${esc(a?.zip || "")}</p>
      <div class="steps-card" role="status" aria-label="${esc(t("ls_title"))}"><ol class="lsteps">${lstep(1, t("ls_1"))}${lstep(2, t("ls_2"))}${lstep(3, t("ls_3"))}</ol></div></div></section></article>`;
}
function stepFacts(d) {
  const j = d.jurisdiction;
  const items = d.categories.flatMap((c) => c.enacted || []);
  const applies = items.filter((x) => x.result === "applies").length;
  const quoted = items.filter((x) => x.rule.quoted_span);
  const ok = quoted.filter((x) => ["exact", "normalized"].includes(x.rule.quote_check?.status)).length;
  const method = t("m_" + j.method).startsWith("m_") ? j.method : t("m_" + j.method);
  return [
    tf("ls_1d", { c: t(j.city || "") || t(STATE_NAMES[d.address?.state] || "") }),
    tf("ls_2d", { n: applies, d: fmtDate(d.as_of) }),
    quoted.some((x) => x.rule.quote_check) ? tf("ls_3d", { a: ok, b: quoted.length }) : t("ls_3n"),
  ];
}
async function runSteps(d, my) {
  const facts = stepFacts(d);
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  for (let i = 1; i <= 3; i++) {
    if (my !== routing) return;
    const li = $(`.lstep[data-step="${i}"]`, main);
    if (!li) return;
    $("small", li).textContent = facts[i - 1];
    li.classList.remove("run"); li.classList.add("done");
    $(`.lstep[data-step="${i + 1}"]`, main)?.classList.add("run");
    await wait(i < 3 ? 170 : 260);
  }
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
  const my = routing;
  const url = addrUrl(id);
  let d = null;
  const p = api(url);
  const same = main.dataset.addr === id && !!$("article.addr:not(.is-loading)", main); // as-of / language change on this address: update in place
  const open = same ? $$(".topic[open]", main).map((x) => x.id) : [];
  let fromSteps = false;
  const fast = await Promise.race([p.then(() => true, () => false), new Promise((r) => setTimeout(() => r(false), 90))]);
  if (!same && !fast && !SEEN.has(id) && !RM.matches && ADDR.length) {
    fromSteps = true;
    await swap(stepsShell(id));
    $('.lstep[data-step="1"]', main)?.classList.add("run");
    const t0 = performance.now();
    try { d = await p; } catch { return my === routing ? viewNotFound("address") : undefined; }
    if (performance.now() - t0 < 120) await new Promise((r) => setTimeout(r, 120)); // let step one be seen
    await runSteps(d, my);
  } else {
    const quick = await Promise.race([p.then((x) => x, () => null), new Promise((r) => setTimeout(r, 140))]);
    if (quick) d = quick;
    if (!quick) {
      if (!same) await swap(addressSkeleton());
      progress(true);
      try { d = await p; } catch { progress(false); return my === routing ? viewNotFound("address") : undefined; }
      progress(false);
    }
  }
  if (my !== routing) return;
  SEEN.add(id);
  const a = d.address, j = d.jurisdiction;
  const methodLabel = t("m_" + j.method).startsWith("m_") ? j.method : t("m_" + j.method);
  // the county drops out when it repeats the city ("Los Angeles County", "City & County of San Francisco")
  const stack = j.stack.filter((s) => !(s.level === "county" && j.city && s.name.toLowerCase().includes(j.city.toLowerCase())))
    .map((s) => s.level === "city" ? `<span class="city">${esc(t(s.name))}</span>` : `<span>${esc(t(s.name))}</span>`);
  const units = a.units ? String(a.units) : a.units_min ? `${a.units_min}+` : "";
  const fact = (k, v, title = "") => `<div${title ? ` title="${esc(title)}"` : ""}><dt>${esc(k)}</dt><dd${v ? "" : ' class="na"'}>${esc(v || t("f_na"))}</dd></div>`;
  const slug = citySlug(j.city) || citySlug(a.postal_city);
  const row = (k, v) => v ? `<div><dt>${esc(k)}</dt><dd>${v}</dd></div>` : "";
  const enacted = d.categories.flatMap((c) => c.enacted || []);
  const nApply = enacted.filter((x) => x.result === "applies").length;
  const quoted = enacted.filter((x) => x.rule.quoted_span), qOk = quoted.filter((x) => ["exact", "normalized"].includes(x.rule.quote_check?.status)).length;
  const stat = (ico, k, v, title = "") => `<div${title ? ` title="${esc(title)}"` : ""}><span class="st-i" aria-hidden="true">${ico}</span><dt>${esc(k)}</dt><dd${v ? "" : ' class="na"'}>${esc(v || t("f_na"))}</dd></div>`;
  const sums = d.categories.map((c) => [c, topicSummary(c, d)]);
  const spots = ["rent_increase_limits", "just_cause_eviction", "security_deposits"].map((id) => sums.find(([c]) => c.id === id)).filter(Boolean)
    .map(([c, sm], i) => `<button type="button" class="spot spot-${i + 1}" data-goto="t-${c.id}"><small>${esc(t("cat_" + c.id))}</small><b>${esc(sm.line)}</b></button>`).join("");
  const coming = sums.filter(([, sm]) => sm.next).map(([c, sm]) => `<li><a href="#t-${c.id}" data-goto="t-${c.id}"><span class="cu-d">${esc(sm.next)}</span><span class="cu-t">${esc(t("cat_" + c.id))}</span></a></li>`).join("");
  const nNotLaw = d.categories.reduce((n, c) => n + (c.pending || []).length + (c.not_law || []).length, 0);
  const html = `
  <article class="addr">
    <section class="ahero">
      <div class="gal${slug ? " street" : ""}">${slug ? streetTag(slug, true) : imgTag("/static/img/hero-building-card.webp", "", "", true)}${spots}</div>
      <header class="addr-head">
        <p class="addr-top"><span class="cc-st">${esc(t(STATE_NAMES[a.state] || a.state))}</span><button type="button" class="linkish" data-how>${t("how_resolved")}</button></p>
        <h1>${esc(titleCase(a.street_address))}</h1>
        <p class="addr-sub">${esc(a.postal_city)}, ${esc(a.state)} ${esc(a.zip || "")}</p>
        <p class="addr-stack">${stack.join('<span class="sep" aria-hidden="true">›</span>')}</p>
        ${j.postal_differs ? `<p class="addr-meta strong">${esc(tf("mailing_legal", { p: a.postal_city, c: j.city }))}</p>` : ""}
        <p class="addr-line">${[j.city ? t(j.city) : "", a.year_built ? tf("built_l", { y: a.year_built }) : "", units ? tf("units_l", { n: units }) : ""].filter(Boolean).map(esc).join('<span class="sep" aria-hidden="true">·</span>')}</p>
        <div class="prop-cta">
          <a class="btn primary" href="#/check/${esc(a.address_id)}">${esc(t("check_cta"))}${I.arrow.replace('class="ico"', 'class="ico arrow-i"')}</a>
          <div class="addr-actions" data-slot="address-actions"></div>
        </div>
      </header>
    </section>
    <div class="adetail">
      <section class="answers">${answersHTML(d)}</section>
      <aside class="aside">
        <div class="aside-card"><div class="mini">${slug ? imgTag(`/static/img/${slug}-sm.webp`, "") : '<span class="mini-i"></span>'}<b>${esc(titleCase(a.street_address))}</b><span>${esc(tf("ls_2d", { n: nApply, d: fmtDate(d.as_of) }))}</span></div>
          <a class="btn primary" href="#/check/${esc(a.address_id)}">${esc(t("check_cta"))}${I.arrow.replace('class="ico"', 'class="ico arrow-i"')}</a></div>
        <div class="aside-card"><h2>${esc(t("cu_h"))}</h2>
          ${coming ? `<ul class="cu">${coming}</ul>` : `<p class="muted">${esc(t("cu_none"))}</p>`}
          <a class="btn cu-go" href="#/changes">${esc(t("cu_all"))}</a></div>
        ${nNotLaw ? `<a class="aside-card aside-nl" href="#nl-h"><b>${nNotLaw}</b><span>${esc(t("nl_n"))}</span>${I.chev}</a>` : ""}
      </aside>
    </div>
  </article>`;
  const howHtml = `<dl class="kv">
          ${row(t("method"), esc(methodLabel))}
          ${row(t("confidence"), `${pctOf(j.confidence)}%`)}
          ${row(lang === "en" ? "" : t("note_en"), j.note ? `<span lang="en">${esc(j.note)}</span>` : "")}
          ${row(t("county"), j.county ? esc(j.county) : "")}
          ${row(t("use"), a.use_description ? esc(a.use_description) : "")}
          ${row(t("data_from"), esc(a.source_dataset || ""))}
          ${row("ID", `<span class="mono">${esc(a.address_id)}</span>`)}
        </dl>`;
  if (same) { main.innerHTML = html; open.forEach((x) => { const el = document.getElementById(x); if (el) el.open = true; }); }
  else await swap(html, null, { quick: fromSteps });
  main.dataset.addr = id;
  try { sessionStorage.setItem("ce.place", j.city ? `${j.city}, ${a.state}` : a.state); } catch { /* private mode */ }
  if (ANS[id]) applyAnswers(id);
  const openT = sessionStorage.getItem("ce.open");
  if (openT) { sessionStorage.removeItem("ce.open"); const el = document.getElementById("t-" + openT); if (el) { el.open = true; setTimeout(() => el.scrollIntoView({ block: "start", behavior: RM.matches ? "auto" : "smooth" }), 60); } }
  const exq = sessionStorage.getItem("ce.example");
  if (exq) { sessionStorage.removeItem("ce.example"); $(".answers", main)?.insertAdjacentHTML("afterbegin", `<p class="ex-banner">${I.info}<span>${esc(tf("ex_banner", { q: exq }))}</span><button type="button" class="linkish" data-cmdk>${esc(t("ex_enter"))}</button></p>`); }
  $("[data-how]", main)?.addEventListener("click", () => openModal(t("how_resolved"), howHtml));
  document.title = `${titleCase(a.street_address)}, ${a.postal_city} · Clause & Effect`;
}

// hotspots on the photo and "Coming up" links open their topic in the list and bring it into view
function gotoTopic(e) {
  const b = e.target.closest("[data-goto]");
  if (!b) return;
  e.preventDefault();
  const el = document.getElementById(b.dataset.goto);
  if (!el) return;
  el.open = true;
  el.scrollIntoView({ block: "start", behavior: RM.matches ? "auto" : "smooth" });
  el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash");
}
document.addEventListener("click", (e) => { if (e.target.closest("#main [data-goto]")) gotoTopic(e); });
// answers to the "unknown" questions, per address, kept on this device
const ANS = JSON.parse(localStorage.getItem("ce.ans") || "{}");
const FKEY = { year: "year_built", units: "units", owner: "owner_occupied" };
const saveAns = () => { try { localStorage.setItem("ce.ans", JSON.stringify(ANS)); } catch { /* private mode */ } };
async function evalFacts(d, extra) {
  const a = d.address, j = d.jurisdiction;
  const facts = { year_built: a.year_built ? +a.year_built : undefined, units: a.units ? +a.units : a.units_min ? +a.units_min : undefined, ...extra };
  Object.keys(facts).forEach((k) => facts[k] === undefined && delete facts[k]);
  const r = await fetch("/api/evaluate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ address: { state: a.state, jurisdiction: j.city ? `${j.city}, ${a.state}` : null }, as_of: asOf, lang, facts }) });
  if (!r.ok) throw new Error(r.status);
  return r.json();
}
document.addEventListener("click", async (e) => {
  const b = e.target.closest(".fq [data-val]");
  if (!b) return;
  const box = b.closest(".fq"), id = main.dataset.addr, key = FKEY[box.dataset.ask], val = b.dataset.val;
  $$("[data-val]", box).forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
  if (val === "unsure") { if (!$(".fq-note", box)) box.insertAdjacentHTML("beforeend", `<p class="fq-note">${esc(t("ask_unsure_" + box.dataset.ask))}</p>`); return; }
  if (!main.contains(box) || box.closest("[data-fact-owner]")) { // answers rendered for a caller (any-address sheet, Rules): it re-evaluates
    box.classList.add("busy");
    box.dispatchEvent(new CustomEvent("ce:fact", { bubbles: true, detail: { key, value: val === "true" ? true : val === "false" ? false : +val, said: b.dataset.said || b.textContent.trim() } }));
    return;
  }
  ANS[id] = { ...(ANS[id] || {}), [key]: val === "true" ? true : val === "false" ? false : +val, ["_" + key]: b.dataset.said || b.textContent.trim() };
  saveAns();
  box.classList.add("busy");
  await applyAnswers(id, { announce: true });
});
// preview under a yes/no question: what each answer would mean (two engine runs, nothing invented)
document.addEventListener("toggle", async (e) => {
  const det = e.target;
  if (!det.matches?.("#main details.topic") || !det.open) return;
  const box = $(".fq[data-preview]", det);
  if (!box || box.dataset.done) return;
  box.dataset.done = 1;
  try {
    const d = await api(addrUrl(main.dataset.addr)), key = FKEY[box.dataset.ask];
    const vals = box.dataset.preview.split(",").map((v) => v === "true" ? true : v === "false" ? false : +v);
    const outs = await Promise.all(vals.map((v) => evalFacts(d, { ...(ANS[main.dataset.addr] || {}), [key]: v })));
    const line = (v) => { const c = v.categories.find((x) => x.id === box.dataset.cat); return c ? topicSummary(c, { ...d, categories: v.categories }).line : ""; };
    const [ly, ln] = outs.map(line);
    if (ly && ln && box.isConnected) $(".fq-pre", box).textContent = tf("ask_pre", { y: ly.replace(/\.$/, ""), n: ln.replace(/\.$/, "") });
  } catch { /* the question still works without the preview */ }
}, true);
async function applyAnswers(id, { announce = false } = {}) {
  const d = await api(addrUrl(id));
  if (!ANS[id]) return;
  const f = Object.fromEntries(Object.entries(ANS[id]).filter(([k]) => !k.startsWith("_")));
  let v;
  try { v = await evalFacts(d, f); } catch { toast(t("ask_fail")); $$(".fq.busy").forEach((x) => x.classList.remove("busy")); return; }
  if (main.dataset.addr !== id) return;
  let n = 0;
  const cats = d.categories.map((c) => {
    const top = ordered(c.enacted || [])[0];
    if (!top || top.result !== "unknown") return c;
    const nc = v.categories.find((x) => x.id === c.id);
    return nc || c;
  });
  const dd = { ...d, categories: cats };
  for (const c of d.categories) {
    const nc = cats.find((x) => x.id === c.id);
    if (nc === c) continue;
    const el = document.getElementById("t-" + c.id);
    if (!el) continue;
    const wasOpen = el.open;
    const ntop = ordered(nc.enacted || [])[0];
    el.outerHTML = topicRow(nc, dd, { asked: !ntop || ntop.result !== "unknown" });
    const ne = document.getElementById("t-" + c.id);
    if (wasOpen) ne.open = true;
    if (announce) { ne.classList.add("pop"); if (wasOpen) ne.scrollIntoView({ block: "nearest", behavior: "auto" }); }
    n++;
  }
  saidChip(id);
  if (announce && n) toast(tf(n === 1 ? "ans_upd1" : "ans_updN", { n }));
  document.dispatchEvent(new CustomEvent("ce:route", { detail: { view: "lookup", arg: id } })); // slots refill
}
function saidChip(id) {
  const head = $(".answers-head", main);
  if (!head) return;
  $(".said", head)?.remove();
  const a = ANS[id];
  if (!a) return;
  const said = Object.entries(a).filter(([k]) => k.startsWith("_")).map(([k, v]) => tf("said_" + k.slice(1), { v: String(v).replace(/^[A-Z]/, (m) => m.toLowerCase()) })).join(" · ");
  head.insertAdjacentHTML("beforeend", `<p class="said">${I.check}<span>${esc(tf("said", { s: said }))}</span><button type="button" class="linkish" data-said-x>${esc(t("change"))}</button></p>`);
}
document.addEventListener("click", (e) => {
  if (!e.target.closest("#main [data-said-x]")) return;
  delete ANS[main.dataset.addr]; saveAns();
  route({ keepScroll: true, soft: true });
});
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
  let d;
  try { d = await api(`/api/source/${doc}?rule_id=${encodeURIComponent(rule || "")}`); }
  catch (e) { // #141: say what happened instead of a skeleton forever
    const m = $("#modal");
    if (!m.hidden) $(".modal-body", m).innerHTML = `<p class="lead-p">${esc(t(/404/.test(e.message) ? "src_missing" : "src_error"))}</p>`;
    return;
  }
  // first line = the page title; then the text. Around the quote, page chrome (short lines that are not sentences:
  // "Skip to main content", "news", menu words) is left out; "Show the whole document" shows everything.
  const txt = d.text, hl = d.highlight;
  const nl = txt.indexOf("\n"), title = (nl > 0 ? txt.slice(0, nl) : "").replace(/\s*[|·–-]\s*[^|·–-]{2,30}$/, "").trim();
  const start = nl > 0 && title.length < 160 ? nl + 1 : 0;
  const mark = (a, b) => hl && hl[0] >= a && hl[0] < b ? esc(txt.slice(a, hl[0])) + `<mark id="hlm">${esc(txt.slice(hl[0], Math.min(hl[1], b)))}</mark>` + esc(txt.slice(Math.min(hl[1], b), b)) : esc(txt.slice(a, b));
  const full = () => mark(start, txt.length);
  let excerpt = "";
  if (hl) {
    const lines = []; let i = start;
    while (i < txt.length) { let j = txt.indexOf("\n", i); if (j < 0) j = txt.length; lines.push([i, j]); i = j + 1; }
    const chrome = ([a, b]) => { const l = txt.slice(a, b).trim(); return !l || (l.split(/\s+/).length < 5 && !/[.;:]$/.test(l)); };
    const k = lines.findIndex(([a, b]) => hl[0] >= a && hl[0] <= b);
    const keep = [];
    for (let x = k - 1, n = 0; x >= 0 && n < 2; x--) if (!chrome(lines[x])) { keep.unshift(x); n++; }
    keep.push(k);
    for (let x = k + 1, n = 0; x < lines.length && n < 2; x++) if (!chrome(lines[x]) || (hl[1] > lines[x][0] && hl[1] <= lines[x][1])) { keep.push(x); n++; }
    // one paragraph per kept line; a line that starts with punctuation continues the previous one; the title is not repeated
    const paras = [];
    for (const x of keep) {
      const html = mark(lines[x][0], Math.max(lines[x][1], x === k ? Math.min(hl[1], txt.length) : 0));
      const raw = txt.slice(lines[x][0], lines[x][1]).trim();
      if (!paras.length && raw === title) continue;
      const words = (x) => new Set(x.toLowerCase().match(/[a-z0-9.%$]{3,}/g) || []);
      const hw = words(txt.slice(hl[0], hl[1])), lw = words(raw);
      if (x !== k && lw.size && [...lw].filter((w) => hw.has(w)).length / lw.size >= .8) continue; // the same sentence again (heading + body)
      if (paras.length && /^[,.;:)\]]/.test(raw)) paras[paras.length - 1] += html; else paras.push(html);
    }
    excerpt = paras.map((h) => `<p>${h}</p>`).join("");
  }
  $("#modal-title").innerHTML = title ? `<span class="doc-title">${esc(title)}</span>` : esc(host(d.meta.url) || doc);
  $(".modal-body").innerHTML = `<p class="rd-meta">${d.meta.url ? `<a href="${esc(d.meta.url)}" target="_blank" rel="noopener">${esc(host(d.meta.url))}${I.ext}</a>` : ""}<span class="sep">·</span>${esc(tf("retrieved", { d: fmtDate(d.meta.retrieved_at) }))}</p>
    <div class="doc-text${excerpt ? " doc-ex" : ""}">${excerpt || full()}</div>${excerpt ? `<p class="doc-more"><button type="button" class="btn" id="doc-all">${esc(t("doc_all"))}</button></p>` : ""}`;
  $("#doc-all")?.addEventListener("click", () => { const dt = $(".doc-text"); dt.classList.remove("doc-ex"); dt.innerHTML = full(); $(".doc-more").remove(); $("#hlm")?.scrollIntoView({ block: "center", behavior: "auto" }); });
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
let CH_PLACE = null;
async function viewChanges() {
  progress(true);
  const [tl, rules] = await Promise.all([api(`/api/timeline?lang=${lang}`), api(`/api/rules?lang=${lang}&as_of=${asOf}`).catch(() => [])]);
  progress(false);
  const R = Object.fromEntries(rules.map((r) => [r.team_rule_id, r]));
  const place = (e) => e.jurisdiction.length === 2 ? t(STATE_NAMES[e.jurisdiction] || e.jurisdiction) : shortJ(e.jurisdiction);
  const places = [...new Set(tl.filter((e) => e.date >= "2024-01-01").map(place))].sort();
  if (CH_PLACE === null) { const last = sessionStorage.getItem("ce.place") || ""; const p0 = last.length === 2 ? t(STATE_NAMES[last] || last) : shortJ(last); CH_PLACE = places.includes(p0) ? p0 : ""; }
  const pf = CH_PLACE && places.includes(CH_PLACE) ? CH_PLACE : "";
  const inPlace = (e) => !pf || place(e) === pf || (STATE_NAMES[e.jurisdiction] && CITIES.some((x) => x.c === pf && x.s === e.jurisdiction));
  const shown = tl.filter((e) => e.date >= "2024-01-01" && inPlace(e)), older = tl.filter((e) => e.date < "2024-01-01" && inPlace(e));
  // a change in plain words: the rule's short answer first, its legal title second
  const plainOf = (e) => { const r = R[e.id]; return r ? (r.answer_display && !(r.plain_until && e.date > r.plain_until) ? r.answer_display : r.headline_display) || r.title_display || e.title : e.title; };
  const stop = (x) => /[.!?]$/.test(x) ? x : x + "."; // one rule for every Changes headline: a full stop
  const tlCut = (m) => { const x = new Date(asOf + "T12:00:00"); x.setMonth(x.getMonth() + m); return x.toISOString().slice(0, 10); };
  const back12 = tlCut(-12), next12 = tlCut(12);
  const all = tl.filter(inPlace);
  const sections = [
    ["ch_next", all.filter((e) => e.date > asOf && e.date <= next12), true],
    ["ch_later", all.filter((e) => e.date > next12), true],
    ["ch_recent", all.filter((e) => e.date <= asOf && e.date > back12).reverse(), true],
    ["ch_earlier", all.filter((e) => e.date <= back12).reverse(), false],
  ];
  const evRow = (e) => { const r = R[e.id]; const later = e.date > asOf; return `<li class="tv-i${later ? " is-later" : ""}"><details class="ev-x"><summary class="ev" data-date="${e.date}"><span class="tv-dot" aria-hidden="true"></span><span class="ev-main"><span class="ev-d">${esc(fmtDate(e.date))}<span class="ev-s"> · ${esc(place(e))} · ${esc(t("cat_" + e.category))}</span></span><span class="ev-t">${esc(stop(cap(plainOf(e))))}</span></span><span class="ev-st"></span><span class="chev">${I.chev}</span></summary>
        <div class="ev-body">${r?.why_display ? `<p class="why">${esc(r.why_display)}</p>` : ""}${e.addresses ? `<p class="ev-title">${esc(tf("ch_reach", { n: e.addresses }))}</p>` : ""}
          <details class="law"><summary><span>${esc(t("law_show"))}</span><span class="chev">${I.chev}</span></summary><div class="law-in">
          <p class="ev-title">${esc(r?.title_display || e.title)}</p>
          ${r?.quoted_span ? `<blockquote class="quote" lang="en">${esc(shownQuote(r.quoted_span))}</blockquote><p class="rd-cite">${r.citation ? `<span>${esc(r.citation)}</span>` : ""}${r.source_url ? `<a href="${esc(r.source_url)}" target="_blank" rel="noopener">${esc(srcLabel(r))}${I.ext}</a>` : ""}${r.retrieved_at ? `<span>${esc(tf("retrieved", { d: fmtDate(r.retrieved_at) }))}</span>` : ""}</p>` : ""}</div></details>
          <p class="ev-go"><button type="button" class="btn" data-goto-date="${e.date}">${esc(tf("ch_see", { d: fmtDate(e.date) }))}</button></p></div></details></li>`; };
  const sec = ([k, xs, open]) => xs.length ? (open ? `<section class="tv-s"><h2>${esc(t(k))} <span>${xs.length}</span></h2><ol class="tv">${xs.map(evRow).join("")}</ol></section>`
    : `<details class="tv-s tv-old"><summary><h2>${esc(t(k))} <span>${xs.length}</span></h2><span class="chev">${I.chev}</span></summary><ol class="tv">${xs.map(evRow).join("")}</ol></details>`) : "";
  const html = `
    <header class="page-head"><h1>${esc(t("ch_h"))}</h1><p>${esc(t("ch_lead"))}</p></header>
    <div class="chips-f" role="group" aria-label="${esc(t("ch_place"))}">${["", ...places].map((p) => `<button type="button" class="chip-f" data-place="${esc(p)}" aria-pressed="${p === pf}">${esc(p || t("all"))}</button>`).join("")}</div>
    <div id="events" class="tv-wrap">${sections.map(sec).join("") || `<p class="empty">${esc(t("ch_none"))}</p>`}</div>
    <section class="block ch-big"><div class="answers-head"><h2>${esc(t("ch_big"))}</h2><p class="note">${esc(t("ch_big_s"))}</p></div>
    <div data-slot="changes-top"></div>
    <section class="tl panel" aria-label="${t("timeline_aria")}">
      <div class="tl-top"><b id="tl-date"></b><span id="tl-sum"></span></div>
      <div class="tl-track"><div class="tl-line"></div><div class="tl-fill" id="tl-fill"></div>
        ${[...new Set(shown.map((e) => e.date))].map((d) => `<i class="tl-tick" data-date="${d}" style="left:${pct(d)}%" aria-hidden="true"></i>`).join("")}
        <input type="range" class="tl-range" id="tl-range" min="0" max="${TL_MAX}" value="${dayIdx(asOf)}" aria-label="${t("asof_aria")}">
      </div>
      <div class="tl-years" aria-hidden="true">${[2024, 2025, 2026, 2027, 2028].map((y) => `<span style="left:${pct(y + "-01-01")}%">${y}</span>`).join("")}</div>
    </section></section>`;
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
        r.querySelector(".ev-st").innerHTML = now ? "" : badge("not_yet_effective", "", null, t("not_yet"));
      });
      const live = tl.filter((e) => e.date <= d).length;
      $("#tl-sum").textContent = `${tf("in_effect", { n: live })} · ${tf("upcoming", { n: tl.length - live })}`;
    };
    paint(asOf);
    range.addEventListener("input", () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(() => paint(idxDay(+range.value))); });
    range.addEventListener("change", () => { $("#asof").value = idxDay(+range.value); setAsOf(idxDay(+range.value), { silent: true }); });
    $$(".chip-f").forEach((b) => b.addEventListener("click", () => { CH_PLACE = b.dataset.place; route({ keepScroll: true, soft: true }); }));
    // time travel only on request: the whole app answers on that date (the header shows it, × resets)
    $$("#events [data-goto-date]").forEach((b) => b.addEventListener("click", () => { $("#asof").value = b.dataset.gotoDate; setAsOf(b.dataset.gotoDate); }));
  });
}

// ------------------------------------------------------------------ rules explorer --
const plural = (n, one, many) => tf(n === 1 ? one : many, { n });
const rulesSentence = (all, inForce, later, pending, open, failed) =>
  tf("rules_sentence", { all: plural(all, "n_rule1", "n_ruleN"), a: plural(inForce, "n_force1", "n_forceN"), b: plural(later, "n_later1", "n_laterN"), c: plural(pending, "n_bill1", "n_billN"), e: plural(failed, "n_fail1", "n_failN"), d: plural(open, "n_open1", "n_openN") });
let RF = { jur: "", cat: "", status: "", q: "", conflicts: false }, RT_OPEN = false;
// Rules: "What are the rules where I live?" Pick a place; its six topics answer like an address page (the engine
// with no building facts, POST /api/evaluate), unknowns ask their one question. The matrix is "Compare all places".
let RP_PLACE = "", RP_FACTS = {};
async function viewRules(jur) {
  progress(true);
  const [rules, cov] = await Promise.all([api(`/api/rules?lang=${lang}&as_of=${asOf}`), api(`/api/coverage?as_of=${asOf}`)]);
  progress(false);
  const places = cov.jurisdictions;
  if (jur && places.includes(jur)) { if (jur !== RP_PLACE) RP_FACTS = {}; RP_PLACE = jur; }
  if (!places.includes(RP_PLACE)) { const last = sessionStorage.getItem("ce.place"); RP_PLACE = places.includes(last) ? last : "San Francisco, CA"; }
  const pname = (j) => j.length === 2 ? t(STATE_NAMES[j] || j) : shortJ(j);
  const chips = ["CA", "NJ", "MA"].map((S) => `<div class="pc-row" data-st="${S}"><span class="pc-l">${esc(t(STATE_NAMES[S]))}</span>${places.filter((j) => j === S || j.endsWith(", " + S)).map((j) => `<button type="button" class="chip-f" data-place="${esc(j)}" aria-pressed="${j === RP_PLACE}">${esc(j === S ? t("pc_state") : shortJ(j))}</button>`).join("")}</div>`).join("");
  const catLabel = Object.fromEntries(cov.categories.map((c) => [c.id, t("cat_" + c.id)]));
  const count = (s) => rules.filter((r) => r.status === s).length;
  const html = `
    <header class="page-head"><h1>${esc(t("rp_h"))}</h1><p>${esc(t("rp_lead"))}</p></header>
    <div class="pc-seg" role="tablist" aria-label="${esc(t("ch_place"))}">${["CA", "NJ", "MA"].map((S) => `<button type="button" role="tab" data-state="${S}" aria-selected="${(RP_PLACE.length === 2 ? RP_PLACE : RP_PLACE.slice(-2)) === S}" aria-label="${esc(t(STATE_NAMES[S]))}"><span class="l-full">${esc(t(STATE_NAMES[S]))}</span><span class="l-abbr" aria-hidden="true">${S}</span></button>`).join("")}</div>
    <div class="pc" role="group" aria-label="${esc(t("ch_place"))}" data-state="${RP_PLACE.length === 2 ? RP_PLACE : RP_PLACE.slice(-2)}">${chips}</div>
    <section class="answers rp-answers" id="rp-answers" data-fact-owner aria-live="polite"></section>
    <details class="block rev" id="rules-all"${RT_OPEN ? " open" : ""}><summary><h2>${esc(t("rp_all"))}</h2><span class="rev-s">${esc(rulesSentence(rules.length, count("in_force"), count("not_yet_effective"), count("pending"), rules.filter((r) => r.conflict_flag).length, count("failed")))}</span><span class="chev">${I.chev}</span></summary>
    <section class="block panel"><h2>${t("coverage")}</h2>
      <div class="table-wrap"><table class="matrix"><thead><tr><th><span class="sr">${t("jurisdiction")}</span></th>${cov.categories.map((c) => `<th>${esc(catLabel[c.id])}</th>`).join("")}</tr></thead>
      <tbody>${cov.jurisdictions.map((j) => `<tr class="${j.length === 2 ? "state" : "city"}"><th>${esc(j.length === 2 ? t(STATE_NAMES[j] || j) : shortJ(j))}</th>${cov.categories.map((c) => {
        const cell = cov.cells[j]?.[c.id] || [];
        const nr = cov.no_rule_cells?.[j]?.[c.id];
        return `<td>${cell.length ? `<button type="button" data-j="${esc(j)}" data-c="${c.id}" title="${esc(cell.map((x) => x.title).join("\n"))}">${cell.length}</button>` : nr ? `<button type="button" class="none finding" data-nr="${esc(nr.id)}" aria-label="${esc(t("legend_nr"))}">–</button>` : `<span class="none" role="img" aria-label="${esc(t("none_level"))}">–</span>`}</td>`;
      }).join("")}</tr>`).join("")}</tbody></table></div>
      <p class="legend">${esc(t("matrix_note"))}</p>
    </section>
    <details class="block disclose panel" id="rules-table"><summary><h2>${tf("show_table", { n: rules.length })}</h2><span class="chev">${I.chev}</span></summary>
      <div class="filters">
        <select id="f-j" aria-label="${t("jurisdiction")}"><option value="">${t("jurisdiction")}: ${t("all")}</option>${cov.jurisdictions.map((j) => `<option value="${esc(j)}">${esc(j)}</option>`).join("")}</select>
        <select id="f-c" aria-label="${t("category")}"><option value="">${t("category")}: ${t("all")}</option>${cov.categories.map((c) => `<option value="${c.id}">${esc(catLabel[c.id])}</option>`).join("")}</select>
        <select id="f-s" aria-label="${t("status")}"><option value="">${t("status")}: ${t("all")}</option>${["in_force", "not_yet_effective", "pending", "failed"].map((s) => `<option value="${s}">${esc(resLabel(s))}</option>`).join("")}</select>
        <input type="search" id="f-q" placeholder="${t("q_filter")}" aria-label="${t("q_filter")}">
        <label class="chk"><input type="checkbox" id="f-x"> ${t("only_conflicts")}</label>
      </div>
      <p class="count-note" id="rc"></p>
      <div class="table-wrap"><table class="rtable"><thead><tr><th>${t("col_rule")}</th><th>${t("key_value")}</th><th>${t("status")}</th><th>${t("effective")}</th><th>${t("col_addresses")}</th></tr></thead><tbody id="rt"></tbody></table></div>
    </details></details>`;
  await swap(html, () => {
    const draw = () => {
      const q = RF.q.trim().toLowerCase();
      const list = rules.filter((r) => (!RF.jur || r.jurisdiction === RF.jur) && (!RF.cat || r.category === RF.cat) && (!RF.status || r.status === RF.status) && (!RF.conflicts || r.conflict_flag) && (!q || JSON.stringify([r.team_rule_id, r.title, r.title_display, r.requirement, r.citation, r.key_value]).toLowerCase().includes(q)));
      $("#rc").textContent = `${list.length} / ${tf("rules_n", { n: rules.length })}`;
      $("#rt").innerHTML = list.map((r) => `<tr class="clickable" data-rule="${esc(r.team_rule_id)}" tabindex="0">
        <td><div class="t">${esc(r.title_display || r.title)}</div><div class="s">${esc(r.jurisdiction)} · ${esc(catLabel[r.category] || r.category)} · <span class="mono">${esc(r.team_rule_id)}</span></div></td>
        <td class="kvc">${esc(r.key_value_display || r.key_value || "–")}</td><td>${badge(r.status)}${r.conflict_flag ? `<div class="s">${t("conflict")}</div>` : ""}</td><td class="s nw">${esc(r.effective_date ? fmtDate(r.effective_date_norm || r.effective_date) : "–")}</td><td class="num">${r.addresses_count}<span class="m-only"> ${esc(t("col_addresses").toLowerCase())}</span></td></tr>`).join("")
        || `<tr><td colspan="5" class="empty">${t("no_rules_match")} <button type="button" class="linkish" id="f-clear">${t("clear_filters")}</button></td></tr>`;
      $("#f-clear")?.addEventListener("click", () => { RF = { jur: "", cat: "", status: "", q: "", conflicts: false }; sync(); });
    };
    const sync = () => { $("#f-j").value = RF.jur; $("#f-c").value = RF.cat; $("#f-s").value = RF.status; $("#f-q").value = RF.q; $("#f-x").checked = RF.conflicts; draw(); };
    $("#rules-all").addEventListener("toggle", (e) => { if (e.target.id === "rules-all") RT_OPEN = e.target.open; });
    // the place's answers
    const box = $("#rp-answers");
    const load = async () => {
      const j = RP_PLACE, st = j.length === 2 ? j : j.slice(-2);
      box.classList.add("aa-stale");
      const open = $$("details.topic[open]", box).map((x) => x.id);
      let v;
      try { const r = await fetch("/api/evaluate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ address: { state: st, jurisdiction: j.length === 2 ? null : j }, as_of: asOf, lang, facts: RP_FACTS }) }); if (!r.ok) throw 0; v = await r.json(); }
      catch { box.classList.remove("aa-stale"); box.innerHTML = `<p class="empty">${esc(t("error"))}</p>`; return; }
      if (!box.isConnected || j !== RP_PLACE) return;
      CE_render(box, v, { ask: true, place: true, heading: tf("rp_in", { p: pname(j) }) });
      open.forEach((id) => { const x = box.querySelector("#" + CSS.escape(id)); if (x) { x.open = true; x.classList.add("pop"); } });
      box.classList.remove("aa-stale");
    };
    $$(".pc-seg button").forEach((b) => b.addEventListener("click", () => {
      $$(".pc-seg button").forEach((x) => x.setAttribute("aria-selected", String(x === b)));
      $(".pc").dataset.state = b.dataset.state;
    }));
    box.addEventListener("ce:fact", (e) => { RP_FACTS = { ...RP_FACTS, [e.detail.key]: e.detail.value }; load(); });
    $$(".pc .chip-f").forEach((b) => b.addEventListener("click", () => {
      if (b.dataset.place === RP_PLACE) return;
      RP_PLACE = b.dataset.place; RP_FACTS = {};
      $$(".pc .chip-f").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      load();
    }));
    load();
    $("#f-j").onchange = (e) => { RF.jur = e.target.value; draw(); };
    $("#f-c").onchange = (e) => { RF.cat = e.target.value; draw(); };
    $("#f-s").onchange = (e) => { RF.status = e.target.value; draw(); };
    $("#f-q").oninput = (e) => { RF.q = e.target.value; draw(); };
    $("#f-x").onchange = (e) => { RF.conflicts = e.target.checked; draw(); };
    $$(".matrix button[data-nr]").forEach((b) => b.onclick = () => {
      const f = cov.no_rule_findings.find((x) => x.finding_id === b.dataset.nr);
      openModal(`${f.jurisdiction} · ${catLabel[f.category] || f.category}`, `<div class="rd"><p class="rd-plain">${esc(f.finding)}</p>${sourceHtml({ quote: f.quoted_span, citation: f.citation, url: f.source_url, id: f.finding_id, rule: f.finding_id, doc: f.quoted_span_doc_id || f.source_doc_id })}</div>`);
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
  return `<details class="topic plain" id="check-${esc(x.test_id)}"><summary><span class="topic-main"><span class="topic-q">${esc(x.title_display || x.title)}</span><span class="topic-a">${esc(t("t_" + x.type))} · ${rulesLine}</span></span><span class="num-b">${esc(tf("addresses_n", { n: x.affected_count }))}</span><span class="chev">${I.chev}</span></summary>
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
  const [d, tests, rules] = await Promise.all([api("/api/audit", { fresh: true }), api(`/api/changes?lang=${lang}&as_of=${asOf}`), api(`/api/rules?lang=${lang}&as_of=${asOf}`).catch(() => [])]);
  progress(false);
  const ver = d.verification, vt = Object.values(ver).reduce((a, b) => a + b, 0);
  const steps = ["ingest", "extract", "resolve", "apply", "track"].map((k) => [t("p_" + k), tf(`p_${k}_d`, { n: d.documents.length })]);
  const geoTotal = Object.values(d.geocoding).reduce((a, b) => a + b, 0);
  const verifiedN = (ver.exact || 0) + (ver.normalized || 0);
  const sec = (id, title, body) => `<details class="topic plain" id="${id}"><summary><span class="topic-main"><span class="topic-q">${title}</span></span><span class="chev">${I.chev}</span></summary><div class="topic-body">${body}</div></details>`;
  // the retrieval dates of the official texts, as one line
  const days = d.documents.map((x) => (x.retrieved_at || "").slice(0, 10)).filter(Boolean).sort();
  const retrieved = days.length ? (days[0] === days.at(-1) ? fmtDate(days[0]) : `${fmtDate(days[0])} – ${fmtDate(days.at(-1))}`) : "";
  const official = d.documents.filter((x) => x.source_type === "official").length;
  // sources grouped by place: state, then its cities
  const ORDER = ["CA", "NJ", "MA"];
  const st = (j) => j.length === 2 ? j : j.slice(-2);
  const row = (x) => {
    const pub = host(x.url), name = x.title && x.title !== x.doc_id ? x.title : tf("page_on", { h: pub });
    const badge = x.quote_checked ? `<span class="sb ok">${I.check}${esc(t("sb_checked"))}</span>` : x.text_available ? `<span class="sb">${esc(t("sb_text"))}</span>` : `<span class="sb warn">${esc(t("sb_link"))}</span>`;
    const attrs = x.text_available ? `href="#" data-doc="${esc(x.doc_id)}"` : `href="${esc(x.url)}" target="_blank" rel="noopener"`;
    return `<li class="sr-row" data-q="${esc(`${name} ${pub} ${x.jurisdictions}`.toLowerCase())}"><a class="sr-a" ${attrs}><span class="sr-m"><span class="sr-t">${esc(name)}</span><span class="sr-s">${esc(pub)}${x.source_type !== "official" ? ` · ${esc(t("sb_secondary"))}` : ""}${x.retrieved_at ? ` · ${esc(tf("retrieved", { d: fmtDate(x.retrieved_at) }))}` : ""}</span></span>${badge}${x.text_available ? I.chev : I.ext}</a></li>`;
  };
  const groups = ORDER.map((S) => {
    const xs = d.documents.filter((x) => st(x.jurisdictions) === S);
    const cities = [...new Set(xs.filter((x) => x.jurisdictions.length > 2).map((x) => x.jurisdictions))].sort();
    const part = (label, ys) => ys.length ? `<div class="sr-sub" data-sub><h4>${esc(label)} <span>${ys.length}</span></h4><ul>${ys.map(row).join("")}</ul></div>` : "";
    const nOk = xs.filter((x) => x.quote_checked).length;
    return `<details class="sr-g" data-group><summary><h3>${esc(t(STATE_NAMES[S]))}</h3><span class="sr-gs">${esc(tf("srcs_n", { n: xs.length, k: nOk }))}</span><span class="chev">${I.chev}</span></summary>${part(tf("state_law", { s: t(STATE_NAMES[S]) }), xs.filter((x) => x.jurisdictions === S))}${cities.map((c) => part(shortJ(c), xs.filter((x) => x.jurisdictions === c))).join("")}</details>`;
  }).join("");
  const flagged = rules.filter((r) => r.conflict_flag || (r.confidence != null && r.confidence < 0.7));
  const html = `
    <section class="src-hero">
      <img class="src-statue" src="/static/img/hero-justice.webp" alt="" decoding="async" data-spring="bg" onerror="this.remove()">
      <header class="page-head"><h1>${esc(t("src_h"))}</h1><p>${esc(t("src_lead"))}</p></header>
    </section>
    <dl class="facts3">
      <div><dd>${d.documents.length}</dd><dt>${esc(tf("f3_docs", { n: official }))}</dt></div>
      <div><dd>${verifiedN}/${vt}</dd><dt>${esc(t("f3_quotes"))}</dt></div>
      <div><dd class="f3-date">${esc(retrieved)}</dd><dt>${esc(t("f3_when"))}</dt></div>
    </dl>
    <section class="block how3"><h2>${esc(t("how_h"))}</h2>
      <ol>${[["read", "magnifier-over-document"], ["check", "shield-check"], ["apply", "house-with-checkmark"]].map(([k, img], i) => `<li><span class="how3-i"><img src="/static/img/${img}.webp" alt="" loading="lazy" decoding="async" data-spring onerror="this.remove()"></span><b><span class="how3-n">${i + 1}</span>${esc(t("how_" + k))}</b><p>${esc(tf("how_" + k + "_d", { n: d.documents.length, o: official, q: vt }))}</p></li>`).join("")}</ol></section>
    <section class="block srcs"><div class="answers-head"><h2>${esc(t("srcs_h"))}</h2></div>
      <label class="sr-find">${I.search}<input type="search" id="sq" placeholder="${esc(t("srcs_find"))}" aria-label="${esc(t("srcs_find"))}"></label>
      <div class="sr-list">${groups}</div><p class="empty" id="sq-none" hidden>${esc(t("srcs_none"))}</p></section>
    <details class="block rev" id="reviewers"><summary><h2>${esc(t("rev_h"))}</h2><span class="rev-s">${esc(t("rev_s"))}</span><span class="chev">${I.chev}</span></summary>
    <dl class="stats">
      <div><dt>${esc(t("k_docs"))}</dt><dd>${d.documents.length}</dd></div>
      <div><dt>${esc(t("k_geo"))}</dt><dd>${geoTotal}</dd></div>
      <div><dt>${esc(t("k_log"))}</dt><dd>${d.audit_total}</dd></div>
    </dl>
    <p class="rev-ask" id="rev-ask" hidden><a class="btn" href="/ask/audit">${I.doc}<span>${esc(t("rev_ask"))}</span></a></p>
    <section class="block panel"><h2>${esc(tf("rev_flags", { n: flagged.length }))}</h2>
      <ul class="flags-l">${flagged.map((r) => `<li><b>${esc(r.title_display || r.title)}</b><span class="sr-s">${esc(shortJ(r.jurisdiction))}${r.confidence != null ? ` · ${esc(tf("conf_l", { n: pctOf(r.confidence) }))}` : ""}</span>${r.conflict_note ? `<p>${esc(r.conflict_note_display || r.conflict_note)}</p>` : ""}</li>`).join("")}</ul></section>
    <section class="block panel"><h2>${t("method_t")}</h2>
      <ol class="steps">${steps.map((x) => `<li><b>${esc(x[0])}</b><span>${esc(x[1])}</span></li>`).join("")}</ol></section>
    <section class="block"><div class="answers-head"><h2>${t("checks_t")}</h2><p class="note">${t("checks_lead")}</p></div>
      <div class="topics group">${tests.map(checkRow).join("")}</div></section>
    <section class="block"><div class="topics group">
      ${sec("a-scale", t("a_scale"), `<ol class="steps">${[1, 2, 3, 4].map((n) => `<li><b>${esc(t(`s${n}_t`))}</b><span>${esc(t("s" + n))}</span></li>`).join("")}</ol>`)}
      ${sec("a-files", t("a_files"), `<dl class="kv">${Object.entries(d.sources).map(([n, src]) => `<div><dt class="mono">${esc(n)}</dt><dd>${esc(src.kind)}${src.modified ? ` · ${esc(src.modified.replace("T", " "))}` : ""}</dd></div>`).join("")}</dl>
        <p class="block-lead">${esc(tf("a_spans", { a: verifiedN, b: vt }))}${ver.not_found ? `; ${esc(tf("a_notfound", { n: ver.not_found }))}` : ""}${ver.no_text ? `; ${esc(tf("a_notext", { n: ver.no_text }))}` : ""}.</p>`)}
      ${sec("a-geo", t("a_geo"), `<dl class="kv">${Object.entries(d.geocoding).map(([k, v]) => `<div><dt>${esc(t("m_" + k).startsWith("m_") ? k : t("m_" + k))}</dt><dd>${v}</dd></div>`).join("")}</dl>
        <div class="table-wrap tall"><table class="rtable"><thead><tr><th>${t("col_address")}</th><th>${t("col_mailing")}</th><th>${t("col_legal")}</th><th>${t("col_method")}</th></tr></thead><tbody>${d.geocoding_notes.map((g) => `<tr><td><a href="#/a/${g.id}">${esc(titleCase(g.street))}</a></td><td>${esc(g.postal_city)}</td><td>${esc(g.city || t("outside"))}</td><td class="s" title="${esc(g.note)}">${esc(t("m_" + g.method).startsWith("m_") ? g.method : t("m_" + g.method))}</td></tr>`).join("")}</tbody></table></div>`)}
      ${sec("a-docs", tf("a_docs", { n: d.documents.length }), `<div class="table-wrap tall"><table class="rtable"><thead><tr><th>${t("col_source")}</th><th>${t("jurisdiction")}</th><th>${t("col_type")}</th><th>${t("col_rules")}</th><th><span class="sr">${t("col_text")}</span></th></tr></thead><tbody>
        ${d.documents.map((x) => `<tr><td><a href="${esc(x.url)}" target="_blank" rel="noopener" title="${esc(x.url)}">${esc(shortUrl(x.url))}</a><div class="s"><span class="mono">${esc(x.doc_id)}</span> · ${esc(tf("retrieved", { d: x.retrieved_at ? fmtDate(x.retrieved_at) : "–" }))} · sha256 ${esc((x.sha256 || "").slice(0, 12))}</div></td><td class="nw">${esc(x.jurisdictions)}</td><td class="s">${esc(x.source_type)}${x.capture !== "yes" ? ` · ${esc(x.capture)}` : ""}</td><td class="num">${x.rules_extracted || 0}</td><td>${x.text_available ? `<a href="#" data-doc="${esc(x.doc_id)}">${t("l_text")}</a>` : `<span class="s">${t("l_link")}</span>`}</td></tr>`).join("")}
        </tbody></table></div>`)}
      ${sec("a-log", `${t("a_log")} · ${d.audit_total}`, `<div class="filters"><input type="search" id="lq" placeholder="${t("q_filter")}" aria-label="${t("q_filter")}"></div><p class="count-note" id="lc"></p><div class="log" id="log"></div>`)}
    </div></section></details>`;
  await swap(html, () => {
    // the Ask audit log (features/ask, web/ask.py): linked only when the server has it, so the link never dead-ends
    if (window.CEAsk?.audit) $("#rev-ask").hidden = false; // set by features/ask.js once the audit log ships (no probing)
    $("#sq").addEventListener("input", (e) => {
      const q = e.target.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
      $$(".sr-row", main).forEach((r) => { r.hidden = !q.every((w) => r.dataset.q.includes(w)); });
      $$("[data-sub]", main).forEach((g) => { g.hidden = !$$(".sr-row", g).some((r) => !r.hidden); });
      $$("[data-group]", main).forEach((g) => { g.hidden = !$$("[data-sub]", g).some((r) => !r.hidden); if (q.length) g.open = !g.hidden; });
      $("#sq-none").hidden = $$(".sr-row", main).some((r) => !r.hidden);
    });
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
  if (lang === "es" && !Object.keys(ES).length) ES = await api("/api/i18n/es").catch(() => ({})); // retry after a failed fetch (#132)
  const [view, arg] = location.hash.replace(/^#\/?/, "").split("/");
  const name = view === "a" || view === "check" || view === "compare" ? "lookup" : view || "lookup"; // #138
  syncHeader(name);
  closeModal(); closeCmdk();
  const titles = { changes: "t_changes", rules: "t_rules", audit: "t_audit" };
  document.title = titles[view] ? `${t(titles[view])} · Clause & Effect` : `Clause & Effect · ${t("tagline_short")}`;
  const y = scrollY;
  const back = !soft && history.state?.ce ? history.state.ce : null; // returning to an entry we left (Back): restore it (#63)
  if (!soft && view !== "a") delete main.dataset.addr;
  main.dataset.view = view || "home";
  document.documentElement.classList.toggle("is-home", !view);
  try {
    if (ROUTES.has(view)) await ROUTES.get(view)(main, arg ? decodeURIComponent(arg) : undefined);
    else if (view === "a" && arg) await viewAddress(arg.toUpperCase());
    else if (view === "changes") await viewChanges();
    else if (view === "rules") await viewRules(arg ? decodeURIComponent(arg) : "");
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
  headArt();
  // the docked "Ask anything" bar (features/ask.js) on home, and on address pages where there is room for it
  // On phones the home hero already has a search box: the bar docks once the hero has scrolled away.
  if (view !== "ask" && window.CEAsk) {
    const phone = innerWidth <= 640, hero = $(".big-search", main);
    if (!view && !phone && hero && "IntersectionObserver" in window) {
      window.CEAsk.unmountDock();
      const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) window.CEAsk.unmountDock(); else window.CEAsk.mountDock(); });
      io.observe(hero); cleanup.push(() => io.disconnect());
    } else if (!phone && (!view || view === "a")) window.CEAsk.mountDock();
    else window.CEAsk.unmountDock();
  }
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

const CE_render = (el, v, opts) => { PV = !!opts.place; try { el.innerHTML = answersHTML({ ...normalizeLookup(v), ...opts }); } finally { PV = false; } };
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
    const item = { result: e.result, headline: e.headline, explanation: e.explanation, explanation_en: e.explanation_en, conflict_flag: !!e.conflict_flag, missing_fact: e.missing_fact, superseded_by: e.superseded_by, overrides_here: e.overrides_here, rule };
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
  renderAnswers(container, lookupResult, { ask = false, heading = "" } = {}) {
    const el = typeof container === "string" ? $(container) : container;
    el.innerHTML = answersHTML({ ...normalizeLookup(lookupResult), ask, heading });
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
