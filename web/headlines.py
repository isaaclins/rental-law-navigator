"""One-line, plain-language answers per rule: the single source for the address page rows, Compare and Listen.

Hand-written from each rule's key_value (outputs/rules.json stays untouched). Fields:
- en / es: the row answer, 8 words or fewer, the number first.
- short_en / short_es, priority: the compact cell text Compare uses; priority 1 leads, <= 1.5 may be appended,
  2 only when nothing else applies (Compare's rules, #48).
- from / until + after_en / after_es (and short_from / short_until + short_after_*): the figure belongs to a period;
  before `from` or after `until` the general wording is shown instead (period_of; one rule for every surface).
- removes_protection: the rule takes a protection away (e.g. a state ban on rent control); shown without a green status.
"""

HEADLINES: dict[str, dict] = {
    "CA-RENT-01": {
        "en": "Up to 5% plus inflation, max 10%",
        "es": "Hasta 5% más inflación, máx. 10%",
        "short_en": "5% + CPI, max 10%/yr",
        "short_es": "5% + IPC, máx. 10%/año",
        "priority": 1,
        # where the building is not known (a place view, the Ask chooser): the exemptions (D024: CO within 15 years,
        # some single-family homes and condos, owner-occupied duplexes, deed-restricted housing) may apply
        "unknown_en": "Up to 5% + inflation, max 10% (most older rentals)",
        "unknown_es": "Hasta 5% + inflación, máx. 10% (la mayoría de alquileres antiguos)",
    },
    "CA-EVIC-01": {
        "en": "Just cause needed after 12 months",
        "es": "Se necesita causa justa tras 12 meses",
        "short_en": "Just cause after 12 months",
        "short_es": "Causa justa tras 12 meses",
        "priority": 1,
    },
    "CA-DEP-01": {
        "en": "Max 1 month's rent",
        "es": "Máximo 1 mes de renta",
        "short_en": "Max 1 month's rent",
        "short_es": "Máx. 1 mes de alquiler",
        "priority": 1,
    },
    "CA-FEE-01": {
        "en": "Fee capped; adjusted yearly for inflation",
        "es": "Cargo con tope; se ajusta cada año",
        # D005: "The maximum tenant screening fee for 2026 is $68.96" (the $30 of 1998, CPI-adjusted, D026)
        "short_en": "Max ~$69 per applicant (2026)",
        "short_es": "Máx. ~$69 por solicitante (2026)",
        "priority": 1,
        "short_until": "2026-12-31",
        "short_after_en": "Max $30 + CPI since 1998",
        "short_after_es": "Máx. $30 + IPC desde 1998",
    },
    "CA-SCR-01": {
        "en": "Vouchers and income source protected",
        "es": "Vales y fuente de ingresos protegidos",
        "short_en": "Vouchers protected",
        "short_es": "Vales protegidos",
        "priority": 1,
    },
    "CA-SCR-02": {
        "en": "No blanket criminal-record bans",
        "es": "Sin rechazos generales por antecedentes",
        "short_en": "Criminal-history limits",
        "short_es": "Límites a antecedentes penales",
        "priority": 1.5,
    },
    "CA-ALG-01": {
        # § 16729(a)/(b): only as part of a conspiracy to restrain trade, or while coercing adoption
        "en": "Pricing algorithms banned in price-fixing deals",
        "es": "Prohibidos los algoritmos de precios en acuerdos colusorios",
        "short_en": "Collusive pricing banned",
        "short_es": "Precios colusorios prohibidos",
        "priority": 1.8,
    },
    "NJ-EVIC-01": {
        "en": "No retaliatory evictions",
        "es": "Sin desalojos por represalia",
        "short_en": "No retaliation",
        "short_es": "Sin represalias",
        "priority": 2,
    },
    "NJ-EVIC-02": {
        # D067: "Foreclosure alone is not grounds for eviction"; 90 days only for a buyer who wants to occupy it
        "en": "Foreclosure alone can't end your tenancy",
        "es": "Una ejecución no basta para desalojarlo",
        "short_en": "Foreclosure: 90 days' notice to move in",
        "short_es": "Ejecución: 90 días de aviso para ocupar",
        "priority": 2,
    },
    "NJ-EVIC-03": {
        "en": "Good cause needed to evict",
        "es": "Se necesita causa justificada para desalojar",
        "short_en": "Just cause required",
        "short_es": "Se exige causa justa",
        "priority": 1,
    },
    "NJ-DEP-01": {
        "en": "Max 1.5 months' rent",
        "es": "Máximo 1,5 meses de renta",
        "short_en": "Max 1.5 months' rent",
        "short_es": "Máx. 1.5 meses de alquiler",
        "priority": 1,
    },
    "NJ-FEE-01": {
        # P.L.2025, c.405 (approved Jan 20, 2026): $50 flat; CPI adjustment from Jan 1 of the year after enactment
        "en": "Up to $50 per application",
        "es": "Hasta $50 por solicitud",
        "short_en": "Max $50 per application",
        "short_es": "Máx. $50 por solicitud",
        "priority": 1,
        "short_until": "2026-12-31",
        "short_after_en": "Max $50 + CPI per application",
        "short_after_es": "Máx. $50 + IPC por solicitud",
        "until": "2026-12-31",
        "after_en": "$50 cap, adjusted yearly for inflation",
        "after_es": "Tope de $50, ajustado cada año por inflación",
    },
    "NJ-SCR-01": {
        "en": "Vouchers and income source protected",
        "es": "Vales y fuente de ingresos protegidos",
        "short_en": "Vouchers protected",
        "short_es": "Vales protegidos",
        "priority": 1,
    },
    "NJ-SCR-02": {
        "en": "No record questions before an offer",
        "es": "Sin preguntar antecedentes antes de la oferta",
        "short_en": "Criminal-history limits",
        "short_es": "Límites a antecedentes penales",
        "priority": 1.5,
    },
    "NJ-ALG-01": {
        "en": "Rent software using rivals' private data banned",
        "es": "Prohibido el software de rentas con datos privados de rivales",
        "short_en": "Rival-data rent software banned",
        "short_es": "Software con datos de rivales prohibido",
        "priority": 1,
    },
    "MA-RENT-01": {
        "en": "Massachusetts bans local rent control",
        "es": "Massachusetts prohíbe el control local de rentas",
        "short_en": "No cap (rent control banned)",
        "short_es": "Sin tope (control prohibido)",
        "priority": 1,
        "removes_protection": True,
    },
    "MA-RENT-P1": {
        "en": "Proposed cap: lesser of CPI or 5%",
        "es": "Tope propuesto: IPC o 5%, el menor",
    },
    "MA-EVIC-01": {
        "en": "14 days' notice for nonpayment",
        "es": "14 días de aviso por falta de pago",
        "short_en": "14 days' notice for unpaid rent",
        "short_es": "14 días de aviso por impago",
        "priority": 2,
    },
    "MA-EVIC-02": {
        # § 12 governs estates at will only (no lease); a fixed-term lease runs to its end
        "en": "No lease: one rent period's notice (30+ days)",
        "es": "Sin contrato: un período de renta de aviso",
        "short_en": "No just cause; 30+ days (no lease)",
        "short_es": "Sin causa justa; 30+ días (sin contrato)",
        "priority": 1,
    },
    "MA-EVIC-03": {
        "en": "No retaliatory evictions",
        "es": "Sin desalojos por represalia",
        "short_en": "No retaliation",
        "short_es": "Sin represalias",
        "priority": 2,
    },
    "MA-EVIC-04": {
        "en": "State form required with nonpayment notice",
        "es": "Formulario estatal con el aviso por impago",
        "short_en": "State form with the notice",
        "short_es": "Formulario estatal con el aviso",
        "priority": 2,
    },
    "MA-DEP-01": {
        "en": "Max 1 month's rent",
        "es": "Máximo 1 mes de renta",
        "short_en": "Max 1 month's rent",
        "short_es": "Máx. 1 mes de alquiler",
        "priority": 1,
    },
    "MA-FEE-01": {
        "en": "Broker fee paid by whoever hired them",
        "es": "La comisión la paga quien contrató al corredor",
        "short_en": "Broker fee paid by who hired",
        "short_es": "Comisión a cargo de quien contrató",
        "priority": 2,
    },
    "MA-FEE-02": {
        "en": "Only first, last, deposit and lock fees",
        "es": "Solo primer y último mes, depósito y llave",
        "short_en": "No application fee",
        "short_es": "Sin cargo de solicitud",
        "priority": 1,
    },
    "MA-SCR-01": {
        "en": "Housing assistance and vouchers protected",
        "es": "Ayuda de vivienda y vales protegidos",
        "short_en": "Vouchers protected",
        "short_es": "Vales protegidos",
        "priority": 1,
    },
    "MA-ALG-P1": {
        "en": "Bill to ban algorithmic rent fixing",
        "es": "Proyecto para prohibir fijar rentas con algoritmos",
    },
    "MA-ALG-P2": {
        "en": "Bill to ban algorithmic rent setting",
        "es": "Proyecto para prohibir fijar rentas con algoritmos",
    },
    "LA-RENT-01": {
        "en": "Up to 3% a year until Jun 2026",
        "es": "Máx. 3% al año hasta jun 2026",
        "short_en": "Yearly % set by the city",
        "short_es": "% anual fijado por la ciudad",
        "priority": 1,
        "until": "2026-06-30",
        "after_en": "Yearly increase set by the city",
        "after_es": "Aumento anual fijado por la ciudad",
    },
    "LA-EVIC-01": {
        "en": "Only for listed reasons",
        "es": "Solo por las causas de la lista",
        "short_en": "Just cause required",
        "short_es": "Se exige causa justa",
        "priority": 1,
    },
    "LA-EVIC-02": {
        "en": "Just cause needed to evict",
        "es": "Se necesita causa justa para desalojar",
        "short_en": "Just cause required",
        "short_es": "Se exige causa justa",
        "priority": 1,
    },
    "LA-EVIC-03": {
        # D043 Chart B: "Only for Low, Very Low and Extremely Low Income Households", July 1, 2026 - June 30, 2027
        "en": "Lower-income, demolition: $87,450–$115,480",
        "es": "Bajos ingresos, demolición: $87,450–$115,480",
        "short_en": "Relocation pay on demolition",
        "short_es": "Pago de reubicación por demolición",
        "priority": 2,
        "from": "2026-07-01",
        "until": "2027-06-30",
        "after_en": "Lower-income, demolition: relocation pay",
        "after_es": "Bajos ingresos, demolición: pago de reubicación",
    },
    "LA-EVIC-04": {
        "en": "$11,000–$27,400 relocation for no-fault evictions",
        "es": "$11,000–$27,400 de reubicación sin culpa",
        "short_en": "Relocation pay for no-fault",
        "short_es": "Pago de reubicación sin culpa",
        "priority": 2,
        "from": "2026-07-01",
        "until": "2027-06-30",
        "after_en": "Relocation pay for no-fault evictions",
        "after_es": "Pago de reubicación en desalojos sin culpa",
    },
    "LA-DEP-01": {
        "en": "Deposit earns 4.32% interest in 2025",
        "es": "El depósito genera 4.32% en 2025",
        "short_en": "Earns interest",
        "short_es": "Genera intereses",
        "priority": 1.5,
        "until": "2025-12-31",
        "after_en": "Deposit earns interest set yearly",
        "after_es": "El depósito genera un interés anual",
    },
    "SF-RENT-01": {
        "en": "Up to 1.6% until Feb 2027",
        "es": "Máx. 1.6% hasta feb 2027",
        "short_en": "1.6%/yr",
        "short_es": "1.6%/año",
        "priority": 1,
        "short_from": "2026-03-01",
        "short_until": "2027-02-28",
        "short_after_en": "Yearly % set by the city",
        "short_after_es": "% anual fijado por la ciudad",
        "from": "2026-03-01",
        "until": "2027-02-28",
        "after_en": "Yearly increase set by the city",
        "after_es": "Aumento anual fijado por la ciudad",
    },
    "SF-EVIC-01": {
        "en": "Only for 17 listed reasons",
        "es": "Solo por 17 causas de la lista",
        "short_en": "Just cause required",
        "short_es": "Se exige causa justa",
        "priority": 1,
    },
    "SF-EVIC-02": {
        "en": "$8,245 per tenant for no-fault evictions",
        "es": "$8,245 por inquilino en desalojos sin culpa",
        "short_en": "Relocation pay for no-fault",
        "short_es": "Pago de reubicación sin culpa",
        "priority": 2,
        "from": "2026-03-01",
        "until": "2027-02-28",
        "after_en": "Relocation pay for no-fault evictions",
        "after_es": "Pago de reubicación en desalojos sin culpa",
    },
    "SF-DEP-01": {
        "en": "Deposit earns 4.2% until Feb 2027",
        "es": "El depósito genera 4.2% hasta feb 2027",
        "short_en": "4.2% interest",
        "short_es": "4.2% de interés",
        "priority": 1.5,
        "short_from": "2026-03-01",
        "short_until": "2027-02-28",
        "short_after_en": "Earns interest",
        "short_after_es": "Genera intereses",
        "from": "2026-03-01",
        "until": "2027-02-28",
        "after_en": "Deposit earns interest set yearly",
        "after_es": "El depósito genera un interés anual",
    },
    "SF-SCR-01": {
        "en": "Records limited in affordable housing",
        "es": "Antecedentes limitados en vivienda asequible",
        "short_en": "Fair chance in affordable housing",
        "short_es": "Oportunidad justa en vivienda asequible",
        "priority": 2,
    },
    "SF-ALG-01": {
        "en": "Rent software using rivals' private data banned",
        "es": "Prohibido el software de rentas con datos privados de rivales",
        "short_en": "Rival-data rent software banned",
        "short_es": "Software con datos de rivales prohibido",
        "priority": 1,
    },
    "SD-EVIC-01": {
        "en": "Just cause needed; 2 months' relocation",
        "es": "Causa justa; 2 meses de reubicación",
        "short_en": "Just cause required",
        "short_es": "Se exige causa justa",
        "priority": 1,
    },
    "SD-SCR-01": {
        "en": "Vouchers and income source protected",
        "es": "Vales y fuente de ingresos protegidos",
        "short_en": "Vouchers protected",
        "short_es": "Vales protegidos",
        "priority": 1,
    },
    "SD-ALG-01": {
        "en": "Rent software using rivals' private data banned",
        "es": "Prohibido el software de rentas con datos privados de rivales",
        "short_en": "Rival-data rent software banned",
        "short_es": "Software con datos de rivales prohibido",
        "priority": 1,
    },
    "BER-RENT-01": {
        "en": "Up to 1.0% in 2026",
        "es": "Máx. 1.0% en 2026",
        "short_en": "1.0%/yr",
        "short_es": "1.0%/año",
        "priority": 1,
        "short_from": "2026-01-01",
        "short_until": "2026-12-31",
        "short_after_en": "65% of CPI, max 5%/yr",
        "short_after_es": "65% del IPC, máx. 5%/año",
        "from": "2026-01-01",
        "until": "2026-12-31",
        # D006: the 5% cap "does not prevent a landlord who has 'banked' (unused) AGAs" from going higher
        "after_en": "Up to 65% of inflation, max 5% (plus banked raises)",
        "after_es": "Hasta 65% de la inflación, máx. 5% (más aumentos acumulados)",
    },
    "BER-EVIC-01": {
        "en": "Good cause needed to evict",
        "es": "Se necesita causa justificada para desalojar",
        "short_en": "Just cause required",
        "short_es": "Se exige causa justa",
        "priority": 1,
    },
    "BER-DEP-01": {
        "en": "Deposit earns yearly interest",
        "es": "El depósito genera interés anual",
        "short_en": "Earns interest",
        "short_es": "Genera intereses",
        "priority": 1.5,
    },
    "BER-FEE-01": {
        "en": "Up to $68.96 per applicant in 2026",
        "es": "Hasta $68.96 por solicitante en 2026",
        "short_en": "No non-refundable renewal fees",
        "short_es": "Sin cargos no reembolsables por renovar",
        "priority": 1.5,
        "until": "2026-12-31",
        "after_en": "Fee capped; disclosure required",
        "after_es": "Cargo con tope; aviso obligatorio",
    },
    "BER-SCR-01": {
        "en": "No criminal-record questions",
        "es": "Sin preguntas sobre antecedentes penales",
        "short_en": "No criminal-history checks",
        "short_es": "Sin revisar antecedentes penales",
        "priority": 1.2,
    },
    "BER-ALG-01": {
        "en": "Rent software using rivals' private data banned",
        "es": "Prohibido el software de rentas con datos privados de rivales",
        "short_en": "Rival-data rent software banned",
        "short_es": "Software con datos de rivales prohibido",
        "priority": 1,
    },
    "SA-RENT-01": {
        # D084: 2.87% "for the period of September 1, 2026 through August 31, 2027"
        "en": "Up to 2.87% until Aug 2027",
        "es": "Máx. 2.87% hasta ago 2027",
        "short_en": "Max 3%/yr",
        "short_es": "Máx. 3%/año",
        "priority": 1,
        "from": "2026-09-01",
        "until": "2027-08-31",
        "after_en": "Up to 3% a year by city formula",
        "after_es": "Máx. 3% al año según fórmula municipal",
    },
    "SA-EVIC-01": {
        "en": "Just cause needed after 30 days",
        "es": "Se necesita causa justa tras 30 días",
        "short_en": "Just cause after 30 days",
        "short_es": "Causa justa tras 30 días",
        "priority": 1,
    },
    "SA-ALG-01": {
        "en": "Rent software using rivals' private data banned",
        "es": "Prohibido el software de rentas con datos privados de rivales",
        "short_en": "Rival-data rent software banned",
        "short_es": "Software con datos de rivales prohibido",
        "priority": 1,
    },
    "JC-RENT-01": {
        "en": "Rent control for buildings with 5+ units",
        "es": "Control de renta en edificios de 5+ unidades",
        "short_en": "City rent control",
        "short_es": "Control de alquiler municipal",
        "priority": 1,
    },
    "JC-ALG-01": {
        "en": "Rent-coordination software banned",
        "es": "Prohibido el software que coordina rentas",
        "short_en": "Rent-coordination software banned",
        "short_es": "Software de coordinación prohibido",
        "priority": 1,
    },
    "HOB-RENT-01": {
        "en": "Rent control limits yearly increases",
        "es": "El control de renta limita los aumentos anuales",
        "short_en": "City rent control",
        "short_es": "Control de alquiler municipal",
        "priority": 1,
    },
    "HOB-ALG-01": {
        "en": "Rent-coordination software banned",
        "es": "Prohibido el software que coordina rentas",
        "short_en": "Rent-coordination software banned",
        "short_es": "Software de coordinación prohibido",
        "priority": 1,
    },
    "NWK-RENT-01": {
        "en": "Local rent control, figure not verified",
        "es": "Control de renta local, cifra sin verificar",
        "short_en": "City rent control",
        "short_es": "Control de alquiler municipal",
        "priority": 1,
    },
    "BOS-RENT-P1": {
        "en": "Proposed rent stabilization, not enacted",
        "es": "Estabilización de rentas propuesta, no aprobada",
    },
    "BOS-EVIC-01": {
        "en": "Tenant-rights notice required before eviction",
        "es": "Aviso de derechos obligatorio antes del desalojo",
        "short_en": "Rights notice required",
        "short_es": "Aviso de derechos obligatorio",
        "priority": 2,
    },
    "BOS-SCR-01": {
        "en": "Vouchers and rental assistance protected",
        "es": "Vales y ayudas de alquiler protegidos",
        "short_en": "Vouchers protected",
        "short_es": "Vales protegidos",
        "priority": 1,
    },
    "BOS-SCR-02": {
        # D010: applies to providers with DND funding/land or BPDA IDP income-restricted units
        "en": "City-funded housing: no old convictions or credit scores",
        "es": "Vivienda con fondos municipales: sin condenas antiguas ni crédito",
        "short_en": "No credit scores in city-funded housing",
        "short_es": "Sin puntaje de crédito en vivienda municipal",
        "priority": 2,
    },
    "CAM-EVIC-01": {
        "en": "Tenant-rights guide required",
        "es": "Guía de derechos del inquilino obligatoria",
        "short_en": "Rights notice required",
        "short_es": "Aviso de derechos obligatorio",
        "priority": 2,
    },
    "CAM-SCR-01": {
        "en": "Vouchers and income source protected",
        "es": "Vales y fuente de ingresos protegidos",
        "short_en": "Vouchers protected",
        "short_es": "Vales protegidos",
        "priority": 1,
    },
}


