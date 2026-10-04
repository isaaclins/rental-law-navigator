// Check a rent increase (#40). Self-contained feature module on window.CE (web/DESIGN.md).
// Route #/check/<addressId> (a known address) or #/check (any address, resolved live). The user enters the current
// and new rent, the notice and effective dates, optionally deposit, application fee and a notice to end the
// tenancy; POST /api/check returns one deterministic verdict per item with the deciding rule, its verbatim quote and
// source. Entry point: a "Check a rent increase" link in the address page's rent / deposit / fee topic slots.
// Not legal advice. Nothing is stored on the server.

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const CE = window.CE;
const lang = () => CE.lang();
// the letter to the landlord (#122) loads alongside, without delaying this route's registration
let LM = null;
const LMP = import("./letter.js").then((m) => (LM = m)).catch(() => null);
import("./backnav.js").catch(() => null); // back pills go to the page the reader came from (all views)
let SAY = null; // Listen to the verdict (features/say.js, the device voice)
const SAYP = import("./say.js").then((m) => (SAY = m)).catch(() => null);

// ------------------------------------------------------------------ i18n --
const EN = {
  title: "Check a rent increase", entry: "Check a rent increase", entry_dep: "Check a deposit", entry_fee: "Check an application fee",
  any_sub: "Any address in California, New Jersey or Massachusetts.",
  address: "Address", address_ph: "Street, city, state",
  cur: "Current rent", new: "New rent", new_ph: "$2,300, +300 or 5%", notice: "Date on the notice", eff: "New rent starts", optional: "optional", pick_date: "Pick a date", dates_hint: "Add both dates to check the notice period too.",
  more: "Deposit, fees and ending the tenancy", deposit: "Deposit asked", fee: "Application fee",
  term: "Notice to end the tenancy", term_none: "None", term_reason: "Yes, with a reason", term_no_reason: "Yes, no reason given",
  moved_in: "Moved in", cpi: "Local CPI change", cpi_hint: "%, if you know it", building: "Building",
  year_built: "Year built", units: "Units", owner_occupied: "Owner lives there", yes: "Yes", no: "No", unsure: "Not sure",
  go: "Check", checking: "Checking…", locating: "Finding the address…",
  it_rent: "Rent increase", it_notice: "Notice", it_deposit: "Deposit", it_fee: "Application fee", it_termination: "Ending the tenancy",
  b_ok: "Allowed", b_over: "Over the limit", b_short: "Too short", b_enough: "Enough notice", b_unknown: "Can't tell", b_none: "No cap",
  b_notallowed: "Not allowed", b_noreason: "No reason needed",
  l_within: "Up to {max} ({pct}%)", l_noinc: "No increase", l_over: "{amt} too high: {an} {inc}% increase, the cap is {pct}%",
  l_over_max: "{amt} too high, even at the highest cap ({pct}%)", l_need: "We need {f}", l_need_figure: "Our sources don't have the allowed % for {d} yet",
  l_no_cap: "No rent cap covers this building", l_state_bar: "No limit here. They can raise it any amount.",
  l_short: "Needs {n} days, got {d}", l_enough: "{n} days needed, {d} given",
  l_dep_within: "Up to {max}", l_dep_over: "{amt} too high", l_dep_none: "No deposit cap in our sources",
  l_fee_within: "Up to {max}", l_fee_over: "{amt} too high", l_fee_not_listed: "Landlords may not charge it here", l_fee_none: "No fee cap in our sources",
  l_reason_required: "A listed reason is required", l_reason_check: "We need to check the reason against the list",
  l_not_yet: "Protection starts {d}", l_no_rule: "None of the rules here requires a reason",
  f_cpi: "the local CPI change", f_year_built: "the year the building was built", f_units: "the number of units",
  f_owner_occupied: "whether the owner lives in the building", f_certificate_of_occupancy_date: "the certificate-of-occupancy date",
  f_rate_figure: "the allowed increase for {d}", f_notice_date: "the date the notice was given", f_effective_date: "the date the increase takes effect",
  f_notice_rule: "the notice period for rent increases in {s}", f_notice_rule_10: "the notice period for increases of 10% or more",
  f_landlord_small: "the landlord type", f_fee_figure: "the {y} fee cap", f_rent: "the monthly rent", f_moved_in: "your move-in date",
  f_reason_on_list: "the reason, checked against the list", f_current_rent: "the current rent", f_new_rent: "the new rent", f_other: "a fact not in public data",
  x_period: "The cap is {pct}% for increases taking effect {a} to {b}: at most {max} on {cur}.",
  x_formula: "The cap is {base}% plus the local CPI change, at most {hi}%. With a CPI change of {cpi}% that is {pct}%: at most {max}.",
  x_formula_share: "The cap is {share}% of the local CPI change, at most {hi}%. With a CPI change of {cpi}% that is {pct}%: at most {max}.",
  l_cpi_ok: "Allowed: {inc}% is within the {base}% base of the cap", x_cpi_ok: "The cap is {base}% plus the local CPI change, at most {hi}%. An increase of {inc}% stays within it unless local prices fell by more than {fall}% over the year.",
  x_need_cpi: "This increase is {inc}%. It is within the cap only if the local CPI change is at least {t}%. The CPI figure is not in our sources.",
  x_over_max: "This increase is {inc}%. Whatever the CPI, the cap never exceeds {hi}% ({max}).",
  x_need_figure: "The rule sets a new percentage each period. Ask your landlord which one they used, and compare it with the published figure (source below).",
  x_need_fact: "Whether a cap applies depends on {f}.",
  x_notice: "The notice came {d} days before the increase. The earliest date for this increase is {e}.",
  x_notice_rule_10: "Our sources state the notice period only for increases under 10%. This one is {inc}%.",
  x_notice_rule: "Our sources do not state a notice period for rent increases in {s}.",
  x_dep: "The limit is {m} months' rent: {max} on {rent}.", x_dep1: "The limit is one month's rent: {max}.",
  x_dep_landlord: "One month's rent ({max}) is always allowed. Up to {alt} only for a small landlord: a natural person with no more than two rental properties and four units, and not from a service member.",
  x_dep_nosmall: "This building has {n} units, so the 2-month small-landlord exception can't apply. The cap is one month's rent ({max}).",
  x_dep_nosmall_min: "This building has {n} or more units, so the 2-month small-landlord exception can't apply. The cap is one month's rent ({max}).",
  x_fee: "The cap is {max} per applicant.", x_fee_not_listed: "At the start of a tenancy a landlord may ask only for first and last month's rent, a deposit and the cost of a lock.",
  x_fee_figure: "The cap changes with CPI every year. Our sources have no figure for {y}.",
  x_reason_required: "A landlord here may end the tenancy only for a reason this law lists, stated in the notice.",
  x_reason_check: "A landlord here may end the tenancy only for a reason this law lists. Compare the reason with the source.",
  x_moved_in: "Protection starts after {n} {u} in the home.", x_not_yet: "Protection starts after {n} {u} in the home, on {d}.",
  months: "months", days: "days",
  not_covered: "Does not cover this building", retrieved: "Retrieved {d}", read_full: "Read the full text", add: "Add",
  as_of: "As of {d}, the date the increase takes effect.", as_of_plain: "As of {d}.",
  assume: "Assumes no other increase in the past 12 months.",
  nla: "Not legal advice.", nla_body: "Read the cited source. A local rent board or tenant organization can help.",
  state_only: "Only state law was checked here: local rules for this address are not in our sources.",
  e_rent: "Enter the current and the new rent.", e_dates: "The increase cannot take effect before the notice.", e_err: "Something went wrong. Try again.", e_invalid: "Check the amounts: enter rents and fees as positive numbers.",
  e_nomatch: "We could not find this address. Add the city and state.", e_out: "This address is outside California, New Jersey and Massachusetts.",
  f_addr: "Pick an address from the list, or type the street, city and state.", f_num: "Enter a number, like 2,000.", f_pos: "Enter a rent above $0.", f_big: "{v} looks too high for a monthly rent. Check the amount.", f_big_amt: "{v} looks too high. Check the amount.", f_nonneg: "Enter an amount of $0 or more.", f_from: "From “My rent now”. Type to replace it.", f_new: "Enter the new rent, +300 or a percent like 4%.", ta_any: "Use this address", ta_ours: "Addresses", ta_examples: "Examples", ta_none: "No sample address matches", ta_none_s: "Type the street with its number, then the city.",
  e_busy: "Too many checks. Wait a minute.", results: "Result", results_more: "The law behind it", echo_new: "New rent: {v}", add_dates: "Add the dates to check the notice too.",
  h_over: "too high", h_within: "Within the limit", h_rent_k: "Your rent increase", h_dep_k: "Deposit", h_fee_k: "Application fee",
  h_max: "Highest allowed: {max}", h_cap: "{pct}% cap", h_new: "New rent {v}", h_asked: "Asked {v}", h_room: "{v} below the limit",
  get_1: "The answer in dollars: within the limit, or how much too high", get_2: "The law that decides it, word for word, with its source", get_3: "A letter to your landlord when it is too high", try_it: "Try it: $2,000 to $2,100", try_any: "Try it with 3515 Fillmore St, San Francisco", empty_t: "Your answer appears here", empty_p: "Enter the current and the new rent. The answer names the law that decides it, with its exact words.",
};
const ES = {
  title: "Revisar un aumento de renta", entry: "Revisar un aumento de renta", entry_dep: "Revisar un depósito", entry_fee: "Revisar una cuota de solicitud",
  any_sub: "Cualquier dirección en California, Nueva Jersey o Massachusetts.",
  address: "Dirección", address_ph: "Calle, ciudad, estado",
  cur: "Renta actual", new: "Renta nueva", new_ph: "$2,300, +300 o 5%", notice: "Fecha del aviso", eff: "La nueva renta empieza", optional: "opcional", pick_date: "Elegir fecha", dates_hint: "Agregue ambas fechas para revisar también el plazo de aviso.",
  more: "Depósito, cuotas y fin del contrato", deposit: "Depósito pedido", fee: "Cuota de solicitud",
  term: "Aviso de fin del contrato", term_none: "Ninguno", term_reason: "Sí, con un motivo", term_no_reason: "Sí, sin motivo",
  moved_in: "Fecha de mudanza", cpi: "Cambio del IPC local", cpi_hint: "%, si lo sabe", building: "Edificio",
  year_built: "Año de construcción", units: "Unidades", owner_occupied: "El dueño vive allí", yes: "Sí", no: "No", unsure: "No sé",
  go: "Revisar", checking: "Revisando…", locating: "Buscando la dirección…",
  it_rent: "Aumento de renta", it_notice: "Aviso", it_deposit: "Depósito", it_fee: "Cuota de solicitud", it_termination: "Fin del contrato",
  b_ok: "Permitido", b_over: "Sobre el límite", b_short: "Muy corto", b_enough: "Aviso suficiente", b_unknown: "No se puede saber", b_none: "Sin límite",
  b_notallowed: "No permitido", b_noreason: "No requiere motivo",
  l_within: "Hasta {max} ({pct}%)", l_noinc: "Sin aumento", l_over: "{amt} de más: un aumento del {inc}%, el límite es {pct}%",
  l_over_max: "{amt} de más, incluso con el límite más alto ({pct}%)", l_need: "Necesitamos {f}", l_need_figure: "Nuestras fuentes aún no tienen el % permitido para el {d}",
  l_no_cap: "Ningún límite de renta cubre este edificio", l_state_bar: "Aquí no hay límite. Pueden subirla cualquier monto.",
  l_short: "Requiere {n} días, recibió {d}", l_enough: "Se requieren {n} días, recibió {d}",
  l_dep_within: "Hasta {max}", l_dep_over: "{amt} de más", l_dep_none: "Sin límite de depósito en nuestras fuentes",
  l_fee_within: "Hasta {max}", l_fee_over: "{amt} de más", l_fee_not_listed: "Aquí el arrendador no puede cobrarla", l_fee_none: "Sin límite de cuota en nuestras fuentes",
  l_reason_required: "Se requiere un motivo de la lista", l_reason_check: "Hay que comparar el motivo con la lista",
  l_not_yet: "La protección empieza el {d}", l_no_rule: "Ninguna norma aquí exige un motivo",
  f_cpi: "el cambio del IPC local", f_year_built: "el año de construcción del edificio", f_units: "el número de unidades",
  f_owner_occupied: "si el dueño vive en el edificio", f_certificate_of_occupancy_date: "la fecha del certificado de ocupación",
  f_rate_figure: "el aumento permitido para el {d}", f_notice_date: "la fecha del aviso", f_effective_date: "la fecha en que entra en vigor el aumento",
  f_notice_rule: "el plazo de aviso para aumentos en {s}", f_notice_rule_10: "el plazo de aviso para aumentos del 10% o más",
  f_landlord_small: "el tipo de arrendador", f_fee_figure: "el límite de cuota de {y}", f_rent: "la renta mensual", f_moved_in: "su fecha de mudanza",
  f_reason_on_list: "comparar el motivo con la lista", f_current_rent: "la renta actual", f_new_rent: "la renta nueva", f_other: "un dato que no está en los datos públicos",
  x_period: "El límite es {pct}% para aumentos que entran en vigor del {a} al {b}: como máximo {max} sobre {cur}.",
  x_formula: "El límite es {base}% más el cambio del IPC local, como máximo {hi}%. Con un cambio del IPC de {cpi}% son {pct}%: como máximo {max}.",
  x_formula_share: "El límite es el {share}% del cambio del IPC local, como máximo {hi}%. Con un cambio del IPC de {cpi}% son {pct}%: como máximo {max}.",
  l_cpi_ok: "Permitido: {inc}% está dentro de la base de {base}% del límite", x_cpi_ok: "El límite es {base}% más el cambio del IPC local, como máximo {hi}%. Un aumento de {inc}% queda dentro, salvo que los precios locales hayan bajado más de {fall}% en el año.",
  x_need_cpi: "Este aumento es de {inc}%. Está dentro del límite solo si el cambio del IPC local es de al menos {t}%. Esa cifra del IPC no está en nuestras fuentes.",
  x_over_max: "Este aumento es de {inc}%. Sea cual sea el IPC, el límite nunca supera {hi}% ({max}).",
  x_need_figure: "La norma fija un porcentaje nuevo cada periodo. Pregunte a su arrendador cuál usó y compárelo con la cifra publicada (fuente abajo).",
  x_need_fact: "Si se aplica un límite depende de {f}.",
  x_notice: "El aviso llegó {d} días antes del aumento. La fecha más temprana para este aumento es el {e}.",
  x_notice_rule_10: "Nuestras fuentes indican el plazo de aviso solo para aumentos de menos del 10%. Este es de {inc}%.",
  x_notice_rule: "Nuestras fuentes no indican un plazo de aviso para aumentos de renta en {s}.",
  x_dep: "El límite es {m} meses de renta: {max} sobre {rent}.", x_dep1: "El límite es un mes de renta: {max}.",
  x_dep_landlord: "Un mes de renta ({max}) siempre está permitido. Hasta {alt} solo para un pequeño arrendador: una persona física con no más de dos propiedades en alquiler y cuatro unidades, y no a un militar en servicio.",
  x_dep_nosmall: "Este edificio tiene {n} unidades, así que la excepción de 2 meses para dueños pequeños no aplica. El tope es un mes de renta ({max}).",
  x_dep_nosmall_min: "Este edificio tiene {n} unidades o más, así que la excepción de 2 meses para dueños pequeños no aplica. El tope es un mes de renta ({max}).",
  x_fee: "El límite es {max} por solicitante.", x_fee_not_listed: "Al inicio del contrato el arrendador solo puede pedir el primer y último mes de renta, un depósito y el costo de una cerradura.",
  x_fee_figure: "El límite cambia cada año con el IPC. Nuestras fuentes no tienen la cifra para {y}.",
  x_reason_required: "Aquí el arrendador solo puede terminar el contrato por un motivo que esta ley enumera, indicado en el aviso.",
  x_reason_check: "Aquí el arrendador solo puede terminar el contrato por un motivo que esta ley enumera. Compare el motivo con la fuente.",
  x_moved_in: "La protección empieza tras {n} {u} en la vivienda.", x_not_yet: "La protección empieza tras {n} {u} en la vivienda, el {d}.",
  months: "meses", days: "días",
  not_covered: "No cubre este edificio", retrieved: "Consultado el {d}", read_full: "Leer el texto completo", add: "Agregar",
  as_of: "Al {d}, la fecha en que entra en vigor el aumento.", as_of_plain: "Al {d}.",
  assume: "Supone que no hubo otro aumento en los últimos 12 meses.",
  nla: "No es asesoría legal.", nla_body: "Lea la fuente citada. Una junta de rentas local o una organización de inquilinos puede ayudar.",
  state_only: "Aquí solo se revisó la ley estatal: las normas locales de esta dirección no están en nuestras fuentes.",
  e_rent: "Indique la renta actual y la nueva.", e_dates: "El aumento no puede entrar en vigor antes del aviso.", e_err: "Algo salió mal. Inténtelo de nuevo.", e_invalid: "Revise los montos: indique rentas y cargos como números positivos.",
  e_nomatch: "No encontramos esta dirección. Agregue la ciudad y el estado.", e_out: "Esta dirección está fuera de California, Nueva Jersey y Massachusetts.",
  f_addr: "Elija una dirección de la lista, o escriba calle, ciudad y estado.", f_num: "Escriba un número, como 2,000.", f_pos: "Escriba una renta mayor que $0.", f_big: "{v} parece demasiado alto para una renta mensual. Revise el monto.", f_big_amt: "{v} parece demasiado alto. Revise el monto.", f_nonneg: "Escriba un monto de $0 o más.", f_from: "De “Mi renta actual”. Escriba para reemplazarlo.", f_new: "Escriba la nueva renta, +300 o un porcentaje como 4%.", ta_any: "Usar esta dirección", ta_ours: "Direcciones", ta_examples: "Ejemplos", ta_none: "Ninguna dirección de ejemplo coincide", ta_none_s: "Escriba la calle con su número y luego la ciudad.",
  e_busy: "Demasiadas consultas. Espere un minuto.", results: "Resultado", results_more: "La ley detrás", echo_new: "Nueva renta: {v}", add_dates: "Agregue las fechas para revisar también el aviso.",
  h_over: "de más", h_within: "Dentro del límite", h_rent_k: "Su aumento de renta", h_dep_k: "Depósito", h_fee_k: "Cargo de solicitud",
  h_max: "Máximo permitido: {max}", h_cap: "límite del {pct}%", h_new: "Nueva renta {v}", h_asked: "Se pide {v}", h_room: "{v} por debajo del límite",
  get_1: "La respuesta en dólares: dentro del límite, o cuánto de más", get_2: "La ley que lo decide, palabra por palabra, con su fuente", get_3: "Una carta a su arrendador cuando es demasiado", try_it: "Pruébelo: de $2,000 a $2,100", try_any: "Pruébelo con 3515 Fillmore St, San Francisco", empty_t: "Aquí aparecerá su respuesta", empty_p: "Ingrese la renta actual y la nueva. La respuesta nombra la ley que lo decide, con sus palabras exactas.",
};
const STATES = { CA: ["California", "California"], NJ: ["New Jersey", "Nueva Jersey"], MA: ["Massachusetts", "Massachusetts"] };
const t = (k, o = {}) => Object.entries(o).reduce((s, [a, b]) => s.replaceAll("{" + a + "}", b), (lang() === "es" && ES[k]) || EN[k] || k);
const svg = (p) => `<svg class="ico" viewBox="0 0 24 24" aria-hidden="true">${p}</svg>`;
const I = { chev: svg('<path d="m9 6 6 6-6 6"/>'), back: svg('<path d="m15 6-6 6 6 6"/>'), ext: svg('<path d="M14 5h5v5M19 5l-8 8M18 14v4a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h4"/>') };

