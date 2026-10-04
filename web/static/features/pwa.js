// Clause & Effect · installable app (#44): service worker, install button + tutorial, offline banner, update toast.
// Self-contained: only reads the DOM app.js renders (#main, .nav-tools, .footer-links, #toasts, <html lang>).
//
// For Google sign-in (#38): window.CE_PWA.isStandalone() is true inside the installed app. Popups are unreliable
// there (iOS opens them in a separate browser context), so use the redirect flow (GIS ux_mode: "redirect" or a
// server /auth/... redirect). sw.js never intercepts /auth/*, /login, /logout, /oauth* or per-user /api/* routes.

const $ = (s, el = document) => el.querySelector(s);
const RM = matchMedia("(prefers-reduced-motion: reduce)");
const ICON = "/static/icons/icon-192.png";
const KEY = "ce.pwa";

// ------------------------------------------------------------------ state --
const st = (() => { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch { return {}; } })();
const save = (patch) => { Object.assign(st, patch); try { localStorage.setItem(KEY, JSON.stringify(st)); } catch { /* private mode */ } };
const isStandalone = () => matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;

// ------------------------------------------------------------------ platform --
const ua = navigator.userAgent;
const isIOS = /iP(hone|od|ad)/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1);
const isAndroid = /Android/.test(ua);
const inApp = /FBAN|FBAV|Instagram|Line\/|LinkedInApp|Twitter|TikTok|Snapchat|GSA\//.test(ua);
const isMacSafari = !isIOS && /Macintosh/.test(ua) && /Version\/[\d.]+.*Safari/.test(ua);
const isFirefoxDesktop = /Firefox\//.test(ua) && !isAndroid && !isIOS;
const flowName = () => (inApp ? "inapp" : isIOS ? "ios" : isAndroid ? "android" : isMacSafari ? "macsafari" : "desktop");
let deferred = null; // beforeinstallprompt event (Chromium)
// installed once (st.installed) hides the entry points, unless the browser offers the install again (uninstalled)
const canInstall = () => !isStandalone() && (!!deferred || (!isFirefoxDesktop && !st.installed));

