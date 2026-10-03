// My properties (#38). Self-contained feature module: sign in with Google (or open the read-only example portfolio), save
// buildings with the facts public data lacks, see per building which rules apply today and what is about to change,
// and get every upcoming date in a calendar feed. Routes: #/properties (sign-in or list), #/properties/<id> (detail),
// registered with window.CE.addRoute; answers render with CE.renderAnswers (web/DESIGN.md). Reuses #39: POST
// /api/resolve + /api/evaluate. Backend: web/accounts.py.
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
  nav: "My properties", nav_short: "Mine", kicker: "My properties",
  out_title: "My properties",
  out_lead: "Save the buildings you own, manage or rent. See which rules apply to each one, and get an email before a change takes effect.",
  google: "Sign in with Google", demo: "See an example portfolio",
  fine: "We store your email, your name and the buildings you save. Delete anytime.",
  how1_t: "Your facts fill the gaps", how1: "Year built, units, owner-occupied: what public data lacks turns “unknown” into answers.",
  how2_t: "Every change, dated", how2: "Effective dates, new figures and pending bills, per building.",
  how3_t: "In your calendar", how3: "One private feed for Google, Apple or Outlook calendars.",
  example: "Example",
  n_props: (n) => (n === 1 ? "1 building" : `${n} buildings`), empty_t: "No buildings yet", empty: "Add the first address you own, manage or rent.",
  add: "Add a property", add_demo: "Sign in to add your own",
  apply: "apply", unknown: "unknown", changes: "changes coming", change: "change coming", no_changes: "No dated change ahead",
  state_only: "State law only", city_state: "City + state rules",
  demo_banner: "This is an example portfolio. It can't be changed.", demo_cta: "Sign in to save your own",
  signout: "Sign out", delete_acct: "Delete account", demo_badge: "Example",
  answers_as_of: "Answers as of",
  cal_t: "Calendar feed", cal: "Every upcoming date for your buildings. Updates daily.",
  cal_google: "Google Calendar", cal_apple: "Apple · Outlook", cal_copy: "Copy link", cal_copied: "Calendar link copied",
  cal_private: "Private link: anyone who has it sees your building names and dates.", cal_new: "New link", cal_rotated: "New calendar link. The old one no longer works.",
  mail_t: "Email alerts", mail_digest: "Email me before a law change affects one of my properties", mail_note: (e) => `We email ${e} about 30 days before a change takes effect. Every email has a one-click unsubscribe.`,
  mail_demo: "The example portfolio doesn't send email.", n_apply: (n) => `${n} ${n === 1 ? "rule applies" : "rules apply"}`, n_unknown: (n) => `${n} unknown`, next: "Next", where_facts: "Facts", del_prop: "Delete this property",
  back: "My properties", edit: "Edit facts", del: "Delete", whats_changing: "What’s changing",
  facts: "Building facts", year_built: "Year built", units: "Units", owner_occupied: "Owner lives there", certificate_of_occupancy_date: "Certificate of occupancy",
  yes: "Yes", no: "No", unsure: "Not sure", not_given: "Not given",
  prompt: (f, n) => `Add “${f}” to resolve ${n} unknown answer${n === 1 ? "" : "s"}.`, all_clear: "Every answer is definite for these facts.",
  k_takes_effect: "Takes effect", k_ends: "Ends", k_figure: "New figure due", k_changes: "Changes", k_pending: "Pending bill",
  fig_note: (d) => `The current figure covers the period ending ${d}. The law continues; check the new figure.`,
  pending_t: "Pending bills · not law", pending_n: "Would apply if enacted. Not in force.",
  nothing_ahead: "No dated change is on record for this building.",
  in_cal: "Add these dates to your calendar",
  a_title: "Add a property", a_addr: "Address", a_addr_ph: "Street, city, state", a_find: "Find",
  a_locating: "Finding the legal jurisdiction…", a_label: "Name", a_label_ph: "e.g. Bloomfield brownstone", a_save: "Save property",
  a_facts_lead: "Only what public records can’t tell. Leave blank if unsure.", a_nomatch: "We could not find this address. Add the city and state.",
  a_out: "This address is outside the states we cover (California, New Jersey, Massachusetts).",
  a_store: "Stored: this address, its jurisdiction and these facts. Never tenant names.",
  saved: "Saved", deleted: "Deleted", updated: "Facts updated", save: "Save",
  del_t: (l) => `Delete “${l}”?`, del_b: "The building and its facts are removed from your account.",
  delacct_t: "Delete your account?", delacct_b: "This deletes your account, every saved building, your alert settings and your calendar link. It cannot be undone.",
  delacct_go: "Delete everything", cancel: "Cancel", acct_deleted: "Account deleted",
  signin_failed: "Google sign-in did not complete. Please try again.",
  r_applies: "Applies", r_unknown: "Unknown", r_superseded: "Superseded", r_not_yet_effective: "Not yet in effect", r_pending: "Pending bill", r_failed: "Failed · not law", r_no_rule: "No rule",
  depends_on: "Depends on:", add_fact: "Add", why_source: "Why & source", no_rule: "No rule found for this building.", proposals: "Not law: pending bills and failed proposals",
  effective: "Effective", retrieved: "Retrieved", nla: "Not legal advice.", nla_body: "Public law with citations, for information only. Check the cited source.",
  privacy: "Privacy", terms: "Terms", error: "Something went wrong.", loading: "Loading…",
  cat_rent_increase_limits: "Rent increases", cat_just_cause_eviction: "Eviction protections", cat_security_deposits: "Security deposit",
  cat_application_screening_fees: "Application & move-in fees", cat_screening_restrictions: "Tenant screening", cat_algorithmic_rent_setting: "Algorithmic rent-setting",
};
const ES = {
  nav: "Mis propiedades", nav_short: "Mías", kicker: "Mis propiedades",
  out_title: "Mis propiedades",
  out_lead: "Guarde los edificios que posee, administra o alquila. Vea qué normas aplican a cada uno y reciba un correo antes de que un cambio entre en vigor.",
  google: "Acceder con Google", demo: "Ver una cartera de ejemplo",
  fine: "Guardamos su correo, su nombre y los edificios que guarde. Puede borrarlo todo cuando quiera.",
  how1_t: "Sus datos completan lo que falta", how1: "Año, unidades, si el dueño vive allí: lo que falta en los datos públicos convierte “desconocido” en respuestas.",
  how2_t: "Cada cambio, con fecha", how2: "Fechas de vigencia, nuevas cifras y proyectos de ley, por edificio.",
  how3_t: "En su calendario", how3: "Un enlace privado para Google, Apple u Outlook.",
  example: "Ejemplo",
  n_props: (n) => (n === 1 ? "1 edificio" : `${n} edificios`), empty_t: "Aún no hay edificios", empty: "Agregue la primera dirección que posee, administra o alquila.",
  add: "Agregar propiedad", add_demo: "Acceda para agregar las suyas",
  apply: "aplican", unknown: "desconocidas", changes: "cambios por venir", change: "cambio por venir", no_changes: "Sin cambios con fecha",
  state_only: "Solo ley estatal", city_state: "Normas de ciudad y estado",
  demo_banner: "Esta es una cartera de ejemplo. No se puede modificar.", demo_cta: "Acceda para guardar las suyas",
  signout: "Cerrar sesión", delete_acct: "Eliminar cuenta", demo_badge: "Ejemplo",
  answers_as_of: "Respuestas al",
  cal_t: "Calendario", cal: "Cada fecha próxima de sus edificios. Se actualiza a diario.",
  cal_google: "Google Calendar", cal_apple: "Apple · Outlook", cal_copy: "Copiar enlace", cal_copied: "Enlace copiado",
  cal_private: "Enlace privado: quien lo tenga ve los nombres de sus edificios y las fechas.", cal_new: "Nuevo enlace", cal_rotated: "Nuevo enlace. El anterior ya no funciona.",
  mail_t: "Alertas por correo", mail_digest: "Avisarme por correo antes de que un cambio legal afecte a una de mis propiedades", mail_note: (e) => `Escribimos a ${e} unos 30 días antes de que un cambio entre en vigor. Cada correo permite darse de baja con un clic.`,
  mail_demo: "La cartera de ejemplo no envía correos.", n_apply: (n) => `${n} ${n === 1 ? "norma aplica" : "normas aplican"}`, n_unknown: (n) => `${n} ${n === 1 ? "desconocida" : "desconocidas"}`, next: "Próximo", where_facts: "Datos", del_prop: "Eliminar esta propiedad",
  back: "Mis propiedades", edit: "Editar datos", del: "Eliminar", whats_changing: "Qué va a cambiar",
  facts: "Datos del edificio", year_built: "Año de construcción", units: "Unidades", owner_occupied: "El dueño vive allí", certificate_of_occupancy_date: "Certificado de ocupación",
  yes: "Sí", no: "No", unsure: "No sé", not_given: "Sin dato",
  prompt: (f, n) => `Indique “${f}” para resolver ${n} respuesta${n === 1 ? "" : "s"} desconocida${n === 1 ? "" : "s"}.`, all_clear: "Todas las respuestas son definitivas con estos datos.",
  k_takes_effect: "Entra en vigor", k_ends: "Termina", k_figure: "Nueva cifra", k_changes: "Cambia", k_pending: "Proyecto de ley",
  fig_note: (d) => `La cifra actual cubre el período hasta ${d}. La ley sigue; verifique la nueva cifra.`,
  pending_t: "Proyectos de ley · no son ley", pending_n: "Aplicarían si se aprueban. No están vigentes.",
  nothing_ahead: "No hay cambios con fecha para este edificio.",
  in_cal: "Agregar estas fechas a su calendario",
  a_title: "Agregar propiedad", a_addr: "Dirección", a_addr_ph: "Calle, ciudad, estado", a_find: "Buscar",
  a_locating: "Buscando la jurisdicción legal…", a_label: "Nombre", a_label_ph: "p. ej. Casa Bloomfield", a_save: "Guardar propiedad",
  a_facts_lead: "Solo lo que los registros públicos no dicen. Déjelo vacío si no sabe.", a_nomatch: "No encontramos esta dirección. Agregue ciudad y estado.",
  a_out: "Esta dirección está fuera de los estados que cubrimos (California, Nueva Jersey, Massachusetts).",
  a_store: "Se guarda: la dirección, su jurisdicción y estos datos. Nunca nombres de inquilinos.",
  saved: "Guardado", deleted: "Eliminado", updated: "Datos actualizados", save: "Guardar",
  del_t: (l) => `¿Eliminar “${l}”?`, del_b: "El edificio y sus datos se eliminan de su cuenta.",
  delacct_t: "¿Eliminar su cuenta?", delacct_b: "Se eliminan su cuenta, todos los edificios, sus alertas y su enlace de calendario. No se puede deshacer.",
  delacct_go: "Eliminar todo", cancel: "Cancelar", acct_deleted: "Cuenta eliminada",
  signin_failed: "El acceso con Google no se completó. Inténtelo de nuevo.",
  r_applies: "Aplica", r_unknown: "Desconocido", r_superseded: "Reemplazada", r_not_yet_effective: "Aún no vigente", r_pending: "Proyecto de ley", r_failed: "Fallida · no es ley", r_no_rule: "Sin norma",
  depends_on: "Depende de:", add_fact: "Agregar", why_source: "Por qué y fuente", no_rule: "No se encontró ninguna norma para este edificio.", proposals: "No es ley: proyectos pendientes y propuestas fallidas",
  effective: "Vigente desde", retrieved: "Consultado", nla: "No es asesoría legal.", nla_body: "Leyes públicas con citas, solo informativo. Verifique la fuente citada.",
  privacy: "Privacidad", terms: "Términos", error: "Algo salió mal.", loading: "Cargando…",
  cat_rent_increase_limits: "Aumentos de renta", cat_just_cause_eviction: "Protección contra desalojo", cat_security_deposits: "Depósito de garantía",
  cat_application_screening_fees: "Cargos de solicitud y mudanza", cat_screening_restrictions: "Selección de inquilinos", cat_algorithmic_rent_setting: "Renta fijada por algoritmos",
};
const t = (k) => (lang() === "es" && ES[k]) || EN[k] || k;
const fmtDate = (d, opts = { month: "short", day: "numeric", year: "numeric" }) => {
  const x = new Date(String(d).slice(0, 10) + "T12:00:00");
  return isNaN(x) ? d || "" : x.toLocaleDateString(lang() === "es" ? "es-US" : "en-US", opts);
};
const relTime = (d) => {
  const days = Math.round((new Date(d + "T12:00:00") - new Date(asOf() + "T12:00:00")) / 864e5);
  const rtf = new Intl.RelativeTimeFormat(lang(), { numeric: "auto" });
  if (Math.abs(days) < 45) return rtf.format(days, "day");
  if (Math.abs(days) < 640) return rtf.format(Math.round(days / 30.4), "month");
  return rtf.format(Math.round(days / 365.25), "year");
};

