// Renders "How this answer was made" with features/howmade.js in a stub DOM (tests/test_howmade.py).
// argv: JSON {kind: "topic", d, cat, lang, howmade?, ans?} or {kind: "ask", cite, lang}
const noop = () => {};
const store = {};
globalThis.document = { addEventListener: noop };
globalThis.window = globalThis;
globalThis.localStorage = { getItem: (k) => store[k] ?? null, setItem: (k, v) => { store[k] = String(v); } };
window.CE = { lang: () => "en", fmtDate: (d) => String(d).slice(0, 10) };
const arg = JSON.parse(process.argv[2]);
if (arg.ans) store["ce.ans"] = JSON.stringify(arg.ans);
const ok = arg.howmade;
globalThis.fetch = async () => ({ ok: !!ok, json: async () => ok });
globalThis.location = { origin: "http://test" };
await import(new URL("../web/static/features/howmade.js", import.meta.url));
await window.CEHowMade.load();
if (arg.kind === "ask") process.stdout.write(window.CEHowMade.askLine(arg.cite, arg.lang));
else {
  const c = arg.d.categories.find((x) => x.id === arg.cat);
  process.stdout.write(window.CEHowMade.html(c, arg.d, { lang: arg.lang }));
}