const loc = () => (lang() === "es" ? "es-US" : "en-US");
const money = (n) => new Intl.NumberFormat(loc(), { style: "currency", currency: "USD", minimumFractionDigits: n % 1 ? 2 : 0, maximumFractionDigits: 2 }).format(n);
const pct = (n) => new Intl.NumberFormat(loc(), { maximumFractionDigits: 2 }).format(n);
const day = (d) => (d ? CE.fmtDate(d) : "");
const host = (u) => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return ""; } };
const stateName = (s) => (STATES[s] ? STATES[s][lang() === "es" ? 1 : 0] : s);
const norm = (x) => String(x || "").toLowerCase();
// display only: title case and the usual suffixes spelled the way people write them ("663 Massachusetts Ave")
const SUFFIX = { av: "Ave", "ave.": "Ave", avenue: "Ave", bl: "Blvd", blv: "Blvd", "st.": "St", "pl.": "Pl", wy: "Way" };
const streetName = (s) => String(s || "").toLowerCase().replace(/\b\w/g, (m) => m.toUpperCase()).replace(/(\s)(\S+)$/, (m, sp, w) => sp + (SUFFIX[w.toLowerCase()] || w)).replace(/(\d)(St|Nd|Rd|Th)\b/g, (m, d, x) => d + x.toLowerCase());
// a few sample addresses for an empty field: one per covered city, CA, MA and NJ
function examples(all) {
  const yr = (a) => parseInt(a.year_built || "0", 10);
  const pick = (f) => all.find(f);
  return [pick((a) => a.city === "Los Angeles" && yr(a) && yr(a) < 1978) || pick((a) => a.city === "Los Angeles"),
    pick((a) => a.city === "San Francisco" && yr(a) && yr(a) < 1979) || pick((a) => a.city === "San Francisco"),
    pick((a) => a.postal_city === "Dorchester") || pick((a) => a.state === "MA"),
    pick((a) => a.city === "Hoboken") || pick((a) => a.state === "NJ"),
    pick((a) => a.city === "San Diego")].filter(Boolean);
}
const num = (s) => { const v = parseFloat(String(s || "").replace(/[$,\s]/g, "")); return Number.isFinite(v) ? v : null; };

