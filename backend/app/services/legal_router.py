from __future__ import annotations

from typing import TypedDict

from app.core.jurisdiction_graph import INDIA_JURISDICTION_GRAPH


class RouterResult(TypedDict):
    """Deterministic routing — graph lock. No LLM. Generic forum labels only."""

    primary_authority: str
    secondary_authority: str
    fallback_path: list[str]
    jurisdiction_reason: str
    routing_steps: list[str]


def _loc_label(location: str | None, entities: list[str] | None) -> str:
    s = (location or "").strip()
    if s:
        return s
    if entities:
        for e in entities:
            t = str(e).strip()
            if len(t) >= 2 and len(t) < 80:
                return t
    return "your district"


def route_case(
    intent: str,
    entities: list[str] | None,
    location: str | None = None,
    *,
    category: str | None = None,
    hybrid_civil_criminal: bool = False,
    priority_level: str | None = None,
    hybrid_police_primary: bool = False,
) -> RouterResult:
    """
    Hard rule system. `intent` from intent engine only — never from the formatter LLM.
    Optional `category` disambiguates corporate when intent is unknown.
    """
    loc = _loc_label(location, entities)
    it = (intent or "unknown").strip().lower()
    cat = (category or "").strip().lower()
    pl = (priority_level or "").strip().upper()

    if hybrid_police_primary:
        return RouterResult(
            primary_authority=(
                "Police Station (Station House Officer — SHO) — FIR or written complaint "
                f"({loc}) — address law-and-order and safety first"
            ),
            secondary_authority=(
                "Civil Court / District Court — possession, injunction, partition, or declaration "
                f"(as legally advised) ({loc})"
            ),
            fallback_path=[
                "Tehsildar / SDM — revenue records or demarcation only where legally relevant (not sole forum)",
                "District Magistrate / Collector — limited supervisory roles per official rules",
            ],
            jurisdiction_reason=(
                "Phase 6 hybrid (law-and-order + land/civil): police is primary to control violence and "
                "preserve safety; civil court is required for underlying ownership or possession claims. "
                "Tehsildar is never treated as the only primary forum here."
            ),
            routing_steps=[
                "If there is ongoing violence or danger: contact police (including 112 if appropriate).",
                "Preserve evidence (photos, witnesses, medical papers if any).",
                "For title or possession: consult an advocate for civil suit or injunction as legally advised.",
            ],
        )

    if pl in ("P0", "P1"):
        return RouterResult(
            primary_authority=(
                "Police Station (Station House Officer — SHO) — FIR or written complaint" + f" ({loc})"
            ),
            secondary_authority="Superintendent of Police (SP) office (escalation)",
            fallback_path=[
                "District Magistrate (limited supervisory / referral roles)",
                "Sessions / Magistrate courts",
            ],
            jurisdiction_reason=(
                "Priority of harm (P0/P1): safety and criminal conduct — police is primary; "
                "Tehsildar / revenue is not the primary forum here."
            ),
            routing_steps=list(INDIA_JURISDICTION_GRAPH["criminal"]["typical_path"]),
        )

    if pl == "P2":
        return RouterResult(
            primary_authority=(
                "Civil Court / District Court — possession, injunction, partition, or declaration "
                f"(as legally advised) ({loc})"
            ),
            secondary_authority=(
                "Police Station (SHO) — written complaint or FIR when force, threat, trespass, "
                f"encroachment, or other cognizable conduct is involved ({loc})"
            ),
            fallback_path=[
                "Tehsildar / SDM — demarcation or revenue records only where legally relevant (not sole forum)",
                "District Magistrate / Collector — limited supervisory roles per official rules",
            ],
            jurisdiction_reason=(
                "Priority of harm (P2): hybrid civil–criminal land/property facts — civil court primary; "
                "police secondary when criminal cues exist."
            ),
            routing_steps=[
                "Preserve dated evidence (title, tax receipts, photos, witnesses).",
                "Civil court track: suit or application per advocate advice (possession / injunction).",
                "Police track: complaint or FIR for cognizable facts; keep copies for civil proceedings.",
            ],
        )

    if hybrid_civil_criminal and it in ("civil_dispute", "land_dispute"):
        return RouterResult(
            primary_authority=(
                "Civil Court / District Court — possession, injunction, partition, or declaration "
                f"(as legally advised) ({loc})"
            ),
            secondary_authority=(
                "Police Station (SHO) — written complaint or FIR when force, threat, trespass, "
                f"encroachment, or other cognizable conduct is involved ({loc})"
            ),
            fallback_path=[
                "Tehsildar / SDM — demarcation or revenue records only where legally relevant (not sole forum)",
                "District Magistrate / Collector — limited supervisory roles per official rules",
            ],
            jurisdiction_reason=(
                "Hybrid civil–criminal: parallel civil remedies and police route when force, threat, "
                "कब्ज़ा-style occupation, or trespass is alleged. Tehsildar alone is not treated as the only forum."
            ),
            routing_steps=[
                "Preserve dated evidence (title, tax receipts, photos, witnesses).",
                "Civil court track: suit or application per advocate advice (possession / injunction).",
                "Police track: complaint or FIR for cognizable facts; keep copies for civil proceedings.",
            ],
        )

    corp = INDIA_JURISDICTION_GRAPH["corporate_business"]
    civ = INDIA_JURISDICTION_GRAPH["civil"]
    crim = INDIA_JURISDICTION_GRAPH["criminal"]
    lab = INDIA_JURISDICTION_GRAPH["labour"]
    tm = INDIA_JURISDICTION_GRAPH["traffic_motor"]
    lr = INDIA_JURISDICTION_GRAPH["land_revenue"]
    fam = INDIA_JURISDICTION_GRAPH["family"]
    cons = INDIA_JURISDICTION_GRAPH["consumer"]
    fin = INDIA_JURISDICTION_GRAPH["financial_banking"]
    rti = INDIA_JURISDICTION_GRAPH["rti_information"]
    civic = INDIA_JURISDICTION_GRAPH["civic_municipal"]
    edu = INDIA_JURISDICTION_GRAPH["education_grievance"]
    wc = INDIA_JURISDICTION_GRAPH["women_child_rights"]
    sen = INDIA_JURISDICTION_GRAPH["senior_maintenance"]
    pol_esc = INDIA_JURISDICTION_GRAPH["police_complaint_escalation"]

    if it in ("share_dispute", "corporate_grievance") or (
        it in ("unknown", "general_issue") and cat == "corporate"
    ):
        return RouterResult(
            primary_authority=corp["primary_forums"][0],
            secondary_authority=civ["primary_forums"][0] + " (commercial/civil, as applicable)",
            fallback_path=[corp["secondary_forums"][1], corp["primary_forums"][1]],
            jurisdiction_reason=(
                "Corporate/share disputes: NCLT or Civil Court per cause of action — "
                "Labour Commissioner is excluded by jurisdiction graph lock."
            ),
            routing_steps=list(corp["typical_path"]),
        )

    if it == "salary_issue":
        return RouterResult(
            primary_authority=lab["primary_forums"][0] + f" ({loc})",
            secondary_authority=lab["secondary_forums"][0],
            fallback_path=["State Labour Commissionerate", "District Magistrate (limited roles)"],
            jurisdiction_reason="Labour graph: wage/PF/employment → Labour Commissioner / Labour Court route.",
            routing_steps=list(lab["typical_path"]),
        )

    if it == "civil_dispute":
        return RouterResult(
            primary_authority=civ["primary_forums"][0] + f" ({loc})",
            secondary_authority="Consult a qualified advocate — civil drafting, limitation, and evidence",
            fallback_path=["High Court (appeals); Lok Adalat", "District Legal Services Authority"],
            jurisdiction_reason=(
                "Civil / contract / recovery: Civil Court / District Court — police is not the primary forum "
                "unless a separate cognizable offence is involved."
            ),
            routing_steps=list(civ["typical_path"]),
        )

    if it == "cyber_fraud":
        return RouterResult(
            primary_authority=(
                "National Cyber Crime Reporting Portal (https://www.cybercrime.gov.in) + "
                f"Cyber Police / jurisdictional police station ({loc})"
            ),
            secondary_authority=crim["primary_forums"][0],
            fallback_path=["Superintendent of Police (district)", "District Magistrate (limited roles)"],
            jurisdiction_reason=(
                "Cybercrime: report on the official cybercrime portal and coordinate with police/FIR as applicable."
            ),
            routing_steps=[
                "Preserve evidence (screenshots, transaction IDs, device details)",
                "National Cyber Crime Reporting Portal + police/cyber cell",
                "Investigation and court process as per law",
            ],
        )

    if it == "fraud_general":
        return RouterResult(
            primary_authority=crim["primary_forums"][0] + f" ({loc})",
            secondary_authority=crim["secondary_forums"][1],
            fallback_path=["Magistrate court (complaint)", cons["primary_forums"][0] + " (if consumer facet)"],
            jurisdiction_reason="Fraud/cheating: police investigation and courts as applicable.",
            routing_steps=list(crim["typical_path"]),
        )

    if it == "traffic_violation":
        return RouterResult(
            primary_authority=tm["primary_forums"][0],
            secondary_authority=tm["secondary_forums"][0],
            fallback_path=[tm["secondary_forums"][1]],
            jurisdiction_reason="Traffic: enforcement (police) vs licence/registration (RTO).",
            routing_steps=list(tm["typical_path"]),
        )

    if it == "land_dispute":
        sf = lr["secondary_forums"]
        fallback_path = [sf[i] for i in (1, 2) if i < len(sf)]
        return RouterResult(
            primary_authority=lr["primary_forums"][0] + f" / {lr['primary_forums'][1]} ({loc})",
            secondary_authority=lr["secondary_forums"][0],
            fallback_path=fallback_path,
            jurisdiction_reason="Land: Tehsildar → SDM → Collector / revenue or civil court for title.",
            routing_steps=list(lr["typical_path"]),
        )

    if it == "family_matters":
        return RouterResult(
            primary_authority=fam["primary_forums"][0],
            secondary_authority=fam["secondary_forums"][0],
            fallback_path=fam["secondary_forums"][1:],
            jurisdiction_reason="Family matters: family court / competent district jurisdiction.",
            routing_steps=list(fam["typical_path"]),
        )

    if it == "consumer_issue":
        return RouterResult(
            primary_authority=cons["primary_forums"][0],
            secondary_authority=cons["secondary_forums"][0],
            fallback_path=["E-Daakhil / state consumer portal (where available)", "Mediation cell"],
            jurisdiction_reason="Consumer: District Commission by pecuniary limits; appeals per CPA.",
            routing_steps=list(cons["typical_path"]),
        )

    if it == "criminal_police":
        return RouterResult(
            primary_authority=(
                "Police Station (Station House Officer — SHO) — FIR or written complaint" + f" ({loc})"
            ),
            secondary_authority="Superintendent of Police (SP) office (escalation)",
            fallback_path=["District Magistrate (limited supervisory / referral roles)", "Sessions / Magistrate courts"],
            jurisdiction_reason=(
                "Criminal: territorial police station for FIR/complaint; escalate to SP; courts as per procedure."
            ),
            routing_steps=list(crim["typical_path"]),
        )

    if it == "police_oversight":
        return RouterResult(
            primary_authority=pol_esc["primary_forums"][0] + f" ({loc})",
            secondary_authority=pol_esc["secondary_forums"][0],
            fallback_path=list(pol_esc["secondary_forums"][1:]),
            jurisdiction_reason=pol_esc["notes"],
            routing_steps=list(pol_esc["typical_path"]),
        )

    if it == "rti_grievance":
        return RouterResult(
            primary_authority=rti["primary_forums"][0],
            secondary_authority=rti["secondary_forums"][0],
            fallback_path=[rti["secondary_forums"][1]],
            jurisdiction_reason=rti["notes"],
            routing_steps=list(rti["typical_path"]),
        )

    if it == "civic_local":
        return RouterResult(
            primary_authority=civic["primary_forums"][0] + f" ({loc})",
            secondary_authority=civic["secondary_forums"][0],
            fallback_path=[civic["secondary_forums"][1]],
            jurisdiction_reason=civic["notes"],
            routing_steps=list(civic["typical_path"]),
        )

    if it == "banking_ombudsman":
        return RouterResult(
            primary_authority=fin["primary_forums"][0],
            secondary_authority=fin["secondary_forums"][0],
            fallback_path=list(fin["secondary_forums"]),
            jurisdiction_reason=fin["notes"],
            routing_steps=list(fin["typical_path"]),
        )

    if it == "education_dispute":
        return RouterResult(
            primary_authority=edu["primary_forums"][0] + f" ({loc})",
            secondary_authority=edu["secondary_forums"][0],
            fallback_path=[edu["secondary_forums"][1], cons["primary_forums"][0]],
            jurisdiction_reason=edu["notes"],
            routing_steps=list(edu["typical_path"]),
        )

    if it == "women_child_route":
        return RouterResult(
            primary_authority=wc["primary_forums"][0],
            secondary_authority=wc["secondary_forums"][0],
            fallback_path=list(wc["secondary_forums"]),
            jurisdiction_reason=wc["notes"],
            routing_steps=list(wc["typical_path"]),
        )

    if it == "senior_maintenance":
        return RouterResult(
            primary_authority=sen["primary_forums"][0] + f" ({loc})",
            secondary_authority=sen["secondary_forums"][0],
            fallback_path=list(sen["secondary_forums"]),
            jurisdiction_reason=sen["notes"],
            routing_steps=list(sen["typical_path"]),
        )

    return RouterResult(
        primary_authority=f"District Administration / Collector office ({loc})",
        secondary_authority=civ["primary_forums"][0],
        fallback_path=[crim["primary_forums"][0], lab["primary_forums"][0]],
        jurisdiction_reason="General / non-specific routing — district administration for referral to the correct department (graph default).",
        routing_steps=[
            "Clarify civil vs criminal vs revenue vs regulatory",
            "Use official state/India portals only",
        ],
    )
