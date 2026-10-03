"""Playwright QA screenshots for My properties (#38), desktop 1440 + mobile 390.

Server (same env as this script, so the QA user's session cookie verifies):
  NAVIGATOR_ACCOUNTS_DB=/tmp/qa/accounts.db NAVIGATOR_SESSION_SECRET=/tmp/qa/secret \
    uv run uvicorn web.app:app --port 8802
Run:
  NAVIGATOR_ACCOUNTS_DB=/tmp/qa/accounts.db NAVIGATOR_SESSION_SECRET=/tmp/qa/secret BASE=http://127.0.0.1:8802/ \
    uv run --with playwright python tests/shots_my_properties.py          (PNGs -> $SHOTS_DIR)

Flow: signed out -> Google button goes to accounts.google.com (not followed further) -> demo landlord (read-only) ->
list -> detail -> calendar feed; then a QA user (session minted locally, never Google) adds a property through the
real /api/resolve (live US Census) + facts sheet, edits facts and deletes the account.
"""

import asyncio
import os
import sys
from pathlib import Path

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from web import accounts as A  # noqa: E402

BASE = os.environ.get("BASE", "http://127.0.0.1:8802/")
OUT = os.environ.get("SHOTS_DIR", "/home/steward/share/hacknation/qa/my-properties")
os.makedirs(OUT, exist_ok=True)
ADDR = "6238 De Longpre Ave, Los Angeles, CA 90028"


async def run(b, w, h, tag, errors):
    ctx = await b.new_context(
        viewport={"width": w, "height": h}, device_scale_factor=2 if w < 500 else 1
    )
    pg = await ctx.new_page()
    pg.on("console", lambda m: errors.append(f"{tag} {m.text}") if m.type == "error" else None)
    pg.on("pageerror", lambda e: errors.append(f"{tag} PAGEERROR {e}"))

    async def shot(name, full=False):
        if full:  # reveal-on-scroll content: scroll through once, then back to the top
            await pg.evaluate(
                "async () => { for (let y = 0; y < document.body.scrollHeight; y += 500) {"
                " scrollTo(0, y); await new Promise((r) => setTimeout(r, 60)); } scrollTo(0, 0); }"
            )
            await pg.wait_for_timeout(900)
        await pg.screenshot(path=f"{OUT}/{tag}-{name}.png", full_page=full)
        print("saved", f"{tag}-{name}.png")

    # 1 signed out
    await pg.goto(BASE + "#/properties")
    await pg.wait_for_selector(".mp-hero .gsi")
    await pg.wait_for_timeout(1400)
    await shot("01-signed-out")
    href = await pg.get_attribute(".mp-hero .gsi", "href")
    r = await ctx.request.get(BASE.rstrip("/") + href, max_redirects=0)
    loc = r.headers.get("location", "")
    assert r.status == 302 and loc.startswith("https://accounts.google.com/"), (r.status, loc[:60])
    assert "code_challenge_method=S256" in loc and "scope=openid+email+profile" in loc
    print(tag, "google login redirects to accounts.google.com with PKCE")

    # 2 demo landlord
    await pg.click(".mp-demo")
    await pg.wait_for_selector(".mp-card")
    await pg.wait_for_timeout(1300)
    await shot("02-demo-list")
    await shot("03-demo-list-full", full=True)

    # 3 detail (Hoboken: FAIR Act takes effect, one unknown a fact would resolve)
    await pg.click(".mp-card:has-text('Bloomfield')")
    await pg.wait_for_selector(".mp-tl")
    await pg.wait_for_selector(".mp-answers .rule")
    await pg.wait_for_timeout(1300)
    await shot("04-demo-detail")
    await shot("05-demo-detail-full", full=True)
    await pg.click(".crumbs .back")
    await pg.wait_for_selector(".mp-card")
    await pg.click(".mp-card:has-text('Fulton')")
    await pg.wait_for_selector(".mp-tl")
    await pg.wait_for_timeout(1000)
    await shot("06-demo-detail-sf")

    # 4 calendar feed
    ics = await ctx.request.get(BASE + "cal/demo.ics")
    body = await ics.text()
    assert ics.ok and body.startswith("BEGIN:VCALENDAR") and "BEGIN:VEVENT" in body
    print(tag, "demo calendar feed:", body.count("BEGIN:VEVENT"), "events")
    await ctx.close()

    # 5 QA user (no Google): add a property via live resolve, edit facts, delete account
    uid = A.upsert_google_user(f"qa:{tag}", f"qa-{tag}@example.com", "QA Tester")
    ctx = await b.new_context(
        viewport={"width": w, "height": h}, device_scale_factor=2 if w < 500 else 1
    )
    host = BASE.split("//")[1].split("/")[0].split(":")[0]
    token = A.sign("session", {"uid": uid, "sid": f"qa-{tag}"}, 3600)
    await ctx.add_cookies([{"name": A.SESSION_COOKIE, "value": token, "domain": host, "path": "/"}])
    pg = await ctx.new_page()
    pg.on("console", lambda m: errors.append(f"{tag} {m.text}") if m.type == "error" else None)
    pg.on("pageerror", lambda e: errors.append(f"{tag} PAGEERROR {e}"))
    await pg.goto(BASE + "#/properties")
    await pg.wait_for_selector("[data-add]")
    await pg.wait_for_timeout(900)
    await shot("07-empty-account")
    await pg.click("[data-add]")
    await pg.fill(".mp-form [name=address]", ADDR)
    await shot("08-add-address")
    await pg.click(".mp-form [type=submit]")
    await pg.wait_for_selector("[data-step=facts] [name=year_built]", timeout=20000)
    await pg.fill("[data-step=facts] [name=year_built]", "1927")
    await pg.fill("[data-step=facts] [name=units]", "32")
    await pg.click("[data-step=facts] [data-oo=no]")
    await pg.wait_for_selector(".mp-preview .badge")
    await pg.wait_for_timeout(900)
    await shot("09-add-facts")
    await pg.click("[data-step=facts] [type=submit]")
    await pg.wait_for_selector(".mp-tl")
    await pg.wait_for_timeout(1200)
    await shot("10-added-detail")
    await pg.click(".mp-side [data-edit]")
    await pg.wait_for_selector(".modal-body .mp-preview .badge")
    await pg.wait_for_timeout(700)
    await shot("11-edit-facts")
    await pg.click(".modal [data-close]")
    await pg.click(".crumbs .back")
    await pg.wait_for_selector(".mp-card")
    await pg.wait_for_timeout(1000)
    await shot("12-own-list", full=True)
    await pg.click(".mp-menu summary")
    await pg.wait_for_timeout(400)
    await shot("13-account-menu")
    await pg.click("[data-delacct]")
    await pg.wait_for_timeout(500)
    await shot("14-delete-account")
    await pg.click(".modal [data-go]")
    await pg.wait_for_selector(".mp-hero .gsi")
    print(tag, "account deleted, back to sign-in")
    await ctx.close()


async def main():
    errors = []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        await run(b, 1440, 900, "desktop", errors)
        await run(b, 390, 844, "mobile", errors)
        await b.close()
    print("console errors:", errors or "none")


asyncio.run(main())
