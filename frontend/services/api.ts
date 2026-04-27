export type AuthorityStatus = "verified" | "suggested" | "unknown";

export type AuthorityInfo = {
  status: AuthorityStatus;
  primary: string;
  secondary: string;
  guidance: string;
  office_name: string | null;
  name: string | null;
  district: string | null;
  state: string | null;
  office_type: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
  source: string | null;
  url: string | null;
  trust_score: number | null;
  verification_status: string | null;
  verification_kind: "internal_directory" | "government_domain" | null;
  authority_tier: "verified_authority" | null;
  fallback_authorities: string[] | null;
  suggestion_label: string | null;
  issue_type: string | null;
  severity: string | null;
  jurisdiction_type: string | null;
  reasoning?: string | null;
  jurisdiction_path?: string[] | null;
  routing_context?: string | null;
};

export type LegalReference = {
  law: string;
  section: string;
  source_url: string;
};

export type RetrievedLaw = {
  law: string;
  section: string;
  chunk: string;
  source_url: string;
  retrieval_score: number;
  verified: boolean;
};

export type RagGroundingLabel = "rag_retrieved" | "general_not_case_specific" | "no_match";

export type AuthoritySummary = {
  status: string;
  name: string;
  type: string;
  source_url: string;
  source?: string;
};

export type LegalClassificationLayer = {
  category: string;
  fine_intent: string;
  classifier_confidence: number;
  router_intent: string;
  entities: string[];
  intent_hint: string;
  context: string;
  issue_type: string;
  severity: string;
  jurisdiction_type: string;
};

export type JurisdictionBlock = {
  primary: string;
  secondary: string;
  path: string[];
  fallback_path: string[];
  jurisdiction_reason: string;
};

export type TrustSummary = {
  authority_routing: string;
  law_knowledge: string;
};

export type AuthorityCompact = {
  status: string;
  name: string;
  source: string;
  warning: string;
};

export type TrustReport = {
  score: number;
  reason: string;
  hallucination_risk?: string | null;
  fix_required?: boolean | null;
};

export type VerifierResult = {
  accuracy_score: number;
  hallucination_risk: string;
  authority_validity: boolean;
  fix_required: boolean;
};

/** Static escalation template; optional `office_name` only when matched in local JSON directory. */
export type AuthorityHierarchyStep = {
  order: number;
  label: string;
  description: string;
  verified: boolean;
  office_name: string | null;
  department_key: string | null;
  source: "template" | "directory";
  district_label: string | null;
};

export type ClarificationPoint = {
  label: string;
  options: string[];
};

export type ClarificationAgentQuestion = {
  id: string;
  question: string;
  type: string;
  options: string[];
  required: boolean;
};

export type DocumentEvaluatorReport = {
  relevance_score?: number;
  template_fit_score?: number;
  issues?: string[];
  format_violations?: string[];
  facts_missing_or_placeholders?: string[];
  summary_for_user?: string;
  refiner_notes?: string;
};

export type GenerateTaskType = "draft_letter" | "qa_only" | "draft_with_qa" | "consumer_complaint_filing";

/** Sprint 6: optional licensed case-law rows (lawyer tier; may be empty). */
export type CaseLawReference = {
  title: string;
  citation: string;
  court: string;
  year: number | null;
  source: string;
  url: string;
  snippet: string;
  relevance_reason?: string;
};

export type GenerateResponse = {
  document: string;
  draft: string;
  /** Second-pass refiner output when `EVALUATOR_DUAL_DRAFT` is enabled on the API. */
  document_revised?: string;
  document_evaluator?: DocumentEvaluatorReport | null;
  explanation: string;
  next_steps: string[];
  clarification_needed?: boolean;
  clarification_question?: string | null;
  clarification_options?: string[];
  clarification_points?: ClarificationPoint[];
  authority: AuthorityInfo | null;
  authority_compact?: AuthorityCompact | null;
  authority_disclaimer: string;
  authority_search_note: string | null;
  legal_explanation?: string | null;
  procedure_steps?: string[] | null;
  step_by_step_procedure?: string[] | null;
  legal_references?: LegalReference[] | null;
  retrieved_laws?: RetrievedLaw[] | null;
  confidence_score?: number | null;
  rag_grounding_label?: RagGroundingLabel | null;
  authority_summary?: AuthoritySummary | null;
  legal_classification?: LegalClassificationLayer | null;
  jurisdiction?: JurisdictionBlock | null;
  trust_summary?: TrustSummary | null;
  trust_report?: TrustReport | null;
  verifier?: VerifierResult | null;
  authority_hierarchy?: AuthorityHierarchyStep[];
  /** Conversational pre-draft questions (2–4); empty when using structured chips only */
  clarifying_questions?: string[];
  clarification_agent_questions?: ClarificationAgentQuestion[];
  clarification_optional?: boolean;
  clarification_agent_reason?: string;
  clarification_agent_confidence_hint?: number | null;
  /** Backend hides RAG + escalation tree; keep response short for safety */
  crisis_triage_mode?: boolean;
  generation_mode?: string;
  alert?: string | null;
  note?: string | null;
  safety_tip?: string | null;
  emergency_contacts?: Array<{
    category: string;
    label: string;
    numbers: string[];
    notes: string;
    provenance: string;
    source_url?: string | null;
  }>;
  emergency_reference_links?: Array<{ title: string; url: string; source: string }>;
  emergency_registry_disclaimer?: string;
  urgency_banner?: string | null;
  urgency_level?: string;
  generation_score?: number;
  /** Daily budget after this request (UTC reset). */
  usage?: {
    used: number;
    limit: number;
    remaining: number;
    reset_at_utc: string;
  };
  /** Effective tier applied (citizen default; lawyer when requested). */
  client_mode?: "citizen" | "lawyer";
  /** P2: letter vs Q&A blend (echo of request). */
  task_type?: GenerateTaskType;
  /** S6: case-law research snippets (may be empty). */
  case_law_references?: CaseLawReference[];
  forum_caption?: string | null;
  prayer_items?: string[];
  annexure_checklist?: string[];
};

export type GenerateRequestPayload = {
  user_input: string;
  city?: string;
  full_name?: string;
  address?: string;
  phone?: string;
  email?: string;
  /** Explanations and next steps language */
  response_language?: "en" | "hi" | "hi_latn";
  /** After one clarification round, set true so the backend drafts without asking again */
  skip_clarification?: boolean;
  /** Clerk user id — sent as X-User-Id for usage limits */
  userId?: string | null;
  /** Citizen (default) vs lawyer path; not authentication — see docs/CLIENT_MODE_DESIGN.md */
  client_mode?: "citizen" | "lawyer";
  /** P2: full letter (default), answer-first memo, or two short answer paragraphs + full letter */
  task_type?: GenerateTaskType;
};

/** Response from `POST /ingest-document` (text extracted for pasting into chat). */
export type IngestDocumentResponse = {
  extracted_text: string;
  filename: string;
  format: string;
  warning: string | null;
  usage: {
    used: number;
    limit: number;
    remaining: number;
    reset_at_utc: string;
  };
};

/** Thrown when `POST /ingest-document` fails; `errorCode` matches API `detail.error_code` (P1-02). */
export class IngestRequestError extends Error {
  constructor(
    message: string,
    public readonly errorCode: string | undefined,
    public readonly status: number
  ) {
    super(message);
    this.name = "IngestRequestError";
  }
}

/** Response from `POST /transcribe` (Whisper — text for the chat box). */
export type TranscribeAudioResponse = {
  text: string;
  usage: {
    used: number;
    limit: number;
    remaining: number;
    reset_at_utc: string;
  };
};

