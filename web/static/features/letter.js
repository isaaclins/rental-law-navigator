// Letter to the landlord (#122). Opened from a rent check whose verdict is "too high": #/check/<addressId>/letter
// (or #/check/letter for any address). POST /api/letter fills a fixed template from the engine's check result (no AI
// writing): every number, quote and link is the engine's. The reader fills in [Your name], [Unit] and
// [Landlord's name] here; those values live only in this page (never sent, never stored).
// Copy, Print (print CSS: the letter only), PDF (generated here, in the browser) and, on phones, the share sheet.

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const CE = window.CE;

{ // the stylesheet travels with the module
  const l = document.createElement("link");
  l.rel = "stylesheet"; l.href = new URL("./letter.css", import.meta.url).href;
  document.head.appendChild(l);
}

const EN = {
  cta: "Write a letter to my landlord", cta_sub: "Ready in a second. English or Spanish.", new: "New",
  back: "Check a rent increase", h: "Letter to your landlord", h_s: "Your letter",
  side_h: "What your letter says", side_p: "Filled in from your rent check. No AI writing, same answer every time.",
  copy: "Copy", print: "Print", pdf: "PDF", share: "Send…", copied: "Letter copied", saved: "PDF saved",
  hint: "Fill in the <mark>[yellow]</mark> parts. They stay on this device.", nla: "Not legal advice.",
  lang_g: "Language of the letter", loading: "Writing your letter…", err: "Something went wrong. Try again.",
  busy: "Too many checks. Wait a minute.",
};
const ES = {
  cta: "Escribir una carta a mi arrendador", cta_sub: "Lista en un segundo. En inglés o en español.", new: "Nuevo",
  back: "Revisar un aumento de renta", h: "Carta a su arrendador", h_s: "Su carta",
  side_h: "Qué dice su carta", side_p: "Completada con su revisión de renta. Sin escritura por IA: la misma respuesta cada vez.",
  copy: "Copiar", print: "Imprimir", pdf: "PDF", share: "Enviar…", copied: "Carta copiada", saved: "PDF guardado",
  hint: "Complete las partes en <mark>[amarillo]</mark>. Se quedan en este dispositivo.", nla: "No es asesoría legal.",
  lang_g: "Idioma de la carta", loading: "Escribiendo su carta…", err: "Algo salió mal. Inténtelo de nuevo.",
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
const vals = { name: "", unit: "", landlord: "" }; // what the reader types: never sent, never stored
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
export function toText(d, v = vals) {
  return blocksOf(d).map((b) => b.s.map((s) => (s.br ? "\n" : s.f ? v[s.f] || d.fields[s.f] : s.href || s.t)).join("")).join("\n\n") + "\n";
}

// A one-file PDF writer for this letter: Helvetica (the PDF base fonts, WinAnsi), US Letter, links as annotations.
// Line breaks are measured with the browser's Helvetica/Arial metrics (Arial and Liberation Sans share them).
const WIN = { "“": 0x93, "”": 0x94, "‘": 0x91, "’": 0x92, "–": 0x96, "—": 0x97, "…": 0x85, "€": 0x80, "•": 0x95 };
const winAnsi = (s) => [...s.replace(/→/g, "->")].map((ch) => { const c = ch.codePointAt(0); return c < 256 ? ch : WIN[ch] ? String.fromCharCode(WIN[ch]) : "?"; }).join("");
const pdfStr = (s) => "(" + winAnsi(s).replace(/[\\()]/g, (m) => "\\" + m) + ")";
const ctx2d = document.createElement("canvas").getContext("2d");
export function letterPdf(d, v = vals) {
  const PW = 612, PH = 792, M = 72, MAXW = PW - 2 * M;
  const FONT = { r: "/F1", b: "/F2", i: "/F3" };
  const css = { r: "", b: "bold ", i: "italic " };
  const width = (s, f, size) => { ctx2d.font = `${css[f]}${size}px Helvetica, Arial, "Liberation Sans", sans-serif`; return ctx2d.measureText(s).width; };
  const pages = [[]], annots = [[]];
  let y = PH - M;
  const newPage = () => { pages.push([]); annots.push([]); y = PH - M; };
  for (const b of blocksOf(d)) {
    const quote = b.k === "quote", src = b.k === "src";
    const size = src ? 9 : quote ? 11 : 11, lead = src ? 12 : 15.5, indent = quote ? 16 : 0;
    // runs -> words with their font
    const words = [[]];
    for (const s of b.s) {
      if (s.br) { words.push([]); continue; }
      const f = s.b || b.k === "title" ? "b" : quote ? "i" : "r";
      const text = s.f ? v[s.f] || "_".repeat(s.f === "unit" ? 8 : 18) : s.t;
      for (const part of text.split(/(\s+)/)) if (part) words[words.length - 1].push({ text: part, f, href: s.href });
    }
    const lines = [];
    for (const hard of words) {
      let line = [], w = 0;
      for (const wd of hard) {
        const ww = width(wd.text, wd.f, size);
        if (/^\s+$/.test(wd.text)) { if (line.length) { line.push({ ...wd, w: ww }); w += ww; } continue; }
        if (w + ww > MAXW - indent && line.length) {
          while (line.length && /^\s+$/.test(line[line.length - 1].text)) w -= line.pop().w;
          lines.push(line); line = []; w = 0;
        }
        line.push({ ...wd, w: ww }); w += ww;
      }
      lines.push(line);
    }
    if (y - lines.length * lead < M) newPage();
    const top = y;
    for (const line of lines) {
      let x = M + indent;
      if (b.k === "title") x = M + (MAXW - line.reduce((a, wd) => a + wd.w, 0)) / 2;
      const grey = src ? "0.38 0.4 0.44 rg" : "0 0.047 0.122 rg";
      for (const wd of line) {
        if (!/^\s+$/.test(wd.text)) {
          const col = wd.href ? "0.039 0.227 0.549 rg" : grey;
          pages.at(-1).push(`BT ${col} ${FONT[wd.f]} ${size} Tf 1 0 0 1 ${x.toFixed(2)} ${(y - size).toFixed(2)} Tm ${pdfStr(wd.text)} Tj ET`);
          if (wd.href) annots.at(-1).push({ rect: [x, y - size - 2, x + wd.w, y + 1], url: wd.href });
        }
        x += wd.w;
      }
      y -= lead;
    }
    if (quote) pages.at(-1).push(`0 0.149 0.392 RG 2 w ${M + 1} ${(top - size * 0.15).toFixed(2)} m ${M + 1} ${(y + lead - size - 3).toFixed(2)} l S`);
    y -= src ? 10 : b.k === "quote" ? 4 : 10;
  }
  // assemble
  const objs = [];
  const add = (s) => { objs.push(s); return objs.length; };
  const fonts = ["Helvetica", "Helvetica-Bold", "Helvetica-Oblique"].map((n) => add(`<< /Type /Font /Subtype /Type1 /BaseFont /${n} /Encoding /WinAnsiEncoding >>`));
  const pid = add(""); // the page tree, written once its kids are known
  const kids = [];
  pages.forEach((ops, i) => {
    const content = ops.join("\n");
    const cid = add(`<< /Length ${content.length} >>\nstream\n${content}\nendstream`);
    const aids = annots[i].map((a) => add(`<< /Type /Annot /Subtype /Link /Rect [${a.rect.map((n) => n.toFixed(2)).join(" ")}] /Border [0 0 0] /A << /S /URI /URI ${pdfStr(a.url)} >> >>`));
    kids.push(add(`<< /Type /Page /Parent ${pid} 0 R /MediaBox [0 0 ${PW} ${PH}] /Resources << /Font << /F1 ${fonts[0]} 0 R /F2 ${fonts[1]} 0 R /F3 ${fonts[2]} 0 R >> >> /Contents ${cid} 0 R${aids.length ? ` /Annots [${aids.map((n) => n + " 0 R").join(" ")}]` : ""} >>`));
  });
  objs[pid - 1] = `<< /Type /Pages /Kids [${kids.map((k) => k + " 0 R").join(" ")}] /Count ${kids.length} >>`;
  const info = add(`<< /Title ${pdfStr(d.title)} /Producer (Clause & Effect) >>`);
  const cat = add(`<< /Type /Catalog /Pages ${pid} 0 R >>`);
  let out = "%PDF-1.4\n%\xE2\xE3\xCF\xD3\n";
  const offs = [];
  objs.forEach((o, i) => { offs.push(out.length); out += `${i + 1} 0 obj\n${o}\nendobj\n`; });
  const xref = out.length;
  out += `xref\n0 ${objs.length + 1}\n0000000000 65535 f \n${offs.map((o) => String(o).padStart(10, "0") + " 00000 n \n").join("")}`;
  out += `trailer\n<< /Size ${objs.length + 1} /Root ${cat} 0 R /Info ${info} 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  const bytes = new Uint8Array(out.length);
  for (let i = 0; i < out.length; i++) bytes[i] = out.charCodeAt(i) & 255;
  return new Blob([bytes], { type: "application/pdf" });
}
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
        <div class="lt-seg" role="group" aria-label="${esc(t("lang_g"))}"><button type="button" data-ll="en" lang="en"><span class="lt-ll">English</span><span class="lt-ls">EN</span></button><button type="button" data-ll="es" lang="es"><span class="lt-ll">Español</span><span class="lt-ls">ES</span></button></div></div>
    </header>
    <div class="lt-grid">
      <div class="lt-col"><div class="lt-sheet" aria-live="polite"><p class="lt-wait">${esc(t("loading"))}</p></div>
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
}

export function bindActions(main, doc, v) {
  main.addEventListener("click", async (e) => {
    const b = e.target.closest("[data-act]");
    if (!b) return;
    const d = doc();
    if (b.dataset.act === "copy") { if (await copyText(toText(d, v))) CE.toast(t("copied")); }
    if (b.dataset.act === "print") { const tt = document.title; document.title = d.title; print(); document.title = tt; }
    if (b.dataset.act === "pdf") {
      const url = URL.createObjectURL(letterPdf(d, v));
      const a = Object.assign(document.createElement("a"), { href: url, download: fileName(d) });
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 30000);
    }
    if (b.dataset.act === "share") {
      const file = new File([letterPdf(d, v)], fileName(d), { type: "application/pdf" });
      try {
        if (navigator.canShare?.({ files: [file] })) await navigator.share({ files: [file], title: d.title });
        else await navigator.share({ title: d.title, text: toText(d, v) });
      } catch { /* the reader closed the sheet */ }
    }
  });
}
