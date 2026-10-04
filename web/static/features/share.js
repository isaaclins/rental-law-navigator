// Share an answer (#117). In the app: a "Share" button at the end of every opened topic on an address page
// (slot .topic-actions, web/DESIGN.md). On the frozen page (/s/<id>/<topic>/<as_of>, web/share.py): the same button,
// and "See today's answer" opens that topic in the app for today.
// Phones get the system share sheet (navigator.share); desktops a popover with the live card preview, Copy link,
// WhatsApp and Email. The link and its texts come from GET /api/share/... so the app and the page say the same thing.

const TOPIC_SLUG = { rent_increase_limits: "rent", just_cause_eviction: "eviction", security_deposits: "deposit", application_screening_fees: "fees", screening_restrictions: "screening", algorithmic_rent_setting: "pricing" };
const S = {
  en: { share: "Share", title: "Share this answer", copy: "Copy link", copied: "Copied", wa: "WhatsApp", mail: "Email", open: "Open page", close: "Close", err: "The link could not be made. Please try again.", nla: "Not legal advice.", as_of: "As of {d}", copy_err: "Copy did not work. Select the link and copy it." },
  es: { share: "Compartir", title: "Compartir esta respuesta", copy: "Copiar enlace", copied: "Copiado", wa: "WhatsApp", mail: "Correo", open: "Abrir página", close: "Cerrar", err: "No se pudo crear el enlace. Inténtelo de nuevo.", nla: "No es asesoría legal.", as_of: "Al {d}", copy_err: "No se pudo copiar. Seleccione el enlace y cópielo." },
};
const PAGE = document.querySelector("[data-share-page]");
const CE = () => window.CE;
const lang = () => (PAGE ? document.documentElement.lang : CE()?.lang?.()) === "es" ? "es" : "en";
const s = (k, o = {}) => Object.entries(o).reduce((x, [a, b]) => x.replaceAll(`{${a}}`, b), (S[lang()] || S.en)[k] || S.en[k]);
const esc = (x) => String(x ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const I = {
  share: '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 15V4M8 8l4-4 4 4M5 12v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6"/></svg>',
  copy: '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><rect x="8" y="8" width="12" height="12" rx="2.5"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/></svg>',
  check: '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12.5 4.2 4.2L19 7"/></svg>',
  wa: '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20l1.3-3.9A8 8 0 1 1 8 19z"/><path d="M9.2 9.3c.3 2 2.3 4 4.4 4.4l1-1 1.5.8c-.2 1-1 1.6-2 1.5-3-.3-5.9-3.2-6.2-6.2-.1-1 .5-1.8 1.5-2l.8 1.5z" fill="currentColor" stroke="none"/></svg>',
  mail: '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5.5" width="18" height="13" rx="2.5"/><path d="m3.8 7 8.2 6 8.2-6"/></svg>',
  x: '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg>',
  ext: '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true" style="width:13px;height:13px"><path d="M14 5h5v5M19 5l-8 8M18 14v4a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h4"/></svg>',
};
const phone = () => matchMedia("(pointer: coarse)").matches && innerWidth <= 900;

// ----------------------------------------------------------------- data
const cache = new Map();
async function shareData(addr, cat, asOf, L) {
  const key = `${addr}|${cat}|${asOf}|${L}`;
  if (!cache.has(key)) {
    const p = fetch(`/api/share/${encodeURIComponent(addr)}/${TOPIC_SLUG[cat]}/${encodeURIComponent(asOf)}?lang=${L}`)
      .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); });
    cache.set(key, p);
    p.catch(() => cache.delete(key));
  }
  return cache.get(key);
}
const mailText = (d) => `${d.question}\n${d.answer}\n${d.why || ""}\n\n${d.url}\n\n${s("as_of", { d: d.as_of_label })} · ${s("nla")}`;

