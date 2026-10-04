// The paper version of the renter letter (#122) and the landlord notice (#96): one model, two renderers.
//   model(d, v)  the document from an /api/letter or /api/notice response (d) and what the reader typed (v)
//   pdf(model)   a US Letter PDF, written here in the browser (the names never leave the device): the site's own
//                fonts embedded (Inter 400/600 + Instrument Serif, WinAnsi subsets from web/pdf_fonts.py, with
//                widths and kerning), recipient in the #10 window-envelope position, fold marks, footer with
//                page X of Y on every page, running header from page 2, the QR code as vector squares, links.
//   html(model)  the same document as HTML for the Print button (features/letter.css @media print).
// DOM-free apart from fetch. load() fetches the fonts (about 45 KB); pdf() needs them loaded (sync, so the
// share sheet on iOS keeps the tap's user gesture).

import { qr } from "./qr.js";

// ------------------------------------------------------------------ strings
const S = {
  en: {
    footer: "Prepared with Clause & Effect", nla: "Not legal advice", page: (p, n) => `Page ${p} of ${n}`,
    dear: "Dear Landlord,", cur: "Current rent", proposed: "Rent in your notice", allowed: "Allowed increase",
    top: "Highest rent allowed", above: "Above the limit", a_month: "a month", from: "from", at_most: "at most",
    cpi: (c) => `with a CPI change of ${c}`, sources: "Sources", retrieved: "Retrieved", orig: "",
    verify_h: "Check the law yourself",
    verify_p: "The rule, its official source and the day it was retrieved. Scan the code or open",
    n_cur: "Current monthly rent", n_new: "New monthly rent",
    n_inc: "Increase", n_start: "Effective date", n_period: "Notice period", n_period_v: (d) => `At least ${d} days`,
    n_lead: "Your monthly rent will increase as follows.", all_occ: "All occupants", and_occ: " and all other occupants", n_title: "Notice of Rent Increase",
    owner_l: "Owner or agent", sign_l: "Signature", given_l: "Date given", check: "Check before sending.",
  },
  es: {
    footer: "Preparado con Clause & Effect", nla: "No es asesoría legal", page: (p, n) => `Página ${p} de ${n}`,
    dear: "Estimado/a arrendador/a:", cur: "Renta actual", proposed: "Renta de su aviso", allowed: "Aumento permitido",
    top: "Renta máxima permitida", above: "Por encima del límite", a_month: "al mes", from: "desde el", at_most: "como máximo",
    cpi: (c) => `con un cambio del IPC del ${c}`, sources: "Fuentes", retrieved: "Consultado el", orig: "Texto original en inglés",
    verify_h: "Compruebe la ley usted mismo",
    verify_p: "La norma, su fuente oficial y el día en que se consultó. Escanee el código o abra",
    n_cur: "Renta mensual actual", n_new: "Renta mensual nueva",
    n_inc: "Aumento", n_start: "Fecha de inicio", n_period: "Plazo de aviso", n_period_v: (d) => `Al menos ${d} días`,
    n_lead: "Su renta mensual aumentará así:", all_occ: "Todos los ocupantes", and_occ: " y todos los demás ocupantes", n_title: "Aviso de aumento de renta",
    owner_l: "Propietario o agente", sign_l: "Firma", given_l: "Fecha de entrega", check: "Revíselo antes de enviarlo.",
  },
};

