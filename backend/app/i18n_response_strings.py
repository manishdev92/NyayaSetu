"""User-visible strings keyed by `response_language` (en | hi | hi_latn)."""

from __future__ import annotations

from app.ai.evaluator import RESPONSE_DISCLAIMER


def normalize_response_lang(raw: str | None) -> str:
    s = (raw or "en").strip().lower().replace("-", "_")
    if s in ("hi", "hin"):
        return "hi"
    if s == "hi_latn":
        return "hi_latn"
    return "en"


def authority_disclaimer(lang: str | None) -> str:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return (
            "कृपया जाने या कार्रवाई करने से पहले सभी विवरण आधिकारिक सरकारी वेबसाइटों पर सत्यापित करें। "
            "NyayaSetu बाहरी डेटा की सटीकता की गारंटी नहीं देता।"
        )
    if rl == "hi_latn":
        return (
            "Kripya jane ya karwai se pehle sabhi vivaran adhikarik sarkari websites par satyapit karein. "
            "NyayaSetu bahari data ki satikta ki guarantee nahi deta."
        )
    return RESPONSE_DISCLAIMER


def suggested_authority_disclaimer_lines(lang: str | None) -> tuple[str, str]:
    """(full sentence for guidance footer, short suggestion_label)."""
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return "सुझाया गया (स्रोत डेटा सत्यापित नहीं)।", "सुझाया (स्रोत सत्यापित नहीं)"
    if rl == "hi_latn":
        return "Suggested (source data satyapit nahi).", "Suggested (source satyapit nahi)"
    return "Suggested (not verified source data).", "Suggested (not verified source data)"


def llm_fallback_explainer_suffix(lang: str | None) -> str:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return (
            "\n\nयह मार्गदर्शन नियम-आधारित पहचान व AI तर्क का मिश्रण है। "
            "कृपया प्राधिकारी व कदम आधिकारिक सरकारी स्रोतों से सत्यापित करें या योग्य वकील से परामर्श लें।"
        )
    if rl == "hi_latn":
        return (
            "\n\nYah margdarshan niyam-adharit pehchan va AI tark ka mishran hai. "
            "Kripya pradhikari va kadam adhikarik sarkari strotom se satyapit karein ya yogya vakil se paramarsh len."
        )
    return (
        "\n\nThis guidance combines rule-based detection and AI reasoning. "
        "Please verify the authority and steps from official government sources "
        "or consult a qualified advocate."
    )


def clarification_safety_intro(lang: str | None) -> str:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return "मसौदा तैयार करने से पहले सुरक्षा जाँच — कृपया संक्षेप में उत्तर दें:"
    if rl == "hi_latn":
        return "Masauda tayar karne se pehle suraksha jaanch — kripya sankshipt mein uttar dein:"
    return "Safety check before drafting — please answer briefly:"


def law_order_safety_questions(lang: str | None) -> list[str]:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return [
            "क्या यह स्थिति अभी हो रही है?",
            "क्या किसी को चोट लगी है?",
            "क्या आप तुरंत पुलिस मदद चाहते हैं?",
        ]
    if rl == "hi_latn":
        return [
            "Kya yah sthiti abhi ho rahi hai?",
            "Kya kisi ko chot lagi hai?",
            "Kya aap turant police madad chahte hain?",
        ]
    return [
        "Is the situation happening right now?",
        "Is anyone injured?",
        "Do you want police help immediately?",
    ]


def clarification_intro_llm_optional(lang: str | None) -> str:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return "वैकल्पिक: मामला स्पष्ट करने में मदद करें — आप छोड़कर आगे बढ़ सकते हैं।"
    if rl == "hi_latn":
        return "Optional: mamla spasht karne mein madad karein — aap chhodkar aage badh sakte hain."
    return "Optional: help us refine your case — you can skip and continue if you prefer."


def clarification_intro_llm_required(lang: str | None) -> str:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return (
            "मसौदा तैयार करने से पहले कुछ त्वरित प्रश्न रूटिंग व प्राधिकारियों की सटीकता के लिए मदद करेंगे।"
        )
    if rl == "hi_latn":
        return (
            "Masauda tayar karne se pehle kuch twarit prashn routing va pradhikariyon ki satikta ke liye madad karenge."
        )
    return (
        "Before we draft, a few quick intake questions will help keep routing and authorities accurate."
    )