/** Thrown when `POST /transcribe` fails; `errorCode` matches API `detail.error_code`. */
export class TranscribeRequestError extends Error {
  constructor(
    message: string,
    public readonly errorCode: string | undefined,
    public readonly status: number
  ) {
    super(message);
    this.name = "TranscribeRequestError";
  }
}

/** Keys match `MessageKey` entries in `lib/i18n.ts` (P5-01 client-side errors). */
export type ClientApiErrorCode =
  | "api_empty_issue"
  | "api_invalid_usage"
  | "api_invalid_response"
  | "api_no_response_body";

export class ClientApiError extends Error {
  constructor(
    public readonly code: ClientApiErrorCode,
    message?: string
  ) {
    super(message ?? code);
    this.name = "ClientApiError";
  }
}

/** Non-2xx JSON from `/generate`, `/generate-stream`, etc. (`detail.error_code` when present). */
export class ServerApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly errorCode?: string
  ) {
    super(message);
    this.name = "ServerApiError";
  }
}

/** Thrown when `/generate-stream` fails before/during read due to network (P7-02 queue). */
export class StreamNetworkFailed extends Error {
  constructor(
    message: string,
    public readonly payload: GenerateRequestPayload,
  ) {
    super(message);
    this.name = "StreamNetworkFailed";
  }
}

export function isLikelyNetworkFailure(err: unknown): boolean {
  if (err == null) return false;
  if (typeof DOMException !== "undefined" && err instanceof DOMException && err.name === "AbortError") {
    return false;
  }
  if (typeof TypeError !== "undefined" && err instanceof TypeError) return true;
  const msg = err instanceof Error ? err.message : String(err);
  const m = msg.toLowerCase();
  return (
    m.includes("failed to fetch") ||
    m.includes("load failed") ||
    m.includes("networkerror") ||
    m.includes("ecconnreset") ||
    m.includes("econnreset")
  );
}

/** Stream parse / mapping failures before server `error` events. */
export type StreamClientMessageKey = "streamErrInvalidResult" | "streamErrGeneric" | "streamErrInvalidData";

function parseUsageBlock(raw: unknown): GenerateResponse["usage"] {
  if (raw === null || typeof raw !== "object") return undefined;
  const o = raw as Record<string, unknown>;
  const used = typeof o.used === "number" && Number.isFinite(o.used) ? o.used : 0;
  const limit = typeof o.limit === "number" && Number.isFinite(o.limit) ? o.limit : 0;
  const remaining = typeof o.remaining === "number" && Number.isFinite(o.remaining) ? o.remaining : 0;
  const reset =
    typeof o.reset_at_utc === "string" && o.reset_at_utc ? o.reset_at_utc : "1970-01-01T00:00:00Z";
  if (!limit) return undefined;
  return { used, limit, remaining, reset_at_utc: reset };
}

export async function ingestDocument(
  file: File,
  userId: string | null,
): Promise<IngestDocumentResponse> {
  const body = new FormData();
  body.append("file", file);
  const headers: Record<string, string> = {};
  if (userId) headers["X-User-Id"] = userId;
  const res = await fetch(`${getBaseUrl()}/ingest-document`, { method: "POST", body, headers });
  const data: unknown = await res.json().catch(() => ({}));
  if (!res.ok) {
    const p = parseErrorPayload(data);
    throw new IngestRequestError(
      p.message || res.statusText,
      p.errorCode,
      res.status
    );
  }
  const j = data as Record<string, unknown>;
  const u = parseUsageBlock(j.usage);
  if (!u) {
    throw new ClientApiError("api_invalid_usage");
  }
  return {
    extracted_text: typeof j.extracted_text === "string" ? j.extracted_text : "",
    filename: typeof j.filename === "string" ? j.filename : "",
    format: typeof j.format === "string" ? j.format : "text",
    warning: typeof j.warning === "string" ? j.warning : null,
    usage: u,
  };
}

export async function transcribeAudio(
  blob: Blob,
  opts: {
    userId: string | null;
    responseLanguage: "en" | "hi" | "hi_latn";
    /** Filename hint for Whisper (e.g. recording.webm) */
    filename?: string;
  },
): Promise<TranscribeAudioResponse> {
  const body = new FormData();
  body.append("file", blob, opts.filename ?? "recording.webm");
  body.append("response_language", opts.responseLanguage);
  const headers: Record<string, string> = {};
  if (opts.userId) headers["X-User-Id"] = opts.userId;
  const res = await fetch(`${getBaseUrl()}/transcribe`, { method: "POST", body, headers });
  const data: unknown = await res.json().catch(() => ({}));
  if (!res.ok) {
    const p = parseErrorPayload(data);
    throw new TranscribeRequestError(p.message || res.statusText, p.errorCode, res.status);
  }
  const j = data as Record<string, unknown>;
  const u = parseUsageBlock(j.usage);
  if (!u) {
    throw new ClientApiError("api_invalid_usage");
  }
  const text = typeof j.text === "string" ? j.text : "";
  return { text, usage: u };
}

export type StreamEvent =
  | { type: "phase"; message: string; phase?: string }
  | {
      type: "clarification";
      question: string;
      options: string[];
      points?: ClarificationPoint[];
      clarifying_questions?: string[];
      clarification_agent_questions?: ClarificationAgentQuestion[];
      clarification_optional?: boolean;
      clarification_agent_reason?: string;
      clarification_agent_confidence_hint?: number | null;
      clarification_needed: boolean;
    }
  | { type: "result"; payload: GenerateResponse }
  | { type: "done" }
  | { type: "error"; message: string; clientMessageKey?: StreamClientMessageKey; error_code?: string };

function getBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

/** Parse `client_modes_supported` from GET /config (P1-3). */
function parseClientModesSupported(raw: unknown): ("citizen" | "lawyer")[] {
  if (!Array.isArray(raw)) return ["citizen", "lawyer"];
  const out: ("citizen" | "lawyer")[] = [];
  for (const x of raw) {
    if (x === "citizen" || x === "lawyer") {
      if (!out.includes(x)) out.push(x);
    }
  }
  if (out.length === 0) return ["citizen", "lawyer"];
  if (out.includes("lawyer")) return ["citizen", "lawyer"];
  return ["citizen"];
}

/** GET `/config` — product flags (no auth). Fails soft if API unreachable. */
export type PublicConfig = {
  /** When true, API may return `document_revised` + `document_evaluator` after generate. */
  evaluator_dual_draft_enabled?: boolean;
  billing_mode: "none" | "stub" | "stripe";
  paywall_visible: boolean;
  /** True when `POST /billing/create-checkout-session` can run (Stripe mode + secret + price id). */
  stripe_checkout_ready: boolean;
  /** True when `POST /billing/create-portal-session` can run (Stripe mode + secret; per-user customer from DB). */
  stripe_portal_ready: boolean;
  stripe_webhook_ready: boolean;
  /** Backend RAG path: in-process (local) or Pinecone index. */
  rag_vector_store: "local" | "pinecone";
  /** Same cap as `POST /ingest-document` (and generate attachments); see `app.config.settings`. */
  max_upload_bytes: number;
  daily_limit_authenticated: number;
  /** Higher daily cap during the trial window after first sign-in activity (server). */
  daily_limit_trial: number;
  trial_period_days: number;
  /** Product positioning for the post-trial base tier (INR); payment may not be enforced yet. */
  base_tier_price_inr: number;
  daily_limit_pro: number;
  /** `none` | `openai` | `textract` | `tesseract` — see `backend/docs/OCR_AND_AWS.md`. */
  ingest_ocr_provider: "none" | "openai" | "textract" | "tesseract";
  /** Heuristic: provider usable (e.g. OpenAI key set, or tesseract on PATH). */
  ingest_ocr_ready: boolean;
  /** `sqlite` (default file) or `postgres` when `ENTITLEMENTS_DATABASE_URL` is set on the API. */
  entitlements_store?: "sqlite" | "postgres";
  /** `memory` (default) or `redis` when `REDIS_URL` is set on the API. */
  rate_limit_backend?: "memory" | "redis";
  /** Subset of modes the UI may advertise (GET /config, GET /ready); see `CLIENT_MODES_SUPPORTED` on API. */
  client_modes_supported: ("citizen" | "lawyer")[];
  /** S6: `off` = hide panel; `noop` = empty placeholder; `tavily_preview` = external research snippets. */
  case_law_research_mode?: "off" | "noop" | "tavily_preview";
  /** P1-1: API rejects lawyer mode without X-User-Id when this is true; UI should require sign-in to select lawyer. */
  lawyer_mode_requires_sign_in?: boolean;
  /** P1-1: Set when deployment may require Pro for lawyer (see `lawyer_pro_gate_active` for effective gate with Stripe). */
  lawyer_mode_requires_pro?: boolean;
  /** True when API enforces Pro for lawyer mode (requires Pro + Stripe billing). */
  lawyer_pro_gate_active?: boolean;
};

