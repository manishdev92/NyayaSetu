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
    daily_limit_authenticated: int = 50
    # When `BILLING_MODE=stripe` and webhooks recorded an active/trialing subscription for the Clerk user
    daily_limit_pro: int = 500
    daily_limit_anonymous: int = 15
    # SQLite path for Stripe → Clerk subscription rows (`:memory:` for isolated tests)
    entitlements_db_path: str = ""
    # When set, entitlements use Postgres instead of SQLite (multi-instance). See docs/ENTITLEMENTS_POSTGRES.md
    entitlements_database_url: str = ""
    # P8-01: SQLite path for `/dashboard/cases` rows (`:memory:` in tests)
    cases_db_path: str = ""
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
    # Pre-issue-filter fetch size; final list is still issue-filtered in-app
    pinecone_query_candidates: int = 48

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


settings = Settings()
