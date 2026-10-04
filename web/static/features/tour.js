// Clause & Effect · product tour (#97): a one-click, ~60 s guided walk through the live app.
// Drives the real UI (search, the topic rows, a topic's plain answer and "Show me the law", the as-of date,
// Check a rent increase, Ask, My properties) and spotlights each part with a ring and a one-sentence caption.
// Entry: "Take the tour" links (data-tour-slot="home" / "footer") and the deep link #/tour.
//
// Geometry (why it never jiggles): each beat first drives the UI to its route, then waits until its target exists, is
// really shown (not inside a closed <details>), fonts and images are ready, no entrance animation moves it, and two
// rAF measurements agree. The page is scrolled once (smooth, or instant with reduced motion) to a planned position;
// the ring and caption spring (critically damped: no overshoot, monotonic) to where the target will be when that
// scroll ends, then stay glued to it. One rAF loop owns all writes, transform only (the ring's size is set inline),
// no CSS transitions on position, no scroll/resize listeners, no ResizeObserver. The caption placer keeps the card
// next to the ring, never over it, never off-screen and never under the phone tab bar; the Ask dock hides meanwhile.
// Esc / close restores route, as-of date, scroll and focus. No scroll lock, no click-eating layer.

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const CE = window.CE;
const RM = matchMedia("(prefers-reduced-motion: reduce)");

// The story: a rent-controlled building in Jersey City. Its rent topic leads (plain answer, then the law); the
// algorithmic-rent topic shows the as-of date at work: New Jersey's FAIR Act takes effect on 2027-07-01, so the
// same row reads "Changes Jul 1, 2027" today and "Banned from Jul 1, 2027" on that day.
const ADDR = { id: "A0012", query: "1064 Summit" };
const OPEN_CAT = "rent_increase_limits";
const DATE_CAT = "algorithmic_rent_setting";
const LATER = "2027-07-01";

// ------------------------------------------------------------------ i18n --
const T = {
  en: {
    entry: "Take the tour",
    s_search: "Type an address, or pick one.",
    s_answer: "Each topic gets a clear answer for this building.",
    s_rule: "Open a topic for the plain answer.",
    s_source: "Then the exact words of the law, and the official source.",
    s_asof: "Change the date to see the law on any day.",
    s_asof_after: "On {d}, this law takes effect here.",
    s_check: "Check a rent increase against the law, step by step.",
    s_ask: "Ask anything in plain words. Every answer quotes the law.",
    s_props: "Save your buildings. We email you before a law changes.",
    s_done: "Now try your own address.",
    cta: "Search your address", next: "Next", back: "Back", close: "Close tour", pause: "Pause", play: "Play",
    of: "{i} of {n}", label: "Product tour",
  },
  es: {
    entry: "Haga el recorrido",
    s_search: "Escribe una dirección o elige una.",
    s_answer: "Cada tema recibe una respuesta clara para este edificio.",
    s_rule: "Abre un tema para ver la respuesta clara.",
    s_source: "Luego, las palabras exactas de la ley y la fuente oficial.",
    s_asof: "Cambia la fecha para ver la ley de cualquier día.",
    s_asof_after: "El {d}, esta ley entra en vigor aquí.",
    s_check: "Comprueba paso a paso si un aumento de alquiler cumple la ley.",
    s_ask: "Pregunta lo que quieras. Cada respuesta cita la ley.",
    s_props: "Guarda tus edificios. Te avisamos por correo antes de que cambie una ley.",
    s_done: "Ahora prueba con tu dirección.",
    cta: "Busque su dirección", next: "Siguiente", back: "Atrás", close: "Cerrar recorrido", pause: "Pausa", play: "Reproducir",
    of: "{i} de {n}", label: "Recorrido",
  },
};
const lang = () => (CE?.lang?.() === "es" || document.documentElement.lang === "es" ? "es" : "en");
const t = (k) => T[lang()][k] ?? T.en[k] ?? k;