export type BillingEntitlements = {
  pro: boolean;
  subscription_status: string | null;
  daily_limit: number;
  in_trial?: boolean;
  trial_ends_at_utc?: string | null;
  base_tier_price_inr?: number;
};

export type ResponseFeedbackPayload = {
  helpful: boolean;
  client_mode: "citizen" | "lawyer";
  task_type: GenerateTaskType;
  locale?: "en" | "hi" | "hiLatn";
  generation_mode?: string | null;
  userId?: string | null;
};

export type ResponseFeedbackSummary = {
  days: number;
  total: number;
  positive: number;
  positive_rate: number;
  by_mode: Array<{ client_mode: "citizen" | "lawyer" | string; total: number; positive: number }>;
  by_task_type: Array<{ task_type: string; total: number; positive: number }>;
  by_day: Array<{ day: string; total: number; positive: number }>;
};

export async function fetchPublicConfig(): Promise<PublicConfig | null> {
  try {
    const res = await fetch(`${getBaseUrl()}/config`, { method: "GET", cache: "no-store" });
    if (!res.ok) return null;
    const j = (await res.json()) as Record<string, unknown>;
    const raw = j.billing_mode;
    const mode =
      raw === "stub" || raw === "stripe" || raw === "none" ? raw : "none";
    const rvs = j.rag_vector_store;
    const mub = j.max_upload_bytes;
    const max_upload_bytes =
      typeof mub === "number" && Number.isFinite(mub) && mub > 0
        ? Math.floor(mub)
        : 2_000_000;
    const dla = j.daily_limit_authenticated;
    const dlt = j.daily_limit_trial;
    const tpd = j.trial_period_days;
    const btpi = j.base_tier_price_inr;
    const dlp = j.daily_limit_pro;
    const ocrRaw = j.ingest_ocr_provider;
    const ocrProv =
      ocrRaw === "openai" || ocrRaw === "textract" || ocrRaw === "tesseract" || ocrRaw === "none"
        ? ocrRaw
        : "none";
    return {
      evaluator_dual_draft_enabled: j.evaluator_dual_draft_enabled === true,
      billing_mode: mode,
      paywall_visible: j.paywall_visible === true,
      stripe_checkout_ready: j.stripe_checkout_ready === true,
      stripe_portal_ready: j.stripe_portal_ready === true,
      stripe_webhook_ready: j.stripe_webhook_ready === true,
      rag_vector_store: rvs === "pinecone" || rvs === "local" ? rvs : "local",
      max_upload_bytes,
      daily_limit_authenticated:
        typeof dla === "number" && Number.isFinite(dla) && dla > 0 ? Math.floor(dla) : 10,
      daily_limit_trial:
        typeof dlt === "number" && Number.isFinite(dlt) && dlt > 0 ? Math.floor(dlt) : 50,
      trial_period_days:
        typeof tpd === "number" && Number.isFinite(tpd) && tpd >= 0 ? Math.floor(tpd) : 7,
      base_tier_price_inr:
        typeof btpi === "number" && Number.isFinite(btpi) && btpi >= 0 ? Math.floor(btpi) : 1,
      daily_limit_pro: typeof dlp === "number" && Number.isFinite(dlp) && dlp > 0 ? Math.floor(dlp) : 500,
      ingest_ocr_provider: ocrProv,
      ingest_ocr_ready: j.ingest_ocr_ready === true,
      entitlements_store:
        j.entitlements_store === "postgres" || j.entitlements_store === "sqlite" ? j.entitlements_store : "sqlite",
      rate_limit_backend:
        j.rate_limit_backend === "redis" || j.rate_limit_backend === "memory" ? j.rate_limit_backend : "memory",
      client_modes_supported: parseClientModesSupported(j.client_modes_supported),
      case_law_research_mode:
        j.case_law_research_mode === "noop" ||
        j.case_law_research_mode === "off" ||
        j.case_law_research_mode === "tavily_preview"
          ? j.case_law_research_mode
          : "off",
      lawyer_mode_requires_sign_in: j.lawyer_mode_requires_sign_in === true,
      lawyer_mode_requires_pro: j.lawyer_mode_requires_pro === true,
      lawyer_pro_gate_active: j.lawyer_pro_gate_active === true,
    };
  } catch {
    return null;
  }
}

/** GET `/billing/entitlements` — Pro state for Clerk user (Stripe webhooks → SQLite). */
export async function fetchBillingEntitlements(userId: string | null): Promise<BillingEntitlements | null> {
  if (!userId) return null;
  try {
    const res = await fetch(`${getBaseUrl()}/billing/entitlements`, {
      method: "GET",
      cache: "no-store",
      headers: { "X-User-Id": userId },
    });
    if (!res.ok) return null;
    const j = (await res.json()) as Record<string, unknown>;
    return {
      pro: j.pro === true,
      subscription_status: typeof j.subscription_status === "string" ? j.subscription_status : null,
      daily_limit: typeof j.daily_limit === "number" && Number.isFinite(j.daily_limit) ? Math.floor(j.daily_limit) : 10,
      in_trial: j.in_trial === true,
      trial_ends_at_utc: typeof j.trial_ends_at_utc === "string" ? j.trial_ends_at_utc : null,
      base_tier_price_inr:
        typeof j.base_tier_price_inr === "number" && Number.isFinite(j.base_tier_price_inr)
          ? Math.floor(j.base_tier_price_inr)
          : undefined,
    };
  } catch {
    return null;
  }
}

/** POST `/feedback/response` — lightweight thumbs feedback for UX analytics. */
export async function postResponseFeedback(payload: ResponseFeedbackPayload): Promise<boolean> {
  try {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (payload.userId) headers["X-User-Id"] = payload.userId;
    const res = await fetch(`${getBaseUrl()}/feedback/response`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        helpful: payload.helpful,
        client_mode: payload.client_mode,
        task_type: payload.task_type,
        locale: payload.locale,
        generation_mode: payload.generation_mode,
      }),
    });
    if (!res.ok) return false;
    return true;
  } catch {
    return false;
  }
}