// ------------------------------------------------------------------ state --
// One check per address is kept in memory, so language changes re-render without losing the inputs.
let S = { key: null, values: {}, place: null, result: null, addr: null };

function factLabel(need) {
  if (!need) return "";
  if (need.key === "other") return lang() === "en" && need.label ? need.label.replace(/\.$/, "").replace(/^Depends on:?\s*/i, "") : t("f_other");
  if (need.key === "rate_figure") return t("f_rate_figure", { d: day(need.date) });
  if (need.key === "notice_rule") return t("f_notice_rule", { s: stateName(need.state) });
  if (need.key === "fee_figure") return t("f_fee_figure", { y: need.year });
  return t("f_" + need.key);
}
// fields that settle a missing fact, by need key
const FIELD = { cpi: "cpi", year_built: "year_built", units: "units", owner_occupied: "owner_occupied", notice_date: "notice_date",
  effective_date: "effective_date", moved_in: "moved_in", current_rent: "current_rent", new_rent: "new" };

// ------------------------------------------------------------------ verdict text --
function verdictText(v) {
  const x = v.values || {};
  const need = factLabel(v.need);
  const out = { badge: t("b_" + (v.kind === "none" ? "none" : v.kind === "short" ? "short" : v.kind)), line: "", body: "", status: v.kind };
  if (v.kind === "unknown") out.line = t("l_need", { f: need });
  if (v.id === "rent") {
    if (v.code === "no_increase") out.line = t("l_noinc");
    else if (v.code === "within" || v.code === "over") {
      out.line = v.code === "within" ? t("l_within", { max: money(x.max_rent), pct: pct(x.cap_pct) }) : t("l_over", { amt: money(x.over_amount), an: /^(8|11|18)/.test(pct(x.increase_pct)) && !/^1[0-9]{2}/.test(pct(x.increase_pct)) ? "an" : "a", inc: pct(x.increase_pct), pct: pct(x.cap_pct) });
      const c = v.cap || {};
      out.body = c.basis === "period" ? t("x_period", { pct: pct(x.cap_pct), a: day(c.start), b: day(c.end), max: money(x.max_rent), cur: money(x.current_rent) })
        : c.share === 1 ? t("x_formula", { base: pct(c.base), hi: pct(c.max), cpi: pct(c.cpi), pct: pct(x.cap_pct), max: money(x.max_rent) })
        : t("x_formula_share", { share: pct(c.share * 100), hi: pct(c.max), cpi: pct(c.cpi), pct: pct(x.cap_pct), max: money(x.max_rent) });
    } else if (v.code === "over_max") { out.line = t("l_over_max", { amt: money(x.over_amount), pct: pct(x.cap_max) }); out.body = t("x_over_max", { inc: pct(x.increase_pct), hi: pct(x.cap_max), max: money(x.max_rent) }); }
    else if (v.code === "need_cpi" && x.cpi_needed <= 0 && x.cpi_share === 1) { // within the fixed part of "5% + CPI": allowed unless prices fell (as Ask says)
      Object.assign(out, { status: "ok", badge: t("b_ok"), line: t("l_cpi_ok", { inc: pct(x.increase_pct), base: pct(x.cap_base) }),
        body: t("x_cpi_ok", { inc: pct(x.increase_pct), base: pct(x.cap_base), hi: pct(x.cap_max), fall: pct(-x.cpi_needed) }) });
    } else if (v.code === "need_cpi") out.body = t("x_need_cpi", { inc: pct(x.increase_pct), t: pct(x.cpi_needed) });
    else if (v.code === "need_figure") { out.line = t("l_need_figure", { d: day(v.need?.date) }); out.body = t("x_need_figure", { d: day(v.need?.date) }); }
    else if (v.code === "need_fact") out.body = t("x_need_fact", { f: need });
    else if (v.code === "no_cap") out.line = t("l_no_cap");
    else if (v.code === "state_bar") out.line = t("l_state_bar");
  } else if (v.id === "notice") {
    if (v.kind === "ok") { out.badge = t("b_enough"); out.line = t("l_enough", { n: x.days_needed, d: x.days_given }); }
    if (v.kind === "short") out.line = t("l_short", { n: x.days_needed, d: x.days_given });
    if (v.kind === "ok" || v.kind === "short") out.body = t("x_notice", { d: x.days_given, e: day(x.earliest) });
    if (v.need?.key === "notice_rule_10") out.body = t("x_notice_rule_10", { inc: pct(x.increase_pct) });
    if (v.need?.key === "notice_rule") out.body = t("x_notice_rule", { s: stateName(v.need.state) });
  } else if (v.id === "deposit") {
    if (v.code === "within") { out.line = t("l_dep_within", { max: money(x.max) }); out.body = x.months === 1 ? t("x_dep1", { max: money(x.max) }) : t("x_dep", { m: pct(x.months), max: money(x.max), rent: money(x.rent) }); }
    if (v.code === "over") { out.line = t("l_dep_over", { amt: money(x.over_amount) }); out.body = x.small_excluded ? t(x.units ? "x_dep_nosmall" : "x_dep_nosmall_min", { n: x.units || x.units_min, max: money(x.max) }) : x.alt_months ? t("x_dep_landlord", { max: money(x.max), alt: money(x.alt_max) }) : x.months === 1 ? t("x_dep1", { max: money(x.max) }) : t("x_dep", { m: pct(x.months), max: money(x.max), rent: money(x.rent) }); }
    if (v.code === "need_landlord") out.body = t("x_dep_landlord", { max: money(x.max), alt: money(x.alt_max) });
    if (v.code === "need_fact" && v.need?.key !== "rent") out.body = t("x_need_fact", { f: need });
    if (v.code === "no_cap") out.line = t("l_dep_none");
  } else if (v.id === "fee") {
    if (v.code === "within") { out.line = x.max != null ? t("l_fee_within", { max: money(x.max) }) : t("l_noinc"); out.body = x.max != null ? t("x_fee", { max: money(x.max) }) : ""; }
    if (v.code === "over") { out.line = t("l_fee_over", { amt: money(x.over_amount) }); out.body = t("x_fee", { max: money(x.max) }); }
    if (v.code === "not_listed") { out.badge = t("b_notallowed"); out.line = t("l_fee_not_listed"); out.body = t("x_fee_not_listed"); }
    if (v.code === "need_figure") out.body = t("x_fee_figure", { y: v.need.year });
    if (v.code === "need_fact") out.body = t("x_need_fact", { f: need });
    if (v.code === "no_cap") out.line = t("l_fee_none");
  } else if (v.id === "termination") {
    const u = x.unit === "day" ? t("days") : t("months");
    if (v.code === "reason_required") { out.badge = t("b_notallowed"); out.line = t("l_reason_required"); out.body = t("x_reason_required"); }
    if (v.code === "reason_check") { out.line = t("l_reason_check"); out.body = t("x_reason_check"); }
    if (v.code === "need_fact" && v.need?.key === "moved_in") out.body = t("x_moved_in", { n: x.min, u });
    else if (v.code === "need_fact") out.body = t("x_need_fact", { f: need });
    if (v.code === "not_yet_protected") { out.badge = t("b_noreason"); out.line = t("l_not_yet", { d: day(x.protected_from) }); out.body = t("x_not_yet", { n: x.min, u, d: day(x.protected_from) }); }
    if (v.code === "no_reason_rule") { out.badge = t("b_noreason"); out.line = t("l_no_rule"); }
  }
  if (v.kind === "over" && !["over", "over_max"].includes(v.code) && out.badge === t("b_over")) out.badge = t("b_notallowed");
  return out;
}

