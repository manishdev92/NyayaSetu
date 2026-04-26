const STORAGE_KEY = "nyaya-locale";

export type AppLocale = "en" | "hi" | "hiLatn";

export function getStoredLocale(): AppLocale {
  if (typeof window === "undefined") return "en";
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (raw === "hi") return "hi";
  if (raw === "hiLatn" || raw === "hi_latn") return "hiLatn";
  return "en";
}

export function setStoredLocale(locale: AppLocale): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, locale);
}

const M = {
  en: {
    language: "Language",
    langEnglish: "English",
    langHindi: "Hindi (हिन्दी)",
    langHindiLatin: "Hindi (Roman / Latin script)",
    responseLanguageHint: "Explanations and next steps will follow this choice when the model runs.",
    ragModeLocal: "RAG: local embedding index (in-process).",
    ragModePinecone: "RAG: Pinecone vector store (server index).",
    heroBrand: "NyayaSetu",
    brandTagline: "Legal clarity for India",
    heroTitle: "AI Legal Companion",
    heroSubtitle:
      "Use the chat to describe your issue. We stream progress like a conversational assistant and ask clarifying questions when routing is uncertain (for example lost vs stolen property), so we do not assign the wrong authority. Add your details below for the letter and local office matching. This is educational support, not a substitute for a qualified lawyer.",
    signIn: "Sign in",
    signedInAs: "Signed in as",
    proTitle: "NyayaSetu Pro (preview)",
    proStripe:
      "Pro checkout will connect here after Stripe is configured in the API. List price: ₹49/mo or ₹399/yr.",
    proStub:
      "Planned: ₹1 trial, then ₹49/mo or ₹399/yr. No payment is taken in BILLING_MODE=stub — this is informational only.",
    proHide: "Set BILLING_MODE=none in the API to hide this box.",
    proBoxAria: "Pricing and plan information",
    proUpgradeCta: "Upgrade with Stripe",
    checkoutSignInFirst: "Sign in first so we can attach your subscription to your account.",
    stripeSetupHint:
      "Checkout is not ready: set STRIPE_SECRET_KEY and STRIPE_PRICE_ID on the API (see backend/docs/STRIPE.md).",
    checkoutSuccessBanner:
      "Thanks — payment completed in Stripe. If the page still shows “upgrade”, wait a few seconds: we confirm Pro as soon as the webhook reaches the API.",
    proActiveTitle: "NyayaSetu Pro is active",
    proActiveBody:
      "You get the higher daily request budget shown in your usage line. Manage or cancel billing in your Stripe customer portal (from the email receipt or Stripe Dashboard).",
    proDailyCapHint: (n: number) =>
      `While Pro is active, your daily cap from the API is up to ${n} requests (UTC calendar day).`,
    billingNotStripeMode: "Billing is not in Stripe mode on the server.",
    stripeCheckoutNotConfigured: "Stripe Checkout is not configured on the server.",
    stripeUpstreamError: "Stripe returned an error. Try again or check API logs.",
    manageBillingCta: "Manage billing",
    authorityStatusVerified: "Verified",
    authorityStatusSuggested: "Suggested",
    authorityStatusUnknown: "Unknown",
    dashboardTitle: "Saved cases",
    dashboardIntro:
      "Save a short title and notes from your analyses. This is stored per signed-in user on the API (SQLite by default).",
    dashboardCaseTitleLabel: "Title",
    dashboardCaseTitlePh: "e.g. Rent dispute — Varanasi",
    dashboardCaseSummaryLabel: "Summary (optional)",
    dashboardCaseSummaryPh: "Key facts, next hearing date, or pasted excerpt…",
    dashboardSaveCase: "Save case",
    dashboardDeleteCase: "Remove",
    dashboardEmptyCases: "No saved cases yet. Add one below or run an analysis from the home app.",
    dashboardUserRequired: "Sign in is required.",
    dashboardCaseInvalid: "Invalid case data.",
    dashboardCaseNotFound: "That case was not found.",
    dashboardUpdated: "Updated",
    dashboardBackHome: "Back to home",
    dashboardLoading: "Loading…",
    authorityDisclaimerDefault:
      "Please verify all details on official government websites before visiting or taking action. NyayaSetu does not guarantee external data accuracy.",
    stripePortalNotConfigured: "Stripe Customer Portal is not configured on the server (missing STRIPE_SECRET_KEY).",
    stripeCustomerMissing: "No Stripe customer on file yet. Complete checkout once, or wait a few seconds after payment for sync.",
    billingPortalUserRequired: "Sign in first to open the billing portal.",
    trustScoreLine: (score: string) => `Trust score: ${score}/10`,
    verifiedAuthorityBadge: "verified authority",
    authoritySourceLine: (source: string) => `Source: ${source}`,
    requestBudget: "Request budget:",
    requestBudgetLine: (r: number, l: number, reset: string) =>
      `${r} of ${l} left for today (UTC). Resets after ${reset}. Sign in for a higher daily limit.`,
    yourDetails: "Your details (optional)",
    fullName: "Full name",
    fullNamePh: "Optional — appears in the letter if provided",
    phone: "Phone",
    email: "Email",
    address: "Address",
    city: "City / district (for local authority directory)",
    cityPh: "e.g. Varanasi, Delhi",
    copyErr: "Could not copy to clipboard.",
    localAuthorityH2: "Authority & next steps",
    localAuthorityIntro:
      "Verified contacts only appear after NyayaSetu trust checks. When we cannot verify an office, we still suggest the usual government pathway for your issue type — clearly labelled as non-verified.",
    noAuthority: "No verified authority found for your location. Please check official government website.",
    issueLabel: "Issue:",
    openGovPage: "Open government page",
    addressNotOnFile: "Address: not on file.",
    phoneL: "Phone:",
    emailL: "Email:",
    suggestedLabel: "Suggested (not verified source data)",
    noVerifiedGeneric: "No verified authority found. Please check official government website.",
    noDocument: "No document text returned.",
    exportWord: "Download as Word (.doc)",
    exportPrintPdf: "Print / Save as PDF",
    exportBlockedPopup:
      "Your browser blocked the print window. Allow pop-ups for this site, or use Word download instead.",
    exportPrintHint:
      "The draft usually starts with blank lines (date, name, mobile, address) to fill by hand after printing or to type in Word. For police-related drafts, an extra line may be included for a contact number you copy from the chowki/station board or an official police website—never guess numbers.",
    draftPrimaryLabel: "Primary draft (formatter)",
    draftRefinedLabel: "Evaluator + refiner draft",
    evaluatorSummary: "Evaluator summary",
    evaluatorRelevance: "Relevance to your issue",
    evaluatorTemplate: "Template / structure fit",
    evaluatorIssues: "Issues noted",
    evaluatorFormat: "Format problems",
    evaluatorFacts: "Facts / placeholders",
    evaluatorRefinerNote: "Refiner note",
    loRag: "Legal overview — Retrieved Legal References (RAG-based)",
    loGeneral: "Legal overview — General Legal References (Not case-specific retrieval)",
    loDefault: "Legal overview",
    loRagDesc:
      "Retrieved chunks are from NyayaSetu's curated store and ranked by embedding similarity when the API key is configured.",
    loGeneralDesc:
      "Match quality is limited (keyword fallback or low similarity). Confirm every statute on India Code or official portals.",
    loDefaultDesc: "Educational notes only — confirm on India Code and official portals.",
    retConf: (n: string) => `Retrieval confidence (max chunk score): ${n}`,
    verDir: "NyayaSetu verified directory",
    verGov: "Government website (.gov.in / .nic.in)",
    verOfficial: "Official reference",
    highConf: "high-confidence gate",
    confirmIC: "confirm on India Code",
    typicalProc: "Typical procedure (general)",
    retChunks: "Retrieved chunks",
    caseLawH2: "Case law (research)",
    caseLawEmpty:
      "No licensed case-law results for this query yet. Statute and curated references above still apply. Connect a vetted case-law source in deployment when available.",
    caseLawNote:
      "Research panel for lawyer mode only. Citations are informational; verify on official court portals or a licensed database.",
    refSummary: "References (summary)",
    immSafety: "Immediate safety & helplines",
    keyHelplines: "Key helplines & emergency numbers",
    crisisNarrow:
      "Crisis triage is active: long legal research, statute lists, and the recommended escalation path are hidden so the screen stays short. Use the numbers below, then the draft and next steps when you are safe.",
    natHelplines: "National and commonly published helplines for your issue type. Confirm on your state police or MHA portal before relying on any number.",
    offPages: "Official pages (for verification)",
    offRef: "Official reference",
    clarTitle: "Clarification needed",
    clarDefault: "Please add a bit more detail so we can route you to the right forum.",
    clarType: "You can use the buttons in the chat above, or type your own follow-up and send again.",
    formalTitle: "Formal complaint / application",
    copy: "Copy to clipboard",
    copied: "Copied",
    explainH2: "Explanation",
    escH2: "Recommended escalation path",
    escIntro:
      "This path is built from fixed templates and your city label. Office names appear only when they match NyayaSetu's local JSON directory — nothing here is invented by the language model.",
    dirMatch: "Directory match:",
    verifiedListing: "VERIFIED LISTING",
    nextH2: "Next steps",
    chatH2: "Chat",
    chatIntro:
      "Messages stream as we analyze your issue. If something is ambiguous, we ask before generating a full draft or assigning an authority.",
    clientModeLabel: "Using NyayaSetu as",
    clientModeCitizen: "General user",
    clientModeLawyer: "Lawyer / legal professional",
    clientModeHint:
      "Lawyer mode requests a wider legal-context window from the API (more retrieved chunks). This does not verify your profession — enable the UI flag only in deployments you trust.",
    clientModeLawyerNeedsSignIn: "This deployment requires sign-in to use lawyer mode.",
    clientModeLawyerNeedsPro:
      "This deployment requires NyayaSetu Pro for lawyer mode. Upgrade or use general user mode.",
    taskTypeLabel: "Response style",
    taskTypeHint:
      "Full letter: formal print-and-fill draft. Q&A first: direct answer with a short annex. Both: two short answer paragraphs, then the full letter.",
    taskTypeLetter: "Full formal letter",
    taskTypeQa: "Q&A first (short annex)",
    taskTypeBoth: "Answer + full letter",
    taskTypeConsumerFiling: "Consumer complaint filing format",
    filingToolkitH2: "Filing toolkit (consumer)",
    filingForumCaption: "Suggested forum caption",
    filingPrayer: "Prayer / relief checklist",
    filingAnnexures: "Annexure checklist",
    emptyChat: "Describe your issue below to begin.",
    streamDone: "Here is your structured guidance and draft below (you can scroll to the letter section).",
    optionalChips: "Optional: help us refine your case — you can answer the chips below, type in the box, or skip.",
    sendAnswers: "Send answers",
    skipContinue: "Skip (continue without answering)",
    answerBelow: "Answer in the box below in one message, then send.",
    structReply: "Send structured reply",
    yourMessage: "Your message",
    msgPlaceholder:
      'e.g. "My wallet is missing" — then pick Lost or Stolen if asked. You can also attach a PDF or .txt.',
    attachSizeHint: (mb: string) => `Max attachment: ${mb} MB (text-based PDF, .txt, or .md).`,
    attachOcrHint:
      "The API has image OCR enabled — photos of notices or forms may be transcribed automatically; verify anything legally critical.",
    ingestFileTooLarge: (mb: string) =>
      `This file is over the server limit of ${mb} MB. Use a smaller file, or paste the text instead.`,
    ingestNoOcr:
      "We cannot read text from this image (OCR is off on the server). Describe the issue in text, use a text-based PDF, or paste the text.",
    ingestOcrFailed: "Image OCR failed on the server. Try a clearer photo, a different format, or paste the text.",
    ingestOcrNotConfigured:
      "Image OCR is selected on the server but is not correctly configured (missing key, Textract IAM, or Tesseract binary).",
    ingestUnsupported: "This file type is not supported. Use a text-based PDF, .txt, or .md.",
    ingestReadFailed: "The file could not be read. Try a different file or a supported format.",
    ingestRateLimited: "Daily request limit reached. Sign in for a higher limit, or try again tomorrow.",
    ingestEmptyExtract: "No text could be extracted from the file. Add a description or try another file.",
    readFile: "Reading file…",
    attach: "Attach .pdf / .txt",
    send: "Send",
    working: "Working…",
    voiceRecord: "Voice input",
    voiceStop: "Stop & insert text",
    voiceRecording: "Recording… tap Stop when finished",
    voiceTranscribing: "Transcribing speech…",
    voiceHint:
      "Record a short description of your issue; text appears in the box — edit if needed, then press Send. Uses the same daily request budget as sending a message.",
    voiceNotSupported:
      "Voice recording is not supported in this browser. Try Chrome or Edge on desktop, or type your issue.",
    voiceMicDenied: "Microphone permission was denied. Allow the mic for this site in browser settings.",
    voiceTooLarge: "That audio clip is too large. Try a shorter recording (under about 2 minutes).",
    voiceTooShort: "Clip was too short to transcribe. Record a few seconds of speech, then stop.",
    transcribeNoSpeech: "No clear speech was detected. Try again closer to the microphone.",
    /** Clarification when server does not provide a custom intro line */
    clarFastQuestions: "A few quick questions first:",
    requestFailed: "Request failed.",
    /** Client-only (api.ts) — aligned with `ClientApiError` codes */
    api_empty_issue: "Please describe your legal issue.",
    api_invalid_usage: "Invalid response from server (usage).",
    api_invalid_response: "Invalid response from server.",
    api_no_response_body: "No response body from server.",
    /** `/generate` / stream when OpenAI env is missing (aligns with backend ValueError). */
    generateOpenaiUnconfigured: "The AI service is not configured (OpenAI API key missing). Add OPENAI_API_KEY to the API environment.",
    generateOpenaiAuthFailed:
      "OpenAI rejected the API key (401). Create a new secret key and set OPENAI_API_KEY in the API .env, then restart the server.",
    generateServiceUnavailable: "The AI service could not complete this request. Try again later.",
    generateUpstreamError: "Generation failed on the server. Try again or simplify your message.",
    streamErrInvalidResult: "Could not read the completed result. Try again or refresh.",
    streamErrGeneric: "Stream error. Try again.",
    streamErrInvalidData: "Invalid stream data. Try again.",
    uploadFailed: "Upload failed",
    /** Lines merged into the user text sent to the model (follows UI locale) */
    mergeAdditional: "Additional detail:",
    mergeMyChoice: "Additional detail (my choice):",
    mergeStructured: "Additional details (structured):",
    fromFileOnly: (name: string) => `[From file: ${name}]\n\n`,
    fromFileAfterText: (name: string) => `---\n[From file: ${name}]\n\n`,
    streamLoadingEllipsis: "…",
    offlineQueuedMessage:
      "The connection dropped before the assistant finished. Your last request was saved — use “Retry oldest” below when you are online.",
    pendingGenerateBanner: (n: number) =>
      `You have ${n} saved request(s) from a failed connection. Retry the oldest, or clear the list.`,
    retryPendingGenerate: "Retry oldest",
    clearPendingGenerate: "Clear saved",
    backOnlinePendingHint: "You are back online — tap Retry oldest if a request is still waiting.",
    /** After a successful file paste: optional note (format-specific) + usage is appended in LegalChat */
    ingestAfterPdf:
      "Text from PDF was inserted. Review and add any missing context, then send.",
    ingestAfterText: "File text inserted. Edit or add details, then send.",
    ingestAfterImage: "OCR text from your image was inserted. Review for mistakes, add context, then send.",
    ingestAfterUsage: (rem: number, limit: number) =>
      ` — ${rem} of ${limit} free requests left today (UTC day).`,
    /** Must match `document_ingest` empty-PDF message when you change copy server-side */
    ingestWarningNoTextPdf:
      "No extractable text (often a scanned image PDF). Add a text description or use a PDF with a text layer.",
    ingestExplainScanHint:
      "Tip: In the box above, briefly describe what the document is (for example: rent demand notice dated …, pages about termination). If you have OCR elsewhere, paste that text here. Image OCR on upload may be available if your administrator enabled it on the API.",
  },
  hi: {
    language: "भाषा",
    langEnglish: "English",
    langHindi: "Hindi (हिन्दी)",
    langHindiLatin: "हिन्दी (रोमन लिपि)",
    responseLanguageHint: "मॉडल चलने पर स्पष्टीकरण व अगले क़दम आपकी इसी पसंद अनुसार होंगे (जहाँ तक मॉडल सक्षम हो)।",
    ragModeLocal: "RAG: लोकल एम्बेडिंग इन्डेक्स (in-process)।",
    ragModePinecone: "RAG: Pinecone वेक्टर स्टोर (सर्वर इन्डेक्स)।",
    heroBrand: "NyayaSetu",
    brandTagline: "भारत के लिए कानूनी स्पष्टता",
    heroTitle: "AI कानूनी साथी",
    heroSubtitle:
      "चैट में अपनी समस्या बताएँ। हम सहायक जैसे बातचीत में प्रगति दिखाते हैं और जब रूटिंग अनिश्चित हो (जैसे खो बनाम चोरी) तो स्पष्ट करने वाले प्रश्न पूछते हैं, ताकि गलत प्राधिकारी तय न हों। पत्र व स्थानीय दफ़्तर मिलान के लिए नीचे अपने विवरण जोड़ें। यह शैक्षणिक सहयोग है, योग्य वकील के बदले नहीं।",
    signIn: "साइन इन",
    signedInAs: "इनके रूप में",
    proTitle: "NyayaSetu Pro (पूर्वावलोकन)",
    proStripe: "API में Stripe कॉन्फ़िगर होने के बाद यहाँ चेकआउट जोड़ा जाएगा। सूची: ₹49/मاہ या ₹399/वर्ष।",
    proStub: "योजना: ₹1 ट्रायल, फिर ₹49/माह या ₹399/वर्ष। BILLING_MODE=stub में कोई भुगतान नहीं — सूचनात्मक।",
    proHide: "यह पेटी छिपाने के लिए API में BILLING_MODE=none।",
    proBoxAria: "कीमत व योजना की जानकारी",
    proUpgradeCta: "Stripe से अपग्रेड",
    checkoutSignInFirst: "पहले साइन इन करें ताकि सदस्यता आपके खाते से जुड़े।",
    stripeSetupHint: "चेकआउट तैयार नहीं: API पर STRIPE_SECRET_KEY व STRIPE_PRICE_ID (docs/STRIPE.md)।",
    checkoutSuccessBanner:
      "धन्यवाद — Stripe में भुगतान पूरा। अगर अभी भी “अपग्रेड” दिखे तो कुछ सेकंड प्रतीक्षा करें — webhook API तक पहुँचते ही Pro पुष्टि हो जाती है।",
    proActiveTitle: "NyayaSetu Pro सक्रिय है",
    proActiveBody:
      "आपको उपयोग पंक्ति में दिखने वाली उच्च दैनिक सीमा मिलती है। Stripe ग्राहक पोर्टल से बिलिंग प्रबंधित करें (ईमेल रसीद या Stripe डैशबोर्ड)।",
    proDailyCapHint: (n: number) =>
      `Pro सक्रिय रहते API से दैनिक अधिकतम ${n} अनुरोध (UTC दिन)।`,
    billingNotStripeMode: "सर्वर पर बिलिंग Stripe मोड में नहीं।",
    stripeCheckoutNotConfigured: "सर्वर पर Stripe चेकआउट कॉन्फ़िगर नहीं।",
    stripeUpstreamError: "Stripe त्रुटि। दोबारा या लॉग देखें।",
    manageBillingCta: "बिलिंग प्रबंधित करें (Stripe)",
    authorityStatusVerified: "सत्यापित",
    authorityStatusSuggested: "सुझाया",
    authorityStatusUnknown: "अज्ञात",
    dashboardTitle: "सहेजे मामले",
    dashboardIntro:
      "अपने विश्लेषण से संक्षिप्त शीर्षक व नोट सहेजें। यह API पर प्रति साइन-इन उपयोगकर्ता संग्रहीत होता है (डिफ़ॉल्ट SQLite)।",
    dashboardCaseTitleLabel: "शीर्षक",
    dashboardCaseTitlePh: "उदा. किराया विवाद — वाराणसी",
    dashboardCaseSummaryLabel: "सारांश (वैकल्पिक)",
    dashboardCaseSummaryPh: "मुख्य तथ्य, अगली तारीख, या अंश…",
    dashboardSaveCase: "मामला सहेजें",
    dashboardDeleteCase: "हटाएँ",
    dashboardEmptyCases: "अभी कोई सहेजा मामला नहीं। नीचे जोड़ें या होम ऐप से विश्लेषण चलाएँ।",
    dashboardUserRequired: "साइन इन आवश्यक।",
    dashboardCaseInvalid: "अमान्य मामला डेटा।",
    dashboardCaseNotFound: "वह मामला नहीं मिला।",
    dashboardUpdated: "अपडेट",
    dashboardBackHome: "होम पर वापस",
    dashboardLoading: "लोड हो रहा है…",
    authorityDisclaimerDefault:
      "जाने या कार्रवाई से पहले सभी विवरण आधिकारिक सरकारी वेबसाइटों पर सत्यापित करें। NyayaSetu बाहरी डेटा की सटीकता की गारंटी नहीं देता।",
    stripePortalNotConfigured: "सर्वर पर Stripe Customer Portal तैयार नहीं (STRIPE_SECRET_KEY)।",
    stripeCustomerMissing: "अभी Stripe ग्राहक रिकॉर्ड नहीं — एक बार चेकआउट पूरा करें या भुगतान के बाद कुछ सेकंड प्रतीक्षा करें।",
    billingPortalUserRequired: "पोर्टल के लिए पहले साइन इन करें।",
    trustScoreLine: (score: string) => `विश्वास स्कोर: ${score}/10`,
    verifiedAuthorityBadge: "सत्यापित प्राधिकारी",
    authoritySourceLine: (source: string) => `स्रोत: ${source}`,
    requestBudget: "अनुरोध सीमा:",
    requestBudgetLine: (r: number, l: number, reset: string) =>
      `आज (UTC) ${l} में से ${r} बचे; ${reset} के बाद रीसेट। उच्च दैनिक सीमा के लिए साइन इन करें।`,
    yourDetails: "आपके विवरण (वैकल्पिक)",
    fullName: "पूरा नाम",
    fullNamePh: "वैकल्पिक — पत्र में अगर दें तो",
    phone: "फोन",
    email: "ईमेल",
    address: "पता",
    city: "शहर / ज़िला (स्थानीय दफ़्तर के लिए)",
    cityPh: "उदा. वाराणसी, दिल्ली",
    copyErr: "क्लिपबोर्ड में कॉपी न हो सका।",
    localAuthorityH2: "प्राधिकारी व अगले कदम",
    localAuthorityIntro:
      "सत्यापित संपर्क तभी दिखते हैं जब NyayaSetu जाँच करे। सत्यापन न हो तो सामान्य सरकारी मार्ग (गैर-सत्यापित) सुझाया जाता है — स्पष्ट लेबल के साथ।",
    noAuthority: "इस जगह सत्यापित दफ़्तर न मिला। कृपया सरकारी वेबसाइट देखें।",
    issueLabel: "मुद्दा:",
    openGovPage: "सरकारी पेज खोलें",
    addressNotOnFile: "पता: फ़ाइल में नहीं।",
    phoneL: "फोन:",
    emailL: "ईमेल:",
    suggestedLabel: "सुझाया (स्रोत सत्यापित नहीं)",
    noVerifiedGeneric: "सत्यापित दफ़्तर न मिला। कृपया सरकारी वेबसाइट देखें।",
    noDocument: "पत्र पाठ वापस न आया।",
    exportWord: "Word में डाउनलोड (.doc)",
    exportPrintPdf: "प्रिंट / PDF सेव करें",
    exportBlockedPopup: "ब्राउज़र ने प्रिंट विंडरो रोक दी। पॉप-अप अनुमति दें, या Word डाउनलोड करें।",
    exportPrintHint:
      "मसौदा अक्सर ऊपर खाली पंक्तियों से शुरू होता है (तिथि, नाम, मोबाइल, पता) — प्रिंट कर कलम से भरें, या .doc खोलकर टाइप करें। पुलिस-मसौदे में कभी-कभी पाँचवीं पंक्ति होती है: निकटतम चौकी/थाने का वह नंबर जो आप नोटिस बोर्ड या आधिकारिक पुलिस साइट से देखकर लिखें—अनुमान न लगाएँ।",
    draftPrimaryLabel: "प्राथमिक मसौदा (फ़ॉर्मेटर)",
    draftRefinedLabel: "मूल्यांकन + दोबारा लेखन मसौदा",
    evaluatorSummary: "मूल्यांकन सार",
    evaluatorRelevance: "आपके मुद्दे से प्रासंगिकता",
    evaluatorTemplate: "टेम्पलेट / संरचना फिट",
    evaluatorIssues: "दर्शित समस्याएँ",
    evaluatorFormat: "प्रारूप समस्याएँ",
    evaluatorFacts: "तथ्य / प्लेसहोल्डर",
    evaluatorRefinerNote: "संपादक टिप्पणी",
    loRag: "कानूनी ओवरव्यू — RAG कानूनी संदर्भ",
    loGeneral: "कानूनी ओवरव्यू — सामान्य संदर्भ (केवल-खोज, मामले-विशिष्ट नहीं)",
    loDefault: "कानूनी ओवरव्यू",
    loRagDesc:
      "API कुंजी हो तो क्यूरेटेड स्टोर से चंक (एम्बेडिंग रैंक)।",
    loGeneralDesc: "मिलान कमज़ोर (कीवर्ड/कम सिमिलैरिटी) — हर धारा India Code पर सत्यापित करें।",
    loDefaultDesc: "केवल शैक्षणिक — India Code व आधिकारिक पोर्टल देखें।",
    retConf: (n: string) => `रिट्रीवल भरोसा (उच्चतम स्कोर): ${n}`,
    verDir: "NyayaSetu सत्यापित नामावली",
    verGov: "सरकारी वेबसाइट (.gov.in / .nic.in)",
    verOfficial: "आधिकारिक संदर्भ",
    highConf: "उच्च-विश्वास गेट",
    confirmIC: "India Code पर पुष्टि करें",
    typicalProc: "सामान्य प्रक्रिया (सामान्य)",
    retChunks: "निकाले गए अंश",
    caseLawH2: "केस कानून (शोध)",
    caseLawEmpty:
      "इस प्रश्न हेतु अभी कोई लाइसेंस प्राप्त केस-कानून परिणाम नहीं। ऊपर संहिता/क्यूरेटेड संदर्भ पहले लागू। उपलब्ध होने पर तैनाती में स्रोत जोड़ा जा सकता है।",
    caseLawNote:
      "केवल वकील मोड — प्रदर्शन सूचनात्मक; आधिकारिक पोर्टल या लाइसेंस डेटाबेस पर सत्यापित करें।",
    refSummary: "संदर्भ (सार)",
    immSafety: "तत्काल सुरक्षा व हेल्पलाइन",
    keyHelplines: "मुख्य हेल्पलाइन व आपात नंबर",
    crisisNarrow:
      "क्राइसिस ट्रायज सक्रिय: लंबा कानूनी अनुसंधान व अनुशिफारिस रास्ता छुपा है; पहले नीचे नंबर, फिर जब सुरक्षित हों तो मसौदा व कदम।",
    natHelplines: "राष्ट्रीय/सामान्य हेल्पलाइन; संख्या हमेशा राज्य पुलिस / MHA पर सत्यापित करें।",
    offPages: "आधिकारिक पृष्ठ (सत्यापन के लिए)",
    offRef: "आधिकारिक संदर्भ",
    clarTitle: "स्पष्टीकरण चाहिए",
    clarDefault: "सही फोरम तक रूट करने के लिए थोड़ा और विवरण जोड़ें।",
    clarType: "ऊपर चैट के बटन, या अपनी लिखित फालो-अप भेज सकते हैं।",
    formalTitle: "औपचारिक शिकायत / आवेदन",
    copy: "क्लिपबोर्ड पर",
    copied: "कॉपी हो गया",
    explainH2: "स्पष्टीकरण",
    escH2: "सुझाया गया बढ़ाव (करम)",
    escIntro: "निश्चित टेम्पलेट + आपका शहर; दफ़्तर का नाम सिर्फ JSON नामावली मिले तभी — LLM नहीं बनाता।",
    dirMatch: "नामावली मिलान:",
    verifiedListing: "सूची सत्यापित",
    nextH2: "अगले कदम",
    chatH2: "चैट",
    chatIntro:
      "हम मुद्दा समझते वक्त संदेश स्ट्रीम करते हैं। अगर अस्पष्ट है तो पूरा मसौदा/प्राधिकारी तय करने से पहले पूछेंगे।",
    clientModeLabel: "NyayaSetu का उपयोग",
    clientModeCitizen: "सामान्य उपयोगकर्ता",
    clientModeLawyer: "वकील / कानूनी पेशेवर",
    clientModeHint:
      "वकील मोड API से अधिक कानूनी संदर्भ (अधिक खोजे गए अंश) माँगता है। यह आपके पेशे की पुष्टि नहीं करता — इसे केवल विश्वसनीय परिनियोजन में चालू रखें।",
    clientModeLawyerNeedsSignIn: "इस सर्वर पर वकील मोड के लिए साइन-इन आवश्यक है।",
    clientModeLawyerNeedsPro:
      "इस सर्वर पर वकील मोड के लिए NyayaSetu Pro आवश्यक है। अपग्रेड करें या सामान्य उपयोगकर्ता मोड चुनें।",
    taskTypeLabel: "उत्तर शैली",
    taskTypeHint:
      "पूर्ण पत्र: औपचारिक मसौदा। पहले प्रश्न–उत्तर: सीधा उत्तर + छोटा परिशिष्ट। दोनों: दो संक्षिप्त उत्तर पैरा, फिर पूर्ण पत्र।",
    taskTypeLetter: "पूर्ण औपचारिक पत्र",
    taskTypeQa: "पहले प्रश्न–उत्तर (छोटा परिशिष्ट)",
    taskTypeBoth: "उत्तर + पूर्ण पत्र",
    taskTypeConsumerFiling: "उपभोक्ता शिकायत फाइलिंग प्रारूप",
    filingToolkitH2: "फाइलिंग टूलकिट (उपभोक्ता)",
    filingForumCaption: "सुझाया गया फोरम कैप्शन",
    filingPrayer: "प्रार्थना / राहत चेकलिस्ट",
    filingAnnexures: "संलग्नक चेकलिस्ट",
    emptyChat: "शुरू करने के लिए नीचे अपनी समस्या लिखें।",
    streamDone: "संरचित मार्गदर्शन व मसौदा नीचे (पत्र खंड तक स्क्रॉल करें)।",
    optionalChips: "वैकल्पिक: नीचे चिप्स, बॉक्स में टाइप, या स्किप।",
    sendAnswers: "उत्तर भेजें",
    skipContinue: "छोड़ें (बिना जवाब जारी रखें)",
    answerBelow: "नीचे एक संदेश में जवाब दें, फिर भेजें।",
    structReply: "संरचित उत्तर भेजें",
    yourMessage: "आपका संदेश",
    msgPlaceholder: 'उदा. "मेरा बटुआ नहीं मिल रहा" — पूछे तो खो/चोनी चुनें; PDF/TXT जोड़ सकते हैं।',
    attachSizeHint: (mb: string) => `अधिकतम ${mb} MB (टेक्स्ट वाला PDF, .txt, या .md)।`,
    attachOcrHint:
      "API पर इमेज OCR चालू है — नोटिस/फ़ॉर्म की फोटो स्वचालित ट्रांसक्रिप्ट हो सकती है; कानूनी रूप से ज़रूरी बातें जाँच लें।",
    ingestFileTooLarge: (mb: string) =>
      `यह फ़ाइल ${mb} MB सीमा से अधिक है। छोटा फ़ाइल चुनें या पाठ पेस्ट करें।`,
    ingestNoOcr:
      "तस्वीर से पाठ नहीं पढ़ा जा सका (सर्वर पर OCR बंद है)। पाठ लिखें, टेक्स्ट-PDF दें, या पेस्ट करें।",
    ingestOcrFailed: "सर्वर पर इमेज OCR विफल। साफ़ फोटो, दूसरा प्रारूप, या पाठ पेस्ट करें।",
    ingestOcrNotConfigured:
      "सर्वर पर OCR चुना है पर सही कॉन्फ़िग नहीं (कुंजी, Textract IAM, या Tesseract)।",
    ingestUnsupported: "यह प्रारूप समर्थित नहीं। टेक्स्ट-आधारित PDF, .txt या .md।",
    ingestReadFailed: "फ़ाइल पढ़ी न जा सकी। दूसरी फ़ाइल प्रयास करें।",
    ingestRateLimited: "दैनिक सीमा पूरी। साइन इन से अधिक सीमा, या कल।",
    ingestEmptyExtract: "इस फ़ाइल से कोई पाठ न निकला। विवरण लिखें या दूसरी फ़ाइल।",
    readFile: "फ़ाइल पढ़ रहा हूँ…",
    attach: "PDF/TXT जोड़ें",
    send: "भेजें",
    working: "चल रहा है…",
    voiceRecord: "आवाज़ से लिखें",
    voiceStop: "रोकें और पाठ जोड़ें",
    voiceRecording: "रिकॉर्ड हो रहा है… समाप्त पर रोकें दबाएँ",
    voiceTranscribing: "भाषण लिखा जा रहा है…",
    voiceHint:
      "अपनी समस्या संक्षेप में बोलें; पाठ नीचे आएगा — ज़रूरत हो तो बदलकर भेजें दबाएँ। यह सामान्य दैनिक अनुरोध सीमा में गिना जाता है।",
    voiceNotSupported:
      "इस ब्राउज़र में आवाज़ रिकॉर्डिंग समर्थित नहीं। डेस्कटॉप पर Chrome या Edge आज़माएँ, या टाइप करें।",
    voiceMicDenied: "माइक्रोफ़ोन की अनुमति अस्वीकृत। ब्राउज़र सेटिंग में साइट हेतु माइक अनुमति दें।",
    voiceTooLarge: "ऑडियो बहुत बड़ा है। लगभग 2 मिनट से कम रिकॉर्ड करें।",
    voiceTooShort: "क्लिप बहुत छोटी। कुछ सेकंड बोलें, फिर रोकें।",
    transcribeNoSpeech: "स्पष्ट भाषण नहीं मिला। माइक के पास फिर कोशिश करें।",
    clarFastQuestions: "पहले कुछ सवाल:",
    requestFailed: "अनुरोध नहीं चल सका।",
    api_empty_issue: "कृपया अपना कानूनी मुद्दा लिखें।",
    api_invalid_usage: "सर्वर से उपयोग जानकारी अमान्य।",
    api_invalid_response: "सर्वर से प्रतिक्रिया अमान्य।",
    api_no_response_body: "सर्वर से कोई पाठ्य नहीं मिला।",
    generateOpenaiUnconfigured: "AI सेवा कॉन्फ़िगर नहीं (OpenAI कुंजी नहीं)। API में OPENAI_API_KEY।",
    generateOpenaiAuthFailed: "OpenAI ने कुंजी अस्वीकार (401)। नई कुंजी बनाएँ, .env में सेट कर सर्वर रीस्टार्ट।",
    generateServiceUnavailable: "AI सेवा यह अनुरोध पूरा न कर सकी। बाद में।",
    generateUpstreamError: "सर्वर पर जनरेशन विफल। दोबारा या छोटा संदेश।",
    streamErrInvalidResult: "पूरा परिणाम न पढ़ा जा सका। दोबारा या रिफ्रेश।",
    streamErrGeneric: "स्ट्रीम त्रुटि। दोबारा।",
    streamErrInvalidData: "स्ट्रीम डेटा अमान्य। दोबारा।",
    uploadFailed: "अपलोड नहीं हुआ",
    mergeAdditional: "अतिरिक्त विवरण:",
    mergeMyChoice: "अतिरिक्त (मेरी पसंद):",
    mergeStructured: "अतिरिक्त (संरचित):",
    fromFileOnly: (name: string) => `[फ़ाइल: ${name}]\n\n`,
    fromFileAfterText: (name: string) => `---\n[फ़ाइल: ${name}]\n\n`,
    streamLoadingEllipsis: "…",
    offlineQueuedMessage:
      "कनेक्शन पूरा होने से पहले टूट गया। आपका आख़िरी अनुरोध सहेजा गया — ऑनलाइन होने पर नीचे “सबसे पुराना दोबारा” दबाएँ।",
    pendingGenerateBanner: (n: number) =>
      `${n} अनुरोध विफल कनेक्शन से सहेजे गए। सबसे पुराना दोबारा चलाएँ या सूची साफ़ करें।`,
    retryPendingGenerate: "सबसे पुराना दोबारा",
    clearPendingGenerate: "सहेजे हटाएँ",
    backOnlinePendingHint: "फिर ऑनलाइन हैं — अगर प्रतीक्षा है तो “सबसे पुराना दोबारा” दबाएँ।",
    ingestAfterPdf: "PDF से पाठ जोड़ा गया। कम-ज्यादा जोड़ने के बाद भेजें।",
    ingestAfterText: "फ़ाइल पाठ जोड़ा गया। बदलाव/विवरण दें, फिर भेजें।",
    ingestAfterImage: "तस्वीर से OCR पाठ जोड़ा गया। गलतियाँ जाँचें, संदर्भ जोड़ें, फिर भेजें।",
    ingestAfterUsage: (rem: number, limit: number) =>
      ` — आज (UTC) ${limit} में से ${rem} अनुरोध बचे।`,
    ingestWarningNoTextPdf:
      "कोई पाठ नहीं मिला (कई बार स्कैन-जैसा PDF)। सामान्य विवरण लिखें या टेक्स्ट-लेयर वाला PDF।",
    ingestExplainScanHint:
      "संकेत: ऊपर बॉक्स में दस्तावेज़ का संक्षिप्त विवरण लिखें (उदा. किराया नोटिस की तारीख, समाप्ति संबंधी पृष्ठ)। यदि कहीं OCR से पाठ मिला हो तो यहाँ पेस्ट करें। अपलोड पर इमेज OCR तभी जब API पर चालू हो।",
  },
} as const;

