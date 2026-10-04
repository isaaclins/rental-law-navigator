"""Rules whose quote does not support their own citation (brief audit v2, item 17).

The quote is found word for word, but in another document than the law the rule cites (or it is only a heading), so the
app must not show the green "Word for word on <site>" line for them. Instead it shows this amber note, in the web layer
only: output/*.json stay as they are. Not legal advice.
"""

from __future__ import annotations

_CITY_EN = "Check the city code before relying on it."
_CITY_ES = "Revise el código de la ciudad antes de basarse en ella."

NOTES: dict[str, dict[str, str]] = {
    "HOB-RENT-01": {
        "en": "This sentence is from New Jersey's state guide on nj.gov, not from Hoboken's own ordinance"
        " (City Code ch. 155), which isn't in our sources. " + _CITY_EN,
        "es": "Esta frase es de una guía estatal de Nueva Jersey en nj.gov, no de la ordenanza de Hoboken"
        " (City Code ch. 155), que no está en nuestras fuentes. " + _CITY_ES,
    },
    "NWK-RENT-01": {
        "en": "This sentence is from New Jersey's state guide on nj.gov, not from Newark's own ordinance,"
        " which isn't in our sources. " + _CITY_EN,
        "es": "Esta frase es de una guía estatal de Nueva Jersey en nj.gov, no de la ordenanza de Newark,"
        " que no está en nuestras fuentes. " + _CITY_ES,
    },
    "SD-SCR-01": {
        "en": "This sentence is from California's Civil Rights Department page on state law"
        " (calcivilrights.ca.gov), not from San Diego's own ordinance (Mun. Code ch. 9, art. 8, div. 8),"
        " which isn't in our sources. " + _CITY_EN,
        "es": "Esta frase es de la página del Departamento de Derechos Civiles de California sobre la ley estatal"
        " (calcivilrights.ca.gov), no de la ordenanza de San Diego (Mun. Code ch. 9, art. 8, div. 8),"
        " que no está en nuestras fuentes. " + _CITY_ES,
    },
    "LA-DEP-01": {
        "en": "This is only a heading on the city's rent stabilization page (housing.lacity.gov); it doesn't"
        " state the rule. The interest rate comes from a landlord association page (aagla.org)."
        " Check the city's current rate before relying on it.",
        "es": "Esto es solo un título en la página de estabilización de rentas de la ciudad (housing.lacity.gov);"
        " no dice la regla. La tasa de interés viene de la página de una asociación de propietarios (aagla.org)."
        " Revise la tasa actual de la ciudad antes de basarse en ella.",
    },
}

LEAD = {"en": "Source unclear.", "es": "Fuente poco clara."}


def note(rule_id: str | None, lang: str = "en") -> dict | None:
    """{"lead": "Source unclear.", "text": ...} for a rule whose quote doesn't back its citation, else None."""
    n = NOTES.get(rule_id or "")
    if not n:
        return None
    lg = "es" if lang == "es" else "en"
    return {"lead": LEAD[lg], "text": n[lg]}
