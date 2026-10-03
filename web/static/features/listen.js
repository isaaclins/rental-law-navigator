// Listen to the answer (#49): one quiet "Listen" button under the address header reads the summary aloud
// (address, as-of date, one line per topic, "not legal advice") in the current language.
// Voice: POST /api/tts builds the text on the server and returns a cached ElevenLabs mp3. When it answers with
// {fallback, text} instead (budget, limits, outage), the browser's own voice reads that same text.
// Keyboard: it is a native button (Enter / Space); Esc pauses. Changing address, date or language stops it.
const L = {
  en: { listen: "Listen", stop: "Stop", aListen: "Listen to this answer", aStop: "Stop reading the answer" },
  es: { listen: "Escuchar", stop: "Detener", aListen: "Escuchar esta respuesta", aStop: "Dejar de leer la respuesta" },
};
const ICON = {
  listen: '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9.5v5h3.5L12 18V6L7.5 9.5H4z"/><path d="M15.5 9a4.2 4.2 0 0 1 0 6"/><path d="M18.2 6.5a8 8 0 0 1 0 11"/></svg>',
  stop: '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>',
};
const words = () => L[window.CE?.lang?.() === "es" ? "es" : "en"];
const clips = new Map(); // "<id>|<asOf>|<lang>" -> {url} (object URL of the mp3) or {text, lang} (browser voice)
let audio = null, key = null, playing = false, pending = null, btn = null;

function addressId() {
  const m = location.hash.match(/^#\/a\/([^/?#]+)/);
  return m ? decodeURIComponent(m[1]).toUpperCase() : null;
}
const currentKey = () => `${addressId()}|${CE.asOf()}|${CE.lang()}`;

function render() {
  if (!btn) return;
  const w = words(), on = playing || !!pending;
  btn.innerHTML = `${on ? ICON.stop : ICON.listen}<span>${on ? w.stop : w.listen}</span>`;
  btn.setAttribute("aria-label", on ? w.aStop : w.aListen);
  btn.toggleAttribute("aria-busy", !!pending && !playing);
}
function setPlaying(v) { playing = v; render(); }

function stop({ reset = false } = {}) {
  pending = null;
  if (audio) { audio.pause(); if (reset) { audio.removeAttribute("src"); audio.load(); audio = null; } }
  if ("speechSynthesis" in window) speechSynthesis.cancel();
  if (reset) key = null;
  setPlaying(false);
}

async function load(k) {
  if (clips.has(k)) return clips.get(k);
  const [id, asOf, lang] = k.split("|");
  const r = await fetch("/api/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ address_id: id, as_of: asOf, lang }),
  });
  let clip;
  if (r.ok && (r.headers.get("content-type") || "").startsWith("audio/")) clip = { url: URL.createObjectURL(await r.blob()) };
  else if (r.ok) { const d = await r.json(); clip = { text: d.text, lang: d.lang || lang }; }
  else throw new Error("tts " + r.status);
  clips.set(k, clip);
  return clip;
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
function speak(clip) {
  if (!("speechSynthesis" in window) || !clip.text) { setPlaying(false); return; }
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(clip.text);
  u.lang = clip.lang === "es" ? "es-US" : "en-US";
  const v = pickVoice(clip.lang);
  if (v) u.voice = v;
  u.rate = 1;
  u.onend = u.onerror = () => { if (key === clip.key) setPlaying(false); };
  clip.key = key;
  speechSynthesis.speak(u);
  setPlaying(true);
}

async function toggle() {
  if (playing || pending) { stop(); return; }
  const k = currentKey();
  if (k !== key) stop({ reset: true });
  key = k;
  if (audio && audio.src && !audio.ended) { // resume where Esc or Stop paused it
    try { await audio.play(); setPlaying(true); } catch { setPlaying(false); }
    return;
  }
  const ticket = (pending = {});
  render();
  let clip;
  try { clip = await load(k); } catch { clip = null; }
  if (pending !== ticket || key !== k) return; // stopped or moved on meanwhile
  pending = null;
  if (clip?.url) {
    audio = new Audio(clip.url);
    audio.addEventListener("ended", () => { audio.currentTime = 0; setPlaying(false); });
    audio.addEventListener("pause", () => setPlaying(false));
    audio.addEventListener("play", () => setPlaying(true));
    try { await audio.play(); } catch { setPlaying(false); }
  } else if (clip?.text) speak(clip);
  else setPlaying(false);
}

function inject() {
  const main = document.getElementById("main");
  const slot = addressId() && main?.querySelector('[data-slot="address-actions"]');
  if (!slot || slot.querySelector(".ce-listen")) return;
  btn = document.createElement("button");
  btn.type = "button";
  btn.className = "linkish ce-listen";
  btn.addEventListener("click", toggle);
  slot.prepend(btn);
  render();
}

function onRoute() {
  if (key && key !== currentKey()) stop({ reset: true }); // other address, date or language
  else if (!addressId()) stop();
  inject();
}
document.addEventListener("ce:route", onRoute);
document.addEventListener("ce:asof", () => stop({ reset: true }));
document.addEventListener("ce:lang", () => stop({ reset: true }));
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && (playing || pending)) stop(); });
addEventListener("pagehide", () => stop());
if ("speechSynthesis" in window) speechSynthesis.getVoices(); // voices load lazily in some browsers
if (window.CE) onRoute(); else document.addEventListener("ce:ready", onRoute, { once: true });