const hiLatnOverrides = {
  exportWord: "Word download (.doc)",
  exportPrintPdf: "Print / PDF save",
  exportBlockedPopup: "Browser ne print window roki. Pop-up allow karein ya Word download karein.",
  exportPrintHint:
    "Masauda aksar upar khali lines se shuru hota hai (tithi, naam, mobile, pata) — print kar kalam se bharen, ya .doc khol kar type karein. Police wale draft mein kabhi paanchvi line: nikatam chowki/thane ka number jo board ya official site se dekh likhen — anumaan na lagayen.",
  draftPrimaryLabel: "Primary draft (formatter)",
  draftRefinedLabel: "Evaluator + refiner draft",
  evaluatorSummary: "Evaluator summary",
  evaluatorRelevance: "Relevance to your issue",
  evaluatorTemplate: "Template / structure fit",
  evaluatorIssues: "Issues noted",
  evaluatorFormat: "Format problems",
  evaluatorFacts: "Facts / placeholders",
  evaluatorRefinerNote: "Refiner note",
  langHindiLatin: "Hindi (Roman / Latin script)",
  brandTagline: "Legal clarity for India",
  responseLanguageHint:
    "Model answers are requested in Hindi using Roman letters (Latin script), not Devanagari. You can keep this UI in English.",
  heroSubtitle:
    "Describe your issue in the chat — we stream progress and ask clarifying questions when routing is uncertain. Explanations and next steps return in Roman Hindi when you choose that language. Educational support only, not a substitute for a qualified lawyer.",
  voiceRecord: "Voice input (Roman UI)",
  voiceStop: "Stop & text insert",
  voiceRecording: "Recording… tap Stop when done",
  voiceTranscribing: "Transcribing…",
  voiceHint:
    "Speak your issue briefly; text appears below — edit, then Send. Counts toward the same daily request limit.",
  voiceNotSupported: "Voice record not supported in this browser. Try Chrome/Edge desktop or type.",
  voiceMicDenied: "Microphone permission denied. Allow mic for this site in browser settings.",
  voiceTooLarge: "Audio too large. Try under ~2 minutes.",
  voiceTooShort: "Clip too short. Speak a few seconds, then stop.",
  transcribeNoSpeech: "No clear speech detected. Try again closer to the mic.",
  clientModeLabel: "Using NyayaSetu as",
  clientModeCitizen: "General user",
  clientModeLawyer: "Lawyer / legal professional",
  clientModeHint:
    "Lawyer mode = API pulls more legal chunks. Ye aapko advocate verify nahi karta — sirf trusted deploy par UI flag on rakhen.",
  clientModeLawyerNeedsSignIn: "Is deployment par lawyer mode ke liye sign-in zaroori hai.",
  clientModeLawyerNeedsPro:
    "Is deployment par lawyer mode ke liye NyayaSetu Pro chahiye. Upgrade karein ya general user mode use karein.",
  taskTypeLabel: "Response style",
  taskTypeHint:
    "Full letter: formal print-and-fill draft. Q&A first: direct answer + chhota annex. Both: do chhote answer paragraphs, phir full letter.",
  taskTypeLetter: "Full formal letter",
  taskTypeQa: "Q&A pehle (chhota annex)",
  taskTypeBoth: "Answer + full letter",
  taskTypeConsumerFiling: "Consumer complaint filing format",
  filingToolkitH2: "Filing toolkit (consumer)",
  filingForumCaption: "Suggested forum caption",
  filingPrayer: "Prayer / relief checklist",
  filingAnnexures: "Annexure checklist",
} as unknown as Partial<(typeof M)["en"]>;