// ------------------------------------------------------------------ DOM helpers --
// really on screen: laid out, not hidden, and not inside a closed <details> (Chrome reports real rects for the
// content of a closed <details>, so a size check alone spotlights invisible elements)
function shown(el) {
  if (!el || !el.isConnected) return false;
  const r = el.getBoundingClientRect();
  if (r.width < 2 || r.height < 2) return false;
  if (el.checkVisibility && !el.checkVisibility({ visibilityProperty: true, contentVisibilityAuto: true })) return false;
  for (let d = el.parentElement?.closest("details"); d; d = d.parentElement?.closest("details")) {
    if (!d.open && !(d.firstElementChild?.matches("summary") && d.firstElementChild.contains(el))) return false;
  }
  const cs = getComputedStyle(el);
  return cs.visibility !== "hidden" && cs.display !== "none";
}
const firstShown = (...lists) => { for (const l of lists) for (const el of l) if (shown(el)) return el; return null; };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const frame = () => new Promise((r) => requestAnimationFrame(() => r()));
async function waitFor(fn, ms = 6000) {
  const t0 = performance.now();
  for (;;) {
    const v = fn();
    if (v && (!Array.isArray(v) || v.length)) return v;
    if (performance.now() - t0 > ms) return null;
    await sleep(50);
  }
}
// resolves after the next finished route (of `view`, at `hash`), once the router has set its scroll position
const routeOnce = (view, hash) => new Promise((res) => {
  const h = (e) => {
    if ((view && e.detail?.view !== view) || (hash && location.hash !== hash)) return;
    document.removeEventListener("ce:route", h); setTimeout(res, 0);
  };
  document.addEventListener("ce:route", h);
  setTimeout(() => { document.removeEventListener("ce:route", h); res(); }, 6000);
});
async function goHash(hash, view) {
  if (location.hash === hash) return;
  const p = routeOnce(view, hash);
  location.replace(hash); // no history entries for tour hops
  await p;
}
function setAsOf(d, { quiet = false } = {}) {
  if (CE.asOf() === d) return Promise.resolve();
  const box = $("#toasts"), n = box ? box.children.length : 0;
  const p = routeOnce();
  if (typeof CE.setAsOf === "function") CE.setAsOf(d);
  else {
    const inp = $("#asof");
    if (!inp) return Promise.resolve();
    inp.value = d;
    inp.dispatchEvent(new Event("change", { bubbles: true }));
  }
  if (quiet && box) while (box.children.length > n) box.lastElementChild.remove();
  return p;
}

// ------------------------------------------------------------------ targets (today's markup) --
const topicEl = (cat) => $(`#main details.topic[data-cat="${cat}"]`);
const TG = {
  search: () => firstShown($$('#main [data-tour="search"]'), $$("#main .big-search")),
  searchInput: () => { const s = TG.search(); return s && (s.matches("input") ? s : $("input", s)); },
  answer: () => { // the topic rows, as many as fit above the caption (at least two)
    const all = $$('#main .answers .topics > details.topic[data-cat]').filter(shown);
    if (!all.length || !S) return all.slice(0, 3);
    const room = ringRoom(), top = all[0].getBoundingClientRect().top;
    const fit = all.filter((el, i) => i < 2 || el.getBoundingClientRect().bottom - top <= room);
    return fit.slice(0, 6);
  },
  // the open topic: its question, its one-line answer and the plain "why" sentence under it
  plain: () => {
    const tp = topicEl(OPEN_CAT);
    if (!tp?.open) return null;
    const sum = $(":scope > summary", tp), why = $(".topic-body > .why", tp);
    return [sum, why].filter(shown);
  },
  // "Show me the law": the quoted sentence and its source line
  source: () => {
    const tp = topicEl(OPEN_CAT), law = tp && $("details.law", tp);
    if (!law?.open) return null;
    return firstShown($$('.law-in > [data-tour="source"]', law), $$(".law-in .quote", law));
  },
  asof: () => firstShown($$('[data-tour="asof"]'), $$("#asof-ctl")),
  dateRow: () => { const tp = topicEl(DATE_CAT); return tp && firstShown([$(":scope > summary", tp)]); },
  check: () => firstShown($$('#main .prop-cta a[href^="#/check/"]'), $$('#main a.btn[href^="#/check/"]')),
  ask: () => firstShown($$("#main .ask-bar--hero")),
  props: () => firstShown($$('.tabs a[data-route="properties"]'), $$('[data-tour="properties"]'), $$("#main .mp-root h1")),
};

