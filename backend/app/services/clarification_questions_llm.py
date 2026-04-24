"""LLM-generated conversational clarification (2–4 short questions) before full drafting."""

from __future__ import annotations

import json
import logging

from openai import OpenAI

from app.config import settings
from app.i18n_response_strings import clarification_conversational_system_language_addon
from app.services.clarification_engine import ClarificationIntent

logger = logging.getLogger(__name__)

_SYSTEM = """You are a legal assistant helping users in India describe problems in plain language.

Return JSON ONLY with this shape:
{"questions": ["...", "...", "..."]}

Rules:
- Ask 2 to 4 short, precise questions (one sentence each) to clarify the user's issue so the correct legal authority can be determined later.
- Avoid legal jargon and statute names.
- Focus on missing facts (who, what, when, where, documents, whether force or threats were involved, loss vs theft if relevant).
- Questions must be answerable by a layperson.
- Do NOT invent office names, phone numbers, or IPC sections."""


def _trl(lang: str, en: str, hi: str, latn: str) -> str:
    rl = (lang or "en").strip().lower().replace("-", "_")
    if rl == "hi":
        return hi
    if rl == "hi_latn":
        return latn
    return en


def _rule_fallback_questions(intent: ClarificationIntent, *, response_language: str = "en") -> list[str]:
    lang = response_language
    if intent.get("is_hybrid"):
        return [
            _trl(
                lang,
                "Was there any use of force, threats, or trespass by anyone?",
                "क्या किसी ने बल, धमकी या अनधिकृत प्रवेश किया?",
                "Kya kisi ne bal, dhamki ya anadhikarit pravesh kiya?",
            ),
            _trl(
                lang,
                "Do you have documents (title, lease, notices, messages) that support your side?",
                "क्या आपके पास आपके पक्ष का समर्थन करने वाले दस्तावेज़ (टाइटल, पट्टा, नोटिस, संदेश) हैं?",
                "Kya aapke paas aapke paksh ka samarthan karne wale dastavez (title, patta, notice, sandesh) hain?",
            ),
            _trl(
                lang,
                "Roughly when did the main events happen?",
                "मुख्य घटनाएँ लगभग कब हुईं?",
                "Mukhya ghatnayein lagbhag kab huin?",
            ),
            _trl(
                lang,
                "What do you want first: help with a police complaint, civil court steps, or both?",
                "पहले आप क्या चाहते हैं: पुलिस शिकायत, सिविल न्यायालय के कदम, या दोनों?",
                "Pehle aap kya chahte hain: police shikayat, civil nyayalay ke kadam, ya donon?",
            ),
        ]
    dom = (intent.get("domain") or "").lower()
    it = (intent.get("issue_type") or "").lower()
    if dom == "labour" or it == "salary" or "salary" in (intent.get("router_intent") or ""):
        return [
            _trl(
                lang,
                "How much is owed and for which months or period?",
                "कितना बकाया है और किस महीने/अवधि का?",
                "Kitna bakaya hai aur kis mahine/avdhi ka?",
            ),
            _trl(
                lang,
                "Were you threatened or assaulted at work, or is this only about unpaid dues?",
                "क्या कार्यस्थल पर धमकी या हमला हुआ, या केवल अवैतनिक वेतन?",
                "Kya karyasthal par dhamki ya hamla hua, ya kewal avaitanik vetan?",
            ),
            _trl(
                lang,
                "Have you already sent a written demand to the employer?",
                "क्या आप नियोक्ता को लिखित माँग पहले ही भेज चुके हैं?",
                "Kya aap niyokta ko likhit mang pehle hi bhej chuke hain?",
            ),
        ]
    if dom == "criminal" or it == "police":
        return [
            _trl(
                lang,
                "When did this happen (approximate date or period)?",
                "यह कब हुआ (लगभग तारीख या अवधि)?",
                "Yah kab hua (lagbhag tarikh ya avdhi)?",
            ),
            _trl(
                lang,
                "Who was involved and what exactly occurred?",
                "कौन शामिल था और ठीक क्या हुआ?",
                "Kaun shamil tha aur theek kya hua?",
            ),
            _trl(
                lang,
                "Have you already approached the police or filed any written complaint?",
                "क्या आप पहले ही पुलिस के पास गए या कोई लिखित शिकायत दर्ज कराई?",
                "Kya aap pehle hi police ke paas gaye ya koi likhit shikayat darj karai?",
            ),
        ]
    if it in ("land_revenue", "civil_court") or "property" in dom or "civil" in dom:
        return [
            _trl(
                lang,
                "What is your relationship to the property or land (owner, tenant, buyer, other)?",
                "संपत्ति/भूमि से आपका क्या संबंध है (मालिक, किरायेदार, खरीदार, अन्य)?",
                "Sampatti/bhumi se aapka kya sambandh hai (malik, kirayedhar, kharidar, anya)?",
            ),
            _trl(
                lang,
                "Do you have documents such as title, lease, sale agreement, or notices?",
                "क्या आपके पास टाइटल, पट्टा, बिक्री करार या नोटिस जैसे दस्तावेज़ हैं?",
                "Kya aapke paas title, patta, bikri karar ya notice jaise dastavez hain?",
            ),
            _trl(
                lang,
                "Was there any force, lockout, or threat related to possession?",
                "क्या कब्ज़े से जुड़ा कोई बल, तालाबंदी या धमकी थी?",
                "Kya kabze se juda koi bal, talabandi ya dhamki thi?",
            ),
        ]
    return [
        _trl(
            lang,
            "What is the main outcome you want (e.g. payment, possession, police action, divorce, compensation)?",
            "आप मुख्यतः क्या परिणाम चाहते हैं (जैसे भुगतान, कब्ज़ा, पुलिस कार्रवाई, तलाक, मुआवज़ा)?",
            "Aap mukhytah kya parinam chahte hain (jaise bhugtan, kabza, police kararvayi, talak, muavja)?",
        ),
        _trl(
            lang,
            "When did the key events happen (approximate timeline)?",
            "मुख्य घटनाएँ कब हुईं (लगभग समयरेखा)?",
            "Mukhya ghatnayein kab huin (lagbhag samayrekha)?",
        ),
        _trl(
            lang,
            "Who are the other parties involved (person or organisation names if you have them)?",
            "अन्य पक्ष कौन हैं (नाम हो तो व्यक्ति या संगठन)?",
            "Anya paksh kaun hain (nam ho to vyakti ya sangathan)?",
        ),
        _trl(
            lang,
            "Do you have any documents, messages, or proof you can share later?",
            "क्या आपके पास बाद में साझा करने योग्य दस्तावेज़, संदेश या साक्ष्य हैं?",
            "Kya aapke paas baad mein sanja karne yogya dastavez, sandesh ya sakshya hain?",
        ),
    ]


