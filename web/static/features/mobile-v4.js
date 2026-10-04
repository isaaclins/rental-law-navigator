// Phones, redesign v4 (features/mobile-v4.css): the header hides on scroll down and comes back on scroll up, and a few
// small pieces the closed cards show (the rent card's why line and source, the double-check flag, the photo dots).
// The extra nodes are aria-hidden copies of text that is already on the page; outside phones the CSS hides them.
const MQ = matchMedia("(max-width: 599px), (pointer: coarse) and (max-height: 500px)");
const root = document.documentElement;
const nav = document.getElementById("nav");

// ---------------------------------------------------------------- header: away on scroll down, back on scroll up
if (nav) {
  let y0 = scrollY;
  const away = (on) => root.classList.toggle("mv4-away", on);
  const strip = document.querySelector("body > .strip");
  const measure = () => {
    root.style.setProperty("--mv4-hide", `${nav.offsetHeight - (parseFloat(getComputedStyle(nav).paddingTop) || 0) + 2}px`);
    root.style.setProperty("--mv4-strip", `${strip && getComputedStyle(strip).display !== "none" ? strip.offsetHeight : 0}px`);
  };
  new ResizeObserver(measure).observe(nav);
  if (strip) new ResizeObserver(measure).observe(strip);
  const busy = () => root.classList.contains("tour-on") || root.classList.contains("locked") || nav.contains(document.activeElement)
    || !!document.querySelector(".modal:not([hidden]), .cmdk:not([hidden])");
  const onScroll = () => {
    const y = scrollY, dy = y - y0;
    const limit = (document.querySelector("body > .strip")?.offsetHeight || 0) + nav.offsetHeight + 40; // offsetTop moves while stuck
    if (!MQ.matches || busy() || y < limit) { away(false); y0 = y; return; }
    if (Math.abs(dy) < 6) return;
    away(dy > 0);
    y0 = y;
  };
  addEventListener("scroll", onScroll, { passive: true });
  addEventListener("resize", measure, { passive: true });
  nav.addEventListener("focusin", () => away(false));
  MQ.addEventListener?.("change", () => { away(false); measure(); });
  measure();
}

// iOS Safari shows :active (the pressed card) only once a touchstart listener exists
document.addEventListener("touchstart", () => {}, { passive: true });

