// Listen (#49): a spoken briefing on what the rules at this address mean for you, as a renter or as an owner.
// Entry points (web/DESIGN.md slots): "Listen" in the address actions, "Explain this" in every opened topic (that
// topic only, about 10-15 s). A tap plays at once as a renter; the transcript panel's header has a segmented
// "I rent · I own" that switches it (remembered in localStorage). Pause / resume, 1x / 1.25x, Esc stops; the topic being spoken
// gets .topic.is-speaking (app.css draws the rule; no motion added here).
// Voice: POST /api/tts builds the script on the server (web/briefing.py) and returns a cached ElevenLabs mp3 with
// its chapters (X-TTS-Chapters: [[category, first character], ...]). When it answers {fallback, text, chapters}
// (budget, limits, outage) the browser's own voice reads the same text and its boundary events drive the chapters.
// Transcript: while a clip plays, a caption panel (bottom right; a sheet above the tab bar on phones) shows the spoken
// text from POST /api/tts/captions, karaoke style: the current sentence in ink, the current word in navy, auto-scroll
// (paused for a few seconds when the reader scrolls), tap a sentence to jump there, pause / play and a seek bar.
// Timing: word times from the ElevenLabs character alignment (or a local alignment / an estimate for older clips);
// with the browser voice, its word boundary events.
const L = {
  en: {
    listen: "Listen", pause: "Pause", resume: "Resume", loading: "Loading",
    as: "Listen as", renter: "I rent", owner: "I own",
    explain: "Listen", speed: "Playback speed", aListen: "Listen to a spoken briefing on these rules",
    listening: "Listening", play: "Play",
    transcript: "Transcript of the spoken briefing", close: "Close", seek: "Position", jump: "Play from this sentence",
  },
  es: {
    listen: "Escuchar", pause: "Pausa", resume: "Continuar", loading: "Cargando",
    as: "Escuchar como", renter: "Alquilo", owner: "Soy dueño",
    explain: "Escuchar", speed: "Velocidad", aListen: "Escuchar un resumen hablado de estas reglas",
    listening: "Escuchando", play: "Reproducir",
    transcript: "Transcripción del resumen hablado", close: "Cerrar", seek: "Posición", jump: "Reproducir desde esta frase",
  },
};
const ICON = {
  listen: '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9.5v5h3.5L12 18V6L7.5 9.5H4z"/><path d="M15.5 9a4.2 4.2 0 0 1 0 6"/><path d="M18.2 6.5a8 8 0 0 1 0 11"/></svg>',
  pause: '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="6" width="3.5" height="12" rx="1"/><rect x="13.5" y="6" width="3.5" height="12" rx="1"/></svg>',
  play: '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5.8v12.4a.8.8 0 0 0 1.2.7l9.8-6.2a.8.8 0 0 0 0-1.4L9.2 5.1a.8.8 0 0 0-1.2.7z"/></svg>',
  close: '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg>',
};
const PKEY = "ce.listen.persona";
const words = () => L[window.CE?.lang?.() === "es" ? "es" : "en"];
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const clips = new Map(); // "<id>|<asOf>|<lang>|<persona>|<topic>" -> {url, chapters, chars} or {text, lang, chapters}

// player state: one clip at a time (the briefing, or one topic)
const P = { key: null, topic: null, state: "idle", audio: null, voice: null, speed: 1 };
// state: idle | loading | playing | paused