# ------------------------------------------------------------------ figure periods (one rule for every surface) --
def period_of(d: dict | None, as_of: str | None, pre: str = "") -> str:
    """'in', 'before' or 'after' the figure period of a table entry (keys from / until, or short_from / short_until
    with pre="short_"); no date or no period: 'in'. Address page, Compare, Changes, Listen and Check all use this."""
    if not d or not as_of:
        return "in"
    a, u = d.get(pre + "from"), d.get(pre + "until")
    if a and str(as_of)[:10] < a:
        return "before"
    if u and str(as_of)[:10] > u:
        return "after"
    return "in"


def fmt_period(start: str | None, end: str | None, lang: str = "en") -> str:
    """A figure's period for running text: 'Jul 2026–Jun 2027', 'until Feb 2027', 'from Mar 2026' (es: 'jul 2026–jun
    2027', 'hasta feb 2027', 'desde mar 2026')."""
    es = lang == "es"
    a, u = (
        fmt_date(str(start)[:7], lang) if start else "",
        fmt_date(str(end)[:7], lang) if end else "",
    )
    if a and u:
        return f"{a}–{u}"
    if u:
        return ("hasta " if es else "until ") + u
    return (("desde " if es else "from ") + a) if a else ""


def _fill(text: str | None, d: dict, lang: str) -> str | None:
    """Put the entry's period into a '{period}' placeholder (the dates come from the entry's own from / until)."""
    if not text or "{period}" not in text:
        return text
    return text.replace("{period}", fmt_period(d.get("from"), d.get("until"), lang))