// ------------------------------------------------------------------ i18n --
const T = {
  en: {
    install: "Install app", install_short: "Install", install_footer: "Install the app", offline_ok: "works offline",
    sub: "No app store · works offline · free",
    nudge_t: "Keep it one tap away", nudge_s: "Install the app · works offline", not_now: "Not now",
    next: "Next", back: "Back", done: "Got it", close: "Close", copy: "Copy link", copied: "Link copied",
    ios_share: "Tap Share", ios_share_hint: "No Share button? Tap ••• first.",
    ios_add: "Tap “Add to Home Screen”", ios_add_hint: "Scroll down if you don't see it.",
    ios_confirm: "Tap Add", ios_confirm_hint: "The § icon lands on your home screen.",
    and_menu: "Tap ⋮", and_menu_hint: "Top right in Chrome.",
    and_install: "Tap “Install app”", and_install_hint: "Or “Add to Home screen”.",
    and_confirm: "Tap Install", and_confirm_hint: "Done: open it from your home screen.",
    dt_icon: "Click the install icon", dt_icon_hint: "Right side of the address bar.",
    dt_confirm: "Click Install", dt_confirm_hint: "It opens in its own window.",
    mac_share: "Click Share", mac_share_hint: "Or File in the menu bar.",
    mac_dock: "Choose “Add to Dock”", mac_dock_hint: "Then click Add.",
    inapp_open: "Open in your browser", inapp_open_hint: "Tap ••• then “Open in browser”.",
    inapp_again: "Tap Install there", inapp_again_hint: "Safari or Chrome can install apps.",
    installed: "Installed!", installed_s: "Open Clause & Effect from your home screen.",
    welcome: "Installed! Welcome to the app", update: "New version available", refresh: "Refresh",
    offline: "Offline · saved pages only", offline_saved: "Offline · saved answer from {d}", online: "Back online",
    add_hs: "Add to Home Screen", copy_row: "Copy", fav_row: "Add to Favorites", read_row: "Add to Reading List",
    cancel: "Cancel", add: "Add", install_btn: "Install", open_browser: "Open in browser", add_dock: "Add to Dock",
    newtab: "New tab", bookmarks: "Bookmarks", share_row: "Share…",
  },
  es: {
    install: "Instalar app", install_short: "Instalar", install_footer: "Instalar la app", offline_ok: "funciona sin conexión",
    sub: "Sin tienda de apps · funciona sin conexión · gratis",
    nudge_t: "Tenla a un toque", nudge_s: "Instala la app · funciona sin conexión", not_now: "Ahora no",
    next: "Siguiente", back: "Atrás", done: "Entendido", close: "Cerrar", copy: "Copiar enlace", copied: "Enlace copiado",
    ios_share: "Toca Compartir", ios_share_hint: "¿No ves Compartir? Toca ••• primero.",
    ios_add: "Toca “Agregar a inicio”", ios_add_hint: "Desliza hacia abajo si no aparece.",
    ios_confirm: "Toca Agregar", ios_confirm_hint: "El icono § aparece en tu pantalla de inicio.",
    and_menu: "Toca ⋮", and_menu_hint: "Arriba a la derecha en Chrome.",
    and_install: "Toca “Instalar app”", and_install_hint: "O “Agregar a la pantalla principal”.",
    and_confirm: "Toca Instalar", and_confirm_hint: "Listo: ábrela desde tu pantalla de inicio.",
    dt_icon: "Haz clic en el icono de instalar", dt_icon_hint: "A la derecha de la barra de direcciones.",
    dt_confirm: "Haz clic en Instalar", dt_confirm_hint: "Se abre en su propia ventana.",
    mac_share: "Haz clic en Compartir", mac_share_hint: "O en Archivo, en la barra de menús.",
    mac_dock: "Elige “Agregar al Dock”", mac_dock_hint: "Luego haz clic en Agregar.",
    inapp_open: "Ábrela en tu navegador", inapp_open_hint: "Toca ••• y “Abrir en el navegador”.",
    inapp_again: "Toca Instalar allí", inapp_again_hint: "Safari o Chrome pueden instalar apps.",
    installed: "¡Instalada!", installed_s: "Abre Clause & Effect desde tu pantalla de inicio.",
    welcome: "¡Instalada! Bienvenido a la app", update: "Nueva versión disponible", refresh: "Actualizar",
    offline: "Sin conexión · solo páginas guardadas", offline_saved: "Sin conexión · respuesta guardada el {d}", online: "Conexión restablecida",
    add_hs: "Agregar a inicio", copy_row: "Copiar", fav_row: "Agregar a favoritos", read_row: "Agregar a la lista de lectura",
    cancel: "Cancelar", add: "Agregar", install_btn: "Instalar", open_browser: "Abrir en el navegador", add_dock: "Agregar al Dock",
    newtab: "Nueva pestaña", bookmarks: "Favoritos", share_row: "Compartir…",
  },
};
const lang = () => (document.documentElement.lang === "es" ? "es" : "en");
const t = (k) => T[lang()][k] ?? T.en[k] ?? k;
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// ------------------------------------------------------------------ icons --
const svg = (p, cls = "ico") => `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${p}</svg>`;
const I = {
  device: svg('<rect x="6.5" y="2.5" width="11" height="19" rx="2.8"/><path d="M12 7v7.2M9.3 11.6 12 14.3l2.7-2.7"/>'),
  share: svg('<path d="M8.5 9H7a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-8a2 2 0 0 0-2-2h-1.5"/><path d="M12 2.8v11M8.6 6.2 12 2.8l3.4 3.4"/>'),
  plusbox: svg('<rect x="4" y="4" width="16" height="16" rx="4.5"/><path d="M12 8.5v7M8.5 12h7"/>'),
  copy: svg('<rect x="8" y="8" width="12" height="12" rx="3"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>'),
  star: svg('<path d="m12 3.5 2.6 5.3 5.8.8-4.2 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8-4.2-4.1 5.8-.8z"/>'),
  glasses: svg('<circle cx="6.5" cy="14" r="3.5"/><circle cx="17.5" cy="14" r="3.5"/><path d="M10 14h4M3 13l2-6M21 13l-2-6"/>'),
  book: svg('<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5z"/><path d="M4 20.5A2.5 2.5 0 0 0 6.5 23H20"/>'),
  tabs: svg('<rect x="4" y="7" width="13" height="13" rx="3"/><path d="M8 4h9a3 3 0 0 1 3 3v9"/>'),
  left: svg('<path d="m15 6-6 6 6 6"/>'), right: svg('<path d="m9 6 6 6-6 6"/>'),
  dots: svg('<circle cx="5" cy="12" r="1.2"/><circle cx="12" cy="12" r="1.2"/><circle cx="19" cy="12" r="1.2"/>'),
  kebab: svg('<circle cx="12" cy="5" r="1.2"/><circle cx="12" cy="12" r="1.2"/><circle cx="12" cy="19" r="1.2"/>'),
  monitor: svg('<rect x="3" y="4" width="18" height="12" rx="2.5"/><path d="M8 20h8M12 7v6M9.5 10.5 12 13l2.5-2.5"/>'),
  close: svg('<path d="M6 6l12 12M18 6 6 18"/>'),
  check: svg('<path d="m5 12 4.5 4.5L19 7"/>'),
  lock: svg('<rect x="5" y="11" width="14" height="10" rx="2.5"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>'),
  refresh: svg('<path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 4v7h-7"/>'),
  wifi: svg('<path d="M2 8.5a15 15 0 0 1 20 0M5.5 12.2a10 10 0 0 1 13 0M9 15.8a5 5 0 0 1 6 0M12 19.5v.01"/>'),
  globe: svg('<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18"/>'),
  dock: svg('<rect x="3" y="15" width="18" height="5" rx="2"/><rect x="6" y="11" width="4" height="4" rx="1"/><rect x="14" y="11" width="4" height="4" rx="1"/>'),
};
const appIco = (cls = "") => `<img class="pwa-app ${cls}" src="${ICON}" alt="" width="40" height="40">`;
const tap = '<i class="pwa-tap" aria-hidden="true"></i>';