// ------------------------------------------------------------------ steps --
// Each step has beats; a beat drives the UI (enter), names its target and caption, and how long it stays (auto mode).
// side: where the caption prefers to sit ("bottom" = at the bottom of the screen, never over the home headline).
const onAddr = () => goHash(`#/a/${ADDR.id}`, "lookup");
const STEPS = [
  { beats: [{
    ms: 6500, text: "s_search", target: TG.search, side: "bottom",
    async enter() {
      await setAsOf(S.asOf, { quiet: true });
      await goHash("#/", "lookup");
      const inp = await waitFor(TG.searchInput);
      if (inp) { inp.value = ""; inp.dispatchEvent(new Event("input", { bubbles: true })); }
    },
    async after(tok) { // types once the spotlight is in place
      const inp = TG.searchInput();
      if (!inp || !live(tok)) return;
      const type = async (s) => { inp.value = s; inp.dispatchEvent(new Event("input", { bubbles: true })); };
      if (RM.matches) return type(ADDR.query);
      for (let i = 1; i <= ADDR.query.length; i++) { if (!live(tok)) return; await type(ADDR.query.slice(0, i)); await sleep(70); }
    },
    leave() { const inp = TG.searchInput(); if (inp) { inp.value = ""; inp.dispatchEvent(new Event("input", { bubbles: true })); } },
  }] },
  { beats: [{
    ms: 7000, text: "s_answer", target: TG.answer,
    async enter() { await setAsOf(S.asOf, { quiet: true }); await onAddr(); foldTopics(); },
  }] },
  { beats: [
    { ms: 5500, text: "s_rule", target: TG.plain, async enter() { await setAsOf(S.asOf, { quiet: true }); await onAddr(); openTopic(false); } },
    { ms: 7500, text: "s_source", target: TG.source, async enter() { await setAsOf(S.asOf, { quiet: true }); await onAddr(); openTopic(true); } },
  ] },
  { beats: [
    { ms: 4500, text: "s_asof", target: TG.asof, async enter() { await setAsOf(S.asOf, { quiet: true }); await onAddr(); foldTopics(); } },
    { ms: 7500, text: "s_asof_after", target: TG.dateRow, async enter() { await onAddr(); foldTopics(); await setAsOf(LATER); foldTopics(); } },
  ] },
  { beats: [{
    ms: 6500, text: "s_check", target: TG.check,
    async enter() { await setAsOf(S.asOf, { quiet: true }); await onAddr(); foldTopics(); },
  }] },
  { beats: [{
    ms: 6500, text: "s_ask", target: TG.ask,
    async enter() { await setAsOf(S.asOf, { quiet: true }); await goHash("#/ask", "ask"); },
  }] },
  { beats: [
    { ms: 7000, text: "s_props", target: TG.props, async enter() { await setAsOf(S.asOf, { quiet: true }); await goHash("#/properties", "properties"); } },
    { ms: 0, text: "s_done", target: null, done: true, async enter() { await setAsOf(S.asOf, { quiet: true }); } },
  ] },
];
const FLAT = STEPS.flatMap((s, si) => s.beats.map((b, bi) => ({ ...b, step: si, first: bi === 0 })));

function foldTopics() { $$("#main details.topic[open]").forEach((d) => { $$("details[open]", d).forEach((x) => { x.open = false; }); d.open = false; }); }
function openTopic(law) {
  const tp = topicEl(OPEN_CAT);
  if (!tp) return;
  $$("#main details.topic[open]").forEach((d) => { if (d !== tp) d.open = false; });
  tp.open = true;
  const l = $("details.law", tp);
  if (l) l.open = law;
  if (!law) $$("details.law details[open]", tp).forEach((d) => { d.open = false; });
}

// ------------------------------------------------------------------ overlay --
let S = null; // running tour state
const live = (tok) => S && S.tok === tok;