def headline(rule_id: str, lang: str = "en", as_of: str | None = None) -> str | None:
    """The row answer for a rule on as_of (general wording outside the figure's period)."""
    d = HEADLINES.get(rule_id)
    if not d:
        return None
    if period_of(d, as_of) != "in" and (d.get("after_en") or d.get(f"after_{lang}")):
        return d.get(f"after_{lang}") or d.get("after_en")
    return d.get(lang) or d.get("en")


def short(rule_id: str, lang: str = "en", as_of: str | None = None) -> str | None:
    """The compact Compare cell text for a rule on as_of."""
    d = HEADLINES.get(rule_id)
    if not d or "short_en" not in d:
        return None
    if period_of(d, as_of, "short_") != "in" and d.get("short_after_en"):
        return d.get(f"short_after_{lang}") or d.get("short_after_en")
    return d.get(f"short_{lang}") or d.get("short_en")


def view(rule_id: str, lang: str = "en") -> dict:
    """Fields for the rule view: both wordings, so a client can pick by its own as-of date."""
    d = HEADLINES.get(rule_id) or {}
    return {
        "headline_display": headline(rule_id, lang),
        "headline_from": d.get("from"),
        "headline_until": d.get("until"),
        "headline_after": (d.get(f"after_{lang}") or d.get("after_en"))
        if d.get("until") or d.get("from")
        else None,
        "headline_short": short(rule_id, lang),
        "headline_short_from": d.get("short_from"),
        "headline_short_until": d.get("short_until"),
        "headline_short_after": (d.get(f"short_after_{lang}") or d.get("short_after_en"))
        if d.get("short_until") or d.get("short_from")
        else None,
        "headline_priority": d.get("priority"),
        "removes_protection": bool(d.get("removes_protection")),
        **plain(rule_id, lang),
    }