function sourceHtml(s) {
  return `<section class="rd-sec">
    ${s.title ? `<h5>${esc(s.title)}</h5>` : ""}
    ${s.requirement ? `<p>${esc(s.requirement)}</p>` : ""}
    ${s.quote ? `<blockquote class="quote">${esc(s.quote)}</blockquote>` : ""}
    <p class="rd-cite">${s.citation ? `<span>${esc(s.citation)}</span>` : ""}${s.url ? `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(host(s.url))}${I.ext}</a>` : ""}${s.doc ? `<a href="#" data-doc="${esc(s.doc)}" data-rule="${esc(s.id || "")}">${t("read_full")}</a>` : ""}</p>
    ${s.retrieved ? `<p class="rd-meta">${esc(t("retrieved", { d: day(String(s.retrieved).slice(0, 10)) }))}</p>` : ""}
  </section>`;
}

function verdictRow(v, hero) {
  const tx = verdictText(v);
  // the verdict already shown big above: its row names the law that decides it instead of repeating the number
  if (hero && v === hero.src) { const r = (v.rules || [])[0]; if (r?.citation || r?.title) tx.line = r.citation || r.title; }
  const field = v.kind === "unknown" && tx.status !== "ok" && FIELD[v.need?.key];
  const fix = field ? ` <button type="button" class="linkish" data-ck-fix="${field}">${t("add")}</button>` : "";
  const srcs = [...(v.rules || []), ...(v.findings || [])];
  const excl = (v.excluded || []).map((x) => `<li>${esc(x.title)}${lang() === "en" && x.reasons?.length ? `: ${esc(x.reasons.join("; "))}` : ""} <span class="muted">(${esc(x.citation || "")})</span></li>`).join("");
  return `<details class="topic ck-v" data-id="${esc(v.id)}">
    <summary>
      <span class="topic-main"><span class="topic-q">${t("it_" + v.id)}</span><span class="topic-a">${esc(tx.line)}</span></span>
      <span class="badge st-${esc(BADGE[tx.status])}">${esc(tx.badge)}</span>
      <span class="chev">${I.chev}</span>
    </summary>
    <div class="topic-body"><div class="rd">
      ${tx.body || fix ? `<p class="rd-plain">${esc(tx.body)}${fix}</p>` : ""}
      ${excl ? `<section class="rd-sec"><h5>${t("not_covered")}</h5><ul>${excl}</ul></section>` : ""}
      ${srcs.map(sourceHtml).join("")}
    </div></div>
  </details>`;
}

