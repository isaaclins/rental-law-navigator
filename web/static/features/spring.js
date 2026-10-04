// Spring-drag: every small decorative image with a fixed spot can be grabbed (mouse, pen or touch), dragged freely and
// let go; it springs home with a real damped spring, the parameters of Josh Comeau's demo
// (joshwcomeau.com/animation/a-friendly-introduction-to-spring-physics: mass 0.5, tension 168.75, friction 7.3).
// The element stays in flow: only the individual `translate`, `rotate` and `scale` properties and a drop-shadow
// change, so existing `transform`s (entrance pops, hover scales) keep working and nothing shifts.
// Opt in: the selector list below, or `data-spring` on any element (`data-spring="off"` opts out). A MutationObserver
// marks newly rendered elements. An opted-in image whose parent only clips it (a round frame with overflow: hidden,
// like the page-head objects' .ph-art) moves together with that frame.
// Physics: F = -tension * x - friction * v, a = F / mass, semi-implicit Euler in fixed 2 ms sub-steps per animation
// frame (frame-rate independent); the release velocity is carried into the spring. Tilt (from the drag velocity),
// scale (1.06 while held) and the shadow follow the same spring. prefers-reduced-motion: no tilt, no oscillation
// (it snaps home on release). A press without 4 px of movement stays a click.
const SPRING = { mass: 0.5, tension: 168.75, friction: 7.3 };
const SEL = [
  "[data-spring]:not([data-spring='off'])",
  ".s-nav, .s-ok", // the arrow and check chips in the home statement (its image chips carry data-spring)
  ".ask-ichip", // the round chips in the Ask statement
  ".ck-art", // the scales / shield sticker in the rent-check verdict
  ".ck-empty > img",
  ".mk", // map city photo markers (a click still selects the city)
  ".mini > img", // the small building photo in the address side card
  ".src-hero > img", // the statue on Sources (a background: see BG)
].join(", ");
// Background images (data-spring="bg", the Sources statue, or a positioned image covering a large part of its
// container) keep their stacking order while dragged: they move under the text and cards, clipped by their container,
// with no lift shadow. Foreground chips, stickers, page-head objects and map markers rise above their neighbours.
const BG = "[data-spring='bg'], .src-hero > img";
function isBg(el) {
  if (el.matches(BG)) return true;
  const cs = getComputedStyle(el), p = el.offsetParent;
  if (cs.position !== "absolute" || !p) return false;
  return el.offsetWidth * el.offsetHeight > 0.35 * p.clientWidth * p.clientHeight;
}
const OFF = "[data-spring='off']";
const STEP = 1 / 500; // s, fixed sub-step
const THRESHOLD = 4; // px before a press becomes a drag
const HOLD = 120; // ms: on touch, a hold this long grabs (then vertical moves drag instead of scrolling)
const HELD_SCALE = 1.06;
const MAX_TILT = 9; // deg
const reduced = matchMedia("(prefers-reduced-motion: reduce)");

// ------------------------------------------------------------------ physics
// one body per element: x, y (px), r (deg), s (scale - 1), l (lift 0..1), each with its velocity
const bodies = new Map();
let raf = 0, last = 0, acc = 0;

function body(el) {
  let b = bodies.get(el);
  if (!b) {
    b = { el, x: 0, y: 0, vx: 0, vy: 0, r: 0, vr: 0, s: 0, vs: 0, l: 0, vl: 0, held: false, tilt: 0, z: null };
    bodies.set(el, b);
    lift(el, b);
  }
  return b;
}
function spring1(pos, vel, target, h) {
  const a = (-SPRING.tension * (pos - target) - SPRING.friction * vel) / SPRING.mass;
  vel += a * h; // semi-implicit Euler: velocity first, then position with the new velocity
  return [pos + vel * h, vel];
}
function step(b, h) {
  if (!b.held) {
    [b.x, b.vx] = spring1(b.x, b.vx, 0, h);
    [b.y, b.vy] = spring1(b.y, b.vy, 0, h);
  }
  [b.r, b.vr] = spring1(b.r, b.vr, b.held && !reduced.matches ? b.tilt : 0, h);
  [b.s, b.vs] = spring1(b.s, b.vs, b.held ? HELD_SCALE - 1 : 0, h);
  [b.l, b.vl] = spring1(b.l, b.vl, b.held ? 1 : 0, h);
}
const still = (b) =>
  !b.held && Math.abs(b.x) < 0.05 && Math.abs(b.y) < 0.05 && Math.hypot(b.vx, b.vy) < 2 &&
  Math.abs(b.r) < 0.01 && Math.abs(b.vr) < 0.5 && Math.abs(b.s) < 0.0004 && Math.abs(b.vs) < 0.01 &&
  Math.abs(b.l) < 0.004 && Math.abs(b.vl) < 0.05;