# Plain answers for the address page (persona test "David", 2026-10-04): the reader's own question answered in 8 words
# or fewer (answer), and one 5th-grade "why" line (why). Static, deterministic; the headline above stays the fallback.
# from / until: the figure belongs to a period (a '{period}' placeholder is filled from these dates); outside it the
# entry's "general" wording is shown, or, without one, the headline (and its general wording).
PLAIN: dict[str, dict] = {
    "CA-RENT-01": {
        "en": (
            "Yes, but max 5% plus inflation (never over 10%).",
            # § 1947.12(g)(3)(B)(ii): increases from August 1 use the April-to-April CPI change
            "The cap follows local inflation (April to April) and resets each August 1.",
        ),
        "es": (
            "Sí, pero máximo 5% más la inflación (nunca más de 10%).",
            "El tope sigue la inflación local (de abril a abril) y se renueva cada 1 de agosto.",
        ),
        "unknown": {
            "en": (
                "For most older rentals, max 5% plus inflation (never over 10%).",
                "The cap follows local inflation (April to April) and resets each August 1.",
            ),
            "es": (
                "En la mayoría de alquileres antiguos, máximo 5% más la inflación (nunca más de 10%).",
                "El tope sigue la inflación local (de abril a abril) y se renueva cada 1 de agosto.",
            ),
        },
    },
    "SF-RENT-01": {
        # D083: "March 1, 2026 – February 28, 2027 1.6%" (1.4% the year before)
        "from": "2026-03-01",
        "until": "2027-02-28",
        "en": (
            "Yes, but only 1.6% until Feb 2027.",
            "San Francisco sets one small raise per year.",
        ),
        "es": (
            "Sí, pero solo 1.6% hasta feb 2027.",
            "San Francisco fija un aumento pequeño por año.",
        ),
        "general": {
            "en": (
                "Yes, once a year, by the Rent Board's %.",
                "San Francisco sets one small raise per year.",
            ),
            "es": (
                "Sí, una vez al año, según el % de la Junta de Rentas.",
                "San Francisco fija un aumento pequeño por año.",
            ),
        },
    },
    "BER-RENT-01": {
        # D008: 1.0% "no earlier than January 1, 2026"; D006: max 5%, but banked (unused) AGAs may be added
        "from": "2026-01-01",
        "until": "2026-12-31",
        "en": (
            "Yes, but only 1.0% in 2026.",
            "Berkeley sets one yearly raise, max 5% (unused past raises can be added).",
        ),
        "es": (
            "Sí, pero solo 1.0% en 2026.",
            "Berkeley fija un aumento anual, máx. 5% (se pueden sumar aumentos no usados).",
        ),
        "general": {
            "en": (
                "Yes, but yearly raises are capped at 5% (Measure BB).",
                "Berkeley sets one yearly raise, max 5% (unused past raises can be added).",
            ),
            "es": (
                "Sí, pero los aumentos anuales tienen un tope de 5% (Medida BB).",
                "Berkeley fija un aumento anual, máx. 5% (se pueden sumar aumentos no usados).",
            ),
        },
    },
    "SA-RENT-01": {
        # D084: 2.87% only "for the period of September 1, 2026 through August 31, 2027"; D085: the formula
        "from": "2026-09-01",
        "until": "2027-08-31",
        "general": {
            "en": (
                "Yes, max 3% a year (or 80% of inflation if lower).",
                "The city caps raises at 3% or less each year.",
            ),
            "es": (
                "Sí, máx. 3% al año (u 80% de la inflación si es menor).",
                "La ciudad limita los aumentos a 3% o menos al año.",
            ),
        },
        "en": (
            "Yes, but only 2.87% until Aug 2027.",
            "The city caps raises at 3% or less each year.",
        ),
        "es": (
            "Sí, pero solo 2.87% hasta ago 2027.",
            "La ciudad limita los aumentos a 3% o menos al año.",
        ),
    },
    "LA-RENT-01": {
        "en": (
            "Yes, once a year, by a % the city sets each year.",
            "Los Angeles sets the yearly % for older buildings.",
        ),
        "es": (
            "Sí, una vez al año, según un % que fija la ciudad cada año.",
            "Los Ángeles fija el % anual para edificios antiguos.",
        ),
    },
    "JC-RENT-01": {
        "en": (
            "Yes, but city rent control limits it.",
            "Ask the city's rent office for this year's number.",
        ),
        "es": (
            "Sí, pero el control de rentas lo limita.",
            "Pida el número de este año a la oficina de rentas.",
        ),
    },
    "HOB-RENT-01": {
        "en": (
            "Yes, but city rent control limits it.",
            "Ask the city's rent office for this year's number.",
        ),
        "es": (
            "Sí, pero el control de rentas lo limita.",
            "Pida el número de este año a la oficina de rentas.",
        ),
    },
    "MA-RENT-01": {
        "en": (
            # D048 c.40P § 4 (no rent control); D053 c.186 § 18: a raise within 6 months of a complaint is
            # presumed a reprisal
            "Yes. Massachusetts has no rent cap.",
            "Cities can't cap rent. A raise within 6 months of a complaint is presumed payback.",
        ),
        "es": (
            "Sí. Massachusetts no tiene tope de renta.",
            "Las ciudades no pueden limitar la renta. Un aumento dentro de 6 meses de una queja se presume"
            " represalia.",
        ),
    },
    "SD-EVIC-01": {
        "en": (
            "Only for a good reason.",
            "If it's not your fault, they pay you 2 months' rent (3 if 62+ or disabled).",
        ),
        "es": (
            "Solo con una razón válida.",
            "Si no es su culpa, le pagan 2 meses de renta (3 si tiene 62+ o discapacidad).",
        ),
    },
    "CA-EVIC-01": {
        "en": (
            "After a year, only for a good reason.",
            # § 1946.2(d): one month's rent as relocation, or a written waiver of the final month's rent
            "If it's not your fault, they owe you 1 month's rent or must waive your last month.",
        ),
        "es": (
            "Después de un año, solo con razón válida.",
            "Si no es su culpa, le deben 1 mes de renta o perdonarle el último mes.",
        ),
    },
    "LA-EVIC-01": {
        # D043 Chart A (RSO/JCO, July 1, 2026 - June 30, 2027): $11,000-$27,400; lower for Mom & Pop owner move-ins
        # and one month's rent for some single-family homes, hence "most tenants"
        "from": "2026-07-01",
        "until": "2027-06-30",
        "en": (
            "Only for a good reason.",
            "If it's not your fault, most tenants get $11,000–$27,400 to move ({period}).",
        ),
        "es": (
            "Solo con una razón válida.",
            "Si no es su culpa, la mayoría recibe $11,000–$27,400 para mudarse ({period}).",
        ),
        "general": {
            "en": (
                "Only for a good reason.",
                "If it's not your fault, they must pay you relocation money.",
            ),
            "es": (
                "Solo con una razón válida.",
                "Si no es su culpa, deben pagarle una ayuda de reubicación.",
            ),
        },
    },
    "LA-EVIC-02": {
        # D043 Chart A (RSO/JCO, July 1, 2026 - June 30, 2027): $11,000-$27,400; lower for Mom & Pop owner move-ins
        # and one month's rent for some single-family homes, hence "most tenants"
        "from": "2026-07-01",
        "until": "2027-06-30",
        "en": (
            "After 6 months, only for a good reason.",
            "If it's not your fault, most tenants get $11,000–$27,400 to move ({period}).",
        ),
        "es": (
            "Después de 6 meses, solo con una razón válida.",
            "Si no es su culpa, la mayoría recibe $11,000–$27,400 para mudarse ({period}).",
        ),
        "general": {
            "en": (
                "After 6 months, only for a good reason.",
                "If it's not your fault, they must pay you relocation money.",
            ),
            "es": (
                "Después de 6 meses, solo con una razón válida.",
                "Si no es su culpa, deben pagarle una ayuda de reubicación.",
            ),
        },
    },
    "SF-EVIC-01": {
        # D082: $8,245 per tenant for notices served 3/01/26 - 2/28/27, only for owner/relative move-in,
        # demolition/removal, temporary capital improvement work or substantial rehabilitation
        "from": "2026-03-01",
        "until": "2027-02-28",
        "en": (
            "Only for 17 listed reasons.",
            "For owner move-in or demolition, they pay $8,245 per tenant in relocation ({period}).",
        ),
        "es": (
            "Solo por 17 razones de la lista.",
            "Si el dueño se muda o demuele, pagan $8,245 por inquilino de reubicación ({period}).",
        ),
        "general": {
            "en": (
                "Only for 17 listed reasons.",
                "For owner move-in or demolition, they must pay relocation.",
            ),
            "es": (
                "Solo por 17 razones de la lista.",
                "Si el dueño se muda o demuele, deben pagar reubicación.",
            ),
        },
    },
    "BER-EVIC-01": {
        "en": (
            "Only for a good reason.",
            # D006: the debt must reach one month of the Fair Market Rent for a unit of equivalent size
            "They can't evict you for owing less than one month of the area's fair market rent.",
        ),
        "es": (
            "Solo con una razón válida.",
            "No lo pueden echar por deber menos de un mes de la renta justa de mercado de la zona.",
        ),
    },
    "SA-EVIC-01": {
        "en": (
            "After 30 days, only for a good reason.",
            # D085: 3 months of relocation assistance, or a waiver of the final 3 months' rent
            "If it's not your fault, they owe 3 months' relocation help or your last 3 months rent-free.",
        ),
        "es": (
            "Después de 30 días, solo con razón válida.",
            "Si no es su culpa, le deben 3 meses de ayuda de reubicación o los últimos 3 meses sin renta.",
        ),
    },
    "NJ-EVIC-03": {
        "en": (
            "Only for a good reason.",
            "New Jersey lists the reasons; the notice time depends on the reason.",
        ),
        "es": (
            "Solo con una razón válida.",
            "Nueva Jersey tiene una lista de razones; el aviso depende de la razón.",
        ),
    },
    "MA-EVIC-02": {
        # G.L. c. 186, § 12: three months, but for rent paid more often than every three months "the interval between
        # the days of payment or thirty days, whichever is longer" (monthly rent: one month, at least 30 days)
        # (estates at will only: without a lease); the 10-day cure only "for a tenant who has not received a
        # similar notice ... within the twelve months next preceding"
        "en": (
            "Without a lease, yes: one rent period's notice (30+ days).",
            "No reason needed. 3 months if rent is paid quarterly or less often. 14 days if rent is unpaid; if"
            " it's your first such notice in 12 months, paying within 10 days stops it.",
        ),
        "es": (
            "Sin contrato, sí: un período de renta de aviso (30+ días).",
            "No necesitan razón. 3 meses si paga cada trimestre o menos seguido. 14 días si no pagó; si es su"
            " primer aviso así en 12 meses, pagar en 10 días lo detiene.",
        ),
    },
    "CA-DEP-01": {
        # § 1950.5(c)(5)(A)-(B): a natural person (or all-natural-person LLC) with 2 rentals, 4 units at most;
        # never from a service member. At an address the unit count decides (small_landlord_possible).
        "en": (
            "Max 1 month's rent.",
            "An individual owner (2 rentals, 4 units at most) may ask for 2 months, but not from a service member.",
        ),
        "es": (
            "Máximo 1 mes de renta.",
            "Un dueño individual (máx. 2 propiedades y 4 unidades) puede pedir 2 meses, pero no a un militar en"
            " servicio.",
        ),
    },
    "NJ-DEP-01": {
        "en": (
            "Max 1.5 months' rent.",
            "They must return it within 30 days of move-out, with interest.",
        ),
        "es": (
            "Máximo 1.5 meses de renta.",
            "Deben devolverlo en 30 días tras mudarse, con intereses.",
        ),
    },
    "MA-DEP-01": {
        "en": (
            "Max 1 month's rent.",
            "It must sit in a separate bank account and come back within 30 days.",
        ),
        "es": ("Máximo 1 mes de renta.", "Debe estar en una cuenta aparte y volver en 30 días."),
    },
    "CA-FEE-01": {
        # D005: "The maximum tenant screening fee for 2026 is $68.96"
        "until": "2026-12-31",
        "en": (
            "About $69 per applicant in 2026, max.",
            "California's cap grows with inflation each year.",
        ),
        "es": (
            "Máximo unos $69 por solicitante en 2026.",
            "El tope de California sube con la inflación cada año.",
        ),
    },
    "BER-FEE-01": {
        # D005: "The maximum tenant screening fee for 2026 is $68.96"
        "until": "2026-12-31",
        "en": (
            "About $69 per applicant in 2026, max.",
            "California's cap grows with inflation each year.",
        ),
        "es": (
            "Máximo unos $69 por solicitante en 2026.",
            "El tope de California sube con la inflación cada año.",
        ),
    },
    "NJ-FEE-01": {
        # § 1d: the $50 is adjusted for CPI "beginning on January 1 of the year next following enactment" (2027),
        # and only when the CPI change is above zero; after 2026 the headline's general wording shows
        "until": "2026-12-31",
        "en": (
            "Max $50 per application.",
            "From 2027 the state adjusts the cap each year for inflation.",
        ),
        "es": (
            "Máximo $50 por solicitud.",
            "Desde 2027 el estado ajusta el tope cada año por la inflación.",
        ),
    },
    "MA-FEE-02": {
        "en": (
            "No application fee allowed.",
            "Only first month, last month, deposit and a lock fee.",
        ),
        "es": (
            "No pueden cobrar por aplicar.",
            "Solo primer mes, último mes, depósito y cerradura.",
        ),
    },
    "NJ-SCR-02": {
        "en": (
            "They can't ask about your record before an offer.",
            # D065 § 4b: 6 / 4 / 1 years by degree; murder, aggravated sexual assault, ... have no time limit
            "After an offer, most convictions count only for 1-6 years; a few serious crimes always can.",
        ),
        "es": (
            "No pueden preguntar por antecedentes antes de una oferta.",
            "Tras una oferta, la mayoría de las condenas solo cuentan de 1 a 6 años; algunos delitos graves siempre"
            " pueden contar.",
        ),
    },
    "CA-SCR-02": {
        "en": (
            "No blanket 'no records' rule.",
            "Arrests without a conviction and sealed records can't count.",
        ),
        "es": (
            "No pueden rechazar a todos con antecedentes.",
            "Arrestos sin condena y antecedentes sellados no cuentan.",
        ),
    },
    "BER-SCR-01": {
        "en": (
            "No questions about your record.",
            "Berkeley bans criminal-record checks for most rentals.",
        ),
        "es": (
            "No pueden preguntar por sus antecedentes.",
            "Berkeley prohíbe revisar antecedentes penales en la mayoría de los alquileres.",
        ),
    },
    "NJ-EVIC-01": {
        "en": (
            # D067: reprisal for exercising civil rights, a good-faith complaint to a governmental authority (after
            # written notice to the landlord), a tenant organization, or refusing retaliatory lease changes
            "They can't evict you for using your rights or reporting code problems.",
            "Punishing you for using your rights is against the law.",
        ),
        "es": (
            "No lo pueden echar por usar sus derechos o denunciar problemas del código.",
            "Castigarlo por usar sus derechos va contra la ley.",
        ),
    },
    "MA-EVIC-03": {
        "en": (
            "They can't evict you for complaining or asking for repairs.",
            # D053 § 18: a notice to end the tenancy (except for nonpayment) or a rent increase within six months
            "A notice to leave (not for unpaid rent) or a raise within 6 months of a complaint is presumed payback.",
        ),
        "es": (
            "No lo pueden echar por quejarse o pedir reparaciones.",
            "Un aviso de desalojo (no por impago) o un aumento dentro de 6 meses de una queja se presume represalia.",
        ),
    },
    "NJ-EVIC-02": {
        "en": (
            "A foreclosure alone can't end your lease.",
            # D067: a lease beyond the 90 days runs out first
            "A buyer who wants to live there must give 90 days' notice and wait for your lease to end.",
        ),
        "es": (
            "Una ejecución hipotecaria no termina su contrato.",
            "Un comprador que quiera vivir allí debe darle 90 días de aviso y esperar a que termine su contrato.",
        ),
    },
    "NJ-ALG-01": {
        # applies (on or after Jul 1, 2027); the not-yet and conflict wordings are in NOT_YET / CONFLICT_WHY below
        "en": (
            "Not with rivals' private data; banned statewide since Jul 1, 2027.",
            "Landlords can't use a rent-setting service that pools rivals' data.",
        ),
        "es": (
            "No con datos privados de la competencia; prohibido en el estado desde el 1 jul 2027.",
            "No pueden usar un servicio que fija rentas con datos de la competencia.",
        ),
    },
    # ---- reviewed copy for rules whose wording was generated (legal review 2026-10-04); generated copy stays the
    # fallback for every other rule
    "LA-EVIC-03": {
        # D043 Chart B: "(Only for Low, Very Low and Extremely Low Income Households) Effective July 1, 2026 through
        # June 30, 2027"; "The RPO only applies to Protected Units that will be demolished for the purpose of new
        # construction."
        "from": "2026-07-01",
        "until": "2027-06-30",
        "en": (
            "Lower-income and torn down: $87,450–$115,480.",
            "You may stay until 6 months before construction and have return rights.",
        ),
        "es": (
            "Bajos ingresos y demolición: $87,450–$115,480.",
            "Puede quedarse hasta 6 meses antes de la construcción y tiene derecho a volver.",
        ),
        "general": {
            "en": (
                "Lower-income and torn down: relocation pay.",
                "You may stay until 6 months before construction and have return rights.",
            ),
            "es": (
                "Bajos ingresos y demolición: pago de reubicación.",
                "Puede quedarse hasta 6 meses antes de la construcción y tiene derecho a volver.",
            ),
        },
    },
    "LA-EVIC-04": {
        # D043 Chart A footnote: some single-family homes owe one month's rent; Mom & Pop move-ins a reduced amount
        "from": "2026-07-01",
        "until": "2027-06-30",
        "en": (
            "If not your fault, usually $11,000–$27,400.",
            "In an eviction that isn't your fault, the landlord must make the payment available within 15 days.",
        ),
        "es": (
            "Si no es su culpa, por lo general $11,000–$27,400.",
            "En un desalojo que no es su culpa, el dueño debe tener el pago disponible en 15 días.",
        ),
        "general": {
            "en": (
                "If not your fault, they must pay relocation.",
                "In an eviction that isn't your fault, the landlord must make the payment available within 15 days.",
            ),
            "es": (
                "Si no es su culpa, deben pagar reubicación.",
                "En un desalojo que no es su culpa, el dueño debe tener el pago disponible en 15 días.",
            ),
        },
    },
    "SF-EVIC-02": {
        # D082, notices served 3/01/26 - 2/28/27: $8,245 per tenant, max $24,733 per unit, PLUS $5,497 for each
        # elderly (60+) or disabled tenant or household with minor children; only the four listed grounds
        "from": "2026-03-01",
        "until": "2027-02-28",
        "en": (
            "Owner move-in or demolition: $8,245 per tenant.",
            "Max $24,733 in relocation per unit, plus $5,497 for each tenant 60+ or disabled, or a household with children.",
        ),
        "es": (
            "Mudanza del dueño o demolición: $8,245 por inquilino.",
            "Máx. $24,733 de reubicación por unidad, más $5,497 por cada inquilino de 60+ o con discapacidad, o un"
            " hogar con menores.",
        ),
        "general": {
            "en": (
                "Owner move-in or demolition: relocation pay.",
                "The Rent Board sets the relocation amounts each year.",
            ),
            "es": (
                "Mudanza del dueño o demolición: pago de reubicación.",
                "La Junta de Rentas fija los montos de reubicación cada año.",
            ),
        },
    },
    "MA-EVIC-01": {
        # D050 § 11: "Upon the neglect or refusal to pay the rent due under a written lease, fourteen days' notice"
        "en": (
            "With a lease: 14 days' notice for unpaid rent.",
            "With a written lease, paying all rent due, with interest and costs, by the answer day stops the eviction.",
        ),
        "es": (
            "Con contrato: 14 días de aviso por renta impaga.",
            "Con contrato escrito, pagar toda la renta, con intereses y costos, antes del día de respuesta detiene"
            " el desalojo.",
        ),
    },
    "MA-EVIC-04": {
        # D058: courts accept a nonpayment case only with proof the form was delivered
        "en": (
            "A nonpayment notice must come with a state form.",
            "Courts won't accept a nonpayment case without proof the form was delivered.",
        ),
        "es": (
            "Un aviso por impago debe venir con un formulario estatal.",
            "Los tribunales no aceptan un caso por falta de pago sin prueba de que se entregó el formulario.",
        ),
    },
    "LA-DEP-01": {
        # D044 gives the 2025 rate only ("Calendar Year 2025 | 4.320%"); the why line carries no dated figure
        "en": (
            "Yes, landlords must pay you interest.",
            "The city sets the interest rate on your deposit each year.",
        ),
        "es": (
            "Sí, el arrendador debe pagarle intereses.",
            "La ciudad fija cada año la tasa de interés de su depósito.",
        ),
    },
    "MA-RENT-P1": {
        # D055 names no month for the ruling
        "en": (
            "Not law: the 5% cap proposal failed.",
            "The state's top court ruled it can't be on the November 2026 ballot.",
        ),
        "es": (
            "No es ley: la propuesta de límite de 5% fracasó.",
            "El tribunal supremo del estado decidió que no puede estar en la boleta de noviembre de 2026.",
        ),
    },
    "SMO-ALG-01": {
        # SM05: "$1,000 per offense or actual damages, whichever is greater, plus attorney fees"
        "en": (
            "Not if it uses competitor data.",
            "If a landlord uses software like this, you can sue for $1,000 per violation or your actual damages,"
            " whichever is more.",
        ),
        "es": (
            "No, si usa datos de la competencia.",
            "Si el arrendador usa este tipo de software, usted puede demandar por $1,000 por infracción o sus daños"
            " reales, lo que sea mayor.",
        ),
    },
}
_VOUCHER = {
    "en": ("No. Vouchers count as income.", "Turning you down for a voucher is illegal."),
    "es": ("No. Los vales cuentan como ingreso.", "Rechazarlo por un vale es ilegal."),
}
# city bans on software that uses rivals' nonpublic data (SF D081, SD D076, Berkeley D001, Santa Ana D002): software
# on public data stays legal
_ALG = {
    "en": (
        "Not with rivals' private data; that's banned.",
        "Landlords can't share private rent data through an app to set prices.",
    ),
    "es": (
        "No con datos privados de la competencia; eso está prohibido.",
        "No pueden compartir datos privados de rentas en un programa para fijar precios.",
    ),
}
# California's Cartwright Act (D022 § 16729): only as part of a conspiracy to restrain trade, or while coercing others
_ALG_CA = {
    "en": (
        "Not as part of price-fixing between landlords.",
        "Using a shared pricing tool to collude, or pushing others to use its prices, is illegal.",
    ),
    "es": (
        "No como parte de un acuerdo de precios entre dueños.",
        "Usar una herramienta de precios compartida para coludirse, o presionar a otros a usar sus precios, es"
        " ilegal.",
    ),
}
# Jersey City (D037) and Hoboken (D002): rent-coordination services and data-sharing platforms
_ALG_COORD = {
    "en": (
        "No. Software that coordinates rents is banned.",
        "Landlords can't use rent-coordination software or data-sharing platforms to set rents.",
    ),
    "es": (
        "No. Está prohibido el software que coordina rentas.",
        "No pueden usar software de coordinación de rentas ni plataformas de datos compartidos para fijarlas.",
    ),
}
_BILL = {
    "en": ("No law yet. A bill is being discussed.", "Nothing changes unless it passes."),
    "es": ("Aún no hay ley. Se discute un proyecto.", "Nada cambia si no se aprueba."),
}
for _r in ("CA-SCR-01", "NJ-SCR-01", "MA-SCR-01", "SD-SCR-01", "BOS-SCR-01", "CAM-SCR-01"):
    PLAIN[_r] = _VOUCHER