export type MessageKey = keyof (typeof M)["en"];

type MsgValue = (typeof M)["en"][MessageKey];
function pick(locale: AppLocale, key: MessageKey): MsgValue {
  if (locale === "hiLatn") {
    const o = hiLatnOverrides[key];
    if (o !== undefined) return o as MsgValue;
    return M.en[key];
  }
  return (M[locale] as (typeof M)["en"])[key] ?? M.en[key];
}

export function t<T extends MessageKey>(locale: AppLocale, key: T): (typeof M)["en"][T] {
  return pick(locale, key) as (typeof M)["en"][T];
}

/** Localize `AuthorityInfo.status` (`verified` | `suggested` | `unknown`). */
export function authorityStatusLabel(locale: AppLocale, status: string): string {
  if (status === "verified") return t(locale, "authorityStatusVerified") as string;
  if (status === "suggested") return t(locale, "authorityStatusSuggested") as string;
  if (status === "unknown") return t(locale, "authorityStatusUnknown") as string;
  return status;
}

const EMERGENCY_REGISTRY_DISCLAIMER_EN =
  "These entries are a triage aid only. Helplines and routing change by state — verify on the official state police, health, disaster, or MHA portal before acting.";

const EMERGENCY_ROW_HI: Record<string, { label: string; notes: string }> = {
  unified_emergency: {
    label: "एकीकृत आपात नंबर (ERSS)",
    notes:
      "अखिल भारतीय आपात पहुँच; क्षेत्रानुसार पुलिस, अग्निशमन या एंबुलेंस में मार्गदर्शन हो सकता है।",
  },
  police: {
    label: "पुलिस (पुराना टोल-फ्री, जहाँ अभी प्रकाशित)",
    notes: "कई राज्य पुरानी संख्याओं को 112 में मिलाते हैं — अनिश्चित हो तो 112 प्राथमिकता।",
  },
  fire: {
    label: "अग्नि आपात",
    notes: "अक्सर 112 के साथ सूचीबद्ध; अपने राज्य के अग्नि / आपदा पोर्टल से पुष्टि करें।",
  },
  ambulance: {
    label: "एंबुलेंस / चिकित्सा (राज्य योजनाएँ भिन्न)",
    notes:
      "108 कई राज्यों में प्रचारित; चिकित्सा सहायता के लिए 112 भी — स्थानीय रूप से सत्यापित करें।",
  },
  women_safety: {
    label: "महिला सहायता (राष्ट्रीय हेल्पलाइन)",
    notes: "राष्ट्रीय महिला हेल्पलाइन के रूप में प्रकाशित — मंत्रालय / राज्य पोर्टल पर पुष्टि करें।",
  },
  child_protection: {
    label: "चाइल्डलाइन इंडिया",
    notes: "राष्ट्रीय बाल हेल्पलाइन — चाइल्डलाइन / NCPCR आधिकारिक पृष्ठों पर सत्यापित करें।",
  },
  cybercrime: {
    label: "राष्ट्रीय साइबर अपराध हेल्पलाइन",
    notes: "ऑनलाइन वित्तीय धोखाधड़ी रिपोर्टिंग — cybercrime.gov.in पोर्टल भी उपयोग करें।",
  },
  human_trafficking: {
    label: "मानव तस्करी विरोधी हेल्पलाइन (सामान्यतः सूचीबद्ध)",
    notes: "राष्ट्रीय स्तर पर उद्धृत — MHA / MWCD आधिकारिक सलाह पर पुष्टि करें।",
  },
  disaster: {
    label: "आपदा / SDMA सार्वजनिक हेल्पलाइन (सामान्यतः सूचीबद्ध)",
    notes: "अक्सर राज्य आपदा नियंत्रण कक्षों के लिए — अपनी राज्य आपदा प्राधिकरण से पुष्टि करें।",
  },
};