/** GET `/feedback/summary` — aggregate thumbs feedback in rolling-day window. */
export async function fetchResponseFeedbackSummary(days = 30): Promise<ResponseFeedbackSummary | null> {
  try {
    const d = Number.isFinite(days) ? Math.max(1, Math.min(365, Math.floor(days))) : 30;
    const res = await fetch(`${getBaseUrl()}/feedback/summary?days=${d}`, {
      method: "GET",
      cache: "no-store",
    });
    if (!res.ok) return null;
    const j = (await res.json()) as Record<string, unknown>;
    return {
      days: typeof j.days === "number" && Number.isFinite(j.days) ? Math.floor(j.days) : d,
      total: typeof j.total === "number" && Number.isFinite(j.total) ? Math.floor(j.total) : 0,
      positive: typeof j.positive === "number" && Number.isFinite(j.positive) ? Math.floor(j.positive) : 0,
      positive_rate:
        typeof j.positive_rate === "number" && Number.isFinite(j.positive_rate) ? j.positive_rate : 0,
      by_mode: Array.isArray(j.by_mode)
        ? j.by_mode
            .filter((x) => x && typeof x === "object")
            .map((x) => {
              const o = x as Record<string, unknown>;
              return {
                client_mode: typeof o.client_mode === "string" ? o.client_mode : "citizen",
                total: typeof o.total === "number" && Number.isFinite(o.total) ? Math.floor(o.total) : 0,
                positive:
                  typeof o.positive === "number" && Number.isFinite(o.positive) ? Math.floor(o.positive) : 0,
              };
            })
        : [],
      by_task_type: Array.isArray(j.by_task_type)
        ? j.by_task_type
            .filter((x) => x && typeof x === "object")
            .map((x) => {
              const o = x as Record<string, unknown>;
              return {
                task_type: typeof o.task_type === "string" ? o.task_type : "",
                total: typeof o.total === "number" && Number.isFinite(o.total) ? Math.floor(o.total) : 0,
                positive:
                  typeof o.positive === "number" && Number.isFinite(o.positive) ? Math.floor(o.positive) : 0,
              };
            })
        : [],
      by_day: Array.isArray(j.by_day)
        ? j.by_day
            .filter((x) => x && typeof x === "object")
            .map((x) => {
              const o = x as Record<string, unknown>;
              return {
                day: typeof o.day === "string" ? o.day : "",
                total: typeof o.total === "number" && Number.isFinite(o.total) ? Math.floor(o.total) : 0,
                positive:
                  typeof o.positive === "number" && Number.isFinite(o.positive) ? Math.floor(o.positive) : 0,
              };
            })
        : [],
    };
  } catch {
    return null;
  }
}

/** FastAPI / custom body: `detail` string, validation array, or `{ message, error_code }` (P1-02). */
function parseErrorPayload(data: unknown): { message: string; errorCode?: string } {
  if (!data || typeof data !== "object" || !("detail" in data)) {
    return { message: "Request failed" };
  }
  const d = (data as { detail: unknown }).detail;
  if (typeof d === "string") {
    return { message: d };
  }
  if (d && typeof d === "object" && "message" in d) {
    const o = d as { message?: unknown; error_code?: unknown };
    if (typeof o.message === "string") {
      return {
        message: o.message,
        errorCode: typeof o.error_code === "string" ? o.error_code : undefined,
      };
    }
  }
  if (Array.isArray(d)) {
    return {
      message: d
        .map((e) => (typeof e === "object" && e && "msg" in e ? String((e as { msg: unknown }).msg) : String(e)))
        .join("; "),
    };
  }
  return { message: "Request failed" };
}

function normalizeDocumentFromServer(raw: string): string {
  const t = raw.trim();
  if (t.startsWith("{") && t.includes('"document"')) {
    try {
      const j = JSON.parse(t) as { document?: unknown };
      if (typeof j.document === "string") return j.document.trim();
    } catch {
      /* ignore */
    }
  }
  return raw;
}

function parseAuthority(raw: unknown): AuthorityInfo | null {
  if (!raw || typeof raw !== "object") return null;
  const o = raw as Record<string, unknown>;
  const st = o.status;
  if (st !== "verified" && st !== "suggested" && st !== "unknown") return null;

  const vk = o.verification_kind;
  const verification_kind =
    vk === "internal_directory" || vk === "government_domain" ? vk : null;
  const ts = o.trust_score;
  const trust_score =
    typeof ts === "number" && Number.isFinite(ts) ? ts : null;
  const tier = o.authority_tier;
  const authority_tier = tier === "verified_authority" ? tier : null;

  const fb = o.fallback_authorities;
  const fallback_authorities = Array.isArray(fb) ? fb.map(String) : null;

  return {
    status: st,
    primary: typeof o.primary === "string" ? o.primary : "",
    secondary: typeof o.secondary === "string" ? o.secondary : "",
    guidance: typeof o.guidance === "string" ? o.guidance : "",
    office_name: typeof o.office_name === "string" ? o.office_name : null,
    name: typeof o.name === "string" ? o.name : null,
    district: typeof o.district === "string" ? o.district : null,
    state: typeof o.state === "string" ? o.state : null,
    office_type: typeof o.office_type === "string" ? o.office_type : null,
    address: typeof o.address === "string" ? o.address : null,
    phone: typeof o.phone === "string" ? o.phone : null,
    email: typeof o.email === "string" ? o.email : null,
    source: typeof o.source === "string" ? o.source : null,
    url: typeof o.url === "string" ? o.url : null,
    trust_score,
    verification_status: typeof o.verification_status === "string" ? o.verification_status : null,
    verification_kind,
    authority_tier,
    fallback_authorities,
    suggestion_label: typeof o.suggestion_label === "string" ? o.suggestion_label : null,
    issue_type: typeof o.issue_type === "string" ? o.issue_type : null,
    severity: typeof o.severity === "string" ? o.severity : null,
    jurisdiction_type: typeof o.jurisdiction_type === "string" ? o.jurisdiction_type : null,
    reasoning: typeof o.reasoning === "string" ? o.reasoning : null,
    jurisdiction_path: Array.isArray(o.jurisdiction_path) ? o.jurisdiction_path.map(String) : null,
    routing_context: typeof o.routing_context === "string" ? o.routing_context : null,
  };
}

