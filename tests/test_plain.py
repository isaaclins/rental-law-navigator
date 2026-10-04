"""Plain-language pipeline (navigator/plain.py): the validator, the template fallback, the pipeline with the model
mocked, and reviewed-over-generated precedence in web/headlines.py. No model calls."""

import json

import pytest

from navigator import plain as P

RULE = {
    "team_rule_id": "XX-DEP-01",
    "jurisdiction": "Testville, CA",
    "level": "city",
    "category": "security_deposits",
    "status": "in_force",
    "title": "Deposit limit",
    "key_value": "one month's rent; 2 months for small landlords",
    "requirement": "A landlord may not demand a deposit above one month's rent. Small landlords may ask for two "
    "months. The deposit must be returned within 21 days after move-out (since 7/1/2024).",
    "coverage_conditions": "All residential units.",
    "exemptions": "Small landlords with up to 2 properties.",
    "effective_date": "2024-07-01",
    "quoted_span": "shall not demand or receive security in an amount in excess of one month's rent",
    "confidence": 0.9,
    "verification": "primary_source",
}

GOOD = {
    "answer_en": "Max 1 month's rent.",
    "answer_es": "Máximo 1 mes de renta.",
    "why_en": "Small landlords may ask for 2 months.",
    "why_es": "Los dueños pequeños pueden pedir 2 meses.",
    "headline_en": "Deposit capped at 1 month's rent",
    "headline_es": "Depósito limitado a 1 mes de renta",
    "short_en": "Max 1 month's rent",
    "short_es": "Máx. 1 mes de renta",
    "period_end": None,
    "after_headline_en": None,
    "after_headline_es": None,
    "after_short_en": None,
    "after_short_es": None,
    "removes_protection": False,
}


def errs(**over):
    return P.validate({**GOOD, **over}, RULE)


def test_good_copy_passes():
    assert P.validate(GOOD, RULE) == []


# ---------------------------------------------------------------------------------------- number check --
@pytest.mark.parametrize(
    "field,text",
    [
        ("answer_en", "Max 3 months' rent."),  # 3 is nowhere in the rule
        ("why_en", "They must pay it back within 30 days."),  # the rule says 21
        ("why_en", "Small landlords may ask for $2,500."),
        ("answer_en", "Max 1 month's rent (5%)."),
    ],
)
def test_numbers_not_in_the_rule_fail(field, text):
    e = errs(**{field: text})
    assert any("is not in key_value" in x for x in e), e


def test_number_words_in_the_source_count_as_digits():
    # "one month's rent" / "two months" in the source back "1" and "2" in the copy
    assert P.source_facts(RULE)[0] >= {1.0, 2.0, 21.0}


def test_money_and_percent_normalised():
    assert P.numbers("They pay $11,000–$27,400 to move you.")[0] == {11000.0, 27400.0}
    assert P.numbers("Hasta 2.87% o 1,5 meses")[0] == {2.87, 1.5}


def test_dates_must_be_in_the_rule():
    es = "Desde el 1 jul 2024, los dueños pequeños pueden pedir 2 meses."
    assert errs(why_en="Since Jul 1, 2024, small landlords may ask for 2 months.", why_es=es) == []
    e = errs(why_en="Since Jan 1, 2025, small landlords may ask for 2 months.")
    assert any("date 2025-01-01" in x for x in e), e
    # US numeric dates in the source are understood
    assert (2024, 7, 1) in P.source_facts({**RULE, "effective_date": None})[1]


# ---------------------------------------------------------------------------------------------- length --
def test_length_limits():
    e = errs(answer_en="You can only be asked for at most 1 month's rent.")
    assert any("answer_en has 11 words (max 8)" in x for x in e), e
    long_why = "Small landlords may ask for 2 months " + "and more words here " * 5
    assert any(x.startswith("why_en has") for x in errs(why_en=long_why.strip() + "."))


