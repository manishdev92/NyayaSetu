"use client";

import { SignInButton, UserButton, useAuth, useUser } from "@clerk/nextjs";
import Link from "next/link";
import { useEffect, useState } from "react";
import { LegalChat, type UserProfileFields } from "@/components/LegalChat";
import {
  createBillingPortalSession,
  createStripeCheckoutSession,
  type AuthorityInfo,
  fetchBillingEntitlements,
  fetchPublicConfig,
  type DocumentEvaluatorReport,
  type GenerateResponse,
  type PublicConfig,
  type RagGroundingLabel,
} from "@/services/api";
import { formatApiThrowable } from "@/lib/apiErrorMessages";
import {
  authorityStatusLabel,
  localizeAuthorityFooterDisclaimer,
  localizeEmergencyContactRow,
  localizeEmergencyRegistryDisclaimer,
  t,
  getStoredLocale,
  setStoredLocale,
  type AppLocale,
} from "@/lib/i18n";
import { downloadDocumentAsWord, printDocumentForPdf } from "@/lib/documentExport";
import { isCaseLawUiEnabled } from "@/lib/caseLawUi";
import { isLawyerModeUiEnabled } from "@/lib/lawyerModeUi";
import { isResponseTaskUiEnabled } from "@/lib/responseTaskUi";
import { FormattedLetter } from "@/components/FormattedLetter";
import { NyayaSetuLogo, NyayaWordmark } from "@/components/marketing/NyayaSetuLogo";

function responseLangFromLocale(loc: AppLocale): "en" | "hi" | "hi_latn" {
  if (loc === "hi") return "hi";
  if (loc === "hiLatn") return "hi_latn";
  return "en";
}

function legalOverviewTitle(
  label: RagGroundingLabel | null | undefined,
  loc: AppLocale
): string {
  if (label === "rag_retrieved") return t(loc, "loRag");
  if (label === "general_not_case_specific") return t(loc, "loGeneral");
  return t(loc, "loDefault");
}

function legalOverviewDescription(
  label: RagGroundingLabel | null | undefined,
  loc: AppLocale
): string {
  if (label === "rag_retrieved") return t(loc, "loRagDesc");
  if (label === "general_not_case_specific") return t(loc, "loGeneralDesc");
  return t(loc, "loDefaultDesc");
}

function verificationLabel(kind: AuthorityInfo["verification_kind"], loc: AppLocale): string {
  if (kind === "internal_directory") return t(loc, "verDir");
  if (kind === "government_domain") return t(loc, "verGov");
  return t(loc, "verOfficial");
}

function statusBadgeClass(status: AuthorityInfo["status"]): string {
  if (status === "verified") return "bg-emerald-100 text-emerald-900";
  if (status === "suggested") return "bg-sky-100 text-sky-950";
  return "bg-amber-100 text-amber-950";
}

