"""Spoken briefings for Listen (#49): what the rules at an address mean for a renter or an owner, EN and ES.

Deterministic templates over the evaluator result (web.app.build_address) and the figure periods of
web/headlines.py; no LLM at runtime. Two products:
- briefing(...)  about 35-50 s: rent limit, eviction protection, deposit and fee caps, what changes in the next
  12 months, what is unknown and which fact settles it, one next step, "sources on screen", "not legal advice".
- topic(...)     about 10-15 s: one topic, for the "Explain this" link in an opened topic.
Both return a list of (category id | None, sentence); the category drives the chapter highlighting.

Spoken style: plain sentences, no citations, no abbreviations (rent control, not RSO; the LA Housing Department,
not LAHD). Spanish is written as its own text (usted, like the site), not translated from English.
"""

from __future__ import annotations

import datetime as dt
import re

from web import headlines as H

LANGS = ("en", "es")
PERSONAS = ("renter", "owner")
CATS = (
    "rent_increase_limits",
    "just_cause_eviction",
    "security_deposits",
    "application_screening_fees",
    "screening_restrictions",
    "algorithmic_rent_setting",
)
MONTHS_ES = "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split()


def say_date(iso: str, lang: str) -> str:
    d = dt.date.fromisoformat(iso[:10])
    if lang == "es":
        return f"{d.day} de {MONTHS_ES[d.month - 1]} de {d.year}"
    return f"{d:%B} {d.day}, {d.year}"


def cap(s: str) -> str:
    return s[:1].upper() + s[1:]


# ------------------------------------------------------------------ what each rule means, spoken
# Per rule: n = spoken name; r / o = renter / owner sentence; ra / oa = the same after the figure's period
# (headlines.py "until", or an own "until"); reset = the sentence for the change on the day after "until";
# brief = order inside its topic in the briefing (None: only in "Explain this"); dep / fee = the cap as a noun
# phrase ("if they ask for <dep>, that's over the limit"); missing = which fact an "unknown" is about.
# Every value is (English, Spanish).

VOUCHER = {
    "r": (
        "A landlord can't turn you down because you pay with a housing voucher or other assistance.",
        "Un arrendador no puede rechazarlo porque pague con un vale de vivienda u otra ayuda.",
    ),
    "o": (
        "You can't turn applicants away because they pay with a housing voucher or other assistance.",
        "No puede rechazar a solicitantes porque paguen con un vale de vivienda u otra ayuda.",
    ),
    "brief": 1,
}
ALGO = {
    "r": (
        "Landlords can't set your rent with software that pools competitors' private pricing data.",
        "Los arrendadores no pueden fijar su renta con software que reúne datos privados de precios de la competencia.",
    ),
    "o": (
        "You can't set rents with software that pools competitors' private pricing data.",
        "No puede fijar rentas con software que reúne datos privados de precios de la competencia.",
    ),
    "brief": 1,
}


def _city(place_en: str, place_es: str | None = None) -> dict:
    """Name of a city's rent-control or rent-software rule."""
    return {"n": (f"{place_en} rent control", f"el control de rentas de {place_es or place_en}")}