def clarification_intro_conversational(lang: str | None) -> str:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return (
            "पूरा उत्तर तैयार करने से पहले कुछ प्रश्न सही प्राधिकारी चुनने व मार्गदर्शन सटीक रखने में मदद करेंगे।"
        )
    if rl == "hi_latn":
        return (
            "Poora uttar tayar karne se pehle kuch prashn sahi pradhikari chunne va margdarshan satik rakhne mein madad karenge."
        )
    return (
        "Before we prepare a full reply, a few quick questions will help choose the right authority "
        "and keep the guidance accurate."
    )


def yes_no_labels(lang: str | None) -> tuple[str, str]:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return ("हाँ", "नहीं")
    if rl == "hi_latn":
        return ("Haan", "Nahi")
    return ("Yes", "No")


def yes_no_not_sure_labels(lang: str | None) -> tuple[str, str, str]:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return ("हाँ", "नहीं", "पक्का नहीं")
    if rl == "hi_latn":
        return ("Haan", "Nahi", "Pakka nahi")
    return ("Yes", "No", "Not sure")


def clarification_agent_system_language_addon(lang: str | None) -> str:
    """Append to LLM clarification agent system prompt so questions/options match UI language."""
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return (
            "\n\n## RESPONSE_LANGUAGE (mandatory)\n"
            "Write every `question`, every string in `options`, and the `reason` field in **Hindi (Devanagari)**.\n"
            "For `type` \"yes_no\", `options` MUST be exactly [\"हाँ\", \"नहीं\"] in that order.\n"
            "Keep JSON keys and each `id` in ASCII snake_case only.\n"
        )
    if rl == "hi_latn":
        return (
            "\n\n## RESPONSE_LANGUAGE (mandatory)\n"
            "Write every `question`, every `options` entry, and `reason` in **Roman Hindi** "
            "(Latin letters only; no Devanagari).\n"
            "For `type` \"yes_no\", `options` MUST be exactly [\"Haan\", \"Nahi\"].\n"
            "Keep JSON keys and each `id` in ASCII snake_case.\n"
        )
    return ""


def clarification_conversational_system_language_addon(lang: str | None) -> str:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return (
            "\n\n## RESPONSE_LANGUAGE (mandatory)\n"
            "Every string in the `questions` array must be **Hindi (Devanagari)** — short, one sentence each.\n"
        )
    if rl == "hi_latn":
        return (
            "\n\n## RESPONSE_LANGUAGE (mandatory)\n"
            "Every string in `questions` must be **Roman Hindi** only (Latin script; no Devanagari).\n"
        )
    return ""


def clarification_more_detail_explanation(lang: str | None) -> str:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return (
            "आपके संदेश में थोड़ा और विवरण चाहिए ताकि सही मंच चुना जा सके "
            "(सिविल न्यायालय, पुलिस/FIR, श्रम प्राधिकरण, उपभोक्ता आयोग आदि)। कृपया नीचे दिए प्रश्न का उत्तर दें।"
        )
    if rl == "hi_latn":
        return (
            "Aapke sandesh mein thoda aur vivaran chahiye taaki sahi manch chuna ja sake "
            "(civil nyayalay, police/FIR, shram pradhikaran, upbhokta ayog aadi). "
            "Kripya neeche diye prashn ka uttar dein."
        )
    return (
        "Your message needs a little more detail so we can choose the correct forum "
        "(civil court, police/FIR, labour authority, consumer commission, etc.). "
        "Please answer the question below."
    )


def clarification_next_hint_select_points(lang: str | None) -> str:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return (
            "नीचे प्रत्येक बिंदु के लिए एक विकल्प चुनें, फिर जारी रखने हेतु अपने उत्तर भेजें "
            "(या अपना उत्तर टाइप करें)।"
        )
    if rl == "hi_latn":
        return (
            "Neeche pratyek bindu ke liye ek vikalp chunen, phir jari rakhne hetu apna uttar bhejen "
            "(ya apna uttar type karen)."
        )
    return (
        "Select one option for each point below, then submit your choices to continue (or type your own reply)."
    )


