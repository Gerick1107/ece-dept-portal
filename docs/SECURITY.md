# Security (OWASP-aligned)

This document summarizes how the ECE Department Smart Portal addresses common OWASP Top 10 risks. Use it for internal review and IT validation.

## Authentication & access control

| Control | Implementation |
|---------|----------------|
| Password hashing | bcrypt via passlib (`auth/service.py`) |
| Session tokens | JWT (HS256), short-ish TTL (`ACCESS_TOKEN_EXPIRE_MINUTES`) |
| Role-based access | `admin`, `hod`, `faculty` enforced with `require_roles()` on sensitive routes |
| Forced password change | `must_change_password` flag on bootstrap / reset |
| Login brute-force | App: 10 attempts / 5 min / IP; nginx edge: `10r/m` on login routes (`limit_req_status 429`) |

## Injection

| Control | Implementation |
|---------|----------------|
| SQL injection | SQLAlchemy ORM + parameterized queries; no raw SQL from user input |
| Command injection | No shell execution of user-provided strings |
| Email validation | Login rejects malformed / injection-like email strings (422) |

## Cryptographic failures

| Control | Implementation |
|---------|----------------|
| Secrets in env | `SECRET_KEY`, DB passwords, API keys via `.env` / `.env.docker` — never committed |
| Production guard | App refuses to start in production with default `SECRET_KEY` |
| TLS | Required at reverse proxy in production (see DOCKER_DEPLOYMENT.md) |
| Backup encryption | Restic AES repositories (`RESTIC_PASSWORD`) — see BACKUP_RESTORE.md |
| Backend ↔ Ollama | Optional **mTLS** via nginx proxy (`docker-compose.ollama.yml`) |

## Insecure design

| Control | Implementation |
|---------|----------------|
| Admin-only mutations | Uploads, user management, requirement tracker, catalog edits |
| Faculty data scope | Users see only permitted modules; notifications scoped per user |
| Department CSVs | `data/assets/` gitignored — not published on GitHub |
| File uploads | PDF-only for minutes; reply attachments ≤ 10 MB; sanitized filenames |
| Notification replies | Faculty can attach files; downloads scoped to recipient or admin |

## Security misconfiguration

