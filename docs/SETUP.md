# Full setup guide (Windows + Linux)

End-to-end instructions for a lab engineer to clone, configure, and run the
ECE Department Smart Portal. Prefer **Docker** for institute servers.

Related docs: [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) ·
[SERVER_SETUP.md](SERVER_SETUP.md) · [BACKUP_RESTORE.md](BACKUP_RESTORE.md) ·
[CONFIGURATION.md](CONFIGURATION.md) · [SECURITY.md](SECURITY.md)

---

## What you need

| Requirement | Notes |
|-------------|-------|
| Git | Clone the repository |
| Docker Engine 24+ + Compose v2 | Production / shared server path |
| (Optional) Python 3.11, Node 20, MySQL 8 | Native local development only |
| (Optional) Ollama | LLM insights / minutes Q&A |
| Out-of-band files | `.env.docker`, `data/assets/` (not in Git) |

---

## A. Docker full stack (recommended)

### A1. Clone

**Linux / macOS / WSL**

```bash
cd ~
git clone <REPO_URL> ece-portal
cd ece-portal
```

**Windows (PowerShell)**

```powershell
cd $env:USERPROFILE\Desktop
git clone <REPO_URL> ece-portal
cd ece-portal
```

### A2. Secrets and assets

```bash
cp .env.docker.example .env.docker
# Edit .env.docker — see “Variables you must change” below
```

Generate a strong secret:

```bash
# Linux / macOS / Git Bash
openssl rand -hex 32

# Windows PowerShell
-join ((1..64) | ForEach-Object { '{0:x}' -f (Get-Random -Max 16) })
```

Copy department CSV/Excel into `data/assets/` (see [DATA_ASSETS.md](DATA_ASSETS.md)).
These files are **not** in Git.

#### Variables you must change in `.env.docker`

| Variable | Action |
|----------|--------|
| `MYSQL_ROOT_PASSWORD` | Replace placeholder with a strong password |
| `MYSQL_PASSWORD` | Replace placeholder (portal DB user) |
| `SECRET_KEY` | Paste output of `openssl rand -hex 32` |
| `BOOTSTRAP_ADMIN_EMAIL` | Default `admin@ece.iiitd.ac.in` (change if desired) |
| `BOOTSTRAP_ADMIN_PASSWORD` | Default `ChangeMeOnFirstLogin!` — change after first login |
| `PORTAL_FRONTEND_URL` | Public URL users open (e.g. `http://SERVER_IP:8080` or HTTPS domain) |
| `CORS_ORIGINS` | Same origin(s) as the frontend URL (comma-separated if multiple) |
| `SERP_API_KEYS` | Comma-separated SerpAPI keys for Google Scholar scraping (see below) |
| `SCRAPER_BACKEND` | Keep `serpapi` for Docker |

Optional but recommended for production: enable SMTP (`SMTP_ENABLED=true` + credentials) for password-reset and reminder emails.

#### How to get SerpAPI keys