function build() {
  const root = document.createElement("div");
  root.className = "tour";
  root.innerHTML = `<div class="tour-ring" aria-hidden="true"></div>
    <section class="tour-card" role="dialog" aria-modal="false" aria-labelledby="tour-text" tabindex="-1">
      <i class="tour-bar" aria-hidden="true"><b></b></i>
      <p class="tour-text" id="tour-text" aria-live="polite"></p>
      <div class="tour-row">
        <span class="tour-count"></span>
        <button type="button" class="tour-icon" data-tour-play></button>
        <span class="tour-gap"></span>
        <button type="button" class="tour-btn ghost" data-tour-back></button>
        <button type="button" class="tour-btn primary" data-tour-next></button>
      </div>
      <button type="button" class="tour-icon tour-x" data-tour-close><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg></button>
    </section>`;
  root.addEventListener("click", (e) => {
    if (e.target.closest("[data-tour-close]")) return stop();
    if (e.target.closest("[data-tour-back]")) { manual(); return show(prevStepStart()); }
    if (e.target.closest("[data-tour-next]")) {
      const b = FLAT[S.i];
      if (b.done) return finish();
      manual(); return show(S.i + 1);
    }
    if (e.target.closest("[data-tour-play]")) { S.auto = !S.auto; paintCard(); return schedule(); }
  });
  return root;
}
// Back jumps to the start of the previous step (or of this one, from its 2nd beat)
function prevStepStart() {
  const cur = FLAT[S.i];
  if (!cur.first) return FLAT.findIndex((b) => b.step === cur.step);
  return FLAT.findIndex((b) => b.step === Math.max(0, cur.step - 1));
}
function manual() { S.auto = false; }

const ICON_PAUSE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6v12M15 6v12"/></svg>';
const ICON_PLAY = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5.5v13l10.5-6.5z"/></svg>';
function paintCard() {
  if (!S) return;
  const b = FLAT[S.i], root = S.root;
  const card = $(".tour-card", root);
  card.setAttribute("aria-label", t("label"));
  let txt = t(b.text);
  if (b.text === "s_asof_after") txt = txt.replace("{d}", CE.fmtDate(LATER));
  $(".tour-text", root).textContent = txt;
  $(".tour-count", root).textContent = t("of").replace("{i}", b.step + 1).replace("{n}", STEPS.length);
  const back = $("[data-tour-back]", root), next = $("[data-tour-next]", root), play = $("[data-tour-play]", root);
  back.textContent = t("back");
  back.hidden = S.i === 0 || b.done;
  next.textContent = b.done ? t("cta") : t("next");
  play.hidden = b.done || RM.matches;
  play.innerHTML = S.auto ? ICON_PAUSE : ICON_PLAY;
  play.setAttribute("aria-label", t(S.auto ? "pause" : "play"));
  $("[data-tour-close]", root).setAttribute("aria-label", t("close"));
  root.classList.toggle("is-done", !!b.done);
  root.classList.toggle("is-auto", S.auto && !b.done);
  const bar = $(".tour-bar b", root);
  bar.style.animation = "none";
  if (S.auto && !b.done && b.ms && root.dataset.ready) { void bar.offsetWidth; bar.style.animation = ""; bar.style.setProperty("--tour-ms", b.ms + "ms"); }
}
function schedule() {
  clearTimeout(S.timer);
  const b = FLAT[S.i];
  if (S.auto && !b.done && b.ms && S.root.dataset.ready) S.timer = setTimeout(() => S && show(S.i + 1), b.ms);
}

async function show(i) {
  if (!S) return;
  i = Math.max(0, Math.min(FLAT.length - 1, i));
  const prev = FLAT[S.i];
  if (prev && prev !== FLAT[i] && prev.leave) { try { prev.leave(); } catch { /* the view is gone */ } }
  S.i = i;
  const tok = ++S.tok;
  clearTimeout(S.timer);
  const b = FLAT[i];
  // while the UI is driven the ring and card hold still; the ring fades out (the page stays dimmed) once the previous
  // target leaves the screen, so it never frames something else; nothing new is measured meanwhile
  S.hold = S.target; S.holdFixed = S.fixed;
  S.target = null; S.getTarget = null; S.plan = null; S.fixed = false;
  S.root.dataset.beat = i; delete S.root.dataset.ready;
  S.root.classList.add("busy");
  paintCard();
  try { await b.enter?.(tok); } catch (e) { console.warn("tour", e); }
  if (!live(tok)) return;
  const target = b.target ? await settle(b.target, tok) : null;
  if (!live(tok)) return;
  S.root.classList.remove("busy");
  S.target = target; S.getTarget = b.target; S.side = b.side || "below"; S.sticky = null;
  S.fixed = !!target && isFixed(els(target)[0]);
  paintCard(); // final text first: the placer measures the card at its real height
  if (target && !S.fixed) await scrollToTarget(tok);
  if (!live(tok)) return;
  S.root.dataset.ready = "1";
  paintCard();
  schedule();
  b.after?.(tok);
  // keep keyboard users in the card
  const f = document.activeElement;
  if (!S.root.contains(f) || f === document.body) $(b.done ? "[data-tour-next]" : ".tour-card", S.root).focus({ preventScroll: true });
}