function LocalAuthoritySection({
  authority,
  disclaimer,
  searchNote,
  locale,
}: {
  authority: AuthorityInfo | null;
  disclaimer: string;
  searchNote: string | null;
  locale: AppLocale;
}) {
  return (
    <section className="rounded-2xl border border-stone-200/90 bg-white p-7 shadow-md">
      <h2 className="text-xl font-semibold tracking-tight text-stone-900">{t(locale, "localAuthorityH2")}</h2>
      <p className="mt-2 text-sm leading-relaxed text-stone-600 sm:text-base">{t(locale, "localAuthorityIntro")}</p>
      <p className="mt-4 rounded-xl border border-stone-200 bg-stone-100/80 px-4 py-3 text-sm leading-relaxed text-stone-700 sm:text-base">
        {localizeAuthorityFooterDisclaimer(locale, disclaimer)}
      </p>

      {!authority ? (
        <div
          className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-base leading-relaxed text-amber-950"
          role="status"
        >
          {searchNote?.trim() || `⚠️ ${t(locale, "noAuthority")}`}
        </div>
      ) : (
            <div className="mt-4 space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`rounded-md px-2.5 py-1 text-sm font-medium ${statusBadgeClass(authority.status)}`}
            >
              {authorityStatusLabel(locale, authority.status)}
            </span>
            {authority.issue_type ? (
              <span className="text-sm text-stone-600">
                {t(locale, "issueLabel")} {authority.issue_type}
              </span>
            ) : null}
          </div>

          {authority.status === "verified" ? (
            <div className="rounded-xl border border-stone-100 bg-stone-50/90 p-4 shadow-sm">
              {authority.trust_score != null ? (
                <p className="text-sm font-medium text-stone-600">
                  {t(locale, "trustScoreLine")(authority.trust_score.toFixed(1))}
                  {authority.authority_tier === "verified_authority" ? (
                    <span className="ml-2 rounded-md bg-sky-100 px-2 py-0.5 text-sky-950">
                      {t(locale, "verifiedAuthorityBadge")}
                    </span>
                  ) : null}
                </p>
              ) : null}
              <p className="mt-2 text-sm font-medium text-stone-600">
                {verificationLabel(authority.verification_kind, locale)}
              </p>
              {authority.source ? (
                <p className="mt-1 text-sm font-medium uppercase tracking-wide text-amber-900/90">
                  {t(locale, "authoritySourceLine")(authority.source)}
                </p>
              ) : null}
              <p className="mt-2 text-lg font-semibold text-stone-900">{authority.primary || authority.office_name}</p>
              {authority.secondary ? (
                <p className="mt-1 text-base text-stone-700">{authority.secondary}</p>
              ) : null}
              {authority.guidance ? (
                <p className="mt-3 text-base leading-relaxed text-stone-700">{authority.guidance}</p>
              ) : null}
              {authority.url ? (
                <p className="mt-2 text-base">
                  <a
                    href={authority.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium text-amber-900 underline decoration-amber-800/40 underline-offset-2 hover:text-amber-950"
                  >
                    {t(locale, "openGovPage")}
                  </a>
                </p>
              ) : null}
              {authority.address ? (
                <p className="mt-2 text-base leading-relaxed text-stone-700">{authority.address}</p>
              ) : (
                <p className="mt-2 text-base text-stone-600">{t(locale, "addressNotOnFile")}</p>
              )}
              {authority.phone ? (
                <p className="mt-2 text-base text-stone-700">
                  <span className="font-medium text-stone-800">{t(locale, "phoneL")}</span> {authority.phone}
                </p>
              ) : null}
              {authority.email ? (
                <p className="mt-2 text-base text-stone-700">
                  <span className="font-medium text-stone-800">{t(locale, "emailL")}</span> {authority.email}
                </p>
              ) : null}
            </div>
          ) : null}

          {authority.status === "suggested" ? (
            <div className="rounded-xl border border-sky-200 bg-sky-50/80 p-5 shadow-sm">
              <p className="text-sm font-semibold text-sky-950 sm:text-base">
                {authority.suggestion_label || t(locale, "suggestedLabel")}
              </p>
              <p className="mt-2 text-lg font-semibold text-stone-900">{authority.primary}</p>
              <p className="mt-1 text-base text-stone-800">{authority.secondary}</p>
              <p className="mt-3 text-base leading-relaxed text-stone-700 whitespace-pre-line">
                {authority.guidance}
              </p>
              {authority.fallback_authorities && authority.fallback_authorities.length > 0 ? (
                <ul className="mt-3 list-disc space-y-1 pl-5 text-base text-stone-700">
                  {authority.fallback_authorities.map((f, i) => (
                    <li key={i}>{f}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}

          {authority.status === "unknown" ? (
            <div
              className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-base leading-relaxed text-amber-950"
              role="status"
            >
              {authority.guidance || searchNote?.trim() || t(locale, "noVerifiedGeneric")}
            </div>
          ) : null}
        </div>
      )}
    </section>
  );
}

function FormattedExplanation({ text }: { text: string }) {
  const blocks = text
    .trim()
    .split(/\n\s*\n/)
    .map((b) => b.trim())
    .filter(Boolean);

  return (
    <div className="space-y-4 text-base leading-relaxed text-stone-800 sm:text-[1.0625rem] sm:leading-[1.65]">
      {blocks.map((block, i) => (
        <p key={i} className="whitespace-pre-line">
          {block}
        </p>
      ))}
    </div>
  );
}

function EvaluatorPanel({ ev, locale }: { ev: DocumentEvaluatorReport; locale: AppLocale }) {
  const issues = ev.issues?.filter(Boolean) ?? [];
  const fmt = ev.format_violations?.filter(Boolean) ?? [];
  const facts = ev.facts_missing_or_placeholders?.filter(Boolean) ?? [];
  return (
    <div className="mb-6 rounded-xl border border-emerald-200/90 bg-emerald-50/50 p-4 text-sm text-emerald-950 shadow-inner sm:p-5 sm:text-base">
      <h3 className="text-base font-semibold text-emerald-950">{t(locale, "evaluatorSummary")}</h3>
      {ev.summary_for_user ? (
        <p className="mt-2 leading-relaxed text-emerald-950">{ev.summary_for_user}</p>
      ) : null}
      <dl className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-lg bg-white/60 px-3 py-2">
          <dt className="text-xs font-medium uppercase tracking-wide text-emerald-800/80">
            {t(locale, "evaluatorRelevance")}
          </dt>
          <dd className="mt-1 text-lg font-semibold text-emerald-950">
            {typeof ev.relevance_score === "number" ? `${ev.relevance_score}/5` : "—"}
          </dd>
        </div>
        <div className="rounded-lg bg-white/60 px-3 py-2">
          <dt className="text-xs font-medium uppercase tracking-wide text-emerald-800/80">
            {t(locale, "evaluatorTemplate")}
          </dt>
          <dd className="mt-1 text-lg font-semibold text-emerald-950">
            {typeof ev.template_fit_score === "number" ? `${ev.template_fit_score}/5` : "—"}
          </dd>
        </div>
      </dl>
      {ev.refiner_notes ? (
        <p className="mt-3 text-sm text-emerald-900/90">
          <span className="font-medium">{t(locale, "evaluatorRefinerNote")}: </span>
          {ev.refiner_notes}
        </p>
      ) : null}
      {issues.length > 0 ? (
        <div className="mt-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-900/85">
            {t(locale, "evaluatorIssues")}
          </p>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-emerald-950">
            {issues.map((x, i) => (
              <li key={i}>{x}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {fmt.length > 0 ? (
        <div className="mt-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-900/85">
            {t(locale, "evaluatorFormat")}
          </p>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-emerald-950">
            {fmt.map((x, i) => (
              <li key={i}>{x}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {facts.length > 0 ? (
        <div className="mt-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-900/85">
            {t(locale, "evaluatorFacts")}
          </p>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-emerald-950">
            {facts.map((x, i) => (
              <li key={i}>{x}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

export default function Home() {
  const { userId, isSignedIn, isLoaded } = useAuth();
  const { user } = useUser();
  const displayName =
    user?.firstName ||
    user?.username ||
    user?.primaryEmailAddress?.emailAddress ||
    null;

  const [fullName, setFullName] = useState("");
  const [address, setAddress] = useState("");
  const [city, setCity] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");

  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copyState, setCopyState] = useState<"idle" | "copied">("idle");
  const [copyRevisedState, setCopyRevisedState] = useState<"idle" | "copied">("idle");
  const [publicConfig, setPublicConfig] = useState<PublicConfig | null>(null);
  const [locale, setLocale] = useState<AppLocale>("en");
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [portalLoading, setPortalLoading] = useState(false);
  const [checkoutSuccess, setCheckoutSuccess] = useState(false);
  const [proEntitled, setProEntitled] = useState(false);

  useEffect(() => {
    void fetchPublicConfig().then(setPublicConfig);
  }, []);

  useEffect(() => {
    if (!userId || !isSignedIn || publicConfig?.billing_mode !== "stripe") {
      setProEntitled(false);
      return;
    }
    let cancelled = false;
    void fetchBillingEntitlements(userId).then((e) => {
      if (!cancelled && e) setProEntitled(e.pro);
    });
    return () => {
      cancelled = true;
    };
  }, [userId, isSignedIn, publicConfig?.billing_mode]);

  useEffect(() => {
    if (!checkoutSuccess || !userId || publicConfig?.billing_mode !== "stripe") return;
    let cancelled = false;
    let attempts = 0;
    const poll = () => {
      if (cancelled || attempts >= 10) return;
      attempts += 1;
      void fetchBillingEntitlements(userId).then((e) => {
        if (cancelled) return;
        if (e?.pro) {
          setProEntitled(true);
          return;
        }
        window.setTimeout(poll, 1600);
      });
    };
    poll();
    return () => {
      cancelled = true;
    };
  }, [checkoutSuccess, userId, publicConfig?.billing_mode]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const sp = new URLSearchParams(window.location.search);
    if (sp.get("checkout") === "success") {
      setCheckoutSuccess(true);
      window.history.replaceState({}, "", window.location.pathname + window.location.hash);
    }
  }, []);

  useEffect(() => {
    setLocale(getStoredLocale());
  }, []);

  useEffect(() => {
    setStoredLocale(locale);
  }, [locale]);

  const profile: UserProfileFields = {
    fullName,
    address,
    city,
    phone,
    email,
  };

  const lawyerModeAvailable =
    isLawyerModeUiEnabled() && Boolean(publicConfig?.client_modes_supported?.includes("lawyer"));
  const responseTaskUiEnabled = isResponseTaskUiEnabled();

  function handleChatComplete(data: GenerateResponse) {
    setResult(data);
    setCopyState("idle");
    setCopyRevisedState("idle");
    setError(null);
  }

  function handleChatError(message: string) {
    if (message.trim()) {
      setError(message);
    }
  }

  async function handleCopyDocument() {
    if (!result?.document) return;
    try {
      await navigator.clipboard.writeText(result.document);
      setCopyState("copied");
      window.setTimeout(() => setCopyState("idle"), 2000);
    } catch {
      setError(t(locale, "copyErr"));
    }
  }

  function handleExportWord() {
    const doc = result?.document?.trim();
    if (!doc) return;
    downloadDocumentAsWord(doc, "NyayaSetu-draft");
  }

  function handlePrintSavePdf() {
    const doc = result?.document?.trim();
    if (!doc) return;
    const opened = printDocumentForPdf(doc, "NyayaSetu-draft");
    if (!opened) setError(t(locale, "exportBlockedPopup"));
  }

  async function handleCopyRevised() {
    const doc = result?.document_revised?.trim();
    if (!doc) return;
    try {
      await navigator.clipboard.writeText(doc);
      setCopyRevisedState("copied");
      window.setTimeout(() => setCopyRevisedState("idle"), 2000);
    } catch {
      setError(t(locale, "copyErr"));
    }
  }

  function handleExportWordRevised() {
    const doc = result?.document_revised?.trim();
    if (!doc) return;
    downloadDocumentAsWord(doc, "NyayaSetu-refined-draft");
  }

  function handlePrintSavePdfRevised() {
    const doc = result?.document_revised?.trim();
    if (!doc) return;
    const opened = printDocumentForPdf(doc, "NyayaSetu-refined-draft");
    if (!opened) setError(t(locale, "exportBlockedPopup"));
  }

  async function handleStripeCheckout() {
    if (!userId) return;
    setCheckoutLoading(true);
    setError(null);
    try {
      const url = await createStripeCheckoutSession(userId);
      window.location.href = url;
    } catch (e: unknown) {
      setCheckoutLoading(false);
      setError(formatApiThrowable(locale, e));
    }
  }

  async function handleBillingPortal() {
    if (!userId) return;
    setPortalLoading(true);
    setError(null);
    try {
      const url = await createBillingPortalSession(userId);
      window.location.href = url;
    } catch (e: unknown) {
      setPortalLoading(false);
      setError(formatApiThrowable(locale, e));
    }
  }

  return (
    <div className="min-h-full bg-gradient-to-b from-stone-50 via-white to-stone-100/80 text-stone-900">
      <div
        className={`mx-auto px-4 py-10 sm:px-6 sm:py-16 ${
          result?.document_revised?.trim() ? "max-w-6xl" : "max-w-4xl"
        }`}
      >
        <header className="mb-12 flex flex-col gap-8 sm:flex-row sm:items-start sm:justify-between">
          <div className="text-center sm:text-left">
            <Link
              href="/"
              className="group mx-auto flex max-w-lg flex-col items-center gap-2 rounded-xl py-1 outline-none ring-amber-700/20 focus-visible:ring-2 sm:mx-0 sm:flex-row sm:items-center sm:gap-3 sm:text-left"
            >
              <NyayaSetuLogo className="h-11 w-11 shrink-0 transition group-hover:opacity-90" aria-hidden />
              <span className="flex flex-col items-center sm:items-start">
                <NyayaWordmark className="text-lg transition group-hover:text-amber-950 sm:text-xl" />
                <span className="mt-0.5 text-xs font-medium text-stone-600 sm:text-sm">
                  {t(locale, "brandTagline")}
                </span>
              </span>
            </Link>
            <h1 className="mt-5 text-4xl font-semibold tracking-tight text-stone-900 sm:mt-6 sm:text-5xl">
              {t(locale, "heroTitle")}
            </h1>
            <p className="mt-4 max-w-2xl text-lg leading-relaxed text-stone-600 sm:text-xl">
              {t(locale, "heroSubtitle")}
            </p>
            <div className="mt-5 flex flex-col gap-2">
            <div className="flex flex-wrap items-center justify-center gap-2 text-base text-stone-600 sm:justify-start">
              <span className="text-sm font-medium text-stone-500">{t(locale, "language")}:</span>
              <div className="inline-flex gap-1 rounded-xl border border-stone-200 bg-stone-100/90 p-1 shadow-sm">
                <button
                  type="button"
                  onClick={() => setLocale("en")}
                  className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                    locale === "en"
                      ? "bg-white text-stone-900 shadow-sm"
                      : "text-stone-600 hover:text-stone-900"
                  }`}
                >
                  {t(locale, "langEnglish")}
                </button>
                <button
                  type="button"
                  onClick={() => setLocale("hi")}
                  className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                    locale === "hi"
                      ? "bg-white text-stone-900 shadow-sm"
                      : "text-stone-600 hover:text-stone-900"
                  }`}
                >
                  {t(locale, "langHindi")}
                </button>
                <button
                  type="button"
                  onClick={() => setLocale("hiLatn")}
                  className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                    locale === "hiLatn"
                      ? "bg-white text-stone-900 shadow-sm"
                      : "text-stone-600 hover:text-stone-900"
                  }`}
                >
                  {t(locale, "langHindiLatin")}
                </button>
              </div>
            </div>
            {publicConfig ? (
              <p className="text-sm text-stone-600">
                {publicConfig.rag_vector_store === "pinecone"
                  ? t(locale, "ragModePinecone")
                  : t(locale, "ragModeLocal")}
              </p>
            ) : null}
            </div>
            <p className="mt-2 text-sm leading-relaxed text-stone-600">{t(locale, "responseLanguageHint")}</p>
          </div>
          <div className="flex flex-col items-center gap-2 sm:items-end">
            {isLoaded && isSignedIn ? (
              <div className="flex flex-col items-center gap-2 sm:items-end">
                {displayName ? (
                  <span className="text-sm text-stone-600">
                    {t(locale, "signedInAs")} <span className="font-medium text-stone-900">{displayName}</span>
                  </span>
                ) : null}
                <UserButton />
              </div>
            ) : null}
            {isLoaded && !isSignedIn ? (
              <SignInButton mode="modal">
                <button
                  type="button"
                  className="rounded-xl border border-stone-300 bg-white px-4 py-2.5 text-base font-medium text-stone-800 shadow-sm hover:bg-stone-50"
                >
                  {t(locale, "signIn")}
                </button>
              </SignInButton>
            ) : null}
          </div>
        </header>

        {checkoutSuccess ? (
          <p
            className="mb-6 rounded-xl border border-emerald-200 bg-emerald-50/90 px-4 py-3 text-sm text-emerald-950"
            role="status"
          >
            {t(locale, "checkoutSuccessBanner")}
          </p>
        ) : null}

        {publicConfig?.paywall_visible ? (
          proEntitled && publicConfig.billing_mode === "stripe" ? (
            <aside
              className="mb-6 rounded-2xl border border-emerald-200 bg-gradient-to-r from-emerald-50/95 to-emerald-100/40 p-4 shadow-sm"
              role="complementary"
              aria-label={t(locale, "proBoxAria")}
            >
              <p className="text-sm font-semibold text-emerald-950">{t(locale, "proActiveTitle")}</p>
              <p className="mt-1 text-xs leading-relaxed text-emerald-950/90">{t(locale, "proActiveBody")}</p>
              {publicConfig.daily_limit_pro ? (
                <p className="mt-2 text-xs text-emerald-900/80">{t(locale, "proDailyCapHint")(publicConfig.daily_limit_pro)}</p>
              ) : null}
              {publicConfig.stripe_portal_ready ? (
                <button
                  type="button"
                  disabled={portalLoading || !userId}
                  onClick={() => void handleBillingPortal()}
                  className="mt-3 w-full max-w-xs rounded-xl border border-emerald-800/40 bg-white px-4 py-2 text-sm font-semibold text-emerald-950 shadow-sm hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {portalLoading ? t(locale, "working") : t(locale, "manageBillingCta")}
                </button>
              ) : null}
            </aside>
          ) : (
            <aside
              className="mb-6 rounded-2xl border border-amber-200 bg-gradient-to-r from-amber-50/95 to-amber-100/40 p-4 shadow-sm"
              role="complementary"
              aria-label={t(locale, "proBoxAria")}
            >
              <p className="text-sm font-semibold text-amber-950">{t(locale, "proTitle")}</p>
              <p className="mt-1 text-xs leading-relaxed text-amber-950/90">
                {publicConfig.billing_mode === "stripe" ? t(locale, "proStripe") : t(locale, "proStub")}
              </p>
              {publicConfig.billing_mode === "stripe" ? (
                <div className="mt-3 flex flex-col gap-2">
                  {publicConfig.stripe_checkout_ready ? (
                    <>
                      <button
                        type="button"
                        disabled={checkoutLoading || !isSignedIn}
                        onClick={() => void handleStripeCheckout()}
                        className="w-full max-w-xs rounded-xl bg-amber-900 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-amber-950 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {checkoutLoading ? t(locale, "working") : t(locale, "proUpgradeCta")}
                      </button>
                      {!isSignedIn ? (
                        <p className="text-xs text-amber-900/85">{t(locale, "checkoutSignInFirst")}</p>
                      ) : null}
                    </>
                  ) : (
                    <p className="text-xs leading-relaxed text-amber-900/85">{t(locale, "stripeSetupHint")}</p>
                  )}
                </div>
              ) : null}
              <p className="mt-2 text-xs text-amber-900/70">{t(locale, "proHide")}</p>
            </aside>
          )
        ) : null}

        {result?.usage ? (
          <p className="rounded-xl border border-stone-200 bg-white px-4 py-3 text-sm text-stone-700 shadow-sm" role="status">
            <span className="font-medium text-stone-800">{t(locale, "requestBudget")}</span>{" "}
            {t(locale, "requestBudgetLine")(
              result.usage.remaining,
              result.usage.limit,
              result.usage.reset_at_utc?.replace("Z", " UTC") ?? "",
            )}
          </p>
        ) : null}

        <div className="space-y-8">
          <div className="space-y-4 rounded-2xl border border-stone-200/80 bg-white/80 p-5 shadow-sm sm:p-6">
            <p className="text-base font-semibold text-stone-800">{t(locale, "yourDetails")}</p>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block sm:col-span-2">
                <span className="mb-1.5 block text-sm font-medium text-stone-600">{t(locale, "fullName")}</span>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder={t(locale, "fullNamePh")}
                  className="w-full rounded-xl border border-stone-200 bg-white px-3.5 py-2.5 text-base text-stone-900 shadow-sm outline-none ring-amber-700/15 focus:border-amber-600 focus:ring-2"
                  autoComplete="name"
                />
              </label>
              <label className="block">
                <span className="mb-1.5 block text-sm font-medium text-stone-600">{t(locale, "phone")}</span>
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="w-full rounded-xl border border-stone-200 bg-white px-3.5 py-2.5 text-base text-stone-900 shadow-sm outline-none ring-amber-700/15 focus:border-amber-600 focus:ring-2"
                  autoComplete="tel"
                />
              </label>
              <label className="block">
                <span className="mb-1.5 block text-sm font-medium text-stone-600">{t(locale, "email")}</span>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-xl border border-stone-200 bg-white px-3.5 py-2.5 text-base text-stone-900 shadow-sm outline-none ring-amber-700/15 focus:border-amber-600 focus:ring-2"
                  autoComplete="email"
                />
              </label>
              <label className="block sm:col-span-2">
                <span className="mb-1.5 block text-sm font-medium text-stone-600">{t(locale, "address")}</span>
                <input
                  type="text"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  className="w-full rounded-xl border border-stone-200 bg-white px-3.5 py-2.5 text-base text-stone-900 shadow-sm outline-none ring-amber-700/15 focus:border-amber-600 focus:ring-2"
                  autoComplete="street-address"
                />
              </label>
              <label className="block sm:col-span-2">
                <span className="mb-1.5 block text-sm font-medium text-stone-600">{t(locale, "city")}</span>
                <input
                  type="text"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  placeholder={t(locale, "cityPh")}
                  className="w-full rounded-xl border border-stone-200 bg-white px-3.5 py-2.5 text-base text-stone-900 shadow-sm outline-none ring-amber-700/15 focus:border-amber-600 focus:ring-2"
                  autoComplete="address-level2"
                />
              </label>
            </div>
          </div>

          <LegalChat
            userId={userId ?? null}
            profile={profile}
            onComplete={handleChatComplete}
            onError={handleChatError}
            locale={locale}
            responseLanguage={responseLangFromLocale(locale)}
            maxUploadBytes={publicConfig?.max_upload_bytes ?? null}
            ingestOcrReady={publicConfig?.ingest_ocr_ready ?? false}
            lawyerModeAvailable={lawyerModeAvailable}
            lawyerModeRequiresSignIn={publicConfig?.lawyer_mode_requires_sign_in === true}
            lawyerProGateActive={publicConfig?.lawyer_pro_gate_active === true}
            proEntitled={proEntitled}
            responseTaskUiEnabled={responseTaskUiEnabled}
          />
        </div>

        {error && (
          <div
            className="mt-8 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-base leading-relaxed text-red-800"
            role="alert"
          >
            {error}
          </div>
        )}

        {result && (
          <div className="mt-10 space-y-10">
            {!result.clarification_needed &&
            (result.crisis_triage_mode ||
              (result.emergency_contacts && result.emergency_contacts.length > 0) ||
              result.alert) ? (
              <section
                className={
                  result.crisis_triage_mode || result.alert
                    ? "rounded-2xl border border-red-200 bg-red-50/90 p-6 shadow-sm"
                    : "rounded-2xl border border-amber-200 bg-amber-50/90 p-6 shadow-sm"
                }
                role="status"
              >
                <h2
                  className={
                    result.crisis_triage_mode || result.alert
                      ? "text-xl font-semibold text-red-950"
                      : "text-xl font-semibold text-amber-950"
                  }
                >
                  {result.crisis_triage_mode || result.alert
                    ? t(locale, "immSafety")
                    : t(locale, "keyHelplines")}
                </h2>
                {result.crisis_triage_mode ? (
                  <p
                    className={
                      result.crisis_triage_mode || result.alert
                        ? "mt-2 text-sm leading-relaxed text-red-900/95"
                        : "mt-2 text-sm leading-relaxed text-amber-900/95"
                    }
                  >
                    {t(locale, "crisisNarrow")}
                  </p>
                ) : !result.alert && (result.emergency_contacts?.length ?? 0) > 0 ? (
                  <p className="mt-2 text-sm leading-relaxed text-amber-900/95">{t(locale, "natHelplines")}</p>
                ) : null}
                {result.alert ? (
                  <p className="mt-3 text-sm font-medium leading-relaxed text-red-950 whitespace-pre-line">
                    {result.alert}
                  </p>
                ) : null}
                {result.safety_tip ? (
                  <p className="mt-2 text-sm leading-relaxed text-red-900/95 whitespace-pre-line">
                    {result.safety_tip}
                  </p>
                ) : null}
                {result.emergency_contacts && result.emergency_contacts.length > 0 ? (
                  <ul
                    className={
                      result.crisis_triage_mode || result.alert
                        ? "mt-4 space-y-3 text-sm text-red-950"
                        : "mt-4 space-y-3 text-sm text-amber-950"
                    }
                  >
                    {result.emergency_contacts.map((row, i) => {
                      const loc = localizeEmergencyContactRow(locale, row);
                      return (
                      <li
                        key={i}
                        className={
                          result.crisis_triage_mode || result.alert
                            ? "rounded-lg border border-red-200/80 bg-white/80 px-3 py-2"
                            : "rounded-lg border border-amber-200/80 bg-white/80 px-3 py-2"
                        }
                      >
                        <div className="font-medium">{loc.label}</div>
                        <p className="mt-1 font-mono text-base font-semibold tracking-tight">
                          {row.numbers.join(" · ")}
                        </p>
                        {loc.notes ? (
                          <p
                            className={
                              result.crisis_triage_mode || result.alert
                                ? "mt-1 text-xs text-red-900/85"
                                : "mt-1 text-xs text-amber-900/85"
                            }
                          >
                            {loc.notes}
                          </p>
                        ) : null}
                        {row.source_url ? (
                          <a
                            href={row.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className={
                              result.crisis_triage_mode || result.alert
                                ? "mt-1 inline-block break-all text-xs text-red-800 underline underline-offset-2"
                                : "mt-1 inline-block break-all text-xs text-amber-900 underline underline-offset-2"
                            }
                          >
                            {t(locale, "offRef")}
                          </a>
                        ) : null}
                      </li>
                      );
                    })}
                  </ul>
                ) : null}
                {result.emergency_registry_disclaimer ? (
                  <p
                    className={
                      result.crisis_triage_mode || result.alert
                        ? "mt-3 text-xs leading-relaxed text-red-900/80"
                        : "mt-3 text-xs leading-relaxed text-amber-900/80"
                    }
                  >
                    {localizeEmergencyRegistryDisclaimer(locale, result.emergency_registry_disclaimer)}
                  </p>
                ) : null}
                {result.emergency_reference_links && result.emergency_reference_links.length > 0 ? (
                  <div className="mt-3">
                    <p
                      className={
                        result.crisis_triage_mode || result.alert
                          ? "text-xs font-medium text-red-950"
                          : "text-xs font-medium text-amber-950"
                      }
                    >
                      {t(locale, "offPages")}
                    </p>
                    <ul
                      className={
                        result.crisis_triage_mode || result.alert
                          ? "mt-1 list-disc space-y-1 pl-4 text-sm text-red-900"
                          : "mt-1 list-disc space-y-1 pl-4 text-sm text-amber-900"
                      }
                    >
                      {result.emergency_reference_links.map((link, j) => (
                        <li key={j}>
                          <a
                            href={link.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="break-all underline underline-offset-2"
                          >
                            {link.title || link.url}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {result.note ? (
                  <p
                    className={
                      result.crisis_triage_mode || result.alert
                        ? "mt-3 text-sm text-red-900/90 whitespace-pre-line border-t border-red-200/60 pt-3"
                        : "mt-3 text-sm text-amber-900/90 whitespace-pre-line border-t border-amber-200/60 pt-3"
                    }
                  >
                    {result.note}
                  </p>
                ) : null}
              </section>
            ) : null}

            {result.clarification_needed ? (
              <section
                className="rounded-2xl border border-sky-200 bg-sky-50/80 p-7 shadow-md"
                role="status"
              >
                <h2 className="text-xl font-semibold text-sky-950">{t(locale, "clarTitle")}</h2>
                <p className="mt-3 text-base leading-relaxed text-sky-950">
                  {result.clarification_question || t(locale, "clarDefault")}
                </p>
                {result.clarification_options && result.clarification_options.length > 0 ? (
                  <p className="mt-3 text-sm text-sky-900/90 sm:text-base">{t(locale, "clarType")}</p>
                ) : null}
              </section>
            ) : null}

            {!result.clarification_needed ? (
            <section className="rounded-2xl border border-amber-900/15 bg-gradient-to-b from-white via-stone-50/40 to-amber-50/10 p-7 shadow-md ring-1 ring-stone-200/50">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <h2 className="text-xl font-semibold tracking-tight text-stone-900">{t(locale, "formalTitle")}</h2>
                {!result.document_revised?.trim() ? (
                  <div className="flex flex-col gap-2 sm:items-end">
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={handleCopyDocument}
                        className="inline-flex shrink-0 items-center justify-center rounded-xl border border-stone-300 bg-white px-4 py-2.5 text-base font-medium text-stone-800 shadow-sm transition hover:bg-stone-50"
                      >
                        {copyState === "copied" ? t(locale, "copied") : t(locale, "copy")}
                      </button>
                      <button
                        type="button"
                        onClick={handleExportWord}
                        disabled={!result.document?.trim()}
                        className="inline-flex shrink-0 items-center justify-center rounded-xl border border-amber-800/30 bg-amber-50 px-4 py-2.5 text-base font-medium text-amber-950 shadow-sm transition hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {t(locale, "exportWord")}
                      </button>
                      <button
                        type="button"
                        onClick={handlePrintSavePdf}
                        disabled={!result.document?.trim()}
                        className="inline-flex shrink-0 items-center justify-center rounded-xl border border-stone-400 bg-stone-800 px-4 py-2.5 text-base font-medium text-white shadow-sm transition hover:bg-stone-900 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {t(locale, "exportPrintPdf")}
                      </button>
                    </div>
                    <p className="max-w-md text-sm leading-relaxed text-stone-600 sm:text-right">
                      {t(locale, "exportPrintHint")}
                    </p>
                  </div>
                ) : null}
              </div>
              {result.document_evaluator ? (
                <EvaluatorPanel ev={result.document_evaluator} locale={locale} />
              ) : null}
              {result.document_revised?.trim() ? (
                <div className="mt-2 grid gap-8 lg:grid-cols-2 lg:gap-10">
                  <div>
                    <h3 className="text-base font-semibold text-stone-900">{t(locale, "draftPrimaryLabel")}</h3>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={handleCopyDocument}
                        className="inline-flex shrink-0 items-center justify-center rounded-xl border border-stone-300 bg-white px-4 py-2.5 text-base font-medium text-stone-800 shadow-sm transition hover:bg-stone-50"
                      >
                        {copyState === "copied" ? t(locale, "copied") : t(locale, "copy")}
                      </button>
                      <button
                        type="button"
                        onClick={handleExportWord}
                        disabled={!result.document?.trim()}
                        className="inline-flex shrink-0 items-center justify-center rounded-xl border border-amber-800/30 bg-amber-50 px-4 py-2.5 text-base font-medium text-amber-950 shadow-sm transition hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {t(locale, "exportWord")}
                      </button>
                      <button
                        type="button"
                        onClick={handlePrintSavePdf}
                        disabled={!result.document?.trim()}
                        className="inline-flex shrink-0 items-center justify-center rounded-xl border border-stone-400 bg-stone-800 px-4 py-2.5 text-base font-medium text-white shadow-sm transition hover:bg-stone-900 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {t(locale, "exportPrintPdf")}
                      </button>
                    </div>
                    <div className="mt-4 rounded-xl border border-stone-200/60 bg-white/70 px-4 py-5 sm:px-6 sm:py-6">
                      <FormattedLetter text={result.document} emptyLabel={t(locale, "noDocument")} />
                    </div>
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-amber-950">{t(locale, "draftRefinedLabel")}</h3>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={handleCopyRevised}
                        className="inline-flex shrink-0 items-center justify-center rounded-xl border border-stone-300 bg-white px-4 py-2.5 text-base font-medium text-stone-800 shadow-sm transition hover:bg-stone-50"
                      >
                        {copyRevisedState === "copied" ? t(locale, "copied") : t(locale, "copy")}
                      </button>
                      <button
                        type="button"
                        onClick={handleExportWordRevised}
                        disabled={!result.document_revised?.trim()}
                        className="inline-flex shrink-0 items-center justify-center rounded-xl border border-amber-800/30 bg-amber-50 px-4 py-2.5 text-base font-medium text-amber-950 shadow-sm transition hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {t(locale, "exportWord")}
                      </button>
                      <button
                        type="button"
                        onClick={handlePrintSavePdfRevised}
                        disabled={!result.document_revised?.trim()}
                        className="inline-flex shrink-0 items-center justify-center rounded-xl border border-stone-400 bg-stone-800 px-4 py-2.5 text-base font-medium text-white shadow-sm transition hover:bg-stone-900 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {t(locale, "exportPrintPdf")}
                      </button>
                    </div>
                    <p className="mt-2 text-sm leading-relaxed text-stone-600">{t(locale, "exportPrintHint")}</p>
                    <div className="mt-4 rounded-xl border border-amber-900/20 bg-white/90 px-4 py-5 shadow-inner sm:px-6 sm:py-6">
                      <FormattedLetter text={result.document_revised} emptyLabel={t(locale, "noDocument")} />
                    </div>
                  </div>
                </div>
              ) : (
                <div className="mt-6 rounded-xl border border-stone-200/60 bg-white/70 px-4 py-5 sm:px-6 sm:py-6">
                  <FormattedLetter text={result.document} emptyLabel={t(locale, "noDocument")} />
                </div>
              )}
            </section>
            ) : null}

            {!result.clarification_needed ? (
            <section className="rounded-2xl border border-stone-200/90 bg-white p-7 shadow-md">
              <h2 className="text-xl font-semibold tracking-tight text-stone-900">{t(locale, "explainH2")}</h2>
              <div className="mt-5">
                <FormattedExplanation text={result.explanation} />
              </div>
            </section>
            ) : null}

            {!result.clarification_needed &&
            !result.crisis_triage_mode &&
            (result.legal_explanation ||
              (result.procedure_steps && result.procedure_steps.length > 0) ||
              (result.step_by_step_procedure && result.step_by_step_procedure.length > 0) ||
              (result.retrieved_laws && result.retrieved_laws.length > 0) ||
              (result.legal_references && result.legal_references.length > 0)) ? (
              <section className="rounded-2xl border border-indigo-100 bg-indigo-50/40 p-7 shadow-md">
                <h2 className="text-xl font-semibold text-indigo-950">
                  {legalOverviewTitle(result.rag_grounding_label, locale)}
                </h2>
                <p className="mt-2 text-sm leading-relaxed text-indigo-900/85 sm:text-base">
                  {legalOverviewDescription(result.rag_grounding_label, locale)}
                </p>
                {typeof result.confidence_score === "number" && result.confidence_score > 0 ? (
                  <p className="mt-2 text-sm font-medium text-indigo-900/90">
                    {t(locale, "retConf")(result.confidence_score.toFixed(3))}
                  </p>
                ) : null}
                {result.legal_explanation ? (
                  <div className="mt-4 whitespace-pre-line text-base leading-relaxed text-indigo-950">
                    {result.legal_explanation}
                  </div>
                ) : null}
                {                (result.procedure_steps && result.procedure_steps.length > 0) ||
                (result.step_by_step_procedure && result.step_by_step_procedure.length > 0) ? (
                  <div className="mt-6">
                    <h3 className="text-base font-semibold text-indigo-950">{t(locale, "typicalProc")}</h3>
                    <ol className="mt-2 list-decimal space-y-2 pl-5 text-base leading-relaxed text-indigo-950 marker:font-medium">
                      {(result.procedure_steps ?? result.step_by_step_procedure ?? []).map((s, i) => (
                        <li key={i} className="pl-1">
                          {s}
                        </li>
                      ))}
                    </ol>
                  </div>
                ) : null}
                {result.retrieved_laws && result.retrieved_laws.length > 0 ? (
                  <div className="mt-6">
                    <h3 className="text-base font-semibold text-indigo-950">{t(locale, "retChunks")}</h3>
                    <ul className="mt-2 space-y-4 text-base text-indigo-950">
                      {result.retrieved_laws.map((r, i) => (
                        <li key={i} className="rounded-lg border border-indigo-200/60 bg-white/60 p-3 leading-relaxed">
                          <div className="flex flex-wrap items-baseline gap-2">
                            <span className="font-medium">{r.law}</span>
                            {r.section ? <span className="text-indigo-900/90">— {r.section}</span> : null}
                            <span className="text-xs text-indigo-800/80">score {r.retrieval_score.toFixed(3)}</span>
                            {r.verified ? (
                              <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-xs font-medium text-emerald-900">
                                {t(locale, "highConf")}
                              </span>
                            ) : (
                              <span className="rounded bg-amber-100 px-1.5 py-0.5 text-xs font-medium text-amber-950">
                                {t(locale, "confirmIC")}
                              </span>
                            )}
                          </div>
                          <p className="mt-2 whitespace-pre-line text-indigo-950/95">{r.chunk}</p>
                          {r.source_url ? (
                            <div className="mt-2">
                              <a
                                href={r.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="break-all text-indigo-800 underline decoration-indigo-300 underline-offset-2 hover:text-indigo-950"
                              >
                                {r.source_url}
                              </a>
                            </div>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {result.legal_references &&
                result.legal_references.length > 0 &&
                (!result.retrieved_laws || result.retrieved_laws.length === 0) ? (
                  <div className="mt-6">
                    <h3 className="text-base font-semibold text-indigo-950">{t(locale, "refSummary")}</h3>
                    <ul className="mt-2 space-y-2 text-base text-indigo-950">
                      {result.legal_references.map((r, i) => (
                        <li key={i} className="leading-relaxed">
                          <span className="font-medium">{r.law}</span>
                          {r.section ? <span className="text-indigo-900/90"> — {r.section}</span> : null}
                          {r.source_url ? (
                            <div className="mt-0.5">
                              <a
                                href={r.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="break-all text-indigo-800 underline decoration-indigo-300 underline-offset-2 hover:text-indigo-950"
                              >
                                {r.source_url}
                              </a>
                            </div>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </section>
            ) : null}

            {!result.clarification_needed &&
            isCaseLawUiEnabled() &&
            publicConfig?.case_law_research_mode &&
            publicConfig.case_law_research_mode !== "off" &&
            result.client_mode === "lawyer" ? (
              <section className="rounded-2xl border border-slate-200/90 bg-slate-50/80 p-7 shadow-md">
                <h2 className="text-xl font-semibold text-slate-900">{t(locale, "caseLawH2")}</h2>
                <p className="mt-2 text-sm leading-relaxed text-slate-600 sm:text-base">{t(locale, "caseLawNote")}</p>
                {Array.isArray(result.case_law_references) && result.case_law_references.length > 0 ? (
                  <ul className="mt-4 space-y-3 text-sm text-slate-800 sm:text-base">
                    {result.case_law_references.map((c, i) => (
                      <li key={i} className="rounded-lg border border-slate-200 bg-white/90 p-3 leading-relaxed">
                        <div className="font-medium text-slate-900">
                          {c.title?.trim() || c.citation?.trim() || "—"}
                        </div>
                        {(c.citation && c.title) || c.court || c.year != null ? (
                          <div className="mt-1 text-xs text-slate-600">
                            {c.court ? <span>{c.court}</span> : null}
                            {c.court && c.year != null ? " · " : null}
                            {c.year != null ? <span>{c.year}</span> : null}
                            {c.citation && c.title && c.citation !== c.title ? (
                              <span className="block sm:inline sm:pl-1">{c.citation}</span>
                            ) : null}
                          </div>
                        ) : null}
                        {c.snippet ? (
                          <p className="mt-2 whitespace-pre-line text-slate-800">{c.snippet}</p>
                        ) : null}
                        {c.url ? (
                          <a
                            href={c.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="mt-2 inline-block break-all text-slate-800 underline decoration-slate-300 underline-offset-2 hover:text-slate-950"
                          >
                            {c.url}
                          </a>
                        ) : null}
                        {c.source ? (
                          <p className="mt-1 text-xs text-slate-500">Source: {c.source}</p>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-3 text-sm leading-relaxed text-slate-600">{t(locale, "caseLawEmpty")}</p>
                )}
              </section>
            ) : null}

            {!result.clarification_needed &&
            (result.task_type === "consumer_complaint_filing" ||
              (Array.isArray(result.prayer_items) && result.prayer_items.length > 0) ||
              (Array.isArray(result.annexure_checklist) && result.annexure_checklist.length > 0)) ? (
              <section className="rounded-2xl border border-teal-200/90 bg-teal-50/60 p-7 shadow-md">
                <h2 className="text-xl font-semibold text-teal-950">{t(locale, "filingToolkitH2")}</h2>
                {result.forum_caption ? (
                  <div className="mt-3 rounded-lg border border-teal-200/80 bg-white/85 p-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-teal-800">
                      {t(locale, "filingForumCaption")}
                    </p>
                    <p className="mt-1 text-sm text-teal-950 sm:text-base">{result.forum_caption}</p>
                  </div>
                ) : null}
                {result.prayer_items && result.prayer_items.length > 0 ? (
                  <div className="mt-4">
                    <h3 className="text-base font-semibold text-teal-950">{t(locale, "filingPrayer")}</h3>
                    <ol className="mt-2 list-decimal space-y-2 pl-5 text-base leading-relaxed text-teal-950 marker:font-medium">
                      {result.prayer_items.map((p, i) => (
                        <li key={i} className="pl-1">
                          {p}
                        </li>
                      ))}
                    </ol>
                  </div>
                ) : null}
                {result.annexure_checklist && result.annexure_checklist.length > 0 ? (
                  <div className="mt-4">
                    <h3 className="text-base font-semibold text-teal-950">{t(locale, "filingAnnexures")}</h3>
                    <ul className="mt-2 list-disc space-y-2 pl-5 text-base leading-relaxed text-teal-950 marker:font-medium">
                      {result.annexure_checklist.map((a, i) => (
                        <li key={i} className="pl-1">
                          {a}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </section>
            ) : null}

            {!result.clarification_needed && result.generation_mode !== "EMERGENCY_WITH_DRAFT" ? (
            <LocalAuthoritySection
              authority={result.authority}
              disclaimer={result.authority_disclaimer}
              searchNote={result.authority_search_note}
              locale={locale}
            />
            ) : null}

            {!result.crisis_triage_mode &&
            result.authority_hierarchy &&
            result.authority_hierarchy.length > 0 ? (
              <section className="rounded-2xl border border-emerald-200/80 bg-emerald-50/50 p-7 shadow-md">
                <h2 className="text-xl font-semibold text-emerald-950">{t(locale, "escH2")}</h2>
                <p className="mt-3 text-sm leading-relaxed text-emerald-900/85 sm:text-base">{t(locale, "escIntro")}</p>
                <ol className="mt-4 list-decimal space-y-4 pl-5 text-base leading-relaxed text-emerald-950 marker:font-semibold">
                  {result.authority_hierarchy.map((step) => (
                    <li key={step.order} className="pl-1">
                      <div className="font-medium text-emerald-950">{step.label}</div>
                      <p className="mt-1 text-emerald-900/95">{step.description}</p>
                      {step.office_name ? (
                        <p className="mt-2 rounded-lg border border-emerald-200/70 bg-white/80 px-3 py-2 text-xs text-emerald-950">
                          <span className="font-medium">{t(locale, "dirMatch")} </span>
                          {step.office_name}
                          {step.verified ? (
                            <span className="ml-2 rounded bg-emerald-200/80 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-950">
                              {t(locale, "verifiedListing")}
                            </span>
                          ) : null}
                        </p>
                      ) : null}
                    </li>
                  ))}
                </ol>
              </section>
            ) : null}

            <section className="rounded-2xl border border-stone-200/90 bg-white p-7 shadow-md">
              <h2 className="text-xl font-semibold tracking-tight text-stone-900">{t(locale, "nextH2")}</h2>
              <ol className="mt-5 list-decimal space-y-3 pl-5 text-base leading-relaxed text-stone-800 marker:font-medium sm:text-[1.0625rem]">
                {result.next_steps.map((step, i) => (
                  <li key={i} className="pl-1">
                    {step}
                  </li>
                ))}
              </ol>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