def clarification_next_hint_optional_agent(lang: str | None) -> str:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return (
            "वैकल्पिक: नीचे एक संदेश में उत्तर दें, या 'स्पष्टीकरण छोड़ें' चुनकर आगे बढ़ें।"
        )
    if rl == "hi_latn":
        return (
            "Optional: neeche ek sandesh mein uttar dein, ya skip clarification chun kar aage badhen."
        )
    return "Optional: answer in one message below, or send again with skip clarification if you prefer not to."


def clarification_next_hint_answer_each(lang: str | None) -> str:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return (
            "प्रत्येक प्रश्न का उत्तर एक ही संदेश में लिखकर फिर भेजें — मसौदे से पहले हम केवल एक बार पूछते हैं।"
        )
    if rl == "hi_latn":
        return (
            "Pratyek prashn ka uttar ek hi sandesh mein likh kar phir bhejen — masaude se pehle hum sirf ek baar poochte hain."
        )
    return "Answer each question in one message below and send again — we only ask once before drafting."


def clarification_next_hint_choose_opts(lang: str | None) -> str:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return (
            "ऊपर दिए विकल्प में से चुनें या अपने शब्दों में उत्तर दें, फिर रूटिंग पूरी करने हेतु फिर भेजें।"
        )
    if rl == "hi_latn":
        return (
            "Upar diye vikalp mein se chunen ya apne shabdon mein uttar dein, phir routing puri karne hetu phir bhejen."
        )
    return "Choose an option above or reply in your own words, then send again so we can finalize routing."


def clarification_next_hint_reply_free(lang: str | None) -> str:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return "अनुरोधित स्पष्टीकरण दें, फिर जनरेट फिर चलाएँ।"
    if rl == "hi_latn":
        return "Anurodhit spashtikaran dein, phir generate phir chalayein."
    return "Reply with the requested clarification, then run generate again."


def clarification_authority_warning_optional(lang: str | None) -> str:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return (
            "वैकल्पिक स्पष्टीकरण — वर्गीकरण आउटपुट वही रहेगा; आप छोड़कर आगे बढ़ सकते हैं।"
        )
    if rl == "hi_latn":
        return (
            "Optional spashtikaran — vargikaran output wahi rahega; aap chhodkar aage badh sakte hain."
        )
    return "Optional clarification — classifier output is unchanged; you may skip and continue."


def clarification_authority_warning_required(lang: str | None) -> str:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return "रूटिंग से पहले स्पष्टीकरण आवश्यक है।"
    if rl == "hi_latn":
        return "Routing se pehle spashtikaran avashyak hai."
    return "Clarification required before routing."


def extreme_uncertainty_clarifying_questions(lang: str | None) -> list[str]:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return [
            "एक-दो वाक्यों में: मुख्य समस्या क्या है?",
            "यह कहाँ हुआ (ज़िला / राज्य)?",
            "पहले आपको किस मार्ग की ज़रूरत है — पुलिस, न्यायालय, या सरकारी दफ़्तर?",
        ]
    if rl == "hi_latn":
        return [
            "Ek-do vakyon mein: mukhya samasya kya hai?",
            "Yah kahan hua (zila / rajya)?",
            "Pehle aapko kis marg ki zarurat hai — police, nyayalay, ya sarkari daftar?",
        ]
    return [
        "In one or two sentences: what is the main problem?",
        "Where did it happen (district / state)?",
        "Which path do you need first — police, court, or a government office?",
    ]


def extreme_uncertainty_clarification_intro(lang: str | None) -> str:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return (
            "मसौदे से पहले थोड़ा और स्पष्टता चाहिए — रूटिंग अभी सुरक्षित उत्तर हेतु पर्याप्त विशिष्ट नहीं है।"
        )
    if rl == "hi_latn":
        return (
            "Masaude se pehle thodi aur spashta chahiye — routing abhi surakshit uttar hetu paryapt visisht nahi hai."
        )
    return "We need a little more clarity before drafting — routing is not yet specific enough for a safe reply."


