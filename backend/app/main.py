import logging
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.auth.service import bootstrap_admin_if_needed
from app.config import get_settings
from app.middleware.security import (
    BlockedUserAgentMiddleware,
    LoginRateLimitMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.copo.download_tokens import cleanup_stale_tokens
from app.analytics.router import router as analytics_router
from app.notifications.routes.router import router as notifications_router
from app.awards.routes.router import router as awards_router
from app.budget.routes.router import router as budget_router
from app.documents.routes.router import router as documents_router
from app.contributions.routes.router import router as contributions_router
from app.course_allocation.routes.router import router as course_allocation_router
from app.copo.router import router as copo_router
from app.courses.routes.router import router as courses_router
from app.copo.services.file_manager import cleanup_upload_directory, ensure_storage_dirs
from app.documents.services.file_manager import ensure_documents_dirs
from app.database.base import Base
from app.database.session import SessionLocal, engine
from app.publications.routes.router import router as publications_router
from app.projects.routes.router import router as projects_router
from app.ece_eve_projects.routes.router import router as ece_eve_projects_router
from app.llm.routes.router import router as llm_insights_router
from app.projects.services.file_manager import ensure_projects_upload_dir
from app.publications.scheduler.jobs import ensure_requirement_reminder_scheduler_started, ensure_scheduler_started

from app.moderation.routes.router import router as moderation_router
from app.labs.routes.router import router as labs_router

settings = get_settings()
logger = logging.getLogger("uvicorn.error")

if settings.app_env == "production":
    if settings.debug:
        logger.warning("DEBUG is enabled in production — set DEBUG=false")
    if settings.secret_key in ("dev-change-me", "change-me", "secret"):
        raise RuntimeError("SECRET_KEY must be set to a strong random value in production")


def _periodic_cleanup_loop():
    while True:
        time.sleep(300)
        try:
            cleanup_stale_tokens()
            cleanup_upload_directory()
        except Exception:
            pass


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_storage_dirs()
    ensure_projects_upload_dir()
    ensure_documents_dirs()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        bootstrap_admin_if_needed(db)
        from app.publications.services.affiliations_import_service import import_faculty_affiliations

        try:
            import_faculty_affiliations(db)
        except Exception as exc:
            logger.warning("Faculty affiliations import skipped: %s", exc)
        try:
            from app.documents.services.ingestion_service import seed_documents_from_disk

            docs_root = ensure_documents_dirs()
            await seed_documents_from_disk(db, docs_root)
        except Exception as exc:
            logger.warning("Document seeding skipped: %s", exc)
    finally:
        db.close()
    if settings.enable_requirement_reminders:
        ensure_requirement_reminder_scheduler_started()
    if settings.enable_scheduler:
        ensure_scheduler_started()
    if settings.local_llm_warmup_on_startup:
        from app.llm.services.local_service import warm_up_model

        threading.Thread(target=warm_up_model, daemon=True).start()
    thread = threading.Thread(target=_periodic_cleanup_loop, daemon=True)
    thread.start()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if settings.app_env == "production" else "/api/docs",
    openapi_url=None if settings.app_env == "production" else "/api/openapi.json",
    redoc_url=None if settings.app_env == "production" else "/api/redoc",
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoginRateLimitMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(BlockedUserAgentMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# The routers live on a mounted sub-app; disable its interactive docs in
# production too (the parent app already hides its own docs there).
_docs_enabled = settings.app_env != "production"
api = FastAPI(
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)
api.include_router(auth_router)
api.include_router(copo_router)
api.include_router(courses_router)
api.include_router(awards_router)
api.include_router(budget_router)
api.include_router(contributions_router)
api.include_router(course_allocation_router)
api.include_router(documents_router)
api.include_router(analytics_router)
api.include_router(notifications_router)
api.include_router(publications_router)
api.include_router(projects_router)
api.include_router(ece_eve_projects_router)
api.include_router(llm_insights_router)
api.include_router(moderation_router)
api.include_router(labs_router)

app.mount(settings.api_v1_prefix, api)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}