// The answer's moment: the deciding number, large, counted up once; a colour sweep and a sticker for the verdict.
function heroData(d) {
  const v = d.verdicts.find((x) => x.id === "rent" && ["within", "over", "over_max"].includes(x.code))
    || d.verdicts.find((x) => (x.id === "deposit" || x.id === "fee") && ["within", "over"].includes(x.code) && x.values?.max != null);
  if (!v) return null;
  const h = heroOf(v);
  if (h) h.src = v;
  return h;
}
function heroOf(v) {
  const x = v.values || {}, ok = v.code === "within";
  if (v.id === "rent") {
    const max = v.code === "over_max" ? x.max_rent : x.max_rent;
    return { ok, k: t("h_rent_k"), n: ok ? x.new_rent - x.current_rent : x.over_amount, plus: ok, from: 0, lo: x.current_rent, hi: max, v: x.new_rent,
      sub: [t("h_new", { v: money(x.new_rent) }), t("h_max", { max: money(max) })], note: ok ? t("h_room", { v: money(Math.max(0, max - x.new_rent)) }) : t("h_cap", { pct: pct(v.code === "over_max" ? x.cap_max : x.cap_pct) }), cap: money(max) };
  }
  const asked = v.id === "deposit" ? S.values.deposit : S.values.application_fee;
  return { ok, k: t(v.id === "deposit" ? "h_dep_k" : "h_fee_k"), n: ok ? num(asked) : x.over_amount, from: 0, lo: 0, hi: x.max, v: num(asked), sub: [t("h_asked", { v: money(num(asked) || 0) })], note: t("h_max", { max: money(x.max) }), cap: money(x.max) };
}
function heroHtml(h) {
  if (!h) return "";
  const top = (h.hi - h.lo) / 0.7 || 1; // one scale for every verdict: the limit always sits at 70 %
  const at = (val) => Math.max(0, Math.min(100, ((val - h.lo) / top) * 100));
  return `<div class="ck-hero ${h.ok ? "is-ok" : "is-over"}" role="status">
    <img class="ck-art" src="/static/img/${h.ok ? "shield-check" : "scales-balanced"}.webp" alt="" onerror="this.remove()">
    <p class="ck-k">${esc(h.k)}</p>
    <p class="ck-big"><span class="ck-n" data-to="${h.n}" data-from="${h.from}" data-plus="${h.plus ? 1 : ""}">${h.plus ? "+" : ""}${esc(money(h.n))}</span>${h.ok ? "" : ` <span class="ck-w">${esc(t("h_over"))}</span>`}</p>
    ${h.ok ? `<p class="ck-ok">${esc(t("h_within"))}</p>` : ""}
    <div class="ck-bar" aria-hidden="true"><i class="ck-fill" style="--w:${at(Math.min(h.v, h.hi))}%"></i>${h.ok ? "" : `<i class="ck-overf" style="--l:${at(h.hi)}%;--w:${at(h.v) - at(h.hi)}%"></i>`}<b class="ck-cap" style="--l:${at(h.hi)}%"><span>${esc(h.cap)}</span></b></div>
    <p class="ck-sub">${h.sub.map(esc).join('<span class="sep" aria-hidden="true">·</span>')}<span class="sep" aria-hidden="true">·</span>${esc(h.note)}</p>
    ${SAY ? SAY.sayButton(lang(), "linkish ck-say") : ""}
  </div>`;
}
function playHero(out) {
  const el = $(".ck-n", out);
  if (!el) return;
  const to = +el.dataset.to, from = +el.dataset.from;
  if (matchMedia("(prefers-reduced-motion: reduce)").matches || !(to > from)) return;
  const t0 = performance.now(), dur = 750;
  const step = (now) => {
    if (!el.isConnected) return;
    const p = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - p, 3);
    const pre = el.dataset.plus ? "+" : "";
    el.textContent = pre + money(Math.round(from + (to - from) * e));
    if (p < 1) requestAnimationFrame(step); else el.textContent = pre + money(to);
  };
  el.textContent = (el.dataset.plus ? "+" : "") + money(from);
  setTimeout(() => requestAnimationFrame(step), 180);
}
function resultHtml(d) {
  const rentChecked = d.verdicts.some((v) => v.id === "rent" && v.values?.new_rent);
  const anyIncrease = d.verdicts.some((v) => v.id === "rent" && v.values?.increase_pct > 0 && (v.kind === "ok" || v.kind === "over"));
  const notes = [S.values.effective_date ? t("as_of", { d: day(d.as_of) }) : t("as_of_plain", { d: day(d.as_of) })];
  if (rentChecked && anyIncrease) notes.push(t("assume"));
  const hero = heroData(d);
  if (hero) hero.v0 = d.verdicts.find((v) => v.id === "rent" && ["within", "over", "over_max"].includes(v.code)) || null;
  // no dates typed: the notice check is skipped quietly instead of an orange "Can't tell" row
  const noDates = !S.values.notice_date && !S.values.effective_date;
  const shown = d.verdicts.filter((v) => !(noDates && v.id === "notice" && v.kind === "unknown"));
  const letter = LM?.canWrite(d) ? LM.ctaHtml(S.addr ? `#/check/${S.addr}/letter` : "#/check/letter") : ""; // #122
  return `${heroHtml(hero)}${letter}<h2>${t(hero ? "results_more" : "results")}</h2>
    <div class="topics group">${shown.map((v) => verdictRow(v, hero)).join("")}</div>
    ${S.place && !S.place.jurisdiction ? `<p class="addr-meta">${t("state_only")}</p>` : ""}
    <p class="addr-meta">${notes.map(esc).join(" ")}</p>
    <p class="addr-meta"><strong>${t("nla")}</strong> ${t("nla_body")}</p>`;
}

// verdict kind -> shared status colour class (st-over is the one addition, in check.css)
const BADGE = { ok: "applies", over: "over", short: "over", unknown: "unknown", none: "exempt" };

// ------------------------------------------------------------------ form --
function row(name, label, input, extra = "") { return `<li><label class="ck-row" for="ck-${name}"><span class="ck-l">${label}</span>${input}</label>${extra}</li>`; }
const opt = (label) => `${esc(label)} <small class="ck-opt">${esc(t("optional"))}</small>`;
const inp = (name, attrs = "") => `<input id="ck-${name}" name="${name}" ${attrs} value="${esc(S.values[name] ?? "")}">`;
const money_in = (name, ph = "") => inp(name, `inputmode="decimal" autocomplete="off" placeholder="${esc(ph)}"`);
const date_in = (name) => inp(name, `type="date" min="1950-01-01" max="2035-12-31"`) + `<span class="ck-dph" aria-hidden="true">${esc(t("pick_date"))}</span>`; // phones show an empty date field blank
function select(name, opts) {
  const cur = S.values[name] ?? opts[0][0];
  return `<select id="ck-${name}" name="${name}">${opts.map(([v, l]) => `<option value="${v}"${String(cur) === v ? " selected" : ""}>${esc(l)}</option>`).join("")}</select>`;
}