/** Normalizes JSON from `/generate` or stream `result` payloads. */
export function mapServerJsonToGenerateResponse(data: unknown): GenerateResponse {
  const parsed = data as Partial<GenerateResponse> & { authority?: unknown };
  if (
    typeof parsed.document !== "string" ||
    typeof parsed.explanation !== "string" ||
    !Array.isArray(parsed.next_steps)
  ) {
    throw new ClientApiError("api_invalid_response");
  }

  const disclaimer =
    typeof parsed.authority_disclaimer === "string" && parsed.authority_disclaimer.trim()
      ? parsed.authority_disclaimer.trim()
      : "Please verify all details on official government websites before visiting or taking action. NyayaSetu does not guarantee external data accuracy.";

  const refsRaw = parsed.legal_references;
  const legal_references = Array.isArray(refsRaw)
    ? (refsRaw as unknown[])
        .filter((x) => x !== null && typeof x === "object")
        .map((x) => {
          const o = x as Record<string, unknown>;
          return {
            law: typeof o.law === "string" ? o.law : "",
            section: typeof o.section === "string" ? o.section : "",
            source_url: typeof o.source_url === "string" ? o.source_url : "",
          };
        })
    : null;

  const sum = parsed.authority_summary;
  const authority_summary =
    sum && typeof sum === "object"
      ? {
          status: typeof (sum as { status?: unknown }).status === "string" ? (sum as { status: string }).status : "",
          name: typeof (sum as { name?: unknown }).name === "string" ? (sum as { name: string }).name : "",
          type: typeof (sum as { type?: unknown }).type === "string" ? (sum as { type: string }).type : "",
          source_url:
            typeof (sum as { source_url?: unknown }).source_url === "string"
              ? (sum as { source_url: string }).source_url
              : "",
          source: typeof (sum as { source?: unknown }).source === "string" ? (sum as { source: string }).source : "",
        }
      : null;

  const rlRaw = parsed.retrieved_laws;
  const retrieved_laws = Array.isArray(rlRaw)
    ? (rlRaw as unknown[])
        .filter((x) => x !== null && typeof x === "object")
        .map((x) => {
          const o = x as Record<string, unknown>;
          const rs = o.retrieval_score;
          return {
            law: typeof o.law === "string" ? o.law : "",
            section: typeof o.section === "string" ? o.section : "",
            chunk: typeof o.chunk === "string" ? o.chunk : "",
            source_url: typeof o.source_url === "string" ? o.source_url : "",
            retrieval_score: typeof rs === "number" && Number.isFinite(rs) ? rs : 0,
            verified: o.verified === true,
          };
        })
    : null;

  const labelRaw = parsed.rag_grounding_label;
  const rag_grounding_label: RagGroundingLabel | null =
    labelRaw === "rag_retrieved" || labelRaw === "general_not_case_specific" || labelRaw === "no_match"
      ? labelRaw
      : null;

  const cs = parsed.confidence_score;
  const confidence_score =
    typeof cs === "number" && Number.isFinite(cs) ? cs : null;

  const procRaw = parsed.procedure_steps;
  const procedure_steps = Array.isArray(procRaw) ? procRaw.map(String) : null;

  const lcRaw = parsed.legal_classification;
  const legal_classification: LegalClassificationLayer | null =
    lcRaw && typeof lcRaw === "object"
      ? (() => {
          const lc = lcRaw as Record<string, unknown>;
          const ent = lc.entities;
          const cc = lc.classifier_confidence;
          const itc = lc.issue_type_confidence;
          const legacy = lc.confidence;
          const conf =
            typeof cc === "number" && Number.isFinite(cc)
              ? cc
              : typeof itc === "number" && Number.isFinite(itc)
                ? itc
                : typeof legacy === "number" && Number.isFinite(legacy)
                  ? legacy
                  : 0;
          return {
            category: typeof lc.category === "string" ? lc.category : "",
            fine_intent: typeof lc.fine_intent === "string" ? lc.fine_intent : "",
            classifier_confidence: conf,
            router_intent:
              typeof lc.router_intent === "string"
                ? lc.router_intent
                : typeof lc.intent === "string"
                  ? lc.intent
                  : "",
            entities: Array.isArray(ent) ? ent.map(String) : [],
            intent_hint: typeof lc.intent_hint === "string" ? lc.intent_hint : "",
            context: typeof lc.context === "string" ? lc.context : "",
            issue_type: typeof lc.issue_type === "string" ? lc.issue_type : "",
            severity: typeof lc.severity === "string" ? lc.severity : "",
            jurisdiction_type: typeof lc.jurisdiction_type === "string" ? lc.jurisdiction_type : "",
          };
        })()
      : null;

  const jurRaw = parsed.jurisdiction;
  const jurisdiction: JurisdictionBlock | null =
    jurRaw && typeof jurRaw === "object"
      ? (() => {
          const j = jurRaw as Record<string, unknown>;
          const p = j.path;
          const fp = j.fallback_path;
          return {
            primary: typeof j.primary === "string" ? j.primary : "",
            secondary: typeof j.secondary === "string" ? j.secondary : "",
            path: Array.isArray(p) ? p.map(String) : [],
            fallback_path: Array.isArray(fp) ? fp.map(String) : [],
            jurisdiction_reason: typeof j.jurisdiction_reason === "string" ? j.jurisdiction_reason : "",
          };
        })()
      : null;

  const tsRaw = parsed.trust_summary;
  const trust_summary: TrustSummary | null =
    tsRaw && typeof tsRaw === "object"
      ? (() => {
          const t = tsRaw as Record<string, unknown>;
          return {
            authority_routing: typeof t.authority_routing === "string" ? t.authority_routing : "",
            law_knowledge: typeof t.law_knowledge === "string" ? t.law_knowledge : "",
          };
        })()
      : null;

  const acRaw = parsed.authority_compact;
  const authority_compact: AuthorityCompact | null =
    acRaw && typeof acRaw === "object"
      ? (() => {
          const a = acRaw as Record<string, unknown>;
          return {
            status: typeof a.status === "string" ? a.status : "",
            name: typeof a.name === "string" ? a.name : "",
            source: typeof a.source === "string" ? a.source : "",
            warning: typeof a.warning === "string" ? a.warning : "",
          };
        })()
      : null;

  const trRaw = parsed.trust_report;
  const trust_report: TrustReport | null =
    trRaw && typeof trRaw === "object"
      ? (() => {
          const t = trRaw as Record<string, unknown>;
          const sc = t.score;
          return {
            score: typeof sc === "number" && Number.isFinite(sc) ? sc : 0,
            reason: typeof t.reason === "string" ? t.reason : "",
            hallucination_risk:
              typeof t.hallucination_risk === "string" ? t.hallucination_risk : null,
            fix_required: typeof t.fix_required === "boolean" ? t.fix_required : null,
          };
        })()
      : null;

  const vfRaw = parsed.verifier;
  const verifier: VerifierResult | null =
    vfRaw && typeof vfRaw === "object"
      ? (() => {
          const v = vfRaw as Record<string, unknown>;
          const acc = v.accuracy_score;
          return {
            accuracy_score: typeof acc === "number" && Number.isFinite(acc) ? acc : 0,
            hallucination_risk: typeof v.hallucination_risk === "string" ? v.hallucination_risk : "",
            authority_validity: v.authority_validity === true,
            fix_required: v.fix_required === true,
          };
        })()
      : null;

  const ahRaw = parsed.authority_hierarchy;
  const authority_hierarchy: AuthorityHierarchyStep[] | undefined =
    Array.isArray(ahRaw) && ahRaw.length > 0
      ? (ahRaw as unknown[])
          .filter((x) => x !== null && typeof x === "object")
          .map((x) => {
            const h = x as Record<string, unknown>;
            const ord = h.order;
            const src = h.source;
            return {
              order: typeof ord === "number" && Number.isFinite(ord) ? ord : 0,
              label: typeof h.label === "string" ? h.label : "",
              description: typeof h.description === "string" ? h.description : "",
              verified: h.verified === true,
              office_name: typeof h.office_name === "string" ? h.office_name : null,
              department_key: typeof h.department_key === "string" ? h.department_key : null,
              source: (src === "directory" ? "directory" : "template") as AuthorityHierarchyStep["source"],
              district_label: typeof h.district_label === "string" ? h.district_label : null,
            };
          })
          .sort((a, b) => a.order - b.order)
      : undefined;

  const draftRaw = parsed.draft;
  const draft =
    typeof draftRaw === "string" && draftRaw.trim()
      ? normalizeDocumentFromServer(draftRaw)
      : normalizeDocumentFromServer(parsed.document);

  const clarOpts = parsed.clarification_options;
  const clarification_options = Array.isArray(clarOpts) ? clarOpts.map(String) : [];

  const cpRaw = parsed.clarification_points;
  const clarification_points: ClarificationPoint[] | undefined =
    Array.isArray(cpRaw) && cpRaw.length > 0
      ? (cpRaw as unknown[])
          .filter((x) => x !== null && typeof x === "object")
          .map((x) => {
            const p = x as Record<string, unknown>;
            const or = p.options;
            return {
              label: typeof p.label === "string" ? p.label : "",
              options: Array.isArray(or) ? or.map(String) : [],
            };
          })
          .filter((p) => p.label && p.options.length > 0)
      : undefined;

  const cqqResp = parsed.clarifying_questions;
  const clarifying_questions =
    Array.isArray(cqqResp) && cqqResp.length > 0 ? cqqResp.map(String).filter((s) => s.trim()) : undefined;

  const caqRaw = parsed.clarification_agent_questions;
  const clarification_agent_questions: ClarificationAgentQuestion[] | undefined =
    Array.isArray(caqRaw) && caqRaw.length > 0
      ? (caqRaw as unknown[])
          .filter((x) => x !== null && typeof x === "object")
          .map((x) => {
            const a = x as Record<string, unknown>;
            const o = a.options;
            return {
              id: typeof a.id === "string" ? a.id : "",
              question: typeof a.question === "string" ? a.question : "",
              type: typeof a.type === "string" ? a.type : "single_choice",
              options: Array.isArray(o) ? o.map(String) : [],
              required: a.required === true,
            };
          })
          .filter((a) => a.question && a.options.length > 0)
      : undefined;

  const copt = parsed.clarification_optional;
  const clarification_optional = copt === true;
  const careason =
    typeof parsed.clarification_agent_reason === "string" ? parsed.clarification_agent_reason : undefined;
  const cahint = parsed.clarification_agent_confidence_hint;
  const clarification_agent_confidence_hint =
    typeof cahint === "number" && Number.isFinite(cahint) ? cahint : null;

  const emRaw = parsed.emergency_contacts;
  const emergency_contacts =
    Array.isArray(emRaw) && emRaw.length > 0
      ? (emRaw as unknown[])
          .filter((x) => x !== null && typeof x === "object")
          .map((x) => {
            const o = x as Record<string, unknown>;
            const nums = o.numbers;
            return {
              category: typeof o.category === "string" ? o.category : "",
              label: typeof o.label === "string" ? o.label : "",
              numbers: Array.isArray(nums) ? nums.map(String) : [],
              notes: typeof o.notes === "string" ? o.notes : "",
              provenance: typeof o.provenance === "string" ? o.provenance : "",
              source_url: typeof o.source_url === "string" ? o.source_url : null,
            };
          })
      : undefined;

  const erlRaw = parsed.emergency_reference_links;
  const emergency_reference_links =
    Array.isArray(erlRaw) && erlRaw.length > 0
      ? (erlRaw as unknown[])
          .filter((x) => x !== null && typeof x === "object")
          .map((x) => {
            const o = x as Record<string, unknown>;
            return {
              title: typeof o.title === "string" ? o.title : "",
              url: typeof o.url === "string" ? o.url : "",
              source: typeof o.source === "string" ? o.source : "",
            };
          })
      : undefined;

  const clRaw = parsed.case_law_references;
  const case_law_references: CaseLawReference[] | undefined = Array.isArray(clRaw)
    ? (clRaw as unknown[])
        .filter((x) => x !== null && typeof x === "object")
        .map((x) => {
          const o = x as Record<string, unknown>;
          const yr = o.year;
          return {
            title: typeof o.title === "string" ? o.title : "",
            citation: typeof o.citation === "string" ? o.citation : "",
            court: typeof o.court === "string" ? o.court : "",
            year: typeof yr === "number" && Number.isFinite(yr) ? Math.floor(yr) : null,
            source: typeof o.source === "string" ? o.source : "",
            url: typeof o.url === "string" ? o.url : "",
            snippet: typeof o.snippet === "string" ? o.snippet : "",
            relevance_reason: typeof o.relevance_reason === "string" ? o.relevance_reason : "",
          };
        })
    : undefined;
  const prayer_items = Array.isArray(parsed.prayer_items) ? parsed.prayer_items.map(String) : undefined;
  const annexure_checklist = Array.isArray(parsed.annexure_checklist)
    ? parsed.annexure_checklist.map(String)
    : undefined;

  const evRaw = parsed.document_evaluator;
  const document_evaluator: DocumentEvaluatorReport | null | undefined =
    evRaw && typeof evRaw === "object" && !Array.isArray(evRaw)
      ? (evRaw as DocumentEvaluatorReport)
      : evRaw === null
        ? null
        : undefined;
  const docRev = parsed.document_revised;
  const document_revised =
    typeof docRev === "string" && docRev.trim() ? normalizeDocumentFromServer(docRev) : "";

  return {
    document: normalizeDocumentFromServer(parsed.document),
    draft,
    document_revised: document_revised || undefined,
    document_evaluator: document_evaluator ?? undefined,
    explanation: parsed.explanation.trim(),
    next_steps: parsed.next_steps.map(String),
    clarification_needed: parsed.clarification_needed === true,
    clarification_question:
      typeof parsed.clarification_question === "string" ? parsed.clarification_question : null,
    clarification_options,
    clarification_points,
    clarifying_questions,
    clarification_agent_questions,
    clarification_optional: clarification_optional || undefined,
    clarification_agent_reason: careason,
    clarification_agent_confidence_hint,
    authority: parseAuthority(parsed.authority),
    authority_compact,
    authority_disclaimer: disclaimer,
    authority_search_note:
      typeof parsed.authority_search_note === "string" ? parsed.authority_search_note : null,
    legal_explanation: typeof parsed.legal_explanation === "string" ? parsed.legal_explanation : null,
    procedure_steps,
    step_by_step_procedure: Array.isArray(parsed.step_by_step_procedure)
      ? parsed.step_by_step_procedure.map(String)
      : null,
    legal_references,
    retrieved_laws,
    confidence_score,
    rag_grounding_label,
    authority_summary,
    legal_classification,
    jurisdiction,
    trust_summary,
    trust_report,
    verifier,
    authority_hierarchy,
    crisis_triage_mode: parsed.crisis_triage_mode === true,
    generation_mode: typeof parsed.generation_mode === "string" ? parsed.generation_mode : undefined,
    alert: typeof parsed.alert === "string" ? parsed.alert : null,
    note: typeof parsed.note === "string" ? parsed.note : null,
    safety_tip: typeof parsed.safety_tip === "string" ? parsed.safety_tip : null,
    emergency_contacts,
    emergency_reference_links,
    emergency_registry_disclaimer:
      typeof parsed.emergency_registry_disclaimer === "string" ? parsed.emergency_registry_disclaimer : undefined,
    urgency_banner: typeof parsed.urgency_banner === "string" ? parsed.urgency_banner : null,
    urgency_level: typeof parsed.urgency_level === "string" ? parsed.urgency_level : undefined,
    generation_score: typeof parsed.generation_score === "number" && Number.isFinite(parsed.generation_score) ? parsed.generation_score : undefined,
    usage: parseUsageBlock(parsed.usage),
    client_mode:
      parsed.client_mode === "lawyer" || parsed.client_mode === "citizen" ? parsed.client_mode : "citizen",
    task_type:
      parsed.task_type === "qa_only" ||
      parsed.task_type === "draft_with_qa" ||
      parsed.task_type === "draft_letter" ||
      parsed.task_type === "consumer_complaint_filing"
        ? parsed.task_type
        : "draft_letter",
    case_law_references,
    forum_caption: typeof parsed.forum_caption === "string" ? parsed.forum_caption : null,
    prayer_items,
    annexure_checklist,
  };
}