// ---------------------------------------------------------------- closed cards and the home photo
// a long host in a pill: its last two labels (leginfo.legislature.ca.gov -> ca.gov, codelibrary.amlegal.com -> amlegal.com)
const shortHost = (txt) => txt.replace(/\b(?:[a-z0-9-]+\.)+([a-z0-9-]+\.[a-z]{2,})\b/gi, "$1");
// the source chip keeps the host whole: when the words and the host don't fit on one line, the words step aside
const SRC_SHORT = { en: "Quoted", es: "Textual" }; // when "Word for word" / "Palabra por palabra" doesn't fit next to the host
const fitSrc = (el) => {
  if (!el || !el.offsetWidth) return;
  const w = el.querySelector(".mv4-src-w");
  const over = () => el.scrollWidth > el.clientWidth + 1 || (w && w.scrollWidth > w.clientWidth + 1);
  el.classList.remove("tight");
  if (w) { w.dataset.full ??= w.textContent; w.textContent = w.dataset.full; }
  if (w && over()) w.textContent = SRC_SHORT[document.documentElement.lang] || SRC_SHORT.en;
  if (over()) el.classList.add("tight");
};
addEventListener("resize", () => document.querySelectorAll(".mv4-src").forEach(fitSrc), { passive: true });
document.fonts?.ready.then(() => document.querySelectorAll(".mv4-src").forEach(fitSrc));
const ICON_CHECK = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12.5 4.2 4.2L19 7"/></svg>';
function enhance() {
  const m = document.getElementById("main");
  if (!m) return;
  // the double-check flag: the dot's own label, as words on the closed card
  for (const d of m.querySelectorAll(".topics.group > .topic > summary > .sdot.sd-check")) {
    const main = d.parentElement.querySelector(".topic-main");
    const label = d.getAttribute("aria-label") || "";
    const f = main?.querySelector(":scope > .mv4-flag");
    if (!main || !label) continue;
    if (f) { if (f.textContent !== label) f.textContent = label; continue; }
    main.insertAdjacentHTML("beforeend", `<span class="mv4-flag" aria-hidden="true"></span>`);
    main.lastElementChild.textContent = label;
  }
  // the rent answer leads the address page: its why line and where the words come from, on the closed card
  const lead = m.querySelector("article.addr .answers .topics.group > #t-rent_increase_limits");
  if (lead && !lead.classList.contains("mv4-lead")) {
    lead.classList.add("mv4-lead");
    const main = lead.querySelector(":scope > summary .topic-main");
    const why = lead.querySelector(":scope > .topic-body > .why")?.textContent.trim();
    const src = lead.querySelector(".l3-ok span")?.textContent.split(" · ")[0].trim();
    if (main && why) {
      main.insertAdjacentHTML("beforeend", `<span class="mv4-why" aria-hidden="true"></span>`);
      main.lastElementChild.textContent = why;
    }
    if (main && src) { // "Word for word on lacity.gov" -> [Word for word] · [lacity.gov]: the host is never cut
      const m2 = shortHost(src).match(/^(.*?)\s+(?:on|en)\s+(\S+)$/);
      main.insertAdjacentHTML("beforeend", `<span class="mv4-src" aria-hidden="true">${ICON_CHECK}<span class="mv4-src-w"></span><span class="mv4-src-h"></span></span>`);
      const el = main.lastElementChild;
      el.querySelector(".mv4-src-w").textContent = m2 ? m2[1] : shortHost(src);
      el.querySelector(".mv4-src-h").textContent = m2 ? m2[2] : "";
      fitSrc(el);
    }
  }
  // the photo's answer chips: the same status colour as their card's dot
  for (const sp of m.querySelectorAll(".ahero .spot[data-goto]")) {
    const d = document.getElementById(sp.dataset.goto)?.querySelector(":scope > summary > .sdot");
    const k = d ? (["ok", "ask", "later"].find((x) => d.classList.contains("sd-" + x)) || "none") : "";
    if (k && sp.dataset.sd !== k) sp.dataset.sd = k;
  }
  // home: one dot per building on the photo, the current one long
  const slides = m.querySelector(".hero .slides");
  if (slides && !slides.querySelector(".mv4-dots")) {
    const n = slides.querySelectorAll(".slide").length;
    if (n > 1) {
      slides.insertAdjacentHTML("beforeend", `<span class="mv4-dots" aria-hidden="true">${"<i></i>".repeat(n)}</span>`);
      const dots = [...slides.querySelectorAll(".mv4-dots i")];
      const paint = () => slides.querySelectorAll(".slide").forEach((s, i) => dots[i]?.classList.toggle("on", s.classList.contains("on")));
      paint();
      new MutationObserver(paint).observe(slides, { subtree: true, attributes: true, attributeFilter: ["class"] });
    }
  }
}
const m = document.getElementById("main");
if (m && !m.hasAttribute("data-share-page")) {
  let q = 0;
  const later = () => { if (!q) q = requestAnimationFrame(() => { q = 0; enhance(); }); };
  new MutationObserver(later).observe(m, { childList: true, subtree: true });
  document.addEventListener("ce:route", later);
  later();
}

// ---------------------------------------------------------------- shared answer: the law open under the headline
// shared answer on a phone: the source link's host short enough for its pill (the full address stays in href)
if (MQ.matches) for (const a of document.querySelectorAll("[data-share-page] .sh-cite > a")) {
  const n = [...a.childNodes].find((x) => x.nodeType === 3 && x.textContent.trim());
  if (n) n.textContent = shortHost(n.textContent);
}
const law = document.querySelector("[data-share-page] .sh-law");
if (law && MQ.matches) law.open = true;

// ---------------------------------------------------------------- tab bar: the pill moves on the tap itself
// The pill is drawn on a[aria-current] (features/mobile-v4.css); setting it here, before the route works, means the
// new page never paints with the pill on the old tab. syncHeader() sets the same value a moment later.
document.querySelector(".tabs")?.addEventListener("click", (e) => {
  const a = e.target.closest("a[data-route]");
  if (!a || !MQ.matches || e.defaultPrevented || e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  for (const x of document.querySelectorAll(".tabs a[aria-current]")) if (x !== a) x.removeAttribute("aria-current");
  a.setAttribute("aria-current", "page");
});
