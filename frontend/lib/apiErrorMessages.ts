import { ClientApiError, ServerApiError, TranscribeRequestError, type StreamEvent } from "@/services/api";
import { t, type AppLocale, type MessageKey } from "./i18n";

/** Backend `error_code` on `/generate`, `/generate-stream` SSE, or aligned ingest rate limit. */
const SERVER_OR_SSE_ERROR_KEY: Record<string, MessageKey> = {
  generate_rate_limited: "ingestRateLimited",
  ingest_rate_limited: "ingestRateLimited",
  transcribe_rate_limited: "ingestRateLimited",
  transcribe_openai_unconfigured: "generateOpenaiUnconfigured",
  transcribe_file_too_large: "voiceTooLarge",
  transcribe_audio_empty: "voiceTooShort",
  transcribe_no_text: "transcribeNoSpeech",
  transcribe_upstream_error: "generateUpstreamError",
  generate_openai_unconfigured: "generateOpenaiUnconfigured",
  generate_openai_auth_failed: "generateOpenaiAuthFailed",
  generate_service_unavailable: "generateServiceUnavailable",
  generate_upstream_error: "generateUpstreamError",
  billing_not_stripe_mode: "billingNotStripeMode",
  stripe_checkout_not_configured: "stripeCheckoutNotConfigured",
  stripe_portal_not_configured: "stripePortalNotConfigured",
  stripe_customer_missing: "stripeCustomerMissing",
  billing_portal_user_required: "billingPortalUserRequired",
  stripe_upstream_error: "stripeUpstreamError",
  dashboard_user_required: "dashboardUserRequired",
  dashboard_case_invalid: "dashboardCaseInvalid",
  dashboard_case_not_found: "dashboardCaseNotFound",
  lawyer_mode_requires_sign_in: "clientModeLawyerNeedsSignIn",
  lawyer_mode_requires_pro: "clientModeLawyerNeedsPro",
};

function localizeServerCode(locale: AppLocale, code: string | undefined, fallback: string): string {
  if (code && Object.prototype.hasOwnProperty.call(SERVER_OR_SSE_ERROR_KEY, code)) {
    return t(locale, SERVER_OR_SSE_ERROR_KEY[code]) as string;
  }
  return fallback;
}

export function formatApiThrowable(locale: AppLocale, err: unknown): string {
  if (err instanceof ServerApiError) {
    return localizeServerCode(locale, err.errorCode, err.message);
  }
  if (err instanceof TranscribeRequestError) {
    return localizeServerCode(locale, err.errorCode, err.message);
  }
  if (err instanceof ClientApiError) {
    return t(locale, err.code as MessageKey) as string;
  }
  if (err instanceof Error) return err.message;
  return t(locale, "requestFailed") as string;
}

export function formatStreamErrorEvent(
  locale: AppLocale,
  ev: Extract<StreamEvent, { type: "error" }>
): string {
  if (ev.error_code) {
    return localizeServerCode(locale, ev.error_code, ev.message);
  }
  if (ev.clientMessageKey) {
    return t(locale, ev.clientMessageKey as MessageKey) as string;
  }
  return ev.message;
}