function formHtml(any, needBuilding) {
  const b = needBuilding ? `
      ${row("year_built", t("year_built"), inp("year_built", `inputmode="numeric" autocomplete="off" maxlength="4"`))}
      ${row("units", t("units"), inp("units", `inputmode="numeric" autocomplete="off"`))}
      ${any ? row("owner_occupied", t("owner_occupied"), select("owner_occupied", [["", t("unsure")], ["true", t("yes")], ["false", t("no")]])) : ""}` : "";
  const open = ["deposit", "application_fee", "moved_in", "cpi", "year_built", "units"].some((k) => S.values[k]) || (S.values.termination && S.values.termination !== "none");
  return `<form class="ck-form" novalidate autocomplete="off">
    <ul class="group ck-group">
      ${any ? row("address", t("address"), inp("address", `type="text" placeholder="${esc(t("address_ph"))}" autocomplete="street-address"`)) : ""}
      ${row("current_rent", t("cur"), money_in("current_rent", "$2,000"))}
      ${row("new", t("new"), money_in("new", t("new_ph")))}
      ${row("notice_date", opt(t("notice")), date_in("notice_date"))}
      ${row("effective_date", opt(t("eff")), date_in("effective_date"), `<p class="ck-hint">${esc(t("dates_hint"))}</p>`)}
    </ul>
    <details class="ck-more"${open ? " open" : ""}><summary>${t("more")}<span class="chev">${I.chev}</span></summary>
      <ul class="group ck-group">
        ${row("deposit", t("deposit"), money_in("deposit", "$"))}
        ${row("application_fee", t("fee"), money_in("application_fee", "$"))}
        ${row("termination", t("term"), select("termination", [["none", t("term_none")], ["reason", t("term_reason")], ["no_reason", t("term_no_reason")]]))}
        ${row("moved_in", t("moved_in"), date_in("moved_in"))}
        ${row("cpi", t("cpi"), inp("cpi", `inputmode="decimal" autocomplete="off" placeholder="${esc(t("cpi_hint"))}"`))}
        ${b}
      </ul>
    </details>
    <p class="ck-err" role="alert" hidden></p>
    <div class="ck-actions"><button class="btn primary" type="submit">${t("go")}</button></div>
  </form>`;
}

function readForm(form) {
  const v = {};
  for (const el of $$("input, select", form)) v[el.name] = el.value.trim();
  return v;
}

function payload(v) {
  const body = { lang: lang(), as_of: CE.asOf(), termination: v.termination || "none" };
  const cur = num(v.current_rent);
  if (cur) body.current_rent = cur;
  const nv = (window.CE_RENT?.parseNewRent || (() => null))(v.new, cur); // "+300" is an increase of $300, not a rent of $300
  if (nv?.increase_pct != null) body.increase_pct = nv.increase_pct;
  else if (nv?.new_rent) body.new_rent = nv.new_rent;
  for (const k of ["notice_date", "effective_date", "moved_in"]) if (v[k]) body[k] = v[k];
  for (const k of ["deposit", "application_fee"]) if (num(v[k]) != null && v[k] !== "") body[k] = num(v[k]);
  if (num(v.cpi) != null && v.cpi !== "") body.cpi = num(v.cpi);
  const facts = {};
  if (num(v.year_built)) facts.year_built = Math.round(num(v.year_built));
  if (num(v.units)) facts.units = Math.round(num(v.units));
  if (v.owner_occupied === "true" || v.owner_occupied === "false") facts.owner_occupied = v.owner_occupied === "true";
  if (Object.keys(facts).length) body.facts = facts;
  return body;
}

async function post(url, body) {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) { const e = new Error(typeof d.detail === "string" ? d.detail : ""); e.status = r.status; throw e; }
  return d;
}

async function resolvePlace(text) {
  const norm = (s) => String(s || "").toLowerCase().replace(/[^a-z0-9 ]/g, " ").replace(/\s+/g, " ").trim();
  const q = norm(text);
  const list = await CE.api("/api/addresses").catch(() => []);
  const hit = list.find((a) => q.startsWith(norm(a.street)) && (q.includes(norm(a.city || a.postal_city)) || q === norm(a.street)));
  if (hit) return { address_id: hit.id };
  const r = await post("/api/resolve", { address: text });
  if (!r.match) throw Object.assign(new Error(t("e_nomatch")), { user: true });
  if (!r.in_scope) throw Object.assign(new Error(t("e_out")), { user: true });
  return { place: { state: r.state, jurisdiction: r.jurisdiction } };
}

// the API's limits (web/app.py CheckReq): above them a field says the amount looks too high instead of a generic error
const RENT_MAX = 1000000;
// after a field error the message and the Check button both stay clear of the phone tab bar (scroll-margin in check.css)
function clearView(field, btn) {
  const li = field?.closest("li") || field;
  if (!li) return;
  btn?.scrollIntoView({ block: "end" });
  if (li.getBoundingClientRect().top < 0) li.scrollIntoView({ block: "start" }); // a tall form: the message wins
}
// a plain amount reads as money: 2000 -> $2,000 (+300 and 5% stay as typed); on leaving a field and on Check (Enter)
const MONEY = ["current_rent", "new", "deposit", "application_fee"];
function moneyField(el) {
  if (!MONEY.includes(el?.name)) return;
  const v = el.value.trim();
  if (/^\$?\s*[\d,]+(\.\d+)?$/.test(v) && num(v) > 0) el.value = money(num(v));
}
async function submit(main, any) {
  const form = $(".ck-form", main), err = $(".ck-err", main), out = $(".ck-result", main), btn = $("button[type=submit]", form);
  form.querySelectorAll("input").forEach(moneyField);
  const v = readForm(form);
  S.values = v;
  const show = (m) => { err.textContent = m; err.hidden = !m; if (m) { out.innerHTML = ""; S.result = null; } }; // an error never sits above an old result (#137)
  show("");
  // per-field checks, each message next to its field
  $$(".ck-ferr", form).forEach((x) => x.remove());
  const ferr = (name, msg) => { const el = $(`#ck-${name}`, form); el?.closest("li")?.insertAdjacentHTML("beforeend", `<p class="ck-ferr" role="alert">${esc(msg)}</p>`); el?.setAttribute("aria-invalid", "true"); return el; };
  $$("[aria-invalid]", form).forEach((x) => x.removeAttribute("aria-invalid"));
  const bad = [];
  const isNum = (x) => x === "" || x == null || /^\$?\s*[\d,]+(\.\d+)?$/.test(String(x).trim());
  if (any && (!v.address || v.address.trim().length < 5 || !/[a-z]{2,}/i.test(v.address))) bad.push(ferr("address", t("f_addr")));
  const neg = (x) => /^-?\s*\$?\s*-?\s*[\d,]+(\.\d+)?$/.test(String(x || "").trim()) && !(num(String(x).replace(/-/g, "")) > 0 && !/-/.test(x)); // 0, -5, $-5
  if (v.current_rent && neg(v.current_rent)) bad.push(ferr("current_rent", t("f_pos")));
  else if (!isNum(v.current_rent) || (v.current_rent && !(num(v.current_rent) > 0))) bad.push(ferr("current_rent", t("f_num")));
  else if (num(v.current_rent) > RENT_MAX) bad.push(ferr("current_rent", t("f_big", { v: money(num(v.current_rent)) })));
  const nr = v.new ? window.CE_RENT?.parseNewRent(v.new, num(v.current_rent)) : null;
  if (v.new && !nr) bad.push(ferr("new", t("f_new")));
  else if (nr?.new_rent > RENT_MAX && !bad.length) bad.push(ferr("new", t("f_big", { v: money(nr.new_rent) })));
  for (const k of ["deposit", "application_fee", "cpi", "year_built", "units"]) if (v[k] && !isNum(v[k].replace("%", ""))) bad.push(ferr(k, k !== "cpi" && /^\s*-/.test(v[k]) ? t("f_nonneg") : t("f_num")));
  for (const [k, hi] of [["deposit", RENT_MAX], ["application_fee", 100000]]) if (v[k] && isNum(v[k]) && num(v[k]) > hi) bad.push(ferr(k, t("f_big_amt", { v: money(num(v[k])) })));
  if (bad.length) { bad.forEach((el) => el?.closest("details")?.setAttribute("open", "")); bad[0]?.focus({ preventScroll: true }); clearView(bad[0], btn); return; }
  const body = payload(v);
  const anyItem = body.current_rent || body.new_rent || body.increase_pct != null || body.deposit != null || body.application_fee != null || body.termination !== "none";
  if (!anyItem || ((body.new_rent || body.increase_pct != null) && !body.current_rent)) { show(t("e_rent")); $("#ck-current_rent", form)?.focus(); return; }
  if (body.notice_date && body.effective_date && body.effective_date < body.notice_date) { show(t("e_dates")); return; }
  btn.disabled = true;
  try {
    if (any) {
      if (!v.address) { show(t("e_nomatch")); $("#ck-address", form)?.focus(); return; }
      if (!S.place || S.place.text !== v.address) { btn.textContent = t("locating"); S.place = { text: v.address, ...(await resolvePlace(v.address)) }; }
      if (S.place.address_id) { S.autorun = true; location.replace("#/check/" + S.place.address_id); return; } // the same step
      body.place = S.place.place;
    } else body.address_id = S.addr;
    btn.textContent = t("checking");
    S.body = body; // the letter (#122) is filled from this same check
    S.result = await post("/api/check", body);
    await Promise.all([LMP, SAYP]);
    out.innerHTML = resultHtml(S.result);
    out.classList.remove("ck-empty-on");
    playHero(out);
    if (matchMedia("(max-width: 640px)").matches) out.scrollIntoView({ block: "start", behavior: "smooth" });
  } catch (e) {
    show(e.user ? e.message : e.status === 429 ? t("e_busy") : e.status === 422 && /notice/.test(e.message) ? t("e_dates") : e.status === 422 || e.status === 400 ? t("e_invalid") : t("e_err"));
  } finally {
    btn.disabled = false; btn.textContent = t("go");
  }
}

