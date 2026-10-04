"""Spanish pages: the engine's live explanations (Rules place view, Check, any address) are Spanish even when the
translation cache can't hold them (web/translate.es_explanation), and so is the missing fact."""

import itertools

from navigator import user_facts as U
from web.any_address import _missing_es
from web.app import DEFAULT_AS_OF, STORE

ENGLISH = (
    " applies in ",
    " may apply in ",
    " not in the data",
    "owner-occupied",
    " units ",
    "you entered",
    "would cover",
    "pending bill",
    " exempt ",
)


def test_live_explanations_have_spanish():
    cities = U.covered_cities()
    places = [(s, None) for s in cities] + [(s, c) for s in cities for c in cities[s]]
    facts = [
        {},
        {"year_built": 1950},
        {"year_built": 2015, "units": 1},
        {"units": 10, "owner_occupied": False},
        {"units": 3, "owner_occupied": True},
    ]
    left = []
    for (s, c), f in itertools.product(places, facts):
        for e in U.evaluate_user(s, c, f, DEFAULT_AS_OF)["results"]:
            x = e.get("explanation") or ""
            es = STORE.t_expl(x, "es")
            if x and (es == x or any(w in es for w in ENGLISH)):
                left.append(x)
    assert not left, left[:5]


def test_missing_fact_spanish():
    assert _missing_es(["year_built", "units"], None) == "Año de construcción o Número de unidades"
    assert _missing_es([], "Depends on: unit is in an affordable housing project.") == (
        "Depende de: la unidad está en un proyecto de vivienda asequible."
    )
    assert _missing_es([], "something new") is None