def test_jargon_banned():
    assert any(
        "jargon" in x for x in errs(why_en="Under § 1950.5 small landlords may ask for 2 months.")
    )
    assert any("jargon" in x for x in errs(short_en="Max 1 month + CPI"))
    assert any("jargon" in x for x in errs(why_en="Small landlords are exempt up to 2 months."))
    assert any("jargon" in x for x in errs(why_en="The source gives no more facts."))


def test_reading_grade():
    hard = "Notwithstanding comprehensive administrative determinations, institutional landlords remain accountable."
    assert P.grade(hard) > P.MAX_GRADE
    assert P.grade("Small landlords may ask for 2 months.") <= P.MAX_GRADE


# ------------------------------------------------------------------------------------ status consistency --
def test_pending_must_say_not_law():
    r = {**RULE, "status": "pending"}
    e = P.validate(GOOD, r)
    assert any("answer_en must say this is not law" in x for x in e)
    assert any("answer_es must say this is not law" in x for x in e)
    ok = {**GOOD, "answer_en": "Not law yet: a bill.", "answer_es": "Aún no es ley: un proyecto."}
    assert P.validate(ok, r) == []


def test_in_force_must_not_say_not_law():
    e = errs(answer_en="Not law yet: max 1 month.")
    assert any("says 'not law'" in x for x in e)


def test_not_yet_effective_must_name_start_date():
    r = {
        **RULE,
        "status": "not_yet_effective",
        "effective_date": "2027-07-01",
        "requirement": RULE["requirement"] + " Starts July 1, 2027.",
    }
    e = P.validate(GOOD, r)
    assert any("must name the start date 2027-07-01" in x for x in e)
    ok = {
        **GOOD,
        "answer_en": "From Jul 1, 2027: max 1 month's rent.",
        "answer_es": "Desde el 1 jul 2027: máximo 1 mes de renta.",
    }
    assert P.validate(ok, r) == []


# --------------------------------------------------------------------------------------------- Spanish --
def test_spanish_present_and_same_numbers():
    assert any("answer_es is empty" in x for x in errs(answer_es=""))
    e = errs(why_es="Los dueños pequeños pueden pedir 1 mes.")
    assert any("why_es must carry the same numbers" in x for x in e), e


def test_period_needs_after_wording():
    e = errs(period_end="2024-07-01")
    assert any("after_headline_en" in x for x in e)
    e = errs(
        period_end="2031-01-31",
        after_headline_en="Deposit limited",
        after_headline_es="Depósito limitado",
    )
    assert any("period_end" in x for x in e)


# -------------------------------------------------------------------------------------------- fallback --
@pytest.mark.parametrize("status", ["in_force", "pending", "failed", "not_yet_effective"])
def test_fallback_always_passes_the_checks(status):
    r = {**RULE, "status": status}
    f = P.fallback(r)
    assert P.validate(f, r) == []
    assert "See the rule" not in f["answer_en"] and RULE["key_value"] not in f["answer_en"]


def test_fallback_uses_category_template_and_the_maximum():
    f = P.fallback({**RULE, "key_value": "max 1.5 months' rent"})
    assert f["answer_en"] == "Deposits are limited here: max 1.5 months' rent."
    assert f["answer_es"].startswith("Los depósitos tienen límite aquí")
    assert P.fallback({**RULE, "status": "pending"})["answer_en"].startswith("Not law yet")


# --------------------------------------------------------------------------------- pipeline, LLM mocked --
class FakeLLM:
    """Returns queued answers in order and records each prompt."""

    def __init__(self, *answers):
        self.answers, self.prompts = list(answers), []

    def __call__(self, system, prompt, schema, **kw):
        self.prompts.append(prompt)
        return self.answers.pop(0), {
            "prompt_hash": f"h{len(self.prompts)}",
            "model": "fake",
            "cached": False,
            "raw": "{}",
        }


