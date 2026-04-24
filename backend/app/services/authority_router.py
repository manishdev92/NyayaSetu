from __future__ import annotations

from typing import TypedDict

from app.services.legal_taxonomy import IssueType


class AuthorityRouting(TypedDict):
    primary_authority: str
    secondary_authority: str
    fallback_authority: list[str]
    guidance_text: str


def _placeholders(district: str, state: str) -> tuple[str, str]:
    d = (district or "").strip() or "your district"
    s = (state or "").strip() or "your state"
    return d, s


def get_recommended_authority(
    issue_type: IssueType,
    district: str,
    state: str,
) -> AuthorityRouting:
    """
    Generic India-wide routing labels — types of offices, not specific phone numbers or officer names.
    """
    d_lab, s_lab = _placeholders(district, state)

    routes: dict[IssueType, AuthorityRouting] = {
        "corporate": AuthorityRouting(
            primary_authority="National Company Law Tribunal (NCLT) — as per jurisdiction",
            secondary_authority="District Civil Court — commercial/civil suits (where pecuniary jurisdiction lies)",
            fallback_authority=[
                "Registrar of Companies (ROC) / MCA for registry filings",
                "National Company Law Appellate Tribunal (NCLAT) — appeals",
            ],
            guidance_text=(
                "Company and shareholder disputes are not handled by labour offices. "
                f"Forum depends on the cause of action and territorial/pecuniary rules for {d_lab}."
            ),
        ),
        "traffic": AuthorityRouting(
            primary_authority="Traffic Police / Traffic unit at your local police station",
            secondary_authority="Superintendent of Police (Traffic) office, if available in the district",
            fallback_authority=[
                "District Magistrate / Collector office (for escalations)",
                "Regional Transport Office (RTO) for licence/registration matters",
            ],
            guidance_text=(
                f"Start with the traffic desk or traffic police covering {d_lab}. "
                "For challans and licence issues, RTO may also apply. "
                "Escalate in writing to the District Magistrate if the matter is not resolved."
            ),
        ),
        "salary": AuthorityRouting(
            primary_authority="Office of the Assistant Labour Commissioner / Labour department (district)",
            secondary_authority="Labour Court / Industrial Tribunal (as per jurisdiction)",
            fallback_authority=[
                "District Magistrate / Collector office",
                "State Labour Commissionerate (for policy-level or interstate issues)",
            ],
            guidance_text=(
                f"Labour and wage complaints are typically filed with the labour office for {d_lab}, {s_lab}. "
                "If conciliation fails, matters may move to labour court/tribunal as per law."
            ),
        ),
        "cyber": AuthorityRouting(
            primary_authority="District Cyber Crime Cell / Cyber police station (where available)",
            secondary_authority="Local police station (for FIR and coordination)",
            fallback_authority=[
                "National Cyber Crime Reporting Portal (citizen reporting)",
                "State cyber nodal agency",
            ],
            guidance_text=(
                "Report online financial fraud promptly with transaction details. "
                "Many states route cyber complaints through district cyber cells and the national portal."
            ),
        ),
        "fraud": AuthorityRouting(
            primary_authority="Local police station (for FIR)",
            secondary_authority="Economic Offences Wing / Crime Branch (if the district has one)",
            fallback_authority=[
                "District Magistrate (for certain public complaints)",
                "Consumer forum (if a consumer transaction is involved)",
            ],
            guidance_text=(
                "Fraud and cheating complaints usually begin with a written complaint or FIR at the police station "
                f"having jurisdiction over {d_lab}. Complex financial fraud may be handled by specialised wings."
            ),
        ),
        "land": AuthorityRouting(
            primary_authority="Tehsildar / Sub-Divisional Magistrate (revenue) office",
            secondary_authority="District Collector / District Magistrate office",
            fallback_authority=[
                "State revenue department helpline / portal",
                "Civil court (for title suits, as applicable)",
            ],
            guidance_text=(
                f"Land and revenue disputes often start with the revenue officer for {d_lab}. "
                "Survey and mutation matters are typically handled through tehsil/district revenue offices."
            ),
        ),
        "police": AuthorityRouting(
            primary_authority="Local police station having territorial jurisdiction",
            secondary_authority="Senior police officials in the district (as per hierarchy)",
            fallback_authority=[
                "District Superintendent of Police office",
                "Human rights commissions (for custodial or serious complaints)",
            ],
            guidance_text=(
                f"Most policing complaints are registered at the station covering the area in {d_lab}. "
                "Escalate in writing to senior officers if required."
            ),
        ),
        "family": AuthorityRouting(
            primary_authority="Family court / District court (as per jurisdiction)",
            secondary_authority="Protection Officer / DWCD (for domestic violence matters, where applicable)",
            fallback_authority=[
                "Mediation centres attached to courts",
                "Legal services authority (legal aid)",
            ],
            guidance_text=(
                "Family matters are handled by courts with appropriate jurisdiction. "
                "Legal aid may be available through district legal services authorities."
            ),
        ),
        "consumer": AuthorityRouting(
            primary_authority="District Consumer Disputes Redressal Commission / Forum (district level)",
            secondary_authority="State consumer commission (appeals, as applicable)",
            fallback_authority=[
                "E-daakhil / consumer portal (online filing, where available)",
                "Mediation cell (pre-litigation)",
            ],
            guidance_text=(
                "Consumer complaints are filed before the district or state consumer forum based on pecuniary limits. "
                "Keep invoices and written communications as evidence."
            ),
        ),
        "civil_dispute": AuthorityRouting(
            primary_authority="Civil Court / District Court (civil jurisdiction)",
            secondary_authority="Mediation centre / Lok Adalat (where applicable)",
            fallback_authority=[
                "High Court — appeals (pecuniary and territorial rules apply)",
                "District Legal Services Authority (legal aid)",
            ],
            guidance_text=(
                "Civil disputes (contracts, recovery, property as civil wrongs) are adjudicated by civil courts — "
                "not the police station as the primary forum unless a cognizable offence is separately involved."
            ),
        ),
        "general": AuthorityRouting(
            primary_authority="District Administration — Collector / District Magistrate office",
            secondary_authority="Local police station (if safety or criminal conduct is involved)",
            fallback_authority=[
                "District legal services authority (guidance)",
                "Official state government portal for the relevant department",
            ],
            guidance_text=(
                f"For general or mixed issues, contact the district administration for {d_lab} for direction "
                "to the correct department. Always prefer official government websites and written records."
            ),
        ),
        "financial": AuthorityRouting(
            primary_authority="RBI Integrated Ombudsman / Banking Ombudsman (as applicable)",
            secondary_authority="Bank’s internal grievance / nodal officer",
            fallback_authority=["Insurance Ombudsman (insurance claims)", "District Consumer Commission (if deficiency)"],
            guidance_text="Banking and NBFC grievances follow regulatory ombudsman routes — not Labour Commissioner.",
        ),
        "rti": AuthorityRouting(
            primary_authority="Public Information Officer (PIO) of the concerned authority",
            secondary_authority="First Appellate Authority — then Information Commission",
            fallback_authority=["Official RTI portals of the Union / state government"],
            guidance_text="RTI Act procedure only — use written applications and prescribed appeals.",
        ),
        "civic": AuthorityRouting(
            primary_authority="Municipal Corporation / local urban body",
            secondary_authority="Ward office / municipal engineer or sanitation wing",
            fallback_authority=["District urban development authority (where applicable)"],
            guidance_text="Civic sanitation and illegal construction are municipal enforcement matters.",
        ),
        "education": AuthorityRouting(
            primary_authority="State Education Department / Board / Directorate",
            secondary_authority="District Consumer Commission (fee or service deficiency facets)",
            fallback_authority=["University / school grievance cell"],
            guidance_text="Education grievances start with the institution and department; consumer route if CPA facts fit.",
        ),
        "women_child": AuthorityRouting(
            primary_authority="Women Helpline (1091) / Childline (1098) — referral and coordination",
            secondary_authority="District Child Protection Unit / CWC; police if cognizable offence",
            fallback_authority=["District Women’s Commission (where established)"],
            guidance_text="Immediate safety first; parallel police/FIR where a criminal offence is disclosed.",
        ),
        "senior_citizen": AuthorityRouting(
            primary_authority="Maintenance Tribunal (senior citizens maintenance route)",
            secondary_authority="District Social Welfare / DM office (schemes and escalation)",
            fallback_authority=["Mediation / family court (linked facts)"],
            guidance_text="Senior maintenance is a tribunal route — distinct from salary disputes before labour office.",
        ),
        "police_oversight": AuthorityRouting(
            primary_authority="Superintendent of Police (SP) / Deputy Commissioner of Police (DCP)",
            secondary_authority="Judicial Magistrate (complaint where FIR refusal is alleged under procedure)",
            fallback_authority=["State police complaints authority (where established)"],
            guidance_text="FIR non-registration and police misconduct escalate in writing to SP/DCP and judicial routes as per law.",
        ),
    }

    return routes.get(issue_type, routes["general"])
