from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    # Second-pass evaluator + refiner (two extra LLM calls per successful generate). Env: EVALUATOR_DUAL_DRAFT=true
    evaluator_dual_draft_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("EVALUATOR_DUAL_DRAFT", "evaluator_dual_draft_enabled"),
    )
    cors_origins: str = "http://localhost:3000"
    # When true, allow browser Origin matching App Runner default hostnames (HTTPS). Env: CORS_ALLOW_APPRUNNER_REGEX
    cors_allow_apprunner_regex: bool = Field(
        default=False,
        validation_alias=AliasChoices("CORS_ALLOW_APPRUNNER_REGEX", "cors_allow_apprunner_regex"),
    )
    # Product: none = hide paywall; stub = "coming soon" copy; stripe = Checkout (see `app/api/v1/billing.py`)
    billing_mode: str = "none"
    # Stripe (P2-01): `POST /billing/create-checkout-session` when BILLING_MODE=stripe + secret + price id
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""
    # Success/cancel URLs for Checkout; must match your Next.js origin (CORS)
    public_app_url: str = "http://localhost:3000"
    # Post–free-trial signed-in daily cap (UTC day). Trial window uses `daily_limit_trial` instead.
    daily_limit_authenticated: int = Field(default=10, ge=1)
    # Higher cap during the first `trial_period_days` after first authenticated activity (SQLite-backed).
    daily_limit_trial: int = Field(
        default=50,
        ge=1,
        validation_alias=AliasChoices("DAILY_LIMIT_TRIAL", "daily_limit_trial"),
    )
    trial_period_days: int = Field(
        default=7,
        ge=0,
        validation_alias=AliasChoices("TRIAL_PERIOD_DAYS", "trial_period_days"),
    )
    trial_db_path: str = ""
    # GTM / future billing: displayed base tier price (INR); payment collection not implied.
    base_tier_price_inr: int = Field(
        default=1,
        ge=0,
        validation_alias=AliasChoices("BASE_TIER_PRICE_INR", "base_tier_price_inr"),
    )
    # When `BILLING_MODE=stripe` and webhooks recorded an active/trialing subscription for the Clerk user
    daily_limit_pro: int = 500
    daily_limit_anonymous: int = 15
    # Phase 6: stop attaching pipeline clarifications when `clarification_round` reaches this (0-based; was 2).
    clarification_max_rounds: int = Field(
        default=8,
        ge=1,
        le=20,
        validation_alias=AliasChoices("CLARIFICATION_MAX_ROUNDS", "clarification_max_rounds"),
    )
    # SQLite path for Stripe → Clerk subscription rows (`:memory:` for isolated tests)
    entitlements_db_path: str = ""
    # When set, entitlements use Postgres instead of SQLite (multi-instance). See docs/ENTITLEMENTS_POSTGRES.md
    entitlements_database_url: str = ""
    # P8-01: SQLite path for `/dashboard/cases` rows (`:memory:` in tests)
    cases_db_path: str = ""
    # P8-02: SQLite path for lightweight response feedback rows (`:memory:` in tests)
    feedback_db_path: str = ""
    # Chat history threads/messages per Clerk user (default `var/chat_history.sqlite`)
    chat_history_db_path: str = ""
    # When set, daily generate/ingest counters use Redis (multi-instance). See docs/RATE_LIMIT_REDIS.md
    redis_url: str = ""
    max_upload_bytes: int = 2_000_000
    max_pdf_pages_extract: int = 40
    # P3-01 image OCR: none | openai | textract | tesseract (see `backend/docs/OCR_AND_AWS.md`)
    ingest_ocr_provider: str = "none"
    ingest_ocr_max_long_edge_px: int = 2000
    ingest_ocr_openai_model: str = "gpt-4o-mini"
    ingest_ocr_openai_max_tokens: int = 2048
    ingest_ocr_tesseract_lang: str = "eng"
    # P3-03: max PDF pages to rasterize + OCR when text layer is empty (0 disables; clamped in validator)
    ingest_ocr_pdf_max_pages: int = 3
    aws_region: str = ""

    tavily_api_key: str = ""
    serpapi_api_key: str = ""
    bing_search_api_key: str = ""
    bing_search_endpoint: str = "https://api.bing.microsoft.com/v7.0/search"

    @field_validator("cors_allow_apprunner_regex", mode="before")
    @classmethod
    def _truthy_cors_apprunner_flag(cls, v: object) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in ("1", "true", "yes", "on")
        return False

    @field_validator("evaluator_dual_draft_enabled", mode="before")
    @classmethod
    def _truthy_evaluator_flag(cls, v: object) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in ("1", "true", "yes", "on")
        return False

    @field_validator("openai_api_key", mode="before")
    @classmethod
    def strip_api_key(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("trial_db_path", mode="before")
    @classmethod
    def strip_trial_db_path(cls, v: object) -> str:
        if isinstance(v, str):
            return v.strip()
        return ""

    @field_validator("stripe_secret_key", "stripe_webhook_secret", "stripe_price_id", mode="before")
    @classmethod
    def strip_stripe_fields(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("public_app_url", mode="before")
    @classmethod
    def strip_public_app_url(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip().rstrip("/")
        return v

    @field_validator("aws_region", mode="before")
    @classmethod
    def strip_aws_region(cls, v: object) -> str:
        if isinstance(v, str):
            return v.strip()
        return ""

    @field_validator("ingest_ocr_tesseract_lang", mode="before")
    @classmethod
    def strip_tesseract_lang(cls, v: object) -> str:
        if isinstance(v, str):
            s = v.strip()
            return s if s else "eng"
        return "eng"

    @field_validator("ingest_ocr_provider", mode="before")
    @classmethod
    def norm_ingest_ocr_provider(cls, v: object) -> str:
        s = str(v or "none").strip().lower()
        if s in ("none", "openai", "textract", "tesseract"):
            return s
        return "none"

    @field_validator("ingest_ocr_max_long_edge_px", mode="before")
    @classmethod
    def _ocr_edge_bounds(cls, v: object) -> int:
        try:
            n = int(v) if v is not None else 2000
        except (TypeError, ValueError):
            return 2000
        return max(512, min(8000, n))

    @field_validator("ingest_ocr_openai_max_tokens", mode="before")
    @classmethod
    def _ocr_tokens_bounds(cls, v: object) -> int:
        try:
            n = int(v) if v is not None else 2048
        except (TypeError, ValueError):
            return 2048
        return max(256, min(8192, n))

    @field_validator("ingest_ocr_pdf_max_pages", mode="before")
    @classmethod
    def _ocr_pdf_pages_bounds(cls, v: object) -> int:
        try:
            n = int(v) if v is not None else 3
        except (TypeError, ValueError):
            return 3
        return max(0, min(20, n))

    @field_validator("entitlements_db_path", mode="before")
    @classmethod
    def strip_entitlements_db_path(cls, v: object) -> str:
        if isinstance(v, str):
            return v.strip()
        return ""

    @field_validator("entitlements_database_url", mode="before")
    @classmethod
    def strip_entitlements_database_url(cls, v: object) -> str:
        if isinstance(v, str):
            return v.strip()
        return ""

    @field_validator("cases_db_path", mode="before")
    @classmethod
    def strip_cases_db_path(cls, v: object) -> str:
        if isinstance(v, str):
            return v.strip()
        return ""

    @field_validator("feedback_db_path", mode="before")
    @classmethod
    def strip_feedback_db_path(cls, v: object) -> str:
        if isinstance(v, str):
            return v.strip()
        return ""

    @field_validator("chat_history_db_path", mode="before")
    @classmethod
    def strip_chat_history_db_path(cls, v: object) -> str:
        if isinstance(v, str):
            return v.strip()
        return ""

    @field_validator("redis_url", mode="before")
    @classmethod
    def strip_redis_url(cls, v: object) -> str:
        if isinstance(v, str):
            return v.strip()
        return ""

    @field_validator("billing_mode", mode="before")
    @classmethod
    def norm_billing_mode(cls, v: object) -> str:
        s = str(v or "none").strip().lower()
        if s in ("none", "stub", "stripe"):
            return s
        return "none"

    @field_validator("daily_limit_pro", mode="before")
    @classmethod
    def _daily_limit_pro_min(cls, v: object) -> int:
        try:
            n = int(v) if v is not None else 500
        except (TypeError, ValueError):
            return 500
        return max(1, n)

    # RAG: "local" = in-process embed over curated JSON; "pinecone" = server index (see `app/rag/pinecone_ingest.py`)
    rag_vector_store: str = "local"
    pinecone_api_key: str = ""
    pinecone_index: str = "nyaya-legal-kb"
    # Optional; default namespace is "" (Pinecone default)
    pinecone_namespace: str = ""
    # Pre-issue-filter fetch size; final list is still issue-filtered in-app. Citizen tier; lawyer override below.
    pinecone_query_candidates: int = 48
    # Optional: larger Pinecone pre-fetch for lawyer tier (cost). None => implicit bump (base + 24, cap 200).
    pinecone_query_candidates_lawyer: int | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "PINECONE_QUERY_CANDIDATES_LAWYER",
            "pinecone_query_candidates_lawyer",
        ),
    )
    # Strict RAG `top_k` by client_mode (P1-2). RAG_TOP_K_DEFAULT is an alias for RAG_TOP_K_CITIZEN (Sprint P3-1).
    rag_top_k_citizen: int = Field(
        default=8,
        validation_alias=AliasChoices("RAG_TOP_K_CITIZEN", "RAG_TOP_K_DEFAULT", "rag_top_k_citizen"),
    )
    rag_top_k_lawyer: int = 12

    # Sprint 6: case-law research adapter — `off` = hidden; `noop` = empty placeholder; `tavily_preview` = web research snippets
    case_law_mode: str = Field(
        default="off",
        validation_alias=AliasChoices("CASE_LAW_MODE", "case_law_mode"),
    )
    case_law_max_results: int = Field(
        default=5,
        validation_alias=AliasChoices("CASE_LAW_MAX_RESULTS", "case_law_max_results"),
    )

    @field_validator("case_law_mode", mode="before")
    @classmethod
    def _norm_case_law_mode(cls, v: object) -> str:
        s = str(v or "off").strip().lower()
        if s in ("off", "noop", "tavily_preview"):
            return s
        return "off"

    @field_validator("case_law_max_results", mode="before")
    @classmethod
    def _bounds_case_law_max_results(cls, v: object) -> int:
        try:
            n = int(v) if v is not None else 5
        except (TypeError, ValueError):
            return 5
        return max(1, min(10, n))

    @field_validator("rag_vector_store", mode="before")
    @classmethod
    def norm_rag_vector_store(cls, v: object) -> str:
        s = str(v or "local").strip().lower()
        if s in ("local", "pinecone"):
            return s
        return "local"

    @field_validator("pinecone_query_candidates", mode="before")
    @classmethod
    def _rag_candidates_min(cls, v: object) -> int:
        if v is None:
            return 48
        try:
            n = int(v)
        except (TypeError, ValueError):
            return 48
        return max(8, min(200, n))

    @field_validator("pinecone_query_candidates_lawyer", mode="before")
    @classmethod
    def _rag_candidates_lawyer_bounds(cls, v: object) -> int | None:
        if v is None or v == "":
            return None
        try:
            n = int(v)
        except (TypeError, ValueError):
            return None
        return max(8, min(200, n))

    @field_validator("rag_top_k_citizen", mode="before")
    @classmethod
    def _rag_top_k_citizen_bounds(cls, v: object) -> int:
        try:
            n = int(v) if v is not None else 8
        except (TypeError, ValueError):
            return 8
        return max(3, min(24, n))

    @field_validator("rag_top_k_lawyer", mode="before")
    @classmethod
    def _rag_top_k_lawyer_bounds(cls, v: object) -> int:
        try:
            n = int(v) if v is not None else 12
        except (TypeError, ValueError):
            return 12
        return max(3, min(24, n))

    # Subset of citizen,lawyer advertised to the UI (GET /config, /ready). Env: CLIENT_MODES_SUPPORTED
    client_modes_supported_csv: str = Field(
        default="citizen,lawyer",
        validation_alias=AliasChoices("CLIENT_MODES_SUPPORTED", "client_modes_supported_csv"),
    )

    @field_validator("client_modes_supported_csv", mode="before")
    @classmethod
    def _norm_client_modes_csv(cls, v: object) -> str:
        if v is None:
            return "citizen,lawyer"
        s = str(v).strip().lower().replace(" ", "")
        return s if s else "citizen,lawyer"

    # P1-1: when true, `client_mode=lawyer` on /generate requires non-empty X-User-Id (Clerk id).
    lawyer_client_mode_requires_user_id: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "LAWYER_CLIENT_MODE_REQUIRES_USER_ID",
            "lawyer_client_mode_requires_user_id",
        ),
    )

    @field_validator("lawyer_client_mode_requires_user_id", mode="before")
    @classmethod
    def _truthy_lawyer_requires_uid(cls, v: object) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in ("1", "true", "yes", "on")
        return False

    # P1-1: when true, lawyer mode on /generate also requires an active Pro row (Stripe billing only).
    lawyer_client_mode_requires_pro: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "LAWYER_CLIENT_MODE_REQUIRES_PRO",
            "lawyer_client_mode_requires_pro",
        ),
    )

    @field_validator("lawyer_client_mode_requires_pro", mode="before")
    @classmethod
    def _truthy_lawyer_requires_pro(cls, v: object) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in ("1", "true", "yes", "on")
        return False

    def lawyer_pro_gate_active(self) -> bool:
        """True when the API will enforce Pro for `client_mode=lawyer` (only meaningful with Stripe billing)."""
        return bool(self.lawyer_client_mode_requires_pro and str(self.billing_mode).strip().lower() == "stripe")

    def get_client_modes_supported(self) -> list[str]:
        """Stable order for API JSON: citizen then lawyer. Invalid CSV => both. `lawyer` token => list both."""
        raw = str(self.client_modes_supported_csv or "").strip().lower()
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        selected: set[str] = set()
        for p in parts:
            pl = p.strip().lower()
            if pl in ("citizen", "lawyer"):
                selected.add(pl)
        if not selected:
            return ["citizen", "lawyer"]
        if "lawyer" in selected:
            return ["citizen", "lawyer"]
        return ["citizen"]

    def pinecone_query_fetch_size(self, client_mode: str) -> int:
        """P3-2: Pre–issue-filter Pinecone query size; lawyer can fetch more (cost cap 200)."""
        base = max(8, min(200, int(self.pinecone_query_candidates or 48)))
        if str(client_mode).lower() == "lawyer":
            ovr = self.pinecone_query_candidates_lawyer
            if ovr is not None:
                return max(8, min(200, int(ovr)))
            return min(200, max(8, base + 24))
        return base


settings = Settings()
