"""One-time, polite fetch of the corpus' link-only sources (corpus/links_only.csv).

The starter corpus ships some sources as links only (law-firm alerts, news, code publishers).
We read each URL once (sequential, delay between requests, no crawling), keep the main text
with a SOURCE/RETRIEVED header in supplementary/text/<doc_id>.txt and never re-fetch.
Pages that refuse automated access (HTTP 403, code publishers) are skipped, not worked around.
These texts are SECONDARY sources: rules extracted from them are flagged as such.
"""

from __future__ import annotations

import csv
import datetime as dt
import time
import urllib.request

from .config import LINKS_ONLY_CSV, SUPP_DIR

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def fetch_all(delay: float = 2.0, force: bool = False) -> list[tuple[str, str]]:
    import trafilatura

    SUPP_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for row in csv.DictReader(open(LINKS_ONLY_CSV, encoding="utf-8")):
        doc_id, url = row["doc_id"], row["url"]
        out = SUPP_DIR / f"{doc_id}.txt"
        if out.exists() and not force:
            results.append((doc_id, "cached"))
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except Exception as e:  # 403 etc: respect the refusal
            results.append((doc_id, f"skipped: {e}"))
            time.sleep(delay)
            continue
        text = (
            trafilatura.extract(
                html, include_comments=False, include_tables=True, favor_recall=True
            )
            or ""
        )
        if len(text) < 300:
            results.append((doc_id, "skipped: no main text"))
            time.sleep(delay)
            continue
        now = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M UTC")
        out.write_text(
            f"SOURCE: {url}\nRETRIEVED: {now}\nSOURCE_TYPE: {row['source_type']} (link-only in starter corpus; fetched by team)\n\n{text}\n",
            encoding="utf-8",
        )
        results.append((doc_id, f"ok {len(text)} chars"))
        time.sleep(delay)
    return results