SAY: dict[str, dict] = {
    # ---------------------------------------------------------------- rent increases
    "CA-RENT-01": {
        "n": ("California's statewide rent cap", "el tope estatal de rentas de California"),
        "r": (
            "State law caps increases at 5 percent plus inflation, and never more than 10 percent a year.",
            "La ley estatal limita los aumentos a un 5 por ciento más la inflación, y nunca más del 10 por ciento al año.",
        ),
        "o": (
            "State law caps your increases at 5 percent plus local inflation, never more than 10 percent in 12 months.",
            "La ley estatal limita sus aumentos a un 5 por ciento más la inflación local, nunca más del 10 por ciento en 12 meses.",
        ),
        "brief": 1,
    },
    "LA-RENT-01": {
        **_city("Los Angeles", "Los Ángeles"),
        "r": (
            "This unit has rent control: your landlord can raise the rent once a year, by at most 3 percent until {until}.",
            "Esta vivienda tiene control de rentas: su arrendador puede subir la renta una vez al año, como máximo un 3 por ciento hasta el {until}.",
        ),
        "ra": (
            "This unit has rent control: one increase a year, by the city's yearly percentage. We have no figure after {until}; the last was 3 percent.",
            "Esta vivienda tiene control de rentas: un aumento al año, con el porcentaje anual de la ciudad. No tenemos cifra posterior al {until}; la última fue del 3 por ciento.",
        ),
        "o": (
            "This building has rent control: one increase every 12 months, at most 3 percent until {until}.",
            "Este edificio tiene control de rentas: un aumento cada 12 meses, como máximo un 3 por ciento hasta el {until}.",
        ),
        "oa": (
            "This building has rent control: one increase every 12 months, up to the city's yearly percentage. We have no figure after {until}, so check it before raising the rent.",
            "Este edificio tiene control de rentas: un aumento cada 12 meses, hasta el porcentaje anual de la ciudad. No tenemos cifra posterior al {until}; confírmela antes de subir la renta.",
        ),
        "reset": (
            "a new rent increase",
            "un nuevo aumento de renta",
        ),
        "brief": 1,
    },
    "SF-RENT-01": {
        **_city("San Francisco"),
        "r": (
            "This unit has rent control: your landlord can raise the rent once a year, by at most 1.6 percent until {until}.",
            "Esta vivienda tiene control de rentas: su arrendador puede subir la renta una vez al año, como máximo un 1,6 por ciento hasta el {until}.",
        ),
        "ra": (
            "This unit has rent control: one increase a year, by the Rent Board's yearly percentage. We have no figure after {until} yet.",
            "Esta vivienda tiene control de rentas: un aumento al año, con el porcentaje anual de la Junta de Rentas. Aún no tenemos cifra posterior al {until}.",
        ),
        "o": (
            "This building has rent control: one increase every 12 months, at most 1.6 percent until {until}.",
            "Este edificio tiene control de rentas: un aumento cada 12 meses, como máximo un 1,6 por ciento hasta el {until}.",
        ),
        "oa": (
            "This building has rent control: one increase every 12 months, up to the Rent Board's yearly percentage. We have no figure after {until}, so check it before raising the rent.",
            "Este edificio tiene control de rentas: un aumento cada 12 meses, hasta el porcentaje anual de la Junta de Rentas. No tenemos cifra posterior al {until}; confírmela antes de subir la renta.",
        ),
        "reset": (
            "a new rent increase",
            "un nuevo aumento de renta",
        ),
        "brief": 1,
    },
    "BER-RENT-01": {
        **_city("Berkeley"),
        "r": (
            "This unit has rent control: for 2026 your rent can go up by at most 1 percent, and never more than 5 percent in any year.",
            "Esta vivienda tiene control de rentas: en 2026 su renta puede subir como máximo un 1 por ciento, y nunca más del 5 por ciento en un año.",
        ),
        "ra": (
            "This unit has rent control: increases follow 65 percent of inflation, never more than 5 percent. We don't have the figure after {until} yet.",
            "Esta vivienda tiene control de rentas: los aumentos siguen el 65 por ciento de la inflación, nunca más del 5 por ciento. Aún no tenemos la cifra posterior al {until}.",
        ),
        "o": (
            "This building has rent control: at most 1 percent for 2026, and never more than 5 percent in any year.",
            "Este edificio tiene control de rentas: como máximo un 1 por ciento en 2026, y nunca más del 5 por ciento en un año.",
        ),
        "oa": (
            "This building has rent control: increases follow 65 percent of inflation, never more than 5 percent. We don't have the figure after {until}, so check it with the Berkeley Rent Board.",
            "Este edificio tiene control de rentas: los aumentos siguen el 65 por ciento de la inflación, nunca más del 5 por ciento. No tenemos la cifra posterior al {until}; confírmela con la Junta de Rentas de Berkeley.",
        ),
        "reset": (
            "a new rent increase",
            "un nuevo aumento de renta",
        ),
        "brief": 1,
    },
    "SA-RENT-01": {
        **_city("Santa Ana"),
        "r": (
            "This unit has rent control: your rent can go up by at most 2.87 percent a year until {until}.",
            "Esta vivienda tiene control de rentas: su renta puede subir como máximo un 2,87 por ciento al año hasta el {until}.",
        ),
        "ra": (
            "This unit has rent control: at most 3 percent a year, or 80 percent of inflation if that's lower.",
            "Esta vivienda tiene control de rentas: como máximo un 3 por ciento al año, o el 80 por ciento de la inflación si es menor.",
        ),
        "o": (
            "This building has rent control: at most 2.87 percent a year until {until}, and every increase notice must mention the ordinance.",
            "Este edificio tiene control de rentas: como máximo un 2,87 por ciento al año hasta el {until}, y cada aviso de aumento debe mencionar la ordenanza.",
        ),
        "oa": (
            "This building has rent control: at most 3 percent a year, or 80 percent of inflation if lower, and every increase notice must mention the ordinance.",
            "Este edificio tiene control de rentas: como máximo un 3 por ciento al año, o el 80 por ciento de la inflación si es menor, y cada aviso de aumento debe mencionar la ordenanza.",
        ),
        "reset": (
            "a new rent increase",
            "un nuevo aumento de renta",
        ),
        "brief": 1,
    },
    "JC-RENT-01": {
        **_city("Jersey City"),
        "r": (
            "This building is under Jersey City rent control, so increases are limited. We don't have the yearly figure; the city's Office of Landlord-Tenant Relations can tell you.",
            "Este edificio tiene control de rentas de Jersey City, así que los aumentos tienen límite. No tenemos la cifra anual; la Oficina de Relaciones entre Propietarios e Inquilinos de la ciudad se la puede dar.",
        ),
        "o": (
            "This building is under Jersey City rent control. Increases are limited, and extra increases for improvements or hardship need the city's approval.",
            "Este edificio tiene control de rentas de Jersey City. Los aumentos tienen límite, y los aumentos extra por mejoras o dificultades necesitan la aprobación de la ciudad.",
        ),
        "brief": 1,
    },
    "HOB-RENT-01": {
        **_city("Hoboken"),
        "r": (
            "Hoboken rent control limits yearly increases here. We don't have the exact figure; the city's rent control office can tell you if your unit is covered.",
            "El control de rentas de Hoboken limita aquí los aumentos anuales. No tenemos la cifra exacta; la oficina de control de rentas de la ciudad le puede decir si su vivienda está cubierta.",
        ),
        "o": (
            "Hoboken rent control limits yearly increases on covered units. We don't have the exact figure, so check coverage and the cap with the city's rent control office.",
            "El control de rentas de Hoboken limita los aumentos anuales de las viviendas cubiertas. No tenemos la cifra exacta; confirme la cobertura y el tope con la oficina de control de rentas de la ciudad.",
        ),
        "brief": 1,
    },
    "NWK-RENT-01": {
        **_city("Newark"),
        "r": (
            "Newark has local rent control, but we couldn't read the ordinance itself. The Newark rent control office can confirm the cap.",
            "Newark tiene control de rentas local, pero no pudimos leer la ordenanza. La oficina de control de rentas de Newark puede confirmar el tope.",
        ),
        "o": (
            "Newark has local rent control, but we couldn't read the ordinance itself, so confirm the cap and which units it covers with the Newark rent control office.",
            "Newark tiene control de rentas local, pero no pudimos leer la ordenanza; confirme el tope y qué viviendas cubre con la oficina de control de rentas de Newark.",
        ),
        "brief": 1,
        "missing": "said",  # the sentence itself says what is unknown
    },
    "MA-RENT-01": {
        "n": (
            "the Massachusetts ban on rent control",
            "la prohibición del control de rentas en Massachusetts",
        ),
        "r": (
            "Massachusetts bans local rent control, so no law caps how much your rent can go up.",
            "Massachusetts prohíbe el control de rentas local, así que ninguna ley limita cuánto puede subir su renta.",
        ),
        "o": (
            "Massachusetts bans local rent control, so no law caps your rent increases here.",
            "Massachusetts prohíbe el control de rentas local, así que ninguna ley limita sus aumentos de renta aquí.",
        ),
        "brief": 1,
        "no_cap": True,
    },
    # ---------------------------------------------------------------- evictions
    "CA-EVIC-01": {
        "n": ("California's just-cause rule", "la regla estatal de causa justa"),
        "r": (
            "After 12 months here, your landlord needs a just cause to end your tenancy, and owes you a month's rent if it's not your fault.",
            "Después de 12 meses aquí, su arrendador necesita una causa justa para terminar su contrato, y le debe un mes de renta si no es por culpa suya.",
        ),
        "o": (
            "After a tenant's first 12 months you need a just cause to end the tenancy, and a no-fault ending costs one month's rent.",
            "Después de los primeros 12 meses de un inquilino necesita una causa justa para terminar el contrato, y si no es por su culpa le cuesta un mes de renta.",
        ),
        "brief": 1,
    },
    "LA-EVIC-01": {
        "n": (
            "the Los Angeles rent control eviction rules",
            "las reglas de desalojo del control de rentas de Los Ángeles",
        ),
        "r": (
            "You can only be evicted for a reason on the city's list.",
            "Solo lo pueden desalojar por una de las causas de la lista de la ciudad.",
        ),
        "o": (
            "You need a reason from the city's list to end a tenancy, and every eviction notice goes to the LA Housing Department within three business days.",
            "Necesita una causa de la lista de la ciudad para terminar un contrato, y cada aviso de desalojo va al Departamento de Vivienda de Los Ángeles en tres días hábiles.",
        ),
        "brief": 1,
        "ob": (
            "You'll need a reason from the city's list to end a tenancy, and no-fault evictions mean relocation payments.",
            "Necesitará una causa de la lista de la ciudad para terminar un contrato, y los desalojos sin culpa implican pagos de reubicación.",
        ),
    },
    "LA-EVIC-02": {
        "n": (
            "the Los Angeles just-cause ordinance",
            "la ordenanza de causa justa de Los Ángeles",
        ),
        "r": (
            "Your landlord needs a just cause to evict you.",
            "Su arrendador necesita una causa justa para desalojarlo.",
        ),
        "o": (
            "You need a just cause to end a tenancy.",
            "Necesita una causa justa para terminar un contrato.",
        ),
        "brief": 1,
    },
    "LA-EVIC-03": {
        "n": (
            "the Los Angeles demolition relocation rule",
            "la regla de reubicación por demolición de Los Ángeles",
        ),
        "r": (
            "If the building is torn down for new construction and your household is lower-income, you're owed 87,450 to 115,480 dollars in relocation.",
            "Si demuelen el edificio para construir y su hogar es de bajos ingresos, le corresponden de 87450 a 115480 dólares de reubicación.",
        ),
        "o": (
            "Demolishing for new construction means enhanced relocation for lower-income households: 87,450 to 115,480 dollars.",
            "Demoler para construir obliga a pagar una reubicación mayor a los hogares de bajos ingresos: de 87450 a 115480 dólares.",
        ),
    },
    "LA-EVIC-04": {
        "n": ("Los Angeles relocation assistance", "la ayuda de reubicación de Los Ángeles"),
        "r": (
            "If it's not your fault, you're owed 11,000 to 27,400 dollars to move.",
            "Si no es por culpa suya, le corresponden de 11000 a 27400 dólares para mudarse.",
        ),
        "ra": (
            "If it's not your fault, you're owed relocation money.",
            "Si no es por culpa suya, le corresponde una ayuda de reubicación.",
        ),
        "o": (
            "No-fault evictions cost 11,000 to 27,400 dollars in relocation, paid within 15 days.",
            "Los desalojos sin culpa del inquilino cuestan de 11000 a 27400 dólares de reubicación, pagados en 15 días.",
        ),
        "oa": (
            "No-fault evictions require relocation payments at the city's yearly rates, paid within 15 days.",
            "Los desalojos sin culpa del inquilino exigen pagar reubicación según las tarifas anuales de la ciudad, en 15 días.",
        ),
        "reset": (
            "new relocation amounts",
            "nuevos montos de reubicación",
        ),
        "brief": 2,
    },
    "SF-EVIC-01": {
        "n": ("San Francisco's just-cause rules", "las reglas de causa justa de San Francisco"),
        "r": (
            "You can only be evicted for one of 17 reasons in the city's rent law.",
            "Solo lo pueden desalojar por una de las 17 causas de la ley de rentas de la ciudad.",
        ),
        "o": (
            "You need one of the city's 17 just causes to end a tenancy, and it must be your main motive.",
            "Necesita una de las 17 causas justas de la ciudad para terminar un contrato, y debe ser su motivo principal.",
        ),
        "brief": 1,
        "ob": (
            "You'll need one of the city's 17 just causes to end a tenancy, and no-fault evictions mean relocation payments.",
            "Necesitará una de las 17 causas justas de la ciudad para terminar un contrato, y los desalojos sin culpa implican pagos de reubicación.",
        ),
    },
    "SF-EVIC-02": {
        "n": ("San Francisco relocation payments", "los pagos de reubicación de San Francisco"),
        "r": (
            "If it's not your fault, like an owner move-in, you're owed at least 8,245 dollars in relocation.",
            "Si no es por culpa suya, como cuando el dueño se muda, le corresponden al menos 8245 dólares de reubicación.",
        ),
        "ra": (
            "If it's not your fault, like an owner move-in, you're owed relocation money.",
            "Si no es por culpa suya, como cuando el dueño se muda, le corresponde una ayuda de reubicación.",
        ),
        "o": (
            "No-fault evictions, like an owner move-in, cost 8,245 dollars per tenant in relocation.",
            "Los desalojos sin culpa, como mudarse usted a la vivienda, cuestan 8245 dólares por inquilino en reubicación.",
        ),
        "oa": (
            "No-fault evictions, like an owner move-in, require relocation payments at the Rent Board's yearly rates.",
            "Los desalojos sin culpa, como mudarse usted a la vivienda, exigen pagar reubicación según las tarifas anuales de la Junta de Rentas.",
        ),
        "reset": (
            "new relocation amounts",
            "nuevos montos de reubicación",
        ),
        "brief": 2,
    },
    "SD-EVIC-01": {
        "n": ("San Diego's just-cause rules", "las reglas de causa justa de San Diego"),
        "r": (
            "Your landlord needs a just cause to end your tenancy. If it's not your fault, you're owed two months' rent in relocation, three if you're 62 or older or disabled.",
            "Su arrendador necesita una causa justa para terminar su contrato. Si no es por culpa suya, le corresponden dos meses de renta de reubicación, tres si tiene 62 años o más o una discapacidad.",
        ),
        "o": (
            "You need a just cause, stated in the notice, to end a tenancy. A no-fault ending costs two months' rent in relocation, three for tenants who are 62 or older or disabled.",
            "Necesita una causa justa, indicada en el aviso, para terminar un contrato. Si no es por culpa del inquilino, debe pagar dos meses de renta de reubicación, tres si tiene 62 años o más o una discapacidad.",
        ),
        "brief": 1,
    },
    "BER-EVIC-01": {
        "n": ("Berkeley's good-cause rules", "las reglas de causa justificada de Berkeley"),
        "r": (
            "Your landlord needs a good cause to evict you, and can't evict you over rent debt smaller than one month's fair market rent.",
            "Su arrendador necesita una causa justificada para desalojarlo, y no puede desalojarlo por una deuda de renta menor que un mes de renta de mercado.",
        ),
        "o": (
            "You need a good cause to evict, and every termination notice must be filed with the Berkeley Rent Board within three business days.",
            "Necesita una causa justificada para desalojar, y cada aviso de terminación debe presentarse a la Junta de Rentas de Berkeley en tres días hábiles.",
        ),
        "brief": 1,
    },
    "SA-EVIC-01": {
        "n": ("Santa Ana's just-cause rules", "las reglas de causa justa de Santa Ana"),
        "r": (
            "After 30 days here, your landlord needs a just cause to end your tenancy. If it's not your fault, you get three months' rent in relocation, or three months rent-free.",
            "Después de 30 días aquí, su arrendador necesita una causa justa para terminar su contrato. Si no es por culpa suya, recibe tres meses de renta de reubicación o tres meses sin pagar renta.",
        ),
        "o": (
            "After a tenant's first 30 days you need a just cause, in writing, to end the tenancy. A no-fault ending costs three months' rent in relocation, or the last three months rent-free.",
            "Después de los primeros 30 días de un inquilino, necesita una causa justa por escrito para terminar el contrato. Si no es por culpa del inquilino, debe pagar tres meses de renta de reubicación o perdonarle los últimos tres meses.",
        ),
        "brief": 1,
    },
    "NJ-EVIC-03": {
        "n": ("New Jersey's Anti-Eviction Act", "la Ley contra el Desalojo de Nueva Jersey"),
        "r": (
            "New Jersey law lets a landlord evict only for a good cause on the state's list, and usually only after a written notice.",
            "La ley de Nueva Jersey solo permite desalojar por una causa justificada de la lista estatal, y normalmente con un aviso por escrito.",
        ),
        "o": (
            "You need a good cause from the state's list to evict or refuse to renew, with written notice of three days to three years depending on the cause.",
            "Necesita una causa justificada de la lista estatal para desalojar o no renovar, con un aviso por escrito de tres días a tres años según la causa.",
        ),
        "brief": 1,
    },
    "NJ-EVIC-01": {
        "n": ("New Jersey's ban on retaliation", "la prohibición de represalias de Nueva Jersey"),
        "r": (
            "Your landlord can't evict you or refuse to renew as payback for a complaint.",
            "Su arrendador no puede desalojarlo ni negarse a renovar como represalia por una queja.",
        ),
        "o": (
            "You can't evict, change the lease or refuse to renew as payback for a tenant's complaint.",
            "No puede desalojar, cambiar el contrato ni negarse a renovar como represalia por una queja del inquilino.",
        ),
        "brief": 2,
    },
    "NJ-EVIC-02": {
        "n": (
            "New Jersey's foreclosure protections",
            "las protecciones de Nueva Jersey ante ejecuciones",
        ),
        "r": (
            "A foreclosure alone isn't a reason to evict you, and a buyer who wants to move in must give you 90 days' notice.",
            "Una ejecución hipotecaria no es por sí sola motivo para desalojarlo, y un comprador que quiera mudarse debe avisarle con 90 días.",
        ),
        "o": (
            "If you buy a foreclosed building, you must notify tenants within 10 business days and give 90 days' notice to move in yourself.",
            "Si compra un edificio en ejecución hipotecaria, debe avisar a los inquilinos en 10 días hábiles y darles 90 días de aviso para mudarse usted.",
        ),
    },
    "MA-EVIC-02": {
        "n": ("the Massachusetts notice rules", "las reglas de aviso de Massachusetts"),
        "r": (
            "To end your tenancy, your landlord must give written notice: at least 30 days or one rental period, and 14 days for unpaid rent.",
            "Para terminar su contrato, su arrendador debe avisarle por escrito: al menos 30 días o un período de renta, y 14 días por renta impaga.",
        ),
        "o": (
            "To end a tenancy you must give written notice: at least 30 days or one rental period, and 14 days for unpaid rent, which the tenant can usually cure.",
            "Para terminar un contrato debe avisar por escrito: al menos 30 días o un período de renta, y 14 días por renta impaga, que el inquilino normalmente puede saldar.",
        ),
        "brief": 1,
    },
    "MA-EVIC-01": {
        "n": ("the Massachusetts nonpayment notice", "el aviso por impago de Massachusetts"),
        "r": (
            "For unpaid rent, your landlord must give you 14 days' written notice.",
            "Por renta impaga, su arrendador debe darle 14 días de aviso por escrito.",
        ),
        "o": (
            "For unpaid rent you must give 14 days' written notice to quit.",
            "Por renta impaga debe dar 14 días de aviso por escrito.",
        ),
    },
    "MA-EVIC-03": {
        "n": (
            "the Massachusetts ban on retaliation",
            "la prohibición de represalias de Massachusetts",
        ),
        "r": (
            "Your landlord can't retaliate for a complaint; a notice to leave within six months of one is presumed retaliation.",
            "Su arrendador no puede tomar represalias por una queja; un aviso de desalojo dentro de los seis meses siguientes se presume represalia.",
        ),
        "o": (
            "You can't retaliate against a tenant for complaints; a notice or rent increase within six months of one is presumed retaliation.",
            "No puede tomar represalias contra un inquilino por sus quejas; un aviso o un aumento dentro de los seis meses siguientes se presume represalia.",
        ),
        "brief": 2,
    },
    "MA-EVIC-04": {
        "n": ("the Massachusetts nonpayment form", "el formulario estatal por impago"),
        "r": (
            "A notice for unpaid rent must come with the state's form on rental help and your rights.",
            "Un aviso por renta impaga debe venir con el formulario estatal sobre ayudas y sus derechos.",
        ),
        "o": (
            "A notice to quit for unpaid rent must come with the state's form, or the court won't take the case.",
            "Un aviso por renta impaga debe ir con el formulario estatal, o el tribunal no aceptará el caso.",
        ),
    },
    "BOS-EVIC-01": {
        "n": ("Boston's tenant notice rule", "la regla de aviso al inquilino de Boston"),
        "r": (
            "In Boston, any notice to end your tenancy must come with a notice of your rights and where to get help.",
            "En Boston, todo aviso para terminar su contrato debe venir con un aviso de sus derechos y de dónde pedir ayuda.",
        ),
        "o": (
            "In Boston, every notice to quit must come with the city's Notice of Tenants' Rights and Resources, and a copy goes to the city.",
            "En Boston, todo aviso de desalojo debe ir con el Aviso de Derechos y Recursos del Inquilino de la ciudad, y una copia va a la ciudad.",
        ),
        "brief": 3,
    },
    "CAM-EVIC-01": {
        "n": ("Cambridge's tenant guide rule", "la regla de la guía del inquilino de Cambridge"),
        "r": (
            "In Cambridge, your landlord must give you the city's tenant rights guide when you move in and with any notice to end your tenancy.",
            "En Cambridge, su arrendador debe darle la guía de derechos del inquilino de la ciudad al mudarse y con cualquier aviso de desalojo.",
        ),
        "o": (
            "In Cambridge, you must give tenants the city's Tenants Rights and Resources Guide at move-in and with any notice to quit.",
            "En Cambridge, debe entregar la guía de derechos y recursos del inquilino de la ciudad al inicio del contrato y con cualquier aviso de desalojo.",
        ),
        "brief": 3,
    },
    # ---------------------------------------------------------------- deposits
    "CA-DEP-01": {
        "n": ("California's deposit cap", "el tope estatal de depósitos"),
        "r": (
            "Your deposit can be at most one month's rent, or two with a small landlord, and comes back with an itemized statement within 21 days after you move out.",
            "Su depósito puede ser como máximo un mes de renta, o dos con un arrendador pequeño, y se le devuelve con un detalle por escrito en 21 días después de mudarse.",
        ),
        "o": (
            "You can ask for a deposit of at most one month's rent, two if you're a small landlord, and must return it with an itemized statement within 21 days.",
            "Puede pedir un depósito de como máximo un mes de renta, dos si es un arrendador pequeño, y debe devolverlo con un detalle por escrito en 21 días.",
        ),
        "dep": (
            "more than one month's rent as a deposit",
            "más de un mes de renta de depósito",
        ),
        "dep_o": (
            "more than one month's rent as a deposit",
            "más de un mes de renta de depósito",
        ),
        "brief": 1,
        "dep_small": (
            "more than one month's rent as a deposit, two for small landlords",
            "más de un mes de renta de depósito, dos con arrendadores pequeños",
        ),
        "dep_small_o": (
            "more than one month's rent as a deposit, two if you're a small landlord",
            "más de un mes de renta de depósito, dos si es un arrendador pequeño",
        ),
    },
    "LA-DEP-01": {
        "n": ("Los Angeles deposit interest", "los intereses del depósito en Los Ángeles"),
        "r": (
            "Your deposit also earns interest: 4.32 percent for 2025.",
            "Su depósito además genera intereses: 4,32 por ciento en 2025.",
        ),
        "ra": (
            "Your deposit also earns interest, at a rate the city sets each year.",
            "Su depósito además genera intereses, con una tasa que la ciudad fija cada año.",
        ),
        "o": (
            "You also owe interest on the deposit: 4.32 percent for 2025.",
            "Además debe pagar intereses sobre el depósito: 4,32 por ciento en 2025.",
        ),
        "oa": (
            "You also owe interest on the deposit, at the rate the city sets each year.",
            "Además debe pagar intereses sobre el depósito, con la tasa que la ciudad fija cada año.",
        ),
        "reset": (
            "a new deposit rate",
            "una nueva tasa para los depósitos",
        ),
        "brief": 2,
    },
    "SF-DEP-01": {
        "n": ("San Francisco deposit interest", "los intereses del depósito en San Francisco"),
        "r": (
            "Your deposit also earns 4.2 percent interest a year until {until}.",
            "Su depósito además genera un 4,2 por ciento de interés al año hasta el {until}.",
        ),
        "ra": (
            "Your deposit also earns interest, at a rate the Rent Board sets each March.",
            "Su depósito además genera intereses, con una tasa que la Junta de Rentas fija cada marzo.",
        ),
        "o": (
            "You also owe 4.2 percent interest a year on deposits until {until}.",
            "Además debe pagar un 4,2 por ciento de interés anual sobre los depósitos hasta el {until}.",
        ),
        "oa": (
            "You also owe interest on deposits, at the rate the Rent Board sets each March.",
            "Además debe pagar intereses sobre los depósitos, con la tasa que la Junta de Rentas fija cada marzo.",
        ),
        "reset": (
            "a new deposit rate",
            "una nueva tasa para los depósitos",
        ),
        "brief": 2,
    },
    "BER-DEP-01": {
        "n": ("Berkeley deposit interest", "los intereses del depósito en Berkeley"),
        "r": (
            "Your deposit also earns interest every year.",
            "Su depósito además genera intereses cada año.",
        ),
        "o": (
            "You also owe interest on the deposit every year, prorated if the tenant moves out.",
            "Además debe pagar intereses sobre el depósito cada año, prorrateados si el inquilino se muda.",
        ),
        "brief": 2,
    },
    "MA-DEP-01": {
        "n": ("the Massachusetts deposit rules", "las reglas de depósito de Massachusetts"),
        "r": (
            "Your deposit can be at most one month's rent. It must sit in a separate bank account and come back within 30 days after you move out.",
            "Su depósito puede ser como máximo un mes de renta. Debe estar en una cuenta bancaria aparte y devolverse en 30 días después de mudarse.",
        ),
        "o": (
            "You can take a deposit of at most one month's rent, hold it in a separate interest-bearing account, and return it within 30 days after move-out.",
            "Puede cobrar un depósito de como máximo un mes de renta, guardarlo en una cuenta aparte con intereses y devolverlo en 30 días después de la mudanza.",
        ),
        "brief": 1,
        "dep": (
            "more than one month's rent as a deposit",
            "más de un mes de renta de depósito",
        ),
    },
    "NJ-DEP-01": {
        "n": ("New Jersey's deposit rules", "las reglas de depósito de Nueva Jersey"),
        "r": (
            "Your deposit can be at most one and a half months' rent, and it comes back with interest within 30 days after you move out.",
            "Su depósito puede ser como máximo un mes y medio de renta, y se le devuelve con intereses en 30 días después de mudarse.",
        ),
        "o": (
            "You can take a deposit of at most one and a half months' rent, hold it in an interest-bearing New Jersey account, and return it within 30 days after the tenancy ends.",
            "Puede cobrar un depósito de como máximo un mes y medio de renta, guardarlo en una cuenta con intereses en Nueva Jersey y devolverlo en 30 días después del contrato.",
        ),
        "dep": (
            "more than one and a half months' rent as a deposit",
            "más de un mes y medio de renta de depósito",
        ),
        "brief": 1,
    },
    # ---------------------------------------------------------------- application and move-in fees
    "CA-FEE-01": {
        "n": ("California's application fee cap", "el tope estatal de cuotas de solicitud"),
        "until": "2026-12-31",  # the dollar figure is the 2026 one
        "r": (
            "An application fee can only cover real screening costs, up to about 69 dollars per applicant in 2026, and you get a receipt.",
            "Una cuota de solicitud solo puede cubrir los costos reales de revisión, hasta unos 69 dólares por solicitante en 2026, y le deben dar un recibo.",
        ),
        "ra": (
            "An application fee can only cover real screening costs, up to a cap that rises with inflation each year.",
            "Una cuota de solicitud solo puede cubrir los costos reales de revisión, hasta un tope que sube con la inflación cada año.",
        ),
        "o": (
            "Application fees may only cover your real screening costs, up to about 69 dollars per applicant in 2026, with a receipt and a refund of anything unused.",
            "Las cuotas de solicitud solo pueden cubrir sus costos reales de revisión, hasta unos 69 dólares por solicitante en 2026, con recibo y devolución de lo que no use.",
        ),
        "oa": (
            "Application fees may only cover your real screening costs, up to a cap that rises with inflation each year, with a receipt and a refund of anything unused.",
            "Las cuotas de solicitud solo pueden cubrir sus costos reales de revisión, hasta un tope que sube con la inflación cada año, con recibo y devolución de lo que no use.",
        ),
        "fee": (
            "more than about 69 dollars to apply",
            "más de unos 69 dólares por solicitar",
        ),
        "fee_after": (
            "an application fee above the inflation-adjusted cap",
            "una cuota de solicitud por encima del tope ajustado por inflación",
        ),
        "brief": 1,
    },
    "NJ-FEE-01": {
        "n": ("New Jersey's application fee cap", "el tope de cuotas de solicitud de Nueva Jersey"),
        "r": (
            "An application fee can be at most 50 dollars, adjusted for inflation.",
            "Una cuota de solicitud puede ser como máximo de 50 dólares, ajustada por inflación.",
        ),
        "o": (
            "Application fees are capped at 50 dollars per application, adjusted for inflation each year.",
            "Las cuotas de solicitud tienen un tope de 50 dólares por solicitud, ajustado por inflación cada año.",
        ),
        "fee": (
            "more than 50 dollars plus inflation to apply",
            "más de 50 dólares más inflación por solicitar",
        ),
        "brief": 1,
    },
    "MA-FEE-02": {
        "n": (
            "the Massachusetts move-in charge rules",
            "las reglas de cobros de mudanza de Massachusetts",
        ),
        "r": (
            "Up front, a landlord can only ask for first and last month's rent, the deposit and the cost of a new lock.",
            "Al inicio, el arrendador solo puede pedir el primer y el último mes de renta, el depósito y el costo de una cerradura nueva.",
        ),
        "o": (
            "Up front you may only charge first and last month's rent, a deposit and the cost of a lock and key. Application fees aren't allowed.",
            "Al inicio solo puede cobrar el primer y el último mes de renta, el depósito y el costo de llave y cerradura. Las cuotas de solicitud no están permitidas.",
        ),
        "fee": ("any application fee", "cualquier cuota de solicitud"),
        "brief": 1,
    },
    "MA-FEE-01": {
        "n": ("the Massachusetts broker fee rule", "la regla de comisiones de Massachusetts"),
        "r": (
            "A broker fee is paid by whoever hired the broker.",
            "La comisión del corredor la paga quien lo contrató.",
        ),
        "o": (
            "A broker fee is paid by whoever hired the broker.",
            "La comisión del corredor la paga quien lo contrató.",
        ),
        "brief": 2,
    },
    "BER-FEE-01": {
        "n": ("Berkeley's fee rules", "las reglas de cuotas de Berkeley"),
        "r": (
            "Berkeley also bans non-refundable fees to renew your lease or add a roommate.",
            "Berkeley además prohíbe cobrar cuotas no reembolsables por renovar su contrato o sumar a un compañero de vivienda.",
        ),
        "o": (
            "You must give applicants Berkeley's fee rights statement, and can't charge non-refundable fees to renew or add a roommate.",
            "Debe entregar a los solicitantes la declaración de derechos sobre cuotas de Berkeley, y no puede cobrar cuotas no reembolsables por renovar o sumar a un compañero de vivienda.",
        ),
        "brief": 2,
    },
    # ---------------------------------------------------------------- tenant screening
    "CA-SCR-01": {
        **VOUCHER,
        "n": (
            "California's income-source protection",
            "la protección estatal de la fuente de ingresos",
        ),
    },
    "NJ-SCR-01": {
        **VOUCHER,
        "n": (
            "New Jersey's income-source protection",
            "la protección de la fuente de ingresos de Nueva Jersey",
        ),
    },
    "SD-SCR-01": {
        **VOUCHER,
        "n": (
            "San Diego's income-source protection",
            "la protección de la fuente de ingresos de San Diego",
        ),
        "missing": "text",
    },
    "MA-SCR-01": {
        **VOUCHER,
        "n": (
            "the Massachusetts assistance protection",
            "la protección de ayudas de Massachusetts",
        ),
    },
    "BOS-SCR-01": {
        **VOUCHER,
        "n": ("Boston's voucher protection", "la protección de vales de Boston"),
        "brief": 2,
    },
    "CAM-SCR-01": {
        **VOUCHER,
        "n": (
            "Cambridge's income-source protection",
            "la protección de la fuente de ingresos de Cambridge",
        ),
        "brief": 2,
    },
    "CA-SCR-02": {
        "n": (
            "California's criminal-record rules",
            "las reglas estatales sobre antecedentes penales",
        ),
        "r": (
            "Landlords can check criminal records, but can't use blanket bans, arrests without a conviction, or sealed or juvenile records.",
            "Pueden revisar antecedentes penales, pero sin rechazos generales, y no cuentan los arrestos sin condena ni los registros sellados o juveniles.",
        ),
        "o": (
            "You may check criminal history, but no blanket bans; arrests without a conviction and sealed or juvenile records are off limits.",
            "Puede revisar antecedentes penales, pero sin rechazos generales; los arrestos sin condena y los registros sellados o juveniles no se pueden usar.",
        ),
        "brief": 2,
    },
    "NJ-SCR-02": {
        "n": ("New Jersey's fair chance rules", "las reglas de oportunidad justa de Nueva Jersey"),
        "r": (
            "A landlord can't ask about your criminal record until after making you a conditional offer.",
            "Un arrendador no puede preguntar por sus antecedentes penales antes de hacerle una oferta condicional.",
        ),
        "o": (
            "You can't ask about criminal history before a conditional offer, and afterwards only certain recent convictions count.",
            "No puede preguntar por antecedentes penales antes de una oferta condicional, y después solo cuentan ciertas condenas recientes.",
        ),
        "brief": 2,
    },
    "BER-SCR-01": {
        "n": ("Berkeley's fair chance rules", "las reglas de oportunidad justa de Berkeley"),
        "r": (
            "In Berkeley, landlords can't ask about or use your criminal history at all.",
            "En Berkeley, los arrendadores no pueden preguntar ni usar sus antecedentes penales.",
        ),
        "o": (
            "In Berkeley you can't ask about or use criminal history in choosing tenants; fines run from 1,000 to 10,000 dollars.",
            "En Berkeley no puede preguntar ni usar antecedentes penales para elegir inquilinos; las multas van de 1000 a 10000 dólares.",
        ),
        "brief": 1,
    },
    "SF-SCR-01": {
        "n": (
            "San Francisco's Fair Chance Ordinance",
            "la Ordenanza de Oportunidad Justa de San Francisco",
        ),
        "r": (
            "In San Francisco affordable housing, your arrest or conviction history is protected under the Fair Chance Ordinance.",
            "En la vivienda asequible de San Francisco, sus antecedentes de arresto o condena están protegidos por la Ordenanza de Oportunidad Justa.",
        ),
        "o": (
            "In San Francisco affordable housing, the Fair Chance Ordinance limits how you use arrest and conviction records.",
            "En la vivienda asequible de San Francisco, la Ordenanza de Oportunidad Justa limita cómo usa los antecedentes de arresto y condena.",
        ),
        "brief": 3,
        "missing": "affordable",
    },
    "BOS-SCR-02": {
        "n": (
            "Boston's tenant selection policy",
            "la política de selección de inquilinos de Boston",
        ),
        "r": (
            "In city-funded or income-restricted housing, convictions older than 5 years and credit scores can't be used against you.",
            "En vivienda financiada por la ciudad o con ingresos restringidos, no pueden usar contra usted condenas de más de 5 años ni su puntaje de crédito.",
        ),
        "o": (
            "In city-funded or income-restricted housing you can't use blanket criminal bans, convictions older than 5 years, or credit scores.",
            "En vivienda financiada por la ciudad o con ingresos restringidos no puede usar rechazos generales por antecedentes, condenas de más de 5 años ni puntajes de crédito.",
        ),
        "brief": 3,
    },
    # ---------------------------------------------------------------- rent-setting software
    "CA-ALG-01": {
        "n": (
            "California's ban on shared pricing software",
            "la prohibición estatal de software de precios compartido",
        ),
        "r": (
            "Landlords can't coordinate rents through shared pricing software that uses competitors' data.",
            "Los arrendadores no pueden coordinar rentas con software de precios compartido que usa datos de la competencia.",
        ),
        "o": (
            "You can't use shared pricing software that coordinates rents with competitors' data.",
            "No puede usar software de precios compartido que coordina rentas con datos de la competencia.",
        ),
        "brief": 2,
    },
    "SF-ALG-01": {
        **ALGO,
        "n": (
            "San Francisco's rent software ban",
            "la prohibición de software de rentas de San Francisco",
        ),
    },
    "SD-ALG-01": {
        **ALGO,
        "n": ("San Diego's rent software ban", "la prohibición de software de rentas de San Diego"),
    },
    "BER-ALG-01": {
        **ALGO,
        "n": ("Berkeley's rent software ban", "la prohibición de software de rentas de Berkeley"),
    },
    "SA-ALG-01": {
        **ALGO,
        "n": ("Santa Ana's rent software ban", "la prohibición de software de rentas de Santa Ana"),
    },
    "JC-ALG-01": {
        **ALGO,
        "n": (
            "Jersey City's rent software ban",
            "la prohibición de software de rentas de Jersey City",
        ),
    },
    "HOB-ALG-01": {
        **ALGO,
        "n": ("Hoboken's rent software ban", "la prohibición de software de rentas de Hoboken"),
    },
    "NJ-ALG-01": {
        **ALGO,
        "n": (
            "New Jersey's ban on rent-setting software",
            "la prohibición de software para fijar rentas de Nueva Jersey",
        ),
    },
    "MA-ALG-P1": {
        "n": (
            "A Massachusetts bill to ban rent-setting software",
            "Un proyecto de ley de Massachusetts para prohibir el software que fija rentas",
        )
    },
    "MA-ALG-P2": {
        "n": (
            "A Massachusetts bill to ban rent-setting software",
            "Un proyecto de ley de Massachusetts para prohibir el software que fija rentas",
        )
    },
}

