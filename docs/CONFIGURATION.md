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
| `BOOTSTRAP_ADMIN_EMAIL` | Created on first boot if no admin exists. Default: `admin@ece.iiitd.ac.in` |
| `BOOTSTRAP_ADMIN_PASSWORD` | Initial admin password. Default: `ChangeMeOnFirstLogin!` (`must_change_password` may apply) |

These apply in `backend/.env` (native) or `.env.docker` (Docker). Bootstrap runs **once** — changing the env later does not reset an existing admin password unless you use `backend/scripts/reset_admin_password.py`.

## Publications / SerpAPI

| Variable | Purpose |
|----------|---------|
| **`SERP_API_KEYS`** | **Preferred.** Comma-separated list of SerpAPI keys; the scraper rotates keys as each hits its monthly budget |
| `SERP_API_KEY` | Single-key fallback — used only when `SERP_API_KEYS` is empty |
| `SCRAPER_BACKEND` | `serpapi` (Docker / production path) or `scholarly` (local browser scrape) |
| `ENABLE_SCHEDULER` | Periodic publication scrape jobs |
| `DATA_ASSETS` | Absolute path to CSV/Excel assets (default `data/assets`) |

### SerpAPI keys {#serpapi-keys}

Google Scholar scraping uses [SerpAPI](https://serpapi.com/).

1. Create an account at [https://serpapi.com/](https://serpapi.com/) and open the dashboard to copy your API key.
2. Free plan: **250 searches per month**, resets monthly. One key is often enough for light use; for department-wide syncs, register **3–4 accounts** and list all keys.
3. Set the variable in the env file you actually run with:
   - Docker: `.env.docker`
   - Native: `backend/.env`

```env
SCRAPER_BACKEND=serpapi
# Prefer this (rotation):
SERP_API_KEYS=key_from_account_1,key_from_account_2,key_from_account_3
SERP_API_KEY=
```

Or a single key:

```env
SCRAPER_BACKEND=serpapi
SERP_API_KEYS=
SERP_API_KEY=your_single_key
```

Do **not** put SerpAPI keys in `ops/backup/bac.env` or `ops/backup/db.env`.

## Which env file? (production / Docker)

| Env file | Used by | What to change |
|----------|---------|----------------|
| `.env.docker` | `docker compose --env-file .env.docker` | DB passwords, `SECRET_KEY`, bootstrap admin, URLs, `SERP_API_KEYS`, SMTP |
| `ops/backup/bac.env` | Backup compose | `RESTIC_PASSWORD`, `BACKUP_TARGET_PATH`, schedule |
| `ops/backup/db.env` | Backup compose (via `env_file`) | MySQL passwords matching `.env.docker` |
| `backend/.env` | Native uvicorn / PM2 | Same app secrets as `.env.docker`, plus local MySQL host/port |

## Local LLM (Ollama)

| Variable | Purpose |
|----------|---------|
| `LOCAL_LLM_BASE_URL` | Default `http://localhost:11434/v1` (host) or `https://ollama-proxy:8443/v1` (compose mTLS) |
| `LOCAL_LLM_MODEL` | Default `llama3.2:3b` |
| `LOCAL_LLM_WARMUP_ON_STARTUP` | Prefetch model weights |
| `LOCAL_LLM_MTLS_ENABLED` | Use client certs when talking to `ollama-proxy` |
| `LOCAL_LLM_MTLS_CA_FILE` | CA that signed the proxy cert (default `/certs/mtls/ca.crt`) |
| `LOCAL_LLM_MTLS_CERT_FILE` | Backend client certificate |
| `LOCAL_LLM_MTLS_KEY_FILE` | Backend client private key |

## Security hardening

| Variable | Purpose |
|----------|---------|
| `BLOCK_AUTOMATION_AGENTS` | Reject curl/wget/postman/etc. on `/api/*` (default true) |
| `RATE_LIMIT_ENABLED` | Per-IP API rate limits |
| `LOGIN_MAX_ATTEMPTS` / `LOGIN_WINDOW_SECONDS` | Login brute-force window |

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
