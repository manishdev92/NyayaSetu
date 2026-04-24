"""Localized UI copy for legal overview, procedure steps, hierarchy, and urgent next-steps (hi / hi_latn)."""

from __future__ import annotations

from app.i18n_response_strings import normalize_response_lang

# (router_intent_key, step_order) -> (label, description_template with {district})
_HIER_HI: dict[tuple[str, int], tuple[str, str]] = {
    ("criminal_police", 1): (
        "स्थानीय पुलिस स्टेशन (SHO)",
        "संज्ञेय अपराधों हेतु लिखित शिकायत या FIR दर्ज कराएँ। {district} हेतु क्षेत्राधिकार वाला स्टेशन राज्य पुलिस के आधिकारिक पोर्टल से पुष्टि करें।",
    ),
    ("criminal_police", 2): (
        "पुलिस अधीक्षक (SP)",
        "यदि स्टेशन बिना वैध आधार संज्ञेय FIR दर्ज करने से इनकार करे या जाँच अनुचित रूप से विलंबित हो, तो आधिकारिक परिपत्रों व लिखित प्रतिनिधित्व के अनुसार बढ़ाव करें।",
    ),
    ("criminal_police", 3): (
        "न्यायिक उपचार (जहाँ कानूनी सलाह हो)",
        "तथ्यों के आधार पर योग्य वकील से मजिस्ट्रेट शिकायत जैसे मार्गों पर India Code व आधिकारिक न्यायालय जानकारी के माध्यम से चर्चा करें — सोशल मीडिया सारांश नहीं।",
    ),
    ("general_issue", 1): (
        "सही विभाग चुनें",
        "{district} के लिए आधिकारिक .gov.in पोर्टलों से पुलिस, श्रम, उपभोक्ता, राजस्व या नगरपालिका मार्ग पहचानें — सोशल मीडिया से अनुमान न लगाएँ।",
    ),
    ("general_issue", 2): (
        "दस्तावेज़ व समय-सारणी जुटाएँ",
        "दिनांकित साक्ष्य (संदेश, अनुबंध, बिल) तैयार रखें; सीमा काल आधिकारिक स्रोतों या वकील से नोट करें।",
    ),
}

_HIER_LATN: dict[tuple[str, int], tuple[str, str]] = {
    ("criminal_police", 1): (
        "Sthaniya police station (SHO)",
        "Sanjneya apradhon hetu likhit shikayat ya FIR darj karaen. {district} hetu kshetradhikar wala station rajya police ke adhikarik portal se pushti karein.",
    ),
    ("criminal_police", 2): (
        "Police Adhikshak (SP)",
        "Yadi station bina vaidh aadhar sanjneya FIR darj karne se inkaar kare ya jaanch anuchit roop se vilambit ho, to adhikarik paripatron va likhit pratinidhitva ke anusar badhav karein.",
    ),
    ("criminal_police", 3): (
        "Nyayik upchar (jahan kanuni salah ho)",
        "Tathyon ke aadhar par yogya vakil se magistrate shikayat jaise margon par India Code va adhikarik nyayalay jaankari ke madhyam se charcha karein.",
    ),
    ("general_issue", 1): (
        "Sahi vibhag chunen",
        "{district} ke liye adhikarik .gov.in portalon se police, shram, upbhokta, rajasva ya nagarpalika marg pahchanen — social media se anuman na lagayen.",
    ),
    ("general_issue", 2): (
        "Dastavez va samay-sarani jutaen",
        "Dinankit sakshya (sandesh, anubandh, bill) tayyar rakhen; sima kaal adhikarik strotom ya vakil se note karein.",
    ),
}


def localize_hierarchy_step(
    router_key: str,
    order: int,
    label_en: str,
    desc_en: str,
    district_display: str,
    lang: str | None,
) -> tuple[str, str]:
    rl = normalize_response_lang(lang)
    if rl == "en":
        return label_en, desc_en
    tab = _HIER_HI if rl == "hi" else _HIER_LATN
    hit = tab.get((router_key, order))
    if not hit:
        return label_en, desc_en
    lab, tmpl = hit
    return lab, tmpl.replace("{district}", district_display)


