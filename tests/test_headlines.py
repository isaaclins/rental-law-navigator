"""The address answers follow the evaluator's result and the address-level conflict flag (brief audit 2026-10-04).

- headline-by-status matrix: a plain answer that says a rule applies ("No. ... is banned") is never shown for a rule
  that is not yet in effect, replaced, pending or failed, on any as-of date that matters for T1-T5;
- conflict rule: an item's conflict flag (and its rule view's) is exactly lookups.json's conflict_flag.

Run: uv run --with pytest --with httpx pytest tests/test_headlines.py -q
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from web import headlines as H
from web.app import STORE, build_address

LOOKUPS = json.loads(Path("output/lookups.json").read_text())
DATES = ["2025-12-31", "2026-01-02", "2026-10-01", "2027-07-02"]  # T1 before/after, today, T3 after
RESULTS = ["applies", "not_yet_effective", "superseded", "pending", "failed", "unknown"]
RULE_IDS = sorted(set(H.PLAIN) | set(H.HEADLINES))
# one address per city (LA, SF, SD, Berkeley, Santa Ana, Newark, Hoboken, Jersey City, Boston, Cambridge)
CITY_IDS = {}
for _id, _a in STORE.addresses.items():
    CITY_IDS.setdefault(_a.get("resolved_city") or _a["postal_city"], _id)


def items(d: dict):
    for c in d["categories"]:
        for it in c["enacted"] + c["pending"] + c["not_law"]:
            yield c, it


# ------------------------------------------------------------------ the matrix, rule by rule
@pytest.mark.parametrize("rid", RULE_IDS)
@pytest.mark.parametrize("result", RESULTS)
@pytest.mark.parametrize("lang", ["en", "es"])
def test_plain_answer_matches_the_result(rid, result, lang):
    applies = H.plain(rid, lang)["answer_display"]
    f = H.for_item(rid, result, "2026-10-01", lang, effective="2027-07-01")
    if result == "not_yet_effective":
        # either a dated "not yet" answer or none (the app then says "Not yet. Starts <date>.")
        assert f["answer_display"] is None or f["answer_display"].startswith(
            ("Not yet", "Todavía no")
        )
        assert f["answer_display"] != applies or applies is None
        assert f["why_display"] is None
        if H.headline(rid, lang):
            assert f["headline"] and ("2027" in f["headline"])
    elif result in ("superseded", "pending", "failed"):
        assert f["answer_display"] is None and f["why_display"] is None
    else:  # applies / unknown (a place view shows the rule's own answer for an unknown building)
        assert f["answer_display"] == applies


def test_not_yet_wording_for_the_bans():
    f = H.for_item("CA-ALG-01", "not_yet_effective", "2025-12-31", effective="2026-01-01")
    assert f["answer_display"] == "Not yet: a ban starts Jan 1, 2026."
    assert f["headline"] == "Not yet: a ban starts Jan 1, 2026"
    es = H.for_item("CA-ALG-01", "not_yet_effective", "2025-12-31", "es", effective="2026-01-01")
    assert es["answer_display"] == "Todavía no: una prohibición empieza el 1 ene 2026."
    nj = H.for_item("NJ-ALG-01", "not_yet_effective", "2026-10-01", effective="2027-07-01")
    assert nj["answer_display"] == "Not yet: a state ban starts Jul 1, 2027."


def test_nj_fair_act_after_its_start_is_past_tense():
    f = H.for_item("NJ-ALG-01", "applies", "2027-07-02")
    assert "since Jul 1, 2027" in f["answer_display"]
    assert "Until then" not in (f["why_display"] or "")
    c = H.for_item("NJ-ALG-01", "applies", "2027-07-02", conflict=True)
    assert (
        "court" in c["why_display"]
    )  # the preemption question only where the address carries the flag


def test_small_landlord_line_follows_the_unit_count():
    many = H.for_item("CA-DEP-01", "applies", "2026-10-01", units=20)
    assert "can't apply" in many["why_display"] and "20 units" in many["why_display"]
    floor = H.for_item("CA-DEP-01", "applies", "2026-10-01", units_min=5)
    assert "5 or more units" in floor["why_display"]
    for small in (dict(units=4), dict(units=None)):
        assert (
            "may ask for 2 months"
            in H.for_item("CA-DEP-01", "applies", "2026-10-01", **small)["why_display"]
        )


def test_massachusetts_notice_is_not_three_months_for_monthly_rent():
    a = H.plain("MA-EVIC-02")["answer_display"]
    assert (
        "3 months" not in a and "30" in a
    )  # G.L. c. 186, § 12: rent interval or 30 days, whichever is longer


# ------------------------------------------------------------------ the matrix on real addresses and dates
@pytest.mark.parametrize("as_of", DATES)
@pytest.mark.parametrize("city", sorted(CITY_IDS))
def test_no_applies_wording_for_a_rule_that_does_not_apply(city, as_of):
    d = build_address(CITY_IDS[city], as_of, "en")
    for _c, it in items(d):
        r = it["rule"]
        applies_answer = H.plain(r["team_rule_id"])["answer_display"]
        if (
            it["result"] in ("not_yet_effective", "superseded", "pending", "failed")
            and applies_answer
            # generated copy for a proposal is already worded for its status (navigator/plain.py)
            and not (it["result"] in ("pending", "failed") and applies_answer.startswith("Not law"))
        ):
            assert r.get("answer_display") != applies_answer, (
                city,
                as_of,
                r["team_rule_id"],
                it["result"],
            )
        if it["result"] == "not_yet_effective" and r.get("answer_display"):
            assert r["answer_display"].startswith("Not yet")
    for c in d["categories"]:
        top_applies = any(i["result"] == "applies" for i in c["enacted"])
        if c["headline"] and not top_applies:
            assert "banned" not in c["headline"].lower() or c["headline"].startswith(
                ("Not yet", "From")
            )


def test_t1_la_before_and_after_jan_1_2026():
    alg = lambda d: next(c for c in d["categories"] if c["id"] == "algorithmic_rent_setting")  # noqa: E731
    before = alg(build_address("A0001", "2025-12-31", "en"))
    top = before["enacted"][0]
    assert top["result"] == "not_yet_effective"
    assert top["rule"]["answer_display"] == "Not yet: a ban starts Jan 1, 2026."
    assert before["headline"] == "Not yet: a ban starts Jan 1, 2026"
    after = alg(build_address("A0001", "2026-01-02", "en"))
    assert after["enacted"][0]["result"] == "applies"
    assert after["enacted"][0]["rule"]["answer_display"] == "No. Price-fixing software is banned."


def test_t3_hoboken_after_the_fair_act_has_no_stale_until_then():
    hob = next(i for i, a in STORE.addresses.items() if a.get("resolved_city") == "Hoboken")
    d = build_address(hob, "2027-07-02", "en")
    text = json.dumps(d)
    assert "Until then" not in text
    nj = next(it for _, it in items(d) if it["rule"]["team_rule_id"] == "NJ-ALG-01")
    assert nj["result"] == "applies" and nj["conflict_flag"] is True
    assert "since Jul 1, 2027" in nj["rule"]["answer_display"]


# ------------------------------------------------------------------ the conflict flag is the address-level one
def test_conflict_flag_equals_lookups_for_every_address():
    as_of = LOOKUPS["as_of"]
    for aid, entries in LOOKUPS["lookups"].items():
        want = {e["team_rule_id"]: bool(e["conflict_flag"]) for e in entries}
        d = build_address(aid, as_of, "en")
        got = {
            it["rule"]["team_rule_id"]: it["conflict_flag"]
            for _, it in items(d)
            if it["result"] != "failed"
        }
        assert got == want, aid
        for _, it in items(d):
            assert it["rule"]["conflict_flag"] == it["conflict_flag"], (
                aid,
                it["rule"]["team_rule_id"],
            )


@pytest.mark.parametrize("as_of", DATES)
def test_newark_has_no_conflict(as_of):
    nwk = [i for i, a in STORE.addresses.items() if a.get("resolved_city") == "Newark"]
    for aid in nwk[:10]:
        d = build_address(aid, as_of, "en")
        alg = next(c for c in d["categories"] if c["id"] == "algorithmic_rent_setting")
        assert not any(
            it["conflict_flag"] or it["rule"]["conflict_flag"] for it in alg["enacted"]
        ), aid