// ------------------------------------------------------------------ view --
async function view(main, arg) {
  // #/check/<id>/letter or #/check/letter: the letter to the landlord from this check (#122, features/letter.js)
  const lm = location.hash.match(/^#\/check\/(?:([^/?#]+)\/)?letter\/?(?:\?.*)?$/i);
  if (lm) {
    const lid = lm[1] ? decodeURIComponent(lm[1]).toUpperCase() : null;
    if (!(await LMP)) { CE.navigate(lid ? `check/${lid}` : "check"); return; }
    return LM.letterView(main, { id: lid, S: S.key === (lid || "any") ? S : null, backHref: lid ? `#/check/${lid}` : "#/check" });
  }
  const id = arg ? String(arg).toUpperCase() : null;
  const key = id || "any";
  if (S.key !== key) S = { key, values: S.key === "any" && id ? S.values : {}, place: null, result: null, addr: id, autorun: S.key === "any" && id ? S.autorun : false };
  let head = `<h1>${t("title")}</h1><p>${esc(t("any_sub"))}</p>`;
  let needBuilding = !id;
  if (id) {
    let a;
    try { a = (await CE.api("/api/addresses")).find((x) => x.id === id); } catch { a = null; }
    if (!a) { CE.navigate("check"); return; }
    const street = streetName(a.street);
    head = `<a class="ck-back" href="#/a/${esc(id)}">${I.back}${esc(street)}</a><h1>${t("title")}</h1><p>${esc(street)}, ${esc(a.city || a.postal_city)}, ${esc(a.state)}</p>`;
    needBuilding = !a.year_built || !a.units;
  }
  document.title = `${t("title")} · Clause & Effect`;
  main.innerHTML = `<article class="ck"><header class="page-head ck-head">${head}</header>
    <div class="ck-grid"><div class="panel ck-main">${formHtml(!id, needBuilding)}</div>
      <aside class="ck-side"><section class="ck-result ck-empty-on" aria-live="polite"><div class="ck-empty"><img src="/static/img/magnifier-over-document.webp" alt="" onerror="this.remove()"><h2>${esc(t("empty_t"))}</h2><p>${esc(t("empty_p"))}</p><ul class="ck-get">${["get_1", "get_2", "get_3"].map((k) => `<li>${CE.icons.check || ""}<span>${esc(t(k))}</span></li>`).join("")}</ul><button type="button" class="linkish ck-try" data-ck-try>${esc(t(id ? "try_it" : "try_any"))}</button></div></section></aside></div></article>`;
  const form = $(".ck-form", main);
  form.addEventListener("submit", (e) => { e.preventDefault(); submit(main, !id); });
  // Listen reads the verdict card and the one sentence behind it
  const art = $(".ck", main);
  SAYP.then(() => SAY?.bindSay(art, () => {
    const hero = $(".ck-hero", art), d = S.result && heroData(S.result);
    if (!hero) return "";
    const said = [...hero.querySelectorAll(".ck-k, .ck-big, .ck-ok, .ck-sub")].map((e) => e.textContent.replace(/\s*·\s*/g, ". ").trim());
    if (d?.src) said.push(verdictText(d.src).body);
    return said.filter(Boolean).join(".\n").replace(/\.\./g, ".");
  }, lang));
  form.addEventListener("input", (e) => { if (e.target.name === "address") S.place = null; });
  form.addEventListener("input", (e) => { const li = e.target.closest("li"); li?.querySelector(".ck-ferr")?.remove(); e.target.removeAttribute("aria-invalid"); });
  // the address field is the same typeahead as the home search: on focus a few sample addresses (CA, NJ, MA), from the
  // first letter the matching ones, then "Use this address" for any other address; arrows, Enter and Esc work
  const ain = $("#ck-address", form);
  if (ain) {
    ain.setAttribute("role", "combobox"); ain.setAttribute("aria-autocomplete", "list"); ain.setAttribute("aria-controls", "ck-ta"); ain.setAttribute("aria-expanded", "false");
    ain.closest("li").insertAdjacentHTML("beforeend", `<ul class="suggest ck-ta" id="ck-ta" role="listbox" hidden></ul>`);
    const list = $("#ck-ta", form);
    let items = [], sel = -1;
    const close = () => { list.hidden = true; ain.setAttribute("aria-expanded", "false"); ain.removeAttribute("aria-activedescendant"); sel = -1; };
    const mark = () => {
      $$(".opt", list).forEach((li, i) => li.setAttribute("aria-selected", String(i === sel)));
      if (sel >= 0) { ain.setAttribute("aria-activedescendant", "ck-o-" + sel); $(`#ck-o-${sel}`, list)?.scrollIntoView({ block: "nearest" }); } else ain.removeAttribute("aria-activedescendant");
    };
    const opt = (i, a) => `<li class="opt" role="option" id="ck-o-${i}" aria-selected="false" data-id="${esc(a.id)}"><div><div class="addr">${esc(streetName(a.street))}</div><div class="sub">${esc(a.postal_city)}${a.city && a.city !== a.postal_city ? ` · ${esc(a.city)}` : ""}, ${esc(a.state)} ${esc(a.zip || "")}</div></div></li>`;
    const draw = async () => {
      const q = ain.value.trim();
      const all = await CE.api("/api/addresses").catch(() => []);
      if (document.activeElement !== ain) return;
      const terms = norm(q).split(/\s+/).filter(Boolean);
      const hits = q ? all.filter((a) => terms.every((w) => norm(`${a.street} ${a.postal_city} ${a.city} ${a.state} ${a.zip}`).includes(w))).slice(0, 5) : examples(all);
      const any = q.length >= 6 && /\d/.test(q) && /[a-z]{2,}/i.test(q);
      items = [...hits.map((a) => ({ id: a.id })), ...(any ? [{ any: true }] : [])];
      let html = hits.length ? `<li class="grp" role="presentation">${esc(t(q ? "ta_ours" : "ta_examples"))}</li>` + hits.map((a, i) => opt(i, a)).join("") : "";
      if (any) html += `<li class="opt aa-opt" role="option" id="ck-o-${hits.length}" aria-selected="false" data-any><div><div class="addr">${esc(t("ta_any"))}</div><div class="sub">“${esc(q)}”</div></div></li>`;
      if (!items.length) html = `<li class="opt empty" aria-disabled="true"><div><div class="addr">${esc(t("ta_none"))}</div><div class="sub">${esc(t("ta_none_s"))}</div></div></li>`;
      list.innerHTML = html;
      sel = -1; mark(); // nothing pre-selected: the first ArrowDown lands on the first row
      list.hidden = false; ain.setAttribute("aria-expanded", "true");
    };
    const pick = (i) => {
      const it = items[i]; if (!it) return;
      close();
      if (it.id) {
        S.autorun = !!S.values.current_rent || !!$("#ck-current_rent", form)?.value; S.values = { ...readForm(form) };
        if (!S.autorun) sessionStorage.setItem("ck.focus", "current_rent"); // the next field, not <main>
        location.replace("#/check/" + it.id); // the same step, not a new page
      }
      else form.requestSubmit();
    };
    ain.addEventListener("input", draw);
    ain.addEventListener("focus", draw);
    ain.addEventListener("blur", () => setTimeout(close, 150));
    ain.addEventListener("keydown", (e) => {
      if (e.key === "Escape") { if (!list.hidden) { e.preventDefault(); close(); } return; }
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        if (list.hidden) { draw(); return; }
        if (!items.length) return;
        sel = (sel + (e.key === "ArrowDown" ? 1 : -1) + items.length) % items.length; mark();
      } else if (e.key === "Enter" && !list.hidden && items.length) {
        // Enter picks the highlighted row; with none highlighted, the one sample address that matches the text
        const i = sel >= 0 ? sel : items.filter((x) => x.id).length === 1 ? 0 : -1;
        if (i >= 0 && items[i]) { e.preventDefault(); pick(i); }
      }
    });
    list.addEventListener("mousedown", (e) => {
      const li = e.target.closest(".opt:not(.empty)"); if (!li) return;
      e.preventDefault(); pick($$(".opt", list).indexOf(li));
    });
  }
  // "+300" echoes the rent it means
  const echo = () => {
    const el = $("#ck-new", form), cur = num($("#ck-current_rent", form)?.value), r = window.CE_RENT?.parseNewRent(el?.value, cur);
    let out = $(".ck-echo", form);
    const show = r?.delta != null && r.new_rent;
    if (!show) { out?.remove(); return; }
    if (!out) { el.closest("li").insertAdjacentHTML("beforeend", `<p class="ck-echo" aria-live="polite"></p>`); out = $(".ck-echo", form); }
    out.textContent = t("echo_new", { v: money(r.new_rent) });
  };
  form.addEventListener("input", (e) => { if (e.target.name === "new" || e.target.name === "current_rent") echo(); });
  // a plain amount reads as money once the field is left: 2000 -> $2,000 (+300 and 5% stay as typed)
  form.addEventListener("focusout", (e) => { moneyField(e.target); blurCheck(e.target); });
  // a wrong amount says so as soon as the field is left, not only on Check
  const blurCheck = (el) => {
    if (!["current_rent", "deposit", "application_fee", "new"].includes(el.name)) return;
    const v = el.value.trim(), li = el.closest("li");
    li?.querySelector(".ck-ferr")?.remove(); el.removeAttribute("aria-invalid");
    if (!v) return;
    const plainNum = /^\$?\s*[\d,]+(\.\d+)?$/.test(v), neg = /^\s*-/.test(v) || (plainNum && !(num(v) > 0) && el.name !== "deposit" && el.name !== "application_fee");
    let msg = "";
    if (el.name === "new") { const cur = num($("#ck-current_rent", form)?.value); msg = !(cur > 0) || window.CE_RENT?.parseNewRent(v, cur) ? "" : t("f_new"); }
    else if (el.name === "current_rent") msg = neg ? t("f_pos") : plainNum ? (num(v) > RENT_MAX ? t("f_big", { v: money(num(v)) }) : "") : t("f_num");
    else msg = neg ? t("f_nonneg") : plainNum ? "" : t("f_num");
    if (msg) { li?.insertAdjacentHTML("beforeend", `<p class="ck-ferr" role="alert">${esc(msg)}</p>`); el.setAttribute("aria-invalid", "true"); }
  };
  // a prefilled amount (the rent given on the address page) is selected on focus, so typing replaces it instead of
  // appending ($2,000 + "2000" = $20,002,000); iOS needs the range set after its own tap handling
  form.addEventListener("focusin", (e) => {
    const el = e.target;
    if (!el.dataset?.prefill || !el.value) return;
    const all = () => { try { el.setSelectionRange(0, el.value.length); } catch { el.select(); } };
    const v0 = el.value; el.select(); all(); setTimeout(() => el.value === v0 && all(), 0); el.addEventListener("mouseup", (m) => m.preventDefault(), { once: true }); // only if nothing was typed yet
  });
  form.addEventListener("input", (e) => {
    const el = e.target;
    if (!el.dataset?.prefill || !e.isTrusted) return;
    delete el.dataset.prefill; el.closest("li")?.querySelector(".ck-from")?.remove();
  });
  const markPrefill = (el) => {
    if (!el || !el.value || el.dataset.prefill) return;
    el.dataset.prefill = "1";
    el.closest("li")?.insertAdjacentHTML("beforeend", `<p class="ck-from">${esc(t("f_from"))}</p>`);
  };
  form.addEventListener("ce:prefill", (e) => markPrefill(e.target));
  echo();
  // empty date fields show their mm/dd/yyyy hint in the placeholder colour
  const dates = $$('input[type="date"]', form);
  const mark = (el) => el.toggleAttribute("data-empty", !el.value);
  dates.forEach(mark);
  form.addEventListener("input", (e) => { if (e.target.type === "date") mark(e.target); });
  // the empty state's example: fills the form with a real check and runs it (any address: one of the sample addresses)
  $("[data-ck-try]", main)?.addEventListener("click", () => {
    if (!id) { S.values = { ...readForm(form), current_rent: "$2,000", new: "$2,100" }; S.autorun = true; CE.navigate("check/A0016"); return; }
    $("#ck-current_rent", form).value = "$2,000"; $("#ck-new", form).value = "$2,100"; echo(); form.requestSubmit();
  });
  main.addEventListener("click", (e) => {
    const b = e.target.closest("[data-ck-fix]");
    if (!b) return;
    const el = $(`#ck-${b.dataset.ckFix}`, main);
    if (!el) return;
    el.closest("details")?.setAttribute("open", "");
    el.scrollIntoView({ block: "center", behavior: "smooth" });
    el.focus({ preventScroll: true });
  });
  const focus = sessionStorage.getItem("ck.focus");
  sessionStorage.removeItem("ck.focus");
  if (focus) { const el = $(`#ck-${focus}`, main); el?.closest("details")?.setAttribute("open", ""); setTimeout(() => el?.focus(), 50); }
  if (S.result || S.autorun) { S.autorun = false; submit(main, !id); } // language change or a known address picked from #/check: run the check
}
CE.addRoute("check", view);

// ------------------------------------------------------------------ entry points on the address page --
const ENTRY = { rent_increase_limits: ["entry", null], security_deposits: ["entry_dep", "deposit"], application_screening_fees: ["entry_fee", "application_fee"] };
function inject() {
  const m = location.hash.match(/^#\/a\/([^/?#]+)/);
  if (!m) return;
  const id = decodeURIComponent(m[1]).toUpperCase();
  for (const [cat, [label, focus]] of Object.entries(ENTRY)) {
    const slot = $(`[data-slot="topic-actions"][data-cat="${cat}"]`);
    if (!slot || $("a.ck-entry", slot)) continue;
    slot.insertAdjacentHTML("beforeend", `<a class="ck-entry" href="#/check/${esc(id)}"${focus ? ` data-ck-focus="${focus}"` : ""}>${esc(t(label))}</a>`);
  }
}
document.addEventListener("click", (e) => { const a = e.target.closest("a.ck-entry[data-ck-focus]"); if (a) sessionStorage.setItem("ck.focus", a.dataset.ckFocus); });
new MutationObserver(() => inject()).observe($("#main"), { childList: true, subtree: true });
document.addEventListener("ce:route", inject);
inject();