def urgency_next_steps_prefix(lang: str | None) -> list[str]:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return [
            "⚠️ तत्काल कार्रवाई — यदि तत्काल खतरा या गंभीर संज्ञेय अपराध हो तो बिना देरी निकटतम पुलिस स्टेशन जाएँ।",
            "तुरंत 112 डायल करें (भारत आपात); पुलिस हेतु जहाँ लागू हो 100 भी उपयोग कर सकते हैं।",
            "धारा पाठ हेतु आधिकारिक India Code: https://www.indiacode.nic.in/",
        ]
    if rl == "hi_latn":
        return [
            "⚠️ Tatkal karwai — yadi tatkal khatra ya gambhir sanjneya apradh ho to bina deri nikatatam police station jayen.",
            "Turant 112 dial karein (Bharat aapat); police hetu jahan lagu ho 100 bhi upayog kar sakte hain.",
            "Dhara path hetu adhikarik India Code: https://www.indiacode.nic.in/",
        ]
    return [
        "⚠️ Urgent Action Required — If there is immediate danger or a serious cognizable offence, go to the nearest police station without delay.",
        "Dial 112 immediately (India emergency); for police you may also use 100 where applicable.",
        "Official India Code for statute text: https://www.indiacode.nic.in/",
    ]


def cyber_urgency_insert(lang: str | None, portal_url: str) -> str:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return (
            f"राष्ट्रीय साइबर अपराध पोर्टल ({portal_url}) के माध्यम से रिपोर्ट व साक्ष्य सुरक्षित रखें — "
            "स्क्रीनशॉट, लेन-देन ID व उपकरण विवरण।"
        )
    if rl == "hi_latn":
        return (
            f"Rashtriya cyber apradh portal ({portal_url}) ke madhyam se report va sakshya surakshit rakhen — "
            "screenshot, len-den ID va upakaran vivaran."
        )
    return (
        f"Report and preserve evidence via the National Cyber Crime Reporting Portal ({portal_url}). "
        "Keep screenshots, transaction IDs, and device details."
    )


_PROCEDURE_HI: dict[str, list[str]] = {
    "corporate": [
        "कंपनी दस्तावेज़, हिस्सेदारी व बोर्ड/AGM रिकॉर्ड जुटाएँ।",
        "राहत NCLT (दमन, समापन) या नागरिक न्यायालय — कानूनी सलाह से पुष्टि करें।",
        "केवल आधिकारिक पोर्टलों के निर्धारित प्रारूपों से दाखिल करें; अपील NCLAT/उच्च न्यायालय मार्ग कानूनानुसार।",
    ],
    "salary": [
        "रोज़गार रिकॉर्ड, वेतन पर्ची व लिखित संचार जुटाएँ।",
        "ज़िला श्रम कार्यालय / सहायक श्रम आयुक्त (या राज्य द्वारा निर्धारित प्राधिकरण) मार्ग अपनाएँ।",
        "यदि सुलह असफल हो या विवाद श्रम अधिकारी के दायरे से बाहर हो, तो आधिकारिक स्रोतों या वकील से ट्रिब्यूनल/न्यायालय क्षेत्राधिकार पुष्टि करें।",
    ],
    "traffic": [
        "चालान नोटिस, वाहन दस्तावेज़ व फोटो/रसीद सुरक्षित रखें।",
        "राज्य परिवहन / ई-चालान पोर्टल से सत्यापित व आपत्ति करें।",
        "लाइसेंस/RTO मामलों में RTO प्रक्रिया; जुर्माने हेतु आधिकारिक नोटिस पर वर्णित अपील मार्ग।",
    ],
    "cyber": [
        "बैंक/UPI लॉग, SMS, स्क्रीनशॉट व लेन-देन ID सुरक्षित रखें।",
        "क्षेत्रीय साइबर सेल / पुलिस स्टेशन में शिकायत व राष्ट्रीय रिपोर्टिंग मार्ग उपयोग करें।",
        "लिखित में अनुवर्तन करें व सभी पावतियों की प्रति रखें।",
    ],
    "land": [
        "शीर्षक दस्तावेज़, सर्वे मानचित्र व राजस्व निकाले उपलब्ध जुटाएँ।",
        "निर्धारित फॉर्मों से तहसील/राजस्व कार्यालय में उत्परिवर्तन व दस्तावेज़ सुधार हेतु संपर्क करें।",
        "कब्ज़ा या शीर्षक विवाद हेतु आधिकारिक स्रोतों या वकील से नागरिक उपचार पर मार्गदर्शन लें।",
    ],
    "police": [
        "तारीख, स्थान व गवाहों (यदि हों) के साथ स्पष्ट तथ्यात्मक शिकायत लिखें।",
        "क्षेत्राधिकार वाले पुलिस स्टेशन जाएँ; FIR दर्ज होने पर प्रति माँगें।",
        "कानून द्वारा अनुमत पदानुक्रमित प्रतिनिधित्व ही करें व प्रतियाँ रखें।",
    ],
    "family": [
        "विवाद से जुड़े विवाह पंजी, वित्तीय रिकॉर्ड व संचार जुटाएँ।",
        "आधिकारिक न्यायालय वेबसाइट या कानूनी सहायता से सही पारिवारिक न्यायालय/मंच क्षेत्राधिकार पहचानें।",
        "यदि अनिवार्य हो तो विवादित सुनवाई से पहले मध्यस्थता आवश्यकतों का पालन करें।",
    ],
    "consumer": [
        "चालान, वारंटी कार्ड व विक्रेता/सेवा प्रदाता को लिखित शिकायतें सुरक्षित रखें।",
        "परिधि सीमा के अनुसार सही उपभोक्ता आयोग में आधिकारिक ई-दाखिल प्रारूप से दाखिल करें।",
        "दाखिला प्रमाण व निर्देशानुसार सुनवाई में उपस्थित रहें।",
    ],
    "fraud": [
        "समय-सारणी, बैंक रिकॉर्ड व आपसे संवाद करने वाली पहुँचों का दस्तावेज़ीकरण करें।",
        "क्षेत्रीय पुलिस में FIR/शिकायत दर्ज कर जाँच में सहयोग करें।",
        "अतिरिक्त धन स्थानांतरण न करें; केवल आधिकारिक संचार चैनल अपनाएँ।",
    ],
    "general": [
        "स्पष्ट समय-सारणी लिखें व पहले से मौजूद दस्तावेज़ जुटाएँ।",
        "आधिकारिक राज्य पोर्टलों से मुद्दा नागरिक, आपराधिक, राजस्व या नियामक है या नहीं पहचानें।",
        "सही विभाग हेतु ज़िला प्रशासन या कानूनी सेवा प्राधिकरण से मार्गदर्शन लें।",
    ],
}

