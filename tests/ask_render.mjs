// Renders an /api/ask response with features/ask.js in a stub DOM and prints the markup (tests/test_ask.py).
const noop = () => {};
const el = () => ({ addEventListener: noop, append: noop, prepend: noop, after: noop, querySelector: () => null, querySelectorAll: () => [], dataset: {}, classList: { add: noop, remove: noop, toggle: noop }, setAttribute: noop });
globalThis.document = { querySelector: () => null, querySelectorAll: () => [], addEventListener: noop, createElement: el, body: { contains: () => false, append: noop }, documentElement: el(), title: "" };
globalThis.matchMedia = () => ({ matches: true });
globalThis.addEventListener = noop;
globalThis.window = globalThis;
globalThis.history = { replaceState: noop };
globalThis.location = { hash: "" };
window.CE = { lang: () => "en", addRoute: noop, api: async () => ({}), fmtDate: (d) => d, asOf: () => "2026-10-01", toast: noop, navigate: noop };
const res = JSON.parse(process.argv[2]);
await import(new URL("../web/static/features/ask.js", import.meta.url));
process.stdout.write(window.CEAsk._answerHTML(res));
