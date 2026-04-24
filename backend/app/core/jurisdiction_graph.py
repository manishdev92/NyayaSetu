"""
India legal jurisdiction graph — single source of truth for routing (no LLM).

Enforcement: `legal_router.route_case` maps classifier output to forums here.
Criminal matters always include police/FIR path; labour/consumer/land use dedicated buckets.
"""

from __future__ import annotations

from typing import TypedDict


class JurisdictionDomain(TypedDict):
    label: str
    primary_forums: list[str]
    secondary_forums: list[str]
    typical_path: list[str]
    notes: str


INDIA_JURISDICTION_GRAPH: dict[str, JurisdictionDomain] = {
    "labour": JurisdictionDomain(
        label="Labour — salary, PF, employment",
        primary_forums=["Labour Commissioner Office (district) — Assistant Labour Commissioner / Labour Commissioner"],
        secondary_forums=["Labour Court / Industrial Tribunal (as per jurisdiction)"],
        typical_path=["Labour office conciliation → tribunal/court if unresolved"],
        notes="Strict: wage/PF/employment — not shareholder or company oppression matters.",
    ),
    "civil": JurisdictionDomain(
        label="Civil — contract, money recovery, general civil",
        primary_forums=["Civil Court / District Court (civil jurisdiction)"],
        secondary_forums=["High Court — appeals; Lok Adalat"],
        typical_path=["Cause of action → territorial jurisdiction → civil suit"],
        notes="Property/title may overlap with revenue first, then civil court.",
    ),
    "criminal": JurisdictionDomain(
        label="Criminal — theft, assault, fraud, cybercrime",
        primary_forums=[
            "Police Station (Station House Officer — SHO) — FIR / written complaint",
            "Judicial Magistrate / Sessions Court",
        ],
        secondary_forums=["Cyber Crime Police / Cell", "EOW / Crime Branch (where applicable)"],
        typical_path=["FIR or complaint → investigation → court"],
        notes="Cybercrime: cyber cell + police coordination.",
    ),
    "consumer": JurisdictionDomain(
        label="Consumer — fees, service, refund, institutional disputes",
        primary_forums=["District Consumer Disputes Redressal Commission (Consumer Commission — district)"],
        secondary_forums=["State Commission; National Commission (limits)"],
        typical_path=["Complaint by pecuniary jurisdiction → evidence → hearings"],
        notes="Use official e-filing where available.",
    ),
    "land_revenue": JurisdictionDomain(
        label="Land — boundary, mutation, records",
        primary_forums=["Tehsildar / revenue officer", "Sub-Divisional Magistrate (SDM)"],
        secondary_forums=[
            "District Collector",
            "Revenue court / Civil court (title)",
            "District Civil Court (injunction / declaration as applicable)",
        ],
        typical_path=["Tehsil mutation/records → SDM → civil court if title dispute"],
        notes="Tehsildar → SDM → Revenue/Civil court per facts.",
    ),
    "traffic_motor": JurisdictionDomain(
        label="Traffic — fine, challan, licence",
        primary_forums=["Traffic Police (traffic wing)", "Regional Transport Office (RTO) Office"],
        secondary_forums=["State Transport Authority", "Appellate forum on challan"],
        typical_path=["Challan → portal / appellate channel"],
        notes="Enforcement: police; licence/registration: RTO.",
    ),
    "corporate_business": JurisdictionDomain(
        label="Corporate — company, shares, partners (NOT labour dept)",
        primary_forums=["National Company Law Tribunal (NCLT)", "NCLAT — appeals"],
        secondary_forums=[
            "District Civil Court — commercial/civil (jurisdiction permitting)",
            "Registrar of Companies (ROC) / MCA",
        ],
        typical_path=["Cause of action → NCLT or civil court per statute → appeals"],
        notes="Shareholder/business partner disputes: NCLT/Civil Court only — never Labour Commissioner as primary.",
    ),
    "family": JurisdictionDomain(
        label="Family",
        primary_forums=["Family Court", "District Court — family jurisdiction"],
        secondary_forums=["Protection Officer (DV)", "Mediation"],
        typical_path=["Forum per relief → mediation where mandatory"],
        notes="Varies by personal law.",
    ),
    "financial_banking": JurisdictionDomain(
        label="Financial — banking, NBFC, insurance (regulatory ombudsman route)",
        primary_forums=["RBI Integrated Ombudsman Scheme / Banking Ombudsman (as applicable)"],
        secondary_forums=["Bank’s grievance redressal / nodal officer", "Insurance Ombudsman (insurance claims)"],
        typical_path=["Internal bank complaint → ombudsman portal → regulatory escalation as per circulars"],
        notes="Not a police/FIR-first route for ordinary banking service disputes.",
    ),
    "rti_information": JurisdictionDomain(
        label="RTI — access to information",
        primary_forums=["Public Information Officer (PIO) of the concerned public authority"],
        secondary_forums=["First Appellate Authority (FAA)", "State / Central Information Commission"],
        typical_path=["RTI application to PIO → first appeal → information commission"],
        notes="RTI Act procedure only — not a substitute for FIR or civil suit.",
    ),
    "civic_municipal": JurisdictionDomain(
        label="Civic — sanitation, local nuisance, illegal construction",
        primary_forums=["Municipal Corporation / Municipal Council / Nagar Palika (local body)"],
        secondary_forums=["Chief Municipal Health Officer / Engineering wing", "District Urban Development Authority (where applicable)"],
        typical_path=["Online civic complaint / ward office → municipal enforcement"],
        notes="Local self-government — not Labour Commissioner or Consumer Commission.",
    ),
    "education_grievance": JurisdictionDomain(
        label="Education — admission, certificates, institutional grievance",
        primary_forums=["State Education Department / Directorate / Board (as applicable)"],
        secondary_forums=["District Consumer Commission (fee/deficiency facets)", "University grievance cell"],
        typical_path=["Institution grievance → education department → consumer commission if deficiency/defect"],
        notes="Parallel consumer route only where facts fit CPA; not criminal police-first unless offence.",
    ),
    "women_child_rights": JurisdictionDomain(
        label="Women & child — helplines and statutory bodies",
        primary_forums=["Women Helpline (1091) / Childline (1098) — coordination and referral"],
        secondary_forums=["District Child Protection Unit / Child Welfare Committee (CWC)", "Police (if cognizable offence)"],
        typical_path=["Immediate safety → helpline / protection mechanisms → police/courts if criminal"],
        notes="Criminal conduct still maps to police/FIR in parallel where applicable.",
    ),
    "senior_maintenance": JurisdictionDomain(
        label="Senior citizen — maintenance and welfare",
        primary_forums=["Maintenance Tribunal (Maintenance and Welfare of Parents and Senior Citizens Act route)"],
        secondary_forums=["District Magistrate / Social Welfare Department (state schemes)", "Mediation / family court (linked facts)"],
        typical_path=["Application to Maintenance Tribunal with prescribed particulars"],
        notes="Not the same forum as salary disputes before Labour Commissioner.",
    ),
    "police_complaint_escalation": JurisdictionDomain(
        label="Police oversight — FIR non-registration / misconduct complaints",
        primary_forums=["Superintendent of Police (SP) / Deputy Commissioner of Police (DCP) office"],
        secondary_forums=["Judicial Magistrate (complaint under CrPC/BNSS procedure)", "State police complaints authority (where established)"],
        typical_path=["Written representation to SP/DCP with facts → judicial remedy if FIR refused where law permits"],
        notes="Not Labour Commissioner or Consumer Commission; not Collector as sole addressee for cognizable crime investigation.",
    ),
}


def flatten_graph_paths() -> list[str]:
    out: list[str] = []
    for dom in INDIA_JURISDICTION_GRAPH.values():
        out.extend(dom["primary_forums"])
        out.extend(dom["secondary_forums"])
    return out