export async function generateLegalResponse(payload: GenerateRequestPayload): Promise<GenerateResponse> {
  const trimmed = payload.user_input.trim();
  if (!trimmed) {
    throw new ClientApiError("api_empty_issue");
  }

  const body: Record<string, string | boolean | undefined> = { user_input: trimmed };
  const opt = ["full_name", "address", "city", "phone", "email"] as const;
  for (const k of opt) {
    const v = payload[k]?.trim();
    if (v) body[k] = v;
  }
  if (payload.skip_clarification === true) {
    body.skip_clarification = true;
  }
  if (payload.response_language) {
    body.response_language = payload.response_language;
  }
  if (payload.client_mode === "lawyer" || payload.client_mode === "citizen") {
    body.client_mode = payload.client_mode;
  }
  if (
    payload.task_type === "qa_only" ||
    payload.task_type === "draft_with_qa" ||
    payload.task_type === "draft_letter" ||
    payload.task_type === "consumer_complaint_filing"
  ) {
    body.task_type = payload.task_type;
  }

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (payload.userId) {
    headers["X-User-Id"] = payload.userId;
  }
  if (payload.response_language === "hi") {
    headers["Accept-Language"] = "hi-IN,hi;q=0.9,en;q=0.8";
  } else if (payload.response_language === "hi_latn") {
    headers["Accept-Language"] = "en-IN,en;q=0.9,hi-Latn;q=0.5";
  } else if (payload.response_language === "en") {
    headers["Accept-Language"] = "en-IN,en;q=0.9";
  }

  const res = await fetch(`${getBaseUrl()}/generate`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });

  const data: unknown = await res.json().catch(() => ({}));

  if (!res.ok) {
    const p = parseErrorPayload(data);
    throw new ServerApiError(p.message, res.status, p.errorCode);
  }

  return mapServerJsonToGenerateResponse(data);
}