// ----------------------------------------------------------------- popover
let pop = null;
function closePop({ focus = true } = {}) {
  if (!pop) return;
  const { el, scrim, trigger, off } = pop;
  pop = null;
  off();
  trigger?.setAttribute("aria-expanded", "false");
  el.classList.add("is-out"); scrim?.remove();
  setTimeout(() => el.remove(), 170);
  if (focus) trigger?.focus({ preventScroll: true });
}
function place(el, trigger) {
  if (innerWidth <= 640) return;
  const r = trigger.getBoundingClientRect(), w = el.offsetWidth;
  const left = Math.max(12, Math.min(r.left + r.width / 2 - w / 2, innerWidth - w - 12));
  let top = r.bottom + 10 + scrollY;
  if (r.bottom + 10 + el.offsetHeight > innerHeight - 8 && r.top - 10 - el.offsetHeight > 8) top = r.top - 10 - el.offsetHeight + scrollY;
  el.style.left = left + scrollX + "px"; el.style.top = top + "px";
  el.style.setProperty("--ox", `${r.left + r.width / 2 - left}px`);
}
function openPop(trigger, d) {
  closePop({ focus: false });
  const el = document.createElement("div");
  el.className = "ce-sp"; el.setAttribute("role", "dialog"); el.setAttribute("aria-label", s("title"));
  const wa = `https://wa.me/?text=${encodeURIComponent(`${d.title}\n${d.answer}\n${d.url}`)}`;
  const mail = `mailto:?subject=${encodeURIComponent(d.title)}&body=${encodeURIComponent(mailText(d))}`;
  el.innerHTML = `<div class="ce-sp-h"><h2>${esc(s("title"))}</h2><button type="button" class="ce-sp-x" aria-label="${esc(s("close"))}">${I.x}</button></div>
    <a class="sh-prev" href="${esc(d.path)}" target="_blank" rel="noopener" tabindex="-1" aria-hidden="true"><img src="${esc(d.image)}" alt="" width="1200" height="630" decoding="async"><span class="sh-prev-t"><b>${esc(d.title)}</b><span>${esc(d.host)}</span></span></a>
    <div class="ce-sp-acts">
      <button type="button" class="btn ce-sp-copy"><span class="cp-a">${I.copy}${esc(s("copy"))}</span><span class="cp-b" aria-hidden="true">${I.check}${esc(s("copied"))}</span></button>
      <a class="btn ce-sp-wa" href="${esc(wa)}" target="_blank" rel="noopener">${I.wa}${esc(s("wa"))}</a>
      <a class="btn ce-sp-mail" href="${esc(mail)}">${I.mail}${esc(s("mail"))}</a>
    </div>
    <p class="ce-sp-url"><span>${esc(d.url.replace(/^https?:\/\//, ""))}</span><a href="${esc(d.path)}" target="_blank" rel="noopener">${esc(s("open"))} ${I.ext}</a></p>
    <p class="ce-sp-live sr" aria-live="polite"></p>`;
  let scrim = null;
  if (innerWidth <= 640) { scrim = document.createElement("div"); scrim.className = "ce-sp-scrim"; document.body.append(scrim); }
  document.body.append(el);
  const img = el.querySelector("img");
  img.addEventListener("load", () => img.classList.add("is-in"), { once: true });
  if (img.complete) img.classList.add("is-in");
  place(el, trigger);
  trigger.setAttribute("aria-expanded", "true");
  const onDoc = (e) => { if (!el.contains(e.target) && !trigger.contains(e.target)) closePop({ focus: false }); };
  const onKey = (e) => {
    if (e.key === "Escape") { e.preventDefault(); closePop(); }
    if (e.key === "Tab") { // keep focus inside the dialog
      const f = [...el.querySelectorAll("button, a[href]:not([tabindex='-1'])")];
      const i = f.indexOf(document.activeElement);
      if (e.shiftKey && i <= 0) { e.preventDefault(); f[f.length - 1].focus(); } else if (!e.shiftKey && i === f.length - 1) { e.preventDefault(); f[0].focus(); }
    }
  };
  const onResize = () => place(el, trigger);
  setTimeout(() => document.addEventListener("pointerdown", onDoc), 0);
  document.addEventListener("keydown", onKey); addEventListener("resize", onResize);
  const onRoute = () => closePop({ focus: false });
  document.addEventListener("ce:route", onRoute);
  pop = { el, scrim, trigger, off: () => { document.removeEventListener("pointerdown", onDoc); document.removeEventListener("keydown", onKey); removeEventListener("resize", onResize); document.removeEventListener("ce:route", onRoute); } };
  scrim?.addEventListener("click", () => closePop());
  el.querySelector(".ce-sp-x").addEventListener("click", () => closePop());
  const copyB = el.querySelector(".ce-sp-copy");
  copyB.addEventListener("click", async () => {
    const ok = await copy(d.url);
    const live = el.querySelector(".ce-sp-live");
    if (!ok) { live.textContent = s("copy_err"); const u = el.querySelector(".ce-sp-url span"); getSelection()?.selectAllChildren(u); return; }
    copyB.classList.remove("is-done"); void copyB.offsetWidth; copyB.classList.add("is-done");
    live.textContent = s("copied");
    navigator.vibrate?.(8);
    clearTimeout(copyB._t); copyB._t = setTimeout(() => copyB.classList.remove("is-done"), 1800);
  });
  copyB.focus({ preventScroll: true });
}
async function copy(text) {
  try { await navigator.clipboard.writeText(text); return true; } catch { /* fall back below */ }
  try {
    const ta = Object.assign(document.createElement("textarea"), { value: text });
    ta.setAttribute("readonly", ""); ta.style.cssText = "position:fixed;opacity:0;top:0;left:0";
    document.body.append(ta); ta.select(); const ok = document.execCommand("copy"); ta.remove(); return ok;
  } catch { return false; }
}

