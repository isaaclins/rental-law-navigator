// Back pills that go back (Isaac, 2026-10-04: "why does the back button go back to a page that wasn't the last page?").
// A small in-app history (sessionStorage, this tab only) follows every route change. Every back pill in the views
// (a.ck-back on check, letter and notice, .mp-back on a My properties building) then points at the page the reader
// really came from, names it ("‹ Ask", "‹ Check a rent increase", "‹ 663 Massachusetts Ave") and goes there with history.back(),
// so the scroll position and opened topics come back too. Only a direct or deep-link load keeps the pill's own
// parent page. A step made with location.replace (picking an address inside the check) is not a new page.
// Loaded by features/check.js.

const CE = window.CE;
const KEY = "ce.hist";
const L = {
  en: { home: "Home", ask: "Ask", changes: "Changes", rules: "Rules", audit: "Sources", properties: "My properties", check: "Check a rent increase",
    letter: "Letter", notice: "Rent notice", compare: "Compare" },
  es: { home: "Inicio", ask: "Preguntar", changes: "Cambios", rules: "Reglas", audit: "Fuentes", properties: "Mis propiedades", check: "Revisar un aumento de renta",
    letter: "Carta", notice: "Aviso de renta", compare: "Comparar" },
};
const SUFFIX = { av: "Ave", "ave.": "Ave", avenue: "Ave", bl: "Blvd", blv: "Blvd", "st.": "St", "pl.": "Pl", wy: "Way" };
const streetName = (s) => String(s || "").toLowerCase().replace(/\b\w/g, (m) => m.toUpperCase()).replace(/(\s)(\S+)$/, (m, sp, w) => sp + (SUFFIX[w.toLowerCase()] || w)).replace(/(\d)(St|Nd|Rd|Th)\b/g, (m, d, x) => d + x.toLowerCase());

const here = () => location.hash && location.hash !== "#" ? location.hash : "#/";
let H = [], N = history.length;
try {
  const s = JSON.parse(sessionStorage.getItem(KEY) || "null");
  if (s && Array.isArray(s.h) && s.h.length && s.h[s.h.length - 1].h === here() && s.n === history.length) H = s.h; // a reload
} catch { /* private mode */ }
if (!H.length) H = [{ h: here() }];
const save = () => { try { sessionStorage.setItem(KEY, JSON.stringify({ h: H.slice(-30), n: N })); } catch { /* full or private */ } };
save();

// called on hashchange and before every decoration (the view may render before this module's hashchange listener runs)
function sync() {
  const h = here(), prev = H[H.length - 2];
  if (H[H.length - 1].h === h && history.length === N) return;
  if (prev && prev.h === h) H.pop(); // Back
  else if (history.length > N) H.push({ h }); // a new page
  else if (H[H.length - 1].h !== h) H[H.length - 1] = { h }; // location.replace: the same step
  N = history.length;
  save();
}
addEventListener("hashchange", sync);
// the page's own title, for routes without a fixed name
document.addEventListener("ce:route", () => { const top = H[H.length - 1]; if (top && top.h === here()) { top.title = document.title.split(" · ")[0]; save(); } });

let ADDR = null;
CE.api("/api/addresses").then((a) => { ADDR = a || []; decorate(true); }).catch(() => {});
function label(entry) {
  const w = L[CE.lang() === "es" ? "es" : "en"];
  const [view, arg, sub] = entry.h.replace(/^#\/?/, "").split(/[/?]/);
  if (!view) return w.home;
  if (view === "a" && arg) { const a = ADDR?.find((x) => x.id === decodeURIComponent(arg).toUpperCase()); return a ? streetName(a.street) : entry.title || null; }
  if (view === "check") return /letter$/i.test(entry.h) ? w.letter : w.check;
  if (w[view]) return view === "properties" && arg && entry.title ? entry.title : w[view];
  void sub;
  return entry.title || null;
}

const PILLS = "#main a.ck-back, #main .mp-back a";
function decorate(force = false) {
  sync();
  const prev = H[H.length - 2];
  for (const a of document.querySelectorAll(PILLS)) {
    if (!force && a.dataset.histAt === here()) continue;
    a.dataset.histAt = here();
    if (!prev || prev.h === here()) { delete a.dataset.hist; continue; } // a deep link: the pill keeps its parent page
    const text = label(prev);
    if (!text) continue;
    a.href = prev.h;
    a.dataset.hist = "1";
    for (const n of [...a.childNodes]) if (n.nodeType === 3 || (n.nodeType === 1 && n.tagName !== "svg")) n.remove();
    a.append(document.createTextNode(text));
  }
}
const main = document.querySelector("#main");
if (main) new MutationObserver(() => decorate()).observe(main, { childList: true, subtree: true });
document.addEventListener("ce:lang", () => setTimeout(() => decorate(true), 0));
decorate();
document.addEventListener("click", (e) => {
  const a = e.target.closest?.("a[data-hist]");
  if (!a || e.defaultPrevented || e.metaKey || e.ctrlKey || e.shiftKey || e.button) return;
  const prev = H[H.length - 2];
  if (!prev || a.getAttribute("href") !== prev.h) return;
  e.preventDefault();
  history.back();
});