// wait until the target exists, is shown, its fonts and images are ready, nothing animates it, and it holds still
async function settle(get, tok) {
  let x = await waitFor(get, 5000);
  if (!x || !live(tok)) return x;
  await Promise.race([document.fonts?.ready, sleep(1500)]);
  const imgs = $$("#main img").filter((im) => !im.complete && im.loading !== "lazy");
  await Promise.race([Promise.all(imgs.map((im) => im.decode().catch(() => {}))), sleep(1200)]);
  for (let round = 0; round < 3 && live(tok); round++) {
    x = get() || x;
    const list = els(x);
    const moving = document.getAnimations().filter((a) => {
      const el = a.effect?.target;
      return a.playState === "running" && el instanceof Element && a.effect.getTiming().iterations !== Infinity && list.some((t) => el.contains(t));
    });
    if (moving.length) await Promise.race([Promise.all(moving.map((a) => a.finished.catch(() => {}))), sleep(1500)]);
    let a = key(x);
    for (let n = 0; n < 30; n++) { // two consecutive frames with the same rect (and still the same element)
      await frame();
      const y = get() || x;
      const b = key(y);
      if (b && b === a) { x = y; break; }
      a = b; x = y;
    }
    if (!document.getAnimations().some((an) => an.playState === "running" && an.effect?.target instanceof Element && an.effect.getTiming().iterations !== Infinity && els(x).some((t) => an.effect.target.contains(t)))) break;
  }
  return x;
}
const key = (x) => { const r = rectOf(x); return r ? [r.left, r.top + scrollY, r.width, r.height].map((v) => Math.round(v)).join(",") : ""; };

// ------------------------------------------------------------------ geometry --
const PAD = 8, GAP = 12, EDGE = 16;
const els = (x) => (Array.isArray(x) ? x : x ? [x] : []);
const isPhone = () => innerWidth < 640;
function rectOf(x) {
  const rs = els(x).filter((e) => e.isConnected).map((e) => e.getBoundingClientRect()).filter((r) => r.width || r.height);
  if (!rs.length) return null;
  const l = Math.min(...rs.map((r) => r.left)), tp = Math.min(...rs.map((r) => r.top));
  const rr = Math.max(...rs.map((r) => r.right)), bt = Math.max(...rs.map((r) => r.bottom));
  return { left: l, top: tp, width: rr - l, height: bt - tp, right: rr, bottom: bt };
}
function isFixed(el) {
  for (let e = el; e && e !== document.body; e = e.parentElement) if (getComputedStyle(e).position === "fixed") return true;
  return !!el?.closest(".nav, #nav"); // the sticky top bar stays put while the page scrolls
}
// the part of the viewport not covered by chrome: the sticky top bar, and the phone tab bar at the bottom
function safeArea() {
  const nav = $("#nav") || $(".nav"), ns = nav && getComputedStyle(nav);
  // the sticky bar covers up to its bottom now, and up to its stuck bottom once the page scrolls (same room either way)
  const top = (ns && ns.position !== "static" ? Math.max(nav.getBoundingClientRect().bottom, (parseFloat(ns.top) || 0) + nav.offsetHeight) : 0) + 8;
  const tabs = $(".tabs");
  const tr = tabs && getComputedStyle(tabs).position === "fixed" ? tabs.getBoundingClientRect() : null;
  const bottom = (tr && tr.top > innerHeight / 2 ? tr.top : innerHeight) - 8;
  return { top, bottom };
}
const cardSize = () => { const c = $(".tour-card", S.root); return { w: c.offsetWidth, h: c.offsetHeight }; };

