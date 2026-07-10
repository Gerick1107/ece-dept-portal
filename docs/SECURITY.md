# Security (OWASP-aligned)

This document summarizes how the ECE Automation Portal addresses common OWASP Top 10 risks. Use it for internal review and IT validation.

## Authentication & access control

| Control | Implementation |
|---------|----------------|
| Password hashing | bcrypt via passlib (`auth/service.py`) |
| Session tokens | JWT (HS256), short-ish TTL (`ACCESS_TOKEN_EXPIRE_MINUTES`) |
| Role-based access | `admin`, `hod`, `faculty` enforced with `require_roles()` on sensitive routes |
| Forced password change | `must_change_password` flag on bootstrap / reset |
| Login brute-force | Rate limit on `/auth/login/json` (20 attempts / 5 min / IP) |

## Injection

| Control | Implementation |
|---------|----------------|
| SQL injection | SQLAlchemy ORM + parameterized queries; no raw SQL from user input |
| Command injection | No shell execution of user-provided strings |

## Cryptographic failures

| Control | Implementation |
|---------|----------------|
| Secrets in env | `SECRET_KEY`, DB passwords, API keys via `.env` / `.env.docker` — never committed |
| Production guard | App refuses to start in production with default `SECRET_KEY` |
| TLS | Required at reverse proxy in production (see DOCKER_DEPLOYMENT.md) |

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
| Security headers | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, HSTS in production |
| API docs | Swagger/OpenAPI disabled when `APP_ENV=production` |
| CORS | Explicit allow-list via `CORS_ORIGINS` (not `*` in production) |
| Debug mode | `DEBUG=false` in production compose |

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

## Software & data integrity

| Control | Implementation |
|---------|----------------|
| Git + tagged releases | Deploy known commits |
| Migrations | Alembic versioned schema changes |

## Logging & monitoring

| Control | Implementation |
|---------|----------------|
| Server logs | Uvicorn/gunicorn stdout; institute SIEM can ingest |
| Failed login | 429 responses on rate limit |

## SSRF / XXE

| Control | Implementation |
|---------|----------------|
| External fetches | Limited to configured APIs (SMTP, publication scraping); LLM runs locally (Ollama); no user-controlled URLs in server-side fetch |

## Pre-IT review checklist

- [ ] `SECRET_KEY` rotated; not default
- [ ] Bootstrap admin password changed after first login
- [ ] HTTPS enabled on public URL
- [ ] `CORS_ORIGINS` matches production origin only
- [ ] MySQL not exposed publicly
- [ ] `.env` / `.env.docker` file permissions restricted on server
- [ ] SMTP credentials secured if email enabled
- [ ] Regular `docker compose pull` / image rebuilds for security patches

## Reporting issues

Report security concerns to the ECE department portal maintainers and institute IT before public disclosure.