// ------------------------------------------------------------------ tutorial visuals --
// Each art is a stylised, label-free mock of the real browser UI, with a pulsing tap target.
const host = location.host;
const ART = {
  ios_share: () => `<div class="pm pm-phone">
      <div class="pm-page">${appIco("ghost")}<div class="pm-lines"><i></i><i></i><i></i></div></div>
      <div class="pm-url">${I.lock}<span>${esc(host)}</span></div>
      <div class="pm-bar">${I.left}${I.right}<b class="pm-hit">${I.share}${tap}</b>${I.book}${I.tabs}</div></div>`,
  ios_add: () => `<div class="pm pm-phone"><div class="pm-dim"></div>
      <div class="pm-sheet"><div class="pm-sheet-head">${appIco()}<div><b>Clause &amp; Effect</b><span>${esc(host)}</span></div></div>
      <div class="pm-list pm-scroll"><div>${I.copy}<span>${t("copy_row")}</span></div><div>${I.star}<span>${t("fav_row")}</span></div>
      <div class="pm-hit">${I.plusbox}<span>${t("add_hs")}</span>${tap}</div></div></div></div>`,
  ios_confirm: () => `<div class="pm pm-phone">
      <div class="pm-dialog"><div class="pm-dlg-bar"><span>${t("cancel")}</span><b>${t("add_hs")}</b><em class="pm-hit">${t("add")}${tap}</em></div>
      <div class="pm-dlg-row">${appIco()}<div><b>Clause &amp; Effect</b><span>${esc(host)}</span></div></div></div>
      <div class="pm-home">${"<i></i>".repeat(7)}<span class="pm-new">${appIco()}<small>Clause &amp; Effect</small></span></div></div>`,
  and_menu: () => `<div class="pm pm-phone">
      <div class="pm-top"><div class="pm-url">${I.lock}<span>${esc(host)}</span></div><b class="pm-hit">${I.kebab}${tap}</b></div>
      <div class="pm-page">${appIco("ghost")}<div class="pm-lines"><i></i><i></i><i></i></div></div></div>`,
  and_install: () => `<div class="pm pm-phone"><div class="pm-top"><div class="pm-url">${I.lock}<span>${esc(host)}</span></div>${I.kebab}</div>
      <div class="pm-menu pm-list"><div>${I.tabs}<span>${t("newtab")}</span></div><div>${I.star}<span>${t("bookmarks")}</span></div><div>${I.share}<span>${t("share_row")}</span></div>
      <div class="pm-hit">${I.device}<span>${t("install").replace(/^./, (c) => c.toUpperCase())}</span>${tap}</div></div></div>`,
  and_confirm: () => `<div class="pm pm-phone"><div class="pm-dim"></div>
      <div class="pm-modal">${appIco("lg")}<b>Clause &amp; Effect</b><span>${esc(host)}</span>
      <div class="pm-modal-btns"><span>${t("cancel")}</span><em class="pm-hit">${t("install_btn")}${tap}</em></div></div></div>`,
  dt_icon: () => `<div class="pm pm-desk"><div class="pm-chrome"><i></i><i></i><i></i>
      <div class="pm-omni">${I.lock}<span>${esc(host)}</span><b class="pm-hit">${I.monitor}${tap}</b></div></div>
      <div class="pm-page wide">${appIco("ghost")}<div class="pm-lines"><i></i><i></i><i></i></div></div></div>`,
  dt_confirm: () => `<div class="pm pm-desk"><div class="pm-chrome"><i></i><i></i><i></i><div class="pm-omni">${I.lock}<span>${esc(host)}</span>${I.monitor}</div></div>
      <div class="pm-pop"><div class="pm-dlg-row">${appIco()}<div><b>${t("install")}?</b><span>Clause &amp; Effect · ${esc(host)}</span></div></div>
      <div class="pm-modal-btns"><span>${t("cancel")}</span><em class="pm-hit">${t("install_btn")}${tap}</em></div></div></div>`,
  mac_share: () => `<div class="pm pm-desk"><div class="pm-chrome mac"><i></i><i></i><i></i>
      <div class="pm-omni">${I.lock}<span>${esc(host)}</span></div><b class="pm-hit">${I.share}${tap}</b></div>
      <div class="pm-page wide">${appIco("ghost")}<div class="pm-lines"><i></i><i></i><i></i></div></div></div>`,
  mac_dock: () => `<div class="pm pm-desk"><div class="pm-chrome mac"><i></i><i></i><i></i><div class="pm-omni">${I.lock}<span>${esc(host)}</span></div>${I.share}</div>
      <div class="pm-menu pm-list right"><div>${I.copy}<span>${t("copy_row")}</span></div><div>${I.glasses}<span>${t("read_row")}</span></div>
      <div class="pm-hit">${I.dock}<span>${t("add_dock")}</span>${tap}</div></div></div>`,
  inapp_open: () => `<div class="pm pm-phone"><div class="pm-top"><div class="pm-url">${I.lock}<span>${esc(host)}</span></div><b>${I.dots}</b></div>
      <div class="pm-menu pm-list"><div>${I.copy}<span>${t("copy_row")}</span></div><div>${I.share}<span>${t("share_row")}</span></div>
      <div class="pm-hit">${I.globe}<span>${t("open_browser")}</span>${tap}</div></div></div>`,
  inapp_again: () => `<div class="pm pm-phone"><div class="pm-page">${appIco("lg")}
      <div class="pm-pill pm-hit">${I.device}<span>${t("install")}</span>${tap}</div></div></div>`,
};
const FLOWS = {
  ios: ["ios_share", "ios_add", "ios_confirm"],
  android: ["and_menu", "and_install", "and_confirm"],
  desktop: ["dt_icon", "dt_confirm"],
  macsafari: ["mac_share", "mac_dock"],
  inapp: ["inapp_open", "inapp_again"],
};
const STEP_MS = 3800;