const EMERGENCY_ROW_LATN: Record<string, { label: string; notes: string }> = {
  unified_emergency: {
    label: "Ekikrit aapat number (ERSS)",
    notes: "Akhil Bharatiya aapat pahunch; kshetranusar police, agnishaman ya ambulance routing ho sakta hai.",
  },
  police: {
    label: "Police (purana toll-free, jahan abhi prakashit)",
    notes: "Kai rajya purani sankhyon ko 112 mein milate hain — anishchit ho to 112 prathamikta.",
  },
  fire: {
    label: "Agni aapat",
    notes: "Aksar 112 ke saath suchibaddh; apne rajya agni / aapda portal se pushti karein.",
  },
  ambulance: {
    label: "Ambulance / chikitsa (rajya yojnaen bhinn)",
    notes: "108 kai rajyon mein pracharit; 112 bhi — sthanik roop se satyapit karein.",
  },
  women_safety: {
    label: "Mahila sahayta (rashtriya helpline)",
    notes: "Rashtriya mahila helpline — mantralay / rajya portal par pushti karein.",
  },
  child_protection: {
    label: "Childline India",
    notes: "Rashtriya baal helpline — Childline / NCPCR adhikarik prishthon par satyapit karein.",
  },
  cybercrime: {
    label: "Rashtriya cyber apradh helpline",
    notes: "Online vitiya dhokhadhadhi reporting — cybercrime.gov.in portal bhi.",
  },
  human_trafficking: {
    label: "Manav taskari virodhi helpline (samanyatah suchibaddh)",
    notes: "Rashtriya star par uddhrut — MHA / MWCD adhikarik salaah par pushti karein.",
  },
  disaster: {
    label: "Aapda / SDMA jan helpline (samanyatah suchibaddh)",
    notes: "Aksar rajya aapda niyantran kaksh — apni rajya aapda pradhikaran se pushti karein.",
  },
};

