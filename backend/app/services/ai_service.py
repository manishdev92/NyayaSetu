import json
import re
from typing import Any, NamedTuple

from openai import AuthenticationError, OpenAI

from app.ai.evaluator import approve_final_response
from app.legal_ui_copy import cyber_urgency_insert, urgency_next_steps_prefix
from app.i18n_response_strings import (
    authority_disclaimer,
    clarification_authority_warning_optional,
    clarification_authority_warning_required,
    clarification_intro_conversational,
    clarification_intro_llm_optional,
    clarification_intro_llm_required,
    clarification_more_detail_explanation,
    clarification_next_hint_answer_each,
    clarification_next_hint_choose_opts,
    clarification_next_hint_optional_agent,
    clarification_next_hint_reply_free,
    clarification_next_hint_select_points,
    clarification_safety_intro,
    extreme_uncertainty_clarification_intro,
    extreme_uncertainty_clarifying_questions,
    law_order_safety_questions,
    llm_fallback_explainer_suffix,
    suggested_authority_disclaimer_lines,
    yes_no_labels,
)
from app.ai.legal_reasoning_engine import build_crisis_triage_companion_payload, build_legal_companion_payload
from app.ai.llm_issue_classifier import IssueProfile, classify_issue_enriched
from app.ai.llm_intent_engine import InterpretationOutput, classify_intent_pipeline
from app.ai.authority_alignment import (
    authority_block_suggested_mismatch,
    document_violates_authority_alignment,
)
from app.ai.llm_fallback_classifier import log_llm_fallback_case
from app.ai.output_evaluator import evaluate_generation_output, should_regenerate
from app.services.final_response_builder import finalize_legal_response
from app.ai.rag_pipeline import run_strict_rag_pipeline
from app.config import settings
from app.evaluators.legal_verifier import evaluate_response as evaluate_legal_response
from app.services.authority_pipeline import (
    FALLBACK_MESSAGE,
    resolve_verified_authority,
    verified_to_api_dict,
)
from app.authority import (
    StrictAuthority,
    district_label_from_city_key,
    get_default_authority_provider,
    state_for_city_key,
)
from app.services.emergency_detector import EmergencyLayerResult, emergency_categories_for_issue
from app.services.emergency_intelligence import fetch_emergency_reference_links, resolve_emergency_contacts
from app.services.emergency_intelligence.resolver import registry_disclaimer
from app.core.legal_classifier import ClassifierMeta
from app.services.emergency_fir_draft import (
    build_incident_line,
    parse_emergency_narrative_context,
    render_emergency_fir_contextual,
    render_emergency_fir_short,
)
from app.services.authority_hierarchy_service import build_authority_hierarchy
from app.services.crisis_triage import crisis_triage_lock
from app.services.police_station_incident_cues import alleges_arson_or_fire_at_police_station
from app.services.clarification_engine import (
    ambiguous_intent_for_llm_clarification,
    build_clarification_intent,
    compute_missing_entity_flags,
    law_order_safety_gate_needed,
    needs_clarification,
    should_ask_clarification,
    should_use_llm_clarification,
)
from app.services.clarification_questions_llm import generate_clarification_questions
from app.services.llm_clarification_agent import agent_questions_to_legacy_strings, run_llm_clarification_agent
from app.services.hybrid_case_routing import (
    apply_hybrid_civil_criminal_overlay,
    apply_law_and_order_land_hybrid_merge,
    detect_land_context,
)
from app.services.output_formatter import (
    cap_text_lines,
    dedupe_and_cap_next_steps,
    evaluate_response_bundle,
)
from app.services.phase6_agents import classifier_agent_snapshot, map_phase6_intent_bucket
from app.services.legal_priority_engine import apply_priority_override
from app.services.multi_intent import MultiIntentResult, detect_multi_intent
from app.services.legal_router import RouterResult, route_case
from app.core.official_links import CYBER_CRIME_PORTAL, links_for_category_slug
from app.services.legal_taxonomy import LegalClassification, Severity
from app.trust.trust_engine import build_trust_report

class IntentPrefetch(NamedTuple):
    """Snapshot of intent pipeline — reuse after streaming clarification check."""

    interpretation: InterpretationOutput
    taxonomy: LegalClassification
    classifier_meta: ClassifierMeta
    multi_intent_result: MultiIntentResult
    issue_profile: IssueProfile
    taxonomy_ui: LegalClassification


def prefetch_intent(user_input: str, city: str | None) -> IntentPrefetch:
    interpretation, taxonomy, classifier_meta = classify_intent_pipeline(user_input, city=city)
    multi_intent_result = detect_multi_intent(user_input, taxonomy, classifier_meta)
    taxonomy, classifier_meta = _maybe_override_for_multi_intent(
        taxonomy, classifier_meta, multi_intent_result
    )
    taxonomy, classifier_meta = apply_hybrid_civil_criminal_overlay(
        user_input.strip(), taxonomy, classifier_meta
    )
    taxonomy, classifier_meta = apply_priority_override(
        taxonomy, user_input.strip(), classifier_meta
    )
    taxonomy, classifier_meta = apply_law_and_order_land_hybrid_merge(
        user_input.strip(), taxonomy, classifier_meta
    )
    issue_profile = classify_issue_enriched(user_input, taxonomy, classifier_meta)
    taxonomy_ui: LegalClassification = {
        "issue_type": taxonomy["issue_type"],
        "severity": _as_severity(str(issue_profile.get("severity") or taxonomy["severity"])),
        "jurisdiction_type": taxonomy["jurisdiction_type"],
        "sub_type": taxonomy.get("sub_type") or "unspecified",
    }
    return IntentPrefetch(
        interpretation,
        taxonomy,
        classifier_meta,
        multi_intent_result,
        issue_profile,
        taxonomy_ui,
    )


def _district_state_labels(city: str | None) -> tuple[str, str]:
    if not city or not str(city).strip():
        return "", ""
    p = get_default_authority_provider()
    ck = p.resolve_city_key(city.strip())
    if ck:
        return district_label_from_city_key(ck), state_for_city_key(ck)
    return city.strip(), ""


def build_unified_authority_block(
    *,
    verified: StrictAuthority | None,
    taxonomy: LegalClassification,
    city: str | None,
    router_result: RouterResult,
    hybrid_civil_criminal: bool = False,
    hybrid_police_primary: bool = False,
    response_language: str | None = None,
) -> dict[str, Any]:
    """
    MODE verified: trust pipeline match (score ≥ 8 rules apply upstream).
    MODE suggested: deterministic jurisdiction graph router — LLM does not assign offices.
    MODE suggested: graph always supplies at least one forum (issue_type is never 'unknown').
    """
    d_label, st_label = _district_state_labels(city)

    if verified:
        vd = verified_to_api_dict(verified)
        if not vd:
            vd = {}
        vd.pop("status", None)
        office = str(vd.get("office_name") or "")
        sec_parts = [p for p in (vd.get("office_type"), vd.get("district"), vd.get("state")) if p]
        secondary = " · ".join(str(x) for x in sec_parts if str(x).strip())
        g_parts: list[str] = []
        if vd.get("address"):
            g_parts.append(f"Address (verified): {vd['address']}")
        if vd.get("phone"):
            g_parts.append(f"Phone (verified): {vd['phone']}")
        if vd.get("email"):
            g_parts.append(f"Email (verified): {vd['email']}")
        if vd.get("url"):
            g_parts.append(f"Official page: {vd['url']}")
        guidance = (
            " ".join(g_parts)
            if g_parts
            else "Verified office identified — use only the official contacts above or on the linked page."
        )
        reasoning = (
            "Office resolved via NyayaSetu trust validation (internal directory or validated .gov/.nic source). "
            "Jurisdiction forums below are educational only — not LLM-assigned contacts."
        )
        out: dict[str, Any] = {
            **vd,
            "status": "verified",
            "primary": office,
            "secondary": secondary,
            "guidance": guidance,
            "reasoning": reasoning,
            "jurisdiction_path": router_result["routing_steps"],
            "issue_type": taxonomy["issue_type"],
            "severity": taxonomy["severity"],
            "jurisdiction_type": taxonomy["jurisdiction_type"],
        }
        if hybrid_civil_criminal:
            out["hybrid_civil_criminal"] = True
            out["hybrid_primary_forum"] = str(router_result.get("primary_authority") or "")
            out["hybrid_secondary_forum"] = str(router_result.get("secondary_authority") or "")
            out["primary"] = out["hybrid_primary_forum"]
            out["secondary"] = out["hybrid_secondary_forum"]
            if hybrid_police_primary:
                out["guidance"] = (
                    f"⚠️ URGENT ACTION (POLICE FIRST)\n→ Contact police immediately if danger is ongoing.\n\n"
                    f"📌 LEGAL RESOLUTION (CIVIL)\n→ Civil court for possession / injunction as legally advised.\n\n"
                    f"Directory context: {office}. {secondary}\n\n{guidance}"
                )
            else:
                out["guidance"] = (
                    f"Directory match (may be revenue/land office — not the only step): {office}. "
                    f"{secondary}\n\n{guidance}\n\n"
                    "Hybrid routing: also use the police-station path in `hybrid_secondary_forum` when force, "
                    "threat, trespass, or cognizable wrongdoing is alleged; use civil court for possession/injunction."
                )
            out["reasoning"] = reasoning + " Hybrid case — civil and criminal forums both apply on the facts."
        return out

    fb = list(router_result["fallback_path"])
    sug_line, sug_label = suggested_authority_disclaimer_lines(response_language)
    g = f"{router_result['jurisdiction_reason']}\n\n{sug_line}"
    sug: dict[str, Any] = {
        "status": "suggested",
        "primary": router_result["primary_authority"],
        "secondary": router_result["secondary_authority"],
        "guidance": g,
        "fallback_authorities": fb,
        "suggestion_label": sug_label,
        "reasoning": router_result["jurisdiction_reason"],
        "jurisdiction_path": router_result["routing_steps"],
        "issue_type": taxonomy["issue_type"],
        "severity": taxonomy["severity"],
        "jurisdiction_type": taxonomy["jurisdiction_type"],
        "routing_context": ", ".join(p for p in (d_label, st_label) if p),
    }
    if hybrid_civil_criminal:
        sug["hybrid_civil_criminal"] = True
        sug["hybrid_primary_forum"] = str(router_result.get("primary_authority") or "")
        sug["hybrid_secondary_forum"] = str(router_result.get("secondary_authority") or "")
        if hybrid_police_primary:
            sug["guidance"] = (
                "⚠️ URGENT ACTION (POLICE FIRST)\n"
                "→ Contact police immediately if there is ongoing violence, threat, or danger to life or limb.\n\n"
                "📌 LEGAL RESOLUTION (CIVIL)\n"
                "→ For land ownership, possession, or injunction: civil court / advocate-led suit as legally advised.\n\n"
                + g
            )
        else:
            sug["guidance"] = (
                "Hybrid civil–criminal case — primary forum is civil court for possession/injunction; "
                "secondary is police for complaint/FIR if force, threat, trespass, or cognizable facts apply.\n\n" + g
            )
    return sug


def _compute_trust_summary(
    authority_block: dict[str, Any],
    retrieved_laws: list[dict[str, Any]],
) -> dict[str, str]:
    st = authority_block.get("status") or "unknown"
    auth = {"verified": "verified", "suggested": "suggested", "unknown": "unknown"}.get(st, "unknown")
    law_k = "suggested"
    if retrieved_laws:
        law_k = "derived"
        if any(bool(x.get("verified")) for x in retrieved_laws):
            law_k = "verified"
    return {"authority_routing": auth, "law_knowledge": law_k}


