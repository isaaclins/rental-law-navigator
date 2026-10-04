// Letter to the landlord (#122). Opened from a rent check whose verdict is "too high": #/check/<addressId>/letter
// (or #/check/letter for any address). POST /api/letter fills a fixed template from the engine's check result (no AI
// writing): every number, quote and link is the engine's. The reader fills in [Your name], [Unit] and
// [Landlord's name] here; those values live only in this page (never sent, never stored).
// Copy, Print (print CSS: the letter only), PDF (generated here, in the browser) and, on phones, the share sheet.

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const CE = window.CE;
import { sayButton, bindSay } from "./say.js";

// the stylesheet travels with the module; views await it (at most 1.2 s) so the first paint already has its layout
const cssLink = (href) => new Promise((ok) => {
  const l = document.createElement("link");
  l.rel = "stylesheet"; l.href = href; l.onload = l.onerror = () => ok();
  document.head.appendChild(l); setTimeout(ok, 1200);
});
export const cssReady = cssLink(new URL("./letter.css", import.meta.url).href);

const EN = {
  cta: "Write a letter to my landlord", cta_sub: "Ready in a second. English or Spanish.", new: "New",
  back: "Check a rent increase", h: "Letter to your landlord", h_s: "Your letter",
  side_h: "What your letter says", side_p: "Filled in from your rent check. No AI writing, same answer every time.",
  copy: "Copy", print: "Print", pdf: "PDF", share: "Send…", copied: "Letter copied", saved: "PDF saved",
  hint: "Fill in the <mark>[yellow]</mark> parts. They stay on this device.", nla: "Not legal advice.",
  lang_g: "Language of the letter", lang_l: "Letter in", loading: "Writing your letter…", err: "Something went wrong. Try again.",
  busy: "Too many checks. Wait a minute.",
};
const ES = {
  cta: "Escribir una carta a mi arrendador", cta_sub: "Lista en un segundo. En inglés o en español.", new: "Nuevo",
  back: "Revisar un aumento de renta", h: "Carta a su arrendador", h_s: "Su carta",
  side_h: "Qué dice su carta", side_p: "Completada con su revisión de renta. Sin escritura por IA: la misma respuesta cada vez.",
  copy: "Copiar", print: "Imprimir", pdf: "PDF", share: "Enviar…", copied: "Carta copiada", saved: "PDF guardado",
  hint: "Complete las partes en <mark>[amarillo]</mark>. Se quedan en este dispositivo.", nla: "No es asesoría legal.",
  lang_g: "Idioma de la carta", lang_l: "Carta en", loading: "Escribiendo su carta…", err: "Algo salió mal. Inténtelo de nuevo.",
  busy: "Demasiadas consultas. Espere un minuto.",
};
const t = (k) => (CE.lang() === "es" && ES[k]) || EN[k] || k;
const svg = (p) => `<svg class="ico" viewBox="0 0 24 24" aria-hidden="true">${p}</svg>`;
const I = {
  back: svg('<path d="m15 6-6 6 6 6"/>'),
  ext: svg('<path d="M14 5h5v5M19 5l-8 8M18 14v4a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h4"/>'),
  check: svg('<path d="m5 12 4.5 4.5L19 7"/>'),
  pen: svg('<path d="M4 20h4L19 9l-4-4L4 16v4zM13.5 6.5l4 4"/>'),
};

// ------------------------------------------------------------------ state (memory only)
const vals = { name: "", unit: "", landlord: "", landlord_street: "", landlord_city: "" }; // what the reader types: never sent, never stored
let L = { key: null, data: null, lang: null }; // data: {en, es} responses of /api/letter for the current check

const isRent = (v) => v.id === "rent" && (v.code === "over" || v.code === "over_max");
export const canWrite = (result) => !!result?.verdicts?.some(isRent);

// The entry button under the verdict (check.js puts it there when the rent is over the limit).
export function ctaHtml(href) {
  return `<div class="lt-cta"><a class="btn lt-go" href="${esc(href)}">${I.pen}<span>${esc(t("cta"))}</span></a></div>
    <p class="lt-cta-sub">${esc(t("cta_sub"))}</p>`;
}

export async function post(url, body) {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) { const e = new Error(typeof d.detail === "string" ? d.detail : ""); e.status = r.status; throw e; }
  return d;
}
const todayIso = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; };

