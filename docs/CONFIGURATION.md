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
| `LOCAL_LLM_BASE_URL` | OpenAI-compatible base URL ending in `/v1`. Compose mTLS: `https://ollama-proxy:8443/v1`. Host Ollama: `http://host.docker.internal:11434/v1`. **Remote server:** `http://OTHER_HOST:11434/v1` (or that host’s HTTPS proxy URL). |
| `LOCAL_LLM_MODEL` | Model tag Ollama must have pulled (default `llama3.2:3b`). UI warnings name **this** value — change it here to use a stronger model. |
| `LOCAL_LLM_WARMUP_ON_STARTUP` | Prefetch model weights on backend start |
| `LOCAL_LLM_MTLS_ENABLED` | `true` when talking to `ollama-proxy`; `false` for plain HTTP (host or remote) |
| `LOCAL_LLM_MTLS_CA_FILE` | CA that signed the proxy cert (default `/certs/mtls/ca.crt`) |
| `LOCAL_LLM_MTLS_CERT_FILE` | Backend client certificate |
| `LOCAL_LLM_MTLS_KEY_FILE` | Backend client private key |

### Which model name appears in warnings?

The portal does **not** hard-code a display model. Availability checks and error text use `LOCAL_LLM_MODEL` from `.env.docker` / `backend/.env`. If you see `llama3.2:3b` or `llama3:latest`, that string is whatever is set in that env file on that server.

### Remote Ollama (another machine)

Skip `docker-compose.ollama.yml` on the portal host. On the Ollama machine, install/run Ollama and pull your model. In the portal `.env.docker`:

```env
LOCAL_LLM_BASE_URL=http://192.168.x.y:11434/v1
LOCAL_LLM_MTLS_ENABLED=false
LOCAL_LLM_MODEL=llama3.2:3b
```

Use the real host/IP (or DNS) and ensure the portal backend container can reach that port (firewall / routing). If the remote side terminates TLS + client certs, point `LOCAL_LLM_BASE_URL` at that proxy and set the `LOCAL_LLM_MTLS_*` paths accordingly.

### Compose Ollama auto-pull

`docker compose -f docker-compose.ollama.yml --env-file .env.docker up -d` starts `ollama-pull`, which downloads `LOCAL_LLM_MODEL` automatically (no manual `ollama pull` required). First pull can take several minutes.

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