# Local agencies named in the rules data (requirement / key value texts). Names only, never contact details.
AGENCY = {
    "Los Angeles": ("the LA Housing Department", "el Departamento de Vivienda de Los Ángeles"),
    "San Francisco": ("the San Francisco Rent Board", "la Junta de Rentas de San Francisco"),
    "Berkeley": ("the Berkeley Rent Board", "la Junta de Rentas de Berkeley"),
    "Jersey City": (
        "the city's Office of Landlord-Tenant Relations",
        "la Oficina de Relaciones entre Propietarios e Inquilinos de la ciudad",
    ),
    "Hoboken": ("the Hoboken rent control office", "la oficina de control de rentas de Hoboken"),
    "Newark": ("the Newark rent control office", "la oficina de control de rentas de Newark"),
}

# ------------------------------------------------------------------ fixed phrases
W = {
    "en": {
        "open_renter": "For renters at {a}, as of {d}.",
        "open_owner": "For owners and managers of {a}, as of {d}.",
        "maybe": "{n} may cover this building, but we can't tell yet.",
        "excluded": "{n} doesn't cover this building.",
        "no_rule": "No rule we track covers this here.",
        "no_rent_rule": "No rent cap we track covers this building.",
        "caps_renter": "If they ask for {x}, that's over the limit.",
        "caps_owner": "You can't ask for {x}.",
        "or": ", or ",
        "or_owner": ", or ",
        "and": " and ",
        "coming_renter": "Coming up: ",
        "coming_owner": "Plan ahead: ",
        "nothing_new": "Nothing we track changes here in the next 12 months.",
        "starts": "On {date}, {n} takes effect.",
        "pending": "{N} is being debated, but it isn't law yet.",
        "reset": "On {date}, the city sets {x}.",
        "next_rent_renter": "Want to check a rent increase? Use 'Check a rent increase' below.",
        "next_dep_renter": "Want to check a deposit? Use 'Check a deposit' below.",
        "next_rent_owner": "Before you send a rent increase, try 'Check a rent increase' below.",
        "next_dep_owner": "Before you take a deposit, try 'Check a deposit' below.",
        "agency": "For rent control questions, {g} is the place to ask.",
        "sources": "Every point has its source on screen.",
        "nla": "This is general information, not legal advice.",
        "nla_short": "General information, not legal advice.",
        "verb1": "applies",
        "verbn": "apply",
    },
    "es": {
        "open_renter": "Para inquilinos de {a}, al {d}.",
        "open_owner": "Para dueños y administradores de {a}, al {d}.",
        "maybe": "Es posible que {n} cubra este edificio, pero aún no podemos saberlo.",
        "excluded": "{N} no cubre este edificio.",
        "no_rule": "Aquí no aplica ninguna regla que sigamos sobre este tema.",
        "no_rent_rule": "Ningún tope de renta que sigamos cubre este edificio.",
        "caps_renter": "Si le piden {x}, eso supera el límite.",
        "caps_owner": "No puede pedir {x}.",
        "or": ", o ",
        "or_owner": ", ni ",
        "and": " y ",
        "coming_renter": "Lo que viene: ",
        "coming_owner": "Para planificar: ",
        "nothing_new": "En los próximos 12 meses no cambia nada de lo que seguimos aquí.",
        "starts": "El {date} entra en vigor {n}.",
        "pending": "{N} está en debate, pero aún no es ley.",
        "reset": "El {date} la ciudad fija {x}.",
        "next_rent_renter": "¿Quiere revisar un aumento de renta? Use 'Revisar un aumento de renta' más abajo.",
        "next_dep_renter": "¿Quiere revisar un depósito? Use 'Revisar un depósito' más abajo.",
        "next_rent_owner": "Antes de enviar un aumento, pruebe 'Revisar un aumento de renta' más abajo.",
        "next_dep_owner": "Antes de cobrar un depósito, pruebe 'Revisar un depósito' más abajo.",
        "agency": "Para preguntas sobre el control de rentas, puede consultar a {g}.",
        "sources": "Cada punto tiene su fuente en pantalla.",
        "nla": "Esto es información general, no asesoría legal.",
        "nla_short": "Información general, no asesoría legal.",
        "verb1": "aplica",
        "verbn": "aplican",
    },
}