// the landlord's address: a recipient block the browser adds to the letter (for the window envelope); never sent
const TO_FIELDS = {
  en: { landlord_street: "[Landlord's street address]", landlord_city: "[City, State ZIP]" },
  es: { landlord_street: "[Dirección del arrendador]", landlord_city: "[Ciudad, estado y código postal]" },
};
const TO_LABELS = {
  en: { landlord_street: "Landlord's street address", landlord_city: "Landlord's city, state and ZIP" },
  es: { landlord_street: "Dirección del arrendador", landlord_city: "Ciudad, estado y código postal del arrendador" },
};
const isLetter = (d) => d.letter.blocks.some((b) => b.k === "salute");
function withTo(d) {
  if (!isLetter(d) || d.letter.blocks.some((b) => b.k === "to")) return d;
  const lg = d.lang === "es" ? "es" : "en";
  const blocks = [...d.letter.blocks];
  const at = blocks.findIndex((b) => b.k === "from") + 1;
  blocks.splice(at, 0, { k: "to", s: [{ f: "landlord" }, { br: 1 }, { f: "landlord_street" }, { br: 1 }, { f: "landlord_city" }] });
  return { ...d, letter: { ...d.letter, blocks }, fields: { ...TO_FIELDS[lg], ...d.fields }, field_labels: { ...TO_LABELS[lg], ...d.field_labels } };
}

// ------------------------------------------------------------------ rendering
// segments: {t} text (b bold, href link, v a value from the engine, over: over the limit, ph: a value still missing),
// {f} a field the reader fills in, {br} a line break
function segHtml(s, fields, labels, v) {
  if (s.br) return "<br>";
  if (s.f) return `<input class="lt-f" data-f="${s.f}" type="text" autocomplete="off" spellcheck="false" placeholder="${esc(fields[s.f])}" aria-label="${esc(labels[s.f])}" value="${esc(v[s.f] || "")}"><span class="lt-fp" data-fp="${s.f}" aria-hidden="true">${esc(v[s.f] || "")}</span>`;
  if (s.href) return `<a href="${esc(s.href)}" target="_blank" rel="noopener">${esc(s.t)}</a>`;
  if (s.ph) return `<mark class="lt-ph">${esc(s.t)}</mark>`;
  if (s.v) return `<span class="lt-v${s.over ? " is-over" : ""}">${esc(s.t)}</span>`;
  return s.b ? `<strong>${esc(s.t)}</strong>` : esc(s.t);
}
export function letterHtml(d, v = vals) {
  d = withTo(d);
  return d.letter.blocks.map((b, i) => {
    const inner = b.s.map((s) => segHtml(s, d.fields, d.field_labels, v)).join("");
    const st = `style="--i:${i}"`;
    return b.k === "quote" ? `<blockquote class="lt-in lt-quote" ${st}>${inner}</blockquote>` : `<p class="lt-in lt-${b.k === "title" ? "heading" : b.k}" ${st}>${inner}</p>`;
  }).join("");
}
export function actsHtml(cls) {
  return `<div class="lt-acts ${cls}">
    <button type="button" class="btn" data-act="copy">${esc(t("copy"))}</button>
    <button type="button" class="btn lt-print" data-act="print">${esc(t("print"))}</button>
    <button type="button" class="btn lt-pdf" data-act="pdf">${esc(t("pdf"))}</button>
    <button type="button" class="btn primary lt-share" data-act="share" hidden>${esc(t("share"))}</button>
  </div>`;
}
function sideHtml(d) {
  return `<h2>${esc(t("side_h"))}</h2><p class="lt-side-p">${esc(t("side_p"))}</p>
    <ul class="lt-checks">${d.summary.map((c, i) => `<li style="--i:${i}"><span class="lt-ok">${I.check}</span><span><b>${esc(c.t)}</b><span>${esc(c.s)}</span></span></li>`).join("")}</ul>
    ${actsHtml("lt-acts-d")}
    <p class="lt-nla"><strong>${esc(t("nla"))}</strong> ${esc(d.help.line)} <a href="${esc(d.help.url)}" target="_blank" rel="noopener">${esc(d.help.name)}${I.ext}</a></p>`;
}

// inputs sized to their text (measured in a hidden span with the same font), so they read as words in the letter
export function fit(el) {
  const cs = getComputedStyle(el), m = document.createElement("span");
  m.style.cssText = `position:absolute;visibility:hidden;white-space:pre;font-family:${cs.fontFamily};font-size:${cs.fontSize};font-weight:${cs.fontWeight};letter-spacing:${cs.letterSpacing};font-feature-settings:${cs.fontFeatureSettings}`;
  m.textContent = el.value || el.placeholder;
  el.after(m);
  const w = m.getBoundingClientRect().width;
  m.remove();
  el.style.width = Math.ceil(w + parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight) + 1) + "px";
}

