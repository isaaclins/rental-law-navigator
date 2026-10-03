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
        "en": "Up to $50 per application",
        "es": "Hasta $50 por solicitud",
        "short_en": "Max $50 + CPI per application",
        "short_es": "Máx. $50 + IPC por solicitud",
        "priority": 1,
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
        "en": "3 months' notice to end a tenancy",
        "es": "3 meses de aviso para terminar el arriendo",
        "short_en": "No just cause; 3 months' notice",
        "short_es": "Sin causa justa; 3 meses de aviso",
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
    }
