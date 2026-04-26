/** Localized GTM bundles + path helper for / vs /hi. */

export type MarketingLocale = "en" | "hi";

export function mpath(locale: MarketingLocale, path: string): string {
  const p = path === "/" || path === "" ? "" : path.startsWith("/") ? path : `/${path}`;
  if (locale === "en") return p === "" ? "/" : p;
  return p === "" ? "/hi" : `/hi${p}`;
}

export type NavItem = { path: string; label: string };

export type MarketingBundle = {
  locale: MarketingLocale;
  nav: NavItem[];
  chrome: {
    signIn: string;
    openApp: string;
    menu: string;
    product: string;
    account: string;
    buildHost: string;
    assistant: string;
    dashboard: string;
    signInViaApp: string;
    footerLegal: string;
  };
  disclaimerShort: string;
  copyright: string;
  /** NyayGuru-style subtitle, e.g. “Legal clarity for India”. */
  brandTagline: string;
  hero: {
    kicker: string;
    title: string;
    subtitle: string;
    primaryCta: string;
    secondaryCta: string;
  };
  home: {
    trustH2: string;
    pillarsH2: string;
    pillarsSub: string;
    fullFeatureLink: string;
    ctaH2: string;
    ctaSub: string;
    ctaButton: string;
  };
  trustPoints: { title: string; body: string }[];
  featureBlocks: { title: string; body: string }[];
  howItWorksSteps: { step: string; title: string; body: string }[];
  pricingNotes: {
    intro: string;
    title: string;
    tiers: { name: string; price: string; blurb: string; bullets: string[] }[];
    openApp: string;
  };
  faqItems: { q: string; a: string }[];
  aboutParagraphs: string[];
  aboutTitle: string;
  aboutCta: string;
  featuresTitle: string;
  featuresIntro: string;
  featuresLaunch: string;
  howTitle: string;
  howIntro: string;
  howTry: string;
  faqTitle: string;
  faqBack: string;
  contactTitle: string;
  contactIntro: string;
  contactEmailLabel: string;
  contactNoEmail: string;
  contactNote: string;
  blogTitle: string;
  blogIntro: string;
  blogSoon: string;
  liveCaps: {
    title: string;
    loading: string;
    offline: string;
    dailyAuth: string;
    dailyPro: string;
    paywall: string;
    billingMode: string;
    rag: string;
    stripeCheckout: string;
    stripePortal: string;
  };
};

