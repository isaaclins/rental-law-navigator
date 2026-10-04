// node ui.mjs <base> <outdir> [chromium|webkit] : the letter and notice views in a real browser: fill the fields, download the
// PDF (desktop) or build the share file (iPhone), print through the Print button (print CSS, Chromium), screenshots
import { chromium, webkit, devices } from "/home/steward/hacknation/teamvideo/node_modules/playwright-core/index.mjs";
import fs from "node:fs";
const [base, out, bname = "chromium"] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const b = await ({ chromium, webkit })[bname].launch();
const errs = [];
const ctxs = { desktop: { viewport: { width: 1440, height: 1000 }, acceptDownloads: true }, phone: { ...devices["iPhone 13"], acceptDownloads: true } };
for (const [form, opts] of Object.entries(ctxs)) {
  if (bname === "chromium" && form === "phone") delete opts.defaultBrowserType;
  const ctx = await b.newContext(opts);
  // the share sheet (iPhone): stubbed before the page loads, so the Send button shows and its file can be checked
  if (form === "phone") await ctx.addInitScript(() => { navigator.canShare = () => true; navigator.share = async (d) => { const f = d.files?.[0]; window.__shared = f ? { n: f.name, size: f.size, type: f.type, head: new TextDecoder().decode((await f.arrayBuffer()).slice(0, 8)) } : { text: !!d.text }; }; });
  const pg = await ctx.newPage();
  pg.on("pageerror", (e) => errs.push(`${form}: ${e}`));
  pg.on("console", (m) => m.type() === "error" && errs.push(`${form}: ${m.text()}`));
  const tag = `${bname}-${form}`;
  // the letter, from a rent check
  await pg.goto(base + "#/check/A0027");
  await pg.waitForSelector(".ck-form");
  await pg.fill("#ck-current_rent", "2400");
  await pg.fill("#ck-new", "2520");
  await pg.fill("#ck-notice_date", "2026-09-20");
  await pg.fill("#ck-effective_date", "2026-11-01");
  await pg.click(".ck-actions .btn");
  await pg.waitForSelector(".lt-go");
  await pg.click(".lt-go");
  await pg.waitForSelector(".lt-sheet .lt-in");
  await pg.waitForTimeout(1500);
  const fill = async (f, v) => pg.locator(`.lt-f[data-f="${f}"]`).first().fill(v);
  await fill("name", "Isaac Lins"); await fill("unit", "22"); await fill("landlord", "Pacific Heights Property Management");
  await fill("landlord_street", "1500 Van Ness Ave, Suite 300"); await fill("landlord_city", "San Francisco, CA 94109");
  const h = await pg.evaluate(() => [...document.querySelectorAll(".lt-f")].map((e) => Math.round(e.getBoundingClientRect().height)));
  console.log(tag, "field heights", h.join(","));
  await pg.screenshot({ path: `${out}/${tag}-letter.png`, fullPage: true });
  await pg.waitForFunction(() => true);
  if (form === "desktop") {
    const [dl] = await Promise.all([pg.waitForEvent("download"), pg.click(".lt-acts-d [data-act=pdf]")]);
    await dl.saveAs(`${out}/${tag}-letter-download.pdf`);
    if (bname === "chromium") {
      await pg.evaluate(() => (window.print = () => {}));
      await pg.click(".lt-acts-d [data-act=print]");
      await pg.waitForSelector(".pp-print .pp", { state: "attached" });
      await pg.emulateMedia({ media: "print" });
      await pg.pdf({ path: `${out}/${tag}-letter-print.pdf`, format: "Letter", preferCSSPageSize: true });
      await pg.emulateMedia({ media: "screen" });
    }
  } else {
    // iPhone: the share sheet gets a PDF file (navigator.share stubbed to capture it)
    const sh = pg.locator(".lt-acts-m [data-act=share]");
    if (await sh.isVisible()) { await sh.click(); await pg.waitForTimeout(800); console.log(tag, "shared", JSON.stringify(await pg.evaluate(() => window.__shared))); }
    else console.log(tag, "share button hidden");
  }
  // the notice
  await pg.goto(base + "#/notice/A0027?rent=2400&last=2025-11-01");
  await pg.waitForSelector(".lt-sheet .lt-in");
  await pg.waitForTimeout(1200);
  await pg.locator('.lt-f[data-f="tenant"]').first().fill("Isaac Lins");
  await pg.locator('.lt-f[data-f="unit"]').first().fill("22");
  await pg.locator('.lt-f[data-f="owner"]').first().fill("Pacific Heights Property Management");
  console.log(tag, "rent field shows", await pg.inputValue('input[name="rent"]'));
  await pg.screenshot({ path: `${out}/${tag}-notice.png`, fullPage: true });
  if (form === "desktop") {
    const [dl] = await Promise.all([pg.waitForEvent("download"), pg.click(".lt-acts-d [data-act=pdf]")]);
    await dl.saveAs(`${out}/${tag}-notice-download.pdf`);
    if (bname === "chromium") {
      await pg.evaluate(() => (window.print = () => {}));
      await pg.click(".lt-acts-d [data-act=print]");
      await pg.waitForTimeout(300);
      await pg.emulateMedia({ media: "print" });
      await pg.pdf({ path: `${out}/${tag}-notice-print.pdf`, format: "Letter", preferCSSPageSize: true });
      await pg.emulateMedia({ media: "screen" });
    }
  }
  await ctx.close();
}
console.log(errs.length ? "ERRORS " + errs.join("\n") : "no page errors");
await b.close();