async function share(trigger, getData) {
  if (pop && pop.trigger === trigger) return closePop();
  trigger.setAttribute("aria-busy", "true");
  let d;
  try { d = await getData(); } catch { trigger.removeAttribute("aria-busy"); CE()?.toast?.(s("err")); return; }
  trigger.removeAttribute("aria-busy");
  if (phone() && navigator.share) {
    try { await navigator.share({ title: d.title, text: d.answer, url: d.url }); return; } catch (e) { if (e?.name === "AbortError") return; }
  }
  openPop(trigger, d);
}

// ----------------------------------------------------------------- in the app
const addrId = () => document.getElementById("main")?.dataset.addr;
function inject() {
  const id = addrId();
  if (!id || !/^A\d{4}$/.test(id)) return;
  for (const slot of document.querySelectorAll('#main .topic-actions[data-slot="topic-actions"][data-cat]')) {
    if (!TOPIC_SLUG[slot.dataset.cat] || slot.querySelector(".ce-share-b")) continue;
    slot.insertAdjacentHTML("beforeend", `<button type="button" class="ce-share-b" data-cat="${esc(slot.dataset.cat)}" aria-haspopup="dialog" aria-expanded="false">${I.share}<span>${esc(s("share"))}</span></button>`);
  }
}
function relabel() { document.querySelectorAll(".ce-share-b span").forEach((x) => { x.textContent = s("share"); }); }

if (PAGE) {
  // the frozen page: Share (needs JS, so it starts hidden) and "See today's answer" opening the topic in the app
  const b = PAGE.querySelector("[data-share]");
  if (b) {
    const d = JSON.parse(b.dataset.share);
    b.hidden = false; b.setAttribute("aria-haspopup", "dialog"); b.setAttribute("aria-expanded", "false");
    b.addEventListener("click", () => share(b, async () => d));
  }
  for (const a of document.querySelectorAll("[data-today]")) {
    a.addEventListener("click", () => {
      try {
        sessionStorage.setItem("ce.open", a.dataset.cat);
        sessionStorage.setItem("asof", a.dataset.asof);
        localStorage.setItem("lang", a.dataset.lang);
      } catch { /* private mode: the address still opens */ }
    });
  }
} else {
  document.addEventListener("click", (e) => {
    const b = e.target.closest?.(".ce-share-b");
    if (!b) return;
    const id = addrId(), asOf = CE()?.asOf?.() || "", L = lang();
    share(b, () => shareData(id, b.dataset.cat, asOf, L));
  });
  const start = () => {
    inject();
    const m = document.getElementById("main");
    if (m) new MutationObserver(inject).observe(m, { childList: true, subtree: true });
  };
  document.addEventListener("ce:route", inject);
  document.addEventListener("ce:lang", () => { relabel(); closePop({ focus: false }); });
  document.addEventListener("ce:asof", () => closePop({ focus: false }));
  if (window.CE) start(); else document.addEventListener("ce:ready", start, { once: true });
}
