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
from fastapi.testclient import TestClient

from web import headlines as H
from web.app import STORE, app, build_address

client = TestClient(app)

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
    elif result == "unknown" and (H.PLAIN.get(rid) or {}).get("unknown"):
        # coverage unknown (a place view): the wording that keeps the exemptions in (CA-RENT-01: most older rentals)
        assert f["answer_display"] == H.PLAIN[rid]["unknown"][lang][0] != applies
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
    assert (
        after["enacted"][0]["rule"]["answer_display"]
        == "Not as part of price-fixing between landlords."
    )


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


# ------------------------------------------------------------------ before the version our data holds (version_gap)
def _cat(d, cid):
    return next(c for c in d["categories"] if c["id"] == cid)


def test_ca_deposit_before_ab12_is_unknown_not_the_current_figure():
    d = build_address("A0001", "2023-08-12", "en")
    dep = next(
        i
        for i in _cat(d, "security_deposits")["enacted"]
        if i["rule"]["team_rule_id"] == "CA-DEP-01"
    )
    assert dep["result"] == "unknown" and dep["version_gap"]["from"] == "2024-07-01"
    assert dep["rule"]["answer_display"].startswith(
        "We can't tell for this date: an older version applied"
    )
    assert "Jul 1, 2024" in dep["rule"]["why_display"]
    assert "1 month" not in json.dumps(
        {k: dep["rule"][k] for k in ("answer_display", "why_display")}
    )
    es = build_address("A0001", "2023-08-12", "es")
    dep_es = next(
        i
        for i in _cat(es, "security_deposits")["enacted"]
        if i["rule"]["team_rule_id"] == "CA-DEP-01"
    )
    assert dep_es["rule"]["answer_display"].startswith("No podemos saberlo para esta fecha")
    # on and after the AB 12 date the current rule answers again
    after = build_address("A0001", "2024-07-01", "en")
    dep2 = next(
        i
        for i in _cat(after, "security_deposits")["enacted"]
        if i["rule"]["team_rule_id"] == "CA-DEP-01"
    )
    assert dep2["result"] == "applies" and "version_gap" not in dep2


def test_la_rent_in_2023_is_not_answered_with_the_current_rule():
    # the RSO froze increases from 2020-03-30 through 2024-01-31 (D041): the 2026 version must not answer for 2023
    d = build_address("A0001", "2023-08-12", "en")
    top = next(
        i
        for i in _cat(d, "rent_increase_limits")["enacted"]
        if i["rule"]["team_rule_id"] == "LA-RENT-01"
    )
    assert top["result"] == "unknown" and top["version_gap"]["from"] == "2026-02-02"
    assert top["rule"]["answer_display"].startswith("We can't tell for this date")
    la_evic = next(
        i
        for i in _cat(d, "just_cause_eviction")["enacted"]
        if i["rule"]["team_rule_id"] == "LA-EVIC-01"
    )
    assert "$11,000" not in (la_evic["rule"]["why_display"] or "")  # the 2026-27 relocation figure


def test_earlier_version_same_keeps_answering():
    # MA's deposit cap text "effective until August 1, 2025" is in the statute too (D052): no gap
    d = build_address("A0006", "2025-06-01", "en")
    dep = next(
        i
        for i in _cat(d, "security_deposits")["enacted"]
        if i["rule"]["team_rule_id"] == "MA-DEP-01"
    )
    assert dep["result"] == "applies" and "version_gap" not in dep
    rent = build_address("A0023", "2023-08-12", "en")
    ca = [
        i
        for i in _cat(rent, "rent_increase_limits")["enacted"]
        if i["rule"]["team_rule_id"] == "CA-RENT-01"
    ]
    assert all("version_gap" not in i for i in ca)


def test_figure_of_the_current_period_is_not_the_answer_before_it():
    # CA application fee: the cap is old (since 1998), the $68.96 figure is 2026's
    d = build_address("A0001", "2025-12-31", "en")
    fee = next(
        i
        for i in _cat(d, "application_screening_fees")["enacted"]
        if i["rule"]["team_rule_id"] == "CA-FEE-01"
    )
    assert fee["result"] == "applies"
    assert "69" not in (fee["rule"]["answer_display"] or "") and "69" not in (fee["headline"] or "")