# A topic as a whole, for unknowns that hold up more than two rules.
TOPIC_WORDS = {
    "en": {
        "rent_increase_limits": "the rent cap",
        "just_cause_eviction": "eviction protections",
        "security_deposits": "the deposit cap",
        "application_screening_fees": "the fee cap",
        "screening_restrictions": "the screening rules",
        "algorithmic_rent_setting": "the rent software ban",
    },
    "es": {
        "rent_increase_limits": "el tope de renta",
        "just_cause_eviction": "la protección contra desalojo",
        "security_deposits": "el tope de depósito",
        "application_screening_fees": "el tope de cuotas",
        "screening_restrictions": "las reglas de selección",
        "algorithmic_rent_setting": "la prohibición de software de rentas",
    },
}

# What an "unknown" result is waiting for, said per persona. {n} = rule name(s), {v} = applies / apply,
# {g} = ", or check with <agency>" when the city has one.
MISSING_KEY = {
    "Year built / certificate-of-occupancy date": "yob",
    "Owner type": "owner",
    "Number of units": "units",
    "Exemption filing / registration status": "filing",
    "Length of tenancy": "tenancy",
}
UNKNOWN = {
    "en": {
        "yob": (
            "We don't know the building's exact certificate-of-occupancy date, which decides whether {n} {v}. Ask your landlord{g}.",
            "Whether {n} {v} depends on your building's certificate-of-occupancy date, so keep that certificate handy.",
        ),
        "owner": (
            "We don't know if the owner is a person or a company, which decides whether {n} {v}. Ask your landlord.",
            "Whether {n} {v} depends on whether you own as a person or through a company.",
        ),
        "units": (
            "We don't know how many units the building has, which decides whether {n} {v}.",
            "Whether {n} {v} depends on how many units your building has.",
        ),
        "filing": (
            "We don't know if the owner filed for an exemption, which decides whether {n} {v}. Ask your landlord{g}.",
            "Whether {n} {v} depends on whether you've filed for an exemption.",
        ),
        "tenancy": (
            "Whether {n} {v} depends on how long you've lived here.",
            "Whether {n} {v} depends on how long the tenant has lived there.",
        ),
        "affordable": (
            "We don't know if this is an affordable housing building, which decides whether {n} {v}.",
            "Whether {n} {v} depends on whether this is an affordable housing building.",
        ),
        "text": (
            "We couldn't read the text of {n}, so we can't confirm the details.",
            "We couldn't read the text of {n}, so we can't confirm the details.",
        ),
        "other": (
            "Whether {n} {v} depends on a fact that isn't in the public data. Ask your landlord{g}.",
            "Whether {n} {v} depends on a fact about your building that isn't in the public data.",
        ),
        "ask": ", or check with {g}",
    },
    "es": {
        "yob": (
            "No sabemos la fecha exacta del certificado de ocupación del edificio, y de eso depende si {v} {n}. Pregúntele a su arrendador{g}.",
            "Si {v} {n} depende de la fecha del certificado de ocupación de su edificio; téngalo a mano.",
        ),
        "owner": (
            "No sabemos si el dueño es una persona o una empresa, y de eso depende si {v} {n}. Pregúntele a su arrendador.",
            "Si {v} {n} depende de si usted es dueño como persona o a través de una empresa.",
        ),
        "units": (
            "No sabemos cuántas viviendas tiene el edificio, y de eso depende si {v} {n}.",
            "Si {v} {n} depende de cuántas viviendas tiene su edificio.",
        ),
        "filing": (
            "No sabemos si el dueño registró una exención, y de eso depende si {v} {n}. Pregúntele a su arrendador{g}.",
            "Si {v} {n} depende de si usted registró una exención.",
        ),
        "tenancy": (
            "Si {v} {n} depende de cuánto tiempo lleva viviendo aquí.",
            "Si {v} {n} depende de cuánto tiempo lleva el inquilino en la vivienda.",
        ),
        "affordable": (
            "No sabemos si este edificio es vivienda asequible, y de eso depende si {v} {n}.",
            "Si {v} {n} depende de si este edificio es vivienda asequible.",
        ),
        "text": (
            "No pudimos leer el texto de {n}, así que no podemos confirmar los detalles.",
            "No pudimos leer el texto de {n}, así que no podemos confirmar los detalles.",
        ),
        "other": (
            "Si {v} {n} depende de un dato que no está en las fuentes públicas. Pregúntele a su arrendador{g}.",
            "Si {v} {n} depende de un dato de su edificio que no está en las fuentes públicas.",
        ),
        "ask": ", o consulte con {g}",
    },
}

