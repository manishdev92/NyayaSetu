"""Two-pass LLM: (1) evaluate draft vs user issue + common India templates; (2) revise document."""

from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI

_MAX_DOC = 14_000

EVALUATOR_SYSTEM = """You are an expert evaluator for India-facing legal drafts (police complaints, FIR-style letters, applications to government offices).

Compare USER_ISSUE to DRAFT_DOCUMENT.

Return ONLY a JSON object with exactly these keys:
- "relevance_score": integer 1–5 (5 = draft matches the user's story and forum)
- "template_fit_score": integer 1–5 (5 = structure matches what a careful complainant would file: print lines if any, To/addressee, Subject, facts, prayer; proper spacing)
- "issues": array of short strings (substantive problems)
- "format_violations": array of short strings (e.g. scene/chaurah used as police station name; line like "Police Station (Station House Officer — SHO)"; authority routing text pasted as if it were the thana name; missing Subject; no prayer for FIR where police theft)
- "facts_missing_or_placeholders": array of short strings (e.g. vehicle reg unknown — OK as placeholder; wrong facts)
- "summary_for_user": string, 2–4 sentences in the SAME language/script as DRAFT_DOCUMENT (English, Hindi Devanagari, or Roman Hindi to match the draft)

Rules: Do not invent statutes or phone numbers. Be concrete and actionable.
- Check **FORUM_CONSISTENCY** from the metadata block in the user message: if the draft’s addressee type does not match the routed issue (e.g. **police / SHO** letter for a **consumer-commission** story, or **Consumer Commission** letter for a **criminal / FIR** story), add a `format_violation` and lower `relevance_score` / `template_fit_score` as appropriate. Describe the mismatch clearly.
"""

REFINER_SYSTEM = """You are a refiner for India-facing formal complaints and applications to **government authorities**.

You receive FORUM_LOCK metadata, USER_ISSUE, EVALUATION_JSON, and ORIGINAL_DOCUMENT.

## FORUM_LOCK (MANDATORY — highest priority)
- Read `ISSUE_CATEGORY` and `PRIMARY_FORUM` from the user message. The **ORIGINAL_DOCUMENT** is already forum-targeted in its **To / addressee / सेवा में** block.
- You MUST **preserve the same class of primary authority** as the original letter:
  * If the original is to a **Consumer Commission** / **Consumer Disputes Redressal** body, the revised document MUST **stay** a consumer-commission style letter. **Do NOT** change the addressee to **police / SHO / thana** or "police station having jurisdiction…" unless the user issue is explicitly police-primary (criminal) — which is NOT the case for consumer.
  * If the original is to **Station House Officer / police / FIR** style, the revised document **stays** police — do **not** retarget to Consumer Commission, Labour, or Tehsildar.
  * **Labour / civil / revenue / other:** keep the same addressee **category**; only improve format and clarity.
- Fix objective **format_violations** from EVALUATION_JSON (locus as PS name, garbled "Police Station (SHO)", etc.) **without** changing forum class.
- **Print-fill** at top and bottom: preserve **## PRINT_FILL_HEADER** and **## PRINT_FILL_FOOTER** (mirrored line labels, blank underscores); do not auto-fill PII; nothing after the footer.
- **To block (police only):** use the jurisdictional police wording or placeholders from layout rules — not scene names, not `AUTHORITY_BLOCK` routing blurbs in parentheses. **(Consumer only):** "Before the … / To the … Commission" style; district/state placeholders.
- **DOCUMENT_WHITESPACE:** blank lines between major sections.
- Never invent government phone numbers; no fake statute numbers — placeholders only.
- Preserve user-stated facts; do not invent new events.

Return JSON only: "document_revised" (string), "refiner_notes" (one short string)."""


def _truncate(s: str, n: int) -> str:
    t = (s or "").strip()
    if len(t) <= n:
        return t
    return t[: n - 20] + "\n[…truncated…]\n"


def _call_json(client: OpenAI, *, model: str, system: str, user: str, temperature: float) -> dict[str, Any]:
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=temperature,
        max_tokens=2048,
    )
    raw = resp.choices[0].message.content
    if not raw:
        return {}
    try:
        out = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return out if isinstance(out, dict) else {}