// the height a target may have so its ring and the caption below it both fit on screen
function ringRoom() { const sa = safeArea(); return sa.bottom - sa.top - cardSize().h - GAP - 2 * PAD; }
// plan one scroll so the target sits in the room the caption leaves (centered if it fits, else from its top)
async function scrollToTarget(tok) {
  const r = rectOf(S.target);
  if (!r) return;
  const sa = safeArea(), room = ringRoom(), top = sa.top + PAD;
  let y;
  if (r.top >= top && r.bottom <= top + room) y = scrollY; // already in place: no motion
  else if (r.height <= room) y = scrollY + r.top - top - (room - r.height) / 2;
  else y = scrollY + r.top - top;
  const max = document.documentElement.scrollHeight - innerHeight;
  y = Math.round(Math.max(0, Math.min(max, y)));
  if (Math.abs(y - scrollY) < 1) return;
  S.plan = y; // until the scroll lands, the ring aims at where the target will be, not where it is
  const smooth = !RM.matches;
  scrollTo({ top: y, behavior: smooth ? "smooth" : "instant" });
  if (smooth) {
    await new Promise((res) => {
      let done = false, still = 0, last = scrollY;
      const end = () => { if (done) return; done = true; removeEventListener("scrollend", end); res(); };
      addEventListener("scrollend", end, { once: true });
      const tick = () => { if (done || !live(tok)) return end(); still = Math.abs(scrollY - last) < 0.5 ? still + 1 : 0; last = scrollY; if (still > 6) end(); else requestAnimationFrame(tick); };
      requestAnimationFrame(tick);
      setTimeout(end, 1500);
    });
  }
  if (live(tok)) S.plan = null;
}

// where the ring and card should be this frame (viewport coordinates), or null when nothing is spotlit
function layout(target, fixed) {
  const W = innerWidth, H = innerHeight, sa = safeArea(), { w: cw, h: ch } = cardSize();
  const b = FLAT[S.i];
  let r = target ? rectOf(target) : null;
  if (r && S.plan != null && !fixed) { const dy = scrollY - S.plan; r = { ...r, top: r.top + dy, bottom: r.bottom + dy }; }
  if (b.done || !r) { // no target: the card sits in the middle (done) or at the bottom
    const y = b.done ? (H - ch) / 2 : sa.bottom - ch;
    return { ring: null, card: { x: (W - cw) / 2, y } };
  }
  const phone = isPhone();
  // ring = target + PAD, kept inside the safe area
  let top = r.top - PAD, bot = r.bottom + PAD;
  const left = Math.max(2, r.left - PAD), right = Math.min(W - 2, r.right + PAD);
  const lo = fixed ? 2 : sa.top - PAD, hi = fixed ? H - 2 : sa.bottom + PAD;
  top = Math.max(top, lo); bot = Math.min(bot, hi);
  // caption side: below, above, or docked at the bottom; sticky for the beat while it still fits
  const fits = {
    bottom: sa.bottom - ch - GAP >= bot,
    below: bot + GAP + ch <= sa.bottom,
    above: top - GAP - ch >= sa.top,
  };
  const order = S.side === "bottom" ? ["bottom", "below", "above"] : S.side === "above" ? ["above", "below", "bottom"] : ["below", "above", "bottom"];
  let side = S.sticky && fits[S.sticky] ? S.sticky : order.find((s) => fits[s]);
  if (!side) { // taller than the room: clip the ring above the card (or below it, when the target sits low)
    side = r.top + r.height / 2 > (sa.top + sa.bottom) / 2 ? "above" : "below";
    if (side === "below") bot = Math.max(top + 24, sa.bottom - ch - GAP);
    else top = Math.min(bot - 24, sa.top + ch + GAP);
  }
  S.sticky = side;
  if (bot - top < 16) return { ring: null, card: { x: (W - cw) / 2, y: sa.bottom - ch } };
  let cy = side === "above" ? top - GAP - ch : side === "below" ? bot + GAP : sa.bottom - ch;
  cy = Math.max(sa.top, Math.min(sa.bottom - ch, cy));
  const cx = phone || side === "bottom" ? (W - cw) / 2 : Math.max(EDGE, Math.min(left, W - cw - EDGE));
  return { ring: { x: left, y: top, w: right - left, h: bot - top }, card: { x: cx, y: cy } };
}