# ------------------------------------------------------------------ helpers
STREET = {
    "ST": "Street",
    "AVE": "Avenue",
    "AV": "Avenue",
    "BLVD": "Boulevard",
    "BL": "Boulevard",
    "BLV": "Boulevard",
    "RD": "Road",
    "DR": "Drive",
    "PL": "Place",
    "CT": "Court",
    "LN": "Lane",
    "TER": "Terrace",
    "PK": "Park",
    "PKWY": "Parkway",
    "WY": "Way",
    "HWY": "Highway",
    "SQ": "Square",
    "CIR": "Circle",
    "JR": "Junior",
}
LEADING = {"N": "North", "S": "South", "E": "East", "W": "West", "MT": "Mount", "ST": "Saint"}


def say_street(s: str, lang: str) -> str:
    """'6238 DE LONGPRE AVE' -> '6238 De Longpre Avenue'; '315-319 X ST' -> '315 to 319 X Street'."""
    words = [
        w.rstrip(".") for w in (s or "").replace("&", " and " if lang == "en" else " y ").split()
    ]
    out = []
    for i, w in enumerate(words):
        u = w.upper()
        last = i == len(words) - 1
        if re.fullmatch(r"\d+-\d+", w):
            a, b = w.split("-")
            out.append(f"{a} {'to' if lang == 'en' else 'a'} {b}")
        elif any(c.isdigit() for c in w):
            out.append(w.lower())
        elif last and u in STREET:
            out.append(STREET[u])
        elif not last and u in LEADING:
            out.append(LEADING[u])
        elif u in STREET and u not in ("ST",):
            out.append(STREET[u])
        else:
            out.append(w.capitalize())
    return " ".join(out)


