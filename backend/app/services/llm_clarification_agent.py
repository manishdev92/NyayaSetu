"""
LLM-powered clarification intake (JSON only). Augments rule-based clarification — never replaces routing.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, TypedDict

from openai import OpenAI

from app.config import settings
from app.i18n_response_strings import (
    clarification_agent_system_language_addon,
    normalize_response_lang,
    yes_no_labels,
    yes_no_not_sure_labels,
)

logger = logging.getLogger(__name__)


def _t(lang: str, en: str, hi: str, latn: str) -> str:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return hi
    if rl == "hi_latn":
        return latn
    return en


def _localize_structured_question_options(
    questions: list[ClarificationAgentQuestion],
    response_language: str,
) -> None:
    """Force yes/no labels and common Yes/No/Not sure triples to match UI language."""
    yn = list(yes_no_labels(response_language))
    ynu = list(yes_no_not_sure_labels(response_language))
    for q in questions:
        typ = str(q.get("type") or "")
        opts = [str(x).strip() for x in (q.get("options") or [])]
        if typ == "yes_no":
            q["options"] = yn
            continue
        if typ == "single_choice" and len(opts) == 3:
            low = tuple(o.lower() for o in opts)
            if low == ("yes", "no", "not sure"):
                q["options"] = ynu

SYSTEM_PROMPT = """You are a legal intake assistant for an Indian legal support system.

Your job is to ask precise clarification questions that help determine:
* correct legal domain (civil, criminal, revenue, consumer, labour, etc.)
* correct authority (police, court, tehsildar, etc.)
* severity and urgency

Rules:
* Ask only high-signal questions
* Maximum 3 questions
* Prefer multiple-choice or yes/no
* Do NOT explain law
* Do NOT generate legal advice
* Return STRICT JSON only
* Focus on missing or ambiguous details
* Each question must have: "id" (short snake_case), "question" (one sentence), "type" ("single_choice" or "yes_no"), "options" (array of 2-5 strings for single_choice; for yes_no use ["Yes","No"]), "required" (boolean)

If the case already looks clear, return:
{"questions": [], "reason": "sufficient clarity", "confidence_hint": 0.9}