// ------------------------------------------------------------------ icons --
const svg = (p) => `<svg class="ico" viewBox="0 0 24 24" aria-hidden="true">${p}</svg>`;
const I = {
  back: svg('<path d="M19 12H5M11 6l-6 6 6 6"/>'),
  arrow: svg('<path d="M5 12h14M13 6l6 6-6 6"/>'),
  plus: svg('<path d="M12 5v14M5 12h14"/>'),
  cal: svg('<rect x="4" y="5" width="16" height="15" rx="3"/><path d="M8 3v4M16 3v4M4 10h16"/>'),
  mail: svg('<rect x="3" y="5" width="18" height="14" rx="3"/><path d="m4 7 8 6 8-6"/>'),
  building: svg('<path d="M4 21V5l8-2v18M12 8l8 2v11M8 8v.01M8 12v.01M8 16v.01M16 13v.01M16 17v.01M2 21h20"/>'),
  key: svg('<circle cx="8" cy="15" r="4"/><path d="m11 12 9-9M17 6l3 3M15 8l2 2"/>'),
  user: svg('<circle cx="12" cy="8" r="4"/><path d="M4 21c1-4.4 4.2-7 8-7s7 2.6 8 7"/>'),
  q: svg('<circle cx="12" cy="12" r="9.5"/><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1 .9-1 1.7M12 17v.01"/>'),
  check: svg('<path d="m5 12 4.5 4.5L19 7"/>'),
  chev: svg('<path d="m9 6 6 6-6 6"/>'),
  copy: svg('<rect x="8" y="8" width="12" height="12" rx="3"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>'),
  ext: svg('<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>'),
  trash: svg('<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>'),
  pen: svg('<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="m13.5 6.5 4 4"/>'),
  alert: svg('<path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17.5v.01"/>'),
  info: svg('<circle cx="12" cy="12" r="9.5"/><path d="M12 11v6M12 7.5v.01"/>'),
  cat: {
    rent_increase_limits: svg('<path d="M3 17l6-6 4 4 8-8"/><path d="M14 7h7v7"/>'),
    just_cause_eviction: svg('<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="m9 12 2 2 4-4"/>'),
    security_deposits: svg('<rect x="3" y="6" width="18" height="13" rx="2"/><path d="M3 10h18M16 15h2"/>'),
    application_screening_fees: svg('<path d="M6 3h12v18l-3-2-3 2-3-2-3 2z"/><path d="M9 8h6M9 12h6"/>'),
    screening_restrictions: svg('<circle cx="10" cy="8" r="4"/><path d="M3 20c.8-3.7 3.6-6 7-6"/><circle cx="17" cy="16" r="3"/><path d="m21 20-1.8-1.8"/>'),
    algorithmic_rent_setting: svg('<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>'),
  },
};
const G_LOGO = `<svg viewBox="0 0 48 48" aria-hidden="true"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>`;
const gsiButton = () => `<a class="gsi" href="/auth/google/login?next=${encodeURIComponent("/#/properties")}">${G_LOGO}<span>${esc(t("google"))}</span></a>`;
const badge = (r, label, i = null) => `<span class="badge ${esc(r)}${i != null ? " anim" : ""}"${i != null ? ` style="--i:${i}"` : ""}>${esc(label ?? t("r_" + r))}</span>`;
const KIND_BADGE = { takes_effect: "not_yet_effective", ends: "superseded", figure: "in_force", changes: "superseded", pending: "pending" };
const where = (p) => p.jurisdiction || `${p.place ? p.place + ", " : ""}${p.state}`;

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
const rerender = () => render(main, (location.hash.match(/^#\/properties\/([^/?]+)/) || [])[1]);
function openSheet(title, body, after) {
  CE.openModal(title, body);
  const m = $("#modal");
  m.classList.add("mp-sheet");
  after?.($(".modal-body", m));
}
const closeSheet = () => $("#modal [data-close]")?.click();
const skeleton = () => {
  const line = (w, h, m = 12) => `<div class="sk" style="width:${w};height:${h}px;margin-top:${m}px"></div>`;
  return `<div class="mp-skel">${line("40%", 32, 0)}${line("60%", 16)}${line("100%", 220, 32)}</div>`;
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
    if (!ME.signed_in) return paintSignedOut();
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

// ------------------------------------------------------------------ signed out --
function paintSignedOut() {
  paint(`<header class="page-head"><h1>${esc(t("out_title"))}</h1><p>${esc(t("out_lead"))}</p></header>
    <div class="mp-cta">${ME?.google ? gsiButton() : ""}<button type="button" class="btn mp-demo">${esc(t("demo"))}</button></div>
    <p class="mp-small">${esc(t("fine"))} <a href="/privacy">${esc(t("privacy"))}</a> · <a href="/terms">${esc(t("terms"))}</a></p>
    <section class="features">${["how1", "how2", "how3"].map((k) => `<div><h2>${esc(t(k + "_t"))}</h2><p>${esc(t(k))}</p></div>`).join("")}</section>`, t("nav"));
  $(".mp-demo", main).addEventListener("click", async (e) => {
    const b = e.currentTarget; b.disabled = true;
    try { await j("/auth/demo", { method: "POST" }); rerender(); } catch (err) { b.disabled = false; toast(err.message); }
  });
}

// ------------------------------------------------------------------ list --
function accountBar(demo) {
  const u = ME.user;
  return `<details class="mp-menu"><summary class="tool" aria-label="${esc(u.email)}"><span class="mp-email">${esc(demo ? t("demo_badge") : u.email)}</span><span class="chev">${I.chev}</span></summary>
      <div class="mp-pop">
        <button type="button" data-signout>${esc(t("signout"))}</button>
        ${demo ? "" : `<button type="button" class="danger" data-delacct>${esc(t("delete_acct"))}</button>`}
        <a href="/privacy">${esc(t("privacy"))}</a>
      </div></details>`;
}
function row(p) {
  const s = p.summary, c = s.counts || {};
  const facts = [t("n_apply")(c.applies || 0), c.unknown ? t("n_unknown")(c.unknown) : ""].filter(Boolean).join(" · ");
  return `<li><a class="mp-row-a" href="#/properties/${p.id}">
    <span class="mp-row-main"><span class="mp-row-t">${esc(p.label)}</span><span class="mp-row-s">${esc(p.address)}</span>
      <span class="mp-row-s">${esc(facts)}</span>
      ${s.next ? `<span class="mp-row-n">${esc(t("next"))}: ${esc(fmtDate(s.next.date))} · ${esc(s.next.title)}</span>` : ""}</span>
    <span class="chev">${I.chev}</span></a></li>`;
}
async function paintList(my) {
  const [list, alerts] = await Promise.all([j(`/api/properties?as_of=${asOf()}`), j("/api/alerts")]);
  if (my !== seq) return;
  const demo = list.demo, props = list.properties;
  const add = demo
    ? (ME.google ? `<li><a class="mp-row-a mp-add" href="/auth/google/login?next=${encodeURIComponent("/#/properties")}">${esc(t("add_demo"))}</a></li>` : "")
    : `<li><button type="button" class="mp-row-a mp-add" data-add>${esc(t("add"))}</button></li>`;
  const cal = alerts.calendar;
  paint(`<header class="mp-head">
      <div class="page-head"><h1>${esc(props.length ? t("n_props")(props.length) : t("empty_t"))}</h1><p>${esc(t("answers_as_of"))} ${esc(fmtDate(list.as_of))}</p></div>
      ${accountBar(demo)}
    </header>
    ${demo ? `<p class="mp-banner">${esc(t("demo_banner"))}${ME.google ? ` <a href="/auth/google/login?next=${encodeURIComponent("/#/properties")}">${esc(t("demo_cta"))}</a>` : ""}</p>` : ""}
    ${props.length ? "" : `<p class="mp-empty">${esc(t("empty"))}</p>`}
    <ul class="group mp-list">${props.map(row).join("")}${add}</ul>
    <section class="block mp-alerts">
      <h2>${esc(t("cal_t"))}</h2>
      <p class="block-lead">${esc(t("cal"))}</p>
      <div class="mp-btns">
        <a class="btn" href="${esc(cal.google)}" target="_blank" rel="noopener">${esc(t("cal_google"))}</a>
        <a class="btn" href="${esc(cal.webcal)}">${esc(t("cal_apple"))}</a>
        <button type="button" class="btn" data-copy="${esc(cal.url)}">${esc(t("cal_copy"))}</button>
      </div>
      <p class="mp-small">${esc(t("cal_private"))}${demo ? "" : ` <button type="button" class="linkish" data-rotate>${esc(t("cal_new"))}</button>`}</p>
    </section>
    <section class="block mp-alerts">
      <h2>${esc(t("mail_t"))}</h2>
      <label class="mp-switch"><span>${esc(t("mail_digest"))}</span><input type="checkbox" role="switch" data-digest ${alerts.email_digest ? "checked" : ""} ${demo ? "disabled" : ""}><span class="mp-knob" aria-hidden="true"></span></label>
      <p class="mp-small">${esc(demo ? t("mail_demo") : t("mail_note")(alerts.email))}</p>
    </section>`, t("nav"));
  wireAccount();
  $("[data-add]", main)?.addEventListener("click", () => addSheet());
  $("[data-copy]", main)?.addEventListener("click", async (e) => {
    try { await navigator.clipboard.writeText(e.currentTarget.dataset.copy); toast(t("cal_copied")); } catch { prompt("Calendar link", e.currentTarget.dataset.copy); }
  });
  $("[data-rotate]", main)?.addEventListener("click", async () => {
    try { await j("/api/alerts/calendar/rotate", { method: "POST" }); toast(t("cal_rotated")); rerender(); } catch (err) { toast(err.message); }
  });
  $("[data-digest]", main)?.addEventListener("change", async (e) => {
    try { await j("/api/alerts", { method: "PUT", body: { email_digest: e.target.checked } }); toast(t("saved")); } catch (err) { e.target.checked = !e.target.checked; toast(err.message); }
  });
}
function wireAccount() {
  $("[data-signout]", main)?.addEventListener("click", async () => {
    try { await j("/auth/logout", { method: "POST" }); } catch { /* signed out anyway */ }
    ME = null; if (location.hash === "#/properties") rerender(); else location.hash = "#/properties";
  });
  $("[data-delacct]", main)?.addEventListener("click", () => {
    openSheet(t("delacct_t"), `<p class="mp-confirm">${esc(t("delacct_b"))}</p><div class="mp-row end"><button type="button" class="pill line" data-close>${esc(t("cancel"))}</button><button type="button" class="pill danger" data-go>${I.trash}<span>${esc(t("delacct_go"))}</span></button></div>`, (b) => {
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
      const order = ["applies", "unknown", "superseded", "not_yet_effective", "pending"];
      const top = Object.entries(d.fact_counts || {}).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1])[0];
      pv.innerHTML = `<div class="sum-row">${order.filter((r) => d.summary[r]).map((r, i) => badge(r, `${d.summary[r]} · ${t("r_" + r)}`, i)).join("")}</div>
        ${top ? `<p class="mp-hintline">${I.q}<span>${esc(t("prompt")(t(top[0]), top[1]))}</span></p>` : d.unknowns ? "" : `<p class="mp-hintline ok">${I.check}<span>${esc(t("all_clear"))}</span></p>`}`;
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
function addSheet() {
  openSheet(t("a_title"), `<form class="mp-form" data-step="addr" novalidate>
      <label class="mp-field"><span>${esc(t("a_addr"))}</span>
        <div class="mp-inline"><input name="address" autocomplete="street-address" minlength="5" maxlength="200" required placeholder="${esc(t("a_addr_ph"))}"><button class="pill primary" type="submit">${esc(t("a_find"))}</button></div></label>
      <div class="mp-resolve" aria-live="polite"></div>
    </form>
    <form class="mp-form" data-step="facts" hidden></form>`, (b) => {
    const fa = $("[data-step=addr]", b), ff = $("[data-step=facts]", b), out = $(".mp-resolve", b);
    setTimeout(() => $("[name=address]", fa).focus(), 60);
    let place = null, typed = "";
    fa.addEventListener("submit", async (e) => {
      e.preventDefault();
      typed = $("[name=address]", fa).value.trim();
      if (typed.length < 5) return;
      out.innerHTML = `<p class="mp-small mp-wait">${esc(t("a_locating"))}</p>`;
      ff.hidden = true;
      try {
        const r = await j("/api/resolve", { method: "POST", body: { address: typed } });
        if (!r.match) { out.innerHTML = `<p class="mp-msg warn">${I.alert}<span>${esc(t("a_nomatch"))}</span></p>`; return; }
        if (!r.in_scope) { out.innerHTML = `<p class="mp-msg warn">${I.alert}<span>${esc(t("a_out"))}</span></p>`; return; }
        place = r;
        out.innerHTML = `<div class="mp-found">${I.check}<div><b>${esc(r.matched_address || typed)}</b>
          <div class="mp-stack">${r.stack.map((s) => `<span class="${s.covered ? "on" : ""}">${esc(s.name)}</span>`).join("<i>›</i>")}</div>
          <span class="mp-small">${esc(r.jurisdiction ? t("city_state") : t("state_only"))}</span></div></div>`;
        const street = (r.matched_address || typed).split(",")[0];
        ff.innerHTML = factsForm({}, street.replace(/\b\w+/g, (w) => w[0] + w.slice(1).toLowerCase())) + `<p class="mp-small">${esc(t("a_store"))}</p><div class="mp-row end"><button class="pill primary" type="submit">${esc(t("a_save"))}</button></div>`;
        ff.hidden = false;
        wireFacts(ff, place);
      } catch (err) { out.innerHTML = `<p class="mp-msg warn">${I.alert}<span>${esc(err.message)}</span></p>`; }
    });
    ff.addEventListener("submit", async (e) => {
      e.preventDefault();
      const btn = $("[type=submit]", ff); btn.disabled = true;
      try {
        const p = await j("/api/properties", { method: "POST", body: { label: $("[name=label]", ff).value.trim() || typed, address: typed, place: { state: place.state, jurisdiction: place.jurisdiction, place: place.place, county: place.county, matched_address: place.matched_address }, facts: readFacts(ff) } });
        closeSheet(); toast(t("saved")); location.hash = `#/properties/${p.id}`;
      } catch (err) { btn.disabled = false; toast(err.message); }
    });
  });
}
function editSheet(p) {
  openSheet(t("edit"), `<form class="mp-form">${factsForm(p.facts, p.label)}<div class="mp-row end"><button type="button" class="pill line" data-close>${esc(t("cancel"))}</button><button class="pill primary" type="submit">${esc(t("save"))}</button></div></form>`, (b) => {
    const f = $("form", b);
    wireFacts(f, { state: p.state, jurisdiction: p.jurisdiction });
    f.addEventListener("submit", async (e) => {
      e.preventDefault();
      try { await j(`/api/properties/${p.id}`, { method: "PATCH", body: { label: $("[name=label]", f).value.trim() || p.label, facts: readFacts(f) } }); closeSheet(); toast(t("updated")); rerender(); } catch (err) { toast(err.message); }
    });
  });
}

// ------------------------------------------------------------------ detail --
function timelineHtml(ch, cal) {
  const ev = ch.events, pend = ch.pending;
  const item = (it) => {
    const label = t("k_" + it.kind);
    const sub = it.kind === "figure" ? t("fig_note")(fmtDate(it.period_end)) : it.kind === "changes" ? `${t("r_" + it.from)} → ${t("r_" + it.to)}` : it.key_value || "";
    return `<div class="mp-ev-item"><span class="mp-ev-t">${esc(it.title)}</span>${CE.badge(KIND_BADGE[it.kind] || "superseded", label)}
      <span class="mp-ev-s">${esc([it.citation, String(it.jurisdiction || "").replace(/, ..$/, "")].filter(Boolean).join(" · "))}</span>${sub ? `<span class="mp-ev-s">${esc(sub)}</span>` : ""}</div>`;
  };
  return `<ul class="group mp-tl">${ev.length ? ev.map((e) => `<li class="mp-ev"><div class="mp-when"><b>${esc(fmtDate(e.date))}</b><span>${esc(relTime(e.date))}</span></div><div class="mp-what">${e.items.map(item).join("")}</div></li>`).join("") : `<li class="mp-ev none"><p class="mp-small">${esc(t("nothing_ahead"))}</p></li>`}</ul>
    ${pend.length ? `<div class="mp-pending"><h3>${esc(t("pending_t"))}</h3><p class="mp-small">${esc(t("pending_n"))}</p><ul class="group mp-tl">${pend.map((x) => `<li class="mp-ev"><div class="mp-what">${item(x)}</div></li>`).join("")}</ul></div>` : ""}
    ${ev.length && cal ? `<p class="mp-calink"><a href="${esc(cal.google)}" target="_blank" rel="noopener">${esc(t("in_cal"))}</a></p>` : ""}`;
}
let CUR = null; // the property shown in the detail view
async function paintDetail(id, my) {
  const [p, alerts] = await Promise.all([j(`/api/properties/${id}?as_of=${asOf()}&lang=${lang()}`), j("/api/alerts").catch(() => null)]);
  if (my !== seq) return;
  const v = p.view, f = p.facts, demo = p.demo;
  const top = Object.entries(v.fact_counts || {}).filter(([, n]) => n > 0).sort((a, b) => b[1] - a[1])[0];
  const fv = (k) => (f[k] == null || f[k] === "" ? null : k === "owner_occupied" ? t(f[k] ? "yes" : "no") : k === "certificate_of_occupancy_date" ? fmtDate(f[k]) : String(f[k]));
  const fact = (k) => `<div><dt>${esc(t(k))}</dt><dd class="${fv(k) ? "" : "miss"}">${esc(fv(k) || t("not_given"))}</dd></div>`;
  const c = v.summary || {};
  paint(`<p class="mp-back"><a href="#/properties">${I.back}${esc(t("back"))}</a></p>
    <article class="addr mp-detail">
      <header class="addr-head">
        <h1>${esc(p.label)}</h1>
        <p class="addr-sub">${esc(p.address)}</p>
        <p class="addr-meta">${esc(where(p))} · ${esc([t("n_apply")(c.applies || 0), c.unknown ? t("n_unknown")(c.unknown) : ""].filter(Boolean).join(" · "))}</p>
      </header>
      <section class="block mp-facts"><h2>${esc(t("facts"))}</h2>
        <dl class="kv">${fact("year_built")}${fact("units")}${fact("owner_occupied")}${f.certificate_of_occupancy_date || v.fact_counts?.certificate_of_occupancy_date ? fact("certificate_of_occupancy_date") : ""}</dl>
        ${top ? `<p class="mp-hintline">${esc(t("prompt")(t(top[0]), top[1]))}</p>` : v.unknowns ? "" : `<p class="mp-hintline ok">${esc(t("all_clear"))}</p>`}
        ${v.scope_note ? `<p class="mp-small">${esc(v.scope_note)}</p>` : ""}
        ${demo ? "" : `<p class="mp-btns"><button type="button" class="btn" data-edit>${esc(t("edit"))}</button></p>`}
      </section>
      <section class="block"><h2>${esc(t("whats_changing"))}</h2>${timelineHtml(p.changes, alerts?.calendar)}</section>
      <section class="answers mp-answers"></section>
      ${demo ? "" : `<p class="mp-del"><button type="button" class="linkish danger-t" data-del>${esc(t("del_prop"))}</button></p>`}
    </article>`, p.label);
  CE.renderAnswers($(".mp-answers", main), v);
  CUR = p;
  $("[data-del]", main)?.addEventListener("click", () => {
    openSheet(t("del_t")(p.label), `<p class="mp-confirm">${esc(t("del_b"))}</p><div class="mp-row end"><button type="button" class="btn" data-close>${esc(t("cancel"))}</button><button type="button" class="btn danger" data-go>${esc(t("del"))}</button></div>`, (b) => {
      $("[data-go]", b).addEventListener("click", async () => {
        try { await j(`/api/properties/${p.id}`, { method: "DELETE" }); closeSheet(); toast(t("deleted")); location.hash = "#/properties"; } catch (err) { toast(err.message); }
      });
    });
  });
}

// ------------------------------------------------------------------ boot --
let CUR_HASH = "";
CE.addRoute("properties", (_main, arg) => { CUR = null; CUR_HASH = location.hash; return render(main, arg); });
main.addEventListener("click", (e) => { if (CUR && location.hash === CUR_HASH && e.target.closest(".mp-root [data-edit]")) editSheet(CUR); });
document.addEventListener("click", (e) => { $$(".mp-menu[open]").forEach((m) => { if (!m.contains(e.target)) m.open = false; }); });
document.addEventListener("ce:lang", navLink);
document.addEventListener("ce:route", (e) => { if (e.detail?.view !== "properties") $("#modal")?.classList.remove("mp-sheet"); });
navLink();
