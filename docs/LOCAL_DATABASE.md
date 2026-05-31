# Local database (Windows MySQL — no Docker)

## Summary

| Item | Local Windows dev | Old Docker setup |
|------|-------------------|------------------|
| Host | `127.0.0.1` | `127.0.0.1` |
| Port | **3306** | **3307** (host map) |
| Service | MySQL80 (Windows) | `docker compose` container |
| Config | `backend/.env` → `MYSQL_*` | same |

The backend assembles `DATABASE_URL` from `MYSQL_*` in `backend/.env` (passwords with `@` or `#` work without URL encoding).

## One-time setup

### 1. Stop Docker MySQL (optional, avoid port conflicts)

```powershell
docker compose down
docker rm -f nportal-mysql-1 poa-16may-mysql-1 2>$null
```

Docker is **not** required for daily development.

### 2. Start Windows MySQL

- **Services** → start **MySQL80** (or your installed service)
- Or MySQL Workbench → `localhost:3306` as `root`

### 3. Create database and user (optional)

Run as **root** in Workbench:

`data/sql/local_mysql_bootstrap.sql`

Creates `ece_dept_portal` and `portal_user` / `portal_pass`.

**Alternative:** use root in `.env`:

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=ece_dept_portal
```

### 4. Configure `backend/.env`

Copy from `backend/.env.example`. Never commit `.env` to Git.

### 5. Migrations

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
```

Current head includes migration **005** (`users.profile_removed` for account removal).

### 6. Verify

```powershell
python scripts/verify_db.py
```

### 7. Bootstrap admin

On first API start, admin is created from `BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD` if missing.

To reset admin password manually:

```powershell
python scripts/reset_admin_password.py
```

## Importing existing data

If migrating from Docker (port 3307) or another machine:

1. Export `ece_dept_portal` from the old instance (Workbench → Data Export).
2. Import into local MySQL on port 3306.
3. Run `alembic upgrade head` to apply any new migrations.

## Production

Set `MYSQL_*` or `DATABASE_URL` on the server `.env`. Run `alembic upgrade head` on each deploy.

## Related

- [USER_MANAGEMENT.md](USER_MANAGEMENT.md)
- [STORAGE.md](STORAGE.md)
