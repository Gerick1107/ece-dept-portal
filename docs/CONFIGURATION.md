# Configuration reference

Primary env file: `backend/.env` (see `backend/.env.example` if present). Docker uses `.env.docker`.

## Core

| Variable | Purpose |
|----------|---------|
| `APP_ENV` | `development` / `production` |
| `DEBUG` | Must be false in production |
| `SECRET_KEY` | JWT signing secret (required strong value in production) |
| `API_V1_PREFIX` | Default `/api/v1` |
| `CORS_ORIGINS` | Comma-separated browser origins |

## Database

| Variable | Purpose |
|----------|---------|
| `MYSQL_HOST` / `MYSQL_PORT` / `MYSQL_USER` / `MYSQL_PASSWORD` / `MYSQL_DATABASE` | SQLAlchemy DSN parts |
| `DATABASE_URL` | Optional full URL override |

## Auth bootstrap

| Variable | Purpose |
|----------|---------|
| `BOOTSTRAP_ADMIN_EMAIL` | Created on first boot if no admin |
| `BOOTSTRAP_ADMIN_PASSWORD` | Initial admin password (`must_change_password` may apply) |

## Publications / SerpAPI

| Variable | Purpose |
|----------|---------|
| `SERP_API_KEYS` or `SERP_API_KEY` | Google Scholar author scrape via SerpAPI |
| `SCRAPER_BACKEND` | `serpapi` (production path) or `scholarly` |
| `ENABLE_SCHEDULER` | Periodic publication scrape jobs |
| `DATA_ASSETS` | Absolute path to CSV/Excel assets (default `data/assets`) |

## Local LLM (Ollama)

| Variable | Purpose |
|----------|---------|
| `LOCAL_LLM_BASE_URL` | Default `http://localhost:11434/v1` |
| `LOCAL_LLM_MODEL` | Default `llama3.2:3b` |
| `LOCAL_LLM_WARMUP_ON_STARTUP` | Prefetch model weights |

## Storage / mail / reminders

| Variable | Purpose |
|----------|---------|
| `UPLOAD_DIR` | Upload root under `storage/` |
| `ENABLE_REQUIREMENT_REMINDERS` | Requirement tracker email scheduler |
| SMTP-related vars | Used by notification / password reset flows (see `USER_MANAGEMENT.md`) |

## Frontend

| Variable | Purpose |
|----------|---------|
| `VITE_API_BASE` | Default `/api/v1` (dev proxy) |
| `VITE_INACTIVITY_MINUTES` | Auto-logout idle timeout |

When a variable is missing in production, check `backend/app/config.py` — it is the authoritative Settings model.