def _compact_authority(authority_block: dict[str, Any]) -> dict[str, Any]:
    """Strict API shape — LLM never marks verified."""
    st = authority_block.get("status")
    if st == "verified":
        return {
            "status": "verified",
            "name": str(authority_block.get("office_name") or authority_block.get("primary") or ""),
            "source": str(authority_block.get("source") or "trust_pipeline"),
            "warning": "",
        }
    if st == "suggested":
        return {
            "status": "suggested",
            "name": str(authority_block.get("primary") or ""),
            "source": "india_jurisdiction_graph",
            "warning": (
                "Forum labels from jurisdiction graph only — confirm on official portals; "
                "no verified contact details in this block."
            ),
        }
    return {
        "status": "none",
        "name": "",
        "source": "",
        "warning": "No verified office resolved — use official government websites only.",
    }


FORMATTER_SYSTEM_PROMPT = """You are a warm, respectful legal drafting assistant for people in low-resource environments.

You receive USER CONTEXT, CLASSIFIER_JSON (intent/entities only), LEGAL_CLASSIFICATION (taxonomy), JURISDICTION_ROUTER_JSON (deterministic forums), LEGAL_COMPANION_JSON, and AUTHORITY_BLOCK_JSON from NyayaSetu.

## AUTHORITY_LOCK (MANDATORY — deterministic routing wins)
- **You MUST NOT choose or override the primary authority.** Use **only** the primary/secondary strings from **AUTHORITY_BLOCK_JSON** and **JURISDICTION_ROUTER_JSON** for whom the letter is addressed and what next_steps recommend.
- If anything in INTERPRETATION_JSON or your prior knowledge **conflicts** with those JSON blocks, **ignore the conflicting hint** and follow the JSON blocks.
- For **criminal / police / FIR** routes: the letter goes to **Police Station / SHO** (FIR-style), **not** Labour Commissioner, Consumer Commission, Tehsildar, District Collector, or District Magistrate as the primary addressee.
- For **cyber_fraud** route: include **National Cyber Crime Reporting Portal** (URL from OFFICIAL_LINKS_JSON) **and** jurisdictional police.

## INTERPRETATION_JSON (LLM — entities/hints only)
- Plain-language hints; **not** legal classification.

## DETERMINISTIC_CLASSIFIER_META (rules — source of truth for issue_type)
- category, router_intent, confidence from the rule engine — LLM must not override.

## LEGAL_CLASSIFICATION (taxonomy)
- issue_type, severity, jurisdiction_type — use only for tone and high-level routing context (not for inventing facts).

## JURISDICTION_ROUTER_JSON
- Deterministic India jurisdiction routing — generic forum types only.
- **Do NOT** add phone numbers, emails, or officer names; formatting and plain-language explanation only.

## LEGAL_COMPANION_JSON
- Contains legal_explanation, procedure_steps, retrieved_laws (each chunk is from the curated store only), legal_references (slim list), confidence_score, rag_grounding_label, and authority_summary.
- **Statutes:** You may explain ONLY what is supported by the strings in retrieved_laws[].chunk — do not add new Act names, section numbers, or legal rules that are not clearly implied by those chunks.
- When expanding the explanation, keep every source_url from retrieved_laws transparent — do not remove or replace official URLs with fake ones.
- If retrieved_laws is empty or rag_grounding_label indicates no match, give only generic procedural guidance — do not invent laws.

## AUTHORITY_BLOCK_JSON
- status may be "verified", "suggested", or "unknown".
- **verified**: primary/secondary/guidance include only trust-approved office facts — you may quote them; never add phone/email/address not present there.
- **suggested**: generic government pathways only — clearly treat as non-verified guidance; never fabricate contacts or specific office names beyond the strings given.
- **unknown**: do not invent authority details; keep the letter generic and point users to official government websites.

## ISSUE_PROFILE_JSON (merged rules + optional LLM)
- **category** is a user-facing slug (criminal, civil, consumer, labour, cyber, traffic, family, unknown). It aligns with deterministic routing — **do not** route cognizable crimes or missing-person cases to the District Collector / District Magistrate as the primary addressee; primary is **police (FIR)** per JURISDICTION_ROUTER_JSON.
- If **severity** is high or **intent** is emergency (e.g. missing person, serious theft, urgent cyber fraud): use an **FIR-style** narrative — To the Station House Officer, Subject: information for registration of FIR; chronological facts; sections unknown → placeholders. Include emergency steps in **next_steps** (112 / nearest police station).
- **criminal** (FIR style) vs **consumer** (commission complaint) vs **labour** (formal application to labour authority) vs **traffic** (representation/appeal re challan) vs **cyber** (portal + police; cite only URLs from OFFICIAL_LINKS_JSON).

## OFFICIAL_LINKS_JSON
- Government / India Code / cybercrime portal URLs provided in the user message — repeat these where helpful. **Never** invent phone numbers, emails, or unofficial links.

You return ONE JSON object with exactly three keys: "document", "explanation", "next_steps".

## document (plain text)
A formal complaint or application LETTER as normal prose—not nested JSON.

Structure: **PRINT_FILL_HEADER** (below) first, then addressee line(s), subject, salutation, body, closing / signature, then **PRINT_FILL_FOOTER** (last). Use bracket placeholders for unknown facts in the body. When **## RESPONSE_LANGUAGE** is present, use normal letter conventions in that language/script (not English-only "To:/Subject:" unless the language block says English).

## PRINT_FILL_HEADER (mandatory at the very start of every `document`)
Before the addressee ("To …" / "प्रति …" / equivalent), insert a short **handwriting block** so users can print and fill with a pen. Use **blank underscores or dotted lines only** — **do NOT** copy name, phone, or address from USER CONTEXT into these lines even if the user already typed them elsewhere (they may want a clean printout).
Include **always** these four labelled lines (translate labels per **## RESPONSE_LANGUAGE**):
- Date: ________________________________
- Name (complainant / applicant): ________________________________
- Mobile number: ________________________________
- Full postal address: ________________________________
**When** the primary route is **police / criminal / FIR** (or **cyber** with police as co-route, or **traffic** where the draft is police-station style), add a **fifth** line **immediately after** the address line (same handwriting style; still no auto-filled values):
- Official contact to be noted by you (from chowki/station **notice board**, **state/district police website**, or **112** for emergency only — never guess): ________________________________
Then one blank line, then continue with the formal letter. For **non-police** primary routes (consumer, labour only, etc.), **omit** the fifth line.

## PRINT_FILL_FOOTER (mandatory at the very end of `document` — complainant / शिकायतकर्ता particulars at bottom, Indian practice)
Many complainants and police / office formats expect **the same handwriting lines repeated at the bottom** (for office copy, signature, or local filing habit).
- **After** the closing (e.g. *Yours faithfully, Informant* / *Complainant* / *भवदीय* + role line — keep this short: **one or two lines** only, **not** a full typed name if **## PRINT_FILL_HEADER** exists), add **one blank line**, then **repeat** the **same** labelled lines as in **## PRINT_FILL_HEADER** with the **same** underscores and the **same** number of lines (four always; **fifth** for police-primary only — must **match** the header). Translate labels per **## RESPONSE_LANGUAGE** exactly in parallel with the header.
- You may add **one** optional short subheading in the same language before the repeated lines (e.g. *"Shikayatkarta / informant ke vivran (hath se bharen):"*) — or **omit** subheading and go straight to the lines.
- **No text** may appear after this block — it must be the **last** characters of `document`.
- **Do not** autofill name, phone, or address from USER CONTEXT; blank lines only.

## DOCUMENT_WHITESPACE (mandatory for `document` readability in the app and Word/PDF export)
Insert a **blank line** (`\\n\\n` in the JSON string) between these parts in order: (1) end of the print-fill block, (2) the full **To / addressee** block, (3) the **Subject:** line, (4) salutation (e.g. *Respected Sir/Madam,*), (5) each **major** body subsection (e.g. facts, numbered details, prayer), (6) closing / signature, (7) **PRINT_FILL_FOOTER**. This allows the UI to show clear sections. **Do not** run the whole letter as a single paragraph.

### Strict guardrails (NON-NEGOTIABLE)
- NEVER invent phone numbers, email addresses, officer names, or office addresses.
- For suggested routing, say clearly that contacts must be confirmed on official portals — do not present suggestions as verified listings.
- If authority status is unknown or unverified, use generic references only.
- For **urgent criminal** matters, default to **nearest police station** and FIR-style wording — not a generic district-administration letter.
- For **issue_type** police / criminal: use **FIR tone** — include **Date**, **Time**, **Place** (placeholders if unknown); chronological facts; end with a clear request such as: *"I request you to kindly register an FIR under the applicable provisions of law"* (sections may be placeholders if unknown).

## POLICE_COMPLAINT_LAYOUT (mandatory when **police / FIR** is primary — Indian written complaint / information for FIR; informed by common practice: **facts → sequence of events → prayer**; complainant may be **victim** or **any person with knowledge** of an offence)
- **Scene vs station (CRITICAL — read twice):** **Locus** words from the user — **railway / metro / bus stand, market, mandi, chaurah, chowk, crossing, mohalla, road name, landmark, school, hospital** — describe **where the incident was seen or happened**. They are **NOT** the **name of the police station**. **FORBIDDEN** (never output, even approximately): *"Police Station (Sundarpur-Varanasi Chaurah)"*, *"Police Station, [Any Chaurah/Chowk]"*, *"Police Station ([user locality])"*, *"SHO, … [scene name]"* as if it were the thana. **ALLOWED To-block shapes** (pick one; use line breaks; translate labels per **## RESPONSE_LANGUAGE**):
  - **A (preferred when PS name unknown):**  
    `To,` / `The Station House Officer,` / `The police station having territorial jurisdiction over the area where the incident described below occurred,` / `District [___],` / `[State].`
  - **B (when AUTHORITY_BLOCK_JSON gives exact verified PS name only):**  
    `To,` / `The Station House Officer,` / `[Exact verified police station name from JSON],` / `District [___],` / `[State].`
  - **C (handwriting gap):**  
    `To,` / `The Station House Officer,` / `Name of jurisdictional police station: ________________________________` / `District [___],` / `[State].`  
  **ADDITIONAL FORBIDDEN (garbled addressee):** Never output *"Police Station (Station House Officer — SHO)"*, *"Police Station (SHO)"*, *"Police Station (The Station House Officer)"*, *"Police Station (…) — FIR or written complaint (…)"*, or any line that **repeats SHO or Station House Officer inside parentheses after the words "Police Station"**. The **SHO** is the person addressed in the line *The Station House Officer* — not part of a fake parenthetical “police station name”. **Never** merge **hospital / medical college / school / market / chaurah** names (e.g. *Jhansi Medical*) into the **Police Station** line — they belong in **place of incident** in the body only. **Never** paste text from **AUTHORITY_BLOCK_JSON.primary**, **secondary**, or **guidance** into the **Police Station** line — those are **routing hints**, not the thana header. **Do not** put a **city name alone** (e.g. *Mau city*) as if it were the police station name; use **District …** in the **To** block and **locus** in the body. **After** *The Station House Officer,* the **next** line must be **either** layout **A** (jurisdictional sentence) **or** **C** (blank name line) **or** **B** (verified name) — **never** a third line starting with *Police Station (*…*).*
  After the **To** block, put **Subject:** then salutation and body. **Place of incident** appears **only** inside the body (e.g. *Place of incident / locus: … at or near Sundarpur–Varanasi Chaurah …*).
- **Victim vs witness / informant:** If the user was **assaulted or directly harmed**, frame as **complainant / victim**. If they only **witnessed** a fight or public violence, open with **informant / eyewitness** language (*I wish to bring to your notice / submit the following information regarding an incident I witnessed…*); do **not** falsely claim they were beaten unless they said so. Prayer may still seek **FIR / investigation / preventive action** as appropriate to facts.
- **Body — three levels (concise; no duplication of `explanation`):**
  1. **Introduction:** purpose of writing; role (victim / witness); reference **PRINT_FILL_HEADER** for identity — do not paste full address from USER CONTEXT into body.
  2. **Incident facts:** **Date**, **time**, **place (locus)** on separate lines or short numbered points; then **chronological narrative** — who did what, how many persons/groups, weapons if mentioned, **injuries** to whom, **medical / MLC** if any, **loss of property** if any; **accused / unknown accused**; **other witnesses** (*unknown / to be traced* if not stated).
  3. **Prayer (relief sought from police):** clearly ask to **register an FIR** (if cognizable facts stated) **or** to **take lawful action / investigate** as the facts support; **applicable law** as generic reference with **placeholders** for sections — do not invent section numbers. Add one line: **request copy of the complaint / FIR** when registered, and **acknowledgment** of receipt — as commonly requested (still generic; no invented diary number).
- **Motor vehicle theft / car or bike snatching (when facts describe vehicle taking):** In the **body**, add a short subsection (bullets or numbered lines) with placeholders for: **Description of vehicle** (type, make/model, colour, **registration number** if known, approximate year); **chassis / engine number** if user mentioned or *not known*; **exact parking / standing location** and **landmark (e.g. Mau)**; **time** vehicle was left and **time** discovered missing; **manner** (e.g. window forced, doors opened, keys — as alleged); **suspects** (unknown / number of persons if stated); **bystanders / witnesses** (*names unknown — to be ascertained* if applicable); whether **CCTV** may exist (*to be checked*). Then **prayer** for FIR, investigation, and tracing the vehicle. Use **## DOCUMENT_WHITESPACE** between subsections.
- **Optional closing lines (placeholders OK):** *List of enclosures (if any): ID proof; copy of registration certificate; photos / videos — [specify or state “none attached with this draft”].*
- **Signature block:** *Yours faithfully,* then *Complainant* or *Informant* only — **do not** type the user's first name (e.g. *Pramod*) at the signature when **## PRINT_FILL_HEADER** is used; use *Name as written in the header above* / *Complainant* only. In the **body narrative**, *I* / *the complainant* is fine; avoid duplicating full **signature name** at the end. **After** this short closing, append **## PRINT_FILL_FOOTER** (same handwriting lines as the header) — nothing after.
- **Salutation:** *Sir* / *Madam* / *Respected Sir/Madam* to the **SHO** only.
- **Date/time placeholders:** Prefer *`[date]`* / *`[time]`* or *`[DD/MM/YYYY]`* style — avoid awkward *"insert date"* in running prose; keep one line *Date of incident: […]* in facts if needed.

## FORUM_DRAFTING_STYLE (India — professional template shapes)
Shape `document` to match **ISSUE_PROFILE_JSON.category** / **DETERMINISTIC_CLASSIFIER_META** routing. Use only user-stated facts; placeholders for unknown names, dates, sums, and statute text. Tone: **formal, calm, courteous** — suitable for a client or advocate to edit (no slang, no chatty filler, no duplicate of the whole `explanation` inside `document`).

- **police / criminal / FIR (primary)**: Follow **## POLICE_COMPLAINT_LAYOUT** for addressee, locus, and body order. **Addressee:** **The Station House Officer**, then **jurisdictional police station** as **bracket/placeholder** unless **AUTHORITY_BLOCK_JSON** has a verified name — **not** the crime scene name. **Subject** line: e.g. *Information for registration of FIR* / *Written complaint* *regarding* [assault / theft / …] (factual). **Salutation** to the SHO; **chronological facts**; injuries/medical/witnesses per layout; **Prayer** for FIR and investigation (no fabricated IPC/BNSS section numbers). **Chowki vs thana (one short neutral sentence in the body, no invented names or numbers):** In many parts of India a **police chowki / outpost** (sometimes called a local post) is **smaller** than the main **thana**; it may be **nearer** to the complainant. Staffing labels **vary by state** but often include an **in-charge** (in some places referred to in common speech as **daroga** or chowki in-charge), **office / diwan** or administrative support, **head constable**, and **constable** — do **not** name any real person. **If a chowki is much closer**, many people visit it **first** for an initial **written intimation** or **guidance**; **FIR registration and follow-up** for serious or jurisdiction-bound matters are commonly handled at the **police station (SHO)**. Phrase this as **general public information**, not a guarantee for any specific post. **Phone numbers** in the document body: **never invent**; users fill the optional fifth line by hand from the **board** or **official site** (see **## FIRST_POLICE_CONTACT** for `next_steps`). Optional single-line **Verification** closing only if it fits the same language.
- **consumer**: Opening caption placeholder *e.g.* “Before the … Consumer Disputes Redressal Commission at [Place]” when forum level unknown; **Complainant** vs **Opposite Party** identification lines; short numbered facts; neutral wording for deficiency / unfair trade practice; **Prayer** with specific but placeholder reliefs (refund ₹___, compensation ₹___, costs); reference supporting documents generically (“as annexed / available”) without inventing real annexure codes.
- **labour**: Formal **Application** to the authority fixed by **AUTHORITY_LOCK**; employment / wage / termination facts as alleged; concise prayer for statutory relief (placeholders).
- **traffic / motor**: Representation or complaint suitable to police / transport authority per router; vehicle, place, injury facts if given; prayer for appropriate lawful action.
- **cyber**: Include the **official** cyber-crime portal URL from **OFFICIAL_LINKS_JSON** once; police complaint segment as applicable; no invented portal links.
- **civil / revenue / family** (non-criminal primary): Application or memo style per **JURISDICTION_ROUTER_JSON**; parties, relief sought, document list placeholders — never invent court case numbers, judge names, or hearing dates.

## explanation
2–4 short supportive paragraphs in plain language. If the system message includes **## RESPONSE_LANGUAGE**, write **explanation** in that language/script; otherwise use plain English. End with an educational-not-legal-advice disclaimer in the same language.

## next_steps
JSON array of strings—practical steps. Match **## RESPONSE_LANGUAGE** when present; otherwise English. For suggested mode, emphasise confirming jurisdiction on official websites.

### FIRST_POLICE_CONTACT (mandatory when **police / FIR** is the primary route — include these ideas across 3–5 separate strings)
- Prefer visiting the **nearest appropriate police chowki / outpost** when it is **geographically much closer** for first information or to learn **where to file**; otherwise go to the **jurisdictional police station** (SHO) as in the letter.
- Explain in plain language that **chowki** is often a smaller post; the **main station** is where many **FIRs and formal follow-up** are processed — wording must stay **non-dogmatic** (practice varies by place).
- **Telephone / contact:** do **not** make up any local number. Tell the user to note the **displayed** contact from the **chowki or police station board**, the **state police / district police official website**, or use **112** (all-India emergency — describe briefly as emergency routing) for **urgent** police/medical help as commonly publicised. Ask them to **write** the number they **verified** on the printed form (fifth line of **## PRINT_FILL_HEADER** when used).
- Carry **ID** and any **evidence**; keep a **copy** of the complaint when possible.

### RESPONSE_LANGUAGE override (when appended to this system message)
If a **## RESPONSE_LANGUAGE** block appears after these rules, **document**, **explanation**, and **next_steps** MUST all comply—including the full formal letter (To/Subject/body/closing). Do not leave **document** in English while localizing the other fields. URLs, email addresses, and standard abbreviations (e.g. FIR, SHO, CrPC, BNSS) may appear as usual; surrounding sentences must follow the requested language.

## Output
Valid JSON only: {"document": "...", "explanation": "...", "next_steps": [...]}
"""