// ------------------------------------------------------------------ sheet --
let sheet = null;
function openSheet({ success = false } = {}) {
  closeSheet(true);
  const flow = FLOWS[flowName()];
  sheet = document.createElement("div");
  sheet.className = "pwa-sheet";
  sheet.setAttribute("role", "dialog");
  sheet.setAttribute("aria-modal", "true");
  sheet.setAttribute("aria-labelledby", "pwa-title");
  sheet.dataset.flow = flowName();
  sheet.innerHTML = `<div class="pwa-card" tabindex="-1">
    <i class="pwa-grab" aria-hidden="true"></i>
    <button type="button" class="icon-btn pwa-x" data-pwa-close aria-label="${t("close")}">${I.close}</button>
    <header class="pwa-head">${appIco()}<div><h2 id="pwa-title">${t("install")}</h2><p>${t("sub")}</p></div></header>
    <div class="pwa-bars" aria-hidden="true">${flow.map(() => "<i><b></b></i>").join("")}</div>
    <div class="pwa-stage">${flow.map((k, i) => `<section class="pwa-slide" data-i="${i}" aria-hidden="true">
      <div class="pwa-art">${ART[k]()}</div>
      <h3><span class="pwa-n">${i + 1}</span>${esc(t(k))}</h3>
      <p>${esc(t(k + "_hint"))}${k === "inapp_open" ? ` <button type="button" class="pill ghost pwa-copy" data-pwa-copy>${I.copy}${t("copy")}</button>` : ""}</p>
    </section>`).join("")}
      <section class="pwa-done" aria-hidden="true"><div class="pwa-done-ico">${appIco("xl")}<b>${I.check}</b></div>
        <h3>${t("installed")}</h3><p>${t("installed_s")}</p></section>
    </div>
    <footer class="pwa-foot">
      <button type="button" class="pill ghost" data-pwa-back>${I.left}<span>${t("back")}</span></button>
      <button type="button" class="pill primary" data-pwa-next><span>${t("next")}</span>${I.right}</button>
    </footer>
  </div>`;
  document.body.append(sheet);
  const card = $(".pwa-card", sheet);
  let i = 0, timer = 0, auto = !RM.matches;
  const show = (n) => {
    i = Math.max(0, Math.min(flow.length - 1, n));
    sheet.querySelectorAll(".pwa-slide").forEach((s) => {
      const on = +s.dataset.i === i;
      s.classList.toggle("on", on); s.classList.toggle("past", +s.dataset.i < i);
      s.setAttribute("aria-hidden", String(!on));
    });
    sheet.querySelectorAll(".pwa-bars i").forEach((b, n2) => { b.className = n2 < i ? "full" : n2 === i ? (auto ? "run" : "full") : ""; });
    $("[data-pwa-back]", sheet).style.visibility = i ? "visible" : "hidden";
    const last = i === flow.length - 1;
    $("[data-pwa-next]", sheet).innerHTML = last ? `<span>${t("done")}</span>${I.check}` : `<span>${t("next")}</span>${I.right}`;
    clearTimeout(timer);
    if (auto && !last) timer = setTimeout(() => show(i + 1), STEP_MS);
    sheet.style.setProperty("--step-ms", STEP_MS + "ms");
  };
  const stop = () => { auto = false; clearTimeout(timer); };
  sheet._done = () => {
    stop(); sheet.classList.add("success");
    $(".pwa-done", sheet).setAttribute("aria-hidden", "false");
    $("[data-pwa-back]", sheet).style.visibility = "hidden";
    $("[data-pwa-next]", sheet).innerHTML = `<span>${t("done")}</span>${I.check}`;
    $("[data-pwa-next]", sheet).onclick = () => closeSheet();
  };
  sheet.addEventListener("click", (e) => {
    if (e.target === sheet || e.target.closest("[data-pwa-close]")) return closeSheet();
    if (e.target.closest("[data-pwa-back]")) { stop(); show(i - 1); }
    else if (e.target.closest("[data-pwa-next]")) {
      if (sheet.classList.contains("success")) return;
      stop();
      if (i === flow.length - 1) { save({ tutorialDone: Date.now() }); closeSheet(); } else show(i + 1);
    } else if (e.target.closest("[data-pwa-copy]")) {
      navigator.clipboard?.writeText(location.href).then(() => { e.target.closest("[data-pwa-copy]").innerHTML = `${I.check}${t("copied")}`; });
    } else if (e.target.closest(".pwa-stage")) stop();
  });
  // swipe between steps
  let x0 = null;
  $(".pwa-stage", sheet).addEventListener("pointerdown", (e) => { x0 = e.clientX; });
  $(".pwa-stage", sheet).addEventListener("pointerup", (e) => {
    if (x0 == null) return;
    const dx = e.clientX - x0; x0 = null;
    if (Math.abs(dx) > 40) { stop(); show(i + (dx < 0 ? 1 : -1)); }
  });
  sheet.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeSheet();
    else if (e.key === "ArrowRight") { stop(); show(i + 1); }
    else if (e.key === "ArrowLeft") { stop(); show(i - 1); }
    else if (e.key === "Tab") { // keep focus inside the dialog
      const f = [...sheet.querySelectorAll("button:not([style*='hidden'])")].filter((b) => b.offsetParent);
      if (!f.length) return;
      const [a, z] = [f[0], f[f.length - 1]];
      if (e.shiftKey && document.activeElement === a) { e.preventDefault(); z.focus(); }
      else if (!e.shiftKey && document.activeElement === z) { e.preventDefault(); a.focus(); }
    }
  });
  sheet._prevFocus = document.activeElement;
  document.documentElement.classList.add("pwa-lock");
  requestAnimationFrame(() => { sheet.classList.add("open"); show(0); card.focus({ preventScroll: true }); if (success) sheet._done(); });
  hideNudge();
}
function closeSheet(instant = false) {
  if (!sheet) return;
  const s = sheet; sheet = null;
  document.documentElement.classList.remove("pwa-lock");
  s._prevFocus?.focus?.({ preventScroll: true });
  if (instant || RM.matches) return s.remove();
  s.classList.remove("open"); s.classList.add("closing");
  setTimeout(() => s.remove(), 320);
}