@pytest.mark.parametrize("as_of", ["2020-06-01", "2023-08-12", "2025-06-01", "2025-12-31"])
@pytest.mark.parametrize("city", sorted(CITY_IDS))
def test_every_gap_says_so_and_never_shows_the_current_answer(city, as_of):
    d = build_address(CITY_IDS[city], as_of, "en")
    for _c, it in items(d):
        if it.get("version_gap"):
            r = it["rule"]
            assert it["result"] == "unknown"
            assert r["answer_display"].startswith("We can't tell for this date")
            assert r["answer_display"] != H.plain(r["team_rule_id"])["answer_display"]
            assert it["version_gap"]["from"] > as_of


def test_engine_version_gap_rule():
    from navigator import evaluate as E

    rules = {r["team_rule_id"]: r for r in E.load_rules()}
    D = __import__("datetime").date
    assert E.version_gap(rules["CA-DEP-01"], D(2024, 6, 30)) == {
        "from": "2024-07-01",
        "in_sources": True,
    }
    assert E.version_gap(rules["CA-DEP-01"], D(2024, 7, 1)) is None
    assert E.version_gap(rules["MA-DEP-01"], D(2025, 1, 1)) is None  # earlier_version: same
    assert (
        E.version_gap(rules["SA-RENT-01"], D(2022, 1, 1)) is None
    )  # in force since its own effective date
    assert E.version_gap(rules["NJ-DEP-01"], D(2020, 1, 1)) is None  # no recorded version date


# ------------------------------------------------------------------ legal review 2026-10-04 (classes of bugs)
def test_small_landlord_helper_uses_count_and_use_code_floor():
    from web import headlines as H

    assert H.small_landlord_possible("CA-DEP-01", 21) is False
    assert H.small_landlord_possible("CA-DEP-01", None, 5) is False  # "5 or more units" by use code
    assert H.small_landlord_possible("CA-DEP-01", 4) is True
    assert (
        H.small_landlord_possible("CA-DEP-01") is True
    )  # unknown count: the landlord type decides
    assert H.small_landlord_possible("SMO-DEP-01", "12") is False
    assert H.small_landlord_possible("CA-RENT-01", 2) is None  # no such exception
    no = H.for_item("CA-DEP-01", "applies", "2026-10-01", units=None, units_min=5)["why_display"]
    assert (
        no == "The 2-month small-landlord exception can't apply: this building has 5 or more units."
    )
    maybe = H.for_item("CA-DEP-01", "applies", "2026-10-01", units=3)["why_display"]
    assert "but not from a service member" in maybe and "individual" in maybe


def test_listen_deposit_line_follows_the_same_unit_test():
    from web import briefing as B

    for aid in ("A0001", "A0016"):  # 32 and 21 units
        for lang in ("en", "es"):
            t = " ".join(
                s
                for _, s in B.topic(
                    build_address(aid, "2026-10-01", lang), "security_deposits", "renter", lang
                )
            )
            t += " ".join(
                s for _, s in B.briefing(build_address(aid, "2026-10-01", lang), "renter", lang)
            )
            assert (
                "small landlord" not in t
                and "dueño pequeño" not in t
                and "arrendadores pequeños" not in t
            )
    cat = {
        "id": "security_deposits",
        "enacted": [
            {
                "result": "applies",
                "small_landlord_possible": True,
                "rule": {"team_rule_id": "CA-DEP-01"},
            }
        ],
    }
    small = B.topic_lines(cat, "renter", "en", "2026-10-01", brief=False)[0]
    assert (
        "or two with a small landlord (an individual with 2 rentals and 4 units at most)" in small
    )
    assert "two for small landlords" in B.caps_line(
        {"security_deposits": cat}, "renter", "en", "2026-10-01"
    )
    cat["enacted"][0]["small_landlord_possible"] = False
    assert "small" not in B.caps_line(
        {"security_deposits": cat}, "renter", "en", "2026-10-01", small=True
    )