Schema for questions when needed:
{
  "questions": [
    {
      "id": "threat_check",
      "question": "Was there any threat, violence, or force involved?",
      "type": "single_choice",
      "options": ["Yes", "No", "Not sure"],
      "required": true
    }
  ],
  "reason": "short note why questions help",
  "confidence_hint": 0.78
}
"""


class ClarificationAgentQuestion(TypedDict):
    id: str
    question: str
    type: str
    options: list[str]
    required: bool


class ClarificationAgentResult(TypedDict):
    questions: list[ClarificationAgentQuestion]
    reason: str
    confidence_hint: float


def _slug_id(raw: str, idx: int) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (raw or "").lower()).strip("_")
    return (s[:48] or f"question_{idx}")[:64]


def _coerce_question(obj: Any, idx: int) -> ClarificationAgentQuestion | None:
    if not isinstance(obj, dict):
        return None
    qid = str(obj.get("id") or "").strip() or _slug_id(str(obj.get("question") or ""), idx)
    qtext = str(obj.get("question") or "").strip()
    if len(qtext) < 8 or len(qtext) > 400:
        return None
    typ = str(obj.get("type") or "single_choice").strip().lower()
    if typ not in ("single_choice", "yes_no"):
        typ = "single_choice"
    opts_raw = obj.get("options")
    opts: list[str] = []
    if isinstance(opts_raw, list):
        opts = [str(o).strip() for o in opts_raw if str(o).strip()][:5]
    if typ == "yes_no":
        opts = opts[:2] if len(opts) >= 2 else ["Yes", "No"]
    elif len(opts) < 2:
        return None
    req = bool(obj.get("required", True))
    return ClarificationAgentQuestion(
        id=qid[:64],
        question=qtext,
        type=typ,
        options=opts,
        required=req,
    )


def _coerce_result(raw: dict[str, Any]) -> ClarificationAgentResult:
    qs_in = raw.get("questions")
    questions: list[ClarificationAgentQuestion] = []
    if isinstance(qs_in, list):
        for i, item in enumerate(qs_in[:5]):
            cq = _coerce_question(item, i)
            if cq:
                questions.append(cq)
    questions = questions[:3]
    reason = str(raw.get("reason") or "clarification").strip()[:500] or "clarification"
    ch = raw.get("confidence_hint")
    try:
        confidence_hint = float(ch) if ch is not None else 0.75
    except (TypeError, ValueError):
        confidence_hint = 0.75
    confidence_hint = max(0.0, min(1.0, confidence_hint))
    return ClarificationAgentResult(questions=questions, reason=reason, confidence_hint=confidence_hint)


def rule_fallback_questions(
    *,
    domain: str,
    issue_type: str,
    router_intent: str,
    is_hybrid: bool,
    soft_optional: bool,
    missing_entities: dict[str, bool],
    response_language: str = "en",
) -> ClarificationAgentResult:
    """Deterministic structured questions when the LLM is unavailable or returns empty."""
    lang = response_language
    dom = (domain or "").lower()
    it = (issue_type or "").lower()
    ri = (router_intent or "").lower()
    yn = list(yes_no_labels(lang))

    if soft_optional and is_hybrid:
        return ClarificationAgentResult(
            questions=[
                ClarificationAgentQuestion(
                    id="force_or_threat",
                    question=_t(
                        lang,
                        "Was there any use of force, threats, or trespass related to this matter?",
                        "क्या इस मामले में बल, धमकी या अनधिकृत प्रवेश शामिल था?",
                        "Kya is mamle mein bal, dhamki ya anadhikarit pravesh shamil tha?",
                    ),
                    type="yes_no",
                    options=yn,
                    required=False,
                ),
                ClarificationAgentQuestion(
                    id="key_documents",
                    question=_t(
                        lang,
                        "Do you have key documents (title, lease, notices, or messages) handy to share later?",
                        "क्या आपके पास बाद में साझा करने हेतु मुख्य दस्तावेज़ (टाइटल, पट्टा, नोटिस, संदेश) उपलब्ध हैं?",
                        "Kya aapke paas baad mein sanja karne hetu mukhya dastavez (title, patta, notice, sandesh) uplabdh hain?",
                    ),
                    type="yes_no",
                    options=yn,
                    required=False,
                ),
            ][:2],
            reason=_t(
                lang,
                "Hybrid civil–criminal routing — optional refinement",
                "संयुक्त नागरिक–आपराधिक रूटिंग — वैकल्पिक स्पष्टीकरण",
                "Sanyukt nagrik-aapradhik routing — optional spashtikaran",
            ),
            confidence_hint=0.88,
        )

    if "land" in ri or "property" in dom or it in ("land_revenue", "civil_court"):
        return ClarificationAgentResult(
            questions=[
                ClarificationAgentQuestion(
                    id="threat_or_force",
                    question=_t(
                        lang,
                        "Was there any threat, violence, or force involved in the dispute?",
                        "विवाद में किसी धमकी, हिंसा या बल का उपयोग हुआ था?",
                        "Vivad mein kisi dhamki, hinsa ya bal ka upyog hua tha?",
                    ),
                    type="single_choice",
                    options=list(yes_no_not_sure_labels(lang)),
                    required=True,
                ),
                ClarificationAgentQuestion(
                    id="ownership_docs",
                    question=_t(
                        lang,
                        "Do you have ownership or possession-related documents (title, sale deed, lease, survey)?",
                        "क्या आपके पास स्वामित्व/कब्ज़े संबंधी दस्तावेज़ (टाइटल, बिक्री विलेख, पट्टा, सर्वे) हैं?",
                        "Kya aapke paas swamitv/kabze sambandhi dastavez (title, bikri vilekh, patta, survey) hain?",
                    ),
                    type="yes_no",
                    options=yn,
                    required=False,
                ),
            ],
            reason=_t(
                lang,
                "Land or property angle — civil vs police path depends on these facts",
                "भूमि/संपत्ति कोण — इन तथ्यों पर सिविल बनाम पुलिस मार्ग निर्भर करता है",
                "Bhumi/sampatti kon — in tathyon par civil banam police marg nirbhar karta hai",
            ),
            confidence_hint=0.72,
        )

    if missing_entities.get("lost_vs_theft"):
        rl = normalize_response_lang(lang)
        lost_opts = {
            "en": ["Lost / misplaced", "Stolen / snatched", "Not sure"],
            "hi": ["खो गई / गलत जगह रखी", "चोरी / छीनना", "पक्का नहीं"],
            "hi_latn": ["Kho gayi / galat jagah rakhi", "Chori / chhinna", "Pakka nahi"],
        }.get(rl, ["Lost / misplaced", "Stolen / snatched", "Not sure"])
        return ClarificationAgentResult(
            questions=[
                ClarificationAgentQuestion(
                    id="lost_or_stolen",
                    question=_t(
                        lang,
                        "Was the item lost or misplaced, or do you believe it was stolen?",
                        "वस्तु खो गई/गलत जगह रख गई, या आपको लगता है कि चोरी हुई?",
                        "Vastu kho gayi/galat jagah rakh gayi, ya aapko lagta hai ki chori hui?",
                    ),
                    type="single_choice",
                    options=list(lost_opts),
                    required=True,
                ),
            ],
            reason=_t(
                lang,
                "Lost property vs theft changes the police route",
                "खोई संपत्ति बनाम चोरी से पुलिस मार्ग बदलता है",
                "Khoi sampatti banam chori se police marg badalta hai",
            ),
            confidence_hint=0.7,
        )

    if dom == "labour" or "salary" in ri:
        rl = normalize_response_lang(lang)
        lab_opts = {
            "en": ["Threats or violence", "Unpaid dues only", "Both"],
            "hi": ["धमकी या हिंसा", "केवल वेतन बकाया", "दोनों"],
            "hi_latn": ["Dhamki ya hinsa", "Kewal vetan bakaya", "Donon"],
        }.get(rl, ["Threats or violence", "Unpaid dues only", "Both"])
        return ClarificationAgentResult(
            questions=[
                ClarificationAgentQuestion(
                    id="threat_at_work",
                    question=_t(
                        lang,
                        "Were you threatened or assaulted at work, or is this only about unpaid dues?",
                        "क्या कार्यस्थल पर धमकी या हमला हुआ, या केवल अवैतनिक वेतन का मामला है?",
                        "Kya karyasthal par dhamki ya hamla hua, ya kewal avaitanik vetan ka mamla hai?",
                    ),
                    type="single_choice",
                    options=list(lab_opts),
                    required=True,
                ),
            ],
            reason=_t(
                lang,
                "Labour vs safety / police routing",
                "श्रम बनाम सुरक्षा / पुलिस रूटिंग",
                "Shram banam suraksha / police routing",
            ),
            confidence_hint=0.74,
        )

    if is_hybrid:
        return ClarificationAgentResult(
            questions=[
                ClarificationAgentQuestion(
                    id="hybrid_threat",
                    question=_t(
                        lang,
                        "Did the situation involve force, threats, or occupation without consent?",
                        "क्या स्थिति में बल, धमकी या बिना सहमति कब्ज़ा शामिल था?",
                        "Kya sthiti mein bal, dhamki ya bina sahmati kabja shamil tha?",
                    ),
                    type="yes_no",
                    options=yn,
                    required=True,
                ),
                ClarificationAgentQuestion(
                    id="hybrid_docs",
                    question=_t(
                        lang,
                        "Do you have written agreements, notices, or title-related papers?",
                        "क्या आपके पास लिखित समझौते, नोटिस या स्वामित्व संबंधी कागज़ हैं?",
                        "Kya aapke paas likhit samjhaute, notice ya swamitv sambandhi kagaz hain?",
                    ),
                    type="yes_no",
                    options=yn,
                    required=False,
                ),
            ],
            reason=_t(
                lang,
                "Hybrid civil–criminal case — high-impact facts",
                "संयुक्त नागरिक–आपराधिक मामला — महत्वपूर्ण तथ्य",
                "Sanyukt nagrik-aapradhik mamla — mahatvpurn tathy",
            ),
            confidence_hint=0.76,
        )

    _ = missing_entities
    rl = normalize_response_lang(lang)
    timeline_opts = {
        "en": ["Within last 30 days", "1–12 months ago", "More than a year ago / not sure"],
        "hi": ["पिछले 30 दिनों में", "1–12 महीने पहले", "एक साल से अधिक / पक्का नहीं"],
        "hi_latn": [
            "Pichhle 30 dinon mein",
            "1–12 mahine pehle",
            "Ek sal se adhik / pakka nahi",
        ],
    }.get(rl, ["Within last 30 days", "1–12 months ago", "More than a year ago / not sure"])
    return ClarificationAgentResult(
        questions=[
            ClarificationAgentQuestion(
                id="timeline",
                question=_t(
                    lang,
                    "Roughly when did the main events happen (month/year is enough)?",
                    "मुख्य घटनाएँ लगभग कब हुईं (महीना/वर्ष पर्याप्त)?",
                    "Mukhya ghatnayein lagbhag kab huin (mahina/varsh paryapt)?",
                ),
                type="single_choice",
                options=list(timeline_opts),
                required=True,
            ),
            ClarificationAgentQuestion(
                id="written_proof",
                question=_t(
                    lang,
                    "Do you have messages, receipts, contracts, or photos that support your side?",
                    "क्या आपके पास संदेश, रसीद, अनुबंध या फोटो हैं जो आपके पक्ष का समर्थन करें?",
                    "Kya aapke paas sandesh, raseed, anubandh ya photo hain jo aapke paksh ka samarthan karen?",
                ),
                type="yes_no",
                options=yn,
                required=False,
            ),
        ],
        reason=_t(
            lang,
            "Ambiguous intake — timeline and documents help routing",
            "अस्पष्ट इनटेक — समयरेखा व दस्तावेज़ रूटिंग में मदद करते हैं",
            "Aspasht intake — samayrekha va dastavez routing mein madad karte hain",
        ),
        confidence_hint=0.68,
    )


def run_llm_clarification_agent(
    user_query: str,
    *,
    domain: str,
    sub_type: str,
    issue_type: str,
    router_intent: str,
    confidence: float,
    is_hybrid: bool,
    missing_entities: dict[str, bool],
    ambiguous_intent: bool,
    soft_optional: bool,
    max_questions: int = 3,
    priority_level: str | None = None,
    hybrid_police_primary: bool = False,
    response_language: str = "en",
) -> ClarificationAgentResult:
    """
    Returns structured questions (max 3). Never assigns authorities or final labels.
    """
    pl = str(priority_level or "").strip().upper()
    if pl in ("P0", "P1") and not hybrid_police_primary:
        return ClarificationAgentResult(
            questions=[],
            reason="priority_of_harm_skip_clarification",
            confidence_hint=max(0.9, float(confidence)),
        )
    max_q = 2 if soft_optional else max(1, min(3, max_questions))
    lang_addon = clarification_agent_system_language_addon(response_language)
    fb_kwargs = dict(
        domain=domain,
        issue_type=issue_type,
        router_intent=router_intent,
        is_hybrid=is_hybrid,
        soft_optional=soft_optional,
        missing_entities=missing_entities,
        response_language=response_language,
    )
    if not settings.openai_api_key:
        out = rule_fallback_questions(**fb_kwargs)
        _localize_structured_question_options(out["questions"], response_language)
        return out

    user_payload = {
        "user_query": (user_query or "").strip()[:8000],
        "current_classification": {
            "domain": domain,
            "sub_type": sub_type,
            "issue_type": issue_type,
            "router_intent": router_intent,
            "confidence": confidence,
        },
        "flags": {
            "is_hybrid": is_hybrid,
            "ambiguous_intent": ambiguous_intent,
            "soft_optional": soft_optional,
            "missing_entities": missing_entities,
        },
        "output_limits": {"max_questions": max_q},
        "response_language": normalize_response_lang(response_language),
    }
    mode_note = (
        "MODE: optional refinement only — return at most 2 questions; required should be false; "
        "keep questions short."
        if soft_optional
        else "MODE: blocking clarification — up to 3 questions; at least one required:true if questions non-empty."
    )
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT + "\n\n" + mode_note + lang_addon,
                },
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            response_format={"type": "json_object"},
            temperature=0.25,
        )
        raw_txt = resp.choices[0].message.content
        if not raw_txt:
            raise ValueError("empty model output")
        parsed = json.loads(raw_txt)
        if not isinstance(parsed, dict):
            raise ValueError("not a dict")
        out = _coerce_result(parsed)
        out["questions"] = out["questions"][:max_q]
        _localize_structured_question_options(out["questions"], response_language)
        if not out["questions"]:
            fb = rule_fallback_questions(**fb_kwargs)
            _localize_structured_question_options(fb["questions"], response_language)
            return fb
        return out
    except Exception as e:  # noqa: BLE001
        logger.info("llm_clarification_agent fallback: %s", e)
        fb = rule_fallback_questions(**fb_kwargs)
        _localize_structured_question_options(fb["questions"], response_language)
        return fb


def agent_questions_to_legacy_strings(questions: list[ClarificationAgentQuestion]) -> list[str]:
    """Plain strings for clients that only render clarifying_questions."""
    return [q["question"] for q in questions]