_PROCEDURE_LATN: dict[str, list[str]] = {
    "corporate": [
        "Company documents, shareholding va board/AGM records jutaen.",
        "Rahat NCLT (daman, samapan) ya nagrik nyayalay — kanuni salah se pushti karein.",
        "Keval adhikarik portalon ke nirdharit praroopon se dakhil karen; appeal NCLAT/uchch nyayalay marg kanunanusar.",
    ],
    "salary": [
        "Rojgar record, vetan parchi va likhit sanchar jutaen.",
        "Zila shram karyalay / sahyak shram ayukt (ya rajya dvara nirdharit pradhikaran) marg apnaen.",
        "Yadi sulah asaphal ho ya vivad shram adhikari ke dayre se bahar ho, to adhikarik strotom ya vakil se tribunal/nyayalay kshetradhikar pushti karein.",
    ],
    "traffic": [
        "Chalan notice, vahan documents va photo/rasid surakshit rakhen.",
        "Rajya parivahan / e-chalan portal se satyapit va aapatti karen.",
        "License/RTO mamalon mein RTO prakriya; jurmane hetu adhikarik notice par varnit appeal marg.",
    ],
    "cyber": [
        "Bank/UPI log, SMS, screenshot va len-den ID surakshit rakhen.",
        "Kshetriya cyber cell / police station mein shikayat va rashtriya reporting marg upayog karen.",
        "Likhit mein anuvartan karen va sabhi pavation ki pratilipi rakhen.",
    ],
    "land": [
        "Shirshak dastavez, survey manchitra va rajasva nikale uplabdh jutaen.",
        "Nirdharit formon se tehsil/rajvas karyalay mein utparivartan va dastavez sudhar hetu sampark karen.",
        "Kabza ya shirshak vivad hetu adhikarik strotom ya vakil se nagrik upchar par margdarshan len.",
    ],
    "police": [
        "Tarikh, sthan va gavahon (yadi hon) ke saath spasht tathyatmak shikayat likhen.",
        "Kshetradhikar wale police station jayen; FIR darj hone par prati mangen.",
        "Kanoon dwara anumit padanukramit pratinidhitva hi karen va pratiyan rakhen.",
    ],
    "family": [
        "Vivad se judde vivah panji, vitiya record va sanchar jutaen.",
        "Adhikarik nyayalay website ya kanuni sahayata se sahi parivarik nyayalay/manch kshetradhikar pahchanen.",
        "Yadi anivary ho to vivadit sunvai se pehle madhyasthta avashyaktaon ka palan karen.",
    ],
    "consumer": [
        "Chalan, warranty card va vikreta/seva pradata ko likhit shikayaten surakshit rakhen.",
        "Pariidhi sima ke anusar sahi upbhokta ayog mein adhikarik e-daakhil praroop se dakhilen.",
        "Dakhila praman va nirdeshanusar sunvai mein upasthit rahen.",
    ],
    "fraud": [
        "Samay-sarani, bank record va aapse sanvad karne wali pahonchon ka dastavejikaran karen.",
        "Kshetriya police mein FIR/shikayat darj kar jaanch mein sahayog karen.",
        "Atirikt dhan sthanantaran na karen; keval adhikarik sanchar chainal apnaen.",
    ],
    "general": [
        "Spasht samay-sarani likhen va pehle se maujud dastavez jutaen.",
        "Adhikarik rajya portalon se mudda nagrik, aapradhik, rajasva ya niyamak hai ya nahi pahchanen.",
        "Sahi vibhag hetu zila prashasan ya kanuni seva pradhikaran se margdarshan len.",
    ],
}