1. Register at [https://serpapi.com/](https://serpapi.com/) (free tier: **250 searches/month**, resets monthly).
2. Copy the API key from the dashboard.
3. Create **3–4 free accounts/keys** if you scrape often — the portal rotates keys when one hits quota.
4. Set in `.env.docker`:

```env
SCRAPER_BACKEND=serpapi
# Preferred — rotation across multiple keys:
SERP_API_KEYS=your_key_1,your_key_2,your_key_3
# Leave SERP_API_KEY empty when using SERP_API_KEYS.
SERP_API_KEY=
```

If `SERP_API_KEYS` is empty, the app falls back to a single `SERP_API_KEY`.  
Full reference: [CONFIGURATION.md](CONFIGURATION.md#serpapi-keys).

### A3. Start the portal (app compose)

```bash
docker compose --env-file .env.docker up -d --build
```

**Windows:** same command in PowerShell from the repo root.

Open `http://localhost:8080` (or `PORTAL_HTTP_PORT` / the server hostname).

Default bootstrap admin (first API start only, if no admin exists yet):

```env
BOOTSTRAP_ADMIN_EMAIL=admin@ece.iiitd.ac.in
BOOTSTRAP_ADMIN_PASSWORD=ChangeMeOnFirstLogin!
```

**Change the password immediately after first login.** Use the eye icon on the login form to show/hide the password while typing.

### A4. Ollama (separate compose) — required for full handoff

Ollama runs in `docker-compose.ollama.yml`, not in the main app compose.
Backend talks to it over the shared Docker network with **mTLS** (client
certificate). Use this on the testing server and the institute server.

```bash
# 1) Certs once (gitignored — must exist on each machine)
./scripts/generate_mtls_certs.sh          # Linux / macOS / Git Bash
# .\scripts\generate_mtls_certs.ps1       # Windows PowerShell

# 2) Start LLM stack
docker compose -f docker-compose.ollama.yml up -d

# 3) Pull model inside the container (~2 GB; first time only)
docker compose -f docker-compose.ollama.yml exec ollama ollama pull llama3.2:3b

# 4) Edit .env.docker (see “Exact .env.docker edits” below), then:
docker compose --env-file .env.docker up -d --build
```

Verify:

```bash
docker compose --env-file .env.docker exec backend python -c \
  "from app.llm.services.local_service import local_available; print(local_available())"
# Expect: (True, 'Ready (model: llama3.2:3b, ...)')
```

### A4b. What “TLS” means (browser HTTPS vs mTLS)

| Term | What it protects | Needed now? |
|------|------------------|-------------|
| **mTLS (backend ↔ Ollama)** | LLM API between containers; client cert required | **Yes** — section A4 |
| **TLS / HTTPS (browser ↔ portal)** | Encrypts the site users open (browser padlock) | **Not required** on testing while using `http://…:8080`. On institute, IT usually terminates HTTPS on a reverse proxy. Optional self-signed portal certs: `scripts/generate_self_signed_cert.sh` + `frontend/nginx.ssl.conf`. |

For handoff on the testing box: finish **mTLS + Ollama compose**. Leave browser HTTPS to institute IT unless they ask you to enable `nginx.ssl.conf`.

### Exact `.env.docker` edits (gitignored — do on every server)

Keep existing `MYSQL_*`, `SECRET_KEY`, and bootstrap passwords. Change/add:

```env
PORTAL_FRONTEND_URL=http://localhost:8080
CORS_ORIGINS=http://localhost:8080
# Institute later: both become https://your-real-host.example.edu

PORTAL_HTTP_PORT=8080

LOCAL_LLM_BASE_URL=https://ollama-proxy:8443/v1
LOCAL_LLM_MTLS_ENABLED=true
LOCAL_LLM_MTLS_CA_FILE=/certs/mtls/ca.crt
LOCAL_LLM_MTLS_CERT_FILE=/certs/mtls/client.crt
LOCAL_LLM_MTLS_KEY_FILE=/certs/mtls/client.key
LOCAL_LLM_MODEL=llama3.2:3b
LOCAL_LLM_NUM_GPU=-1
LOCAL_LLM_WARMUP_ON_STARTUP=true

EMBEDDING_DEVICE=cpu
```

Stop using the old host-Ollama settings with the compose stack:

```env
# OLD — do not use with docker-compose.ollama.yml:
# LOCAL_LLM_BASE_URL=http://host.docker.internal:11434/v1
# LOCAL_LLM_MTLS_ENABLED=false
```

`certs/mtls/*` are **not** in Git — generate on each machine.

### Commands after `git pull`

```bash
git pull
./scripts/generate_mtls_certs.sh   # or .\scripts\generate_mtls_certs.ps1 (skip if certs exist)
# Edit .env.docker as above

docker compose --env-file .env.docker up -d --build
docker compose -f docker-compose.ollama.yml up -d
docker compose -f docker-compose.ollama.yml exec ollama ollama pull llama3.2:3b
```

### A5. Encrypted backups (restic)

See [BACKUP_RESTORE.md](BACKUP_RESTORE.md). Quick start:

```bash
cd ops/backup
cp bac.env.example bac.env
cp db.env.example db.env
```

**Edit these two files (not `.env.docker`):**

| File | Variables to set |
|------|------------------|
| `bac.env` | `RESTIC_PASSWORD` (long random — store offline), `BACKUP_TARGET_PATH` (durable disk/NAS), optionally `BACKUP_START_TIME` / `BACKUP_INTERVAL_DAYS` |
| `db.env` | `MYSQL_PASSWORD` and `MYSQL_ROOT_PASSWORD` — **must match** the same values in `.env.docker` |

Then:

```bash
docker compose -f docker-compose.backup.yml --env-file bac.env up -d --build
```

First start runs an **immediate** backup, then daily runs **automatically**.
Admin only acts again for restore after a crash.

### A6. Useful Docker commands

```bash
docker compose --env-file .env.docker ps
docker compose --env-file .env.docker logs -f backend
docker compose --env-file .env.docker exec backend alembic upgrade head
docker compose --env-file .env.docker down
docker compose -f docker-compose.ollama.yml ps
docker compose -f docker-compose.ollama.yml logs -f ollama
```

---

## B. Native development (optional)

### B1. MySQL

Install MySQL 8 on port **3306**. Copy `backend/.env.example` → `backend/.env`,
set `MYSQL_*`, then:

```bash
# optional bootstrap
mysql -u root -p < data/sql/local_mysql_bootstrap.sql
```

Details: [LOCAL_DATABASE.md](LOCAL_DATABASE.md).

### B2. Backend

**Linux / macOS**

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

**Windows (PowerShell)**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

### B3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 (Vite proxies API to port 8001).

---

## C. Verify the install

1. `GET /health` → `{"status":"ok",...}`
2. Admin login works; change bootstrap password
3. Faculty directory / one CO-PO page loads
4. (If Ollama configured) LLM Insights status shows the model as reachable
5. (If backup running) `ops/backup` logs show snapshot creation; see verification
   checklist in [BACKUP_RESTORE.md](BACKUP_RESTORE.md)

---

## D. Files that are never in Git

| Path | How to obtain |
|------|----------------|
| `.env.docker` / `backend/.env` | Copy from `*.example`, fill secrets |
| `data/assets/*` | Secure copy / restore from backup |
| `backend/documents/**/*.pdf` | Secure copy / restore from backup |
| `backend/storage/` | Runtime uploads; restore from backup |
| `certs/mtls/*` | `scripts/generate_mtls_certs.*` |
| `ops/backup/bac.env`, `db.env` | Copy from examples |
| `backup-data/` | Created by restic on first backup |

---

## E. After a crash / fresh machine

1. Clone repo + restore `.env.docker` and certs from secure offline storage
2. Restore files + DB using [BACKUP_RESTORE.md](BACKUP_RESTORE.md)
3. `docker compose --env-file .env.docker up -d --build`
4. Start Ollama (host or `docker-compose.ollama.yml`)
5. Re-enable backup service