/** Default English authority footer from API — swap for hi / hi-Latn UI. */
export function localizeAuthorityFooterDisclaimer(locale: AppLocale, text: string): string {
  const d = (text || "").trim();
  if (locale === "en" || !d) return text;
  const enDef = (M.en.authorityDisclaimerDefault as string).trim();
  if (d === enDef) return t(locale, "authorityDisclaimerDefault") as string;
  return text;
}

export function localizeEmergencyRegistryDisclaimer(locale: AppLocale, text: string): string {
  const d = (text || "").trim();
  if (locale === "en" || !d) return text;
  if (d === EMERGENCY_REGISTRY_DISCLAIMER_EN) {
    if (locale === "hi") {
      return (
        "ये प्रविष्टियाँ केवल ट्रायज सहायता हैं। हेल्पलाइन व मार्ग राज्यानुसार बदलते हैं — " +
        "कार्रवाई से पहले राज्य पुलिस, स्वास्थ्य, आपदा या MHA पोर्टल पर सत्यापित करें।"
      );
    }
    return (
      "Ye pravishiyan keval triaj sahayta hain. Helpline va marg rajyanusar badalte hain — " +
      "karwai se pehle rajya police, swasthya, aapda ya MHA portal par satyapit karein."
    );
  }
  return text;
}