const MON_EN = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(" ");
const MON_ES = "ene feb mar abr may jun jul ago sep oct nov dic".split(" ");
const LMON_EN = "January February March April May June July August September October November December".split(" ");
const LMON_ES = "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split(" ");
const ymd = (s) => String(s || "").slice(0, 10).split("-").map(Number);
export const shortDate = (s, lang) => { const [y, m, d] = ymd(s); return lang === "es" ? `${d} ${MON_ES[m - 1]} ${y}` : `${MON_EN[m - 1]} ${d}, ${y}`; };
const longDate = (s, lang) => { const [y, m, d] = ymd(s); return lang === "es" ? `${d} de ${LMON_ES[m - 1]} de ${y}` : `${LMON_EN[m - 1]} ${d}, ${y}`; };
const money2 = (n) => "$" + Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const pct = (n) => String(Math.round(n * 100) / 100) + "%";
const bare = (u) => { const s = String(u || "").replace(/^https?:\/\//, "").replace(/^www\./, "").replace(/\/$/, ""); try { return decodeURIComponent(s); } catch { return s; } };
const shortUrl = (u) => { const s = bare(u).replace(/[?#].*$/, ""); return s.length <= 64 ? s : s.slice(0, 61) + "…"; };

// "22" -> "Apt 22", "3B" -> "Apt 3B"; "Unit 4", "#5", "Apt 22", "Penthouse North Tower 4501" stay as typed
export const unitLine = (u) => {
  u = String(u || "").trim();
  if (!u) return "";
  return /^[0-9]{1,5}[A-Za-z]?$|^[A-Za-z][0-9]{0,4}$|^[0-9]{1,4}-[0-9A-Za-z]{1,4}$/.test(u) ? `Apt ${u}` : u;
};
const join = (...a) => a.filter(Boolean).join(", ");

// text of a block's segments with the reader's values (fields left empty become "")
const segText = (segs, v) => segs.map((s) => (s.br ? "\n" : s.f ? (v[s.f] || "").trim() : s.t)).join("");
const runsOf = (segs, v) => segs.filter((s) => !s.br).map((s) => (s.f ? { t: (v[s.f] || "").trim() } : { t: s.t, f: s.b ? "b" : "r", c: s.over ? "red" : undefined }));

// ------------------------------------------------------------------ the model
export function model(d, v = {}) {
  const lang = d.lang === "es" ? "es" : "en", L = { ...S[lang] };
  const notice = d.letter.blocks[0]?.k === "title";
  const P = d.paper || {};
  const sources = (P.sources || []).filter((s) => s.url);
  const numbered = sources.length > 1;
  const srcMeta = (i) => {
    const s = sources[i];
    if (!s) return [];
    const r = [];
    if (numbered) r.push({ t: `[${i + 1}]  `, f: "b", c: "grey" });
    if (s.cite) r.push({ t: s.cite + "  ·  ", c: "grey" });
    r.push({ t: shortUrl(s.url), href: s.url, c: "accent" });
    if (s.retrieved) r.push({ t: `  ·  ${L.retrieved} ${shortDate(s.retrieved, lang)}`, c: "grey" });
    if (L.orig) r.push({ t: `  ·  ${L.orig}`, c: "grey" });
    return r;
  };
  const unit = unitLine(v.unit);
  const street = join(P.street, unit);
  const m = { lang, notice, title: d.title, L, sources: numbered ? sources : [], body: [] };
  m.footer = { left: `${L.footer}  ·  `, site: bare(P.site || "https://navigator.isaaclins.com"), siteUrl: P.site || "https://navigator.isaaclins.com", right: `  ·  ${L.nla}` };
  const vu = P.verify || m.footer.siteUrl;
  m.verify = { url: vu, h: L.verify_h, p: L.verify_p };

  const blocks = d.letter.blocks;
  let q = 0; // quotes seen, for their source
  const body = [];
  const pushBlocks = (skip) => {
    for (let i = 0; i < blocks.length; i++) {
      const b = blocks[i];
      if (skip.includes(b.k)) continue;
      if (b.k === "p") body.push({ k: "p", runs: runsOf(b.s, v) });
      if (b.k === "quote") body.push({ k: "quote", text: segText(b.s, v), meta: srcMeta(q++) });
    }
  };

  if (!notice) {
    // ---------------- the renter's letter
    const x = d.verdict?.values || {}, code = d.verdict?.code, cap = d.verdict?.cap || {};
    const rule = d.verdict?.rules?.[0] || {};
    m.head = { name: (v.name || "").trim(), lines: [street, P.city].filter(Boolean) };
    m.to = { lines: [v.landlord, v.landlord_street, v.landlord_city].map((s) => (s || "").trim()).filter(Boolean) };
    m.date = segText(blocks.find((b) => b.k === "date")?.s || [], v);
    m.subject = segText(blocks.find((b) => b.k === "re")?.s || [], v);
    const sal = blocks.find((b) => b.k === "salute");
    m.salute = (v.landlord || "").trim() ? segText(sal.s, v) : L.dear;
    pushBlocks(["date", "from", "re", "salute", "sign"]);
    const limit = code === "over_max" ? x.cap_max : x.cap_pct;
    const rows = [
      { l: L.cur, v: money2(x.current_rent) },
      { l: L.proposed, n: `+${pct(x.increase_pct)}`, v: money2(x.new_rent) },
      { l: L.allowed, n: [code === "over_max" ? L.at_most : "", cap.basis === "formula" && cap.cpi != null ? L.cpi(pct(cap.cpi)) : "", rule.citation || ""].filter(Boolean).join(" · "), v: pct(limit) },
      { l: L.top, n: `${money2(x.current_rent)} × ${String(Math.round((1 + limit / 100) * 1e4) / 1e4)}`, v: money2(x.max_rent), strong: 1 },
    ];
    if (x.over_amount) rows.push({ l: L.above, v: `${money2(x.over_amount)} ${L.a_month}`, red: 1 });
    // the numbers right after the paragraph that states the increase
    body.splice(1, 0, { k: "table", rows });
    m.closing = segText(blocks.find((b) => b.k === "sign")?.s || [], {}).split("\n")[0].trim();
    m.sign = [{ name: (v.name || "").trim() }];
  } else {
    // ---------------- the landlord's notice
    const owner = (v.owner || "").trim(), contact = (v.contact || "").trim(), tenant = (v.tenant || "").trim();
    m.head = { name: owner, lines: contact ? [contact] : [], label: L.owner_l };
    m.to = { lines: [tenant ? tenant + L.and_occ : L.all_occ, street, P.city].filter(Boolean) };
    m.date = (v.given || "").trim() || null;
    m.subject = L.n_title;
    pushBlocks(["title", "to", "sign"]);
    if (d.over) {
      const c = (d.checks || []).find((c) => c.st === "over");
      m.banner = [{ t: L.check + " ", f: "b" }, { t: c ? `${c.t}. ${c.s}.` : "" }];
    }
    const inc = d.new_rent ? `+${money2(d.new_rent - d.current_rent)} (${pct((d.new_rent - d.current_rent) / d.current_rent * 100)})` : "";
    const rows = [
      { l: L.n_cur, v: money2(d.current_rent) },
      { l: L.n_new, v: d.new_rent ? money2(d.new_rent) : "", strong: 1, red: d.over ? 1 : 0, blank: !d.new_rent },
      { l: L.n_inc, v: inc, blank: !d.new_rent },
      { l: L.n_start, v: longDate(d.start, lang), strong: 1 },
    ];
    if (d.notice_days) rows.push({ l: L.n_period, v: L.n_period_v(d.notice_days) });
    // the table says what the first sentence says (amounts, increase, start): a short lead instead
    body.splice(0, 1, { k: "p", runs: [{ t: L.n_lead }] }, { k: "table", rows });
    // the notice-period sentence cites the notice rule (the source after the quoted ones)
    if (numbered && sources.length > q) {
      const last = [...body].reverse().find((b) => b.k === "p");
      if (last) last.runs.push({ t: "  " + sources.slice(q).map((_, i) => `[${q + i + 1}]`).join(" "), f: "b", c: "grey" });
    }
    m.sign = [{ label: L.sign_l, name: owner, sub: contact }, { label: L.given_l, value: m.date || "" }];
  }
  m.body = body;
  m.running = [m.head.name, m.subject].filter(Boolean).join("  ·  ");
  return m;
}

// ------------------------------------------------------------------ fonts
let KIT = null, KITP = null;
const FONTS = { r: "Inter-Regular", b: "Inter-SemiBold", s: "InstrumentSerif-Regular" };
export const ready = () => !!KIT;
export function load() {
  if (KITP) return KITP;
  const base = new URL("../fonts/pdf/", import.meta.url);
  KITP = (async () => {
    const met = await (await fetch(new URL("metrics.json", base))).json();
    const files = await Promise.all(Object.values(FONTS).map(async (n) => {
      const r = await fetch(new URL(met[n].file, base));
      if (!r.ok) throw new Error("font " + r.status);
      return new Uint8Array(await r.arrayBuffer());
    }));
    KIT = {};
    Object.entries(FONTS).forEach(([k, n], i) => (KIT[k] = { ...met[n], name: n, data: files[i] }));
    return KIT;
  })().catch((e) => { KITP = null; throw e; });
  return KITP;
}

// unicode -> WinAnsi (cp1252)
const HI = "€\0‚ƒ„…†‡ˆ‰Š‹Œ\0Ž\0\0‘’“”•–—˜™š›œ\0žŸ";
const WIN = new Map();
for (let c = 32; c < 127; c++) WIN.set(String.fromCharCode(c), c);
for (let c = 160; c < 256; c++) WIN.set(String.fromCharCode(c), c);
[...HI].forEach((ch, i) => ch !== "\0" && WIN.set(ch, 0x80 + i));
const SUBST = { "→": "->", "←": "<-", "≤": "<=", "≥": ">=", "−": "-", "‑": "-", "‐": "-", " ": " ", " ": " ", " ": " ", " ": " ", " ": " ", "\t": " ", "\n": " ", "′": "'", "″": '"', "≈": "~" };
export const clean = (s) => [...String(s ?? "").normalize("NFC")].map((ch) => {
  if (WIN.has(ch)) return ch;
  if (SUBST[ch] != null) return SUBST[ch];
  const base = ch.normalize("NFD")[0];
  return WIN.has(base) ? base : "?";
}).join("");

const width = (s, f, size) => {
  const F = KIT[f];
  let w = 0, prev = "";
  for (const ch of s) {
    w += F.widths[WIN.get(ch)] || 0;
    if (prev) w += F.kern[prev + ch] || 0;
    prev = ch;
  }
  return (w * size) / 1000;
};
// a PDF string in TJ form with the kerning pairs: [(Te) 80 (st)]
const tj = (s, f) => {
  const F = KIT[f];
  const parts = [];
  let cur = "", prev = "";
  for (const ch of s) {
    const k = prev ? F.kern[prev + ch] || 0 : 0;
    if (k) { parts.push(lit(cur), String(-k)); cur = ""; }
    cur += ch; prev = ch;
  }
  parts.push(lit(cur));
  return "[" + parts.join(" ") + "] TJ";
};
const lit = (s) => "(" + [...s].map((ch) => {
  const c = WIN.get(ch) ?? 63;
  if (ch === "(" || ch === ")" || ch === "\\") return "\\" + ch;
  return c < 127 ? ch : "\\" + c.toString(8).padStart(3, "0");
}).join("") + ")";

// ------------------------------------------------------------------ line breaking
// runs [{t, f, c, href}] -> lines [[{t, f, c, href, w, x}]], width-limited; long words break after / - or anywhere
const COL = { ink: "0 0.047 0.122", grey: "0.36 0.39 0.45", light: "0.62 0.65 0.7", accent: "0.039 0.227 0.549", red: "0.706 0.137 0.102" };
function wrap(runs, maxw, size, dflt = "r") {
  const toks = []; // words and spaces, each a list of pieces
  for (const r of runs) {
    const f = r.f || dflt;
    for (const part of clean(r.t).split(/( +)/)) {
      if (!part) continue;
      const sp = /^ +$/.test(part);
      const last = toks[toks.length - 1];
      const piece = { t: part, f, c: r.c, href: r.href };
      if (!sp && last && !last.sp) last.p.push(piece); // a word continues across runs ("$2,400" + ".")
      else toks.push({ sp, p: [piece] });
    }
  }
  const pw = (p) => width(p.t, p.f, size);
  const lines = [];
  let line = [], w = 0;
  const flush = () => { while (line.length && line[line.length - 1].sp) w -= line.pop().w; lines.push(line); line = []; w = 0; };
  for (const tok of toks) {
    if (tok.sp) { if (line.length) { const p = { ...tok.p[0], t: " ", sp: 1 }; p.w = pw(p); line.push(p); w += p.w; } continue; }
    let ww = tok.p.reduce((a, p) => a + pw(p), 0);
    if (w + ww > maxw && line.length) flush();
    if (ww > maxw) { // a word wider than the line: cut it
      for (const p of tok.p) {
        let rest = p.t;
        while (rest) {
          let n = rest.length;
          while (n > 1 && w + width(rest.slice(0, n), p.f, size) > maxw) n--;
          const cut = rest.slice(0, n), soft = Math.max(cut.lastIndexOf("/"), cut.lastIndexOf("-"));
          if (n < rest.length && soft > n * 0.5) n = soft + 1;
          const q = { ...p, t: rest.slice(0, n) };
          q.w = pw(q); line.push(q); w += q.w;
          rest = rest.slice(n);
          if (rest) flush();
        }
      }
      continue;
    }
    for (const p of tok.p) { const q = { ...p }; q.w = pw(q); line.push(q); w += q.w; }
  }
  if (line.length || !lines.length) flush();
  return lines;
}
const lineW = (ln) => ln.reduce((a, p) => a + p.w, 0);

// ------------------------------------------------------------------ the PDF
const PW = 612, PH = 792, ML = 72, MR = 540, CW = MR - ML, BOTTOM = 68, TOP2 = 716;
const n2 = (x) => (Math.round(x * 100) / 100).toString();

export function pdf(m) {
  if (!KIT) throw new Error("paper: fonts not loaded");
  const pages = [];
  let pg, y;
  const page = () => { pg = { ops: [], links: [] }; pages.push(pg); y = TOP2; };
  const op = (s) => pg.ops.push(s);
  const fill = (c) => `${COL[c] || c} rg`;
  const text = (s, x, yy, f, size, c = "ink") => { s = clean(s); if (s) op(`BT /${f.toUpperCase()} ${n2(size)} Tf ${fill(c)} ${n2(x)} ${n2(yy)} Td ${tj(s, f)} ET`); return width(s, f, size); };
  const rule = (x1, yy, x2, c = "0.85 0.87 0.9", w = 0.5) => op(`${c} RG ${w} w ${n2(x1)} ${n2(yy)} m ${n2(x2)} ${n2(yy)} l S`);
  const rect = (x, yy, w, h, c) => op(`${COL[c] || c} rg ${n2(x)} ${n2(yy)} ${n2(w)} ${n2(h)} re f`);
  const drawLine = (ln, x, base, size, dflt = "ink") => {
    for (const p of ln) {
      if (!p.sp) {
        op(`BT /${p.f.toUpperCase()} ${n2(size)} Tf ${fill(p.c || (p.href ? "accent" : dflt))} ${n2(x)} ${n2(base)} Td ${tj(p.t, p.f)} ET`);
        if (p.href) pg.links.push({ r: [x, base - size * 0.28, x + p.w, base + size * 0.85], url: p.href });
      }
      x += p.w;
    }
  };
  const para = (runs, { x = ML, w = CW, size = 10.5, lead = 15.5, f = "r", c = "ink", keep = 2 } = {}) => {
    const lines = wrap(runs, w, size, f);
    if (y - Math.min(keep, lines.length) * lead < BOTTOM) page();
    for (const ln of lines) {
      if (y - lead < BOTTOM) page();
      drawLine(ln, x, y - lead + (lead - size) / 2 + size * 0.22, size, c);
      y -= lead;
    }
  };

  // ---------------- page 1: letterhead, recipient, date, subject
  page();
  const L = m.L;
  const hx = ML, HW = CW - 236; // the right of the letterhead holds the QR code
  let hy = PH - 62;
  if (m.head.name) {
    let size = 21, nl = wrap([{ t: m.head.name, f: "s" }], HW, size);
    if (nl.length > 1) { size = 15; nl = wrap([{ t: m.head.name, f: "s" }], HW, size); }
    nl.forEach((ln, i) => drawLine(ln, hx, hy - i * (size + 1), size));
    hy -= (nl.length - 1) * (size + 1) + 16;
  } else {
    rule(hx, hy - 2, hx + 200, "0.55 0.58 0.63", 0.6);
    if (m.head.label) text(m.head.label, hx, hy - 11, "r", 7, "light");
    hy -= 24;
  }
  for (const s of m.head.lines) for (const ln of wrap([{ t: s }], HW, 9)) { drawLine(ln, hx, hy, 9, "grey"); hy -= 12; }
  // verify: a QR code to the public answer for this address (dark modules as runs of rectangles: vector, crisp)
  {
    const Q = qr(m.verify.url), mod = Math.min(1.9, 52 / Q.size), qs = Q.size * mod;
    const qx = MR - qs, qy = PH - 50 - qs;
    const parts = [];
    for (let r = 0; r < Q.size; r++) {
      for (let c = 0; c < Q.size; c++) {
        if (!Q.dark(c, r)) continue;
        let e = c; while (e + 1 < Q.size && Q.dark(e + 1, r)) e++;
        parts.push(`${n2(qx + c * mod)} ${n2(qy + (Q.size - 1 - r) * mod)} ${n2((e - c + 1) * mod + 0.02)} ${n2(mod + 0.02)} re`);
        c = e;
      }
    }
    op(`${COL.ink} rg ${parts.join(" ")} f`);
    pg.links.push({ r: [qx, qy, qx + qs, qy + qs], url: m.verify.url });
    const tr = qx - 10, CWV = 150;
    let ty = PH - 58;
    const right = (ln, size, c) => { drawLine(ln, tr - lineW(ln), ty, size, c); ty -= size + 3; };
    for (const ln of wrap([{ t: m.verify.h, f: "b" }], CWV, 8)) right(ln, 8);
    for (const ln of wrap([{ t: m.verify.p }], CWV, 7)) right(ln, 7, "grey");
    const vu = bare(m.verify.url), cut = vu.indexOf("/");
    for (const part of cut > 0 ? [vu.slice(0, cut), vu.slice(cut)] : [vu]) for (const ln of wrap([{ t: part, href: m.verify.url }], CWV, 7)) right(ln, 7, "accent");
    hy = Math.min(hy, qy + 10, ty + 8);
  }
  const ruleY = Math.min(hy + 2, PH - 106);
  rule(ML, ruleY, MR);
  // fold marks (thirds) on the left edge
  for (const fy of [PH - 264, PH - 528]) rule(20, fy, 32, "0.7 0.72 0.76", 0.5);

  if (m.to.lines.length) {
    // recipient: #10 window envelope (window 4.5" x 1.125", 7/8" from the left); first line 2.1" from the top
    // at most 5 lines: long ones get smaller; if still too many, the name gives way (street and city always print)
    const RX = ML, RW = 300, RY = PH - 160;
    let rs = 10.5;
    const fit = () => m.to.lines.map((s) => wrap([{ t: s }], RW, rs));
    let parts = fit();
    if (parts.flat().length > 5) { rs = 9; parts = fit(); }
    while (parts.flat().length > 5 && parts[0].length > 1) parts[0].pop();
    const rl = parts.flat().slice(-5), RL = rs + 3;
    rl.forEach((ln, i) => drawLine(ln, RX, RY - i * RL, rs));
    if (m.date) { const w = width(clean(m.date), "r", 10); text(m.date, MR - w, RY, "r", 10, "grey"); }
    y = Math.min(PH - 224, RY - (rl.length - 1) * RL - 24); // 3.1"
  } else {
    // no address to show: no empty window, the date right under the letterhead rule
    y = ruleY - 14;
    if (m.date) { para([{ t: m.date }], { c: "grey", size: 10, lead: 15 }); y -= 16; }
    else y -= 8;
  }
  if (m.notice) {
    para([{ t: m.subject }], { f: "s", size: 24, lead: 28 });
    y -= 8;
  } else {
    para([{ t: m.subject, f: "b" }], { size: 11, lead: 15.5 });
    y -= 12;
  }
  if (m.banner) {
    const lines = wrap(m.banner, CW - 28, 9.5);
    const h = lines.length * 14 + 16;
    rect(ML, y - h, CW, h, "0.992 0.937 0.929");
    rect(ML, y - h, 2.5, h, "red");
    let by = y - 8;
    for (const ln of lines) { drawLine(ln, ML + 14, by - 10.5, 9.5, "red"); by -= 14; }
    y -= h + 16;
  }
  if (m.salute) { para([{ t: m.salute }]); y -= 7; }

  // ---------------- body (the last paragraph stays with the closing and signature)
  const SW = 214, VX = ML + SW + 34, VW = MR - VX;
  const sh = (s) => (s === m.sign[0] ? 30 : 24) + (s.label ? 12 : 0) + (s.name ? wrap([{ t: s.name }], SW, 10.5).length * 14 : 0) + (s.sub ? wrap([{ t: s.sub }], SW, 9).length * 12 : 0);
  const signH = m.sign.reduce((a, s) => a + sh(s) + 6, 0);
  const srcs = m.sources.map((s) => wrap([
    { t: `${s.cite || ""}. `, c: "ink" }, { t: s.url, href: s.url, c: "accent" },
    ...(s.retrieved ? [{ t: `. ${L.retrieved} ${shortDate(s.retrieved, m.lang)}.`, c: "grey" }] : []),
  ], VW - 12, 7));
  const srcH = srcs.length ? 20 + srcs.reduce((a, l) => a + l.length * 9 + 3, 0) : 0;
  const closeH = m.closing ? 15.5 + 4 : 0;
  const tailH = Math.max(closeH + signH, srcH + 4);
  for (const b of m.body) {
    if (b === m.body[m.body.length - 1] && b.k === "p" && y - wrap(b.runs, CW, 10.5).length * 15.5 - 8 - tailH < BOTTOM) page();
    if (b.k === "p") { para(b.runs); y -= 8; }
    if (b.k === "table") table(b.rows);
    if (b.k === "quote") quote(b);
  }
  function table(rows) {
    const LX = ML + 12, NX = ML + 168, VX = MR - 12, size = 10;
    const lay = rows.map((r) => {
      const vl = r.text ? wrap([{ t: r.v, f: r.strong ? "b" : "r" }], VX - NX, size) : null;
      const nl = r.n ? wrap([{ t: r.n }], VX - NX - 110, 8.5) : [];
      const h = Math.max(21, vl ? vl.length * 14 + 7 : 21, nl.length * 10.5 + 10.5);
      return { r, vl, nl, h };
    });
    const total = lay.reduce((a, x) => a + x.h, 0);
    if (y - total - 8 < BOTTOM) page();
    y -= 4;
    rule(ML, y, MR, "0.8 0.82 0.86", 0.6);
    for (const { r, vl, nl, h } of lay) {
      if (r.strong && !r.text) rect(ML, y - h, CW, h, "0.949 0.957 0.973");
      const base = y - 14;
      text(r.l, LX, base, "r", size, "grey");
      if (vl) vl.forEach((ln, i) => drawLine(ln, NX, base - i * 14, size));
      else {
        nl.forEach((ln, i) => drawLine(ln, NX, base - i * 10.5, 8.5, "grey"));
        if (r.blank) rule(VX - 110, base - 2, VX, "0.55 0.58 0.63", 0.6);
        else { const f = r.strong ? "b" : "r", w = width(clean(r.v), f, size); text(r.v, VX - w, base, f, size, r.red ? "red" : "ink"); }
      }
      y -= h;
      rule(ML, y, MR, r === rows[rows.length - 1] ? "0.8 0.82 0.86" : "0.9 0.91 0.93", r === rows[rows.length - 1] ? 0.6 : 0.4);
    }
    y -= 18;
  }
  function quote(b) {
    const PAD = 14, size = 12.5, lead = 17, w = CW - PAD * 2 - 4;
    const ql = wrap([{ t: b.text, f: "s" }], w, size);
    const ml = b.meta.length ? wrap(b.meta, w, 7.5) : [];
    const h = PAD + ql.length * lead + (ml.length ? 6 + ml.length * 10.5 : 0) + PAD - 4;
    if (y - h - 10 < BOTTOM) page();
    y -= 2;
    rect(ML, y - h, CW, h, "0.957 0.965 0.98");
    rect(ML, y - h, 2.5, h, "0 0.149 0.392");
    let qy = y - PAD;
    for (const ln of ql) { drawLine(ln, ML + PAD + 4, qy - 12, size); qy -= lead; }
    qy -= 6;
    for (const ln of ml) { drawLine(ln, ML + PAD + 4, qy - 7.5, 7.5, "grey"); qy -= 10.5; }
    y -= h + 14;
  }

  // ---------------- closing; signature lines (left) beside the numbered sources (right, when more than one)
  {
    if (y - tailH < BOTTOM) page();
    const top = y;
    if (m.closing) { para([{ t: m.closing }], { keep: 1 }); y -= 4; }
    let sy = y;
    for (const s of m.sign) {
      sy -= s === m.sign[0] ? 30 : 24;
      if (s.value) text(s.value, ML, sy + 5, "r", 10.5);
      rule(ML, sy, ML + SW, "0.35 0.38 0.44", 0.6);
      sy -= 12;
      if (s.label) { text(s.label, ML, sy, "r", 7.5, "grey"); sy -= 12; }
      if (s.name) for (const ln of wrap([{ t: s.name }], SW, 10.5)) { sy -= 2; drawLine(ln, ML, sy, 10.5); sy -= 12; }
      if (s.sub) for (const ln of wrap([{ t: s.sub }], SW, 9)) { drawLine(ln, ML, sy, 9, "grey"); sy -= 12; }
      sy -= 6;
    }
    let ty = top - 4;
    if (srcs.length) {
      rule(VX, ty, MR);
      ty -= 11;
      text(L.sources, VX, ty, "b", 7);
      ty -= 10;
      srcs.forEach((lines, i) => {
        lines.forEach((ln, j) => { if (!j) text(String(i + 1), VX, ty, "b", 7, "grey"); drawLine(ln, VX + 12, ty, 7, "grey"); ty -= 9; });
        ty -= 3;
      });
    }
    y = Math.min(sy, ty) - 6;
  }

  // ---------------- footer and running header on every page
  const N = pages.length;
  pages.forEach((p, i) => {
    pg = p;
    rule(ML, 50, MR);
    let x = ML;
    x += text(m.footer.left, x, 36, "r", 7.5, "grey");
    const sw = text(m.footer.site, x, 36, "r", 7.5, "accent");
    p.links.push({ r: [x, 33, x + sw, 44], url: m.footer.siteUrl });
    x += sw;
    text(m.footer.right, x, 36, "r", 7.5, "grey");
    const pt = L.page(i + 1, N), pw = width(clean(pt), "r", 7.5);
    text(pt, MR - pw, 36, "r", 7.5, "grey");
    if (i > 0) {
      const rl = wrap([{ t: m.running }], CW - 80, 8);
      const ln = rl.length > 1 ? wrap([{ t: m.subject }], CW - 80, 8)[0] : rl[0];
      drawLine(ln, ML, PH - 50, 8, "grey");
      rule(ML, PH - 58, MR);
    }
  });
  return write(pages, m.title, m.lang);
}

// ------------------------------------------------------------------ the file
function write(pages, title, lang) {
  const latin = (s) => { const b = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) b[i] = s.charCodeAt(i) & 255; return b; };
  const objs = []; // each: array of Uint8Array/strings
  const add = (...parts) => { objs.push(parts); return objs.length; };
  const fontIds = {};
  for (const [k, F] of Object.entries(KIT)) {
    const ff = add(`<< /Length ${F.data.length} /Length1 ${F.length1} /Filter /FlateDecode >>\nstream\n`, F.data, "\nendstream");
    const tag = { r: "AAAAAA", b: "AAAAAB", s: "AAAAAC" }[k] + "+" + F.name;
    const fd = add(`<< /Type /FontDescriptor /FontName /${tag} /Flags ${F.flags} /FontBBox [${F.bbox.join(" ")}] /ItalicAngle ${F.italicAngle} /Ascent ${F.ascent} /Descent ${F.descent} /CapHeight ${F.capHeight} /XHeight ${F.xHeight} /StemV ${F.stemV} /FontFile2 ${ff} 0 R >>`);
    fontIds[k] = add(`<< /Type /Font /Subtype /TrueType /BaseFont /${tag} /FirstChar 32 /LastChar 255 /Widths [${F.widths.slice(32).join(" ")}] /Encoding /WinAnsiEncoding /FontDescriptor ${fd} 0 R >>`);
  }
  const fontRes = `<< ${Object.entries(fontIds).map(([k, id]) => `/${k.toUpperCase()} ${id} 0 R`).join(" ")} >>`;
  const pid = add(""); // the page tree, filled in below
  const kids = [];
  for (const p of pages) {
    const content = p.ops.join("\n");
    const cid = add(`<< /Length ${content.length} >>\nstream\n${content}\nendstream`);
    const aids = p.links.map((a) => add(`<< /Type /Annot /Subtype /Link /Rect [${a.r.map(n2).join(" ")}] /Border [0 0 0] /A << /S /URI /URI ${uriStr(a.url)} >> >>`));
    kids.push(add(`<< /Type /Page /Parent ${pid} 0 R /MediaBox [0 0 ${PW} ${PH}] /Resources << /Font ${fontRes} /ProcSet [/PDF /Text] >> /Contents ${cid} 0 R${aids.length ? ` /Annots [${aids.map((n) => n + " 0 R").join(" ")}]` : ""} >>`));
  }
  objs[pid - 1] = [`<< /Type /Pages /Kids [${kids.map((k) => k + " 0 R").join(" ")}] /Count ${kids.length} >>`];
  const info = add(`<< /Title ${utf16(title)} /Creator (Clause & Effect) /Producer (Clause & Effect) >>`);
  const cat = add(`<< /Type /Catalog /Pages ${pid} 0 R /Lang (${lang === "es" ? "es-US" : "en-US"}) /ViewerPreferences << /DisplayDocTitle true >> >>`);
  const chunks = [];
  let len = 0;
  const put = (x) => { const b = typeof x === "string" ? latin(x) : x; chunks.push(b); len += b.length; };
  put("%PDF-1.4\n%\xE2\xE3\xCF\xD3\n");
  const offs = [];
  objs.forEach((parts, i) => { offs.push(len); put(`${i + 1} 0 obj\n`); parts.forEach(put); put("\nendobj\n"); });
  const xref = len;
  put(`xref\n0 ${objs.length + 1}\n0000000000 65535 f \n${offs.map((o) => String(o).padStart(10, "0") + " 00000 n \n").join("")}`);
  put(`trailer\n<< /Size ${objs.length + 1} /Root ${cat} 0 R /Info ${info} 0 R >>\nstartxref\n${xref}\n%%EOF\n`);
  return new Blob(chunks, { type: "application/pdf" });
}
const uriStr = (u) => "(" + String(u).replace(/[^\x21-\x7e]/g, (c) => encodeURIComponent(c)).replace(/[\\()]/g, (m) => "\\" + m) + ")";
// a text string in UTF-16BE (titles with accents show right in the viewer's title bar)
const utf16 = (s) => "<FEFF" + [...String(s)].map((ch) => {
  const c = ch.codePointAt(0);
  const u = c > 0xffff ? [0xd800 + ((c - 0x10000) >> 10), 0xdc00 + ((c - 0x10000) & 0x3ff)] : [c];
  return u.map((x) => x.toString(16).padStart(4, "0")).join("");
}).join("") + ">";

// ------------------------------------------------------------------ HTML (the Print button)
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const runsHtml = (runs) => runs.map((r) => {
  const cls = [r.f === "b" ? "pp-b" : "", r.c ? "pp-" + r.c : ""].filter(Boolean).join(" ");
  const inner = esc(r.t);
  if (r.href) return `<a href="${esc(r.href)}"${cls ? ` class="${cls}"` : ""}>${inner}</a>`;
  return cls ? `<span class="${cls}">${inner}</span>` : inner;
}).join("");
export function qrSvg(url) {
  const Q = qr(url);
  let d = "";
  for (let r = 0; r < Q.size; r++) for (let c = 0; c < Q.size; c++) if (Q.dark(c, r)) { let e = c; while (e + 1 < Q.size && Q.dark(e + 1, r)) e++; d += `M${c} ${r}h${e - c + 1}v1h-${e - c + 1}z`; c = e; }
  return `<svg viewBox="0 0 ${Q.size} ${Q.size}" shape-rendering="crispEdges" aria-hidden="true"><path d="${d}"/></svg>`;
}
export function html(m) {
  const L = m.L, vu = bare(m.verify.url);
  const verify = `<div class="pp-verify">${qrSvg(m.verify.url)}<div><b>${esc(m.verify.h)}</b><p>${esc(m.verify.p)} <a href="${esc(m.verify.url)}">${vu.includes("/") ? `${esc(vu.split("/")[0])}<wbr><span class="pp-nw">${esc(vu.slice(vu.indexOf("/")))}</span>` : esc(vu)}</a></p></div></div>`;
  const head = `<header class="pp-head">${m.head.name ? `<div class="pp-name">${esc(m.head.name)}</div>` : `<div class="pp-name pp-blank">${m.head.label ? `<span>${esc(m.head.label)}</span>` : ""}</div>`}
    ${m.head.lines.map((l) => `<div class="pp-meta">${esc(l)}</div>`).join("")}${verify}</header>`;
  const to = m.to.lines.length
    ? `<div class="pp-window"><div class="pp-to">${m.to.lines.map((l) => `<div>${esc(l)}</div>`).join("")}</div>${m.date ? `<div class="pp-date">${esc(m.date)}</div>` : ""}</div>`
    : `<div class="pp-window pp-none">${m.date ? `<div class="pp-date">${esc(m.date)}</div>` : ""}</div>`;
  const subj = m.notice ? `<h1 class="pp-title">${esc(m.subject)}</h1>` : `<p class="pp-subject">${esc(m.subject)}</p>`;
  const banner = m.banner ? `<p class="pp-banner">${runsHtml(m.banner)}</p>` : "";
  const body = m.body.map((b) => {
    if (b.k === "p") return `<p>${runsHtml(b.runs)}</p>`;
    if (b.k === "quote") return `<blockquote class="pp-quote"><p>${esc(b.text)}</p>${b.meta.length ? `<footer>${runsHtml(b.meta)}</footer>` : ""}</blockquote>`;
    if (b.k === "table") return `<table class="pp-table"><tbody>${b.rows.map((r) => {
      const v = r.blank ? '<span class="pp-line"></span>' : esc(r.v);
      return `<tr${r.strong ? ' class="pp-strong"' : ""}><th>${esc(r.l)}</th><td class="pp-n">${esc(r.n || "")}</td><td class="pp-v${r.red ? " pp-red" : ""}">${v}</td></tr>`;
    }).join("")}</tbody></table>`;
    return "";
  }).join("");
  const sign = `<div class="pp-sign">${m.sign.map((s) => `<div>${s.value ? `<div class="pp-sv">${esc(s.value)}</div>` : ""}<div class="pp-sl"></div>${s.label ? `<div class="pp-lab">${esc(s.label)}</div>` : ""}${s.name ? `<div>${esc(s.name)}</div>` : ""}${s.sub ? `<div class="pp-meta">${esc(s.sub)}</div>` : ""}</div>`).join("")}</div>`;
  const sources = m.sources.length ? `<section class="pp-sources"><h2>${esc(L.sources)}</h2><ol>${m.sources.map((s) => `<li>${esc(s.cite || "")}. <a href="${esc(s.url)}">${esc(s.url)}</a>${s.retrieved ? `. ${esc(L.retrieved)} ${esc(shortDate(s.retrieved, m.lang))}.` : ""}</li>`).join("")}</ol></section>` : "";
  const tail = `<div class="pp-keep">${m.closing ? `<p class="pp-closing">${esc(m.closing)}</p>` : ""}<div class="pp-tail">${sign}${sources}</div></div>`;
  return `<div class="pp${m.notice ? " pp-notice" : ""}" lang="${m.lang}">${head}${to}${subj}${banner}${m.salute ? `<p>${esc(m.salute)}</p>` : ""}${body}${tail}</div>`;
}
// the @page margin boxes need the strings in CSS (Chromium prints them on every page with the page numbers)
export function printCss(m) {
  const q = (s) => JSON.stringify(String(s));
  const pg = m.lang === "es" ? `"Página " counter(page) " de " counter(pages)` : `"Page " counter(page) " of " counter(pages)`;
  return `@page { @bottom-left { content: ${q(m.footer.left + m.footer.site + m.footer.right)}; } @bottom-right { content: ${pg}; } }`;
}