// ------------------------------------------------------------------ install --
async function install(src = "button") {
  save({ lastSource: src });
  if (deferred) {
    const ev = deferred; deferred = null;
    hideNudge();
    try {
      await ev.prompt();
      const { outcome } = await ev.userChoice;
      if (outcome === "dismissed") save({ dismissedAt: Date.now() });
    } catch { openSheet(); }
    sync();
    return;
  }
  openSheet();
}
function onInstalled() {
  save({ installed: Date.now() });
  hideNudge();
  if (sheet) sheet._done(); else openSheet({ success: true });
  sync();
}

// ------------------------------------------------------------------ entry points --
let navBtn = null, footLink = null;
// The nav row is tight on phones: keep the nav button only when it fits without wrapping the row.
function fitNav() {
  const tools = $(".nav-tools");
  if (!navBtn || !tools || navBtn.hidden) return;
  navBtn.classList.add("pwa-nofit");
  const base = tools.getBoundingClientRect().top;
  navBtn.classList.remove("pwa-nofit");
  if (Math.abs(tools.getBoundingClientRect().top - base) > 4) navBtn.classList.add("pwa-nofit");
}
addEventListener("resize", () => { clearTimeout(fitNav.t); fitNav.t = setTimeout(fitNav, 150); });
// home: no install link in the hero (redesign); install lives in the footer and in one card after the first answer
function mountHero() {}
function mountEntry() {
  const tools = $(".nav-tools");
  if (tools && !navBtn) {
    navBtn = document.createElement("button");
    navBtn.type = "button";
    navBtn.className = "pill ghost pwa-nav";
    navBtn.dataset.pwaInstall = "nav";
    tools.prepend(navBtn);
  }
  const links = $(".footer-links");
  if (links && !footLink) {
    footLink = document.createElement("a");
    footLink.href = "#install";
    footLink.className = "pwa-foot-link";
    footLink.dataset.pwaInstall = "footer";
    links.append(footLink);
  }
  sync();
}
function sync() {
  const show = canInstall();
  document.documentElement.classList.toggle("pwa-standalone", isStandalone());
  if (navBtn) {
    navBtn.hidden = !show;
    navBtn.innerHTML = `${I.device}<span class="pwa-nav-l">${t("install_short")}</span>`;
    navBtn.setAttribute("aria-label", t("install"));
    navBtn.title = t("install");
    navBtn.classList.toggle("ready", !!deferred);
  }
  if (footLink) { footLink.hidden = !show; footLink.textContent = t("install_footer"); }
  document.querySelectorAll(".pwa-hero").forEach((b) => {
    b.hidden = !show;
    b.innerHTML = `${I.device}<span>${t("install_footer")}</span><small>${t("offline_ok")}</small>`;
  });
  requestAnimationFrame(fitNav);
  if (nudge) { $("b", nudge).textContent = t("nudge_t"); $("span", nudge).textContent = t("nudge_s"); }
}
document.addEventListener("click", (e) => {
  const b = e.target.closest("[data-pwa-install]");
  if (!b) return;
  e.preventDefault();
  install(b.dataset.pwaInstall);
});