def test_period_formatter_and_dated_relocation_amounts():
    from web import headlines as H

    assert H.fmt_period("2026-07-01", "2027-06-30", "en") == "Jul 2026–Jun 2027"
    assert H.fmt_period("2026-07-01", "2027-06-30", "es") == "jul 2026–jun 2027"
    assert H.fmt_period(None, "2027-02-28", "en") == "until Feb 2027"
    assert H.fmt_period("2026-03-01", None, "es") == "desde mar 2026"
    assert H.period_of({"from": "2026-07-01", "until": "2027-06-30"}, "2026-06-30") == "before"
    assert H.period_of({"from": "2026-07-01", "until": "2027-06-30"}, "2027-07-01") == "after"
    la = lambda d: H.plain("LA-EVIC-01", "en", d)["why_display"]  # noqa: E731
    assert (
        la("2026-10-01")
        == "If it's not your fault, most tenants get $11,000–$27,400 to move (Jul 2026–Jun 2027)."
    )
    assert (
        la("2026-01-15")
        == la("2027-07-15")
        == "If it's not your fault, they must pay you relocation money."
    )
    assert "$11,000" in H.plain("LA-EVIC-01", "es", "2026-10-01")["why_display"]
    sf = lambda d: H.plain("SF-EVIC-01", "en", d)["why_display"]  # noqa: E731
    assert "$8,245 per tenant" in sf("2026-10-01") and "Mar 2026–Feb 2027" in sf("2026-10-01")
    assert "$" not in sf("2026-01-15") and "$" not in sf("2027-03-01")
    for d in ("2026-01-15", "2027-07-15"):  # LA demolition figures: lower-income only, dated
        assert "$" not in H.headline("LA-EVIC-03", "en", d)
        assert "$" not in H.plain("LA-EVIC-03", "en", d)["answer_display"]
    assert (
        H.headline("LA-EVIC-03", "en", "2026-10-01") == "Lower-income, demolition: $87,450–$115,480"
    )
    # every surface: the address row (resolved) and the Changes event of the rule's own date
    a = build_address("A0001", "2026-01-15", "en")
    ev = next(c for c in a["categories"] if c["id"] == "just_cause_eviction")
    for i in ev["enacted"]:
        assert "27,400" not in (i["rule"].get("why_display") or "")
    # CA application fee: the 2026 figure ends with 2026, also in the Compare cell
    assert H.short("CA-FEE-01", "en", "2026-10-01") == "Max ~$69 per applicant (2026)"
    assert H.short("CA-FEE-01", "en", "2027-03-01") == "Max $30 + CPI since 1998"
    assert H.plain("CA-FEE-01", "en", "2027-03-01")["answer_display"] is None


def test_santa_ana_287_only_from_sep_1_2026():
    from web import headlines as H

    for d in ("2021-11-19", "2025-06-01", "2026-08-31"):
        assert "2.87" not in H.headline("SA-RENT-01", "en", d)
        assert (
            H.plain("SA-RENT-01", "en", d)["answer_display"]
            == "Yes, max 3% a year (or 80% of inflation if lower)."
        )
    assert (
        H.plain("SA-RENT-01", "en", "2026-09-01")["answer_display"]
        == "Yes, but only 2.87% until Aug 2027."
    )
    tl = client.get("/api/timeline?lang=en").json()
    sa = next(e for e in tl if e["id"] == "SA-RENT-01")
    assert sa["date"] == "2021-11-19" and "2.87" not in (sa["answer"] or "") + (
        sa["headline"] or ""
    )
    ber = next(e for e in tl if e["id"] == "BER-RENT-01")
    assert "1.0%" not in (ber["answer"] or "") and "5%" in ber["answer"]


def test_ma_tenancy_at_will_notice_says_without_a_lease():
    from web import briefing as B
    from web import headlines as H

    assert H.plain("MA-EVIC-02", "en")["answer_display"].startswith("Without a lease")
    assert H.plain("MA-EVIC-02", "es")["answer_display"].startswith("Sin contrato")
    assert H.headline("MA-EVIC-02", "en").startswith("No lease")
    assert "(no lease)" in H.short("MA-EVIC-02", "en")
    assert "first such notice in 12 months" in H.plain("MA-EVIC-02", "en")["why_display"]
    assert B.rule_sentence("MA-EVIC-02", "renter", "en", "2026-10-01").startswith("Without a lease")
    r = STORE.rules["MA-EVIC-02"]
    assert "3 months' notice" not in r["key_value"] and "30 days" in r["key_value"]
    assert (
        r["requirement"].startswith("Without a lease")
        and "every three months or less often" in r["requirement"]
    )
    assert r["review_evidence"]  # backed by the verbatim § 12 sentence (navigator/review_fixes.py)