_ALG_RULES = (
    "CA-ALG-01",
    "SF-ALG-01",
    "SD-ALG-01",
    "BER-ALG-01",
    "SA-ALG-01",
    "JC-ALG-01",
    "HOB-ALG-01",
)
for _r in _ALG_RULES:
    PLAIN[_r] = (
        _ALG_CA if _r == "CA-ALG-01" else _ALG_COORD if _r in ("JC-ALG-01", "HOB-ALG-01") else _ALG
    )
for _r in ("MA-ALG-P1", "MA-ALG-P2"):
    PLAIN[_r] = _BILL


_NO_PLAIN = {
    "answer_display": None,
    "why_display": None,
    "plain_until": None,
    "plain_from": None,
    "answer_general": None,
    "why_general": None,
}


def plain(rule_id: str, lang: str = "en", as_of: str | None = None) -> dict:
    """answer / why for a rule (both None when it has none).

    With as_of: the wording for that date (the period's or the general one), already resolved (plain_from / _until
    None). Without: the period's wording plus plain_from / plain_until and the general wording (answer_general /
    why_general), so a client can pick by its own date (the Rules view)."""
    d = PLAIN.get(rule_id)
    if not d:
        return dict(_NO_PLAIN)
    g = (d.get("general") or {}).get(lang) or (d.get("general") or {}).get("en") or (None, None)
    a, w = d.get(lang) or d["en"]
    if as_of:
        if period_of(d, as_of) != "in":
            a, w = g
        return {**_NO_PLAIN, "answer_display": _fill(a, d, lang), "why_display": _fill(w, d, lang)}
    return {
        "answer_display": _fill(a, d, lang),
        "why_display": _fill(w, d, lang),
        "plain_until": d.get("until"),
        "plain_from": d.get("from"),
        "answer_general": _fill(g[0], d, lang),
        "why_general": _fill(g[1], d, lang),
    }