// gentle prompt after the first successful answer (once per 14 days after a dismissal, at most 3 times)
let nudge = null;
const DAY = 864e5;
function maybeNudge() {
  if (!canInstall() || sheet || nudge) return;
  if (st.installed || (st.dismissedAt && Date.now() - st.dismissedAt < 14 * DAY) || (st.nudges || 0) >= 1) return;
  if (!matchMedia("(max-width: 640px), (pointer: coarse)").matches) return; // desktop: footer link only
  if (sessionStorage.getItem("ce.pwa.nudged")) return;
  // not on the first answer: only from the second address of a visit, so it never greets a new reader
  const seen = new Set(JSON.parse(sessionStorage.getItem("ce.pwa.addr") || "[]")); seen.add(location.hash);
  sessionStorage.setItem("ce.pwa.addr", JSON.stringify([...seen]));
  if (seen.size < 2) return;
  // shown once, after the reader has scrolled past the answers, so it never covers one
  removeEventListener("scroll", nudgeWatch);
  addEventListener("scroll", nudgeWatch, { passive: true });
}
function nudgeWatch() {
  const lists = document.querySelectorAll("#main .answers .topics");
  const last = lists[lists.length - 1];
  if (!last || last.getBoundingClientRect().bottom > innerHeight - 200) return;
  removeEventListener("scroll", nudgeWatch);
  if (sheet || nudge || sessionStorage.getItem("ce.pwa.nudged")) return;
  sessionStorage.setItem("ce.pwa.nudged", "1");
  save({ nudges: (st.nudges || 0) + 1 });
  nudge = document.createElement("div");
  nudge.className = "pwa-nudge";
  nudge.setAttribute("role", "dialog");
  nudge.setAttribute("aria-label", t("install"));
  nudge.innerHTML = `${appIco()}<div class="pwa-nudge-t"><b></b><span></span></div>
    <button type="button" class="pill primary" data-pwa-install="nudge">${t("install_short")}</button>
    <button type="button" class="icon-btn" data-pwa-nudge-x aria-label="${t("not_now")}">${I.close}</button>`;
  nudge.querySelector("[data-pwa-nudge-x]").onclick = () => { save({ dismissedAt: Date.now() }); hideNudge(); };
  document.body.append(nudge);
  sync();
}
function hideNudge() {
  removeEventListener("scroll", nudgeWatch);
  if (!nudge) return;
  const n = nudge; nudge = null;
  n.classList.add("out");
  setTimeout(() => n.remove(), RM.matches ? 0 : 300);
}