export function localizeEmergencyContactRow(
  locale: AppLocale,
  row: { category: string; label: string; notes: string },
): { label: string; notes: string } {
  if (locale === "en") return { label: row.label, notes: row.notes };
  const map = locale === "hi" ? EMERGENCY_ROW_HI : EMERGENCY_ROW_LATN;
  const hit = map[row.category];
  if (hit) return { label: hit.label, notes: hit.notes };
  return { label: row.label, notes: row.notes };
}

export type IngestErrorLike = {
  message: string;
  errorCode: string | undefined;
  status: number;
};

/** Map API `error_code` (P1-02) to a localized line; fall back to server `message` for unknown codes. */
export function messageForIngestError(
  locale: AppLocale,
  err: IngestErrorLike,
  maxUploadBytes: number | null | undefined,
  formatMaxUploadMb: (b: number) => string
): string {
  const c = err.errorCode;
  if (c === "ingest_file_too_large" && maxUploadBytes != null) {
    return t(locale, "ingestFileTooLarge")(formatMaxUploadMb(maxUploadBytes));
  }
  if (c === "ingest_image_no_ocr") return t(locale, "ingestNoOcr");
  if (c === "ingest_ocr_failed") return t(locale, "ingestOcrFailed");
  if (c === "ingest_ocr_not_configured") return t(locale, "ingestOcrNotConfigured");
  if (c === "ingest_unsupported_type") return t(locale, "ingestUnsupported");
  if (c === "ingest_rate_limited") return t(locale, "ingestRateLimited");
  if (c === "ingest_read_failed") return t(locale, "ingestReadFailed");
  return err.message;
}

/** Same string as `document_ingest` empty-PDF warning; keep in sync. */
export const INGEST_SERVER_WARN_NO_TEXT_PDF =
  "No extractable text (often a scanned image PDF). Add a text description or use a PDF with a text layer.";

/** Localize known server warning strings; unknown English passes through. */
export function localizeIngestServerWarning(locale: AppLocale, warning: string | null | undefined): string {
  const w = (warning || "").trim();
  if (!w) return "";
  if (w === INGEST_SERVER_WARN_NO_TEXT_PDF) return t(locale, "ingestWarningNoTextPdf");
  return warning || "";
}