def _coerce_questions(raw: object) -> list[str]:
    if not isinstance(raw, dict):
        return []
    arr = raw.get("questions")
    if not isinstance(arr, list):
        return []
    out: list[str] = []
    for x in arr[:6]:
        s = str(x).strip()
        if len(s) < 6 or len(s) > 320:
            continue
        out.append(s)
    return out[:4]


def generate_clarification_questions(
    text: str,
    intent: ClarificationIntent,
    *,
    response_language: str = "en",
) -> list[str]:
    """
    Ask the LLM for 2–4 short questions; on failure or short output, merge with rule-based fallback.
    """
    trimmed = (text or "").strip()[:8000]
    if not trimmed:
        return _rule_fallback_questions(intent, response_language=response_language)[:4]

    if not settings.openai_api_key:
        return _rule_fallback_questions(intent, response_language=response_language)[:4]

    ctx = json.dumps(
        {
            "user_text": trimmed,
            "intent_summary": {
                "is_hybrid": bool(intent.get("is_hybrid")),
                "domain": intent.get("domain") or "",
                "router_intent": intent.get("router_intent") or "",
                "issue_type": intent.get("issue_type") or "",
                "category": intent.get("category") or "",
            },
            "response_language": (response_language or "en").strip().lower().replace("-", "_"),
        },
        ensure_ascii=False,
    )
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": _SYSTEM + clarification_conversational_system_language_addon(response_language),
                },
                {"role": "user", "content": ctx},
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
        )
        raw = resp.choices[0].message.content
        if not raw:
            raise ValueError("empty")
        qs = _coerce_questions(json.loads(raw))
    except Exception as e:  # noqa: BLE001
        logger.info("clarification_questions_llm fallback: %s", e)
        qs = []

    if len(qs) >= 2:
        return qs[:4]

    fb = _rule_fallback_questions(intent, response_language=response_language)
    merged: list[str] = []
    seen: set[str] = set()
    for q in qs + fb:
        k = q.strip().lower()
        if k in seen or not q.strip():
            continue
        seen.add(k)
        merged.append(q.strip())
        if len(merged) >= 4:
            break
    return merged[:4] if len(merged) >= 2 else fb[:4]
