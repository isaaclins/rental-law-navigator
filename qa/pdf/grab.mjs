// node grab.mjs <base> <outdir> [browser=chromium] [filter]: runs the site's own PDF code in a real browser per scenario
import { chromium, webkit } from "/home/steward/hacknation/teamvideo/node_modules/playwright-core/index.mjs";
import fs from "node:fs";
const [base, out, bname = "chromium", filter = ""] = process.argv.slice(2);
const S = JSON.parse(fs.readFileSync(new URL("./scenarios.json", import.meta.url), "utf8")).filter((s) => s.name.includes(filter));
const b = await ({ chromium, webkit })[bname].launch();
const pg = await (await b.newContext({ viewport: { width: 1280, height: 900 } })).newPage();
const errs = [];
pg.on("pageerror", (e) => errs.push(String(e)));
pg.on("console", (m) => m.type() === "error" && errs.push(m.text()));
await pg.goto(base);
await pg.waitForFunction(() => window.CE);
fs.mkdirSync(out, { recursive: true });
for (const s of S) {
  const b64 = await pg.evaluate(async (s) => {
    const m = await import("/static/features/letter.js");
    const url = s.kind === "letter" ? "/api/letter" : "/api/notice";
    const body = s.kind === "letter" ? { letter_date: "2026-10-04", ...s.body } : { as_of: "2026-10-04", ...s.body };
    const d = await m.post(url, body);
    const blob = await m.letterPdf(d, s.vals);
    const buf = new Uint8Array(await blob.arrayBuffer());
    let bin = ""; for (const x of buf) bin += String.fromCharCode(x);
    return btoa(bin);
  }, s);
  fs.writeFileSync(`${out}/${s.name}.pdf`, Buffer.from(b64, "base64"));
  console.log("ok", s.name);
}
if (errs.length) console.log("ERRORS", errs);
await b.close();