def stream_phase_analyzing(lang: str | None) -> str:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return "आपका मुद्दा समझा जा रहा है…"
    if rl == "hi_latn":
        return "Aapka mudda samjha ja raha hai…"
    return "Analyzing your issue…"


def stream_phase_urgent_violence(lang: str | None) -> str:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return "⚠️ तत्काल: प्रतीत होता है कि हिंसा शामिल है। आपको तुरंत पुलिस से संपर्क करना चाहिए।"
    if rl == "hi_latn":
        return "⚠️ Tatkal: prateet hota hai ki hinsa shamil hai. Aapko turant police se sampark karna chahiye."
    return "⚠️ Urgent: This appears to involve violence. You should contact police immediately."


def _domain_slug_display(lang: str | None, domain_slug: str) -> str:
    """Map router domain slug for SSE (English slug from meta.domain)."""
    rl = normalize_response_lang(lang)
    low = (domain_slug or "").strip().lower()
    if rl == "hi":
        hi = {
            "general": "सामान्य",
            "criminal": "आपराधिक",
            "civil": "नागरिक",
            "consumer": "उपभोक्ता",
            "cyber": "साइबर",
            "labour": "श्रम",
            "family": "पारिवारिक",
            "traffic": "यातायात",
            "financial": "वित्तीय",
            "police complaint": "पुलिस शिकायत",
        }
        return hi.get(low, domain_slug)
    if rl == "hi_latn":
        latn = {
            "general": "samanya",
            "criminal": "aapradhik",
            "civil": "nagrik",
            "consumer": "upbhokta",
            "cyber": "cyber",
            "labour": "shram",
            "family": "parivarik",
            "traffic": "yatayat",
            "financial": "vitiya",
            "police complaint": "police shikayat",
        }
        return latn.get(low, domain_slug)
    return domain_slug


def stream_phase_domain_check(lang: str | None, domain_slug: str) -> str:
    """domain_slug is humanized domain (spaces, not underscores)."""
    rl = normalize_response_lang(lang)
    disp = _domain_slug_display(lang, domain_slug)
    if rl == "hi":
        return (
            f"यह {disp} से संबंधित मुद्दा प्रतीत होता है। "
            "विश्वास व सुरक्षा नियमों की जाँच…"
        )
    if rl == "hi_latn":
        return (
            f"Yah {disp} se sambandhit mudda prateet hota hai. "
            "Vishwas va suraksha niyamon ki jaanch…"
        )
    return (
        f"This looks like a {domain_slug}-related issue. "
        "Checking confidence and safety rules…"
    )


def stream_phase_preparing(lang: str | None) -> str:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return "कानूनी मार्गदर्शन व मसौदा तैयार किया जा रहा है…"
    if rl == "hi_latn":
        return "Kanuni margdarshan va masauda tayar kiya ja raha hai…"
    return "Preparing your legal guidance and draft…"


def stream_phase_clarification_banner(
    lang: str | None, *, optional: bool, has_agent_q: bool, multi_q: bool
) -> str:
    rl = normalize_response_lang(lang)
    if optional:
        return clarification_intro_llm_optional(lang)
    if has_agent_q:
        if rl == "hi":
            return "मसौदा से पहले कुछ लक्षित स्पष्टीकरण प्रश्न।"
        if rl == "hi_latn":
            return "Masauda se pehle kuch lakshit spashtikaran prashn."
        return "A few targeted clarification questions before we draft."
    if multi_q:
        if rl == "hi":
            return "मसौदा से पहले कुछ प्रश्न मदद करेंगे।"
        if rl == "hi_latn":
            return "Masauda se pehle kuch prashn madad karenge."
        return "A few quick questions will help before we draft anything."
    if rl == "hi":
        return "मसौदा से पहले एक स्पष्टीकरण चाहिए।"
    if rl == "hi_latn":
        return "Masauda se pehle ek spashtikaran chahiye."
    return "I need one clarification before drafting anything."