def procedure_steps_localized(issue_type: str, lang: str | None) -> list[str] | None:
    rl = normalize_response_lang(lang)
    if rl not in ("hi", "hi_latn"):
        return None
    tab = _PROCEDURE_HI if rl == "hi" else _PROCEDURE_LATN
    return list(tab.get(issue_type) or tab["general"])


_ISSUE_TYPE_LABEL_HI: dict[str, str] = {
    "police": "पुलिस",
    "fraud": "धोखाधड़ी",
    "general": "सामान्य",
    "consumer": "उपभोक्ता",
    "cyber": "साइबर",
    "civil_dispute": "नागरिक विवाद",
    "salary": "वेतन / श्रम",
    "traffic": "यातायात",
    "land": "भूमि / राजस्व",
    "family": "पारिवारिक",
    "corporate": "कॉर्पोरेट",
    "rti": "RTI",
    "civic": "नगरपालिका",
    "financial": "वित्तीय",
    "education": "शिक्षा",
    "women_child": "महिला व बाल",
    "senior_citizen": "वरिष्ठ नागरिक",
    "police_oversight": "पुलिस पर्यवेक्षण",
}

_ISSUE_TYPE_LABEL_LATN: dict[str, str] = {
    "police": "Police",
    "fraud": "Dhokhadhadhi",
    "general": "Samanya",
    "consumer": "Upbhokta",
    "cyber": "Cyber",
    "civil_dispute": "Nagrik vivad",
    "salary": "Vetan / shram",
    "traffic": "Yatayat",
    "land": "Bhumi / rajasva",
    "family": "Parivarik",
    "corporate": "Corporate",
    "rti": "RTI",
    "civic": "Nagarpalika",
    "financial": "Vitiya",
    "education": "Shiksha",
    "women_child": "Mahila va baal",
    "senior_citizen": "Varishth nagarik",
    "police_oversight": "Police paryavekshan",
}


def issue_type_display(issue_type: str, lang: str | None) -> str:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return _ISSUE_TYPE_LABEL_HI.get(issue_type, issue_type)
    if rl == "hi_latn":
        return _ISSUE_TYPE_LABEL_LATN.get(issue_type, issue_type)
    return issue_type


_SEV_HI = {"low": "निम्न", "medium": "मध्यम", "high": "उच्च"}
_SEV_LATN = {"low": "nimn", "medium": "madhyam", "high": "uchch"}

_JUR_HI = {
    "district": "ज़िला",
    "state": "राज्य",
    "national": "राष्ट्रीय",
    "local": "स्थानीय",
}
_JUR_LATN = {
    "district": "Zila",
    "state": "Rajya",
    "national": "Rashtriya",
    "local": "Sthaniya",
}