# ---------------------------------------------------------------- per address: the answer follows the result --
# The tables above word the answer for a rule that applies. At an address the evaluator may say the rule is not yet
# in effect, replaced, unknown, ...; the row must then not claim it applies ("No. ... is banned" next to "Starts Jan 1,
# 2026" was the T1 bug). for_item() returns the per-address wording for one result; the address builders
# (web.app.build_address, web.any_address.build_view) copy it into the item and its rule view.
_MON = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "es": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sept", "oct", "nov", "dic"],
}


def fmt_date(iso: str | None, lang: str = "en") -> str:
    """'2026-01-01' -> 'Jan 1, 2026' / '1 ene 2026' (the app's fmtDate); '2025-06' -> 'Jun 2025'."""
    s = str(iso or "")[:10]
    parts = s.split("-")
    if len(parts) < 2 or not all(p.isdigit() for p in parts):
        return s
    y, m = parts[0], _MON["es" if lang == "es" else "en"][int(parts[1]) - 1]
    if len(parts) == 2:
        return f"{m} {y}"
    d = int(parts[2])
    return f"{d} {m} {y}" if lang == "es" else f"{m} {d}, {y}"


# not yet in effect: the plain answer says so (rules without an entry get None: the app shows "Not yet. Starts ...");
# the why line stays the app's own "A new law starts on ..." wording
_NY_ALG = {"en": "Not yet: a ban starts {d}.", "es": "Todavía no: una prohibición empieza el {d}."}
NOT_YET: dict[str, dict] = {r: _NY_ALG for r in _ALG_RULES}
NOT_YET["NJ-ALG-01"] = {
    "en": "Not yet: a state ban starts {d}.",
    "es": "Todavía no: una prohibición estatal empieza el {d}.",
}
# the why line when this address carries a conflict flag for the rule (lookups conflict_flag)
CONFLICT_WHY: dict[str, dict] = {
    "NJ-ALG-01": {
        "en": "The state ban may replace the city ban here; a court may decide which one applies.",
        "es": "La prohibición estatal puede reemplazar a la de la ciudad; un tribunal puede decidir cuál aplica.",
    },
}
# deposit rules with a two-month exception for small landlords (<= 2 properties, <= 4 units in total): the line only
# where the building's own unit count allows it (the brief's 20-unit San Francisco example: it can't apply)
SMALL_LANDLORD_MAX_UNITS = {"CA-DEP-01": 4, "SMO-DEP-01": 4}
_SMALL_NO = {
    "en": "The 2-month small-landlord exception can't apply: this building has {n} units.",
    "es": "La excepción de 2 meses para dueños pequeños no aplica: este edificio tiene {n} unidades.",
}
_SMALL_NO_MIN = {
    "en": "The 2-month small-landlord exception can't apply: this building has {n} or more units.",
    "es": "La excepción de 2 meses para dueños pequeños no aplica: este edificio tiene {n} unidades o más.",
}
_SMALL_MAYBE = {
    # § 1950.5(c)(5)(A)(i): a natural person or an LLC of natural persons; (B): not from a service member
    "en": "An individual owner (2 rentals, 4 units at most) may ask for 2 months, but not from a service member.",
    "es": "Un dueño individual (máx. 2 propiedades y 4 unidades) puede pedir 2 meses, pero no a un militar en servicio.",
}


