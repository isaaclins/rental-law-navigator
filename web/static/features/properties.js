// My properties (#38, #152). Self-contained feature module: a property dashboard. Signed out it opens the read-only
// example portfolio; signed in (Google) it holds the reader's own buildings with the facts public data lacks. Per
// building: its photo, a plain status line, one dot per topic coloured by result, the next dated change in plain words
// and the next lawful rent increase (date, most you may charge, notice deadline: POST-free, computed by the check
// engine on the server, web/accounts.py next_raise). On top: the numbers an owner cares about and a "Coming up"
// timeline across all buildings. Routes: #/properties (dashboard), #/properties/<id> (one building), registered with
// window.CE.addRoute; answers render with CE.renderAnswers (web/DESIGN.md). Backend: web/accounts.py.
// Not legal advice. Design language: web/DESIGN.md.

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const CE = window.CE;
const main = $("#main");
const lang = () => CE.lang();
const asOf = () => CE.asOf();

// ------------------------------------------------------------------ i18n --
const EN = {
  nav: "My properties", nav_short: "Mine", title: "My properties",
  sub: (d) => `As of ${d}. Not legal advice.`,
  out_lead: "Save the buildings you own, manage or rent. See which rules apply to each one, and get an email before a change takes effect.",
  google: "Sign in with Google", demo: "See an example portfolio",
  fine: "We store your email, your name and the buildings you save. Delete anytime.",
  ex_t: "Example portfolio", ex_b: "Sign in with Google to save your own.", ex_nums: "Example numbers",
  st_bldg: (n) => (n === 1 ? "building" : "buildings"), st_bldg_s: (c) => c,
  st_chg: (n) => (n === 1 ? "change in the next 12 months" : "changes in the next 12 months"), st_chg_s: (d) => `Next on ${d}`, st_chg_none: "Nothing dated ahead",
  st_q: (n) => (n === 1 ? "open question" : "open questions"), st_q_s: (n) => (n ? `${n} you can answer in one tap` : "Answers we can't give yet"), st_q_none: "Every answer is definite",
  st_notice: "next rent notice due", st_notice_s: (l, n) => `${l} · ${n} days ahead`, st_notice_none: "No rent notice dated yet", st_notice_add: "Add a rent to see it",
  coming: "Coming up", coming_s: "Next 24 months, all buildings", coming_none: "Nothing dated in the next 24 months.", today: "Today",
  ev_notice: "Send rent notice", ev_raise: (v) => `Raise up to ${v}`,
  bldgs: "Your buildings",
  open: (l) => `Open ${l}`,
  // status line (6 words or fewer)
  s_cap: (p, d) => `Rent capped at ${p}% until ${d}`, s_cap0: (p) => `Rent capped at ${p}%`,
  s_cpi: (b) => `Raises capped at ${b}% plus inflation`, s_city: "City sets a yearly raise limit", s_rc: "City rent control limits raises",
  s_none: "No rent cap on this building", s_unk: "We can't tell yet", s_later: (d) => `Rent cap starts ${d}`, s_q: (f) => `We can't tell yet: ${f}`,
  qf_year_built: "year built?", qf_units: "how many units?", qf_owner_occupied: "owner lives there?",
  q_owner: "Does the owner live in the building?", q_units: "How many units does the building have?",
  q_year1: (y) => `Was it built in ${y} or earlier?`, q_year: "When was it built?", q_before: (y) => `Before ${y}`, q_after: (y) => `After ${y}`,
  q_lead: "We can't tell yet.", q_try: "Example: not saved", q_saved: (n) => (n ? `Saved · ${n} ${n === 1 ? "answer" : "answers"} updated` : "Saved"),
  yes: "Yes", no: "No", unsure: "Not sure",
  topics: "Topics", t_rent_increase_limits: "Rent increases", t_just_cause_eviction: "Evictions", t_security_deposits: "Deposit",
  t_application_screening_fees: "Fees", t_screening_restrictions: "Screening", t_algorithmic_rent_setting: "Rent software",
  r_applies: "a limit or protection", r_unknown: "we need one answer", r_not_yet_effective: "starts later", r_no_rule: "no limit here", r_exempt: "this building is exempt", r_superseded: "replaced here",
  next_none: "No dated change ahead",
  // next raise (#152)
  nr: "Next raise", nr_q: "When can I raise the rent next?", nr_add: "Add last raise and rent", nr_last: "Last raise took effect", nr_rent: "Rent now (per month)",
  nr_upto: (v) => `up to ${v}`, nr_upto_l: (v) => `Up to ${v} a month`, nr_by: (d) => `send notice by ${d}`, nr_by_l: (d) => `Send notice by ${d}`, nr_today: "send the notice today",
  nr_days: (n) => `${n} days ahead, in writing`, nr_days_if: (n, p) => `${n} days ahead, for a raise under ${p}%`,
  nr_after: "send notice after the cap is out", nr_notice_na: "notice period not in our sources",
  nr_notout: "Cap not out yet", nr_notsrc: "Not in our sources", nr_need: "We need one answer first", nr_nocap: "No legal cap",
  nr_notout_w: (p, d, a) => `${p}% ends ${d}. ${a} sets the next one.`, nr_notsrc_w: (p, d, a) => `${p}% ran to ${d}. ${a} sets the new figure.`,
  nr_cpi: (v, m) => `at most ${v} (${m}% max)`, nr_cpi_w: "The exact cap depends on local inflation.", nr_nocap_w: "No rent cap covers this building. Notice rules still apply.",
  nr_from: (d, r) => `From your last raise on ${d} and rent of ${r}.`, nr_from_ex: (d, r) => `Example: last raise ${d}, rent ${r}.`,
  draft: "Draft the notice", why: "Why", edit: "Edit", add_cal: "Add to calendar", save: "Save", cancel: "Cancel", clear: "Clear",
  why_t: (d, v) => (v ? `Why ${d} and ${v}` : `Why ${d}`), why_sub: (l, d, r) => `${l} · last raise ${d} · rent ${r}`,
  why_12: "One raise per 12 months", why_12_b: (a, b) => `Your last raise took effect ${a}, so the next can start ${b}.`, why_12_now: (a, b) => `12 months since ${a} have passed; with notice, the earliest is ${b}.`,
  why_cap: (p) => `The cap: ${p}%`, why_cap_x: "The cap", why_notice: (n) => `The notice: ${n} days`, why_notice_x: "The notice",
  why_notice_none: "Our sources don't state a notice period for rent increases in this state. Ask your city's housing office.",
  retrieved: (d) => `retrieved ${d}`, ics_t: (l) => `Send rent notice: ${l}`, ics_s: "In your calendar feed · Google, Apple, Outlook",
  // card actions
  check: "Check a rent increase", changed: "What changed", remove: "Remove", remove_t: (l) => `Remove “${l}”?`, remove_b: "The building and its facts are removed from your account.",
  add_t: "Add a building", add_s: "Any address in California, New Jersey or Massachusetts.", add_ph: "Street, city, state", add_go: "Find",
  add_demo: "Sign in to add your own buildings.",
  ta_ours: "Addresses we know", ta_any: "Any other address", ta_lookup: "Look up this address", ta_more: "Keep typing: street, city and state",
  ta_nomatch: (q) => `We couldn't find “${q}”`, ta_nomatch_s: "Add the city and state, e.g. 3918 Fulton St, San Francisco, CA", added: (l) => `Added “${l}”`, undo: "Undo",
  // events in plain words
  e_fig_rent: (p) => `${p} sets the new raise limit`, e_fig_fee: (p) => `${p} sets the new fee cap`, e_fig_dep: (p) => `${p} updates the deposit cap`, e_fig: (p) => `${p} sets a new figure`,
  e_start: (p, t) => `${p} ${t} starts`, e_end: (p, t) => `${p} ${t} ends`, e_ends2: (p, t) => `${p} ${t} end`, e_chg: (p, t) => `${p} ${t} changes`, e_backup: (p) => `${p} rules end; city rules stay`,
  and: "and",
  n_rent_increase_limits: "rent limit", n_just_cause_eviction: "eviction protection", n_security_deposits: "deposit rule",
  n_application_screening_fees: "fee cap", n_screening_restrictions: "screening rule", n_algorithmic_rent_setting: "rent-software ban",
  CA: "California", NJ: "New Jersey", MA: "Massachusetts",
  // settings
  set_t: "Calendar and alerts", cal_t: "Calendar feed", cal: "Every date and rent notice for your buildings. Updates daily.",
  cal_google: "Google", cal_apple: "Apple · Outlook", cal_copy: "Copy link", cal_copied: "Calendar link copied",
  cal_private: "Private link: anyone who has it sees your building names and dates.", cal_new: "New link", cal_rotated: "New calendar link. The old one no longer works.",
  mail_t: "Email alerts", mail_digest: "Email me about 30 days before a change", mail_note: (e) => `To ${e}. One-click unsubscribe in every email.`,
  mail_demo: "The example portfolio doesn't send email.",
  // account
  signout: "Sign out", delete_acct: "Delete account", privacy: "Privacy", terms: "Terms",
  delacct_t: "Delete your account?", delacct_b: "This deletes your account, every saved building, your alert settings and your calendar link. It cannot be undone.",
  delacct_go: "Delete everything", acct_deleted: "Account deleted", signin_failed: "Google sign-in did not complete. Please try again.",
  // detail
  back: "My properties", edit_facts: "Edit facts", whats_changing: "What’s changing", facts: "Building facts",
  year_built: "Year built", units: "Units", owner_occupied: "Owner lives there", certificate_of_occupancy_date: "Certificate of occupancy",
  not_given: "Not given", built: (y) => `built ${y}`, n_units: (n) => `${n} ${n === 1 ? "unit" : "units"}`,
  prompt: (f, n) => `Add “${f}” to settle ${n} open answer${n === 1 ? "" : "s"}.`, all_clear: "Every answer is definite for these facts.",
  fig_note: (d) => `Today's figure covers the period to ${d}. The law stays; a new figure follows.`, ends_note: "The city rule still applies here.",
  pending_t: "Bills that are not law yet", pending_n: "Would apply if passed. Not in force.", nothing_ahead: "No dated change is on record for this building.",
  // add / edit sheet
  a_title: "Add a building", a_addr: "Address", a_addr_ph: "Street, city, state", a_find: "Find",
  a_locating: "Finding the address…", a_label: "Name", a_label_ph: "e.g. Bloomfield brownstone", a_save: "Save building",
  a_facts_lead: "Only what public records can’t tell. Leave blank if unsure.", a_nomatch: "We could not find this address. Add the city and state.",
  a_out: "This address is outside the states we cover (California, New Jersey, Massachusetts).",
  a_store: "Stored: this address, its facts and your rent numbers. Never tenant names.", a_rent_lead: "For the next lawful raise (optional).",
  city_state: "City and state rules", state_only: "State law only",
  saved: "Saved", deleted: "Removed", updated: "Facts updated",
  r_applies_b: "Applies", r_unknown_b: "Open", r_superseded_b: "Replaced", r_not_yet_effective_b: "Starts later", r_pending_b: "Bill",
  error: "Something went wrong.", demo_ro: "The example portfolio can't be changed. Sign in to save your own.",
};
const ES = {
  nav: "Mis propiedades", nav_short: "Mías", title: "Mis propiedades",
  sub: (d) => `Al ${d}. No es asesoría legal.`,
  out_lead: "Guarde los edificios que posee, administra o alquila. Vea qué normas aplican a cada uno y reciba un correo antes de que un cambio entre en vigor.",
  google: "Acceder con Google", demo: "Ver una cartera de ejemplo",
  fine: "Guardamos su correo, su nombre y los edificios que guarde. Puede borrarlo todo cuando quiera.",
  ex_t: "Cartera de ejemplo", ex_b: "Acceda con Google para guardar la suya.", ex_nums: "Cifras de ejemplo",
  st_bldg: (n) => (n === 1 ? "edificio" : "edificios"), st_bldg_s: (c) => c,
  st_chg: (n) => (n === 1 ? "cambio en los próximos 12 meses" : "cambios en los próximos 12 meses"), st_chg_s: (d) => `El próximo: ${d}`, st_chg_none: "Nada con fecha por delante",
  st_q: (n) => (n === 1 ? "pregunta abierta" : "preguntas abiertas"), st_q_s: (n) => (n ? `${n} con respuesta de un toque` : "Respuestas que aún no podemos dar"), st_q_none: "Todas las respuestas son claras",
  st_notice: "próximo aviso de aumento", st_notice_s: (l, n) => `${l} · ${n} días antes`, st_notice_none: "Sin aviso con fecha", st_notice_add: "Agregue una renta para verlo",
  coming: "Próximamente", coming_s: "Próximos 24 meses, todos los edificios", coming_none: "Nada con fecha en los próximos 24 meses.", today: "Hoy",
  ev_notice: "Enviar aviso de aumento", ev_raise: (v) => `Aumento hasta ${v}`,
  bldgs: "Sus edificios",
  open: (l) => `Abrir ${l}`,
  s_cap: (p, d) => `Renta limitada a ${p}% hasta ${d}`, s_cap0: (p) => `Renta limitada a ${p}%`,
  s_cpi: (b) => `Aumentos hasta ${b}% más inflación`, s_city: "La ciudad fija un límite anual", s_rc: "Control de rentas de la ciudad",
  s_none: "Sin tope de renta aquí", s_unk: "Aún no sabemos", s_later: (d) => `Tope de renta desde ${d}`, s_q: (f) => `Aún no sabemos: ${f}`,
  qf_year_built: "¿año de construcción?", qf_units: "¿cuántas unidades?", qf_owner_occupied: "¿vive el dueño allí?",
  q_owner: "¿Vive el dueño en el edificio?", q_units: "¿Cuántas unidades tiene el edificio?",
  q_year1: (y) => `¿Se construyó en ${y} o antes?`, q_year: "¿Cuándo se construyó?", q_before: (y) => `Antes de ${y}`, q_after: (y) => `Después de ${y}`,
  q_lead: "Aún no lo sabemos.", q_try: "Ejemplo: no se guarda", q_saved: (n) => (n ? `Guardado · ${n} ${n === 1 ? "respuesta actualizada" : "respuestas actualizadas"}` : "Guardado"),
  yes: "Sí", no: "No", unsure: "No sé",
  topics: "Temas", t_rent_increase_limits: "Aumentos de renta", t_just_cause_eviction: "Desalojos", t_security_deposits: "Depósito",
  t_application_screening_fees: "Cargos", t_screening_restrictions: "Selección", t_algorithmic_rent_setting: "Software de rentas",
  r_applies: "hay un límite o protección", r_unknown: "falta una respuesta", r_not_yet_effective: "empieza más tarde", r_no_rule: "sin límite aquí", r_exempt: "este edificio está exento", r_superseded: "reemplazada aquí",
  next_none: "Sin cambios con fecha",
  nr: "Próximo aumento", nr_q: "¿Cuándo puedo subir la renta?", nr_add: "Agregar último aumento y renta", nr_last: "Último aumento desde", nr_rent: "Renta actual (al mes)",
  nr_upto: (v) => `hasta ${v}`, nr_upto_l: (v) => `Hasta ${v} al mes`, nr_by: (d) => `aviso antes del ${d}`, nr_by_l: (d) => `Envíe el aviso antes del ${d}`, nr_today: "envíe el aviso hoy",
  nr_days: (n) => `${n} días antes, por escrito`, nr_days_if: (n, p) => `${n} días antes, para un aumento de menos del ${p}%`,
  nr_after: "aviso cuando se publique el tope", nr_notice_na: "plazo de aviso no está en nuestras fuentes",
  nr_notout: "Tope aún no publicado", nr_notsrc: "No está en nuestras fuentes", nr_need: "Falta una respuesta", nr_nocap: "Sin tope legal",
  nr_notout_w: (p, d, a) => `El ${p}% termina el ${d}. ${a} fija el siguiente.`, nr_notsrc_w: (p, d, a) => `El ${p}% rigió hasta el ${d}. ${a} fija la nueva cifra.`,
  nr_cpi: (v, m) => `como máximo ${v} (${m}% máx.)`, nr_cpi_w: "El tope exacto depende de la inflación local.", nr_nocap_w: "Ningún tope de renta cubre este edificio. Las reglas de aviso siguen vigentes.",
  nr_from: (d, r) => `Según su último aumento del ${d} y una renta de ${r}.`, nr_from_ex: (d, r) => `Ejemplo: último aumento ${d}, renta ${r}.`,
  draft: "Redactar el aviso", why: "Por qué", edit: "Editar", add_cal: "Agregar al calendario", save: "Guardar", cancel: "Cancelar", clear: "Borrar",
  why_t: (d, v) => (v ? `Por qué ${d} y ${v}` : `Por qué ${d}`), why_sub: (l, d, r) => `${l} · último aumento ${d} · renta ${r}`,
  why_12: "Un aumento cada 12 meses", why_12_b: (a, b) => `Su último aumento rige desde el ${a}; el siguiente puede empezar el ${b}.`, why_12_now: (a, b) => `Ya pasaron 12 meses desde el ${a}; con aviso, lo más pronto es el ${b}.`,
  why_cap: (p) => `El tope: ${p}%`, why_cap_x: "El tope", why_notice: (n) => `El aviso: ${n} días`, why_notice_x: "El aviso",
  why_notice_none: "Nuestras fuentes no indican un plazo de aviso para aumentos en este estado. Consulte la oficina de vivienda de su ciudad.",
  retrieved: (d) => `consultado ${d}`, ics_t: (l) => `Enviar aviso de aumento: ${l}`, ics_s: "En su calendario · Google, Apple, Outlook",
  check: "Revisar un aumento", changed: "Qué cambió", remove: "Quitar", remove_t: (l) => `¿Quitar “${l}”?`, remove_b: "El edificio y sus datos se eliminan de su cuenta.",
  add_t: "Agregar un edificio", add_s: "Cualquier dirección en California, Nueva Jersey o Massachusetts.", add_ph: "Calle, ciudad, estado", add_go: "Buscar",
  add_demo: "Acceda para agregar sus edificios.",
  ta_ours: "Direcciones que conocemos", ta_any: "Cualquier otra dirección", ta_lookup: "Buscar esta dirección", ta_more: "Siga escribiendo: calle, ciudad y estado",
  ta_nomatch: (q) => `No encontramos “${q}”`, ta_nomatch_s: "Agregue ciudad y estado, p. ej. 3918 Fulton St, San Francisco, CA", added: (l) => `Agregado: “${l}”`, undo: "Deshacer",
  e_fig_rent: (p) => `${p} fija el nuevo límite de aumento`, e_fig_fee: (p) => `${p} fija el nuevo tope de cargos`, e_fig_dep: (p) => `${p} actualiza el tope de depósito`, e_fig: (p) => `${p} fija una nueva cifra`,
  e_start: (p, t) => `Empieza: ${t} de ${p}`, e_end: (p, t) => `Termina: ${t} de ${p}`, e_ends2: (p, t) => `Terminan: ${t} de ${p}`, e_chg: (p, t) => `Cambia: ${t} de ${p}`, e_backup: (p) => `Terminan normas de ${p}; siguen las de la ciudad`,
  and: "y",
  n_rent_increase_limits: "límite de renta", n_just_cause_eviction: "protección contra desalojo", n_security_deposits: "regla de depósito",
  n_application_screening_fees: "tope de cargos", n_screening_restrictions: "regla de selección", n_algorithmic_rent_setting: "prohibición de software de rentas",
  CA: "California", NJ: "Nueva Jersey", MA: "Massachusetts",
  set_t: "Calendario y alertas", cal_t: "Calendario", cal: "Cada fecha y aviso de aumento de sus edificios. Se actualiza a diario.",
  cal_google: "Google", cal_apple: "Apple · Outlook", cal_copy: "Copiar enlace", cal_copied: "Enlace copiado",
  cal_private: "Enlace privado: quien lo tenga ve los nombres de sus edificios y las fechas.", cal_new: "Nuevo enlace", cal_rotated: "Nuevo enlace. El anterior ya no funciona.",
  mail_t: "Alertas por correo", mail_digest: "Avisarme unos 30 días antes de un cambio", mail_note: (e) => `A ${e}. Cada correo permite darse de baja con un clic.`,
  mail_demo: "La cartera de ejemplo no envía correos.",
  signout: "Cerrar sesión", delete_acct: "Eliminar cuenta", privacy: "Privacidad", terms: "Términos",
  delacct_t: "¿Eliminar su cuenta?", delacct_b: "Se eliminan su cuenta, todos los edificios, sus alertas y su enlace de calendario. No se puede deshacer.",
  delacct_go: "Eliminar todo", acct_deleted: "Cuenta eliminada", signin_failed: "El acceso con Google no se completó. Inténtelo de nuevo.",
  back: "Mis propiedades", edit_facts: "Editar datos", whats_changing: "Qué va a cambiar", facts: "Datos del edificio",
  year_built: "Año de construcción", units: "Unidades", owner_occupied: "El dueño vive allí", certificate_of_occupancy_date: "Certificado de ocupación",
  not_given: "Sin dato", built: (y) => `construido en ${y}`, n_units: (n) => `${n} ${n === 1 ? "unidad" : "unidades"}`,
  prompt: (f, n) => `Indique “${f}” para resolver ${n} respuesta${n === 1 ? "" : "s"} abierta${n === 1 ? "" : "s"}.`, all_clear: "Todas las respuestas son claras con estos datos.",
  fig_note: (d) => `La cifra actual cubre hasta el ${d}. La ley sigue; luego viene una nueva cifra.`, ends_note: "La norma de la ciudad sigue aplicando aquí.",
  pending_t: "Proyectos que aún no son ley", pending_n: "Aplicarían si se aprueban. No están vigentes.", nothing_ahead: "No hay cambios con fecha para este edificio.",
  a_title: "Agregar un edificio", a_addr: "Dirección", a_addr_ph: "Calle, ciudad, estado", a_find: "Buscar",
  a_locating: "Buscando la dirección…", a_label: "Nombre", a_label_ph: "p. ej. Casa Bloomfield", a_save: "Guardar edificio",
  a_facts_lead: "Solo lo que los registros públicos no dicen. Déjelo vacío si no sabe.", a_nomatch: "No encontramos esta dirección. Agregue ciudad y estado.",
  a_out: "Esta dirección está fuera de los estados que cubrimos (California, Nueva Jersey, Massachusetts).",
  a_store: "Se guarda: la dirección, sus datos y sus cifras de renta. Nunca nombres de inquilinos.", a_rent_lead: "Para el próximo aumento legal (opcional).",
  city_state: "Normas de ciudad y estado", state_only: "Solo ley estatal",
  saved: "Guardado", deleted: "Quitado", updated: "Datos actualizados",
  r_applies_b: "Aplica", r_unknown_b: "Abierta", r_superseded_b: "Reemplazada", r_not_yet_effective_b: "Más tarde", r_pending_b: "Proyecto",
  error: "Algo salió mal.", demo_ro: "La cartera de ejemplo no se puede cambiar. Acceda para guardar la suya.",
};
const t = (k) => (lang() === "es" && ES[k]) || EN[k] || k;
const loc = () => (lang() === "es" ? "es-US" : "en-US");
const day = (d) => new Date(String(d).slice(0, 10) + "T12:00:00");
const fmtDate = (d, opts = { month: "short", day: "numeric", year: "numeric" }) => { const x = day(d); return isNaN(x) ? d || "" : x.toLocaleDateString(loc(), opts); };
const fmtMY = (d) => fmtDate(d, { month: "short", year: "numeric" });
const fmtMD = (d) => fmtDate(d, { month: "short", day: "numeric" });
const money = (n) => new Intl.NumberFormat(loc(), { style: "currency", currency: "USD", minimumFractionDigits: n % 1 ? 2 : 0, maximumFractionDigits: 2 }).format(n);
const pct = (p) => new Intl.NumberFormat(loc(), { maximumFractionDigits: 2 }).format(p);
const daysBetween = (a, b) => Math.round((day(b) - day(a)) / 864e5);
const relTime = (d) => {
  const days = daysBetween(asOf(), d);
  const rtf = new Intl.RelativeTimeFormat(lang(), { numeric: "auto" });
  if (Math.abs(days) < 45) return rtf.format(days, "day");
  if (Math.abs(days) < 640) return rtf.format(Math.round(days / 30.4), "month");
  return rtf.format(Math.round(days / 365.25), "year");
};
const host = (u) => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return ""; } };