| Control | Implementation |
|---------|----------------|
| Security headers | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`; HSTS + CSP in production API |
| API docs | Swagger/OpenAPI disabled when `APP_ENV=production` |
| CORS | Explicit allow-list via `CORS_ORIGINS` (not `*` in production) |
| Debug mode | `DEBUG=false` in production compose |
| Automation clients | `BlockedUserAgentMiddleware` rejects curl/wget/postman/etc. on `/api/*` |
| MySQL bind | Published only as `127.0.0.1:3307` (not on the public interface) |

## Vulnerable components

| Control | Implementation |
|---------|----------------|
| Pinned dependencies | `backend/requirements.txt`, `frontend/package-lock.json` |
| Docker images | Pinned base images (`python:3.11-slim-bookworm`, `nginx:1.27-alpine`, `mysql:8.0`) |

## Identification & authentication failures

| Control | Implementation |
|---------|----------------|
| No user enumeration on forgot-password | Generic success message |
| JWT in `Authorization` header | Not in cookies (CSRF not applicable to bearer API) |
| `alg=none` / garbage JWT | Rejected as invalid token (401) |

## Software & data integrity

| Control | Implementation |
|---------|----------------|
| Git + tagged releases | Deploy known commits |
| Migrations | Alembic versioned schema changes |

## Logging & monitoring

| Control | Implementation |
|---------|----------------|
| Server logs | Uvicorn/gunicorn stdout; institute SIEM can ingest |
| Failed login | 401 then edge/app rate limit (429) |

## SSRF / XXE

| Control | Implementation |
|---------|----------------|
| External fetches | Limited to configured APIs (SMTP, publication scraping); LLM runs locally (Ollama); no user-controlled URLs in server-side fetch |

---

## Blackbox probes run against localhost (Docker)

These were run against `http://localhost:8080` with the production Docker stack.
Use a **browser-like User-Agent** for API checks that should succeed; use `curl`
to verify automation blocking.

Browser UA used:

```text
Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36
```

### PowerShell (Windows)

```powershell
$base = 'http://localhost:8080'
$UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'

# 1. Health / liveness
Invoke-WebRequest "$base/health" -UserAgent $UA -UseBasicParsing
# Aim: confirm stack is up. Expect 200 {"status":"ok",...}

# 2. Security headers on UI
(Invoke-WebRequest "$base/" -UserAgent $UA -UseBasicParsing).Headers
# Aim: X-Content-Type-Options=nosniff, X-Frame-Options=DENY, Referrer-Policy set

# 3. Block automation User-Agents on API
Invoke-WebRequest "$base/api/v1/auth/me" -UserAgent 'curl/8.0' -UseBasicParsing
# Aim: 403 Forbidden client

# 4. Unauthenticated access to protected routes
Invoke-WebRequest "$base/api/v1/auth/me" -UserAgent $UA -UseBasicParsing
Invoke-WebRequest "$base/api/v1/auth/users" -UserAgent $UA -UseBasicParsing
# Aim: 401 Not authenticated

# 5. Swagger / OpenAPI disabled in production
Invoke-WebRequest "$base/api/docs" -UserAgent $UA -UseBasicParsing
Invoke-WebRequest "$base/api/openapi.json" -UserAgent $UA -UseBasicParsing
# Aim: 404 (not exposed). Note: /$path may serve the SPA shell — that is not Swagger.

# 6. SQL injection via login email
$body = '{"email":"admin@ece.iiitd.ac.in'' OR 1=1--","password":"x"}'
Invoke-WebRequest "$base/api/v1/auth/login/json" -Method POST -UserAgent $UA -ContentType 'application/json' -Body $body -UseBasicParsing
# Aim: 422 validation error — no session

# 7. JWT alg=none / forged token
Invoke-WebRequest "$base/api/v1/auth/me" -UserAgent $UA -Headers @{ Authorization = 'Bearer eyJhbGciOiJub25lIn0.eyJzdWIiOiIxIn0.' } -UseBasicParsing
# Aim: 401 Invalid token

# 8. CORS reflection
Invoke-WebRequest "$base/api/v1/auth/me" -UserAgent $UA -Headers @{ Origin = 'https://evil.example' } -UseBasicParsing
# Aim: no Access-Control-Allow-Origin: https://evil.example

# 9. Forgot-password user enumeration
Invoke-WebRequest "$base/api/v1/auth/forgot-password" -Method POST -UserAgent $UA -ContentType 'application/json' -Body '{"email":"nosuchuser@example.com"}' -UseBasicParsing
# Aim: generic success message (no "user not found")

# 10. Login brute-force / rate limit
1..15 | ForEach-Object {
  try {
    (Invoke-WebRequest "$base/api/v1/auth/login/json" -Method POST -UserAgent $UA -ContentType 'application/json' -Body '{"email":"admin@ece.iiitd.ac.in","password":"WrongPass!!!"}' -UseBasicParsing).StatusCode
  } catch { $_.Exception.Response.StatusCode.value__ }
}
# Aim: 401s then 429 from nginx/app rate limits

# 11. Path traversal via static URL
Invoke-WebRequest "$base/../../etc/passwd" -UserAgent $UA -UseBasicParsing
# Aim: SPA HTML only — never /etc/passwd contents

# 12. MySQL not on public interface
Test-NetConnection 127.0.0.1 -Port 3307   # may be open locally (Docker bind)
# Aim: 3306/3307 not exposed on 0.0.0.0 to the LAN (compose uses 127.0.0.1:3307)
```

### curl (Linux)

```bash
BASE=http://localhost:8080
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36'

curl -sS "$BASE/health"
curl -sSI "$BASE/" | grep -iE 'x-content-type|x-frame|referrer'
curl -sS -A curl/8.0 -o /dev/null -w '%{http_code}\n' "$BASE/api/v1/auth/me"   # expect 403
curl -sS -A "$UA" -o /dev/null -w '%{http_code}\n' "$BASE/api/v1/auth/me"      # expect 401
curl -sS -A "$UA" -o /dev/null -w '%{http_code}\n' "$BASE/api/docs"            # expect 404
curl -sS -A "$UA" -H 'Authorization: Bearer eyJhbGciOiJub25lIn0.eyJzdWIiOiIxIn0.' \
  -o /dev/null -w '%{http_code}\n' "$BASE/api/v1/auth/me"                       # expect 401
```

### Results summary (Jul 2026 localhost Docker)

| Probe | Result |
|-------|--------|
| Health | 200 ok, `env=production` |
| curl / empty UA on API | 403 Forbidden client |
| `/auth/me` & `/auth/users` unauthenticated | 401 |
| `/api/docs`, `/api/openapi.json` | 404 |
| SQLi login email | 422 (rejected) |
| JWT `alg=none` | 401 Invalid token |
| Evil CORS origin | Not reflected |
| Forgot-password | Generic message |
| Login flood | 401 then rate-limited |
| Path traversal | SPA only (no file leak) |
| MySQL | Bound to `127.0.0.1:3307` |
| UI security headers | Fixed in nginx (repeat headers on `index.html` / assets locations) |

---

## Pre-IT review checklist

- [ ] `SECRET_KEY` rotated; not default
- [ ] Bootstrap admin password changed after first login
- [ ] HTTPS enabled on public URL
- [ ] `CORS_ORIGINS` matches production origin only
- [ ] MySQL not exposed publicly
- [ ] `.env` / `.env.docker` file permissions restricted on server
- [ ] SMTP credentials secured if email enabled
- [ ] Restic `RESTIC_PASSWORD` stored offline; backups verified
- [ ] If using containerized Ollama: mTLS certs generated; proxy up
- [ ] Regular `docker compose pull` / image rebuilds for security patches

## Reporting issues

Report security concerns to the ECE department portal maintainers and institute IT before public disclosure.