def small_landlord_possible(rule_id: str, units=None, units_min=None) -> bool | None:
    """Can the two-month small-landlord deposit exception apply at this building? The one test for the address page,
    Listen, Check and the letter.

    None: the rule has no such exception. False: the building's unit count (units), or its lower bound from the use
    code ("5 or more units": units_min), is above the 4 units the exception allows in total. True: it may apply (the
    count is unknown or small; the landlord's type and other rentals are not in the public data)."""
    cap = SMALL_LANDLORD_MAX_UNITS.get(rule_id)
    if not cap:
        return None
    n, lo = _int(units), _int(units_min)
    if n is not None:
        return n <= cap
    return not (lo is not None and lo > cap)


# before the version of an amended law that our data holds (navigator.evaluate.version_gap): the engine says unknown
# and the row says so, with the current version's start as "Starts <date>"; never the current figure
_GAP = {
    "en": (
        "We can't tell for this date: an older version applied that our sources don't include.",
        "We can't tell for this date: an older version applied. Our sources mention it, but our data has only"
        " the current one.",
        "The current version starts {d}. Pick that date or later to see it.",
        "Can't tell for this date (current version from {d})",
        "The rule's text for this date (an older version applied)",
    ),
    "es": (
        "No podemos saberlo para esta fecha: regía una versión anterior que nuestras fuentes no incluyen.",
        "No podemos saberlo para esta fecha: regía una versión anterior. Nuestras fuentes la mencionan, pero"
        " nuestros datos solo tienen la actual.",
        "La versión actual empieza el {d}. Elija esa fecha o una posterior para verla.",
        "No se puede saber para esta fecha (versión actual desde el {d})",
        "El texto de la regla para esta fecha (regía una versión anterior)",
    ),
}