function parseSseDataLines(buffer: string): { events: StreamEvent[]; rest: string } {
  const events: StreamEvent[] = [];
  let rest = buffer;
  let idx: number;
  while ((idx = rest.indexOf("\n\n")) !== -1) {
    const block = rest.slice(0, idx);
    rest = rest.slice(idx + 2);
    const lines = block.split("\n").map((l) => l.trimEnd());
    for (const line of lines) {
      if (!line.startsWith("data:")) continue;
      const jsonStr = line.slice(5).trim();
      if (!jsonStr) continue;
      try {
        const obj = JSON.parse(jsonStr) as { type?: string };
        const t = obj.type;
        if (t === "phase" && typeof (obj as { message?: unknown }).message === "string") {
          const ph = (obj as { phase?: unknown }).phase;
          events.push({
            type: "phase",
            message: (obj as { message: string }).message,
            ...(typeof ph === "string" && ph ? { phase: ph } : {}),
          });
        } else if (t === "clarification") {
          const q = (obj as { question?: unknown }).question;
          const opts = (obj as { options?: unknown }).options;
          const ptsRaw = (obj as { points?: unknown }).points;
          const points: ClarificationPoint[] | undefined =
            Array.isArray(ptsRaw) && ptsRaw.length > 0
              ? (ptsRaw as unknown[])
                  .filter((x) => x !== null && typeof x === "object")
                  .map((x) => {
                    const p = x as Record<string, unknown>;
                    const or = p.options;
                    return {
                      label: typeof p.label === "string" ? p.label : "",
                      options: Array.isArray(or) ? or.map(String) : [],
                    };
                  })
                  .filter((p) => p.label && p.options.length > 0)
              : undefined;
          const cqqRaw = (obj as { clarifying_questions?: unknown }).clarifying_questions;
          const clarifying_questions =
            Array.isArray(cqqRaw) && cqqRaw.length > 0 ? cqqRaw.map(String).filter((s) => s.trim()) : undefined;
          const aqRaw = (obj as { clarification_agent_questions?: unknown }).clarification_agent_questions;
          const clarification_agent_questions: ClarificationAgentQuestion[] | undefined =
            Array.isArray(aqRaw) && aqRaw.length > 0
              ? (aqRaw as unknown[])
                  .filter((x) => x !== null && typeof x === "object")
                  .map((x) => {
                    const a = x as Record<string, unknown>;
                    const o = a.options;
                    return {
                      id: typeof a.id === "string" ? a.id : "",
                      question: typeof a.question === "string" ? a.question : "",
                      type: typeof a.type === "string" ? a.type : "single_choice",
                      options: Array.isArray(o) ? o.map(String) : [],
                      required: a.required === true,
                    };
                  })
                  .filter((a) => a.question && a.options.length > 0)
              : undefined;
          const optClar = (obj as { clarification_optional?: unknown }).clarification_optional === true;
          const car = (obj as { clarification_agent_reason?: unknown }).clarification_agent_reason;
          const cach = (obj as { clarification_agent_confidence_hint?: unknown }).clarification_agent_confidence_hint;
          events.push({
            type: "clarification",
            question: typeof q === "string" ? q : "",
            options: Array.isArray(opts) ? opts.map(String) : [],
            points,
            clarifying_questions,
            clarification_agent_questions,
            clarification_optional: optClar,
            clarification_agent_reason: typeof car === "string" ? car : undefined,
            clarification_agent_confidence_hint:
              typeof cach === "number" && Number.isFinite(cach) ? cach : null,
            clarification_needed: (obj as { clarification_needed?: unknown }).clarification_needed === true,
          });
        } else if (t === "result") {
          const payload = (obj as { payload?: unknown }).payload;
          try {
            events.push({ type: "result", payload: mapServerJsonToGenerateResponse(payload) });
          } catch {
            events.push({
              type: "error",
              message: "Invalid result payload",
              clientMessageKey: "streamErrInvalidResult",
            });
          }
        } else if (t === "done") {
          events.push({ type: "done" });
        } else if (t === "error") {
          const m = (obj as { message?: unknown }).message;
          const ecRaw = (obj as { error_code?: unknown }).error_code;
          const ec = typeof ecRaw === "string" ? ecRaw : undefined;
          const msg = typeof m === "string" ? m : "Stream error";
          events.push({
            type: "error",
            message: msg,
            ...(ec ? { error_code: ec } : {}),
            ...(typeof m !== "string" ? { clientMessageKey: "streamErrGeneric" as const } : {}),
          });
        }
      } catch {
        events.push({
          type: "error",
          message: "Invalid stream data",
          clientMessageKey: "streamErrInvalidData",
        });
      }
    }
  }
  return { events, rest };
}

/** POST `/generate-stream` — yields typed events (SSE `data:` JSON lines). */
export async function streamGenerateLegalResponse(
  payload: GenerateRequestPayload,
  onEvent: (ev: StreamEvent) => void,
): Promise<void> {
  const trimmed = payload.user_input.trim();
  if (!trimmed) {
    throw new ClientApiError("api_empty_issue");
  }

  const body: Record<string, string | boolean | undefined> = { user_input: trimmed };
  const opt = ["full_name", "address", "city", "phone", "email"] as const;
  for (const k of opt) {
    const v = payload[k]?.trim();
    if (v) body[k] = v;
  }
  if (payload.skip_clarification === true) {
    body.skip_clarification = true;
  }
  if (payload.response_language) {
    body.response_language = payload.response_language;
  }
  if (payload.client_mode === "lawyer" || payload.client_mode === "citizen") {
    body.client_mode = payload.client_mode;
  }
  if (
    payload.task_type === "qa_only" ||
    payload.task_type === "draft_with_qa" ||
    payload.task_type === "draft_letter" ||
    payload.task_type === "consumer_complaint_filing"
  ) {
    body.task_type = payload.task_type;
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "text/event-stream",
  };
  if (payload.userId) {
    headers["X-User-Id"] = payload.userId;
  }
  if (payload.response_language === "hi") {
    headers["Accept-Language"] = "hi-IN,hi;q=0.9,en;q=0.8";
  } else if (payload.response_language === "hi_latn") {
    headers["Accept-Language"] = "en-IN,en;q=0.9,hi-Latn;q=0.5";
  } else if (payload.response_language === "en") {
    headers["Accept-Language"] = "en-IN,en;q=0.9";
  }

  let res: Response;
  try {
    res = await fetch(`${getBaseUrl()}/generate-stream`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
  } catch (e) {
    if (isLikelyNetworkFailure(e)) {
      const m = e instanceof Error ? e.message : "Network error";
      throw new StreamNetworkFailed(m, payload);
    }
    throw e;
  }

  if (!res.ok) {
    const data: unknown = await res.json().catch(() => ({}));
    const p = parseErrorPayload(data);
    throw new ServerApiError(p.message, res.status, p.errorCode);
  }

  const reader = res.body?.getReader();
  if (!reader) {
    throw new ClientApiError("api_no_response_body");
  }

  const decoder = new TextDecoder();
  let carry = "";
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      carry += decoder.decode(value, { stream: true });
      const { events, rest } = parseSseDataLines(carry);
      carry = rest;
      for (const ev of events) {
        onEvent(ev);
      }
    }
    if (carry.trim()) {
      const { events } = parseSseDataLines(carry + "\n\n");
      for (const ev of events) {
        onEvent(ev);
      }
    }
  } catch (e) {
    if (isLikelyNetworkFailure(e)) {
      const m = e instanceof Error ? e.message : "Network error";
      throw new StreamNetworkFailed(m, payload);
    }
    throw e;
  }
}