def test_nj_fee_flat_50_in_2026_in_every_surface():
    from web import briefing as B
    from web import headlines as H

    r26 = B.rule_sentence("NJ-FEE-01", "renter", "en", "2026-10-01")
    assert r26 == "An application fee can be at most 50 dollars."
    assert "inflation" in B.rule_sentence("NJ-FEE-01", "renter", "en", "2027-03-01")
    cat = {
        "id": "application_screening_fees",
        "enacted": [{"result": "applies", "rule": {"team_rule_id": "NJ-FEE-01"}}],
    }
    assert "more than 50 dollars to apply" in B.caps_line(
        {"application_screening_fees": cat}, "renter", "en", "2026-10-01"
    )
    assert "más de 50 dólares por solicitar" in B.caps_line(
        {"application_screening_fees": cat}, "renter", "es", "2026-10-01"
    )
    assert "inflation-adjusted" in B.caps_line(
        {"application_screening_fees": cat}, "renter", "en", "2027-03-01"
    )
    assert H.headline("NJ-FEE-01", "en", "2026-10-01") == "Up to $50 per application"
    assert "from 2027" in STORE.rules["NJ-FEE-01"]["key_value"]


def test_rent_software_answers_keep_their_condition():
    from web import headlines as H

    for rid in ("SF-ALG-01", "SD-ALG-01", "BER-ALG-01", "SA-ALG-01"):
        assert (
            H.plain(rid, "en")["answer_display"] == "Not with rivals' private data; that's banned."
        )
        assert H.short(rid, "en") == "Rival-data rent software banned"
    assert (
        H.plain("CA-ALG-01", "en")["answer_display"]
        == "Not as part of price-fixing between landlords."
    )
    assert "price-fixing" in H.headline("CA-ALG-01", "en")
    assert (
        H.plain("JC-ALG-01", "en")["answer_display"]
        == "No. Software that coordinates rents is banned."
    )
    assert "sale" not in H.short("NJ-EVIC-02", "en") and "Foreclosure" in H.short(
        "NJ-EVIC-02", "en"
    )


def test_changes_event_after_the_as_of_date_is_not_past_tense():
    tl = {e["id"]: e for e in client.get("/api/timeline?lang=en&as_of=2026-10-01").json()}
    nj = tl["NJ-ALG-01"]
    assert nj["answer"] == "Not yet: a state ban starts Jul 1, 2027." and "since" not in (
        nj["headline"] or ""
    )
    es = {e["id"]: e for e in client.get("/api/timeline?lang=es&as_of=2026-10-01").json()}[
        "NJ-ALG-01"
    ]
    assert es["answer"].startswith("Todavía no") and "desde" not in es["answer"]
    after = {e["id"]: e for e in client.get("/api/timeline?lang=en&as_of=2027-08-01").json()}[
        "NJ-ALG-01"
    ]
    assert "since Jul 1, 2027" in after["answer"]


def test_no_rule_finding_before_the_state_law_starts():
    # #158: "the $50 cap is a state law" under a "No rule" badge on a date before that law existed
    c = TestClient(app)

    def fee(as_of, lang="en"):
        d = c.get(f"/api/address/A0002?as_of={as_of}&lang={lang}").json()
        cat = next(x for x in d["categories"] if x["id"] == "application_screening_fees")
        return cat, [f["finding_display"] for f in cat["no_rule_findings"]]

    cat, f = fee("2024-01-01")
    assert cat["no_rule"] and f == [
        "On Jan 1, 2024, no state or city rule on this was in force yet. New Jersey law P.L.2025, c.405 "
        "was enacted on Jan 20, 2026 and takes effect on May 1, 2026."
    ]
    assert fee("2024-01-01", "es")[1][0].startswith("El 1 ene 2024 todavía no había")
    cat, _ = fee("2026-10-01")
    assert not cat["no_rule"]  # the state cap applies


def test_source_text_drops_the_capture_header():
    d = TestClient(app).get("/api/source/D030?rule_id=NR-02").json()
    assert not d["text"].startswith(("SOURCE", "RETRIEVED")) and d["highlight"]
