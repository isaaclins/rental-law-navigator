// Clause & Effect · search typeaheads with the phone keyboard open (iOS Safari first).
// The home search (#hq → #hs), the add-a-building search (My properties, #mp-find → #mp-ta-list) and the search
// sheet (#cmdk-q → #cmdk-list). On phones, on focus: the field moves to the top of the visible area (below the sticky
// header), and the open list is sized to what the keyboard leaves (window.visualViewport), so it scrolls inside
// itself instead of running under the keyboard; it follows visualViewport resize/scroll while the field has focus.
// The fields are type=search with autocomplete/autocorrect/autocapitalize off and non-address names, so iOS does not
// offer contact AutoFill over the list (markup in app.js, index.html, properties.js).

const FIELDS = [
  { input: "#hq", list: "#hs" },
  { input: "#mp-find", list: "#mp-ta-list" },
  { input: "#cmdk-q", list: "#cmdk-list", sheet: "#cmdk" },
];
const GAP = 8;
const vv = window.visualViewport;
const phone = () => matchMedia("(max-width: 640px), (pointer: coarse)").matches;
const RM = matchMedia("(prefers-reduced-motion: reduce)");

let cur = null; // { input, list, sheet }
let raf = 0, mo = null, settleT = 0;

const view = () => vv ? { top: vv.offsetTop, height: vv.height } : { top: 0, height: innerHeight };
// the sticky header covers the top of the page; the field goes just below it
function headerBottom() {
  const nav = document.querySelector("#nav");
  if (!nav) return 0;
  const cs = getComputedStyle(nav);
  if (cs.position !== "sticky" && cs.position !== "fixed") return 0;
  return (parseFloat(cs.top) || 0) + nav.offsetHeight;
}

// bring the field to the top of the visible area (page fields only; the sheet is fixed and fills the screen)
function lift() {
  if (!cur || cur.sheet) return;
  const box = cur.input.closest("form") || cur.input;
  const r = box.getBoundingClientRect(), v = view();
  const want = v.top + headerBottom() + GAP; // where the field's top should sit, in layout-viewport coordinates
  const dy = r.top - want;
  if (Math.abs(dy) < 2) return;
  scrollTo({ top: Math.max(0, scrollY + dy), behavior: RM.matches ? "instant" : "smooth" });
}

// fit the list (or the whole sheet) into what the keyboard leaves
function fit() {
  raf = 0;
  if (!cur) return;
  const v = view();
  if (cur.sheet) {
    const sh = document.querySelector(cur.sheet);
    if (!sh || sh.hidden) return;
    sh.style.top = v.top + "px";
    sh.style.height = v.height + "px";
    sh.style.bottom = "auto";
    return;
  }
  const list = cur.list;
  if (list.hidden) return;
  const top = list.getBoundingClientRect().top;
  const room = Math.floor(v.top + v.height - top - GAP);
  list.style.maxHeight = Math.max(120, room) + "px";
}
const queue = () => { if (!raf) raf = requestAnimationFrame(fit); };

function clear(c) {
  if (!c) return;
  c.list.style.maxHeight = "";
  if (c.sheet) { const sh = document.querySelector(c.sheet); if (sh) { sh.style.top = ""; sh.style.height = ""; sh.style.bottom = ""; } }
  c.list.classList.remove("ta-fit");
}

function onFocus(e) {
  if (!phone()) return;
  const f = FIELDS.find((x) => e.target.matches?.(x.input));
  if (!f) return;
  const list = document.querySelector(f.list);
  if (!list) return;
  if (cur && cur.input !== e.target) clear(cur);
  cur = { input: e.target, list, sheet: f.sheet || null };
  list.classList.add("ta-fit");
  mo?.disconnect();
  mo = new MutationObserver(queue); // the list opens, closes and refills as the user types
  mo.observe(list, { attributes: true, attributeFilter: ["hidden"], childList: true });
  queue();
  // the keyboard takes a moment to come up: lift once the visual viewport has shrunk (or after a short wait)
  clearTimeout(settleT);
  const h0 = view().height;
  let tries = 0;
  const wait = () => {
    if (!cur) return;
    if (view().height < h0 - 40 || ++tries > 12) { lift(); queue(); return; }
    settleT = setTimeout(wait, 50);
  };
  settleT = setTimeout(wait, 50);
}
function onBlur(e) {
  if (!cur || e.target !== cur.input) return;
  const c = cur;
  setTimeout(() => { if (cur === c && document.activeElement !== c.input) { clear(c); cur = null; mo?.disconnect(); } }, 200);
}

document.addEventListener("focusin", onFocus);
document.addEventListener("focusout", onBlur);
vv?.addEventListener("resize", queue);
vv?.addEventListener("scroll", queue);
addEventListener("scroll", queue, { passive: true });
window.CE_TA = { fit: () => fit(), lift: () => lift() };