// Connectors: a line drawn from a fixed point to the element (the map markers' leader lines to their city dots, or
// any element with data-spring-line="<selector of its lines>") stretches and turns with it every frame, the fixed end
// staying put; companions (the selected marker's city name, or data-spring-with="<selector>") move along. Pure
// transforms: the line keeps its box and only gets rotate() scaleX(), so nothing is laid out again.
function linksOf(el) {
  const line = el.dataset.springLine || (el.matches(".mk") && el.dataset.city ? `.mk-line[data-for="${CSS.escape(el.dataset.city)}"]` : "");
  const mate = el.dataset.springWith || (el.matches('.mk[aria-pressed="true"]') ? ".mk-name" : "");
  return { lines: line ? [...document.querySelectorAll(line)] : [], mates: mate ? [...document.querySelectorAll(mate)] : [] };
}
function bindLinks(b) {
  const { lines, mates } = linksOf(b.el);
  const r = b.el.getBoundingClientRect();
  const cx = r.left + r.width / 2 - b.x, cy = r.top + r.height / 2 - b.y; // its centre at home (rotate/scale keep it)
  b.lines = lines.map((line) => {
    const p = line.offsetParent, pr = p ? p.getBoundingClientRect() : { left: 0, top: 0 };
    const sx = pr.left + (p?.clientLeft || 0) + line.offsetLeft, sy = pr.top + (p?.clientTop || 0) + line.offsetTop + line.offsetHeight / 2;
    return { line, t: line.style.transform, vx: cx - sx, vy: cy - sy, l0: line.offsetWidth || 1 };
  });
  // a companion moves along only if it sits at the element (on phones the city name is placed elsewhere)
  const near = (m) => { const q = m.getBoundingClientRect(); return Math.hypot(q.left + q.width / 2 - cx, q.top + q.height / 2 - cy) < Math.max(r.width, r.height) * 1.5; };
  b.mates = mates.filter((m) => b.el.dataset.springWith || near(m)).map((m) => ({ m, tr: m.style.translate }));
}
function paintLinks(b) {
  if (b.lines.some((L) => !L.line.isConnected)) { unbindLinks(b); bindLinks(b); } // the map re-laid its lines
  for (const L of b.lines) {
    const vx = L.vx + b.x, vy = L.vy + b.y;
    L.line.style.transform = `rotate(${Math.atan2(vy, vx).toFixed(5)}rad) scaleX(${(Math.hypot(vx, vy) / L.l0).toFixed(5)})`;
  }
  for (const M of b.mates) M.m.style.translate = `${b.x.toFixed(2)}px ${b.y.toFixed(2)}px`;
}
function unbindLinks(b) {
  for (const L of b.lines || []) if (L.line.isConnected) L.line.style.transform = L.t;
  for (const M of b.mates || []) M.m.style.translate = M.tr;
}
function paint(b) {
  paintLinks(b);
  const st = b.el.style, l = Math.max(0, b.l);
  st.translate = `${b.x.toFixed(2)}px ${b.y.toFixed(2)}px`;
  st.rotate = `${b.r.toFixed(3)}deg`;
  st.scale = (1 + b.s).toFixed(4);
  st.filter = !b.bg && l > 0.002 ? `drop-shadow(0 ${(16 * l).toFixed(1)}px ${(22 * l).toFixed(1)}px rgb(0 12 31 / ${(0.24 * l).toFixed(3)}))` : "";
}
function lift(el, b) {
  // raise it above its neighbours while it moves; static elements need a position for z-index to apply
  b.z = { z: el.style.zIndex, p: el.style.position, w: el.style.willChange };
  b.bg = isBg(el);
  bindLinks(b);
  if (!b.bg) {
    if (getComputedStyle(el).position === "static") el.style.position = "relative";
    el.style.zIndex = "60";
  }
  el.style.willChange = "translate, rotate, scale, filter";
  el.classList.add("is-springing");
}
function settle(b) {
  unbindLinks(b);
  const st = b.el.style;
  st.translate = st.rotate = st.scale = st.filter = "";
  st.zIndex = b.z.z; st.position = b.z.p; st.willChange = b.z.w;
  b.el.classList.remove("is-springing");
  bodies.delete(b.el);
}
function frame(now) {
  raf = 0;
  acc += Math.min(0.064, (now - last) / 1000); // a long gap (background tab) can't explode the integration
  last = now;
  for (; acc >= STEP; acc -= STEP) for (const b of bodies.values()) step(b, STEP);
  for (const b of bodies.values()) {
    if (!b.el.isConnected) { bodies.delete(b.el); continue; }
    if (still(b)) settle(b);
    else paint(b);
  }
  if (bodies.size) raf = requestAnimationFrame(frame);
}
function run() {
  if (!raf) { last = performance.now(); acc = 0; raf = requestAnimationFrame(frame); }
}

