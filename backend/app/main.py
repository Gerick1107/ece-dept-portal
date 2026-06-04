import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.auth.service import bootstrap_admin_if_needed
from app.config import get_settings
from app.copo.download_tokens import cleanup_stale_tokens
from app.analytics.router import router as analytics_router
from app.awards.routes.router import router as awards_router
from app.copo.router import router as copo_router
from app.courses.routes.router import router as courses_router
from app.copo.services.file_manager import cleanup_upload_directory, ensure_storage_dirs
from app.database.base import Base
from app.database.session import SessionLocal, engine
from app.publications.routes.router import router as publications_router
from app.projects.routes.router import router as projects_router
from app.projects.services.file_manager import ensure_projects_upload_dir
from app.publications.scheduler import ensure_scheduler_started

settings = get_settings()


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
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        bootstrap_admin_if_needed(db)
    finally:
        db.close()
    if settings.enable_scheduler:
        ensure_scheduler_started()
    thread = threading.Thread(target=_periodic_cleanup_loop, daemon=True)
    thread.start()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = FastAPI()
api.include_router(auth_router)
api.include_router(copo_router)
api.include_router(courses_router)
api.include_router(awards_router)
api.include_router(analytics_router)
api.include_router(publications_router)
api.include_router(projects_router)

app.mount(settings.api_v1_prefix, api)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}