@pytest.fixture
def tmp_audit(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "AUDIT_LOG", tmp_path / "audit.jsonl")
    monkeypatch.setattr(P, "reviewed_ids", lambda: ({"XX-RENT-01"}, {"XX-RENT-01"}))
    return tmp_path


def test_pipeline_first_try(tmp_audit):
    llm = FakeLLM(GOOD)
    doc = P.run(rules=[RULE], llm=llm, out=tmp_audit / "plain.json", log=lambda *_: None)
    rec = doc["records"]["XX-DEP-01"]
    assert rec["source"] == "generated" and rec["method"] == "model" and not rec["needs_review"]
    assert rec["headline"]["en"] == GOOD["headline_en"] and rec["headline"]["priority"] == 1
    assert rec["plain"]["en"] == [GOOD["answer_en"], GOOD["why_en"]]
    assert rec["question_en"] == "How large can the deposit be?"
    assert len(llm.prompts) == 1 and "Rule record" in llm.prompts[0]
    # the model sees only the rule's own fields
    assert '"confidence"' not in llm.prompts[0] and '"key_value"' in llm.prompts[0]
    lines = [json.loads(x) for x in open(tmp_audit / "audit.jsonl")]
    assert lines[0]["stage"] == "plain" and lines[0]["validation"] == []
    assert json.loads((tmp_audit / "plain.json").read_text())["counts"]["generated"] == 1


def test_pipeline_retry_with_errors_then_ok(tmp_audit):
    bad = {**GOOD, "answer_en": "Max 3 months' rent."}
    llm = FakeLLM(bad, GOOD)
    rec = P.run(rules=[RULE], llm=llm, out=tmp_audit / "p.json", log=lambda *_: None)["records"][
        "XX-DEP-01"
    ]
    assert rec["method"] == "model" and len(rec["validation"]["attempts"]) == 2
    assert "the number 3 is not in key_value" in llm.prompts[1]  # the errors go back to the model


def test_pipeline_falls_back_after_two_failures(tmp_audit):
    bad = {**GOOD, "answer_en": "Max 3 months' rent."}
    rec = P.run(rules=[RULE], llm=FakeLLM(bad, bad), out=tmp_audit / "p.json", log=lambda *_: None)[
        "records"
    ]["XX-DEP-01"]
    assert rec["method"] == "template" and rec["needs_review"]
    assert rec["fields"]["answer_en"].startswith("Deposits are limited here")
    assert not rec["validation"]["passed"]


def test_pipeline_skips_reviewed_rules(tmp_audit):
    llm = FakeLLM()
    reviewed = {**RULE, "team_rule_id": "XX-RENT-01", "category": "rent_increase_limits"}
    doc = P.run(rules=[reviewed], llm=llm, out=tmp_audit / "p.json", log=lambda *_: None)
    assert doc["records"]["XX-RENT-01"]["source"] == "reviewed" and llm.prompts == []


def test_low_confidence_is_flagged(tmp_audit):
    r = {**RULE, "confidence": 0.35, "verification": "unverified_link_only"}
    rec = P.run(rules=[r], llm=FakeLLM(GOOD), out=tmp_audit / "p.json", log=lambda *_: None)[
        "records"
    ]["XX-DEP-01"]
    assert rec["method"] == "model" and rec["needs_review"]


# --------------------------------------------------------------------------------- override precedence --
def test_reviewed_copy_wins_and_generated_fills_gaps(tmp_path, monkeypatch):
    from web import headlines as H

    reviewed_id = next(iter(H.REVIEWED_PLAIN & H.REVIEWED_HEADLINES))
    before = (dict(H.HEADLINES[reviewed_id]), H.PLAIN[reviewed_id])
    rec = {**P.generate(RULE, FakeLLM(GOOD)), "fills": ["headline", "plain"]}
    doc = {"records": {"XX-DEP-01": rec, reviewed_id: {**rec, "rule_id": reviewed_id}}}
    (tmp_path / "plain_language.json").write_text(json.dumps(doc), encoding="utf-8")
    for name in ("HEADLINES", "PLAIN", "GENERATED"):
        monkeypatch.setattr(H, name, dict(getattr(H, name)))
    H.load_generated(tmp_path)
    # reviewed entries are untouched
    assert H.HEADLINES[reviewed_id] == before[0] and H.PLAIN[reviewed_id] == before[1]
    assert H.view(reviewed_id)["plain_source"] == "reviewed"
    # the gap is filled and marked
    v = H.view("XX-DEP-01", "es")
    assert v["answer_display"] == GOOD["answer_es"] and v["headline_display"] == GOOD["headline_es"]
    assert v["plain_source"] == "generated" and v["plain_needs_review"] is False


