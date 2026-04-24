from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.billing import router as billing_router, stripe_checkout_ready, stripe_portal_ready
from app.api.v1.config_public import router as config_public_router
from app.api.v1.generate import router as generate_router
from app.api.v1.dashboard_cases import router as dashboard_cases_router
from app.api.v1.ingest import router as ingest_router
from app.api.v1.transcribe import router as transcribe_router
from app.config import settings

app = FastAPI(title="NyayaSetu API", version="0.1.0")

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
# App Runner: https://<id>.<region>.awsapprunner.com — avoids chicken/egg with CORS_ORIGINS before web URL exists.
_apprunner_origin_regex = (
    r"^https://[\w-]+\.[\w-]+\.awsapprunner\.com$"
    if settings.cors_allow_apprunner_regex
    else None
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["http://localhost:3000"],
    allow_origin_regex=_apprunner_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(config_public_router, tags=["config"])
app.include_router(billing_router, tags=["billing"])
app.include_router(generate_router, tags=["generate"])
app.include_router(ingest_router, tags=["ingest"])
app.include_router(transcribe_router, tags=["transcribe"])
app.include_router(dashboard_cases_router, tags=["dashboard"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, str | bool]:
    """Liveness: always up. `openai_configured` false means generation will 503 (NS-S6-03)."""
    pinecone_key = bool(settings.pinecone_api_key and str(settings.pinecone_api_key).strip())
    pinecone_name = bool(settings.pinecone_index and str(settings.pinecone_index).strip())
    return {
        "status": "ok",
        "openai_configured": bool(settings.openai_api_key and str(settings.openai_api_key).strip()),
        "openai_model": settings.openai_model,
        "rag_vector_store": settings.rag_vector_store,
        "pinecone_configured": pinecone_key and pinecone_name,
        "stripe_checkout_ready": stripe_checkout_ready(),
        "stripe_portal_ready": stripe_portal_ready(),
    }
