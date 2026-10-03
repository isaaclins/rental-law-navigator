// Clause & Effect service worker (#44). Served by web/app.py at /sw.js (scope "/"), with __BUILD_ID__ replaced by a
// hash over all static files. A deploy that changes the front end changes this file, so browsers install the new
// worker, which drops every cache of the old build.
//
// Strategies
//   navigations ("/")        network-first; offline: cached app shell, else /static/offline.html
//   /api/address/*           network-first; the last 20 answers are kept for offline reading (survive deploys)
//   other /api/*             network-first; last good copy per build (meta, addresses, i18n, lists)
//   /static/*?v=<hash>       stale-while-revalidate (content-addressed, so never stale code)
//   other /static/*          network-first (fonts, icons)
//   sign-in and per-user routes (#38) are never touched: they always go to the network.
const BUILD = "__BUILD_ID__";
const SHELL = `ce-shell-${BUILD}`;
const API = `ce-api-${BUILD}`;
const ANSWERS = "ce-answers-v1";
const MAX_ANSWERS = 20;
const MAX_API = 40;
const OFFLINE = "/static/offline.html";
const MUST = ["/", OFFLINE];
const NICE = [
  "/manifest.webmanifest",
  "/static/icons/icon-192.png",
  "/static/icons/apple-touch-icon.png",
  "/static/fonts/InterVariable.woff2",
  "/api/meta",
  "/api/addresses",
];
const BYPASS = /^\/(auth|login|logout|oauth2?|api\/(auth|me|user|users|account|properties|session|alerts))(\/|$)/;

self.addEventListener("install", (e) => {
  e.waitUntil((async () => {
    const shell = await caches.open(SHELL);
    const api = await caches.open(API);
    // the shell page decides which hashed assets belong to this build
    const page = await fetch("/", { cache: "reload" });
    if (!page.ok) throw new Error("shell " + page.status);
    const html = await page.clone().text();
    await shell.put("/", page);
    const hashed = [...html.matchAll(/(?:href|src)="(\/static\/[^"]+\?v=[^"]+)"/g)].map((m) => m[1]);
    await shell.addAll([OFFLINE, ...new Set(hashed)]);
    await Promise.all(NICE.map(async (u) => {
      try {
        const r = await fetch(u, { cache: "reload" });
        if (r.ok) await (u.startsWith("/api/") ? api : shell).put(u, r);
      } catch { /* optional */ }
    }));
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    const keep = new Set([SHELL, API, ANSWERS]);
    for (const k of await caches.keys()) if (k.startsWith("ce-") && !keep.has(k)) await caches.delete(k);
    if (self.registration.navigationPreload) await self.registration.navigationPreload.enable();
    await self.clients.claim();
  })());
});

self.addEventListener("message", (e) => {
  if (e.data === "build") e.source?.postMessage({ type: "build", build: BUILD });
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin || BYPASS.test(url.pathname)) return;
  if (req.mode === "navigate") return e.respondWith(navigate(e, url));
  if (url.pathname.startsWith("/api/address/")) return e.respondWith(answer(e, url));
  if (url.pathname.startsWith("/api/")) return e.respondWith(networkFirst(req, API, MAX_API));
  if (url.pathname.startsWith("/static/") && url.searchParams.has("v")) return e.respondWith(swr(e, req));
  if (url.pathname.startsWith("/static/") || url.pathname === "/manifest.webmanifest") {
    return e.respondWith(networkFirst(req, SHELL));
  }
});

async function navigate(e, url) {
  try {
    const res = (await e.preloadResponse) || (await fetch(e.request));
    if (res.ok && url.pathname === "/") (await caches.open(SHELL)).put("/", res.clone());
    return res;
  } catch {
    const shell = await caches.open(SHELL);
    const hit = (url.pathname === "/" && (await shell.match("/"))) || (await shell.match(OFFLINE));
    return hit || new Response("Offline", { status: 503, headers: { "Content-Type": "text/plain" } });
  }
}

async function answer(e, url) {
  const c = await caches.open(ANSWERS);
  try {
    const res = await fetch(e.request);
    if (res.ok) {
      const copy = new Response(await res.clone().blob(), {
        headers: { "Content-Type": "application/json", "X-Saved-At": new Date().toISOString() },
      });
      await c.delete(e.request); // re-insert so key order = recency
      await c.put(e.request, copy);
      await trim(c, MAX_ANSWERS);
      (await self.clients.get(e.clientId))?.postMessage({ type: "fresh-answer", path: url.pathname });
    }
    return res;
  } catch {
    // exact match first, else the same address saved for another date or language (newest first)
    let hit = await c.match(e.request);
    if (!hit) {
      const k = (await c.keys()).reverse().find((r) => new URL(r.url).pathname === url.pathname);
      if (k) hit = await c.match(k);
    }
    if (!hit) return json503();
    const client = await self.clients.get(e.clientId);
    client?.postMessage({ type: "offline-answer", path: url.pathname, savedAt: hit.headers.get("X-Saved-At") });
    return hit;
  }
}

async function networkFirst(req, name, max) {
  const c = await caches.open(name);
  try {
    const res = await fetch(req);
    if (res.ok) {
      await c.put(req, res.clone());
      if (max) await trim(c, max);
    }
    return res;
  } catch (err) {
    const hit = await c.match(req, { ignoreVary: true });
    if (hit) return hit;
    if (req.url.includes("/api/")) return json503();
    throw err;
  }
}

async function swr(e, req) {
  const c = await caches.open(SHELL);
  const hit = await c.match(req);
  const net = fetch(req).then((res) => {
    if (res.ok) c.put(req, res.clone());
    return res;
  });
  if (hit) {
    e.waitUntil(net.catch(() => {}));
    return hit;
  }
  return net;
}

async function trim(c, max) {
  const keys = await c.keys();
  for (const k of keys.slice(0, Math.max(0, keys.length - max))) await c.delete(k);
}

function json503() {
  return new Response(JSON.stringify({ detail: "offline" }), {
    status: 503,
    headers: { "Content-Type": "application/json" },
  });
}