def _int(v) -> int | None:
    try:
        return int(float(str(v).strip().rstrip("+")))
    except (TypeError, ValueError):
        return None


def for_item(
    rule_id: str,
    result: str,
    as_of: str,
    lang: str = "en",
    *,
    effective: str | None = None,
    units=None,
    units_min=None,
    conflict: bool = False,
    gap: dict | None = None,
    current_from: str | None = None,
) -> dict:
    """The per-address answer fields for one evaluator result.

    -> {"answer_display", "why_display", "plain_until", "headline"}: the plain answer and why line (None = the app's
    own wording for that result) and, for a rule not yet in effect, the dated row headline (else None: keep).
    effective: the rule's start (for "not yet" wordings); units / units_min: the building's unit count or its lower
    bound; conflict: the address-level conflict flag."""
    lang = "es" if lang == "es" else "en"
    p = plain(rule_id, lang, as_of)
    if gap:  # unknown: an older version applied on this date (gap = the engine's version_gap)
        g, d = _GAP[lang], fmt_date(gap.get("from"), lang)
        return {
            **_NO_PLAIN,
            "answer_display": g[1] if gap.get("in_sources") else g[0],
            "why_display": g[2].format(d=d),
            "headline": g[3].format(d=d),
        }
    if result == "not_yet_effective":
        hl = headline(rule_id, lang, as_of)
        d = fmt_date(effective, lang)
        ny = (NOT_YET.get(rule_id) or {}).get(lang)
        ans = ny.format(d=d) if ny and d else None
        if ans:
            hl = ans.rstrip(".")
        elif hl and d:
            hl = (f"Desde el {d}: " if lang == "es" else f"From {d}: ") + hl[:1].lower() + hl[1:]
        return {**_NO_PLAIN, "answer_display": ans, "headline": hl}
    if result in ("superseded", "pending", "failed"):
        # replaced here, or not law: the applies-wording would claim the rule governs this address
        return {**_NO_PLAIN, "headline": None}
    out = {**p, "headline": None}
    unk = (PLAIN.get(rule_id) or {}).get("unknown")
    if result == "unknown" and unk:
        # coverage not known (no building: a place view): the wording that keeps the exemptions in
        a, w = unk.get(lang) or unk["en"]
        out.update(answer_display=a, why_display=w)
        h = HEADLINES.get(rule_id) or {}
        out["headline"] = h.get(f"unknown_{lang}") or h.get("unknown_en")
    reviewed_period = bool((PLAIN.get(rule_id) or {}).get("from"))
    if current_from and as_of < str(current_from)[:10] and not reviewed_period:
        # the long-standing law applies, but the figure in the answer is the current version's (#158): no figure
        for k in ("answer_display", "why_display"):
            if any(ch.isdigit() for ch in out.get(k) or ""):
                out[k] = None
    if conflict and rule_id in CONFLICT_WHY and out.get("why_display"):
        out["why_display"] = CONFLICT_WHY[rule_id][lang]
    small = small_landlord_possible(rule_id, units, units_min)
    if small is not None and out.get("why_display"):
        n, lo = _int(units), _int(units_min)
        if small:
            out["why_display"] = _SMALL_MAYBE[lang]
        elif n is not None:
            out["why_display"] = _SMALL_NO[lang].format(n=n)
        else:
            out["why_display"] = _SMALL_NO_MIN[lang].format(n=lo)
    return out


def apply_item(item: dict, as_of: str, lang: str, *, units=None, units_min=None) -> dict:
    """Copy for_item() into an address item (its rule view is a per-item copy) and make the conflict flag the
    address-level one (lookups.json conflict_flag), not the rule-level flag."""
    r = item["rule"]
    item["rule"]["conflict_flag"] = bool(item.get("conflict_flag"))
    f = for_item(
        r["team_rule_id"],
        item["result"],
        as_of,
        lang,
        effective=r.get("effective_date_norm") or r.get("effective_date"),
        units=units,
        units_min=units_min,
        conflict=bool(item.get("conflict_flag")),
        gap=item.get("version_gap"),
        current_from=r.get("current_version_effective") if r.get("amends_existing_law") else None,
    )
    hl = f.pop("headline")
    r.update(f)
    if hl is not None:
        item["headline"] = hl
    small = small_landlord_possible(r["team_rule_id"], units, units_min)
    if small is not None:
        item["small_landlord_possible"] = small  # Listen and the letter read the same test
    if item.get("version_gap"):
        item["missing_fact"] = _GAP["es" if lang == "es" else "en"][4]
    cve = r.get("current_version_effective") if r.get("amends_existing_law") else None
    d = HEADLINES.get(r["team_rule_id"]) or {}
    if period_of(d, as_of, "short_") != "in" and d.get("short_after_en"):
        r["headline_short"] = d.get(f"short_after_{lang}") or d["short_after_en"]
    elif cve and as_of < str(cve)[:10] and d.get("short_after_en"):
        # before the current figure's period: the compact Compare text without the figure, like the headline (#158)
        r["headline_short"] = d.get(f"short_after_{lang}") or d["short_after_en"]
    return item


# ------------------------------------------------- generated copy for rules without an entry (navigator/plain.py) --
# The tables above are the reviewed copy and always win. A rule without an entry (a new jurisdiction from
# `navigator extend` or `ingest-new`) gets the generated, code-checked copy from output/plain_language.json and
# output/extension/*/plain_language.json; view() marks it plain_source "generated" (the app shows "auto-summary").
REVIEWED_HEADLINES = frozenset(HEADLINES)
REVIEWED_PLAIN = frozenset(PLAIN)
GENERATED: dict[str, dict] = {}


def load_generated(output_dir=None) -> int:
    """Fill HEADLINES / PLAIN gaps from the generated files; returns the number of rules filled."""
    import json
    from pathlib import Path

    out = Path(output_dir) if output_dir else Path(__file__).resolve().parent.parent / "output"
    n = 0
    for p in [out / "plain_language.json", *sorted(out.glob("extension/*/plain_language.json"))]:
        try:
            recs = json.loads(p.read_text(encoding="utf-8")).get("records", {})
        except (OSError, ValueError):
            continue
        for rid, rec in recs.items():
            if rec.get("source") != "generated" or rid in GENERATED:
                continue
            reviewed = {"headline": REVIEWED_HEADLINES, "plain": REVIEWED_PLAIN}
            fills = [k for k in rec.get("fills") or [] if rid not in reviewed.get(k, ())]
            if not fills:
                continue
            GENERATED[rid] = rec
            if "headline" in fills:
                HEADLINES[rid] = rec["headline"]
            if "plain" in fills:
                PLAIN[rid] = {
                    k: tuple(v) if isinstance(v, list) else v for k, v in rec["plain"].items()
                }
                # a reviewed headline's period also ends the generated answer (its figures may be dated)
                for k in ("from", "until"):
                    if not PLAIN[rid].get(k) and (HEADLINES.get(rid) or {}).get(k):
                        PLAIN[rid][k] = HEADLINES[rid][k]
            n += 1
    return n


load_generated()
_view_tables = view


def view(rule_id: str, lang: str = "en") -> dict:  # noqa: F811 - adds the copy's source to the table view
    v = _view_tables(rule_id, lang)
    gen = rule_id in GENERATED
    v["plain_source"] = (
        "generated" if gen else "reviewed" if rule_id in REVIEWED_HEADLINES else None
    )
    v["plain_needs_review"] = bool(gen and GENERATED[rule_id].get("needs_review"))
    return v