// ------------------------------------------------------------------ plain text and PDF
function blocksOf(d) { return d.letter.blocks; }
// what Listen reads: the letter without its source links; a field not filled in is read as its label
function sayText(d, v = vals) {
  return blocksOf(d).filter((b) => b.k !== "src").map((b) => b.s.map((s) => (s.br ? "\n" : s.f ? v[s.f] || String(d.fields[s.f] || "").replace(/[[\]]/g, "") : s.t)).join("")).join("\n\n");
}
export function toText(d, v = vals) {
  d = withTo(d);
  return d.letter.blocks.map((b) => (b.k === "to"
    ? b.s.filter((s) => s.f && v[s.f]?.trim()).map((s) => v[s.f].trim()).join("\n")
    : b.s.map((s) => (s.br ? "\n" : s.f ? v[s.f] || d.fields[s.f] : s.href || s.t)).join(""))).filter(Boolean).join("\n\n") + "\n";
}

// The PDF and the printed page: features/paper.js (loaded when a letter or notice opens, fonts included), so the
// tap on PDF or Send… builds the file at once and keeps its user gesture (iOS share sheet).
let PAPER = null;
export const paperKit = () => import("./paper.js").then(async (P) => { await P.load(); PAPER = P; return P; });
export async function letterPdf(d, v = vals) {
  const P = PAPER || (await paperKit());
  return P.pdf(P.model(d, v));
}
const pdfNow = (d, v) => (PAPER ? Promise.resolve(PAPER.pdf(PAPER.model(d, v))) : letterPdf(d, v));
export const fileName = (d) => d.title.replace(/[\\/:*?"<>|]+/g, " ").trim() + ".pdf";

export async function copyText(s) {
  try { await navigator.clipboard.writeText(s); return true; } catch {
    const ta = document.createElement("textarea"); ta.value = s; ta.setAttribute("readonly", ""); ta.style.cssText = "position:fixed;opacity:0";
    document.body.appendChild(ta); ta.select(); const ok = document.execCommand("copy"); ta.remove(); return ok;
  }
}

// ------------------------------------------------------------------ view
export const phone = () => matchMedia("(max-width: 640px)").matches;
export const canShare = () => typeof navigator.share === "function" && (phone() || matchMedia("(pointer: coarse)").matches);

export async function letterView(main, { id, S, backHref }) {
  await cssReady;
  const body = S?.body;
  if (!body || !canWrite(S.result)) { CE.navigate(backHref.slice(1)); return; }
  const key = JSON.stringify(body);
  if (L.key !== key) L = { key, data: null, lang: null };
  const ui = CE.lang();
  const lang = () => L.lang || ui;
  document.title = `${t("h")} · Clause & Effect`;
  main.innerHTML = `<article class="lt-view">
    <header class="lt-head">
      <a class="ck-back" href="${esc(backHref)}">${I.back}${esc(t("back"))}</a>
      <div class="lt-title"><h1><span class="lt-h-l">${esc(t("h"))}</span><span class="lt-h-s">${esc(t("h_s"))}</span></h1>
        <div class="lt-langs"><span class="lt-lang-l" aria-hidden="true">${esc(t("lang_l"))}</span><div class="lt-seg" role="group" aria-label="${esc(t("lang_g"))}"><button type="button" data-ll="en" lang="en"><span class="lt-ll">English</span><span class="lt-ls">EN</span></button><button type="button" data-ll="es" lang="es"><span class="lt-ll">Español</span><span class="lt-ls">ES</span></button></div></div></div>
    </header>
    <div class="lt-grid">
      <div class="lt-col">${sayButton(ui, "linkish lt-say")}<div class="lt-sheet" aria-live="polite"><p class="lt-wait">${esc(t("loading"))}</p></div>
        ${actsHtml("lt-acts-m")}<p class="lt-hint">${t("hint")}</p></div>
      <aside class="lt-side"></aside>
    </div></article>`;
  const sheet = $(".lt-sheet", main), side = $(".lt-side", main);
  try {
    if (!L.data) {
      const extra = { letter_date: todayIso(), ...(S.values?.address && !body.address_id ? { address_text: S.values.address } : {}) };
      const [en, es] = await Promise.all(["en", "es"].map((l) => post("/api/letter", { ...body, ...extra, lang: l })));
      L.data = { en, es };
    }
  } catch (e) {
    sheet.innerHTML = `<p class="lt-wait">${esc(e.status === 429 ? t("busy") : t("err"))}</p>`;
    return;
  }
  if (!main.contains(sheet)) return;
  const draw = (animate) => {
    const d = L.data[lang()];
    sheet.lang = d.lang;
    sheet.innerHTML = letterHtml(d);
    sheet.classList.toggle("lt-anim", !!animate);
    $$(".lt-seg button", main).forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.ll === d.lang)));
    $$(".lt-f", sheet).forEach(fit);
  };
  side.innerHTML = sideHtml(L.data[ui]);
  side.classList.add("lt-anim");
  draw(true);
  if (document.fonts?.ready) document.fonts.ready.then(() => $$(".lt-f", sheet).forEach(fit));
  $$(".lt-share", main).forEach((b) => (b.hidden = !canShare()));
  $(".lt-view", main).classList.toggle("lt-can-share", canShare());

  $(".lt-seg", main).addEventListener("click", (e) => {
    const b = e.target.closest("button[data-ll]");
    if (!b || b.dataset.ll === lang()) return;
    L.lang = b.dataset.ll; draw(true);
  });
  sheet.addEventListener("input", (e) => {
    const el = e.target.closest(".lt-f");
    if (!el) return;
    vals[el.dataset.f] = el.value;
    $$(`.lt-f[data-f="${el.dataset.f}"]`, sheet).forEach((x) => { if (x !== el) x.value = el.value; fit(x); });
    $$(`.lt-fp[data-fp="${el.dataset.f}"]`, sheet).forEach((x) => (x.textContent = el.value.trim())); // what prints
  });
  sheet.addEventListener("keydown", (e) => { if (e.key === "Enter" && e.target.closest(".lt-f")) { e.preventDefault(); e.target.blur(); } });
  bindActions($(".lt-view", main), () => L.data[lang()], vals);
  bindSay($(".lt-view", main), () => sayText(L.data[lang()]), lang);
}