// ------------------------------------------------------------------ pointer
let g = null; // the current grab
function samplesVelocity(s) {
  // px/s over the last ~80 ms of movement; 0 if the pointer rested before letting go
  const end = s[s.length - 1];
  if (!end || performance.now() - end.t > 90) return [0, 0];
  let i = s.length - 1;
  while (i > 0 && end.t - s[i - 1].t < 80) i--;
  const a = s[Math.max(0, i - 1)], dt = (end.t - a.t) / 1000;
  if (dt <= 0.004) return [0, 0];
  let vx = (end.x - a.x) / dt, vy = (end.y - a.y) / dt;
  const v = Math.hypot(vx, vy), max = 4000;
  if (v > max) { vx *= max / v; vy *= max / v; }
  return [vx, vy];
}
function grab() {
  const b = body(g.el);
  g.b = b;
  g.bx = b.x; g.by = b.y; // grabbing it mid-flight continues from where it is
  g.ox = g.sx; g.oy = g.sy; // the element follows the pointer exactly from where it was pressed
  b.held = true;
  b.vx = b.vy = 0;
  g.dragging = true;
  try { g.el.setPointerCapture(g.id); } catch { /* the pointer is gone already */ }
  document.documentElement.classList.add("spring-grabbing");
  run();
}
function resolve(node) {
  // the element that moves: the matched one, or the frame that only clips it (marked .ce-spring once resolved)
  const known = node?.closest?.(".ce-spring");
  if (known) return known.closest(OFF) ? null : known;
  let el = node?.closest?.(SEL);
  if (!el || el.closest(OFF)) return null;
  if (el.matches(BG)) return el; // a background stays inside (and clipped by) its frame
  for (let p = el.parentElement; p && p.childElementCount === 1 && p.id !== "main"; el = p, p = p.parentElement) {
    const cs = getComputedStyle(p);
    if (cs.overflow === "visible" && cs.clipPath === "none") break;
  }
  return el;
}
// on phones and touch, a background never moves: a press on it is always the page's (scroll, tap)
const phone = matchMedia("(max-width: 640px), (pointer: coarse)");
function onDown(e) {
  if (g || !e.isPrimary || (e.pointerType === "mouse" && e.button !== 0)) return;
  const el = resolve(e.target);
  if (!el || ((e.pointerType === "touch" || phone.matches) && isBg(el))) return;
  g = { el, id: e.pointerId, touch: e.pointerType === "touch", sx: e.clientX, sy: e.clientY, lx: e.clientX, ly: e.clientY,
    dragging: false, moved: false, armed: e.pointerType !== "touch", samples: [], timer: 0 };
  if (g.touch) {
    const mine = g;
    g.timer = setTimeout(() => { if (g === mine && !g.dragging) { g.armed = true; grab(); } }, HOLD);
  }
}
function onMove(e) {
  if (!g || e.pointerId !== g.id) return;
  g.lx = e.clientX; g.ly = e.clientY;
  const dx = e.clientX - g.sx, dy = e.clientY - g.sy;
  if (!g.moved && Math.hypot(dx, dy) >= THRESHOLD) {
    // a touch that starts mostly vertical is a page scroll (touch-action: pan-y lets the browser take it)
    if (g.touch && !g.armed && Math.abs(dx) < Math.abs(dy) * 0.58) return end(false);
    g.moved = true;
    if (!g.dragging) grab();
  }
  if (!g.dragging || !g.moved) return;
  const b = g.b, t = performance.now();
  b.x = g.bx + (e.clientX - g.ox);
  b.y = g.by + (e.clientY - g.oy);
  g.samples.push({ t, x: b.x, y: b.y });
  if (g.samples.length > 12) g.samples.shift();
  const [vx] = samplesVelocity(g.samples);
  b.tilt = Math.max(-MAX_TILT, Math.min(MAX_TILT, vx * 0.006 + b.x * 0.02)); // leans into the drag
  run();
}
function end(released) {
  if (!g) return;
  clearTimeout(g.timer);
  const was = g;
  g = null;
  document.documentElement.classList.remove("spring-grabbing");
  if (!was.dragging) return;
  const b = was.b;
  b.held = false;
  if (reduced.matches) { b.x = b.y = b.vx = b.vy = b.r = b.vr = b.s = b.vs = b.l = b.vl = 0; } // home, no bounce
  else if (released) [b.vx, b.vy] = samplesVelocity(was.samples);
  run();
  if (was.moved) swallowClick();
}
function swallowClick() {
  // the click that follows a drag must not open the chip's link or select the map city
  const kill = (e) => { e.stopPropagation(); e.preventDefault(); };
  addEventListener("click", kill, { capture: true, once: true });
  setTimeout(() => removeEventListener("click", kill, { capture: true }), 350);
}
addEventListener("pointerdown", onDown, { passive: true });
addEventListener("pointermove", onMove, { passive: true });
addEventListener("pointerup", (e) => { if (g && e.pointerId === g.id) end(true); });
addEventListener("pointercancel", (e) => { if (g && e.pointerId === g.id) end(false); });
// an interrupted gesture (capture lost, touch cancelled, tab hidden) springs home instead of leaving a transform
// (only our own capture: taking it over from the browser's implicit touch capture fires this for the old target)
addEventListener("lostpointercapture", (e) => { if (g?.dragging && e.pointerId === g.id && e.target === g.el) end(false); }, true);
addEventListener("touchcancel", () => { if (g?.touch) end(false); });
addEventListener("blur", () => end(false));
document.addEventListener("visibilitychange", () => { if (document.hidden) end(false); });
// once a touch drag owns the gesture, the page must not scroll under it
addEventListener("touchmove", (e) => { if (g?.touch && (g.dragging || g.armed)) e.preventDefault(); }, { passive: false });
addEventListener("dragstart", (e) => { if (e.target.closest?.(".ce-spring, " + SEL)) e.preventDefault(); });
addEventListener("contextmenu", (e) => { if (g?.touch && e.target.closest?.(SEL)) e.preventDefault(); });

// ------------------------------------------------------------------ marking
function mark(node) {
  const el = resolve(node);
  if (!el || el.classList.contains("ce-spring")) return;
  el.classList.add("ce-spring");
  if (isBg(el)) el.classList.add("ce-spring-bg");
  for (const img of el.tagName === "IMG" ? [el] : el.querySelectorAll("img")) img.draggable = false;
  const interactive = el.matches("a, button, [tabindex], input, select, textarea") || el.querySelector("a, button, [tabindex]");
  if (!interactive && !el.closest("[aria-hidden='true']") && (el.tagName !== "IMG" || !el.getAttribute("alt"))) el.setAttribute("aria-hidden", "true");
}
let queued = 0;
function scan() {
  queued = 0;
  for (const el of document.querySelectorAll(SEL)) mark(el);
}
const later = () => { if (!queued) queued = requestAnimationFrame(scan); };
function start() {
  scan();
  new MutationObserver(later).observe(document.body, { childList: true, subtree: true });
  addEventListener("resize", later, { passive: true });
  document.addEventListener("ce:route", later);
}
if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
else start();

// for tests and other modules: the parameters and a way to opt elements in or out at runtime
window.CESpring = { params: { ...SPRING }, selector: SEL, rescan: scan };