STRICT_REGEN_ADDON = (
    "\n\nREGENERATION: Your previous draft may have violated rules. "
    "Remove ANY invented government phone numbers, emails, or street addresses. "
    "Follow AUTHORITY_BLOCK_JSON strictly. "
    "If police-primary: fix **## POLICE_COMPLAINT_LAYOUT** violations — no user locality (chaurah/chowk/railway/bus stand) "
    "as police station name; use jurisdictional wording from layout **A** or **C**. Remove garbled lines like "
    "*Police Station (Station House Officer / SHO)*. Apply **## DOCUMENT_WHITESPACE**. For vehicle theft, include vehicle "
    "description and time-window subsections. No complainant first name in signature line when print-fill header is used. "
    "Apply **## PRINT_FILL_FOOTER** at the very end (repeat of header handwriting lines; nothing after)."
)

QUALITY_REGEN_ADDON = (
    "\n\nQUALITY PASS: Improve the draft. Ensure **## PRINT_FILL_HEADER** is at the very top of `document` "
    "with blank lines only (no auto-filled user contact). For police-primary routes: also include the **fifth** "
    "handwriting line (official contact from verified sources). For criminal/police matters: follow **## POLICE_COMPLAINT_LAYOUT** — "
    "**never** put chaurah / chowk / crossing / locality / railway station / market name **inside or after** "
    "\"Police Station\" as the station's name (forbidden: *Police Station (…Chaurah)*). Use layout **A** or **C** from that section. "
    "Separate **locus** from **jurisdictional PS**. If user is a **witness**, use **informant** framing. "
    "Include facts → narrative → prayer with copy/ack request; date, time, place, injuries if any. "
    "Vehicle theft: vehicle details + parking time + manner + witnesses subsections. "
    "No redundant [Your Name] or user's first name in signature if print header exists. "
    "End `document` with **## PRINT_FILL_FOOTER** (repeat header lines; last text). "
    "Use **## DOCUMENT_WHITESPACE** between To / Subject / body / signature / footer. "
    "To the Station House Officer; do not use District Collector as sole addressee for cognizable offences. "
    "`next_steps` must follow **## FIRST_POLICE_CONTACT** (chowki vs thana, no invented phone numbers, 112/board/website) "
    "when police is primary. "
    "Polish prose: clear sentences, conventional legal courtesy, no redundant rhetoric; align layout with "
    "## FORUM_DRAFTING_STYLE for the active category."
)

AUTHORITY_ALIGNMENT_REGEN_ADDON = (
    "\n\nAUTHORITY VIOLATION FIX: Your draft broke AUTHORITY_LOCK. "
    "Re-draft with primary addressee Station House Officer / Police Station; FIR narrative; cognizable framing; "
    "explicit request to register an FIR under applicable law (phrase this in the same language/script as "
    "## RESPONSE_LANGUAGE when that section exists; otherwise English). "
    "Keep **document**, **explanation**, and **next_steps** in that same language when ## RESPONSE_LANGUAGE exists. "
    "Do NOT address Labour Commissioner, Consumer Commission, Collector, or Tehsildar as the primary recipient."
)

HYBRID_AUTHORITY_ALIGNMENT_REGEN_ADDON = (
    "\n\nHYBRID CIVIL–CRIMINAL FIX: The case requires BOTH forums in one document with clear headings.\n"
    "Include (A) Police Station / SHO — FIR or written complaint for force, threat, trespass, or cognizable facts.\n"
    "Include (B) Civil Court / District Court — possession, injunction, or partition outline.\n"
    "Do NOT use Tehsildar or revenue office as the sole addressee; do not omit the police or civil court section.\n"
    "When ## RESPONSE_LANGUAGE exists, write all sections in that language/script (headings may mirror the same language)."
)