def _val(d: dict, key: str, lang: str) -> str | None:
    v = d.get(key)
    return v[0 if lang == "en" else 1] if v else None


def _until(rid: str) -> str | None:
    s = SAY.get(rid, {})
    return s.get("until") or H.HEADLINES.get(rid, {}).get("until")


def _after(rid: str, as_of: str) -> bool:
    u = _until(rid)
    return bool(u and as_of > u)


def name(rid: str, lang: str) -> str:
    return _val(SAY.get(rid, {}), "n", lang) or rid


def rule_sentence(rid: str, persona: str, lang: str, as_of: str, brief: bool = False) -> str:
    """What the rule means for this persona on as_of, one or two sentences (brief: the briefing's wording)."""
    s = SAY.get(rid)
    p = "r" if persona == "renter" else "o"
    if not s or p not in s:  # not hand-written: the row answer as a sentence
        h = H.headline(rid, lang, as_of) or ""
        return cap(re.sub(r"\s*\([^)]*\)", "", h).rstrip(".")) + "." if h else ""
    key = p + "a" if _after(rid, as_of) and p + "a" in s else p
    if brief and p + "b" in s and key == p:
        key = p + "b"
    u = _until(rid)
    return _val(s, key, lang).format(until=say_date(u, lang) if u else "")