// ------------------------------------------------------------------ icons --
const svg = (p) => `<svg class="ico" viewBox="0 0 24 24" aria-hidden="true">${p}</svg>`;
const I = {
  back: svg('<path d="M19 12H5M11 6l-6 6 6 6"/>'),
  arrow: svg('<path d="M5 12h14M13 6l6 6-6 6"/>'),
  plus: svg('<path d="M12 5v14M5 12h14"/>'),
  cal: svg('<rect x="4" y="5" width="16" height="15" rx="3"/><path d="M8 3v4M16 3v4M4 10h16"/>'),
  mail: svg('<rect x="3" y="5" width="18" height="14" rx="3"/><path d="m4 7 8 6 8-6"/>'),
  search: svg('<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.5 4.5"/>'),
  check: svg('<path d="m5 12 4.5 4.5L19 7"/>'),
  chev: svg('<path d="m9 6 6 6-6 6"/>'),
  trash: svg('<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>'),
  pen: svg('<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="m13.5 6.5 4 4"/>'),
  alert: svg('<path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17.5v.01"/>'),
  ext: svg('<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>'),
  cat: {
    rent_increase_limits: svg('<path d="M3 17l6-6 4 4 8-8"/><path d="M14 7h7v7"/>'),
    just_cause_eviction: svg('<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="m9 12 2 2 4-4"/>'),
    security_deposits: svg('<rect x="3" y="6" width="18" height="13" rx="2"/><path d="M3 10h18M16 15h2"/>'),
    application_screening_fees: svg('<path d="M6 3h12v18l-3-2-3 2-3-2-3 2z"/><path d="M9 8h6M9 12h6"/>'),
    screening_restrictions: svg('<circle cx="10" cy="8" r="4"/><path d="M3 20c.8-3.7 3.6-6 7-6"/><circle cx="17" cy="16" r="3"/><path d="m21 20-1.8-1.8"/>'),
    algorithmic_rent_setting: svg('<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>'),
  },
};
const TOPICS = ["rent_increase_limits", "just_cause_eviction", "security_deposits", "application_screening_fees", "screening_restrictions", "algorithmic_rent_setting"];
const G_LOGO = `<svg viewBox="0 0 48 48" aria-hidden="true"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>`;
const loginHref = () => `/auth/google/login?next=${encodeURIComponent("/#/properties")}`;
const gsiButton = (cls = "") => `<a class="gsi ${cls}" href="${loginHref()}">${G_LOGO}<span>${esc(t("google"))}</span></a>`;