def _formatter_language_addon(response_language: str) -> str:
    rl = (response_language or "en").strip().lower().replace("-", "_")
    if rl == "hi_latn":
        return (
            "\n\n## RESPONSE_LANGUAGE (mandatory — Hindi in Roman / Latin script only)\n"
            "Write **document**, **explanation**, and **next_steps** entirely in **Roman Hindi** (Hinglish-style "
            "transliteration). **Do not** use Devanagari anywhere in the JSON values. "
            "Formal letter: use Roman Hindi for To/Subject/salutation/body/closing (e.g. \"Seva mein\", \"Vishay:\", "
            "\"Thanadhayaksh\", \"FIR darj karne ka anurodh\"). "
            "**## PRINT_FILL_HEADER** labels must also be Roman Hindi (e.g. \"Tithi:\", \"Naam (shikayatakarta):\", "
            "\"Mobile number:\", \"Poora postal pata:\"). For police-primary drafts, a fifth line: "
            "\"Aadhikarik sampark (board/website/112 se likhen — random number na guess karein):\" with underscores. "
            "At the **end** of `document` after Yours faithfully / Informant: **## PRINT_FILL_FOOTER** — **repeat** the same five (or four if non-police) lines as **## PRINT_FILL_HEADER** (Tithi, Naam, Mobile, Poora postal pata, Aadhikarik line if police); nothing after that block. "
            "Keep URLs, emails, and tokens like FIR, SHO, CrPC, BNSS as written; user sentences must stay Roman Hindi.\n"
        )
    if rl != "hi":
        return ""
    return (
        "\n\n## RESPONSE_LANGUAGE (mandatory — Hindi, Devanagari)\n"
        "Write **document**, **explanation**, and **next_steps** entirely in **Hindi (Devanagari)**. "
        "The formal **document** must be a full Hindi letter (प्रति/सेवा में, विषय, सम्मानित अभिवादन, मुख्य भाग, समापन) — "
        "not English with Hindi UI. "
        "**## PRINT_FILL_HEADER** की पंक्तियाँ भी देवनागरी में हों (जैसे: तिथि:, नाम (शिकायतकर्ता/आवेदक):, मोबाइल नंबर:, पूरा डाक पता:). "
        "पुलिस-प्राथमिक मसौदे में पाँचवीं पंक्ति: आधिकारिक संपर्क (नोटिस बोर्ड/वेबसाइट/आपात 112 से — अनुमान न करें): — रेखाएँ खाली। "
        "Statute/portfolio names may stay in common Latin forms (e.g. FIR, SHO, CrPC, BNSS, India Code) where standard; "
        "all explanatory prose around them must be Hindi.\n"
        "**## PRINT_FILL_FOOTER:** पत्र के **अंत** में (समापन के तुरंत बाद) **## PRINT_FILL_HEADER** जैसी ही पंक्तियाँ दोहराएँ — चार हमेशा; पुलिस-प्राथमिक मार्ग पर पाँचवीं भी; उसके बाद `document` में कुछ न लिखें।\n"
        "\n## HINDI_POLICE_LETTER_STYLE (केवल जब **पुलिस / FIR** प्राथमिक मार्ग हो — ग्रामीण/शहरी सामान्य प्रारूप)\n"
        "ऊपर **## PRINT_FILL_HEADER** (तिथि/नाम/मोबाइल/पता) के बाद, पत्र को अक्सर इस क्रम में लिखें: "
        "(1) 'दिनांक / Date:' एक पंक्ति (दोनों लेबल acceptable) जहाँ उपयुक्त हो; "
        "(2) 'सेवा में,' / 'प्रति', फिर 'थाना प्रभारी महोदय,'; "
        "(3) 'पुलिस थाना __________ (उदा. जिला/क्षेत्र के अनुसार नाम)' — **दृश्य (चौराहा/स्टेशन) को थाने का नाम मत बनाएँ**; "
        "(4) 'जनपद __________, __________ (राज्य)'; "
        "(5) 'विषय: …' स्पष्ट व आसान; "
        "(6) 'महोदय,' तथा 'सविनय निवेदन है कि…' — तिथि/समय/स्थान, घटनाक्रम, प्रार्थना (जैसे FIR दर्ज कर जाँच); "
        "(7) समापन: 'धन्यवाद' / 'भवदীয়,' + छोटा समापन (उदा. शिकायतकर्ता/सूचनाकर्ता); फिर **## PRINT_FILL_FOOTER** — ऊपर **## PRINT_FILL_HEADER** जैसी ही पंक्तियाँ (तिथि, नाम, मोबाइल, पता, [पाँचवीं पुलिस-मार्ग]) पत्र के **अंत** में हाथ से भरने हेतु; `document` की अंतिम पंक्तियाँ।\n"
    )


def _maybe_override_for_multi_intent(
    taxonomy: LegalClassification,
    classifier_meta: ClassifierMeta,
    multi: MultiIntentResult,
) -> tuple[LegalClassification, ClassifierMeta]:
    """When LLM + keywords say criminal is primary but rules matched labour only."""
    intents = multi.get("intents") or []
    if len(intents) < 2:
        return taxonomy, classifier_meta
    if multi.get("primary") == "criminal" and classifier_meta.get("router_intent") == "salary_issue":
        c_lab = max(float(classifier_meta.get("confidence") or 0), 0.86)
        return (
            LegalClassification(
                issue_type="police",
                severity="high",
                jurisdiction_type="district",
                sub_type="labour_with_threat",
            ),
            ClassifierMeta(
                domain="criminal",
                sub_type="labour_with_threat",
                category="criminal",
                fine_intent="composite_labour_criminal",
                confidence=c_lab,
                confidence_score=c_lab,
                router_intent="criminal_police",
            ),
        )
    return taxonomy, classifier_meta


def get_llm_clarifications(
    user_input: str,
    *,
    classifier_meta: ClassifierMeta,
    taxonomy_ui: LegalClassification,
    issue_profile: IssueProfile,
    skip_clarification: bool,
    response_language: str = "en",
) -> dict[str, Any] | None:
    """
    LLM clarification agent output merged into clarification payloads.
    Does not change classifier output — only supplies questions for the user.
    """
    use, soft = should_use_llm_clarification(
        classifier_meta,
        taxonomy_ui,
        issue_profile,
        user_input,
        skip_clarification=skip_clarification,
    )
    if not use:
        return None
    flags = compute_missing_entity_flags(user_input, classifier_meta, taxonomy_ui, issue_profile)
    ambiguous = ambiguous_intent_for_llm_clarification(classifier_meta, taxonomy_ui, issue_profile)
    conf = max(float(classifier_meta.get("confidence") or 0), float(classifier_meta.get("confidence_score") or 0))
    result = run_llm_clarification_agent(
        user_input,
        domain=str(classifier_meta.get("domain") or ""),
        sub_type=str(taxonomy_ui.get("sub_type") or ""),
        issue_type=str(taxonomy_ui.get("issue_type") or ""),
        router_intent=str(classifier_meta.get("router_intent") or ""),
        confidence=conf,
        is_hybrid=bool(classifier_meta.get("is_hybrid")),
        missing_entities=flags,
        ambiguous_intent=ambiguous,
        soft_optional=soft,
        priority_level=str(classifier_meta.get("priority_level") or "").strip() or None,
        hybrid_police_primary=bool(classifier_meta.get("hybrid_police_primary")),
        response_language=response_language,
    )
    qs = list(result.get("questions") or [])
    serializable: list[dict[str, Any]] = []
    for q in qs:
        serializable.append(
            {
                "id": str(q.get("id") or ""),
                "question": str(q.get("question") or ""),
                "type": str(q.get("type") or "single_choice"),
                "options": list(q.get("options") or []),
                "required": bool(q.get("required", True)),
            }
        )
    if not serializable:
        return None
    return {
        "clarification_agent_questions": serializable,
        "clarifying_questions": agent_questions_to_legacy_strings(qs),
        "clarification_optional": soft,
        "clarification_agent_reason": str(result.get("reason") or ""),
        "clarification_agent_confidence_hint": float(result.get("confidence_hint") or 0.0),
    }


def _clarification_early_return_if_needed(
    user_input: str,
    *,
    classifier_meta: ClassifierMeta,
    taxonomy_ui: LegalClassification,
    issue_profile: IssueProfile,
    interpretation: Any,
    city: str | None,
    response_language: str = "en",
) -> dict[str, Any] | None:
    """Deterministic structured clarification, else conversational LLM questions, else None."""
    if law_order_safety_gate_needed(classifier_meta, user_input):
        return _build_clarification_response(
            clarification_safety_intro(response_language),
            classifier_meta=classifier_meta,
            taxonomy=taxonomy_ui,
            interpretation=interpretation,
            clarification_options=[],
            clarification_points=[],
            clarifying_questions=list(law_order_safety_questions(response_language)),
            city=city if isinstance(city, str) else None,
            response_language=response_language,
        )
    needed, clar_q, clar_opts, clar_pts = needs_clarification(
        classifier_meta, taxonomy_ui, issue_profile, user_input
    )
    if needed and clar_q:
        return _build_clarification_response(
            clar_q,
            classifier_meta=classifier_meta,
            taxonomy=taxonomy_ui,
            interpretation=interpretation,
            clarification_options=clar_opts,
            clarification_points=clar_pts,
            city=city if isinstance(city, str) else None,
            response_language=response_language,
        )
    bundle = get_llm_clarifications(
        user_input,
        classifier_meta=classifier_meta,
        taxonomy_ui=taxonomy_ui,
        issue_profile=issue_profile,
        skip_clarification=False,
        response_language=response_language,
    )
    if bundle and bundle.get("clarification_agent_questions"):
        intro = (
            clarification_intro_llm_optional(response_language)
            if bundle.get("clarification_optional")
            else clarification_intro_llm_required(response_language)
        )
        return _build_clarification_response(
            intro,
            classifier_meta=classifier_meta,
            taxonomy=taxonomy_ui,
            interpretation=interpretation,
            clarification_options=[],
            clarification_points=[],
            clarifying_questions=list(bundle.get("clarifying_questions") or []),
            clarification_agent_questions=list(bundle.get("clarification_agent_questions") or []),
            clarification_optional=bool(bundle.get("clarification_optional")),
            clarification_agent_reason=str(bundle.get("clarification_agent_reason") or ""),
            clarification_agent_confidence_hint=float(bundle.get("clarification_agent_confidence_hint") or 0.0),
            city=city if isinstance(city, str) else None,
            response_language=response_language,
        )
    intent = build_clarification_intent(classifier_meta, taxonomy_ui, issue_profile)
    if should_ask_clarification(intent, classifier_meta, user_input):
        qs = generate_clarification_questions(user_input, intent, response_language=response_language)
        intro = clarification_intro_conversational(response_language)
        return _build_clarification_response(
            intro,
            classifier_meta=classifier_meta,
            taxonomy=taxonomy_ui,
            interpretation=interpretation,
            clarification_options=[],
            clarification_points=[],
            clarifying_questions=qs,
            city=city if isinstance(city, str) else None,
            response_language=response_language,
        )
    return None