const EN: MarketingBundle = {
  locale: "en",
  nav: [
    { path: "/features", label: "Features" },
    { path: "/how-it-works", label: "How it works" },
    { path: "/pricing", label: "Pricing" },
    { path: "/faq", label: "FAQ" },
    { path: "/about", label: "About" },
    { path: "/blog", label: "Blog" },
    { path: "/contact", label: "Contact" },
  ],
  chrome: {
    signIn: "Sign in",
    openApp: "Open app",
    menu: "Menu",
    product: "Product",
    account: "Account",
    buildHost: "Build & host",
    assistant: "Assistant",
    dashboard: "Dashboard",
    signInViaApp: "Sign in via app",
    footerLegal:
      "Marketing pages ship with Next.js and are static-friendly. For a pure static bucket (e.g. S3), export or mirror these routes behind CloudFront and keep the assistant API on App Runner or similar.",
  },
  disclaimerShort:
    "NyayaSetu is not a law firm and does not provide legal advice. Outputs are for education and drafting assistance only.",
  copyright: "Educational tool—not a law firm.",
  brandTagline: "Legal clarity for India",
  hero: {
    kicker: "NyayaSetu",
    title: "Clarity for everyday legal steps in India",
    subtitle:
      "Describe your issue in plain language. Get structured guidance, authority-aware drafting, and practical next steps—with safety gates for emergencies and clear disclaimers.",
    primaryCta: "Open the assistant",
    secondaryCta: "See how it works",
  },
  home: {
    trustH2: "Why teams ship NyayaSetu",
    pillarsH2: "Product pillars",
    pillarsSub:
      "Comparable in spirit to full-funnel legal AI sites—without promising case-law databases you have not licensed.",
    fullFeatureLink: "Full feature list",
    ctaH2: "Ready to try the assistant?",
    ctaSub: "Use the same deployment your organisation configures—RAG mode, limits, and billing follow the API.",
    ctaButton: "Open NyayaSetu",
  },
  trustPoints: [
    {
      title: "Grounded on curated sources",
      body: "Retrieval is tuned for Indian legal context where your deployment enables it (local knowledge base or vector index). Always verify on official portals.",
    },
    {
      title: "Citizen and lawyer paths",
      body: "A general-user mode and an optional professional mode (when your org enables it) for deeper context windows—not a substitute for licensing or court filings advice.",
    },
    {
      title: "Privacy-conscious by design",
      body: "Sign in when you need saved limits or billing. Review your deployment privacy policy for retention and region.",
    },
  ],
  featureBlocks: [
    {
      title: "Chat-first guidance",
      body: "Streaming responses, clarifying questions when routing is uncertain, and explanations in English or Hindi-style locales supported by the app.",
    },
    {
      title: "Document drafting",
      body: "Task types include full letters, Q&A-first answers, and consumer complaint filing helpers—formatted for print where appropriate.",
    },
    {
      title: "Local authority context",
      body: "When your directory data matches, the assistant surfaces verified or suggested offices; otherwise it stays transparent about limits.",
    },
    {
      title: "Uploads & OCR (when enabled)",
      body: "Attach PDFs or images where your API is configured for ingest and OCR—useful for notices and orders.",
    },
    {
      title: "Optional research hints",
      body: "Lawyer-oriented panels can show external research snippets when your backend enables them—never a replacement for official judgments.",
    },
    {
      title: "Offline queue (PWA)",
      body: "Failed requests can be queued when connectivity returns—check your product configuration.",
    },
  ],
  howItWorksSteps: [
    {
      step: "1",
      title: "Describe your situation",
      body: "Type or use voice where supported. You can add your city and contact details for drafts.",
    },
    {
      step: "2",
      title: "We route and clarify",
      body: "If the issue is ambiguous, the assistant asks before assigning an authority or generating a long draft.",
    },
    {
      step: "3",
      title: "Review and verify",
      body: "Read the draft and next steps. Confirm statutes, forums, and contacts on government sites or with a qualified advocate.",
    },
  ],
  pricingNotes: {
    intro:
      "NyayaSetu is built so each deployment can set its own limits and billing. The values below describe a typical setup; your live app shows actual caps after sign-in.",
    title: "Pricing",
    tiers: [
      {
        name: "Guest",
        price: "Free",
        blurb: "Try the assistant with a modest daily request budget.",
        bullets: ["No account required on many deployments", "Good for one-off questions"],
      },
      {
        name: "Signed in",
        price: "Free",
        blurb: "Higher daily limits when you authenticate (e.g. Clerk).",
        bullets: ["Usage tracked per user id", "Unlocks dashboard or saved cases where enabled"],
      },
      {
        name: "Pro",
        price: "Per deployment",
        blurb: "When Stripe billing is enabled, subscriptions can raise limits and show manage-billing in the app.",
        bullets: ["Requires checkout to be configured on the API", "Not legal advice or a regulated service by itself"],
      },
    ],
    openApp: "Open app",
  },
  faqItems: [
    {
      q: "Is this legal advice?",
      a: "No. NyayaSetu provides educational and drafting assistance. It does not create an advocate–client relationship. For court deadlines, strategy, and filings, consult a qualified lawyer.",
    },
    {
      q: "Which laws does it cover?",
      a: "Coverage depends on your deployment’s knowledge base and configuration. The assistant may reference major Indian statutes and procedures where data exists—always verify citations.",
    },
    {
      q: "Is my chat private?",
      a: "Treat chats as sensitive. Privacy and retention follow your deployment’s policy and infrastructure (region, logging, backups).",
    },
    {
      q: "Can advocates rely on it?",
      a: "Optional lawyer mode can request broader retrieval settings. It does not verify enrolment or bar membership; your firm should set its own governance.",
    },
    {
      q: "What about emergencies?",
      a: "The product includes crisis and emergency heuristics. If you are in immediate danger, contact local police or emergency services first.",
    },
  ],
  aboutParagraphs: [
    "NyayaSetu is an AI legal companion focused on the Indian context: clearer language, structured outputs, and honest limits about what automation can do.",
    "We combine careful routing, retrieval where configured, and formatting helpers so users spend less time fighting templates—and more time verifying facts with official sources.",
    "The stack is designed for responsible deployments: feature flags, optional sign-in gates for professional modes, and room to plug in licensed corpora as your organisation grows.",
  ],
  aboutTitle: "About NyayaSetu",
  aboutCta: "Use the product",
  featuresTitle: "Features",
  featuresIntro: "NyayaSetu is modular: enable flags and backends that match your compliance and corpus strategy.",
  featuresLaunch: "Launch the assistant",
  howTitle: "How it works",
  howIntro: "A simple loop designed to reduce wrong-authority mistakes and template friction.",
  howTry: "Try it now",
  faqTitle: "Frequently asked questions",
  faqBack: "Back to assistant",
  contactTitle: "Contact",
  contactIntro:
    "For deployment, partnerships, or product questions, reach your team through the channel you publish here. This page reads a public email when configured.",
  contactEmailLabel: "Email",
  contactNoEmail:
    "Set NEXT_PUBLIC_CONTACT_EMAIL in the frontend environment to show a mailto link. Until then, use the assistant or your internal support channel.",
  contactNote: "We do not offer legal advice or accept privileged case materials through this form.",
  blogTitle: "Blog",
  blogIntro: "Product updates, deployment notes, and legal-tech context for Indian teams.",
  blogSoon:
    "Posts are coming soon. Follow your organisation’s announcements or add MDX posts under app/blog when you are ready.",
  liveCaps: {
    title: "Live limits on this deployment",
    loading: "Loading public configuration…",
    offline: "Could not reach the API. Limits below are illustrative only.",
    dailyAuth: "Daily requests (signed in)",
    dailyPro: "Daily requests (Pro, when entitled)",
    paywall: "Paywall visible",
    billingMode: "Billing mode",
    rag: "RAG backend",
    stripeCheckout: "Stripe checkout ready",
    stripePortal: "Stripe portal ready",
  },
};