// critically damped spring per value: no overshoot, so every value moves one way from start to end
const OMEGA = 18; // rad/s: ~0.35 s to land
function springTo(st, goal, dt) {
  let moving = false;
  for (const k of Object.keys(goal)) {
    const x0 = st.p[k] - goal[k], v0 = st.v[k] || 0;
    if (Math.abs(x0) < 0.25 && Math.abs(v0) < 4) { st.p[k] = goal[k]; st.v[k] = 0; continue; }
    const e = Math.exp(-OMEGA * dt), c = v0 + OMEGA * x0;
    st.p[k] = goal[k] + (x0 + c * dt) * e;
    st.v[k] = (v0 - OMEGA * c * dt) * e;
    moving = true;
  }
  return moving;
}
function loop(now) {
  if (!S) return;
  S.raf = requestAnimationFrame(loop);
  const dt = Math.min(0.05, Math.max(0, (now - (S.last || now)) / 1000)); S.last = now;
  const root = S.root, ring = $(".tour-ring", root), card = $(".tour-card", root);
  const busy = root.classList.contains("busy") && !S.target;
  if (busy && S.hold && !els(S.hold).every(shown)) S.hold = null; // the previous target left the screen
  if (!busy && S.getTarget && !els(S.target).every((e) => e.isConnected)) { const n = S.getTarget(); if (n && els(n).length) S.target = n; } // re-rendered view
  const L = busy ? layout(S.hold, S.holdFixed) : layout(S.target, S.fixed);
  if (busy && S.card.on) L.card = { ...S.card.p }; // the card holds still while the UI is driven
  if (busy && L.ring && S.ring.on) L.ring = { ...S.ring.p }; // so does the ring, while its target is still on screen
  root.classList.toggle("dim", !L.ring);
  // ring
  if (L.ring) {
    // fresh = it was hidden long enough to have faded out; a ring hidden for a moment springs on from where it was
    const fresh = !S.ring.on && (!S.ring.p.w || now - S.ring.off > 220);
    if (fresh || RM.matches) { S.ring.p = { ...L.ring }; S.ring.v = {}; }
    const moving = !fresh && !RM.matches && springTo(S.ring, L.ring, dt);
    if (!moving) { S.ring.p = { ...L.ring }; S.ring.v = {}; }
    const p = S.ring.p;
    ring.style.transform = `translate3d(${p.x}px, ${p.y}px, 0)`;
    ring.style.width = p.w + "px"; ring.style.height = p.h + "px";
    if (!S.ring.on) { ring.classList.add("on"); S.ring.on = true; }
  } else if (S.ring.on) { ring.classList.remove("on"); S.ring.on = false; S.ring.off = now; }
  // card
  const fresh = !S.card.on;
  if (fresh || RM.matches) { S.card.p = { ...L.card }; S.card.v = {}; }
  const cm = !fresh && !RM.matches && springTo(S.card, L.card, dt);
  if (!cm) { S.card.p = { ...L.card }; S.card.v = {}; }
  card.style.transform = `translate3d(${S.card.p.x}px, ${S.card.p.y}px, 0)`;
  if (fresh) { card.classList.add("in"); S.card.on = true; }
}