def maybe_clarification_only_response(
    user_input: str,
    prefetch: IntentPrefetch,
    *,
    city: str | None,
    response_language: str = "en",
) -> dict[str, Any] | None:
    """Used by streaming endpoint after prefetch — same rules as sync `generate_legal_response` clarification."""
    return _clarification_early_return_if_needed(
        user_input.strip(),
        classifier_meta=prefetch.classifier_meta,
        taxonomy_ui=prefetch.taxonomy_ui,
        issue_profile=prefetch.issue_profile,
        interpretation=prefetch.interpretation,
        city=city,
        response_language=response_language,
    )


def _build_clarification_response(
    question: str,
    *,
    classifier_meta: ClassifierMeta,
    taxonomy: LegalClassification,
    interpretation: Any,
    clarification_options: list[str] | None = None,
    clarification_points: list[dict[str, Any]] | None = None,
    clarifying_questions: list[str] | None = None,
    clarification_agent_questions: list[dict[str, Any]] | None = None,
    clarification_optional: bool = False,
    clarification_agent_reason: str = "",
    clarification_agent_confidence_hint: float | None = None,
    city: str | None = None,
    response_language: str = "en",
) -> dict[str, Any]:
    """Minimal payload — frontend shows `clarification_question` instead of full draft."""
    opts = [str(x).strip() for x in (clarification_options or []) if str(x).strip()]
    pts_in = clarification_points or []
    pts: list[dict[str, Any]] = []
    for p in pts_in:
        if not isinstance(p, dict):
            continue
        lab = str(p.get("label") or "").strip()
        oraw = p.get("options")
        if not lab or not isinstance(oraw, list):
            continue
        olist = [str(x).strip() for x in oraw if str(x).strip()][:4]
        if len(olist) < 2:
            continue
        pts.append({"label": lab[:220], "options": olist})
    has_pts = bool(pts)
    agent_raw = clarification_agent_questions or []
    agent_qs: list[dict[str, Any]] = []
    for item in agent_raw:
        if not isinstance(item, dict):
            continue
        qid = str(item.get("id") or "").strip()
        qtext = str(item.get("question") or "").strip()
        typ = str(item.get("type") or "single_choice")
        oraw = item.get("options")
        olist = [str(x).strip() for x in (oraw if isinstance(oraw, list) else []) if str(x).strip()][:6]
        if not qtext:
            continue
        if typ == "yes_no":
            olist = list(yes_no_labels(response_language))
        elif len(olist) < 2:
            continue
        agent_qs.append(
            {
                "id": qid[:64] or f"q_{len(agent_qs)}",
                "question": qtext[:400],
                "type": typ if typ in ("single_choice", "yes_no") else "single_choice",
                "options": olist,
                "required": bool(item.get("required", True)),
            }
        )
    cqs = [str(x).strip() for x in (clarifying_questions or []) if str(x).strip()]
    if agent_qs and not cqs:
        cqs = [str(x.get("question") or "") for x in agent_qs if x.get("question")]
    has_agent = bool(agent_qs)
    has_cqs = len(cqs) >= 2 or (has_agent and len(cqs) >= 1)
    next_hint = (
        clarification_next_hint_select_points(response_language)
        if has_pts
        else (
            clarification_next_hint_optional_agent(response_language)
            if clarification_optional and has_agent
            else (
                clarification_next_hint_answer_each(response_language)
                if has_cqs
                else (
                    clarification_next_hint_choose_opts(response_language)
                    if opts
                    else clarification_next_hint_reply_free(response_language)
                )
            )
        )
    )
    return finalize_legal_response(
        {
            "document": "",
            "draft": "",
            "explanation": clarification_more_detail_explanation(response_language),
            "next_steps": [next_hint],
            "clarification_needed": True,
            "clarification_question": question,
            "clarification_options": opts,
            "clarification_points": pts,
            "clarifying_questions": cqs if has_cqs else [],
            "clarification_agent_questions": agent_qs,
            "clarification_optional": clarification_optional,
            "clarification_agent_reason": (clarification_agent_reason or "")[:500],
            "clarification_agent_confidence_hint": clarification_agent_confidence_hint,
            "urgency_banner": None,
            "urgency_level": "low",
            "issue_profile": {
                "category": "unknown",
                "severity": "low",
                "intent": "information",
                "keywords": [],
                "urgency": "normal",
            },
            "official_links": links_for_category_slug("unknown"),
            "multi_intent": None,
            "generation_score": None,
            "routing_summary": None,
            "is_verified": False,
            "legal_overview": None,
            "authority": {
                "status": "unknown",
                "primary": "",
                "secondary": "",
                "guidance": question,
            },
            "authority_compact": {
                "status": "none",
                "name": "",
                "source": "",
                "warning": (
                    clarification_authority_warning_optional(response_language)
                    if clarification_optional
                    else clarification_authority_warning_required(response_language)
                ),
            },
            "authority_disclaimer": authority_disclaimer(response_language),
            "authority_search_note": None,
            "legal_classification": {
                "domain": classifier_meta.get("domain", ""),
                "sub_type": taxonomy.get("sub_type", ""),
                "category": classifier_meta["category"],
                "fine_intent": classifier_meta["fine_intent"],
                "classifier_confidence": classifier_meta["confidence"],
                "router_intent": classifier_meta["router_intent"],
                "entities": interpretation["entities"],
                "intent_hint": interpretation["intent_hint"],
                "context": interpretation["context"],
                "issue_type": taxonomy["issue_type"],
                "severity": taxonomy["severity"],
                "jurisdiction_type": taxonomy["jurisdiction_type"],
                "authority_primary": "",
                "authority_secondary": "",
                "issue_profile": None,
            },
            "jurisdiction": None,
            "trust_summary": {"authority_routing": "unknown", "law_knowledge": "unknown"},
            "trust_report": {"score": 0.0, "reason": "clarification_pending"},
            "verifier": {
                "accuracy_score": 0.0,
                "hallucination_risk": "n/a",
                "authority_validity": False,
                "fix_required": False,
            },
            "legal_explanation": None,
            "procedure_steps": None,
            "step_by_step_procedure": None,
            "legal_references": [],
            "retrieved_laws": [],
            "confidence_score": None,
            "rag_grounding_label": None,
            "authority_summary": None,
            "authority_hierarchy": build_authority_hierarchy(
                str(classifier_meta.get("router_intent") or ""),
                city,
                response_language=response_language,
            ),
        }
    )


def _as_severity(s: str) -> Severity:
    if s in ("low", "medium", "high"):
        return s  # type: ignore[return-value]
    return "medium"


def _merge_urgency_next_steps(
    issue_profile: IssueProfile,
    issue_type: str,
    steps: list[str],
    *,
    classifier_meta: ClassifierMeta | None = None,
    taxonomy: LegalClassification | None = None,
    response_language: str = "en",
) -> list[str]:
    urgent_meta = classifier_meta and str(classifier_meta.get("fine_intent") or "") in (
        "sexual_offence",
        "missing_person",
        "theft",
        "labour_with_criminal_threat",
    )
    urgent_sub = classifier_meta and str(classifier_meta.get("sub_type") or "") in (
        "sexual_offence",
        "missing_person",
        "assault",
        "fraud_general",
    )
    serious_fraud = (
        taxonomy
        and str(taxonomy.get("issue_type") or "") == "fraud"
        and str(taxonomy.get("severity") or "") == "high"
    )
    if (
        issue_profile.get("urgency") != "high"
        and issue_profile.get("intent") != "emergency"
        and not urgent_meta
        and not urgent_sub
        and not serious_fraud
    ):
        return steps
    head = list(urgency_next_steps_prefix(response_language))
    if issue_type == "cyber" or issue_profile.get("category") == "cyber":
        head.insert(1, cyber_urgency_insert(response_language, CYBER_CRIME_PORTAL))
    return head + steps


def _block_generation_extreme_uncertainty(meta: ClassifierMeta) -> bool:
    """Do not draft when the classifier is very weak on a generic bucket (safety fallback)."""
    conf = max(float(meta.get("confidence") or 0), float(meta.get("confidence_score") or 0))
    if conf >= 0.35:
        return False
    if str(meta.get("router_intent") or "") != "general_issue":
        return False
    return bool(meta.get("needs_llm_fallback"))


def _regenerate_until_authority_aligned(
    client: OpenAI,
    user_message: str,
    data: dict[str, Any],
    *,
    classifier_meta: ClassifierMeta,
    taxonomy_ui: LegalClassification,
    authority_block: dict[str, Any],
    language_addon: str = "",
) -> None:
    """Up to 2 extra formatter passes if draft violates deterministic authority routing (mutates data)."""
    for _ in range(2):
        doc = str(data.get("document") or "")
        bad_doc, _ = document_violates_authority_alignment(
            doc,
            classifier_meta=classifier_meta,
            taxonomy=taxonomy_ui,
        )
        bad_block, _ = authority_block_suggested_mismatch(
            authority_block,
            classifier_meta=classifier_meta,
            taxonomy=taxonomy_ui,
        )
        if not bad_doc and not bad_block:
            return
        align_addon = (
            HYBRID_AUTHORITY_ALIGNMENT_REGEN_ADDON
            if classifier_meta.get("is_hybrid")
            else AUTHORITY_ALIGNMENT_REGEN_ADDON
        )
        try:
            new = _run_formatter(
                client,
                user_message,
                strict_addon=STRICT_REGEN_ADDON + align_addon,
                language_addon=language_addon,
            )
            data["document"] = new.get("document", "")
            data["explanation"] = new.get("explanation", "")
            data["next_steps"] = new.get("next_steps", [])
        except Exception:
            return


def _strip_accidental_json_document(text: str) -> str:
    t = text.strip()
    if t.startswith("{") and '"document"' in t:
        try:
            parsed = json.loads(t)
            if isinstance(parsed, dict) and isinstance(parsed.get("document"), str):
                return str(parsed["document"]).strip()
        except json.JSONDecodeError:
            pass
    return text


def _sanitize_garbled_police_station_line(text: str) -> str:
    """
    Some model drafts still emit invalid lines like:
    Police Station (Station House Officer — SHO) — FIR or written complaint (Jhansi Medical),
    Replace with layout **A** third line (jurisdictional police station sentence).
    """
    replacement = (
        "The police station having territorial jurisdiction over the area where the incident described below occurred,"
    )
    lines = text.split("\n")
    out: list[str] = []
    for line in lines:
        s = line.strip()
        if not s:
            out.append(line)
            continue
        low = s.lower()
        if not low.startswith("police station"):
            out.append(line)
            continue
        if "(" not in s:
            out.append(line)
            continue
        # Garbled: SHO / Station House Officer / routing blurbs inside "Police Station (...)"
        if (
            "station house officer" in low
            or re.search(r"\bsho\b", low)
            or "fir or written" in low
        ):
            out.append(replacement)
            continue
        out.append(line)
    return "\n".join(out)


def _normalize_document_spacing(text: str) -> str:
    text = _strip_accidental_json_document(text)
    text = re.sub(r"\r\n", "\n", text)
    text = _sanitize_garbled_police_station_line(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _build_user_blob(user_input: str, user_details: dict[str, str | None] | None) -> str:
    user_details = user_details or {}
    lines: list[str] = []
    if user_details.get("full_name"):
        lines.append(f"Full name (for the letter): {user_details['full_name']}")
    if user_details.get("address"):
        lines.append(f"Postal address: {user_details['address']}")
    fc = user_details.get("city")
    lines.append(f"city_from_form: {fc if fc else '(not provided)'}")
    if user_details.get("phone"):
        lines.append(f"Phone: {user_details['phone']}")
    if user_details.get("email"):
        lines.append(f"Email: {user_details['email']}")

    details_block = "USER CONTEXT\n" + ("\n".join(lines) if lines else "USER CONTEXT\n(city_from_form not provided)")

    return (
        f"{details_block}\n\n---\n\nLegal issue described by the user:\n\n{user_input.strip()}"
    )


def _run_formatter(
    client: OpenAI,
    user_message: str,
    *,
    strict_addon: str = "",
    language_addon: str = "",
) -> dict[str, Any]:
    sys_content = FORMATTER_SYSTEM_PROMPT + language_addon + strict_addon
    final = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": sys_content},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
        temperature=0.35,
    )
    raw = final.choices[0].message.content
    if not raw:
        raise RuntimeError("Empty response from model")
    return json.loads(raw)