// city photo for a building (the generated photoreal set in /static/img; a missing file falls back to the stage colour)
const CITY_IMG = { "San Francisco": "san-francisco", "Los Angeles": "los-angeles", Hoboken: "hoboken", "Jersey City": "jersey-city", Newark: "newark", Boston: "boston", Cambridge: "cambridge", Berkeley: "berkeley", "San Diego": "san-diego" };
const cityOf = (p) => (p.jurisdiction ? p.jurisdiction.replace(/, [A-Z]{2}$/, "") : p.place || "");
const photo = (p, sm = false) => `/static/img/${CITY_IMG[cityOf(p)] || "hero-building"}${sm && CITY_IMG[cityOf(p)] ? "-sm" : ""}.webp`;
const img = (src, cls = "", lazy = true, spring = false) => `<img src="${src}" alt="" class="${cls}" ${lazy ? 'loading="lazy"' : ""} decoding="async"${spring ? " data-spring" : ""} onerror="this.remove()">`;
const SHORT = { "San Francisco, CA": "SF", "Los Angeles, CA": "LA" };
const AGENCY = { "San Francisco, CA": { en: "The SF Rent Board", es: "La Junta de Rentas de SF" }, "Los Angeles, CA": { en: "LAHD", es: "LAHD" } };
const placeShort = (j) => SHORT[j] || (/^[A-Z]{2}$/.test(j || "") ? t(j) : String(j || "").replace(/, [A-Z]{2}$/, ""));
const agency = (j) => AGENCY[j]?.[lang()] || (lang() === "es" ? `La ciudad de ${placeShort(j)}` : `${placeShort(j)}`);
const STATUS = (s) => ({ applies: "ok", unknown: "unk", not_yet_effective: "soon", no_rule: "none", exempt: "none", superseded: "none", pending: "none" })[s] || "none";

// ------------------------------------------------------------------ rent-increase notice (#96, features/notice.js) --
// "Draft the notice" opens #/notice/p<id>?rent=&last=&new=&start= (its route lives in notice.js). window.CE is frozen,
// so the button shows only when that module is on the page (its script tag or window.CENotice).
const hasNotice = () => !!(window.CENotice || document.querySelector('script[src*="features/notice.js"]'));
function noticeHref(p) {
  const nr = p.next_raise || {};
  if (nr.state !== "ok" || !hasNotice()) return "";
  const q = new URLSearchParams({ rent: nr.current_rent, last: nr.last_increase_date, new: nr.max_rent, start: nr.date });
  return `#/notice/p${p.id}?${q}`;
}

// ------------------------------------------------------------------ api --
let ME = null;
async function j(url, { method = "GET", body } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET") headers["X-CSRF-Token"] = ME?.csrf || "";
  const r = await fetch(url, { method, headers, credentials: "same-origin", body: body === undefined ? undefined : JSON.stringify(body) });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) {
    const msg = typeof d.detail === "string" ? d.detail : r.status === 422 ? "Please check the values you entered." : r.status === 429 ? "Too many requests. Please wait a minute." : t("error");
    throw Object.assign(new Error(msg), { status: r.status });
  }
  return d;
}
const me = async () => (ME = await j("/api/me"));