// Print: the same document as the PDF, as HTML (.pp, letter.css @media print), refreshed before every print
// (also Ctrl+P / the browser menu)
async function printPrep(d, v) {
  const P = PAPER || (await paperKit().catch(() => null));
  const col = document.querySelector(".lt-view .lt-col");
  if (!P || !col || !d) return;
  const m = P.model(d, v);
  let box = col.querySelector(".pp-print");
  if (!box) { box = document.createElement("div"); box.className = "pp-print"; box.setAttribute("aria-hidden", "true"); col.appendChild(box); }
  box.innerHTML = P.html(m);
  let st = document.getElementById("pp-page-css");
  if (!st) { st = Object.assign(document.createElement("style"), { id: "pp-page-css" }); document.head.appendChild(st); }
  st.textContent = P.printCss(m);
}
let printDoc = null;
addEventListener("beforeprint", () => { if (printDoc && PAPER) { const [d, v] = printDoc(); if (d) printPrep(d, v); } });

export function bindActions(main, doc, v) {
  printDoc = () => { try { return [main.isConnected ? doc() : null, v]; } catch { return [null, v]; } };
  if (!PAPER) (window.requestIdleCallback || ((f) => setTimeout(f, 300)))(() => paperKit().catch(() => {}));
  main.addEventListener("click", async (e) => {
    const b = e.target.closest("[data-act]");
    if (!b) return;
    const d = doc();
    if (b.dataset.act === "copy") { if (await copyText(toText(d, v))) CE.toast(t("copied")); }
    if (b.dataset.act === "print") { const tt = document.title; document.title = d.title; await printPrep(d, v); print(); document.title = tt; }
    if (b.dataset.act === "pdf") {
      const url = URL.createObjectURL(await pdfNow(d, v));
      const a = Object.assign(document.createElement("a"), { href: url, download: fileName(d) });
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 30000);
    }
    if (b.dataset.act === "share") {
      const file = new File([await pdfNow(d, v)], fileName(d), { type: "application/pdf" });
      try {
        if (navigator.canShare?.({ files: [file] })) await navigator.share({ files: [file], title: d.title });
        else await navigator.share({ title: d.title, text: toText(d, v) });
      } catch { /* the reader closed the sheet */ }
    }
  });
}