def _items(cat: dict, *results: str) -> list[dict]:
    return [i for i in cat.get("enacted") or [] if i["result"] in results]


def _brief_order(i: dict):
    rid = i["rule"]["team_rule_id"]
    b = SAY.get(rid, {}).get("brief")
    pr = (H.HEADLINES.get(rid) or {}).get("priority") or 9
    return (b if b is not None else 9, pr, 0 if i["rule"].get("level") == "city" else 1)


def _rent_rule(cat: dict) -> dict | None:
    """The governing rent rule: an applying one (local rules come first), else an unknown one."""
    for res in ("applies", "unknown"):
        items = sorted(
            _items(cat, res),
            key=lambda i: (not i.get("overrides_here"), i["rule"].get("level") != "city"),
        )
        if items:
            return items[0]
    return None


def _join(names: list[str], lang: str) -> str:
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + W[lang]["and"] + names[-1]


# ------------------------------------------------------------------ sections
def topic_lines(cat: dict, persona: str, lang: str, as_of: str, brief: bool) -> list[str]:
    """What the topic means. Briefing: the essentials only; Explain this: up to three rules."""
    w = W[lang]
    cid = cat["id"]
    if cid == "rent_increase_limits":
        top = _rent_rule(cat)
        if not top:
            ex = cat.get("excluded") or []
            if ex and ex[0]["id"] in SAY:
                return [
                    w["excluded"].format(n=name(ex[0]["id"], lang), N=cap(name(ex[0]["id"], lang)))
                ] + ([] if brief else [w["no_rent_rule"]])
            return [w["no_rent_rule"]]
        rid = top["rule"]["team_rule_id"]
        if top["result"] == "unknown":
            return [cap(w["maybe"].format(n=name(rid, lang)))]
        return [rule_sentence(rid, persona, lang, as_of)]
    applies = sorted(_items(cat, "applies"), key=_brief_order)
    if brief:
        applies = [i for i in applies if SAY.get(i["rule"]["team_rule_id"], {}).get("brief")]
    out: list[str] = []
    budget = 230 if brief else 300
    for i in applies[: 2 if brief else 3]:
        s = rule_sentence(i["rule"]["team_rule_id"], persona, lang, as_of, brief)
        if s and s not in out and (not out or sum(map(len, out)) + len(s) <= budget):
            out.append(s)
    if out or brief:
        return out
    unknown = sorted(_items(cat, "unknown"), key=_brief_order)
    if unknown:
        return [cap(w["maybe"].format(n=name(unknown[0]["rule"]["team_rule_id"], lang)))]
    ex = cat.get("excluded") or []
    if ex and ex[0]["id"] in SAY:
        n = name(ex[0]["id"], lang)
        return [w["excluded"].format(n=cap(n), N=cap(n))]
    return [] if cat.get("pending") else [w["no_rule"]]


def caps_line(cats: dict, persona: str, lang: str, as_of: str, small: bool = True) -> str | None:
    """'If they ask for a deposit above one month's rent, or an application fee above ..., that's over the limit.'"""
    parts = []
    for cid, key in (("security_deposits", "dep"), ("application_screening_fees", "fee")):
        for i in sorted(_items(cats.get(cid, {}), "applies"), key=_brief_order):
            rid = i["rule"]["team_rule_id"]
            s = SAY.get(rid, {})
            ks = [key + "_after"] if _after(rid, as_of) else []
            if small:  # a small landlord (at most 4 units) may be allowed more
                ks += [key + "_small_o"] if persona == "owner" else []
                ks += [key + "_small"]
            ks += [key + "_o"] if persona == "owner" else []
            k = next((k for k in [*ks, key] if k in s), None)
            if k:
                parts.append(_val(s, k, lang))
                break
    if not parts:
        return None
    w = W[lang]
    return w["caps_" + persona].format(x=w["or" if persona == "renter" else "or_owner"].join(parts))