/** POST `/billing/create-checkout-session` (P2-01) — Stripe-hosted subscription Checkout URL. */
export async function createStripeCheckoutSession(userId: string | null): Promise<string> {
  const headers: Record<string, string> = {};
  if (userId) headers["X-User-Id"] = userId;
  const res = await fetch(`${getBaseUrl()}/billing/create-checkout-session`, {
    method: "POST",
    headers,
  });
  const data: unknown = await res.json().catch(() => ({}));
  if (!res.ok) {
    const p = parseErrorPayload(data);
    throw new ServerApiError(p.message, res.status, p.errorCode);
  }
  const j = data as Record<string, unknown>;
  const url = j.checkout_url;
  if (typeof url !== "string" || !url.startsWith("http")) {
    throw new ClientApiError("api_invalid_response");
  }
  return url;
}

export async function createBillingPortalSession(userId: string | null): Promise<string> {
  const headers: Record<string, string> = {};
  if (userId) headers["X-User-Id"] = userId;
  const res = await fetch(`${getBaseUrl()}/billing/create-portal-session`, {
    method: "POST",
    headers,
  });
  const data: unknown = await res.json().catch(() => ({}));
  if (!res.ok) {
    const p = parseErrorPayload(data);
    throw new ServerApiError(p.message, res.status, p.errorCode);
  }
  const j = data as Record<string, unknown>;
  const url = j.portal_url;
  if (typeof url !== "string" || !url.startsWith("http")) {
    throw new ClientApiError("api_invalid_response");
  }
  return url;
}

export type DashboardCase = {
  id: string;
  title: string;
  summary: string | null;
  result: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export async function fetchDashboardCases(userId: string): Promise<DashboardCase[]> {
  const res = await fetch(`${getBaseUrl()}/dashboard/cases`, {
    method: "GET",
    cache: "no-store",
    headers: { "X-User-Id": userId },
  });
  const data: unknown = await res.json().catch(() => ({}));
  if (!res.ok) {
    const p = parseErrorPayload(data);
    throw new ServerApiError(p.message, res.status, p.errorCode);
  }
  const j = data as { cases?: unknown };
  if (!Array.isArray(j.cases)) return [];
  return j.cases as DashboardCase[];
}

export async function createDashboardCase(
  userId: string,
  body: { title: string; summary?: string; result?: Record<string, unknown> | null },
): Promise<DashboardCase> {
  const res = await fetch(`${getBaseUrl()}/dashboard/cases`, {
    method: "POST",
    cache: "no-store",
    headers: { "X-User-Id": userId, "Content-Type": "application/json" },
    body: JSON.stringify({
      title: body.title,
      summary: body.summary,
      result: body.result ?? undefined,
    }),
  });
  const data: unknown = await res.json().catch(() => ({}));
  if (!res.ok) {
    const p = parseErrorPayload(data);
    throw new ServerApiError(p.message, res.status, p.errorCode);
  }
  return data as DashboardCase;
}

export async function deleteDashboardCase(userId: string, caseId: string): Promise<void> {
  const res = await fetch(`${getBaseUrl()}/dashboard/cases/${encodeURIComponent(caseId)}`, {
    method: "DELETE",
    cache: "no-store",
    headers: { "X-User-Id": userId },
  });
  const data: unknown = await res.json().catch(() => ({}));
  if (!res.ok) {
    const p = parseErrorPayload(data);
    throw new ServerApiError(p.message, res.status, p.errorCode);
  }
}

/** Signed-in chat history (`/chat/threads`) — Clerk user via `X-User-Id`. */
export type ChatThreadSummary = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type ChatHistoryMessage = {
  id: string;
  thread_id: string;
  role: "user" | "assistant";
  content: string;
  meta: Record<string, unknown> | null;
  created_at: string;
};

export async function fetchChatThreads(userId: string, limit = 50): Promise<ChatThreadSummary[]> {
  const res = await fetch(`${getBaseUrl()}/chat/threads?limit=${limit}`, {
    method: "GET",
    cache: "no-store",
    headers: { "X-User-Id": userId },
  });
  const data: unknown = await res.json().catch(() => ({}));
  if (!res.ok) {
    const p = parseErrorPayload(data);
    throw new ServerApiError(p.message, res.status, p.errorCode);
  }
  const j = data as { threads?: unknown };
  if (!Array.isArray(j.threads)) return [];
  return j.threads as ChatThreadSummary[];
}

export async function createChatThread(userId: string, title?: string): Promise<ChatThreadSummary> {
  const res = await fetch(`${getBaseUrl()}/chat/threads`, {
    method: "POST",
    cache: "no-store",
    headers: { "X-User-Id": userId, "Content-Type": "application/json" },
    body: JSON.stringify({ title: title ?? undefined }),
  });
  const data: unknown = await res.json().catch(() => ({}));
  if (!res.ok) {
    const p = parseErrorPayload(data);
    throw new ServerApiError(p.message, res.status, p.errorCode);
  }
  return data as ChatThreadSummary;
}

export async function patchChatThreadTitle(userId: string, threadId: string, title: string): Promise<void> {
  const res = await fetch(`${getBaseUrl()}/chat/threads/${encodeURIComponent(threadId)}`, {
    method: "PATCH",
    cache: "no-store",
    headers: { "X-User-Id": userId, "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  const data: unknown = await res.json().catch(() => ({}));
  if (!res.ok) {
    const p = parseErrorPayload(data);
    throw new ServerApiError(p.message, res.status, p.errorCode);
  }
}

export async function fetchThreadMessages(userId: string, threadId: string, limit = 500): Promise<ChatHistoryMessage[]> {
  const res = await fetch(
    `${getBaseUrl()}/chat/threads/${encodeURIComponent(threadId)}/messages?limit=${limit}`,
    {
      method: "GET",
      cache: "no-store",
      headers: { "X-User-Id": userId },
    },
  );
  const data: unknown = await res.json().catch(() => ({}));
  if (!res.ok) {
    const p = parseErrorPayload(data);
    throw new ServerApiError(p.message, res.status, p.errorCode);
  }
  const j = data as { messages?: unknown };
  if (!Array.isArray(j.messages)) return [];
  return j.messages as ChatHistoryMessage[];
}

export async function postChatMessage(
  userId: string,
  threadId: string,
  body: { role: "user" | "assistant"; content: string; meta?: Record<string, unknown> },
): Promise<ChatHistoryMessage> {
  const res = await fetch(`${getBaseUrl()}/chat/threads/${encodeURIComponent(threadId)}/messages`, {
    method: "POST",
    cache: "no-store",
    headers: { "X-User-Id": userId, "Content-Type": "application/json" },
    body: JSON.stringify({
      role: body.role,
      content: body.content,
      meta: body.meta,
    }),
  });
  const data: unknown = await res.json().catch(() => ({}));
  if (!res.ok) {
    const p = parseErrorPayload(data);
    throw new ServerApiError(p.message, res.status, p.errorCode);
  }
  return data as ChatHistoryMessage;
}
