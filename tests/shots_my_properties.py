"""Playwright QA screenshots for My properties (#38, #152), desktop 1440 + mobile 390.

Server (same env as this script, so the QA user's session cookie verifies):
  NAVIGATOR_ACCOUNTS_DB=/tmp/qa/accounts.db NAVIGATOR_SESSION_SECRET=/tmp/qa/secret \
    uv run uvicorn web.app:app --port 8802
Run:
  NAVIGATOR_ACCOUNTS_DB=/tmp/qa/accounts.db NAVIGATOR_SESSION_SECRET=/tmp/qa/secret BASE=http://127.0.0.1:8802/ \
    uv run --with playwright python tests/shots_my_properties.py          (PNGs -> $SHOTS_DIR)

Flow: signed out -> the example portfolio opens by itself (banner + Google button, which goes to accounts.google.com,
not followed further) -> dashboard (summary, Coming up, building cards) -> one-tap answer (preview, not saved) ->
Why sheet -> one building -> calendar feed; then a QA user (session minted locally, never Google) adds a sample
address through the instant typeahead (with undo), enters the last raise and rent, edits facts and deletes the account.
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


async def run(b, w, h, tag, errors):
    ctx = await b.new_context(
        viewport={"width": w, "height": h}, device_scale_factor=2 if w < 500 else 1
    )
    pg = await ctx.new_page()
    pg.on("console", lambda m: errors.append(f"{tag} {m.text}") if m.type == "error" else None)
    pg.on("pageerror", lambda e: errors.append(f"{tag} PAGEERROR {e}"))

    async def shot(name, full=False):
        await pg.screenshot(path=f"{OUT}/{tag}-{name}.png", full_page=full)
        print("saved", f"{tag}-{name}.png")

    # 1 signed out: the example portfolio
    await pg.goto(BASE + "#/properties")
    await pg.wait_for_selector(".mp-exbar")
    await pg.wait_for_selector(".mp-card[data-pid]")
    await pg.wait_for_timeout(1400)
    await shot("01-example")
    await shot("02-example-full", full=True)
    href = await pg.get_attribute(".mp-exbar .gsi", "href")
    r = await ctx.request.get(BASE.rstrip("/") + href, max_redirects=0)
    loc = r.headers.get("location", "")
    assert r.status == 302 and loc.startswith("https://accounts.google.com/"), (r.status, loc[:60])
    assert "code_challenge_method=S256" in loc and "scope=openid+email+profile" in loc
    print(tag, "google login redirects to accounts.google.com with PKCE")
    assert await pg.locator(".mp-stats .mp-stat").count() == 4
    assert "Fulton" in await pg.inner_text(".mp-coming")

    # 2 one-tap answer on the example (Hoboken: does the owner live there?), not saved
    card = pg.locator(".mp-card:has-text('Bloomfield')")
    await card.locator("[data-ans='true']").click()
    await pg.wait_for_timeout(1200)
    await shot("03-answered")

    # 3 why sheet (#152)
    await pg.locator(".mp-card:has-text('Fulton') [data-why]").first.click()
    await pg.wait_for_selector("#modal .mp-why .quote")
    await pg.wait_for_timeout(500)
    await shot("04-why")
    await pg.click("#modal [data-close]")

    # 4 one building
    await pg.locator(".mp-card:has-text('Fulton') .mp-name a").click()
    await pg.wait_for_selector(".mp-tl")
    await pg.wait_for_selector(".mp-answers .topic, .mp-answers [data-cat]")
    await pg.wait_for_timeout(1200)
    await shot("05-building", full=True)

    # 5 calendar feed
    ics = await ctx.request.get(BASE + "cal/demo.ics")
    body = await ics.text()
    assert ics.ok and body.startswith("BEGIN:VCALENDAR") and "Send rent notice" in body
    print(tag, "demo calendar feed:", body.count("BEGIN:VEVENT"), "events")
    await ctx.close()

    # 6 QA user (no Google): add through the typeahead, undo, add again, rent, edit facts, delete the account
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
    await pg.wait_for_selector(".mp-ta input")
    await pg.wait_for_timeout(900)
    await shot("06-empty-account")
    await pg.locator(".mp-ta input").type("fulton st", delay=30)
    await pg.wait_for_selector(".mp-ta-list .opt[data-i]")
    await shot("07-typeahead")
    await pg.keyboard.press("Enter")
    await pg.wait_for_selector(".mp-undo")
    await shot("08-added")
    await pg.click(".mp-undo button")
    await pg.wait_for_function("!document.querySelector('.mp-card[data-pid]')")
    await pg.locator(".mp-ta input").type("fulton st", delay=30)
    await pg.wait_for_selector(".mp-ta-list .opt[data-i]")
    await pg.keyboard.press("Enter")
    await pg.wait_for_selector(".mp-card[data-pid]")
    await pg.click(".mp-card[data-pid] [data-rent]")
    await pg.fill("[name=last_increase_date]", "2026-01-01")
    await pg.fill("[name=current_rent]", "2400")
    await pg.click("[data-rentform] [type=submit]")
    await pg.wait_for_selector(".mp-card[data-pid] .mp-raise [data-why]")
    await pg.wait_for_timeout(1200)
    await shot("09-own-list", full=True)
    await pg.locator(".mp-card[data-pid] .mp-name a").click()
    await pg.wait_for_selector(".mp-detail [data-edit]")
    await pg.click(".mp-detail [data-edit]")
    await pg.wait_for_selector(".modal-body .mp-preview .badge")
    await pg.wait_for_timeout(700)
    await shot("10-edit-facts")
    await pg.click(".modal [data-close]")
    await pg.click(".mp-back a")
    await pg.wait_for_selector(".mp-menu summary")
    await pg.click(".mp-menu summary")
    await pg.wait_for_timeout(400)
    await shot("11-account-menu")
    await pg.click("[data-delacct]")
    await pg.wait_for_timeout(500)
    await pg.click(".modal [data-go]")
    await pg.wait_for_selector(".mp-exbar")  # signed out again: back to the example portfolio
    print(tag, "account deleted, back to the example portfolio")
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