def test_template_never_replaces_a_reviewed_headline(tmp_audit, monkeypatch):
    monkeypatch.setattr(P, "reviewed_ids", lambda: ({"XX-DEP-01"}, set()))
    bad = {**GOOD, "answer_en": "Max 3 months' rent."}
    rec = P.run(rules=[RULE], llm=FakeLLM(bad, bad), out=tmp_audit / "p.json", log=lambda *_: None)[
        "records"
    ]["XX-DEP-01"]
    assert rec["fills"] == []


def test_reviewed_headline_period_ends_a_generated_answer():
    from web import headlines as H

    # LA-DEP-01: reviewed headline ends 2025-12-31; the generated why quotes the 2025 rate
    if "LA-DEP-01" in H.GENERATED and "LA-DEP-01" not in H.REVIEWED_PLAIN:
        assert H.plain("LA-DEP-01")["plain_until"] == H.HEADLINES["LA-DEP-01"]["until"]


# ----------------------------------------------------------------------------------------- on topic --
def test_why_line_in_another_topics_words_fails():
    # the NJ-DEP-01 case: a rent-cap phrase under a deposit rule
    e = errs(
        why_en="Yearly increases can't go over 10%, and the deposit must be returned within 21 days."
    )
    assert any("uses rent increases wording" in x for x in e), e
    e = errs(
        why_es="Los aumentos de renta tienen tope, y los dueños pequeños pueden pedir 2 meses."
    )
    assert any("why_es uses rent increases wording" in x for x in e), e
    e = errs(why_en="Small landlords may ask for 2 months, and you can't be evicted for asking.")
    assert any("uses evictions wording" in x for x in e), e


def test_why_line_must_name_its_topic():
    e = errs(why_en="The city sets the rate each year.")  # deposit interest? rent? unclear
    assert any("does not say what it is about" in x for x in e), e
    assert not P.topic_errors(
        {"why_en": "The city sets the deposit interest rate each year."}, RULE
    )


def test_topic_overlaps_that_are_fine():
    fee = {**RULE, "category": "application_screening_fees", "key_value": "no application fee"}
    g = {
        **GOOD,
        "why_en": "Only first month, last month, a deposit and a lock fee.",
        "why_es": "Solo primer mes, último mes, depósito y cerradura.",
    }
    assert P.topic_errors(g, fee) == []
    ev = {**RULE, "category": "just_cause_eviction"}
    g = {
        **GOOD,
        "why_en": "The notice goes to the Rent Control Board.",
        "why_es": "Una copia va a la Junta de Control de Rentas.",
    }
    assert P.topic_errors(g, ev) == []
    # proposals explain their fate, not the topic
    assert (
        P.topic_errors({"why_en": "Voters decide in November."}, {**ev, "status": "pending"}) == []
    )


def test_reviewed_why_lines_pass_the_topic_check():
    from web import headlines as H

    rules = {r["team_rule_id"]: r for r in json.loads(P.RULES_JSON.read_text())["rules"]}
    for rid in H.REVIEWED_PLAIN & set(rules):
        p = H.PLAIN[rid]
        assert P.topic_errors({"why_en": p["en"][1], "why_es": p["es"][1]}, rules[rid]) == [], rid