def unknown_lines(
    cats: list[dict], persona: str, lang: str, city: str | None, limit: int
) -> list[tuple[str, str]]:
    """(category, sentence) per missing fact: what we don't know and what would settle it."""
    groups: dict[str, list[tuple[str, str]]] = {}
    for c in cats:
        for i in _items(c, "unknown"):
            rid = i["rule"]["team_rule_id"]
            fact = SAY.get(rid, {}).get("missing") or MISSING_KEY.get(
                i.get("missing_fact") or "", "other"
            )
            if fact == "said":
                continue
            groups.setdefault(fact, [])
            if rid not in [r for _, r in groups[fact]]:
                groups[fact].append((c["id"], rid))
    t = UNKNOWN[lang]
    w = W[lang]
    ag = _val(AGENCY, city, lang) if city in AGENCY else None
    out = []
    for fact, rules in list(groups.items())[:limit]:
        names = [name(r, lang) for _, r in rules]
        if len(names) > 2:  # name the topics instead of every rule
            names = list(dict.fromkeys(TOPIC_WORDS[lang][cid] for cid, _ in rules))
        n = _join(names, lang)
        v = w["verb1"] if len(names) == 1 else w["verbn"]
        g = t["ask"].format(g=ag) if ag else ""
        s = t[fact][0 if persona == "renter" else 1].format(n=n, v=v, g=g)
        out.append((rules[0][0], cap(s)))
    return out


def change_lines(
    cats: list[dict], persona: str, lang: str, as_of: str, limit: int
) -> list[tuple[str, str]]:
    """What changes at this address in the next 12 months, by date: rules taking effect and figures the city
    sets anew (headlines.py periods). Same-day figures share one sentence."""
    w = W[lang]
    end = (dt.date.fromisoformat(as_of) + dt.timedelta(days=365)).isoformat()
    starts: list[tuple[str, str, str]] = []
    resets: dict[str, list[tuple[str, str]]] = {}
    for c in cats:
        for i in c.get("enacted") or []:
            rid = i["rule"]["team_rule_id"]
            if i["result"] == "not_yet_effective":
                eff = i["rule"].get("effective_date_norm")
                if eff and as_of < eff <= end:
                    n = name(rid, lang)
                    s = w["starts"].format(date=say_date(eff, lang), n=n, N=cap(n))
                    starts.append((eff, c["id"], s))
            elif i["result"] == "applies" and SAY.get(rid, {}).get("reset"):
                u = H.HEADLINES.get(rid, {}).get("until")
                if u and as_of <= u:
                    nxt = (dt.date.fromisoformat(u) + dt.timedelta(days=1)).isoformat()
                    x = _val(SAY[rid], "reset", lang)
                    if nxt <= end and x not in [y for _, y in resets.get(nxt, [])]:
                        resets.setdefault(nxt, []).append((c["id"], x))
    dated = list(starts)
    for day, xs in resets.items():
        s = w["reset"].format(date=say_date(day, lang), x=_join([x for _, x in xs], lang))
        dated.append((day, xs[0][0], s))
    dated.sort()
    return [(cid, s) for _, cid, s in dated[:limit]]


def pending_line(cats: list[dict], lang: str) -> tuple[str, str] | None:
    """At most one bill that is being debated (not law)."""
    for c in cats:
        for i in c.get("pending") or []:
            return (
                c["id"],
                W[lang]["pending"].format(N=cap(name(i["rule"]["team_rule_id"], lang))),
            )
    return None


# ------------------------------------------------------------------ the two products
Script = list[tuple[str | None, str]]
TARGET = {
    "en": 680,
    "es": 760,
}  # characters: about 50-53 s at the voice's ~12-13 characters per second
TOPIC_RULES = 170  # "Explain this": about 10-15 s, the rule first
TOPIC_TOTAL = {"en": 230, "es": 260}
TOPIC_MAX = {"en": 330, "es": 370}
CORE = {
    "rent_increase_limits",
    "just_cause_eviction",
    "security_deposits",
    "application_screening_fees",
}


def briefing(d: dict, persona: str, lang: str) -> Script:
    """The spoken briefing for an address (d = web.app.build_address(...)).

    Renter: rent limit, eviction protection, deposit and fee caps, what changes, what is unknown, one next step.
    Owner: the same as obligations; what to settle, the next step, and last what to prepare for.
    Over TARGET, optional lines are dropped (highest rank first) until it fits.
    """
    w = W[lang]
    as_of = d["as_of"]
    cats = {c["id"]: c for c in d["categories"]}
    city = (d.get("jurisdiction") or {}).get("city")
    street = say_street(d["address"]["street_address"], lang)
    # (category, sentence, drop rank: 0 = always kept)
    head = [(None, w["open_" + persona].format(a=street, d=say_date(as_of, lang)), 0)]
    facts = []
    for cid in ("rent_increase_limits", "just_cause_eviction"):
        for n, s in enumerate(topic_lines(cats[cid], persona, lang, as_of, brief=True)):
            facts.append((cid, s, 2 if n else 0))
    try:
        small = int(float(d["address"].get("units") or 0)) <= 4
    except ValueError:
        small = True
    caps = caps_line(cats, persona, lang, as_of, small)
    if caps:
        facts.append(("security_deposits", caps, 0))
    ch = change_lines(list(cats.values()), persona, lang, as_of, limit=2)
    changes = [
        (cid, (w["coming_" + persona] + s[0].lower() + s[1:]) if n == 0 else s, 3 if n else 0)
        for n, (cid, s) in enumerate(ch)
    ]
    if not changes:
        changes = [(None, w["nothing_new"], 0)]
    pend = pending_line(list(cats.values()), lang)
    if pend:
        changes.append((*pend, 4))
    unknowns = [
        (cid, s, (1 if n else 0) if cid in CORE else 5)
        for n, (cid, s) in enumerate(
            unknown_lines(list(cats.values()), persona, lang, city, limit=2)
        )
    ]
    rent = _rent_rule(cats["rent_increase_limits"])
    if rent and rent["result"] == "unknown":  # say right away what the rent cap depends on
        hit = next((u for u in unknowns if u[0] == "rent_increase_limits"), None)
        if hit:
            unknowns.remove(hit)
            facts = [hit if f[0] == "rent_increase_limits" else f for f in facts]
    # one next step: the check that fits, plus the local agency if the data names one and it wasn't said yet
    capped = bool(
        rent
        and rent["result"] == "applies"
        and not SAY.get(rent["rule"]["team_rule_id"], {}).get("no_cap")
    )
    nxt = [(None, w[("next_rent_" if capped else "next_dep_") + persona], 0)]
    said = " ".join(s for _, s, _ in facts + unknowns)
    ag = _val(AGENCY, city, lang) if city in AGENCY else None
    if capped and ag and ag not in said:
        nxt.append((None, w["agency"].format(g=ag), 6))
    if persona == "renter":
        body = head + facts + changes + unknowns + nxt
    else:
        body = head + facts + unknowns + nxt + changes
    body += [(None, w["sources"], 0), (None, w["nla"], 0)]
    while len(" ".join(s for _, s, _ in body)) > TARGET[lang] and any(r for _, _, r in body):
        worst = max(r for _, _, r in body)
        i = max(i for i, x in enumerate(body) if x[2] == worst)
        body.pop(i)
    return [(cid, s) for cid, s, _ in body]


def topic(d: dict, cat_id: str, persona: str, lang: str) -> Script:
    """'Explain this' for one topic: what it means, what is unknown, what changes soon (about 10-15 s)."""
    w = W[lang]
    as_of = d["as_of"]
    c = next(x for x in d["categories"] if x["id"] == cat_id)
    city = (d.get("jurisdiction") or {}).get("city")
    out: list[str] = []
    for s in topic_lines(c, persona, lang, as_of, brief=False):
        if not out or len(" ".join(out)) + len(s) <= TOPIC_RULES:
            out.append(s)
    unknown = [s for _, s in unknown_lines([c], persona, lang, city, limit=1)]
    if unknown and not _items(
        c, "applies"
    ):  # nothing applies for sure: what it depends on is the answer
        out = []
    later = [s for _, s in change_lines([c], persona, lang, as_of, limit=1)]
    pend = pending_line([c], lang)
    later += [pend[1]] if pend else []
    # what is unknown (kept unless far too long), then what changes (only while it stays short)
    for s, limit in [(x, TOPIC_MAX[lang]) for x in unknown] + [
        (x, TOPIC_TOTAL[lang]) for x in later
    ]:
        if not out or len(" ".join(out)) + len(s) <= limit:
            out.append(s)
    out.append(w["nla_short"])
    return [(cat_id, s) for s in out]


def text_of(script: Script) -> str:
    return " ".join(s for _, s in script)


def chapters(script: Script) -> list[list]:
    """[[category or "", first character], ...] where the spoken topic changes; the client maps it onto time."""
    out, pos, last = [], 0, object()
    for cid, s in script:
        if cid != last:
            out.append([cid or "", pos])
            last = cid
        pos += len(s) + 1
    return out
