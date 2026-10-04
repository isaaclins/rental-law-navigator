"""One-line, plain-language answers per rule: the single source for the address page rows, Compare and Listen.

Hand-written from each rule's key_value (outputs/rules.json stays untouched). Fields:
- en / es: the row answer, 8 words or fewer, the number first.
- short_en / short_es, priority: the compact cell text Compare uses; priority 1 leads, <= 1.5 may be appended,
  2 only when nothing else applies (Compare's rules, #48).
- until + after_en / after_es (and short_until + short_after_*): the figure belongs to a period; after `until` the
  general wording is shown instead.
- removes_protection: the rule takes a protection away (e.g. a state ban on rent control); shown without a green status.
"""

HEADLINES: dict[str, dict] = {
    "CA-RENT-01": {
        "en": "Up to 5% plus inflation, max 10%",
        "es": "Hasta 5% más inflación, máx. 10%",
        "short_en": "5% + CPI, max 10%/yr",
        "short_es": "5% + IPC, máx. 10%/año",
        "priority": 1,
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
        "short_en": "Max $30 + inflation per applicant",
        "short_es": "Máx. $30 + inflación por solicitante",
        "priority": 1,
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
        "en": "Shared pricing algorithms banned",
        "es": "Algoritmos de precios compartidos prohibidos",
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
        "en": "90 days' notice after a foreclosure",
        "es": "90 días de aviso tras una ejecución",
        "short_en": "90 days' notice after a sale",
        "short_es": "90 días de aviso tras una venta",
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
        "en": "Rent-setting algorithms banned",
        "es": "Algoritmos para fijar la renta prohibidos",
        "short_en": "Banned",
        "short_es": "Prohibido",
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
        "en": "One rent period's notice (30+ days)",
        "es": "Aviso de un período de renta (30+ días)",
        "short_en": "No just cause; 30+ days' notice",
        "short_es": "Sin causa justa; 30+ días de aviso",
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
        "en": "$87,450–$115,480 if demolished",
        "es": "$87,450–$115,480 si se demuele",
        "short_en": "Relocation pay on demolition",
        "short_es": "Pago de reubicación por demolición",
        "priority": 2,
    },
    "LA-EVIC-04": {
        "en": "$11,000–$27,400 relocation for no-fault evictions",
        "es": "$11,000–$27,400 de reubicación sin culpa",
        "short_en": "Relocation pay for no-fault",
        "short_es": "Pago de reubicación sin culpa",
        "priority": 2,
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
        "short_until": "2027-02-28",
        "short_after_en": "Yearly % set by the city",
        "short_after_es": "% anual fijado por la ciudad",
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
        "short_until": "2027-02-28",
        "short_after_en": "Earns interest",
        "short_after_es": "Genera intereses",
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
        "en": "Rent-setting algorithms banned",
        "es": "Algoritmos para fijar la renta prohibidos",
        "short_en": "Banned",
        "short_es": "Prohibido",
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
        "en": "Rent-setting algorithms banned",
        "es": "Algoritmos para fijar la renta prohibidos",
        "short_en": "Banned",
        "short_es": "Prohibido",
        "priority": 1,
    },
    "BER-RENT-01": {
        "en": "Up to 1.0% in 2026",
        "es": "Máx. 1.0% en 2026",
        "short_en": "1.0%/yr",
        "short_es": "1.0%/año",
        "priority": 1,
        "short_until": "2026-12-31",
        "short_after_en": "65% of CPI, max 5%/yr",
        "short_after_es": "65% del IPC, máx. 5%/año",
        "until": "2026-12-31",
        "after_en": "Up to 65% of inflation, max 5%",
        "after_es": "Hasta 65% de la inflación, máx. 5%",
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
        "short_en": "No renewal fees",
        "short_es": "Sin cargos por renovación",
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
        "en": "Rent-setting algorithms banned",
        "es": "Algoritmos para fijar la renta prohibidos",
        "short_en": "Banned",
        "short_es": "Prohibido",
        "priority": 1,
    },
    "SA-RENT-01": {
        "en": "Up to 2.87% until Aug 2027",
        "es": "Máx. 2.87% hasta ago 2027",
        "short_en": "Max 3%/yr",
        "short_es": "Máx. 3%/año",
        "priority": 1,
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
        "en": "Rent-setting algorithms banned",
        "es": "Algoritmos para fijar la renta prohibidos",
        "short_en": "Banned",
        "short_es": "Prohibido",
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
        "en": "Rent-setting algorithms banned",
        "es": "Algoritmos para fijar la renta prohibidos",
        "short_en": "Banned",
        "short_es": "Prohibido",
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
        "en": "Rent-setting algorithms banned",
        "es": "Algoritmos para fijar la renta prohibidos",
        "short_en": "Banned",
        "short_es": "Prohibido",
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
        "en": "No old convictions, no credit scores",
        "es": "Sin condenas antiguas ni puntaje de crédito",
        "short_en": "No credit scores",
        "short_es": "Sin puntaje de crédito",
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


def headline(rule_id: str, lang: str = "en", as_of: str | None = None) -> str | None:
    """The row answer for a rule on as_of (general wording once the figure's period has ended)."""
    d = HEADLINES.get(rule_id)
    if not d:
        return None
    if d.get("until") and as_of and as_of > d["until"]:
        return d.get(f"after_{lang}") or d.get("after_en")
    return d.get(lang) or d.get("en")


def short(rule_id: str, lang: str = "en", as_of: str | None = None) -> str | None:
    """The compact Compare cell text for a rule on as_of."""
    d = HEADLINES.get(rule_id)
    if not d or "short_en" not in d:
        return None
    if d.get("short_until") and as_of and as_of > d["short_until"]:
        return d.get(f"short_after_{lang}") or d.get("short_after_en")
    return d.get(f"short_{lang}") or d.get("short_en")


def view(rule_id: str, lang: str = "en") -> dict:
    """Fields for the rule view: both wordings, so a client can pick by its own as-of date."""
    d = HEADLINES.get(rule_id) or {}
    return {
        "headline_display": headline(rule_id, lang),
        "headline_until": d.get("until"),
        "headline_after": (d.get(f"after_{lang}") or d.get("after_en")) if d.get("until") else None,
        "headline_short": short(rule_id, lang),
        "headline_short_until": d.get("short_until"),
        "headline_short_after": (d.get(f"short_after_{lang}") or d.get("short_after_en"))
        if d.get("short_until")
        else None,
        "headline_priority": d.get("priority"),
        "removes_protection": bool(d.get("removes_protection")),
        **plain(rule_id, lang),
    }


# Plain answers for the address page (persona test "David", 2026-10-04): the reader's own question answered in 8 words
# or fewer (answer), and one 5th-grade "why" line (why). Static, deterministic; the headline above stays the fallback.
# until: the figure belongs to a period; after it the headline (and its general wording) is shown instead.
PLAIN: dict[str, dict] = {
    "CA-RENT-01": {
        "en": (
            "Yes, but max 5% plus inflation (never over 10%).",
            "The state sets the cap each August from local inflation.",
        ),
        "es": (
            "Sí, pero máximo 5% más la inflación (nunca más de 10%).",
            "El estado fija el tope cada agosto según la inflación local.",
        ),
    },
    "SF-RENT-01": {
        "until": "2027-02-28",
        "en": (
            "Yes, but only 1.6% until Feb 2027.",
            "San Francisco sets one small raise per year.",
        ),
        "es": (
            "Sí, pero solo 1.6% hasta feb 2027.",
            "San Francisco fija un aumento pequeño por año.",
        ),
    },
    "BER-RENT-01": {
        "until": "2026-12-31",
        "en": (
            "Yes, but only 1.0% in 2026.",
            "Berkeley sets the yearly raise; it can never pass 5%.",
        ),
        "es": ("Sí, pero solo 1.0% en 2026.", "Berkeley fija el aumento anual; nunca pasa de 5%."),
    },
    "SA-RENT-01": {
        "until": "2027-08-31",
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
            "Yes, once a year, by the city's %.",
            "Los Angeles sets the yearly % for older buildings.",
        ),
        "es": (
            "Sí, una vez al año, según el % de la ciudad.",
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
            "Yes, any amount. No cap in Massachusetts.",
            "The state doesn't allow cities to cap rent.",
        ),
        "es": (
            "Sí, cualquier monto. No hay tope en Massachusetts.",
            "El estado no permite que las ciudades limiten la renta.",
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
            "If it's not your fault, they owe you 1 month's rent.",
        ),
        "es": (
            "Después de un año, solo con razón válida.",
            "Si no es su culpa, le deben 1 mes de renta.",
        ),
    },
    "LA-EVIC-01": {
        "en": (
            "Only for a good reason.",
            "If it's not your fault, they pay $11,000–$27,400 to move you.",
        ),
        "es": (
            "Solo con una razón válida.",
            "Si no es su culpa, pagan $11,000–$27,400 por su mudanza.",
        ),
    },
    "LA-EVIC-02": {
        "en": (
            "Only for a good reason.",
            "If it's not your fault, they pay $11,000–$27,400 to move you.",
        ),
        "es": (
            "Solo con una razón válida.",
            "Si no es su culpa, pagan $11,000–$27,400 por su mudanza.",
        ),
    },
    "SF-EVIC-01": {
        "en": (
            "Only for 17 listed reasons.",
            "If it's not your fault, they pay $8,245 per person.",
        ),
        "es": ("Solo por 17 razones de la lista.", "Si no es su culpa, pagan $8,245 por persona."),
    },
    "BER-EVIC-01": {
        "en": (
            "Only for a good reason.",
            "They can't evict you for owing less than about one month's rent.",
        ),
        "es": (
            "Solo con una razón válida.",
            "No lo pueden echar por deber menos de un mes de renta aprox.",
        ),
    },
    "SA-EVIC-01": {
        "en": (
            "After 30 days, only for a good reason.",
            "If it's not your fault, they owe 3 months' help.",
        ),
        "es": (
            "Después de 30 días, solo con razón válida.",
            "Si no es su culpa, le deben 3 meses de ayuda.",
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
        "en": (
            "Yes, with one rent period's notice (30+ days).",
            "No reason needed. 3 months if rent is paid quarterly or less often. 14 days if rent is unpaid, and"
            " you get 10 days to pay.",
        ),
        "es": (
            "Sí, con un período de renta de aviso (30+ días).",
            "No necesitan razón. 3 meses si paga cada trimestre o menos seguido. 14 días si no pagó, y tiene"
            " 10 días para pagar.",
        ),
    },
    "CA-DEP-01": {
        "en": ("Max 1 month's rent.", "Small landlords may ask for 2 months."),
        "es": ("Máximo 1 mes de renta.", "Los dueños pequeños pueden pedir 2 meses."),
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
        "en": ("About $69 per applicant, max.", "California's cap grows with inflation each year."),
        "es": (
            "Máximo unos $69 por solicitante.",
            "El tope de California sube con la inflación cada año.",
        ),
    },
    "BER-FEE-01": {
        "en": ("About $69 per applicant, max.", "California's cap grows with inflation each year."),
        "es": (
            "Máximo unos $69 por solicitante.",
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
            "Old convictions can't count after a set number of years.",
        ),
        "es": (
            "No pueden preguntar por antecedentes antes de una oferta.",
            "Las condenas viejas no cuentan después de cierto tiempo.",
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
            "Berkeley prohíbe revisar antecedentes penales.",
        ),
    },
    "NJ-EVIC-01": {
        "en": (
            "They can't evict you for complaining or asking for repairs.",
            "Punishing you for using your rights is against the law.",
        ),
        "es": (
            "No lo pueden echar por quejarse o pedir reparaciones.",
            "Castigarlo por usar sus derechos va contra la ley.",
        ),
    },
    "MA-EVIC-03": {
        "en": (
            "They can't evict you for complaining or asking for repairs.",
            "If they try within 6 months of a complaint, the law assumes it is payback.",
        ),
        "es": (
            "No lo pueden echar por quejarse o pedir reparaciones.",
            "Si lo intentan dentro de 6 meses de una queja, la ley supone que es una represalia.",
        ),
    },
    "NJ-EVIC-02": {
        "en": (
            "A foreclosure alone can't end your lease.",
            "A buyer who wants to move in must give you 90 days' notice.",
        ),
        "es": (
            "Una ejecución hipotecaria no termina su contrato.",
            "Un comprador que quiera mudarse debe darle 90 días de aviso.",
        ),
    },
    "NJ-ALG-01": {
        # applies (on or after Jul 1, 2027); the not-yet and conflict wordings are in NOT_YET / CONFLICT_WHY below
        "en": (
            "No. Banned statewide since Jul 1, 2027.",
            "Landlords can't use a rent-setting service that pools rivals' data.",
        ),
        "es": (
            "No. Prohibido en todo el estado desde el 1 jul 2027.",
            "No pueden usar un servicio que fija rentas con datos de la competencia.",
        ),
    },
}
_VOUCHER = {
    "en": ("No. Vouchers count as income.", "Turning you down for a voucher is illegal."),
    "es": ("No. Los vales cuentan como ingreso.", "Rechazarlo por un vale es ilegal."),
}
_ALG = {
    "en": (
        "No. Price-fixing software is banned.",
        "Landlords can't share private rent data through an app to set prices.",
    ),
    "es": (
        "No. Los programas para fijar precios están prohibidos.",
        "No pueden compartir datos privados de rentas en un programa para fijar precios.",
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
    PLAIN[_r] = _ALG
for _r in ("MA-ALG-P1", "MA-ALG-P2"):
    PLAIN[_r] = _BILL


def plain(rule_id: str, lang: str = "en") -> dict:
    """answer / why for a rule (both None when it has none); plain_until ends a period-bound answer."""
    d = PLAIN.get(rule_id)
    if not d:
        return {"answer_display": None, "why_display": None, "plain_until": None}
    a, w = d.get(lang) or d["en"]
    return {"answer_display": a, "why_display": w, "plain_until": d.get("until")}


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
    "en": "A small landlord (2 rentals, 4 units in total at most) may ask for 2 months.",
    "es": "Un dueño pequeño (máx. 2 propiedades y 4 unidades en total) puede pedir 2 meses.",
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
) -> dict:
    """The per-address answer fields for one evaluator result.

    -> {"answer_display", "why_display", "plain_until", "headline"}: the plain answer and why line (None = the app's
    own wording for that result) and, for a rule not yet in effect, the dated row headline (else None: keep).
    effective: the rule's start (for "not yet" wordings); units / units_min: the building's unit count or its lower
    bound; conflict: the address-level conflict flag."""
    lang = "es" if lang == "es" else "en"
    p = plain(rule_id, lang)
    if result == "not_yet_effective":
        hl = headline(rule_id, lang, as_of)
        d = fmt_date(effective, lang)
        ny = (NOT_YET.get(rule_id) or {}).get(lang)
        ans = ny.format(d=d) if ny and d else None
        if ans:
            hl = ans.rstrip(".")
        elif hl and d:
            hl = (f"Desde el {d}: " if lang == "es" else f"From {d}: ") + hl[:1].lower() + hl[1:]
        return {
            "answer_display": ans,
            "why_display": None,
            "plain_until": None,
            "headline": hl,
        }
    if result in ("superseded", "pending", "failed"):
        # replaced here, or not law: the applies-wording would claim the rule governs this address
        return {"answer_display": None, "why_display": None, "plain_until": None, "headline": None}
    out = {**p, "headline": None}
    if conflict and rule_id in CONFLICT_WHY and out.get("why_display"):
        out["why_display"] = CONFLICT_WHY[rule_id][lang]
    cap = SMALL_LANDLORD_MAX_UNITS.get(rule_id)
    if cap and out.get("why_display"):
        n, lo = _int(units), _int(units_min)
        if n is not None and n > cap:
            out["why_display"] = _SMALL_NO[lang].format(n=n)
        elif n is None and lo is not None and lo > cap:
            out["why_display"] = _SMALL_NO_MIN[lang].format(n=lo)
        else:
            out["why_display"] = _SMALL_MAYBE[lang]
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
    )
    hl = f.pop("headline")
    r.update(f)
    if hl is not None:
        item["headline"] = hl
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
                if not PLAIN[rid].get("until") and (HEADLINES.get(rid) or {}).get("until"):
                    PLAIN[rid]["until"] = HEADLINES[rid]["until"]
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