const HI: MarketingBundle = {
  ...EN,
  locale: "hi",
  nav: [
    { path: "/features", label: "विशेषताएँ" },
    { path: "/how-it-works", label: "यह कैसे काम करता है" },
    { path: "/pricing", label: "मूल्य निर्धारण" },
    { path: "/faq", label: "सामान्य प्रश्न" },
    { path: "/about", label: "हमारे बारे में" },
    { path: "/blog", label: "ब्लॉग" },
    { path: "/contact", label: "संपर्क" },
  ],
  chrome: {
    ...EN.chrome,
    signIn: "साइन इन",
    openApp: "ऐप खोलें",
    menu: "मेनू",
    product: "उत्पाद",
    account: "खाता",
    buildHost: "बिल्ड और होस्ट",
    assistant: "सहायक",
    dashboard: "डैशबोर्ड",
    signInViaApp: "ऐप के ज़रिए साइन इन",
    footerLegal:
      "ये पेज Next.js के साथ आते हैं और स्थिर होस्टिंग (जैसे S3 + CloudFront) के अनुकूल हैं। सहायक API App Runner जैसे सर्वर पर चल सकता है।",
  },
  disclaimerShort:
    "NyayaSetu वकालत संस्थान नहीं है और कानूनी सलाह नहीं देता। आउटपुट शिक्षा और मसौदा सहायता के लिए हैं।",
  copyright: "शैक्षिक उपकरण—वकालत संस्थान नहीं।",
  brandTagline: "भारत के लिए कानूनी स्पष्टता",
  hero: {
    kicker: "NyayaSetu",
    title: "भारत में रोज़मर्रा के कानूनी कदमों के लिए स्पष्टता",
    subtitle:
      "अपनी समस्या साधारण भाषा में बताएँ। संरचित मार्गदर्शन, प्राधिकरण-संबंधी मसौदा, और व्यावहारिक अगले कदम—आपातकालीन सुरक्षा गेट और स्पष्ट अस्वीकरण के साथ।",
    primaryCta: "सहायक खोलें",
    secondaryCta: "देखें यह कैसे काम करता है",
  },
  home: {
    trustH2: "टीमें NyayaSetu क्यों चुनती हैं",
    pillarsH2: "उत्पाद के मुख्य स्तंभ",
    pillarsSub:
      "पूर्ण कानूनी AI साइटों जैसा संरचना—बिना उन केस-लॉ डेटाबेस का वादा जो आपने लाइसेंस न किए हों।",
    fullFeatureLink: "सभी विशेषताएँ",
    ctaH2: "सहायक आज़माने के लिए तैयार?",
    ctaSub: "वही डिप्लॉयमेंट जो आपकी संस्था कॉन्फ़िगर करती है—RAG, सीमाएँ और बिलिंग API के अनुसार।",
    ctaButton: "NyayaSetu खोलें",
  },
  trustPoints: [
    {
      title: "चयनित स्रोतों पर आधारित",
      body: "जहाँ आपका डिप्लॉयमेंट सक्षम हो, भारतीय संदर्भ के लिए रिट्रीवल ट्यून है। आधिकारिक पोर्टल पर हमेशा सत्यापित करें।",
    },
    {
      title: "नागरिक और वकील मार्ग",
      body: "सामान्य उपयोगकर्ता मोड और वैकल्पिक पेशेवर मोड—यह वकालत लाइसेंस या अदालती दावों की सलाह का विकल्प नहीं है।",
    },
    {
      title: "गोपनीयता-सचेत डिज़ाइन",
      body: "सीमाएँ या बिलिंग के लिए साइन इन करें। प्रतिधारण और क्षेत्र के लिए अपनी गोपनीयता नीति देखें।",
    },
  ],
  featureBlocks: [
    {
      title: "चैट-प्रथम मार्गदर्शन",
      body: "स्ट्रीमिंग उत्तर, अस्पष्ट रूटिंग पर स्पष्टीकरण प्रश्न, और ऐप में समर्थित अंग्रेज़ी या हिंदी शैली।",
    },
    {
      title: "दस्तावेज़ मसौदा",
      body: "पूर्ण पत्र, पहले प्रश्नोत्तर, और उपभोक्ता शिकायत सहायक—जहाँ उपयुक्त हो मुद्रण के अनुकूल।",
    },
    {
      title: "स्थानीय प्राधिकरण संदर्भ",
      body: "डायरेक्टरी मेल खाने पर सत्यापित या सुझाए गए दफ़्तर; अन्यथा सीमाएँ स्पष्ट।",
    },
    {
      title: "अपलोड और OCR (जब सक्षम हो)",
      body: "जब API कॉन्फ़िगर हो तो PDF या छवि संलग्न करें—नोटिस और आदेशों के लिए उपयोगी।",
    },
    {
      title: "वैकल्पिक अनुसंधान संकेत",
      body: "जब बैकएंड सक्षम हो तो बाहरी संशोधन स्निपेट—आधिकारिक निर्णयों का विकल्प नहीं।",
    },
    {
      title: "ऑफ़लाइन कतार (PWA)",
      body: "कनेक्टिविटी लौटने पर विफल अनुरोध कतारबद्ध हो सकते हैं—कॉन्फ़िगरेशन देखें।",
    },
  ],
  howItWorksSteps: [
    {
      step: "1",
      title: "अपनी स्थिति बताएँ",
      body: "टाइप करें या जहाँ समर्थित हो आवाज़। मसौदे के लिए शहर और संपर्क विवरण जोड़ सकते हैं।",
    },
    {
      step: "2",
      title: "हम रूट और स्पष्ट करते हैं",
      body: "यदि मुद्दा अस्पष्ट है, तो प्राधिकरण या लंबा मसौदा बनाने से पहले पूछते हैं।",
    },
    {
      step: "3",
      title: "समीक्षा और सत्यापन",
      body: "मसौदा और अगले कदम पढ़ें। कानून, फोरम और संपर्क सरकारी साइटों या योग्य वकील से सुनिश्चित करें।",
    },
  ],
  pricingNotes: {
    intro:
      "प्रत्येक डिप्लॉयमेंट अपनी सीमाएँ और बिलिंग सेट कर सकता है। नीचे सामान्य तस्वीर; साइन इन के बाद ऐप में वास्तविक सीमाएँ देखें।",
    title: "मूल्य निर्धारण",
    tiers: [
      {
        name: "अतिथि",
        price: "मुफ़्त",
        blurb: "सीमित दैनिक अनुरोध बजट के साथ सहायक आज़माएँ।",
        bullets: ["कई डिप्लॉयमेंट पर खाता ज़रूरी नहीं", "एक बार के प्रश्नों के लिए उपयुक्त"],
      },
      {
        name: "साइन इन",
        price: "मुफ़्त",
        blurb: "प्रमाणीकरण पर अधिक दैनिक सीमाएँ (जैसे Clerk)।",
        bullets: ["उपयोग उपयोगकर्ता आईडी से ट्रैक", "सक्षम होने पर डैशबोर्ड या सहेजे केस"],
      },
      {
        name: "Pro",
        price: "डिप्लॉयमेंट अनुसार",
        blurb: "Stripe सक्षम होने पर सदस्यता सीमाएँ बढ़ा सकती है और ऐप में बिलिंग प्रबंधन।",
        bullets: ["API पर चेकआउट कॉन्फ़िगर होना चाहिए", "कानूनी सलाह या विनियमित सेवा नहीं"],
      },
    ],
    openApp: "ऐप खोलें",
  },
  faqItems: [
    {
      q: "क्या यह कानूनी सलाह है?",
      a: "नहीं। NyayaSetu शिक्षा और मसौदा सहायता देता है। यह वकील–मुवक्किल संबंध नहीं बनाता। अदालती समय सीमा, रणनीति और दाखिलों के लिए योग्य वकील से संपर्क करें।",
    },
    {
      q: "किन कानूनों को कवर करता है?",
      a: "कवरेज आपके नॉलेज बेस और कॉन्फ़िगरेशन पर निर्भर है। हमेशा उद्धरण सत्यापित करें।",
    },
    {
      q: "क्या मेरी चैट निजी है?",
      a: "चैट को संवेदनशील मानें। गोपनीयता और प्रतिधारण आपकी नीति और इन्फ्रास्ट्रक्चर पर निर्भर है।",
    },
    {
      q: "क्या वकील इस पर भरोसा कर सकते हैं?",
      a: "वैकल्पिक वकील मोड व्यापक रिट्रीवल माँग सकता है। यह नामांकन सत्यापित नहीं करता; आपकी फर्म अपनी नीति बनाए।",
    },
    {
      q: "आपातकाल?",
      a: "उत्पाद में संकट ह्यूरिस्टिक्स हैं। तत्काल खतरे में स्थानीय पुलिस या आपात सेवाओं से पहले संपर्क करें।",
    },
  ],
  aboutParagraphs: [
    "NyayaSetu भारतीय संदर्भ पर केंद्रित AI कानूनी साथी है: स्पष्ट भाषा, संरचित आउटपुट, और ईमानदार सीमाएँ।",
    "हम सावधान रूटिंग, कॉन्फ़िगर किए गए रिट्रीवल, और फ़ॉर्मैटिंग सहायकों को जोड़ते हैं ताकि उपयोगकर्ता टेम्प्लेट से कम लड़ें—और आधिकारिक स्रोतों पर अधिक समय दें।",
    "जिम्मेदार डिप्लॉयमेंट के लिए स्टैक: फ़ीचर फ़्लैग, वैकल्पिक साइन-इन गेट, और लाइसेंस कॉर्पोरा जोड़ने की गुंजाइश।",
  ],
  aboutTitle: "NyayaSetu के बारे में",
  aboutCta: "उत्पाद उपयोग करें",
  featuresTitle: "विशेषताएँ",
  featuresIntro: "NyayaSetu मॉड्यूलर है: अनुपालन और कॉर्पस रणनीति से मेल खाने वाले फ़्लैग और बैकएंड सक्षम करें।",
  featuresLaunch: "सहायक चलाएँ",
  howTitle: "यह कैसे काम करता है",
  howIntro: "गलत प्राधिकरण और टेम्प्लेट घर्षण कम करने के लिए सरल लूप।",
  howTry: "अभी आज़माएँ",
  faqTitle: "अक्सर पूछे जाने वाले प्रश्न",
  faqBack: "सहायक पर वापस",
  contactTitle: "संपर्क",
  contactIntro:
    "डिप्लॉयमेंट, साझेदारी या उत्पाद प्रश्नों के लिए वह चैनल उपयोग करें जो आप प्रकाशित करते हैं। कॉन्फ़िगर होने पर सार्वजनिक ईमेल दिखता है।",
  contactEmailLabel: "ईमेल",
  contactNoEmail:
    "mailto लिंक दिखाने के लिए फ़्रंटएंड में NEXT_PUBLIC_CONTACT_EMAIL सेट करें। तब तक सहायक या आंतरिक सहायता उपयोग करें।",
  contactNote: "हम कानूनी सलाह नहीं देते और इस फ़ॉर्म के माध्यम से विशेषाधिकार सुरक्षित सामग्री स्वीकार नहीं करते।",
  blogTitle: "ब्लॉग",
  blogIntro: "उत्पाद अपडेट, डिप्लॉयमेंट नोट्स, और भारतीय टीमों के लिए कानूनी-तकनीकी संदर्भ।",
  blogSoon:
    "पोस्ट जल्द आ रही हैं। अपनी संस्था की घोषणाएँ देखें या तैयार होने पर app/blog में MDX जोड़ें।",
  liveCaps: {
    title: "इस डिप्लॉयमेंट पर लाइव सीमाएँ",
    loading: "सार्वजनिक कॉन्फ़िगरेशन लोड हो रहा है…",
    offline: "API तक नहीं पहुँच सके। नीचे की सीमाएँ केवल उदाहरण हैं।",
    dailyAuth: "दैनिक अनुरोध (साइन इन)",
    dailyPro: "दैनिक अनुरोध (Pro, जब अधिकार हो)",
    paywall: "पेवॉल दृश्यमान",
    billingMode: "बिलिंग मोड",
    rag: "RAG बैकएंड",
    stripeCheckout: "Stripe चेकआउट तैयार",
    stripePortal: "Stripe पोर्टल तैयार",
  },
};

export function marketingBundle(locale: MarketingLocale): MarketingBundle {
  return locale === "hi" ? HI : EN;
}
