import shutil
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
DATA_ASSETS = PROJECT_ROOT / "data" / "assets"


def _first_existing(*paths: Path) -> Path:
    for path in paths:
        if path.exists():
            return path.resolve()
    return paths[0].resolve()


def resolve_data_file(env_value: str | None, default_name: str, root_alternates: list[str]) -> str:
    """Resolve Excel reference files to absolute paths (env relative paths often break)."""
    candidates: list[Path] = []
    if env_value:
        raw = Path(env_value)
        if raw.is_absolute():
            candidates.append(raw)
        else:
            candidates.extend(
                [
                    (BACKEND_ROOT / raw).resolve(),
                    (PROJECT_ROOT / raw).resolve(),
                    (Path.cwd() / raw).resolve(),
                ]
            )
    candidates.append(DATA_ASSETS / default_name)
    for name in root_alternates:
        candidates.append(PROJECT_ROOT / name)
    return str(_first_existing(*candidates))


def ensure_reference_data_files() -> None:
    """Copy bundled Excel from project root into data/assets if missing."""
    DATA_ASSETS.mkdir(parents=True, exist_ok=True)
    pairs = [
        (
            "default_mapping.xlsx",
            "Course, CO and PO mapping Nov 2025 (2).xlsx",
        ),
        ("indirect.xlsx", "indirect.xlsx"),
    ]
    for dest_name, src_name in pairs:
        dest = DATA_ASSETS / dest_name
        if dest.exists():
            continue
        src = PROJECT_ROOT / src_name
        if src.exists():
            shutil.copy2(src, dest)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ECE Department Automation Portal"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    secret_key: str = "dev-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    # Prefer MYSQL_* fields (passwords with @, #, etc. work without URL encoding).
    # Optional: set DATABASE_URL to override the assembled URL (production).
    database_url: str = ""
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "portal_user"
    mysql_password: str = "portal_pass"
    mysql_database: str = "ece_dept_portal"

    upload_dir: str = str(BACKEND_ROOT / "storage" / "uploads")
    results_dir: str = str(BACKEND_ROOT / "storage" / "results")
    archive_dir: str = str(BACKEND_ROOT / "storage" / "archives")
    file_max_age_seconds: int = 1800

    default_mapping_path: str = ""
    default_indirect_path: str = ""

    bootstrap_admin_email: str = "admin@ece.iiitd.ac.in"
    bootstrap_admin_password: str = "ChangeMeOnFirstLogin!"

    portal_frontend_url: str = "http://localhost:5173"

    smtp_enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_use_tls: bool = True
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""

    publications_scrape_delay_min_seconds: float = 3.0
    publications_scrape_delay_max_seconds: float = 8.0

    serp_api_key: str = ""
    scraper_backend: str = "scholarly"
    enable_scheduler: bool = False

    projects_upload_dir: str = str(BACKEND_ROOT / "storage" / "uploads" / "projects")

    # SDG tagging — set ENABLE_SDG_LLM=true to turn on Gemini/OpenRouter auto-tagging
    enable_sdg_llm: bool = False
    sdg_llm_provider: str = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash-lite"
    openrouter_api_key: str = ""
    openrouter_model: str = "deepseek/deepseek-chat"
    sdg_request_delay_seconds: float = 6.0
    sdg_max_retries: int = 5

    @model_validator(mode="after")
    def _assemble_database_url(self) -> "Settings":
        if not self.database_url.strip():
            user = quote_plus(self.mysql_user)
            password = quote_plus(self.mysql_password)
            self.database_url = (
                f"mysql+pymysql://{user}:{password}"
                f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def resolved_mapping_path(self) -> str:
        return resolve_data_file(
            self.default_mapping_path or None,
            "default_mapping.xlsx",
            [
                "Course, CO and PO mapping Nov 2025 (2).xlsx",
                "Course, CO and PO mapping Nov 2025 (3).xlsx",
            ],
        )

    @property
    def resolved_indirect_path(self) -> str:
        return resolve_data_file(
            self.default_indirect_path or None,
            "indirect.xlsx",
            ["indirect.xlsx"],
        )


@lru_cache
def get_settings() -> Settings:
    ensure_reference_data_files()
    return Settings()