def generate_legal_response(
    user_input: str,
    user_details: dict[str, str | None] | None = None,
    *,
    _intent_prefetch: IntentPrefetch | None = None,
    skip_clarification: bool = False,
    response_language: str = "en",
) -> dict[str, Any]:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not configured")

    user_details = user_details or {}
    city = user_details.get("city")

    if _intent_prefetch is not None:
        interpretation = _intent_prefetch.interpretation
        taxonomy = _intent_prefetch.taxonomy
        classifier_meta = _intent_prefetch.classifier_meta
        multi_intent_result = _intent_prefetch.multi_intent_result
        issue_profile = _intent_prefetch.issue_profile
        taxonomy_ui = _intent_prefetch.taxonomy_ui
    else:
        interpretation, taxonomy, classifier_meta = classify_intent_pipeline(user_input, city=city)
        multi_intent_result = detect_multi_intent(user_input, taxonomy, classifier_meta)
        taxonomy, classifier_meta = _maybe_override_for_multi_intent(
            taxonomy, classifier_meta, multi_intent_result
        )
        taxonomy, classifier_meta = apply_hybrid_civil_criminal_overlay(
            user_input.strip(), taxonomy, classifier_meta
        )
        taxonomy, classifier_meta = apply_priority_override(
            taxonomy, user_input.strip(), classifier_meta
        )
        taxonomy, classifier_meta = apply_law_and_order_land_hybrid_merge(
            user_input.strip(), taxonomy, classifier_meta
        )
        issue_profile = classify_issue_enriched(user_input, taxonomy, classifier_meta)
        taxonomy_ui = {
            "issue_type": taxonomy["issue_type"],
            "severity": _as_severity(str(issue_profile.get("severity") or taxonomy["severity"])),
            "jurisdiction_type": taxonomy["jurisdiction_type"],
            "sub_type": taxonomy.get("sub_type") or "unspecified",
        }

    if not skip_clarification:
        early = _clarification_early_return_if_needed(
            user_input.strip(),
            classifier_meta=classifier_meta,
            taxonomy_ui=taxonomy_ui,
            issue_profile=issue_profile,
            interpretation=interpretation,
            city=city if isinstance(city, str) else None,
            response_language=response_language,
        )
        if early is not None:
            return early
        if _block_generation_extreme_uncertainty(classifier_meta):
            qs = list(classifier_meta.get("phase6_pipeline_questions") or [])
            if len(qs) < 2:
                qs = extreme_uncertainty_clarifying_questions(response_language)
            return _build_clarification_response(
                extreme_uncertainty_clarification_intro(response_language),
                classifier_meta=classifier_meta,
                taxonomy=taxonomy_ui,
                interpretation=interpretation,
                clarification_options=[],
                clarification_points=[],
                clarifying_questions=qs,
                city=city if isinstance(city, str) else None,
                response_language=response_language,
            )

    is_hybrid_case = bool(classifier_meta.get("is_hybrid"))
    generation_mode = "EMERGENCY_WITH_DRAFT" if bool(classifier_meta.get("is_emergency")) else "NORMAL"
    use_emergency_template = generation_mode == "EMERGENCY_WITH_DRAFT"
    router_result = route_case(
        classifier_meta["router_intent"],
        interpretation["entities"],
        city,
        category=classifier_meta["category"],
        hybrid_civil_criminal=is_hybrid_case,
        priority_level=str(classifier_meta.get("priority_level") or "").strip() or None,
        hybrid_police_primary=bool(classifier_meta.get("hybrid_police_primary")),
    )
    verified, meta = resolve_verified_authority(
        user_input,
        city,
        router_intent=str(classifier_meta.get("router_intent") or "") or None,
        domain=str(classifier_meta.get("domain") or "") or None,
    )
    meta["legal_classification"] = taxonomy_ui
    meta["classifier_meta"] = classifier_meta
    meta["interpretation"] = interpretation

    authority_block = build_unified_authority_block(
        verified=verified,
        taxonomy=taxonomy_ui,
        city=city,
        router_result=router_result,
        hybrid_civil_criminal=is_hybrid_case,
        hybrid_police_primary=bool(classifier_meta.get("hybrid_police_primary")),
        response_language=response_language,
    )

    if classifier_meta.get("needs_llm_fallback"):
        log_llm_fallback_case(
            user_input,
            classifier_meta.get("llm_fallback_raw")
            if isinstance(classifier_meta.get("llm_fallback_raw"), dict)
            else None,
            router_result,
        )

    _crisis_triage = crisis_triage_lock(
        classifier_meta, taxonomy_ui, user_input=(user_input or "").strip() or None
    )
    if _crisis_triage:
        companion = build_crisis_triage_companion_payload(authority_block=authority_block)
    else:
        rag_result = run_strict_rag_pipeline(user_input, str(taxonomy_ui["issue_type"]), top_k=8)
        companion = build_legal_companion_payload(
            user_input=user_input,
            city=city,
            taxonomy=taxonomy_ui,
            authority_block=authority_block,
            rag_result=rag_result,
            response_language=response_language,
        )
    companion_json = json.dumps(companion, ensure_ascii=False)

    trust_is_verified = verified is not None
    trust_score = (
        float(authority_block.get("trust_score") or 0.0)
        if authority_block.get("status") == "verified"
        else 0.0
    )

    classification_json = json.dumps(taxonomy_ui, ensure_ascii=False)
    issue_profile_payload = {
        "category": issue_profile.get("category"),
        "severity": issue_profile.get("severity"),
        "intent": issue_profile.get("intent"),
        "keywords": issue_profile.get("keywords") or [],
        "urgency": issue_profile.get("urgency"),
        "primary_category": multi_intent_result.get("primary"),
        "secondary_categories": multi_intent_result.get("secondaries") or [],
        "multi_intent_split": multi_intent_result.get("confidence_split"),
    }
    issue_profile_json = json.dumps(issue_profile_payload, ensure_ascii=False)
    official_link_list = links_for_category_slug(str(issue_profile.get("category") or "unknown"))
    if _crisis_triage:
        official_link_list = []
    official_links_json = json.dumps(official_link_list, ensure_ascii=False)
    interpretation_json = json.dumps(
        {
            "entities": interpretation["entities"],
            "intent_hint": interpretation["intent_hint"],
            "context": interpretation["context"],
        },
        ensure_ascii=False,
    )
    deterministic_json = json.dumps(classifier_meta, ensure_ascii=False)
    jurisdiction_router_json = json.dumps(
        {
            "primary": router_result["primary_authority"],
            "secondary": router_result["secondary_authority"],
            "fallback_path": router_result["fallback_path"],
            "routing_steps": router_result["routing_steps"],
            "jurisdiction_reason": router_result["jurisdiction_reason"],
            "is_hybrid_civil_criminal": is_hybrid_case,
        },
        ensure_ascii=False,
    )
    authority_json = json.dumps(authority_block, ensure_ascii=False)

    multi_intent_json = json.dumps(dict(multi_intent_result), ensure_ascii=False)
    skip_full_generation = False
    alert: str | None = None
    note: str | None = None
    safety_tip: str | None = None
    gen_score = 7.0

    if use_emergency_template:
        _rl = (response_language or "en").strip().lower().replace("-", "_")
        _lang_hi_deva = _rl == "hi"
        _lang_hi_latn = _rl == "hi_latn"
        skip_full_generation = True
        if _lang_hi_deva:
            alert = "⚠️ तत्काल खतरा। अभी 112 डायल करें या निकटतम पुलिस थाने जाएँ।"
        elif _lang_hi_latn:
            alert = "⚠️ Turant khatra. Abhi 112 dial karein ya nazdik police thane jayein."
        else:
            alert = "⚠️ Immediate danger detected. Call 112 or go to nearest police station NOW."
        d_label, st_label = _district_state_labels(city)
        if _lang_hi_deva:
            district_lbl = ", ".join(p for p in (d_label, st_label) if p) or "[ज़िला दर्ज करें]"
        elif _lang_hi_latn:
            district_lbl = ", ".join(p for p in (d_label, st_label) if p) or "[Zila darj karein]"
        else:
            district_lbl = ", ".join(p for p in (d_label, st_label) if p) or "[District]"
        loc = next(
            (e for e in (interpretation.get("entities") or []) if isinstance(e, str) and len(e.strip()) > 1),
            None,
        )
        location_hint = str(loc).strip() if loc else None
        ctx = parse_emergency_narrative_context(user_input, location_hint=location_hint)
        if bool(ctx.get("ongoing")):
            if _lang_hi_deva:
                safety_tip = "सुरक्षित दूरी बनाए रखें; शारीरिक हस्तक्षेप न करें।"
            elif _lang_hi_latn:
                safety_tip = "Surakshit doori banaye rakhen; sharirik hastakshshep na karen."
            else:
                safety_tip = "Stay at a safe distance. Do not try to intervene physically."
        incident_line = build_incident_line(ctx, language=_rl)
        if _lang_hi_deva:
            name_ph = "[अपना पूरा नाम]"
            ps_ph = "[थाना का नाम]"
        elif _lang_hi_latn:
            name_ph = "[Apna pura naam]"
            ps_ph = "[Thane ka naam]"
        else:
            name_ph = "[Your full name]"
            ps_ph = "[Police station name]"
        full_name = str(user_details.get("full_name") or "").strip() or name_ph
        document = render_emergency_fir_contextual(
            police_station=ps_ph,
            district=district_lbl,
            incident_line=incident_line,
            name=full_name,
            language=_rl,
        )
        if _lang_hi_deva:
            note = "सुरक्षा मिलने के बाद इस मसौदे का उपयोग करें।"
        elif _lang_hi_latn:
            note = "Suraksha milne ke baad is masaude ka upyog karen."
        else:
            note = "Use this draft after reaching safety."
        if bool(classifier_meta.get("is_hybrid")) and detect_land_context(user_input):
            if _lang_hi_deva:
                note += (
                    "\n\nपुलिस की तत्काल कार्रवाई के बाद, ज़रूरत पड़ने पर भूमि स्वामित्व के लिए सिविल मुकदमे "
                    "(कब्ज़ा/रोक/विभाजन) पर वकील की सलाह लें।"
                )
            elif _lang_hi_latn:
                note += (
                    "\n\nTurant police karvayi ke baad, zarurat padne par bhumi swami ke liye civil mukadma "
                    "(kabja/rok/vibhajan) par vakil ki salah len."
                )
            else:
                note += (
                    "\n\nAfter immediate police action, you may also need to file a civil case for land ownership "
                    "(possession, injunction, or partition as legally advised)."
                )
        if _lang_hi_deva:
            precision = (
                "यह हिंसा वाला गंभीर कानून-व्यवस्था मामला है। तत्काल पुलिस हस्तक्षेप ज़रूरी है।"
            )
        elif _lang_hi_latn:
            precision = (
                "Yah hinsa wala gambhir kanoon-vyavastha mamla hai. Turant police hastakshshep zaroori hai."
            )
        else:
            precision = (
                "This is a serious law-and-order issue involving violence. "
                "Police intervention is required immediately to control the situation."
            )
        explanation = cap_text_lines(precision, max_lines=4)
        next_steps: list[str] = []
        if safety_tip:
            next_steps.append(safety_tip)
        if _lang_hi_deva:
            next_steps.append(
                "सुरक्षित होने के बाद: निकटतम थाने जाएँ, इस मसौदे के साथ FIR/लिखित शिकायत दर्ज कराने में मदद माँगें।"
            )
        elif _lang_hi_latn:
            next_steps.append(
                "Surakshit hone ke baad: nazdik thane jayein, is masaude ke saath FIR/likhshit shikayat "
                "darj karane me madad mangein."
            )
        else:
            next_steps.append(
                "When safe: go to the nearest police station with this draft and request FIR registration help."
            )
        if _lang_hi_deva:
            next_steps.append("पहचान प्रमाण और फोटो/वीडियो/गवाह जैसा हो, साथ रखें।")
        elif _lang_hi_latn:
            next_steps.append(
                "Pehchan praman aur photo/video/gawah jaisa ho, saath rakhen."
            )
        else:
            next_steps.append(
                "Bring identity proof and any photos, videos, or witness details you may have."
            )
        if bool(classifier_meta.get("is_hybrid")) and detect_land_context(user_input):
            if _lang_hi_deva:
                next_steps.append(
                    "पुलिस कदमों के बाद: स्वामित्व विवाद में सिविल उपचार (वकील) पर विचार करें।"
                )
            elif _lang_hi_latn:
                next_steps.append(
                    "Police kadamon ke baad: swamitv vivad me civil upchar (vakil) par vichar karen."
                )
            else:
                next_steps.append(
                    "After police steps: consult an advocate for civil land remedies if ownership is disputed."
                )
        next_steps = dedupe_and_cap_next_steps(next_steps, max_steps=4)
        gen_score = 8.0
    else:
        hybrid_instruction = ""
        if is_hybrid_case and _crisis_triage:
            if bool(classifier_meta.get("hybrid_police_primary")):
                hybrid_instruction = (
                    "\n\n---\nHYBRID_CRISIS_MODE (mandatory — police route only in `document` body):\n"
                    "The case is hybrid (land + law & order) but CRISIS/SAFETY triage is active: ongoing violence and "
                    "police help come first. In `document`, include ONLY a single police/FIR request to the SHO — full "
                    "factual narrative; request for FIR. Do NOT add a second formal 'civil court' or 'injunction' "
                    "letter in `document`.\n"
                    "In `explanation` only (or as a 3–4 line paragraph after the police draft in `document`, not as a "
                    "separate court application), state briefly that land/possession/injunction is a **separate civil "
                    "remedy** the user can pursue **after** safety and police action, with an advocate and official sources.\n"
                )
            else:
                hybrid_instruction = (
                    "\n\n---\nHYBRID_CRISIS_MODE (mandatory — one police path in `document`):\n"
                    "Hybrid (civil + criminal) with crisis triage: in `document`, only the SHO / FIR or written complaint. "
                    "No full second civil-court application in the same `document` — at most one short 'Note' that civil "
                    "remedies (possession/injunction) are separate, with placeholder facts.\n"
                )
        elif is_hybrid_case:
            if bool(classifier_meta.get("hybrid_police_primary")):
                hybrid_instruction = (
                    "\n\n---\nHYBRID_CIVIL_CRIMINAL_CASE_POLICE_FIRST (mandatory — deterministic flag):\n"
                    "Law-and-order plus land/civil: police controls ongoing violence; civil court resolves ownership.\n"
                    "In `document`, use two clearly separated sections with headings IN THIS ORDER:\n"
                    "(1) OPTION A — POLICE COMPLAINT / FIR REQUEST — To the Station House Officer; factual narrative; "
                    "request for FIR or written complaint as applicable.\n"
                    "(2) OPTION B — CIVIL SUIT / INJUNCTION — To the Civil Court / District Court; possession, "
                    "injunction, or partition outline (placeholders where facts unknown).\n"
                    "Do NOT use Tehsildar or revenue office as the sole addressee. Do not merge sections without headings.\n"
                )
            else:
                hybrid_instruction = (
                    "\n\n---\nHYBRID_CIVIL_CRIMINAL_CASE (mandatory — deterministic flag, not LLM-invented):\n"
                    "The issue has BOTH civil remedies (possession, injunction, partition) AND a police route when "
                    "force, threat, trespass, कब्ज़ा-style occupation, or cognizable conduct is alleged.\n"
                    "In `document`, you MUST include two clearly separated sections with headings:\n"
                    "(1) OPTION A — POLICE COMPLAINT / FIR REQUEST — To the Station House Officer; factual narrative; "
                    "request for registration of FIR or written complaint as applicable.\n"
                    "(2) OPTION B — CIVIL SUIT / INJUNCTION — To the Civil Court / District Court; outline for possession "
                    "or injunction (placeholders where facts unknown).\n"
                    "Do NOT present Tehsildar or revenue office as the sole or exclusive forum. Do not merge the two "
                    "options into one letter without headings.\n"
                )
        crisis_formatter_addon = ""
        if _crisis_triage:
            crisis_formatter_addon = (
                "\n\n---\nCRISIS_SAFETY_MODE (mandatory — action first):\n"
                "The user may need immediate safety or police help. Keep `document` to a concise police complaint / "
                "FIR-style draft only. Keep `explanation` to at most 4 short lines. "
                "Return at most 3 short items in `next_steps` (safety, 112/police, evidence/preservation). "
                "Do not add long legal theory, wide civil-law alternatives, or academic background.\n"
            )
        if alleges_arson_or_fire_at_police_station(user_input):
            crisis_formatter_addon += (
                "\n\n---\nARSON_OR_ATTACK_ON_POLICE_STATION (mandatory):\n"
                "The user describes a fire, arson, or an extremely serious incident concerning a "
                "police station (thana). In `document`, do NOT use vague phrasing like "
                "'concerning police incident' or 'raised concerns'. State alleged facts in plain language: "
                "what happened to the police station (e.g. fire, attack), place, and date/time if the user "
                "gave them. Request registration of an FIR and investigation for the appropriate serious "
                "offences (use placeholders for IPC/BNSS section numbers if unknown). Match the tone to the "
                "gravity of harm to public property or a police installation.\n"
            )
        user_message = (
            f"{_build_user_blob(user_input, user_details)}\n\n"
            f"---\nLEGAL_CLASSIFICATION (taxonomy):\n{classification_json}\n\n"
            f"---\nINTERPRETATION_JSON:\n{interpretation_json}\n\n"
            f"---\nDETERMINISTIC_CLASSIFIER_META:\n{deterministic_json}\n\n"
            f"---\nMULTI_INTENT_JSON (primary wins for routing; secondaries are additional facets):\n{multi_intent_json}\n\n"
            f"---\nISSUE_PROFILE_JSON:\n{issue_profile_json}\n\n"
            f"---\nOFFICIAL_LINKS_JSON:\n{official_links_json}\n\n"
            f"---\nJURISDICTION_ROUTER_JSON:\n{jurisdiction_router_json}\n\n"
            f"---\nLEGAL_COMPANION_JSON:\n{companion_json}\n\n"
            f"---\nAUTHORITY_BLOCK_JSON:\n{authority_json}\n"
            f"{hybrid_instruction}{crisis_formatter_addon}"
        )

        client = OpenAI(api_key=settings.openai_api_key)
        lang_addon = _formatter_language_addon(response_language)

        try:
            data = _run_formatter(client, user_message, language_addon=lang_addon)
        except AuthenticationError as e:
            raise ValueError(
                "OpenAI rejected your API key (401). Create a new secret key at "
                "https://platform.openai.com/account/api-keys and set OPENAI_API_KEY in "
                "backend/.env with no extra spaces or characters. Restart the API server after saving."
            ) from e

        document = data.get("document", "")
        explanation = data.get("explanation", "")
        next_steps = data.get("next_steps", [])

        ok, _reason = approve_final_response(
            authority_api=authority_block,
            trust_is_verified=trust_is_verified,
            trust_score=trust_score,
        )
        if not ok:
            try:
                data = _run_formatter(
                    client,
                    user_message,
                    strict_addon=STRICT_REGEN_ADDON,
                    language_addon=lang_addon,
                )
                document = data.get("document", "")
                explanation = data.get("explanation", "")
                next_steps = data.get("next_steps", [])
            except Exception:
                pass

        try:
            gen_score, _gen_detail = evaluate_generation_output(
                document=str(document),
                issue_profile=issue_profile_payload,
                authority_block=authority_block,
                classifier_category=str(classifier_meta.get("category") or ""),
            )
        except Exception:
            pass
        if should_regenerate(gen_score):
            try:
                data = _run_formatter(
                    client,
                    user_message,
                    strict_addon=STRICT_REGEN_ADDON + QUALITY_REGEN_ADDON,
                    language_addon=lang_addon,
                )
                document = data.get("document", "")
                explanation = data.get("explanation", "")
                next_steps = data.get("next_steps", [])
                gen_score, _gen_detail = evaluate_generation_output(
                    document=str(document),
                    issue_profile=issue_profile_payload,
                    authority_block=authority_block,
                    classifier_category=str(classifier_meta.get("category") or ""),
                )
            except Exception:
                pass

        _alignment_bundle = {"document": document, "explanation": explanation, "next_steps": next_steps}
        _regenerate_until_authority_aligned(
            client,
            user_message,
            _alignment_bundle,
            classifier_meta=classifier_meta,
            taxonomy_ui=taxonomy_ui,
            authority_block=authority_block,
            language_addon=lang_addon,
        )
        document = str(_alignment_bundle.get("document") or "")
        explanation = str(_alignment_bundle.get("explanation") or "")
        next_steps = _alignment_bundle.get("next_steps", next_steps)

    if not isinstance(next_steps, list):
        next_steps = [str(next_steps)]
    else:
        next_steps = [str(s).strip() for s in next_steps if str(s).strip()]

    if not use_emergency_template:
        next_steps = _merge_urgency_next_steps(
            issue_profile,
            str(taxonomy_ui["issue_type"]),
            next_steps,
            classifier_meta=classifier_meta,
            taxonomy=taxonomy_ui,
            response_language=response_language,
        )

    _eval_meta: dict[str, Any] = {
        **dict(classifier_meta),
        "is_emergency": use_emergency_template,
        "crisis_triage": _crisis_triage,
    }
    document, explanation, next_steps = evaluate_response_bundle(
        document=str(document or ""),
        explanation=str(explanation or ""),
        next_steps=next_steps if isinstance(next_steps, list) else [],
        meta=_eval_meta,
        alert=alert if use_emergency_template else None,
    )

    urgent_banner_meta = str(classifier_meta.get("sub_type") or "") in (
        "sexual_offence",
        "missing_person",
    ) or str(classifier_meta.get("fine_intent") or "") in ("sexual_offence", "missing_person")
    urgency_banner = (
        alert
        if use_emergency_template and alert
        else (
            "⚠️ Urgent Action Required"
            if issue_profile.get("urgency") == "high"
            or issue_profile.get("intent") == "emergency"
            or urgent_banner_meta
            or (
                str(taxonomy_ui.get("issue_type") or "") == "fraud"
                and str(taxonomy_ui.get("severity") or "") == "high"
            )
            else None
        )
    )
    urgency_level = str(taxonomy_ui.get("severity") or "medium")
    if urgency_level not in ("high", "medium", "low"):
        urgency_level = "medium"
    if use_emergency_template:
        urgency_level = "high"

    legal_overview: dict[str, Any] = {
        "summary": companion.get("legal_explanation"),
        "grounding_label": companion.get("rag_grounding_label"),
        "confidence_score": companion.get("confidence_score"),
        "references": [],  # filled after legal_refs_filtered
    }

    search_note = None
    if authority_block.get("status") == "verified":
        search_note = meta.get("fallback_message")
    elif authority_block.get("status") == "unknown":
        search_note = FALLBACK_MESSAGE

    _meta_for_em = dict(classifier_meta)
    _em_layer_raw = _meta_for_em.get("emergency_layer")
    _em_layer: dict[str, Any] = dict(_em_layer_raw) if isinstance(_em_layer_raw, dict) else {}
    _layer_for_cats = EmergencyLayerResult(
        bypass_recommended=bool(_em_layer.get("bypass_recommended")),
        triggers=[str(t) for t in (_em_layer.get("triggers") or []) if str(t).strip()],
        categories=[str(c) for c in (_em_layer.get("categories") or []) if str(c).strip()],
    )
    _emergency_cats = emergency_categories_for_issue(
        user_input=user_input.strip(),
        classifier_domain=str(classifier_meta.get("domain") or ""),
        classifier_category=str(classifier_meta.get("category") or ""),
        issue_type=str(taxonomy_ui.get("issue_type") or ""),
        fine_intent=str(classifier_meta.get("fine_intent") or ""),
        sub_type=str(taxonomy_ui.get("sub_type") or classifier_meta.get("sub_type") or ""),
        severity=str(taxonomy_ui.get("severity") or ""),
        layer=_layer_for_cats,
    )
    if use_emergency_template and not _emergency_cats:
        _emergency_cats = ["unified_emergency", "police", "ambulance"]
    elif str(classifier_meta.get("phase6_priority") or "") == "law_and_order" and not _emergency_cats:
        _emergency_cats = ["unified_emergency", "police"]
    _include_emergency_block = bool(
        use_emergency_template
        or str(classifier_meta.get("phase6_priority") or "") == "law_and_order"
        or bool(_emergency_cats)
    )
    emergency_contacts: list[dict[str, Any]] = []
    emergency_reference_links: list[dict[str, str]] = []
    if _include_emergency_block and _emergency_cats:
        _d_em, _s_em = _district_state_labels(city if isinstance(city, str) else None)
        emergency_contacts = resolve_emergency_contacts(
            categories_needed=_emergency_cats,
            state_label=_s_em or None,
            city_label=_d_em or None,
        )
    if _include_emergency_block:
        _d_link, _s_link = _district_state_labels(city if isinstance(city, str) else None)
        emergency_reference_links = fetch_emergency_reference_links(
            state_label=_s_link or None,
            city_label=_d_link or None,
            categories_needed=_emergency_cats,
        )

    legal_classification_out: dict[str, Any] = {
        "domain": classifier_meta.get("domain", ""),
        "sub_type": taxonomy_ui.get("sub_type", ""),
        "category": classifier_meta["category"],
        "fine_intent": classifier_meta["fine_intent"],
        "classifier_confidence": classifier_meta["confidence"],
        "router_intent": classifier_meta["router_intent"],
        "entities": interpretation["entities"],
        "intent_hint": interpretation["intent_hint"],
        "context": interpretation["context"],
        "issue_type": taxonomy_ui["issue_type"],
        "severity": taxonomy_ui["severity"],
        "jurisdiction_type": taxonomy_ui["jurisdiction_type"],
        "authority_primary": str(router_result["primary_authority"]),
        "authority_secondary": str(router_result["secondary_authority"]),
        "issue_profile": issue_profile_payload,
        "phase6_agents": {"classifier": classifier_agent_snapshot(taxonomy_ui, classifier_meta)},
        "intent_bucket": map_phase6_intent_bucket(
            taxonomy_ui=dict(taxonomy_ui),
            classifier_meta=dict(classifier_meta),
            emergency_layer=_em_layer,
        ),
        "emergency_layer": _em_layer,
    }
    if classifier_meta.get("secondary_domain"):
        legal_classification_out["secondary_domain"] = str(classifier_meta["secondary_domain"])
    if classifier_meta.get("is_hybrid"):
        legal_classification_out["is_hybrid"] = True
    jurisdiction_out = {
        "primary": router_result["primary_authority"],
        "secondary": router_result["secondary_authority"],
        "path": router_result["routing_steps"],
        "fallback_path": router_result["fallback_path"],
        "jurisdiction_reason": router_result["jurisdiction_reason"],
    }
    if classifier_meta.get("is_hybrid"):
        jurisdiction_out["is_hybrid"] = True

    verified_laws_only = [x for x in companion["retrieved_laws"] if x.get("verified")]
    legal_refs_filtered = [
        {"law": x["law"], "section": x["section"], "source_url": x["source_url"]}
        for x in verified_laws_only
    ]
    legal_overview["references"] = legal_refs_filtered

    verifier = evaluate_legal_response(
        str(document),
        authority_block,
        verified_laws_only,
    )
    trust_report = build_trust_report(
        authority_block=authority_block,
        verifier=verifier,
        law_refs_verified_only=bool(verified_laws_only),
    )

    doc_final = _normalize_document_spacing(str(document))
    still_bad_align, _ = document_violates_authority_alignment(
        doc_final,
        classifier_meta=classifier_meta,
        taxonomy=taxonomy_ui,
    )
    if still_bad_align:
        gen_score = min(float(gen_score), 5.0)
    if classifier_meta.get("is_llm_fallback") and not classifier_meta.get("is_hybrid"):
        gen_score = min(float(gen_score), 6.0)
    authority_compact = _compact_authority(authority_block)

    authority_hierarchy = build_authority_hierarchy(
        str(classifier_meta.get("router_intent") or ""),
        city if isinstance(city, str) else None,
        response_language=response_language,
    )
    if _crisis_triage:
        authority_hierarchy = []

    is_verified = bool(
        authority_block.get("status") == "verified" and not classifier_meta.get("is_llm_fallback")
    )
    llm_fb_conf = classifier_meta.get("llm_fallback_confidence")
    llm_fb_conf_f = float(llm_fb_conf) if isinstance(llm_fb_conf, (int, float)) else None
    routing_summary = {
        "issue_type": str(taxonomy_ui["issue_type"]),
        "sub_type": str(taxonomy_ui.get("sub_type") or ""),
        "domain": str(classifier_meta.get("domain") or ""),
        "severity": str(taxonomy_ui["severity"]),
        "authority_primary": str(authority_block.get("primary") or ""),
        "authority_secondary": str(authority_block.get("secondary") or ""),
        "is_verified": is_verified,
        "urgency": urgency_level,
        "router_intent": str(classifier_meta.get("router_intent") or ""),
        "is_llm_fallback": bool(classifier_meta.get("is_llm_fallback")),
        "llm_fallback_confidence": llm_fb_conf_f,
    }
    if classifier_meta.get("is_hybrid"):
        routing_summary["is_hybrid"] = True
        routing_summary["secondary_domain"] = str(classifier_meta.get("secondary_domain") or "criminal")
        if bool(classifier_meta.get("hybrid_police_primary")):
            routing_summary["routing_primary_forum"] = "police"
            routing_summary["routing_secondary_forum"] = "civil_court"
        else:
            routing_summary["routing_primary_forum"] = "civil_court"
            routing_summary["routing_secondary_forum"] = "police"

    explanation_out = str(explanation).strip()
    if (
        not _crisis_triage
        and not use_emergency_template
        and bool(classifier_meta.get("hybrid_police_primary"))
        and str(classifier_meta.get("phase6_priority") or "") == "law_and_order"
        and detect_land_context(user_input)
    ):
        explanation_out = (
            "This case involves:\n\n"
            "• Immediate law & order issue (violence / threat)\n"
            "• Underlying civil dispute (for example land ownership or possession)\n\n"
            "Police action is required first to control an ongoing safety risk where applicable.\n"
            "Civil court action may be required to resolve ownership or possession legally.\n\n"
        ) + explanation_out
    if classifier_meta.get("is_llm_fallback") and not classifier_meta.get("is_hybrid"):
        explanation_out += llm_fallback_explainer_suffix(response_language)

    document_evaluator_out: dict[str, Any] | None = None
    document_revised_out = ""
    if (
        bool(getattr(settings, "evaluator_dual_draft_enabled", False))
        and not use_emergency_template
        and not _crisis_triage
        and doc_final.strip()
        and not skip_full_generation
    ):
        try:
            from app.ai.draft_evaluator_agent import run_draft_evaluator_and_refiner

            _ev_client = OpenAI(api_key=settings.openai_api_key)
            document_evaluator_out, document_revised_out = run_draft_evaluator_and_refiner(
                _ev_client,
                user_input=user_input.strip(),
                document=doc_final,
                issue_profile=issue_profile_payload,
                category=str(classifier_meta.get("category") or ""),
                response_language=response_language,
                model=str(settings.openai_model or "gpt-4o-mini").strip() or "gpt-4o-mini",
                primary_forum=str(router_result.get("primary_authority") or ""),
                router_intent=str(classifier_meta.get("router_intent") or ""),
            )
            if document_revised_out.strip():
                document_revised_out = _normalize_document_spacing(document_revised_out)
        except Exception:
            document_evaluator_out = None
            document_revised_out = ""

    return finalize_legal_response(
        {
        "document": doc_final,
        "draft": doc_final,
        "explanation": explanation_out,
        "next_steps": next_steps,
        "routing_summary": routing_summary,
        "is_verified": is_verified,
        "clarification_needed": False,
        "clarification_question": None,
        "clarification_options": [],
        "clarification_points": [],
        "urgency_banner": urgency_banner,
        "urgency_level": urgency_level,
        "issue_profile": issue_profile_payload,
        "official_links": official_link_list,
        "multi_intent": dict(multi_intent_result),
        "generation_score": gen_score,
        "legal_overview": legal_overview,
        "authority": authority_block,
        "authority_compact": authority_compact,
        "authority_disclaimer": authority_disclaimer(response_language),
        "authority_search_note": search_note,
        "legal_classification": legal_classification_out,
        "jurisdiction": jurisdiction_out,
        "trust_summary": _compute_trust_summary(authority_block, companion["retrieved_laws"]),
        "trust_report": trust_report,
        "verifier": verifier,
        "legal_explanation": companion["legal_explanation"],
        "procedure_steps": companion["procedure_steps"],
        "step_by_step_procedure": companion["step_by_step_procedure"],
        "legal_references": legal_refs_filtered,
        "retrieved_laws": companion["retrieved_laws"],
        "confidence_score": companion["confidence_score"],
        "rag_grounding_label": companion["rag_grounding_label"],
        "authority_summary": companion["authority_summary"],
        "authority_hierarchy": authority_hierarchy,
        "generation_mode": generation_mode,
        "skip_full_generation": skip_full_generation,
        "alert": alert,
        "note": note,
        "safety_tip": safety_tip,
        "emergency_contacts": emergency_contacts,
        "emergency_reference_links": emergency_reference_links,
        "emergency_registry_disclaimer": registry_disclaimer(),
        "crisis_triage_mode": _crisis_triage,
        "document_evaluator": document_evaluator_out,
        "document_revised": document_revised_out,
        }
    )