// ------------------------------------------------------------------ small UI helpers --
const toast = (msg) => CE.toast(msg);
const rerender = () => render(main, (location.hash.match(/^#\/properties\/([^/?#]+)/) || [])[1]);
function openSheet(title, body, after) {
  CE.openModal(title, body);
  const m = $("#modal");
  m.classList.add("mp-sheet");
  after?.($(".modal-body", m));
}
const closeSheet = () => $("#modal [data-close]")?.click();
const skeleton = () => {
  const line = (w, h, m = 12, r = 10) => `<div class="sk" style="width:${w};height:${h}px;margin-top:${m}px;border-radius:${r}px"></div>`;
  return `<div class="mp-skel">${line("36%", 56, 0)}${line("24%", 16)}${line("100%", 132, 32, 28)}<div class="mp-skel-g">${line("100%", 420, 24, 28)}${line("100%", 420, 24, 28)}${line("100%", 420, 24, 28)}</div></div>`;
};

// ------------------------------------------------------------------ routing --
let seq = 0;
function navLink() {
  const tabs = $(".tabs");
  if (tabs && !$('a[data-route="properties"]', tabs)) {
    const a = document.createElement("a");
    a.href = "#/properties"; a.dataset.route = "properties";
    tabs.append(a);
  }
  const foot = $(".footer-links");
  if (foot && !$('a[href="#/properties"]', foot)) {
    const a = document.createElement("a");
    a.href = "#/properties"; a.dataset.mp = "1";
    foot.append(a);
  }
  $$('.tabs a[data-route="properties"], .footer-links a[href="#/properties"]').forEach((a) => { a.textContent = t("nav"); });
  $$('.tabs a[data-route="properties"]').forEach((a) => { a.dataset.short = t("nav_short"); a.dataset.tour = "properties"; });
}
async function render(_main, arg) {
  const my = ++seq;
  navLink();
  const id = /^\d+$/.test(arg || "") ? arg : null;
  if (arg === "signin-failed") { history.replaceState(null, "", "#/properties"); setTimeout(() => toast(t("signin_failed")), 300); }
  main.innerHTML = `<div class="mp-root">${skeleton()}</div>`;
  try {
    await me();
    if (my !== seq) return;
    // signed out: the read-only example portfolio opens right away (a quiet banner says so)
    if (!ME.signed_in) {
      try { await j("/auth/demo", { method: "POST" }); await me(); } catch { /* fall back to the sign-in page */ }
      if (my !== seq) return;
      if (!ME.signed_in) return paintSignedOut();
    }
    if (id) return await paintDetail(id, my);
    return await paintList(my);
  } catch (e) {
    if (my !== seq) return;
    if (e.status === 401) { ME = null; return paintSignedOut(); }
    main.innerHTML = `<div class="mp-root"><div class="empty">${esc(e.message || t("error"))} <a href="#/properties">${esc(t("back"))}</a></div></div>`;
  }
}
function paint(html, title) {
  main.innerHTML = `<div class="mp-root">${html}</div>`;
  document.title = `${title} · Clause & Effect`;
}

// ------------------------------------------------------------------ signed out (only when the example cannot open) --
function paintSignedOut() {
  paint(`<header class="mp-top"><div class="mp-title"><h1>${esc(t("title"))}</h1><p class="mp-lead">${esc(t("out_lead"))}</p></div></header>
    <div class="mp-cta">${ME?.google ? gsiButton() : ""}<button type="button" class="btn mp-demo">${esc(t("demo"))}</button></div>
    <p class="mp-small">${esc(t("fine"))} <a href="/privacy">${esc(t("privacy"))}</a> · <a href="/terms">${esc(t("terms"))}</a></p>`, t("nav"));
  $(".mp-demo", main).addEventListener("click", async (e) => {
    const b = e.currentTarget; b.disabled = true;
    try { await j("/auth/demo", { method: "POST" }); rerender(); } catch (err) { b.disabled = false; toast(err.message); }
  });
}

// ------------------------------------------------------------------ plain words for the engine's data --
// One dated change (several rule items on one day) in at most ~7 plain words: no titles, no ids, no "(+1 more)".
function evLabel(items) {
  const byKind = {};
  for (const it of items) (byKind[it.kind] ||= []).push(it);
  const kind = Object.keys(byKind).sort((a, b) => byKind[b].length - byKind[a].length)[0];
  const xs = byKind[kind], p = placeShort(xs[0].jurisdiction);
  const topics = [...new Set(xs.map((x) => t("n_" + x.category)))];
  const list = topics.length > 1 ? `${topics.slice(0, -1).join(", ")} ${t("and")} ${topics.at(-1)}` : topics[0];
  if (kind === "figure") {
    const c = xs[0].category;
    return t(c === "rent_increase_limits" ? "e_fig_rent" : c === "application_screening_fees" ? "e_fig_fee" : c === "security_deposits" ? "e_fig_dep" : "e_fig")(p);
  }
  if (kind === "takes_effect") return t("e_start")(p, list);
  if (kind === "ends") return xs.every((x) => x.from === "superseded") && xs[0].level === "state" ? t("e_backup")(p) : t(topics.length > 1 ? "e_ends2" : "e_end")(p, list);
  return t("e_chg")(p, list);
}
// The building's status in six words or fewer, led by the rent question (the one a landlord plans around).
function statusLine(p) {
  if (!p.brief) return { s: "unk", line: t("s_unk") }; // missing data never reads as "no cap"
  const b = p.brief || {}, nr = p.next_raise || {}, cn = nr.cap_now || {};
  const rent = (b.topics || []).find((x) => x.id === "rent_increase_limits") || {};
  if (b.question?.topic === "rent_increase_limits") return { s: "unk", line: t("s_q")(t("qf_" + b.question.fact)) };
  if (rent.status === "applies") {
    if (cn.code === "within") return { s: "ok", line: cn.end ? t("s_cap")(pct(cn.pct), fmtMY(cn.end)) : t("s_cap0")(pct(cn.pct)) };
    if (cn.code === "need_cpi") return { s: "ok", line: t("s_cpi")(pct(cn.base)) };
    if (cn.code === "no_cap" || cn.code === "state_bar") return { s: "none", line: t("s_none") };
    return { s: "ok", line: t("s_city") };
  }
  if (rent.status === "unknown") return { s: "unk", line: t("s_rc") };
  if (rent.status === "not_yet_effective") return { s: "soon", line: t("s_later")(fmtMY(nr.date || asOf())) };
  if (b.question) return { s: "unk", line: t("s_q")(t("qf_" + b.question.fact)) };
  if (["no_rule", "exempt", "no_limit"].includes(rent.status)) return { s: "none", line: t("s_none") };
  return { s: "unk", line: t("s_unk") };
}
const within = (d, months) => { const n = daysBetween(asOf(), d); return n > 0 && n <= months * 30.44; };

// ------------------------------------------------------------------ dashboard --
let LIST = null, ALERTS = null;
function accountBar(demo) {
  if (demo) return "";
  const u = ME.user;
  return `<details class="mp-menu"><summary class="tool" aria-label="${esc(u.email)}"><span class="mp-email">${esc(u.email)}</span><span class="chev">${I.chev}</span></summary>
      <div class="mp-pop">
        <button type="button" data-signout>${esc(t("signout"))}</button>
        <button type="button" class="danger" data-delacct>${esc(t("delete_acct"))}</button>
        <a href="/privacy">${esc(t("privacy"))}</a>
      </div></details>`;
}
function statsHtml(props) {
  const cities = [...new Set(props.map(cityOf).filter(Boolean))];
  const evs = eventsOf(props, 12); // the same list as Coming up and the cards
  const nextEv = evs[0];
  const nChg = evs.length;
  const nQ = props.reduce((n, p) => n + (p.summary.counts?.unknown || 0), 0);
  const nTap = props.filter((p) => p.brief?.question).length;
  const notices = props.map((p) => ({ p, n: p.next_raise?.notice, s: p.next_raise?.state })).filter((x) => x.n?.by && ["ok", "need_cpi", "no_cap"].includes(x.s) && x.n.by >= asOf()).sort((a, b) => a.n.by.localeCompare(b.n.by));
  const nx = notices[0], anyRent = props.some((p) => p.next_raise?.state !== "need_input");
  const cell = (big, label, sub, cls = "") => `<div class="mp-stat ${cls}"><b class="mp-num">${big}</b><span class="mp-stat-l">${esc(label)}</span><span class="mp-stat-s">${esc(sub)}</span></div>`;
  return `<section class="mp-stats" aria-label="${esc(t("title"))}">
    ${cell(props.length, t("st_bldg")(props.length), cities.join(" · "))}
    ${cell(nChg, t("st_chg")(nChg), nextEv ? t("st_chg_s")(fmtDate(nextEv.date)) : t("st_chg_none"))}
    ${cell(nQ, t("st_q")(nQ), nQ ? t("st_q_s")(nTap) : t("st_q_none"), nQ ? "is-unk" : "")}
    ${nx ? cell(esc(fmtMD(nx.n.by)), t("st_notice"), t("st_notice_s")(nx.p.label, nx.n.days), "is-act") : cell("–", t("st_notice"), anyRent ? t("st_notice_none") : t("st_notice_add"))}
  </section>`;
}
function eventsOf(props, months) {
  const ev = [];
  for (const p of props) {
    for (const e of p.summary.events || []) if (within(e.date, months)) ev.push({ date: e.date, label: evLabel(e.items), p, k: e.items[0].kind === "figure" ? "fig" : e.items[0].kind === "takes_effect" ? "soon" : "none" });
    const nr = p.next_raise || {};
    if (nr.notice?.by && ["ok", "need_cpi", "no_cap"].includes(nr.state) && nr.notice.by >= asOf() && within(nr.notice.by, months)) ev.push({ date: nr.notice.by, label: t("ev_notice"), p, k: "act" });
    if (nr.state === "ok" && nr.max_rent && within(nr.date, months)) ev.push({ date: nr.date, label: t("ev_raise")(money(nr.max_rent)), p, k: "act" });
  }
  ev.sort((a, b) => a.date.localeCompare(b.date) || a.p.id - b.p.id);
  return ev;
}
function comingHtml(props) {
  const ev = eventsOf(props, 24);
  const stop = (e, i) => `<li class="mp-stop k-${e.k}" style="--i:${i + 1}">
      <span class="mp-stop-d"><b>${esc(fmtDate(e.date))}</b><span>${esc(relTime(e.date))}</span></span>
      <span class="mp-stop-dot" aria-hidden="true"></span>
      <a class="mp-stop-c" href="#/properties/${e.p.id}">${img(photo(e.p, true), "mp-stop-img")}<span><b>${esc(e.label)}</b><span>${esc(e.p.label)}</span></span></a></li>`;
  return `<section class="mp-coming mp-panel">
    <div class="mp-sec-h"><h2>${esc(t("coming"))}</h2><span>${esc(t("coming_s"))}</span></div>
    ${ev.length ? `<ol class="mp-tl2"><li class="mp-stop k-today" style="--i:0"><span class="mp-stop-d"><b>${esc(t("today"))}</b><span>${esc(fmtDate(asOf()))}</span></span><span class="mp-stop-dot" aria-hidden="true"></span></li>${ev.map(stop).join("")}</ol>` : `<p class="mp-small">${esc(t("coming_none"))}</p>`}
  </section>`;
}
function dotsHtml(p) {
  const by = Object.fromEntries((p.brief?.topics || []).map((x) => [x.id, x]));
  return `<ul class="mp-dots" aria-label="${esc(t("topics"))}">${TOPICS.map((id, i) => {
    const x = by[id] || { status: "no_rule" }, lab = `${t("t_" + id)}: ${x.answer || t("r_" + x.status)}`;
    return `<li class="mp-dot mp-s-${STATUS(x.status)}" style="--d:${i}" title="${esc(lab)}"><span class="vh">${esc(lab)}</span>${I.cat[id]}</li>`;
  }).join("")}</ul>`;
}
function questionHtml(p) {
  const q = p.brief?.question;
  if (!q) return "";
  const b = (v, l) => `<button type="button" class="btn sm" data-ans="${esc(String(v))}">${esc(l)}</button>`;
  let text = "", btns = "";
  if (q.fact === "owner_occupied") { text = t("q_owner"); btns = b(true, t("yes")) + b(false, t("no")); }
  else if (q.fact === "units") { text = t("q_units"); btns = b(1, "1") + b(2, "2") + b(4, "3–4") + b(5, "5+"); }
  else if (q.fact === "year_built") {
    const ys = q.cuts || [];
    if (ys.length === 1) { text = t("q_year1")(ys[0]); btns = b(ys[0] - 1, t("yes")) + b(ys[0] + 1, t("no")); }
    else if (ys.length > 1) {
      text = t("q_year"); btns = b(ys[0] - 1, t("q_before")(ys[0]));
      for (let i = 1; i < ys.length; i++) btns += b(Math.round((ys[i - 1] + ys[i]) / 2), `${ys[i - 1]}–${ys[i]}`);
      btns += b(ys.at(-1) + 1, t("q_after")(ys.at(-1)));
    } else return "";
  }
  return `<div class="mp-q" data-fact="${esc(q.fact)}"><p><span>${esc(t("q_lead"))}</span> ${esc(text)}</p><div class="mp-q-b">${btns}</div></div>`;
}
// #152: the next lawful raise, compact (card) or full (building page)
function raiseHtml(p, demo, full = false) {
  const nr = p.next_raise || {}, n = nr.notice;
  if (nr.state === "need_input") {
    if (demo) return "";
    return `<div class="mp-raise is-empty"><p class="mp-raise-k">${esc(t("nr_q"))}</p><button type="button" class="btn sm" data-rent>${I.plus}<span>${esc(t("nr_add"))}</span></button></div>`;
  }
  let amount = "", why = "", noticeTxt = "", s = "ok";
  const known = ["ok", "need_cpi", "no_cap"].includes(nr.state);
  if (nr.state === "ok") amount = full ? `${esc(t("nr_upto_l")(money(nr.max_rent)))} <i>+${esc(pct(nr.cap_pct))}%</i>` : `${esc(t("nr_upto")(money(nr.max_rent)))} <i>+${esc(pct(nr.cap_pct))}%</i>`;
  else if (nr.state === "need_cpi") { amount = esc(t("nr_cpi")(money(nr.max_rent), pct(nr.cap_max))); why = t("nr_cpi_w"); }
  else if (nr.state === "no_cap") { amount = esc(t("nr_nocap")); why = t("nr_nocap_w"); s = "none"; }
  else if (nr.state === "cap_not_out") { amount = `<span class="mp-tag">${esc(t("nr_notout"))}</span>`; why = t("nr_notout_w")(pct(nr.last_pct), fmtDate(nr.cap_end), agency(nr.place)); s = "unk"; }
  else if (nr.state === "not_in_sources") { amount = `<span class="mp-tag">${esc(t("nr_notsrc"))}</span>`; why = nr.last_pct != null ? t("nr_notsrc_w")(pct(nr.last_pct), fmtDate(nr.cap_end), agency(nr.place)) : nr.why || ""; s = "unk"; }
  else if (nr.state === "need_fact") { amount = `<span class="mp-tag">${esc(t("nr_need"))}</span>`; s = "unk"; }
  if (!n) noticeTxt = t("nr_notice_na");
  else if (!known) noticeTxt = t("nr_after");
  else noticeTxt = n.by <= asOf() ? t("nr_today") : t(full ? "nr_by_l" : "nr_by")(fmtDate(n.by));
  const days = n && known ? (n.sure ? t("nr_days")(n.days) : t("nr_days_if")(n.days, pct(n.below_pct))) : "";
  const from = t(demo ? "nr_from_ex" : "nr_from")(fmtDate(nr.last_increase_date), money(nr.current_rent));
  const cal = ALERTS?.calendar;
  const nh = noticeHref(p);
  const acts = `${nh ? `<a class="btn sm mp-draft" href="${esc(nh)}">${I.pen}<span>${esc(t("draft"))}</span></a>` : ""}<div class="mp-raise-acts"><button type="button" class="linkish" data-why>${esc(t("why"))}</button>${known && n?.by && cal ? `<a class="linkish" href="${esc(cal.google)}" target="_blank" rel="noopener">${esc(t("add_cal"))}</a>` : ""}${demo ? "" : `<button type="button" class="linkish" data-rent>${esc(t("edit"))}</button>`}</div>`;
  if (full) {
    return `<section class="mp-raise full mp-s-${s}">
      <p class="mp-raise-k">${esc(t("nr"))}${demo ? `<span class="mp-ex">${esc(t("ex_nums"))}</span>` : ""}</p>
      <p class="mp-raise-big">${esc(fmtDate(nr.date))}</p>
      <p class="mp-raise-a">${amount}</p>${why ? `<p class="mp-raise-w">${esc(why)}</p>` : ""}
      <div class="mp-due">${img("/static/img/calendar-with-clock.webp", "mp-due-img")}<div><b>${esc(noticeTxt.charAt(0).toUpperCase() + noticeTxt.slice(1))}</b>${days ? `<span>${esc(days)}</span>` : ""}</div></div>
      ${nh ? `<a class="btn primary mp-cal-btn" href="${esc(nh)}">${I.pen}<span>${esc(t("draft"))}</span></a>` : ""}
      ${known && n?.by && cal ? `<a class="btn ${nh ? "" : "primary "}mp-cal-btn" href="${esc(cal.google)}" target="_blank" rel="noopener">${I.cal}<span>${esc(t("add_cal"))}</span></a>` : ""}
      <p class="mp-raise-from">${esc(from)} ${demo ? "" : `<button type="button" class="linkish" data-rent>${esc(t("edit"))}</button>`} <button type="button" class="linkish" data-why>${esc(t("why"))}</button></p>
    </section>`;
  }
  return `<div class="mp-raise mp-s-${s}">
    <p class="mp-raise-k">${esc(t("nr"))}${demo ? `<span class="mp-ex">${esc(t("ex_nums"))}</span>` : ""}</p>
    <p class="mp-raise-l"><b>${esc(fmtDate(nr.date))}</b><span class="mp-raise-a">${amount}</span></p>
    ${why ? `<p class="mp-raise-w">${esc(why)}</p>` : ""}
    <p class="mp-raise-n">${I.cal}<span>${esc(noticeTxt.charAt(0).toUpperCase() + noticeTxt.slice(1))}${days && n.by > asOf() ? ` · ${esc(n.sure ? `${n.days} ${lang() === "es" ? "días antes" : "days ahead"}` : days)}` : ""}</span></p>
    ${acts}
  </div>`;
}
function cardHtml(p, i, demo) {
  const st = statusLine(p), nx = p.summary.next;
  return `<article class="mp-card" style="--i:${i}" data-pid="${p.id}">
    <a class="mp-photo" href="#/properties/${p.id}" aria-label="${esc(t("open")(p.label))}">${img(photo(p), "", i > 2, true)}<span class="mp-place">${esc(cityOf(p) || p.state)}</span></a>
    <div class="mp-body">
      <h3 class="mp-name"><a href="#/properties/${p.id}">${esc(p.label)}</a></h3>
      <p class="mp-addr">${esc(p.address)}</p>
      <p class="mp-status mp-s-${st.s}">${esc(st.line)}</p>
      ${dotsHtml(p)}
      ${questionHtml(p)}
      ${raiseHtml(p, demo)}
      <p class="mp-next${nx ? "" : " none"}">${nx ? `<span class="mp-next-d">${esc(fmtDate(nx.date))}</span><span class="mp-next-t">${esc(evLabel(nx.items))}</span>` : `<span class="mp-next-t">${esc(t("next_none"))}</span>`}</p>
      <span class="mp-fill"></span>
      <div class="mp-acts">
        <button type="button" class="btn primary sm" data-check>${esc(t("check"))}</button>
        <a class="btn sm" href="#/properties/${p.id}/changes">${esc(t("changed"))}</a>
        ${demo ? "" : `<button type="button" class="icon-btn mp-rm" data-rm aria-label="${esc(t("remove"))}" title="${esc(t("remove"))}">${I.trash}</button>`}
      </div>
    </div>
  </article>`;
}
function addCardHtml(demo, i) {
  if (demo) return "";
  return `<article class="mp-card mp-addc" style="--i:${i}">
    <div class="mp-addc-art">${img("/static/img/house-with-checkmark.webp", "", true, true)}</div>
    <h3 class="mp-name">${esc(t("add_t"))}</h3><p class="mp-addr">${esc(t("add_s"))}</p>
    <div class="mp-ta">
      <form class="mp-search" data-addsearch role="search" autocomplete="off"><span class="mp-search-i">${I.search}</span><input name="q" type="text" role="combobox" aria-expanded="false" aria-controls="mp-ta-list" aria-autocomplete="list" spellcheck="false" autocomplete="off" placeholder="${esc(t("add_ph"))}" aria-label="${esc(t("add_t"))}" maxlength="200"></form>
      <ul class="suggest mp-ta-list" id="mp-ta-list" role="listbox" hidden></ul>
    </div>
  </article>`;
}
function settingsHtml(alerts, demo) {
  const cal = alerts.calendar;
  return `<section class="mp-settings mp-panel" aria-label="${esc(t("set_t"))}">
    <div class="mp-set-row">
      <span class="mp-set-i">${I.cal}</span>
      <div class="mp-set-t"><b>${esc(t("cal_t"))}</b><span>${esc(t("cal"))}</span></div>
      <div class="mp-set-a">
        <a class="btn sm" href="${esc(cal.google)}" target="_blank" rel="noopener">${esc(t("cal_google"))}</a>
        <a class="btn sm" href="${esc(cal.webcal)}">${esc(t("cal_apple"))}</a>
        <button type="button" class="btn sm" data-copy="${esc(cal.url)}">${esc(t("cal_copy"))}</button>
      </div>
      <p class="mp-set-f">${esc(t("cal_private"))}${demo ? "" : ` <button type="button" class="linkish" data-rotate>${esc(t("cal_new"))}</button>`}</p>
    </div>
    <div class="mp-set-row">
      <span class="mp-set-i">${I.mail}</span>
      <label class="mp-set-t mp-switch"><span><b>${esc(t("mail_t"))}</b><span>${esc(demo ? t("mail_demo") : t("mail_note")(alerts.email))}</span></span>
        <input type="checkbox" role="switch" aria-label="${esc(t("mail_digest"))}" data-digest ${alerts.email_digest ? "checked" : ""} ${demo ? "disabled" : ""}><span class="mp-knob" aria-hidden="true"></span></label>
    </div>
  </section>`;
}
async function paintList(my) {
  const [list, alerts] = await Promise.all([j(`/api/properties?as_of=${asOf()}&lang=${lang()}`), j("/api/alerts")]);
  if (my !== seq) return;
  LIST = list; ALERTS = alerts;
  const demo = list.demo, props = list.properties;
  paint(`<div class="mp-dash">
    <header class="mp-top">
      <div class="mp-title"><h1>${esc(t("title"))}</h1><p class="mp-lead">${esc(t("sub")(fmtDate(list.as_of)))}</p></div>
      <div class="mp-acct">${accountBar(demo)}</div>
    </header>
    ${demo ? `<div class="mp-exbar"><span class="mp-exdot" aria-hidden="true"></span><span><b>${esc(t("ex_t"))}</b> · ${esc(t("ex_b"))}</span>${ME.google ? gsiButton("sm") : ""}</div>` : ""}
    ${props.length ? statsHtml(props) + comingHtml(props) : ""}
    <section class="mp-bldgs">
      <div class="mp-sec-h"><h2>${esc(t("bldgs"))}</h2></div>
      <div class="mp-grid">${props.map((p, i) => cardHtml(p, i, demo)).join("")}${addCardHtml(demo, props.length)}</div>
    </section>
    ${settingsHtml(alerts, demo)}
  </div>`, t("nav"));
  wireAccount();
  wireList(demo);
}
function wireList(demo) {
  $("[data-copy]", main)?.addEventListener("click", async (e) => {
    try { await navigator.clipboard.writeText(e.currentTarget.dataset.copy); toast(t("cal_copied")); } catch { prompt("Calendar link", e.currentTarget.dataset.copy); }
  });
  $("[data-rotate]", main)?.addEventListener("click", async () => {
    try { await j("/api/alerts/calendar/rotate", { method: "POST" }); toast(t("cal_rotated")); rerender(); } catch (err) { toast(err.message); }
  });
  $("[data-digest]", main)?.addEventListener("change", async (e) => {
    try { await j("/api/alerts", { method: "PUT", body: { email_digest: e.target.checked } }); toast(t("saved")); } catch (err) { e.target.checked = !e.target.checked; toast(err.message); }
  });
  const ta = $(".mp-ta", main);
  if (ta) typeahead(ta);
}
// ------------------------------------------------------------------ add a building: instant typeahead --
// The same search as the home page and ⌘K (GET /api/addresses, the same scoring): our 500 sample addresses first,
// then "Look up this address" (POST /api/resolve, any address in the covered states). Picking a row adds the building.
const titleCase = (s) => String(s || "").toLowerCase().replace(/\b\w/g, (m) => m.toUpperCase());
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
function hl(text, q) {
  let out = esc(text);
  for (const term of q.split(/\s+/).filter((x) => x.length > 1)) out = out.replace(new RegExp("(" + term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "ig"), "<mark>$1</mark>");
  return out;
}
function typeahead(box) {
  const input = $("input", box), list = $(".mp-ta-list", box), form = $("form", box);
  let ADDR = [], items = [], sel = 0, timer = 0, busy = false;
  CE.api("/api/addresses").then((a) => { ADDR = a || []; }).catch(() => {});
  const close = () => { list.hidden = true; input.setAttribute("aria-expanded", "false"); input.removeAttribute("aria-activedescendant"); };
  const hint = (title, sub = "") => `<li class="opt empty" aria-disabled="true"><div><div class="addr">${esc(title)}</div>${sub ? `<div class="sub">${esc(sub)}</div>` : ""}</div></li>`;
  const mark = () => { $$(".opt[data-i]", list).forEach((li) => li.setAttribute("aria-selected", +li.dataset.i === sel)); input.setAttribute("aria-activedescendant", "mp-o-" + sel); };
  const render = () => {
    if (busy) return;
    const q = input.value.trim();
    if (!q) { close(); return; }
    const hits = ADDR.map((a) => [scoreAddr(a, q), a]).filter((x) => x[0] >= 0).sort((a, b) => b[0] - a[0]).slice(0, 5).map((x) => x[1]);
    items = hits.map((a) => ({ a }));
    if (q.length >= 5) items.push({ resolve: q });
    sel = 0;
    let html = hits.length ? `<li class="grp" role="presentation">${esc(t("ta_ours"))}</li>` : "";
    html += items.map((it, i) => it.a
      ? `<li class="opt" role="option" id="mp-o-${i}" data-i="${i}" aria-selected="${i === sel}"><div><div class="addr">${hl(titleCase(it.a.street), q)}</div><div class="sub">${hl(it.a.postal_city, q)}, ${esc(it.a.state)} ${esc(it.a.zip)}</div></div><span class="arrow">${I.plus}</span></li>`
      : `${hits.length ? `<li class="grp" role="presentation">${esc(t("ta_any"))}</li>` : ""}<li class="opt mp-ta-any" role="option" id="mp-o-${i}" data-i="${i}" aria-selected="${i === sel}"><div><div class="addr">${esc(t("ta_lookup"))}</div><div class="sub">${esc(q)}</div></div><span class="arrow">${I.search}</span></li>`).join("");
    if (!items.length) html = hint(t("ta_more"), t("add_s"));
    list.innerHTML = html;
    list.hidden = false; input.setAttribute("aria-expanded", "true");
  };
  const done = (li) => { li.classList.add("is-added"); li.querySelector(".arrow").innerHTML = I.check; };
  const pick = async (i) => {
    const it = items[i], li = $(`.opt[data-i="${i}"]`, list);
    if (!it || busy) return;
    busy = true;
    try {
      let body;
      if (it.a) body = { address_id: it.a.id, label: titleCase(it.a.street), address: `${titleCase(it.a.street)}, ${it.a.postal_city}, ${it.a.state} ${it.a.zip}` };
      else {
        li.classList.add("is-wait"); $(".addr", li).textContent = t("a_locating");
        const r = await j("/api/resolve", { method: "POST", body: { address: it.resolve } });
        if (!r.match || !r.in_scope) {
          li.outerHTML = hint(!r.match ? t("ta_nomatch")(it.resolve) : t("a_out"), !r.match ? t("ta_nomatch_s") : "");
          items = items.filter((x) => x !== it); busy = false; return;
        }
        const street = titleCase((r.matched_address || it.resolve).split(",")[0]);
        body = { label: street, address: r.matched_address ? titleCase(r.matched_address).replace(/, ([a-z]{2}),? (\d{5})$/i, (m, st, z) => `, ${st.toUpperCase()} ${z}`) : it.resolve, place: { state: r.state, jurisdiction: r.jurisdiction, place: r.place, county: r.county, matched_address: r.matched_address } };
      }
      done(li);
      const p = await j("/api/properties", { method: "POST", body });
      await new Promise((res) => setTimeout(res, 380)); // let the check land
      close(); input.value = "";
      await rerender();
      const card = $(`.mp-card[data-pid="${p.id}"]`, main);
      if (card) { card.classList.add("is-new"); card.scrollIntoView({ block: "nearest", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" }); }
      undoToast(p);
    } catch (err) {
      busy = false;
      if (li?.isConnected) li.outerHTML = hint(err.message || t("error"));
    }
    busy = false;
  };
  input.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(render, 120); });
  input.addEventListener("focus", render);
  input.addEventListener("blur", () => setTimeout(() => { if (!busy) close(); }, 150));
  input.addEventListener("keydown", (e) => {
    if (e.key === "Escape") return close();
    if (list.hidden || !items.length) return;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); sel = (sel + (e.key === "ArrowDown" ? 1 : -1) + items.length) % items.length; mark(); }
  });
  form.addEventListener("submit", (e) => { e.preventDefault(); clearTimeout(timer); if (list.hidden) render(); if (items[sel]) pick(sel); });
  list.addEventListener("mousedown", (e) => { const li = e.target.closest(".opt[data-i]"); if (li) { e.preventDefault(); pick(+li.dataset.i); } });
  list.addEventListener("mousemove", (e) => { const li = e.target.closest(".opt[data-i]"); if (li && +li.dataset.i !== sel) { sel = +li.dataset.i; mark(); } });
}
function undoToast(p) {
  $(".mp-undo")?.remove();
  const el = document.createElement("div");
  el.className = "mp-undo"; el.setAttribute("role", "status");
  el.innerHTML = `<span class="mp-undo-c">${I.check}</span><span>${esc(t("added")(p.label))}</span><button type="button" class="linkish">${esc(t("undo"))}</button>`;
  document.body.append(el);
  const kill = () => { el.classList.add("out"); setTimeout(() => el.remove(), 300); };
  const timer = setTimeout(kill, 7000);
  $("button", el).addEventListener("click", async () => {
    clearTimeout(timer); kill();
    try { await j(`/api/properties/${p.id}`, { method: "DELETE" }); toast(t("deleted")); if (/^#\/properties\/?$/.test(location.hash)) rerender(); } catch (err) { toast(err.message); }
  });
}

// card and building-page actions (delegated; the list re-renders on every change)
const propById = (id) => (LIST?.properties || []).find((p) => String(p.id) === String(id)) || (CUR && String(CUR.id) === String(id) ? CUR : null);
main.addEventListener("click", async (e) => {
  if (!e.target.closest(".mp-root")) return;
  const host_ = e.target.closest("[data-pid]");
  const p = host_ && propById(host_.dataset.pid);
  const demo = LIST?.demo ?? CUR?.demo;
  if (e.target.closest("[data-why]") && p) return whySheet(p, demo);
  if (e.target.closest("[data-rent]") && p) return rentSheet(p);
  if (e.target.closest("[data-check]") && p) return openCheck(p);
  if (e.target.closest("[data-rm]") && p) return removeSheet(p);
  if (e.target.closest("[data-edit]") && CUR) return editSheet(CUR);
  const ans = e.target.closest("[data-ans]");
  if (ans && p) return answer(p, ans, demo);
});
async function answer(p, btn, demo) {
  const q = btn.closest(".mp-q"), k = q.dataset.fact, raw = btn.dataset.ans;
  const v = k === "owner_occupied" ? raw === "true" : parseInt(raw, 10);
  const facts = { ...p.facts, [k]: v };
  for (const x of Object.keys(facts)) if (facts[x] == null) delete facts[x];
  $$("button", q).forEach((b) => { b.disabled = true; });
  btn.classList.add("is-on");
  const before = p.summary.counts?.unknown || 0;
  try {
    let np;
    if (demo) {
      const r = await j(`/api/properties/${p.id}/preview`, { method: "POST", body: { facts, as_of: asOf(), lang: lang() } });
      np = { ...p, ...r };
      toast(t("q_try"));
    } else {
      await j(`/api/properties/${p.id}`, { method: "PATCH", body: { facts } });
      const r = await j(`/api/properties/${p.id}/preview`, { method: "POST", body: { facts, as_of: asOf(), lang: lang() } });
      np = { ...p, ...r };
      toast(t("q_saved")(Math.max(0, before - (r.summary.counts?.unknown || 0))));
    }
    const i = LIST.properties.findIndex((x) => x.id === p.id);
    LIST.properties[i] = np;
    const card = $(`.mp-card[data-pid="${p.id}"]`, main);
    card.outerHTML = cardHtml(np, 0, demo).replace('class="mp-card"', 'class="mp-card is-new"');
    const stats = $(".mp-stats", main);
    if (stats) stats.outerHTML = statsHtml(LIST.properties).replace('class="mp-stats"', 'class="mp-stats is-new"');
  } catch (err) { $$("button", q).forEach((b) => { b.disabled = false; }); btn.classList.remove("is-on"); toast(err.message); }
}
// "Check a rent increase", prefilled with this building (features/check.js renders #/check; we fill its form)
function openCheck(p) {
  const nr = p.next_raise || {};
  const vals = { address: p.address, current_rent: nr.current_rent, effective_date: nr.state === "ok" ? nr.date : "", notice_date: nr.state === "ok" && nr.notice?.by ? nr.notice.by : "", year_built: p.facts.year_built, units: p.facts.units, owner_occupied: p.facts.owner_occupied == null ? "" : String(p.facts.owner_occupied) };
  CE.navigate("check");
  let n = 0;
  const fill = () => {
    const f = $(".ck-form", main);
    if (!f) { if (++n < 40) setTimeout(fill, 50); return; }
    for (const [k, v] of Object.entries(vals)) {
      const el = $(`#ck-${k}`, f);
      if (!el || v == null || v === "") continue;
      el.value = String(v);
      el.dispatchEvent(new Event("input", { bubbles: true }));
    }
    if (vals.year_built || vals.units) $(".ck-more", f)?.setAttribute("open", "");
    $("#ck-new", f)?.focus();
  };
  setTimeout(fill, 30);
}
function quoteBlock(r) {
  if (!r) return "";
  const when = r.retrieved ? t("retrieved")(fmtDate(String(r.retrieved).slice(0, 10))) : "";
  return `${r.quote ? `<blockquote class="quote" lang="en">“${esc(r.quote.replace(/\s+/g, " ").trim())}”</blockquote>` : ""}
    <p class="mp-cite">${esc(r.citation || "")}${r.url ? ` · <a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(host(r.url))}</a>` : ""}${when ? ` · ${esc(when)}` : ""}</p>`;
}
function whySheet(p, demo) {
  const nr = p.next_raise || {}, n = nr.notice, cap = nr.rules?.[0];
  const v = nr.state === "ok" ? money(nr.max_rent) : "";
  const known = ["ok", "need_cpi", "no_cap"].includes(nr.state);
  const cal = ALERTS?.calendar;
  const capTitle = nr.state === "ok" ? t("why_cap")(pct(nr.cap_pct)) : t("why_cap_x");
  const capNote = nr.state === "ok" ? "" : nr.state === "cap_not_out" ? t("nr_notout_w")(pct(nr.last_pct), fmtDate(nr.cap_end), agency(nr.place)) : nr.state === "not_in_sources" ? (nr.last_pct != null ? t("nr_notsrc_w")(pct(nr.last_pct), fmtDate(nr.cap_end), agency(nr.place)) : nr.why || t("nr_notsrc")) : nr.state === "need_cpi" ? t("nr_cpi_w") : nr.state === "no_cap" ? t("nr_nocap_w") : t("nr_need");
  const by = n?.by ? day(n.by) : null;
  openSheet(t("why_t")(fmtDate(nr.date), v), `<div class="mp-why">
    <p class="mp-small">${esc(t("why_sub")(p.address.split(",")[0], fmtDate(nr.last_increase_date), money(nr.current_rent)))}${demo ? ` · ${esc(t("ex_nums"))}` : ""}</p>
    <section class="mp-src"><h3>${esc(t("why_12"))}</h3><p>${esc((nr.now ? t("why_12_now") : t("why_12_b"))(fmtDate(nr.last_increase_date), fmtDate(nr.date)))}</p></section>
    <section class="mp-src"><h3>${esc(capTitle)}</h3>${capNote ? `<p>${esc(capNote)}</p>` : ""}${quoteBlock(cap)}</section>
    <section class="mp-src"><h3>${esc(n ? t("why_notice")(n.days) : t("why_notice_x"))}</h3>${n ? quoteBlock(n.rule) : `<p>${esc(t("why_notice_none"))}</p>`}</section>
    ${known && by && cal ? `<a class="mp-ics" href="${esc(cal.google)}" target="_blank" rel="noopener"><span class="mp-ics-cal"><i>${esc(by.toLocaleDateString(loc(), { month: "short" }).toUpperCase())}</i><b>${by.getDate()}</b></span><span><b>${esc(t("ics_t")(p.label))}</b><span>${esc(t("ics_s"))}</span></span></a>` : ""}
  </div>`);
}
function rentSheet(p) {
  const r = p.rent || {};
  openSheet(t("nr_q"), `<form class="mp-form" data-rentform>
      <div class="mp-fgrid">
        <label class="mp-field"><span>${esc(t("nr_last"))}</span><input name="last_increase_date" type="date" min="1990-01-01" max="2035-12-31" required value="${esc(r.last_increase_date || "")}"></label>
        <label class="mp-field"><span>${esc(t("nr_rent"))}</span><input name="current_rent" type="text" inputmode="decimal" autocomplete="off" required placeholder="$2,400" value="${r.current_rent ?? ""}"></label>
      </div>
      <div class="mp-row end">${r.current_rent ? `<button type="button" class="btn" data-clear>${esc(t("clear"))}</button>` : ""}<button type="button" class="btn" data-close>${esc(t("cancel"))}</button><button class="btn primary" type="submit">${esc(t("save"))}</button></div>
    </form>`, (b) => {
    const f = $("form", b);
    setTimeout(() => $("[name=last_increase_date]", f).focus(), 60);
    const send = async (rent) => {
      try { await j(`/api/properties/${p.id}`, { method: "PATCH", body: { rent } }); closeSheet(); toast(t("saved")); rerender(); } catch (err) { toast(err.message); }
    };
    $("[data-clear]", f)?.addEventListener("click", () => send({ last_increase_date: null, current_rent: null }));
    f.addEventListener("submit", (e) => {
      e.preventDefault();
      const d = $("[name=last_increase_date]", f).value, v = parseFloat($("[name=current_rent]", f).value.replace(/[^0-9.]/g, ""));
      if (!d || !(v > 0)) return toast(t("error"));
      send({ last_increase_date: d, current_rent: v });
    });
  });
}
function removeSheet(p) {
  openSheet(t("remove_t")(p.label), `<p class="mp-confirm">${esc(t("remove_b"))}</p><div class="mp-row end"><button type="button" class="btn" data-close>${esc(t("cancel"))}</button><button type="button" class="btn danger" data-go>${esc(t("remove"))}</button></div>`, (b) => {
    $("[data-go]", b).addEventListener("click", async () => {
      try { await j(`/api/properties/${p.id}`, { method: "DELETE" }); closeSheet(); toast(t("deleted")); if (location.hash === "#/properties") rerender(); else location.hash = "#/properties"; } catch (err) { toast(err.message); }
    });
  });
}
function wireAccount() {
  $("[data-signout]", main)?.addEventListener("click", async () => {
    try { await j("/auth/logout", { method: "POST" }); } catch { /* signed out anyway */ }
    ME = null; if (location.hash === "#/properties") rerender(); else location.hash = "#/properties";
  });
  $("[data-delacct]", main)?.addEventListener("click", () => {
    openSheet(t("delacct_t"), `<p class="mp-confirm">${esc(t("delacct_b"))}</p><div class="mp-row end"><button type="button" class="btn" data-close>${esc(t("cancel"))}</button><button type="button" class="btn danger" data-go>${I.trash}<span>${esc(t("delacct_go"))}</span></button></div>`, (b) => {
      $("[data-go]", b).addEventListener("click", async () => {
        try { await j("/api/account", { method: "DELETE" }); ME = null; closeSheet(); toast(t("acct_deleted")); if (location.hash === "#/properties") rerender(); else location.hash = "#/properties"; } catch (err) { toast(err.message); }
      });
    });
  });
}

// ------------------------------------------------------------------ add / edit sheet --
function factsForm(f = {}, label = "", showLabel = true) {
  const oo = f.owner_occupied;
  return `${showLabel ? `<label class="mp-field"><span>${esc(t("a_label"))}</span><input name="label" maxlength="60" required value="${esc(label)}" placeholder="${esc(t("a_label_ph"))}"></label>` : ""}
    <p class="mp-small">${esc(t("a_facts_lead"))}</p>
    <div class="mp-fgrid">
      <label class="mp-field"><span>${esc(t("year_built"))}<i data-chip="year_built"></i></span><input name="year_built" type="number" inputmode="numeric" min="1700" max="2100" placeholder="1962" value="${f.year_built ?? ""}"></label>
      <label class="mp-field"><span>${esc(t("units"))}<i data-chip="units"></i></span><input name="units" type="number" inputmode="numeric" min="1" max="5000" placeholder="8" value="${f.units ?? ""}"></label>
      <div class="mp-field"><span id="mp-oo">${esc(t("owner_occupied"))}<i data-chip="owner_occupied"></i></span>
        <div class="mp-seg" role="radiogroup" aria-labelledby="mp-oo">${[["yes", true], ["no", false], ["unsure", null]].map(([k, v]) => `<button type="button" role="radio" data-oo="${k}" aria-checked="${oo === v || (v === null && oo == null)}">${esc(t(k))}</button>`).join("")}</div></div>
      <label class="mp-field" data-co ${f.certificate_of_occupancy_date ? "" : "hidden"}><span>${esc(t("certificate_of_occupancy_date"))}<i data-chip="certificate_of_occupancy_date"></i></span><input name="certificate_of_occupancy_date" type="date" value="${esc(f.certificate_of_occupancy_date || "")}"></label>
    </div>
    <div class="mp-preview" aria-live="polite"></div>`;
}
function readFacts(box) {
  const f = {};
  for (const k of ["year_built", "units"]) { const v = $(`[name=${k}]`, box)?.value.trim(); if (v) f[k] = parseInt(v, 10); }
  const co = $("[name=certificate_of_occupancy_date]", box)?.value;
  if (co) f.certificate_of_occupancy_date = co;
  const oo = $("[data-oo][aria-checked=true]", box)?.dataset.oo;
  if (oo === "yes") f.owner_occupied = true; else if (oo === "no") f.owner_occupied = false;
  return f;
}
function wireFacts(box, place) {
  let timer = 0, n = 0;
  const preview = async () => {
    const my = ++n, pv = $(".mp-preview", box);
    if (!pv) return;
    pv.classList.add("stale");
    try {
      const d = await j("/api/evaluate", { method: "POST", body: { address: { state: place.state, jurisdiction: place.jurisdiction }, as_of: asOf(), facts: readFacts(box), lang: lang() } });
      if (my !== n) return;
      const order = ["applies", "unknown", "not_yet_effective"];
      const top = Object.entries(d.fact_counts || {}).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1])[0];
      pv.innerHTML = `<div class="sum-row">${order.filter((r) => d.summary[r]).map((r) => CE.badge(r, `${d.summary[r]} · ${t("r_" + r + "_b")}`)).join("")}</div>
        ${top ? `<p class="mp-hintline">${esc(t("prompt")(t(top[0]), top[1]))}</p>` : d.unknowns ? "" : `<p class="mp-hintline ok">${esc(t("all_clear"))}</p>`}`;
      $$("[data-chip]", box).forEach((el) => { const v = d.fact_counts?.[el.dataset.chip]; el.textContent = v ? `+${v}` : ""; el.title = v ? t("prompt")(t(el.dataset.chip), v) : ""; });
      const co = $("[data-co]", box);
      if (co && d.fact_counts?.certificate_of_occupancy_date) co.hidden = false;
    } catch { if (my === n) pv.innerHTML = ""; }
    pv.classList.remove("stale");
  };
  const schedule = () => { clearTimeout(timer); timer = setTimeout(preview, 300); };
  $$("input", box).forEach((inp) => inp.addEventListener("input", schedule));
  $$("[data-oo]", box).forEach((b) => b.addEventListener("click", () => { $$("[data-oo]", box).forEach((x) => x.setAttribute("aria-checked", x === b)); preview(); }));
  preview();
}
function editSheet(p) {
  openSheet(t("edit_facts"), `<form class="mp-form">${factsForm(p.facts, p.label)}<div class="mp-row end"><button type="button" class="btn" data-close>${esc(t("cancel"))}</button><button class="btn primary" type="submit">${esc(t("save"))}</button></div></form>`, (b) => {
    const f = $("form", b);
    wireFacts(f, { state: p.state, jurisdiction: p.jurisdiction });
    f.addEventListener("submit", async (e) => {
      e.preventDefault();
      try { await j(`/api/properties/${p.id}`, { method: "PATCH", body: { label: $("[name=label]", f).value.trim() || p.label, facts: readFacts(f) } }); closeSheet(); toast(t("updated")); rerender(); } catch (err) { toast(err.message); }
    });
  });
}

// ------------------------------------------------------------------ one building --
function timelineHtml(ch) {
  const ev = ch.events, pend = ch.pending;
  const note = (it) => it.kind === "figure" ? t("fig_note")(fmtDate(it.period_end)) : it.kind === "ends" && it.from === "superseded" ? t("ends_note") : "";
  const item = (it) => `<div class="mp-ev-item"><span class="mp-ev-dot mp-s-${it.kind === "takes_effect" ? "soon" : it.kind === "figure" ? "unk" : "none"}" aria-hidden="true"></span><span class="mp-ev-t">${esc(evLabel([it]))}</span>${note(it) ? `<span class="mp-ev-s">${esc(note(it))}</span>` : ""}</div>`;
  // items that read the same in plain words (two state rules ending together) show once
  const dedupe = (items) => { const seen = new Set(); return items.filter((it) => { const k = evLabel([it]) + note(it); return !seen.has(k) && seen.add(k); }); };
  return `<ul class="group mp-tl">${ev.length ? ev.map((e) => `<li class="mp-ev"><div class="mp-when"><b>${esc(fmtDate(e.date))}</b><span>${esc(relTime(e.date))}</span></div><div class="mp-what">${dedupe(e.items).map(item).join("")}</div></li>`).join("") : `<li class="mp-ev none"><p class="mp-small">${esc(t("nothing_ahead"))}</p></li>`}</ul>
    ${pend.length ? `<div class="mp-pending"><h3>${esc(t("pending_t"))}</h3><p class="mp-small">${esc(t("pending_n"))}</p><ul class="group mp-tl">${pend.map((x) => `<li class="mp-ev"><div class="mp-what"><div class="mp-ev-item"><span class="mp-ev-t">${esc(x.title)}</span></div></div></li>`).join("")}</ul></div>` : ""}`;
}
let CUR = null; // the property shown on its own page
async function paintDetail(id, my) {
  const [p, alerts] = await Promise.all([j(`/api/properties/${id}?as_of=${asOf()}&lang=${lang()}`), j("/api/alerts").catch(() => null)]);
  if (my !== seq) return;
  ALERTS = alerts;
  const v = p.view, f = p.facts, demo = p.demo;
  const top = Object.entries(v.fact_counts || {}).filter(([, n]) => n > 0).sort((a, b) => b[1] - a[1])[0];
  const fv = (k) => (f[k] == null || f[k] === "" ? null : k === "owner_occupied" ? t(f[k] ? "yes" : "no") : k === "certificate_of_occupancy_date" ? fmtDate(f[k]) : String(f[k]));
  const fact = (k) => `<div><dt>${esc(t(k))}</dt><dd class="${fv(k) ? "" : "miss"}">${esc(fv(k) || t("not_given"))}</dd></div>`;
  const meta = [cityOf(p) || p.state, f.year_built ? t("built")(f.year_built) : "", f.units ? t("n_units")(f.units) : ""].filter(Boolean).join(" · ");
  CUR = p;
  paint(`<p class="mp-back"><a href="#/properties">${I.back}${esc(t("back"))}</a></p>
    <article class="mp-detail" data-pid="${p.id}">
      <header class="mp-dhead">
        <div class="mp-dphoto">${img(photo(p), "", false, true)}</div>
        <div class="mp-dtitle"><h1>${esc(p.label)}</h1><p class="mp-addr">${esc(p.address)}</p><p class="mp-dmeta">${esc(meta)}</p>
          <div class="mp-acts"><button type="button" class="btn primary sm" data-check>${esc(t("check"))}</button>${demo ? "" : `<button type="button" class="btn sm" data-edit>${esc(t("edit_facts"))}</button><button type="button" class="icon-btn mp-rm" data-rm aria-label="${esc(t("remove"))}" title="${esc(t("remove"))}">${I.trash}</button>`}</div></div>
      </header>
      <div class="mp-dgrid">
        <div class="mp-dmain">
          ${raiseHtml(p, demo, true)}
          <section class="block" id="changes"><h2>${esc(t("whats_changing"))}</h2>${timelineHtml(p.changes)}</section>
          <section class="answers mp-answers"></section>
        </div>
        <aside class="mp-dside">
          <section class="mp-panel mp-facts"><h2>${esc(t("facts"))}</h2>
            <dl class="kv">${fact("year_built")}${fact("units")}${fact("owner_occupied")}${f.certificate_of_occupancy_date || v.fact_counts?.certificate_of_occupancy_date ? fact("certificate_of_occupancy_date") : ""}</dl>
            ${top ? `<p class="mp-hintline">${esc(t("prompt")(t(top[0]), top[1]))}</p>` : v.unknowns ? "" : `<p class="mp-hintline ok">${esc(t("all_clear"))}</p>`}
            ${v.scope_note ? `<p class="mp-small">${esc(v.scope_note)}</p>` : ""}
          </section>
        </aside>
      </div>
    </article>`, p.label);
  CE.renderAnswers($(".mp-answers", main), v);
  if (/\/changes$/.test(location.hash)) setTimeout(() => $("#changes", main)?.scrollIntoView({ block: "start", behavior: "smooth" }), 60);
}

// ------------------------------------------------------------------ boot --
CE.addRoute("properties", (_main, arg) => { CUR = null; LIST = null; return render(main, arg); });
document.addEventListener("click", (e) => { $$(".mp-menu[open]").forEach((m) => { if (!m.contains(e.target)) m.open = false; }); });
document.addEventListener("ce:lang", navLink);
document.addEventListener("ce:route", (e) => { if (e.detail?.view !== "properties") $("#modal")?.classList.remove("mp-sheet"); });
navLink();