// ------------------------------------------------------------------ offline banner --
let net = null;
const fmtWhen = (iso) => {
  const d = new Date(iso);
  if (isNaN(d)) return "";
  return d.toLocaleString(lang() === "es" ? "es-US" : "en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
};
function netBanner(kind, savedAt) {
  const main = $("#main");
  if (!main) return;
  if (!kind) { net?.remove(); net = null; return; }
  if (!net) {
    net = document.createElement("div");
    net.className = "pwa-net";
    net.setAttribute("role", "status");
    main.before(net);
  }
  net.dataset.kind = kind;
  const text = kind === "saved" ? t("offline_saved").replace("{d}", fmtWhen(savedAt)) : kind === "online" ? t("online") : t("offline");
  net.innerHTML = `<span class="pwa-net-pill"><i class="dot"></i>${esc(text)}</span>`;
  if (kind === "online") setTimeout(() => net?.dataset.kind === "online" && netBanner(null), 2400);
}
// answers the service worker served from its offline store, by API path -> saved-at time
const savedAnswers = new Map();
function refreshNet() {
  const id = (location.hash.match(/^#\/a\/([^/?]+)/) || [])[1];
  const at = id && savedAnswers.get("/api/address/" + id.toUpperCase());
  if (at) netBanner("saved", at);
  else if (!navigator.onLine) netBanner("offline");
  else if (net && net.dataset.kind !== "online") netBanner(null);
}
addEventListener("offline", refreshNet);
addEventListener("online", () => { savedAnswers.clear(); if (net) netBanner("online"); });
addEventListener("hashchange", refreshNet);

// ------------------------------------------------------------------ update toast --
function updateToast() {
  if ($(".pwa-update")) return;
  const el = document.createElement("div");
  el.className = "toast pwa-update";
  el.setAttribute("role", "alert");
  el.innerHTML = `${I.refresh}<span>${t("update")}</span><button type="button" class="pwa-refresh">${t("refresh")}</button>
    <button type="button" class="pwa-tx" aria-label="${t("close")}">${I.close}</button>`;
  el.querySelector(".pwa-refresh").onclick = () => location.reload();
  el.querySelector(".pwa-tx").onclick = () => { el.classList.add("out"); el.addEventListener("animationend", () => el.remove(), { once: true }); };
  ($("#toasts") || document.body).append(el);
}
function toast(msg) {
  const el = document.createElement("div");
  el.className = "toast pwa-welcome";
  el.innerHTML = `${appIco()}<span>${esc(msg)}</span>`;
  ($("#toasts") || document.body).append(el);
  setTimeout(() => { el.classList.add("out"); el.addEventListener("animationend", () => el.remove(), { once: true }); }, 3200);
}
// The page is stale when the newest shell references other hashed assets than the ones this page runs.
async function pageIsStale() {
  try {
    const html = await (await fetch("/", { cache: "no-store" })).text();
    const mine = [...document.querySelectorAll('script[src*="?v="], link[href*="?v="]')].map((e) => e.getAttribute("src") || e.getAttribute("href"));
    return mine.some((u) => !html.includes(u));
  } catch { return false; }
}

// ------------------------------------------------------------------ service worker --
let swStarted = false;
async function registerSW() {
  if (swStarted || !("serviceWorker" in navigator)) return;
  swStarted = true;
  let controlled = !!navigator.serviceWorker.controller;
  navigator.serviceWorker.addEventListener("controllerchange", async () => {
    if (controlled && (await pageIsStale())) updateToast();
    controlled = true;
  });
  navigator.serviceWorker.addEventListener("message", (e) => {
    if (e.data?.type === "offline-answer") { savedAnswers.set(e.data.path, e.data.savedAt); refreshNet(); }
    if (e.data?.type === "fresh-answer" && savedAnswers.delete(e.data.path)) refreshNet();
  });
  try {
    const reg = await navigator.serviceWorker.register("/sw.js", { scope: "/", updateViaCache: "none" });
    const check = () => reg.update().catch(() => {});
    document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") check(); });
    setInterval(check, 15 * 60 * 1000);
  } catch (err) { console.warn("service worker", err); }
}

// ------------------------------------------------------------------ boot --
addEventListener("beforeinstallprompt", (e) => { e.preventDefault(); deferred = e; sync(); });
addEventListener("appinstalled", onInstalled);
matchMedia("(display-mode: standalone)").addEventListener?.("change", sync);
new MutationObserver(sync).observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });

function boot() {
  mountEntry();
  const main = $("#main");
  if (main) new MutationObserver(() => { mountHero(); if ($(".answers-head", main)) maybeNudge(); }).observe(main, { childList: true });
  mountHero();
  const q = new URLSearchParams(location.search);
  if (isStandalone()) {
    if (!st.installed) { save({ installed: Date.now() }); setTimeout(() => toast(t("welcome")), 900); }
  }
  if (q.get("action") === "search") {
    // home-screen shortcut "Check an address": open the search once the app has rendered
    const open = () => $("[data-cmdk]")?.click();
    if (main?.children.length) setTimeout(open, 300); else new MutationObserver((_, o) => { o.disconnect(); setTimeout(open, 300); }).observe(main, { childList: true });
  }
  if (q.has("source") || q.has("action")) history.replaceState(null, "", location.pathname + location.hash);
  refreshNet();
  // Cloudflare Rocket Loader (on for the zone) reports readyState "loading" for good and swallows "load", so the
  // real load time comes from navigation timing, with a timer as the last resort
  const loaded = document.readyState === "complete" || performance.getEntriesByType?.("navigation")[0]?.loadEventEnd > 0;
  if (loaded) registerSW(); else { addEventListener("load", registerSW, { once: true }); setTimeout(registerSW, 5000); }
}
if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, { once: true }); else boot();

window.CE_PWA = { isStandalone, install, openTutorial: () => openSheet(), state: st };
