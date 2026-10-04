// Read a text aloud with the device voice (speechSynthesis): the letter, the notice and the rent-check verdict.
// The device voice on purpose: the letter holds the names the reader typed, and they never leave this device.
// sayButton(label) is the markup; bindSay(root, getText, getLang) wires every [data-act="listen"] under root.
// No speech support: the buttons stay hidden.

const ok = () => "speechSynthesis" in window && typeof SpeechSynthesisUtterance === "function";
const svg = (p) => `<svg class="ico" viewBox="0 0 24 24" aria-hidden="true">${p}</svg>`;
const I = {
  play: svg('<path d="M11 5 6 9H3v6h3l5 4V5z"/><path d="M15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13"/>'),
  stop: svg('<rect x="7" y="7" width="10" height="10" rx="1.5"/>'),
};
const W = { en: { listen: "Listen", stop: "Stop" }, es: { listen: "Escuchar", stop: "Detener" } };
const w = (l) => W[l === "es" ? "es" : "en"];

export function sayButton(lang, cls = "btn") {
  if (!ok()) return "";
  return `<button type="button" class="${cls} ce-say" data-act="listen" aria-pressed="false">${I.play}<span>${w(lang).listen}</span></button>`;
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

let current = null; // the button that is speaking
function setBtn(b, on) {
  if (!b) return;
  const lang = window.CE?.lang?.() || "en"; // labels in the page language; the voice reads in the text's language
  b.setAttribute("aria-pressed", String(on));
  b.innerHTML = `${on ? I.stop : I.play}<span>${on ? w(lang).stop : w(lang).listen}</span>`;
}
export function stopSay() {
  if (!ok()) return;
  speechSynthesis.cancel();
  if (current) setBtn(current.b, false);
  current = null;
}

export function bindSay(root, getText, getLang) {
  if (!ok()) return;
  speechSynthesis.getVoices(); // voices load lazily in some browsers
  root.addEventListener("click", (e) => {
    const b = e.target.closest('[data-act="listen"]');
    if (!b || !root.contains(b)) return;
    const lang = getLang() === "es" ? "es" : "en";
    if (current?.b === b) { stopSay(); return; }
    stopSay();
    // paragraph by paragraph: long single utterances stall on some phones
    const parts = String(getText() || "").split(/\n\s*\n|\n/).map((s) => s.trim()).filter(Boolean);
    if (!parts.length) return;
    current = { b, lang };
    setBtn(b, true);
    const v = pickVoice(lang);
    parts.forEach((p, i) => {
      const u = new SpeechSynthesisUtterance(p);
      u.lang = lang === "es" ? "es-US" : "en-US";
      if (v) u.voice = v;
      if (i === parts.length - 1) u.onend = () => { if (current?.b === b) { setBtn(b, false); current = null; } };
      u.onerror = (ev) => { if (ev.error !== "interrupted" && ev.error !== "canceled" && current?.b === b) { setBtn(b, false); current = null; } };
      speechSynthesis.speak(u);
    });
  });
}
// leaving the page ends the reading
window.addEventListener("hashchange", () => { if (current) stopSay(); });