def severity_display(sev: str, lang: str | None) -> str:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return _SEV_HI.get(sev, sev)
    if rl == "hi_latn":
        return _SEV_LATN.get(sev, sev)
    return sev


def jurisdiction_display(jt: str, lang: str | None) -> str:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return _JUR_HI.get(jt, jt)
    if rl == "hi_latn":
        return _JUR_LATN.get(jt, jt)
    return jt


def legal_education_disclaimer(lang: str | None) -> str:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return (
            "यह सार शैक्षणिक है। India Code या आधिकारिक पोर्टलों पर धारा पाठ सत्यापित करें। "
            "यह कानूनी सलाह नहीं — अपनी स्थिति हेतु योग्य वकील से परामर्श लें।"
        )
    if rl == "hi_latn":
        return (
            "Yah saar shakshnik hai. India Code ya adhikarik portalon par dhara path satyapit karein. "
            "Yah kanuni salah nahi — apni sthiti hetu yogya vakil se paramarsh len."
        )
    return (
        "This summary is educational. Confirm statute text on India Code or official portals. "
        "This is not legal advice — consult a qualified advocate for your situation."
    )


def no_rag_match_message(lang: str | None) -> str:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return (
            "क्यूरेटेड कानूनी डेटाबेस में इस प्रश्न व मुद्दा प्रकार हेतु मजबूत मेल नहीं मिला। "
            "केवल सामान्य सरकारी प्रक्रिया मार्गदर्शन उपयोग करें व किसी भी धारा को "
            "https://www.indiacode.nic.in या राज्य पोर्टल पर सत्यापित करें।"
        )
    if rl == "hi_latn":
        return (
            "Curated kanuni database mein is prashn va mudda prakar hetu majboot mel nahi mila. "
            "Keval samanya sarkari prakriya margdarshan upayog karen va kisi bhi dhara ko India Code ya rajya portal par satyapit karein."
        )
    return (
        "No strong legal match was found in the curated legal database for this query and issue type. "
        "Use general government procedure guidance only, and verify any statute on "
        "https://www.indiacode.nic.in or your state portal. Do not treat uncited detail as authoritative."
    )


def rag_header_sub(lang: str | None, rag_label: str) -> tuple[str, str]:
    rl = normalize_response_lang(lang)
    if rag_label == "rag_retrieved":
        if rl == "hi":
            return (
                "निकाले गए कानूनी संदर्भ (RAG-आधारित)",
                "नीचे के अंश क्यूरेटेड स्टोर से रैंक किए गए (जहाँ उपलब्ध हो एम्बेडिंग समानता)।",
            )
        if rl == "hi_latn":
            return (
                "Nikale gaye kanuni sandarbh (RAG-adharit)",
                "Neeche ke ansh curated store se rank kiye gaye (jahan uplabdh ho embedding samanta).",
            )
        return (
            "Retrieved Legal References (RAG-based)",
            "Chunks below were ranked from the curated store (embedding similarity when available).",
        )
    if rl == "hi":
        return (
            "सामान्य कानूनी संदर्भ (मामला-विशिष्ट पुनर्प्राप्ति नहीं)",
            "पुनर्प्राप्ति भरोसा सीमित है (जैसे कीवर्ड फॉलबैक या कम समानता)। "
            "हर बिंदु India Code पर पुष्टि करें — स्कोर को कानूनी प्रमाण न मानें।",
        )
    if rl == "hi_latn":
        return (
            "Samanya kanuni sandarbh (mamla-vishisht punarprapti nahi)",
            "Punarprapti bharosa simit hai (jaise keyword fallback ya kam samanta). "
            "Har bindu India Code par pushti karen — score ko kanuni praman na maanen.",
        )
    return (
        "General Legal References (Not case-specific retrieval)",
        "Retrieval confidence is limited (e.g. keyword fallback or low similarity). "
        "Confirm every point on India Code — do not treat scores as legal proof.",
    )


def law_line_prefixes(lang: str | None) -> tuple[str, str]:
    rl = normalize_response_lang(lang)
    if rl == "hi":
        return "प्राप्ति स्कोर", "सत्यापित"
    if rl == "hi_latn":
        return "Prapti score", "Satyapit"
    return "retrieval_score", "verified"