function persona() { try { return localStorage.getItem(PKEY); } catch { return null; } }
function setPersona(p) { try { localStorage.setItem(PKEY, p); } catch { /* private mode: ask again next time */ } }
function addressId() {
  const m = location.hash.match(/^#\/a\/([^/?#]+)/);
  return m ? decodeURIComponent(m[1]).toUpperCase() : null;
}
const keyFor = (topic) => `${addressId()}|${CE.asOf()}|${CE.lang()}|${persona()}|${topic || ""}`;
const main = () => document.getElementById("main");

// ------------------------------------------------------------------ chapters
function speaking(cat) {
  for (const el of main()?.querySelectorAll("details.topic.is-speaking") || []) if (el.dataset.cat !== cat) el.classList.remove("is-speaking");
  if (cat) main()?.querySelector(`details.topic[data-cat="${cat}"]`)?.classList.add("is-speaking");
}
function chapterAt(chapters, pos) {
  let cat = "";
  for (const [c, start] of chapters || []) { if (start <= pos) cat = c; else break; }
  return cat;
}
function trackAudio() {
  const a = P.audio, clip = P.clip;
  if (!a || !clip) return;
  if (P.topic) return speaking(P.topic);
  if (!a.duration || !isFinite(a.duration)) return;
  speaking(chapterAt(clip.chapters, (a.currentTime / a.duration) * clip.chars));
}

// ------------------------------------------------------------------ loading
async function load(k) {
  const dev = deviceVoice(), ck = (dev ? "device|" : "") + k;
  if (clips.has(ck)) return clips.get(ck);
  const [id, asOf, lang, who, topic] = k.split("|");
  if (dev) { // the device voice reads the transcript: never ask the server to record (no characters spent)
    const cap = await loadCaptions(k);
    const clip = { text: cap.text, lang: cap.lang || lang, chapters: cap.chapters || [], cap };
    clips.set(ck, clip);
    return clip;
  }
  const r = await fetch("/api/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ address_id: id, as_of: asOf, lang, persona: who, topic: topic || null }),
  });
  let clip;
  if (r.ok && (r.headers.get("content-type") || "").startsWith("audio/")) {
    let chapters = [];
    try { chapters = JSON.parse(r.headers.get("x-tts-chapters") || "[]"); } catch { /* no highlighting */ }
    clip = { url: URL.createObjectURL(await r.blob()), chapters, chars: +r.headers.get("x-tts-chars") || 1 };
  } else if (r.ok) {
    const d = await r.json();
    clip = { text: d.text, lang: d.lang || lang, chapters: d.chapters || [] };
  } else throw new Error("tts " + r.status);
  try { clip.cap = await loadCaptions(k); } catch { clip.cap = null; } // after the audio: a new clip's timing is saved by then
  clips.set(ck, clip);
  return clip;
}

// ------------------------------------------------------------------ browser voice (fallback)
// ?voice=device (remembered) forces the device voice instead of the recorded one; ?voice=auto resets
function deviceVoice() {
  try {
    const q = new URLSearchParams(location.search).get("voice");
    if (q) localStorage.setItem("ce.voice", q);
    return localStorage.getItem("ce.voice") === "device" && "speechSynthesis" in window;
  } catch { return false; }
}
function pickVoice(lang) {
  const vs = speechSynthesis.getVoices().filter((v) => v.lang?.toLowerCase().startsWith(lang));
  const pref = lang === "es" ? ["es-us", "es-mx", "es-es"] : ["en-us", "en-gb"];
  for (const p of pref) {
    const v = vs.find((x) => x.lang.toLowerCase() === p && x.localService) || vs.find((x) => x.lang.toLowerCase() === p);
    if (v) return v;
  }
  return vs[0] || null;
}
function speakFrom(clip, offset) {
  speechSynthesis.cancel();
  speechSynthesis.resume(); // Chrome keeps a paused queue paused after cancel()
  const u = new SpeechSynthesisUtterance(clip.text.slice(offset));
  u.lang = clip.lang === "es" ? "es-US" : "en-US";
  const v = pickVoice(clip.lang);
  if (v) u.voice = v;
  u.rate = P.speed;
  const key = P.key;
  P.voice = { clip, offset, pos: offset, u, t0: performance.now(), heard: false };
  u.onboundary = (e) => {
    if (P.key !== key || !P.voice) return;
    P.voice.pos = offset + (e.charIndex || 0);
    P.voice.heard = true;
    capTick();
    if (!P.topic) speaking(chapterAt(clip.chapters, P.voice.pos));
  };
  u.onend = () => { if (P.key === key && P.voice?.u === u) finish(); };
  u.onerror = (e) => { if (P.key === key && P.voice?.u === u && e.error !== "interrupted" && e.error !== "canceled") finish(); };
  speechSynthesis.speak(u);
  capTick();
  if (P.topic) speaking(P.topic);
  else speaking(chapterAt(clip.chapters, offset));
}