def _coerce_int_score(v: object) -> int:
    if isinstance(v, bool):
        return 0
    if isinstance(v, int):
        return max(0, min(5, v))
    if isinstance(v, float) and not isinstance(v, bool):
        return max(0, min(5, int(round(v))))
    if isinstance(v, str):
        m = re.match(r"^\s*(\d+)\s*$", v)
        if m:
            return max(0, min(5, int(m.group(1))))
    return 0


def run_evaluator_llm_normalized(
    client: OpenAI,
    *,
    user_input: str,
    document: str,
    issue_profile: dict[str, Any],
    category: str,
    response_language: str,
    model: str,
    primary_forum: str = "",
    router_intent: str = "",
) -> dict[str, Any]:
    user = (
        f"PRIMARY_FORUM: {primary_forum}\n"
        f"ROUTER_INTENT: {router_intent}\n"
        f"ISSUE_CATEGORY: {category}\n"
        f"RESPONSE_LANGUAGE: {response_language}\n"
        f"ISSUE_PROFILE_JSON:\n{json.dumps(issue_profile, ensure_ascii=False)}\n\n"
        f"USER_ISSUE:\n{_truncate(user_input, 6000)}\n\n"
        f"DRAFT_DOCUMENT:\n{_truncate(document, _MAX_DOC)}"
    )
    data = _call_json(client, model=model, system=EVALUATOR_SYSTEM, user=user, temperature=0.15)
    issues = data.get("issues") if isinstance(data.get("issues"), list) else []
    fv = data.get("format_violations") if isinstance(data.get("format_violations"), list) else []
    fmp = (
        data.get("facts_missing_or_placeholders")
        if isinstance(data.get("facts_missing_or_placeholders"), list)
        else []
    )
    return {
        "relevance_score": _coerce_int_score(data.get("relevance_score")),
        "template_fit_score": _coerce_int_score(data.get("template_fit_score")),
        "issues": [str(x) for x in issues if str(x).strip()][:12],
        "format_violations": [str(x) for x in fv if str(x).strip()][:12],
        "facts_missing_or_placeholders": [str(x) for x in fmp if str(x).strip()][:12],
        "summary_for_user": str(data.get("summary_for_user") or "").strip()[:2000],
    }


def run_refiner_llm(
    client: OpenAI,
    *,
    user_input: str,
    original_document: str,
    evaluation: dict[str, Any],
    response_language: str,
    model: str,
    issue_category: str = "",
    primary_forum: str = "",
    router_intent: str = "",
) -> tuple[str, str]:
    user = (
        f"ISSUE_CATEGORY: {issue_category}\n"
        f"PRIMARY_FORUM: {primary_forum}\n"
        f"ROUTER_INTENT: {router_intent}\n"
        f"RESPONSE_LANGUAGE: {response_language}\n"
        f"(Policing hint: for **consumer** category, the letter must **not** be re-addressed to police.)\n\n"
        f"USER_ISSUE:\n{_truncate(user_input, 6000)}\n\n"
        f"EVALUATION_JSON:\n{json.dumps(evaluation, ensure_ascii=False)}\n\n"
        f"ORIGINAL_DOCUMENT:\n{_truncate(original_document, _MAX_DOC)}"
    )
    data = _call_json(client, model=model, system=REFINER_SYSTEM, user=user, temperature=0.25)
    doc = str(data.get("document_revised") or "").strip()
    notes = str(data.get("refiner_notes") or "").strip()[:500]
    return doc, notes


def run_draft_evaluator_and_refiner(
    client: OpenAI,
    *,
    user_input: str,
    document: str,
    issue_profile: dict[str, Any],
    category: str,
    response_language: str,
    model: str,
    primary_forum: str = "",
    router_intent: str = "",
) -> tuple[dict[str, Any] | None, str]:
    """Runs evaluator then refiner; returns (evaluation dict, revised document). On failure returns (None, '')."""
    try:
        ev = run_evaluator_llm_normalized(
            client,
            user_input=user_input,
            document=document,
            issue_profile=issue_profile,
            category=category,
            response_language=response_language,
            model=model,
            primary_forum=primary_forum,
            router_intent=router_intent,
        )
        revised, notes = run_refiner_llm(
            client,
            user_input=user_input,
            original_document=document,
            evaluation=ev,
            response_language=response_language,
            model=model,
            issue_category=category,
            primary_forum=primary_forum,
            router_intent=router_intent,
        )
        if notes:
            ev = {**ev, "refiner_notes": notes}
        if not revised.strip():
            return ev, ""
        return ev, revised
    except Exception:
        return None, ""