// ------------------------------------------------------------------ start / stop --
function start({ from } = {}) {
  if (S) return;
  if (!CE) return;
  const hash = from ?? (location.hash.startsWith("#/tour") ? "#/" : location.hash || "#/");
  S = {
    tok: 0, i: 0, timer: 0, target: null, getTarget: null, auto: !RM.matches, plan: null, side: "below", sticky: null,
    ring: { p: {}, v: {}, on: false, off: 0 }, card: { p: {}, v: {}, on: false }, raf: 0, last: 0,
    hash, asOf: CE.asOf(), hadAsOfKey: sessionStorage.getItem("asof") !== null,
    scroll: hash === location.hash ? scrollY : 0, focus: document.activeElement,
    root: build(),
  };
  document.body.append(S.root);
  document.documentElement.classList.add("tour-on");
  document.addEventListener("keydown", onKey, true);
  document.addEventListener("pointerdown", onPointer, true);
  document.addEventListener("ce:lang", paintCard);
  requestAnimationFrame(() => S?.root.classList.add("open"));
  S.raf = requestAnimationFrame(loop);
  show(0);
}
function onKey(e) {
  if (!S) return;
  if (e.key === "Escape") { e.preventDefault(); e.stopImmediatePropagation(); stop(); return; }
  const typing = e.target.closest?.("input, textarea, select, [contenteditable]");
  if (typing) return;
  if (e.key === "ArrowRight") { e.preventDefault(); manual(); FLAT[S.i].done ? finish() : show(S.i + 1); }
  else if (e.key === "ArrowLeft") { e.preventDefault(); manual(); show(prevStepStart()); }
}
// any touch of the page pauses auto-advance, the page stays fully usable
function onPointer(e) { if (S && !S.root.contains(e.target) && S.auto) { S.auto = false; paintCard(); clearTimeout(S.timer); } }

async function teardown() {
  const s = S;
  if (!s) return null;
  S = null;
  clearTimeout(s.timer);
  cancelAnimationFrame(s.raf);
  document.removeEventListener("keydown", onKey, true);
  document.removeEventListener("pointerdown", onPointer, true);
  document.removeEventListener("ce:lang", paintCard);
  document.documentElement.classList.remove("tour-on");
  const root = s.root;
  if (RM.matches) root.remove();
  else { root.classList.remove("open"); root.classList.add("closing"); setTimeout(() => root.remove(), 220); }
  foldTopics();
  return s;
}
async function restoreAsOf(s) {
  if (CE.asOf() !== s.asOf) await setAsOf(s.asOf, { quiet: true });
  if (!s.hadAsOfKey) sessionStorage.removeItem("asof");
}
// Esc / close: back to exactly where the user was
async function stop() {
  const s = await teardown();
  if (!s) return;
  const back = location.hash !== s.hash;
  const asof = restoreAsOf(s); // date first: the route below then renders once with the user's own date
  if (back) { const p = routeOnce(null, s.hash); location.replace(s.hash); await p; }
  await asof;
  scrollTo({ top: s.scroll, behavior: "instant" });
  const f = s.focus;
  if (f && f.isConnected && f !== document.body) f.focus({ preventScroll: true });
}
// last step: "Search your address"
async function finish() {
  const s = await teardown();
  if (!s) return;
  await restoreAsOf(s);
  await goHash("#/", "lookup");
  scrollTo({ top: 0, behavior: "instant" });
  const inp = await waitFor(TG.searchInput, 3000);
  if (inp && inp.matches("input")) inp.focus();
  else CE.openSearch?.();
}

// ------------------------------------------------------------------ entry points --
function mountEntries() {
  const add = (slot, where) => {
    if (!slot || $(".tour-entry", slot.parentElement || slot)) return;
    const a = document.createElement("a");
    a.href = "#/tour";
    a.className = "tour-entry";
    a.dataset.tourEntry = "1";
    a.textContent = t("entry");
    if (where === "after") slot.after(a); else slot.append(a);
  };
  const home = $('#main [data-tour-slot="home"]');
  if (home) add(home, "in");
  else { const chips = $("#main .hero .chips"); if (chips) add(chips, "after"); }
  const foot = $('[data-tour-slot="footer"]') || $(".footer-links");
  if (foot && !$(".tour-entry", foot)) add(foot, "in");
  $$(".tour-entry").forEach((a) => { a.textContent = t("entry"); });
}
document.addEventListener("click", (e) => {
  const a = e.target.closest("[data-tour-entry]");
  if (!a) return;
  e.preventDefault();
  start();
});

if (CE) {
  CE.addRoute("tour", async () => { start({ from: "#/" }); });
  document.addEventListener("ce:route", mountEntries);
  document.addEventListener("ce:lang", mountEntries);
  mountEntries();
}
window.CE_TOUR = { start: () => start(), stop: () => stop(), running: () => !!S };