// ------------------------------------------------------------------ transport
function finish() { stop(); }
function stop() {
  P.state = "idle";
  if (P.audio) { P.audio.pause(); P.audio.removeAttribute("src"); P.audio.load(); P.audio = null; }
  if (P.voice && "speechSynthesis" in window) speechSynthesis.cancel();
  P.voice = null; P.clip = null; P.key = null; P.topic = null;
  speaking(null);
  closeCaptions();
  render();
}
function pause() {
  if (P.state !== "playing") return;
  if (P.audio) P.audio.pause();
  else if (P.voice) { speechSynthesis.pause(); P.voice.pausedFor = performance.now() - P.voice.t0; }
  P.state = "paused"; render();
}
async function resume() {
  if (P.state !== "paused") return;
  P.state = "playing"; render();
  if (P.voice) P.voice.t0 = performance.now() - (P.voice.pausedFor || 0);
  if (P.audio) { try { await P.audio.play(); capTick(); } catch { stop(); } }
  else if (P.voice) { speechSynthesis.resume(); if (!speechSynthesis.speaking) speakFrom(P.voice.clip, P.voice.pos); }
}
function setSpeed() {
  P.speed = P.speed === 1 ? 1.25 : 1;
  if (P.audio) P.audio.playbackRate = P.speed;
  else if (P.voice && P.state === "playing") speakFrom(P.voice.clip, sentenceStart(P.voice.clip.text, P.voice.pos)); // a new rate needs a new utterance
  render();
}
const sentenceStart = (text, pos) => { const i = text.lastIndexOf(". ", Math.max(0, pos - 1)); return i < 0 ? 0 : i + 2; };

async function play(topic = null) {
  if (!persona()) setPersona("renter"); // plays at once as a renter; the panel header switches to owner
  const k = keyFor(topic);
  if (P.key === k && P.state === "paused") return resume();
  if (P.key === k && P.state === "playing") return pause();
  if (P.key === k && P.state === "loading") return stop();
  stop();
  P.key = k; P.topic = topic; P.state = "loading"; render();
  let clip = null;
  try { clip = await load(k); } catch { clip = null; }
  if (P.key !== k || P.state !== "loading") return; // stopped or moved on meanwhile
  P.clip = clip;
  if (clip?.url && !deviceVoice()) {
    const a = (P.audio = new Audio(clip.url));
    a.playbackRate = P.speed;
    a.addEventListener("timeupdate", trackAudio);
    a.addEventListener("ended", () => { if (P.audio === a) finish(); });
    a.addEventListener("loadedmetadata", () => { if (P.audio === a) capTick(); });
    P.state = "playing"; openCaptions(clip); render();
    try { await a.play(); trackAudio(); capTick(); } catch { if (P.audio === a) stop(); }
  } else if ((clip?.text || clip?.cap?.text) && "speechSynthesis" in window) {
    if (!clip.text) { clip.text = clip.cap.text; clip.lang = k.split("|")[2]; } // recorded clip, device voice forced
    P.state = "playing"; openCaptions(clip); render();
    speakFrom(clip, 0);
  } else stop();
}

// ------------------------------------------------------------------ transcript (time-synced captions)
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)");
const C = { el: null, clip: null, s: -1, w: -1, raf: 0, user: 0, seeking: false, left: false };

async function loadCaptions(k) {
  const [id, asOf, lang, who, topic] = k.split("|");
  const r = await fetch("/api/tts/captions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ address_id: id, as_of: asOf, lang, persona: who, topic: topic || null }),
  });
  if (!r.ok) throw new Error("captions " + r.status);
  return r.json();
}
function splitSentences(text) { // only if the captions request failed: the same rule as the server
  const out = [], re = /(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¿¡'"0-9])/g;
  let start = 0, m;
  while ((m = re.exec(text))) { out.push([start, m.index]); start = m.index + m[0].length; }
  out.push([start, text.length]);
  return out;
}
const fmtTime = (s) => { s = Math.max(0, Math.floor(s || 0)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };

function openCaptions(clip) {
  closeCaptions();
  const cap = clip.cap || (clip.text ? { text: clip.text, sentences: splitSentences(clip.text), words: null, chapters: clip.chapters } : null);
  if (!cap?.text) return;
  const w = words(), text = cap.text;
  const spans = cap.words || [...text.matchAll(/\S+/g)].map((m) => [m.index, m.index + m[0].length]);
  const sents = cap.sentences?.length ? cap.sentences : splitSentences(text);
  const chapterStarts = new Set((cap.chapters || []).map(([, p]) => p));
  const wordSent = [];
  let html = "", j = 0;
  sents.forEach(([a, b], i) => {
    if (i && chapterStarts.has(a)) html += `</p><p class="ce-cap-p">`; // a new topic starts a new paragraph
    let inner = "", at = a;
    for (; j < spans.length && spans[j][0] < b; j++) {
      const [c0, c1] = spans[j];
      inner += esc(text.slice(at, c0)) + `<span class="ce-cap-w">${esc(text.slice(c0, c1))}</span>`;
      at = c1;
      wordSent.push(i);
    }
    html += `<span class="ce-cap-s" data-c="${a}" role="button" tabindex="0" title="${esc(w.jump)}">${inner}${esc(text.slice(at, b))}</span> `;
  });
  const el = document.createElement("section");
  el.className = "ce-cap";
  el.setAttribute("aria-label", w.transcript);
  el.lang = cap.lang || clip.lang || CE.lang();
  el.innerHTML = `<header class="ce-cap-h"><span class="ce-cap-eq" aria-hidden="true"><i></i><i></i><i></i></span>
      <span class="ce-cap-t"><b>${esc(w.listening)}</b></span>${choiceHTML(w, persona())}
      <button type="button" class="ce-cap-x" aria-label="${esc(w.close)}">${ICON.close}</button></header>
    <div class="ce-cap-body"><p class="ce-cap-p">${html}</p></div>
    <footer class="ce-cap-f">
      <button type="button" class="ce-cap-pp"></button>
      <input class="ce-cap-r" type="range" min="0" max="1000" step="1" value="0" aria-label="${esc(w.seek)}">
      <span class="ce-cap-tm" aria-hidden="true"></span>
      <button type="button" class="ce-speed ce-cap-sp" aria-label="${esc(w.speed)}"></button>
    </footer>`;
  document.body.append(el);
  const timed = !!cap.words;
  Object.assign(C, {
    el, clip, cap, text, spans, timed, wordSent, s: -1, w: -1, user: 0,
    sentEls: [...el.querySelectorAll(".ce-cap-s")], wordEls: [...el.querySelectorAll(".ce-cap-w")],
    body: el.querySelector(".ce-cap-body"), range: el.querySelector(".ce-cap-r"), tm: el.querySelector(".ce-cap-tm"),
  });
  const mark = () => { C.user = performance.now(); };
  C.body.addEventListener("wheel", mark, { passive: true });
  C.body.addEventListener("touchmove", mark, { passive: true });
  C.range.addEventListener("input", () => { C.seeking = true; seekFraction(C.range.value / 1000, false); });
  C.range.addEventListener("change", () => { C.seeking = false; seekFraction(C.range.value / 1000, true); });
  document.documentElement.classList.add("ce-cap-open");
  el.classList.add("ce-cap-still"); // pick the corner without animating there; then commit the closed state,
  place(); //                        so the opening always animates (and only the opening)
  void el.offsetWidth;
  el.classList.remove("ce-cap-still");
  void el.offsetWidth;
  el.classList.add("in");
  capRender(w);
  capTick();
}
// Desktop: the panel sits in the bottom-right corner unless that would cover the control that started it (the
// Listen / Pause button, or a topic's Listen); then it takes the bottom-left corner. Rechecked on scroll and resize.
let placeQueued = 0;
function trigger() {
  // the control that started it, with the actions next to it (Check a rent increase, Compare, the topic's actions)
  const m = main();
  if (P.topic) { const x = m?.querySelector(`.ce-explain[data-cat="${P.topic}"]`); return x?.closest(".topic-actions") || x; }
  const x = m?.querySelector(".ce-listen");
  return x?.closest(".prop-cta, [data-slot='address-actions']") || x;
}
function box(el) {
  // the area its controls actually take (a block container spans the whole column)
  let u = null;
  for (const c of el ? [el, ...el.querySelectorAll("a, button")] : []) {
    if (c === el && el.querySelector("a, button")) continue;
    const q = c.getBoundingClientRect();
    if (!q.width) continue;
    u = u ? { left: Math.min(u.left, q.left), top: Math.min(u.top, q.top), right: Math.max(u.right, q.right), bottom: Math.max(u.bottom, q.bottom) } : { left: q.left, top: q.top, right: q.right, bottom: q.bottom };
  }
  return u && { ...u, width: u.right - u.left };
}
function dockLift(el) {
  // the docked Ask bar (features/ask.js) covers the bottom: how far to raise the panel to clear its bar
  const d = document.documentElement.classList.contains("ask-docked") ? document.querySelector(".ask-dock.on") : null;
  const bar = d?.querySelector(".ask-bar");
  if (!bar) return "0px";
  const barTop = innerHeight - parseFloat(getComputedStyle(d).bottom || 0) - d.offsetHeight + bar.offsetTop; // without its slide
  return `${Math.max(0, Math.round(el.offsetTop + el.offsetHeight - (barTop - (innerWidth <= 640 ? 8 : 16))))}px`;
}
function place() {
  placeQueued = 0;
  const el = C.el;
  if (!el) return;
  // above the docked Ask bar: a transform, so neither this nor the bar toggling on scroll is a layout shift
  const lift = dockLift(el);
  if (el.style.getPropertyValue("--cap-lift") !== lift) el.style.setProperty("--cap-lift", lift);
  const r = box(trigger());
  const w = el.offsetWidth, h = el.offsetHeight, gap = 24, pad = 12;
  const top = el.offsetTop - (parseFloat(lift) || 0); // offsetTop ignores transforms (the slide and the lift)
  // room at the end of the page, so nothing stays hidden behind the panel
  document.documentElement.style.setProperty("--cap-room", `${Math.round(innerHeight - top + 16)}px`);
  if (innerWidth <= 640 || !r || !r.width) { side(el, false, w); return; }
  const hits = (q, left) => q && q.width && q.right + pad > left && q.left - pad < left + w && q.bottom + pad > top && q.top - pad < top + h;
  // never its own trigger; and, if a corner allows it, not the address's main actions either
  const cta = box(main()?.querySelector(".prop-cta"));
  const R = document.documentElement.clientWidth - gap - w, L = gap; // clientWidth: without the scrollbar
  const ok = (left) => !hits(r, left), clear = (left) => ok(left) && !hits(cta, left);
  // stay in the current corner while it is clear; move only when it would cover something
  const cur = C.left ? L : R, other = C.left ? R : L;
  const left = clear(cur) ? C.left : clear(other) ? !C.left : ok(cur) ? C.left : ok(other) ? !C.left : false;
  side(el, left, w);
}
function side(el, left, w) {
  // the panel is anchored bottom-right; the left corner is a transform away, so a switch glides instead of jumping
  C.left = left;
  const x = left ? `${-(document.documentElement.clientWidth - 48 - w)}px` : "0px";
  if (el.style.getPropertyValue("--cap-x") !== x) el.style.setProperty("--cap-x", x);
}
const placeSoon = () => { if (C.el && !placeQueued) placeQueued = requestAnimationFrame(place); };
addEventListener("scroll", placeSoon, { passive: true });
addEventListener("resize", placeSoon, { passive: true });
function closeCaptions() {
  if (C.raf) cancelAnimationFrame(C.raf);
  C.raf = 0;
  const el = C.el;
  C.el = null; C.clip = null;
  if (!el) return;
  document.documentElement.classList.remove("ce-cap-open");
  if (reduceMotion.matches) return el.remove();
  el.classList.remove("in");
  el.classList.add("out");
  setTimeout(() => el.remove(), 260);
}
function capRender(w) {
  if (!C.el) return;
  const pp = C.el.querySelector(".ce-cap-pp"), playing = P.state === "playing";
  const html = playing ? ICON.pause : ICON.play;
  if (pp._html !== html) { pp._html = html; pp.innerHTML = html; }
  pp.setAttribute("aria-label", playing ? w.pause : w.play);
  C.el.classList.toggle("is-paused", !playing);
  const sp = C.el.querySelector(".ce-cap-sp"), txt = P.speed === 1 ? "1×" : "1.25×";
  if (sp.textContent !== txt) sp.textContent = txt;
}
// where the voice is: a word index (audio with word times) or a character position (everything else)
function wordAtTime(t) {
  const sp = C.spans;
  let lo = 0, hi = sp.length - 1, ans = -1;
  while (lo <= hi) { const m = (lo + hi) >> 1; if (sp[m][2] <= t) { ans = m; lo = m + 1; } else hi = m - 1; }
  return ans;
}
function wordAtChar(pos) {
  const sp = C.spans;
  let lo = 0, hi = sp.length - 1, ans = 0;
  while (lo <= hi) { const m = (lo + hi) >> 1; if (sp[m][0] <= pos) { ans = m; lo = m + 1; } else hi = m - 1; }
  return ans;
}
const timeScale = (a) => (C.cap?.timing === "estimated" && C.cap.duration && isFinite(a.duration) && a.duration ? a.duration / C.cap.duration : 1);
function capTick() {
  if (C.raf) { cancelAnimationFrame(C.raf); C.raf = 0; }
  if (!C.el) return;
  let j = -1, frac = 0, tm = "";
  const a = P.audio;
  if (a) {
    const d = isFinite(a.duration) ? a.duration : C.cap?.duration || 0;
    frac = d ? a.currentTime / d : 0;
    if (C.timed) j = wordAtTime(a.currentTime / timeScale(a) + 0.04);
    else j = wordAtChar(frac * C.text.length);
    tm = `${fmtTime(a.currentTime)} / ${fmtTime(d)}`;
  } else if (P.voice) {
    let pos = P.voice.pos;
    if (!P.voice.heard && P.state === "playing") { // this voice sends no word boundaries: estimate from time
      pos = P.voice.offset + ((performance.now() - P.voice.t0) / 1000) * 14 * P.speed;
    } else if (!P.voice.heard && P.voice.pausedFor) pos = P.voice.offset + (P.voice.pausedFor / 1000) * 14 * P.speed;
    pos = Math.min(pos, C.text.length - 1);
    j = wordAtChar(pos);
    frac = pos / C.text.length;
    const s = C.wordSent[j] ?? 0;
    tm = `${s + 1} / ${C.sentEls.length}`;
  }
  setWord(j);
  if (!C.seeking) {
    C.range.value = String(Math.round(frac * 1000));
    C.range.style.setProperty("--p", `${(frac * 100).toFixed(2)}%`);
  }
  if (C.tm.textContent !== tm) C.tm.textContent = tm;
  if (P.state === "playing") C.raf = requestAnimationFrame(capTick);
}
function setWord(j) {
  if (j === C.w) return;
  C.wordEls[C.w]?.classList.remove("is-w");
  C.w = j;
  C.wordEls[j]?.classList.add("is-w");
  const s = j < 0 ? 0 : C.wordSent[j] ?? 0;
  if (s === C.s) return;
  C.s = s;
  C.sentEls.forEach((el, i) => { el.classList.toggle("is-on", i === s); el.classList.toggle("is-past", i < s); });
  follow(C.sentEls[s]);
}
function follow(el) {
  if (!el || performance.now() - C.user < 3500) return; // the reader is scrolling: don't fight them
  const body = C.body;
  const top = el.offsetTop - body.clientHeight * 0.28;
  body.scrollTo({ top: Math.max(0, top), behavior: reduceMotion.matches ? "auto" : "smooth" });
}
function seekChar(c) {
  C.user = 0;
  if (P.audio) {
    const a = P.audio;
    let t;
    if (C.timed) { const w = C.spans.find((x) => x[0] >= c) || C.spans[C.spans.length - 1]; t = w[2] * timeScale(a) - 0.03; }
    else t = (c / C.text.length) * (a.duration || 0);
    a.currentTime = Math.max(0, t);
    if (P.state === "paused") resume();
  } else if (P.voice) {
    if (P.state === "paused") { P.state = "playing"; render(); }
    speakFrom(P.voice.clip, c);
  }
  capTick();
}
function seekFraction(f, commit) {
  if (P.audio) {
    const d = P.audio.duration;
    if (d && isFinite(d)) P.audio.currentTime = f * d;
    C.range.style.setProperty("--p", `${(f * 100).toFixed(2)}%`);
    capTick();
  } else if (P.voice && commit) {
    const pos = Math.floor(f * C.text.length);
    const s = C.sentEls.findLast?.((el) => +el.dataset.c <= pos) || C.sentEls[0];
    seekChar(+s.dataset.c);
  }
}
document.addEventListener("click", (e) => {
  if (!C.el?.contains(e.target)) return;
  const t = e.target.closest(".ce-seg-b, .ce-cap-x, .ce-cap-pp, .ce-cap-sp, .ce-cap-s");
  if (!t) return;
  if (t.classList.contains("ce-seg-b")) choose(t.dataset.ceWho);
  else if (t.classList.contains("ce-cap-x")) stop();
  else if (t.classList.contains("ce-cap-pp")) { if (P.state === "playing") pause(); else resume(); }
  else if (t.classList.contains("ce-cap-sp")) setSpeed();
  else seekChar(+t.dataset.c);
});
document.addEventListener("keydown", (e) => {
  const t = e.target.closest?.(".ce-cap-s");
  if (t && C.el?.contains(t) && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); seekChar(+t.dataset.c); }
});

// ------------------------------------------------------------------ markup
function choiceHTML(w, cur) { // segmented "I rent · I own" in the panel header
  return `<span class="ce-seg" role="group" aria-label="${esc(w.as)}">${["renter", "owner"].map((p) =>
    `<button type="button" class="ce-seg-b" data-ce-who="${p}" aria-pressed="${cur === p}">${esc(w[p])}</button>`).join("")}</span>`;
}
function setHTML(el, html) { if (el._html !== html) { el._html = html; el.innerHTML = html; } }
// The Listen controls never change size: every label (and both icons) sit stacked in one grid cell, only the current
// one visible, so the box is as wide as the longest label in this language and its neighbours never move.
const STATES = ["idle", "loading", "playing", "paused"];
const labelOf = (w, st, idle) => (st === "playing" ? w.pause : st === "paused" ? w.resume : st === "loading" ? w.loading : idle);
function stackHTML(w, idle, icons) {
  return (icons ? `<span class="ce-ico" aria-hidden="true"><span data-i="listen">${ICON.listen}</span><span data-i="pause">${ICON.pause}</span></span>` : "") +
    `<span class="ce-lab" aria-hidden="true">${STATES.map((st) => `<span data-st="${st}">${esc(labelOf(w, st, idle))}</span>`).join("")}</span>`;
}
function setState(btn, st, label) {
  if (btn.dataset.st !== st) btn.dataset.st = st;
  btn.setAttribute("aria-label", label);
  btn.toggleAttribute("aria-busy", st === "loading");
}
function render() {
  const w = words();
  capRender(w);
  const box = main()?.querySelector(".ce-listen");
  if (box) {
    const st = !P.topic && P.key ? P.state : "idle";
    const btn = box.querySelector(".ce-l-main");
    setHTML(btn, stackHTML(w, w.listen, true));
    setState(btn, st, st === "idle" ? w.aListen : labelOf(w, st, w.listen));
  }
  for (const b of main()?.querySelectorAll(".ce-explain") || []) {
    const st = P.topic === b.dataset.cat && P.key ? P.state : "idle";
    setHTML(b, stackHTML(w, w.explain, false));
    setState(b, st, labelOf(w, st, w.explain));
  }
}
// focus ring only for keyboard focus: a mouse or touch press on these controls never shows it
addEventListener("pointerdown", (e) => {
  e.target.closest?.(".ce-l-main, .ce-explain, .ce-cap button")?.classList.add("ce-pressed");
}, { capture: true, passive: true });
addEventListener("keydown", (e) => {
  if (e.key === "Tab" || e.key.startsWith("Arrow")) for (const b of document.querySelectorAll(".ce-pressed")) b.classList.remove("ce-pressed");
}, { capture: true });
function inject() {
  const m = main();
  if (!m || !addressId()) return;
  let added = false;
  const slot = m.querySelector('[data-slot="address-actions"]');
  if (slot && !slot.querySelector(".ce-listen")) {
    slot.insertAdjacentHTML("afterbegin", `<span class="ce-listen"><button type="button" class="linkish ce-l-main"></button></span>`);
    added = true;
  }
  for (const s of m.querySelectorAll('.topic-actions[data-slot="topic-actions"][data-cat]')) {
    if (s.querySelector(".ce-explain")) continue;
    s.insertAdjacentHTML("afterbegin", `<button type="button" class="linkish ce-explain" data-cat="${esc(s.dataset.cat)}"></button>`);
    added = true;
  }
  if (added) render(); // only then: render() itself changes the DOM this observer watches
  if (P.state !== "idle" && P.topic) speaking(P.topic); // re-rendered rows keep the highlight
}

document.addEventListener("click", (e) => {
  const t = e.target.closest(".ce-l-main, .ce-explain");
  if (!t || !main()?.contains(t)) return;
  if (t.classList.contains("ce-l-main")) play(null);
  else play(t.dataset.cat);
});
function choose(who) { // remembered; the same briefing or topic starts again for the other side
  const topic = P.topic;
  if (who === persona() && P.state !== "idle") return;
  setPersona(who);
  stop();
  play(topic);
}
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && P.state !== "idle") stop(); });
document.addEventListener("ce:route", () => { if (P.key && !P.key.startsWith(`${addressId()}|`)) stop(); inject(); });
document.addEventListener("ce:asof", () => stop());
document.addEventListener("ce:lang", () => stop());
addEventListener("pagehide", () => stop());
if ("speechSynthesis" in window) speechSynthesis.getVoices(); // voices load lazily in some browsers
function start() {
  inject();
  new MutationObserver(() => inject()).observe(main(), { childList: true, subtree: true });
}
if (window.CE) start(); else document.addEventListener("ce:ready", start, { once: true });
