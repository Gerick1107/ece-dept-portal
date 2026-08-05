# Backup and restore (restic)

The portal uses **restic** for encrypted, incremental backups of:

| What | Restic repo under `BACKUP_TARGET_PATH` |
|------|----------------------------------------|
| `backend/storage/` | `storage/` |
| `backend/documents/` | `documents/` |
| `data/assets/` | `assets/` |
| `data/templates/` | `templates/` |
| MySQL logical dump (`mysqldump`) | `mysql/` |

Snapshots are AES-encrypted with `RESTIC_PASSWORD`. Without that password,
backups cannot be restored.

Implementation lives in `ops/backup/` (Dockerfile, loop script, restore script,
Compose file). The temporary `backup/` folder at the repo root (if present) is
reference-only and is gitignored — do not rely on it.

---

## 1. One-time setup

```bash
cd ops/backup
cp bac.env.example bac.env
cp db.env.example db.env
```

You edit **two** env files here (in addition to the app’s `.env.docker` at the repo root).

### What to change in each file

| File | Variables you must set | Notes |
|------|------------------------|--------|
| **`bac.env`** | `RESTIC_PASSWORD` | Long random secret (`openssl rand -base64 48`). **Store offline** — without it you cannot restore. |
| **`bac.env`** | `BACKUP_TARGET_PATH` | Durable host path (NAS / large disk). Linux: `/mnt/nas/ece-portal/backup`. Windows: `C:\ece-portal-backup`. |
| **`bac.env`** | `BACKUP_START_TIME`, `BACKUP_INTERVAL_DAYS` | Optional schedule (default `13:00` daily) |
| **`db.env`** | `MYSQL_PASSWORD` | **Must match** `MYSQL_PASSWORD` in `.env.docker` |
| **`db.env`** | `MYSQL_ROOT_PASSWORD` | **Must match** `MYSQL_ROOT_PASSWORD` in `.env.docker` |
| **`db.env`** | `MYSQL_USER`, `MYSQL_DATABASE` | Usually leave as in the example (`portal_user` / `ece_dept_portal`) |

Do **not** put SerpAPI keys or `SECRET_KEY` in these backup files — those belong only in `.env.docker` / `backend/.env`.

The backup container joins Docker networks `portal-app` (to reach MySQL) and
`portal-shared`. Start the **main portal stack first** so those networks exist.

### Start the backup service

**Linux / macOS / Git Bash**

```bash
cd ops/backup
docker compose -f docker-compose.backup.yml --env-file bac.env up -d --build
docker compose -f docker-compose.backup.yml logs -f backup
```

**Windows (PowerShell)**

```powershell
cd ops\backup
docker compose -f docker-compose.backup.yml --env-file bac.env up -d --build
docker compose -f docker-compose.backup.yml logs -f backup
```

On first start the service runs an **immediate initial backup**, then waits for
the scheduled window.

---

## 2. How to know it is working

| Check | Expected |
|-------|----------|
| Container running | `docker ps` shows `ece-portal-backup` |
| Logs | `Initializing encrypted restic repository` then `Completed backup for storage/documents/assets/templates/mysql-logical` |
| Activity CSV | `$BACKUP_TARGET_PATH/logs/backup_activity.csv` gains a row each cycle |
| Snapshots exist | See commands below |
| Repos on disk | `$BACKUP_TARGET_PATH/{storage,documents,assets,templates,mysql}/` contain restic data |

List snapshots (example for storage):

```bash
docker run --rm --env-file ops/backup/bac.env \
  -v "${BACKUP_TARGET_PATH}:/backup-root:ro" \
  restic/restic:0.18.1 \
  -r /backup-root/storage snapshots
```

PowerShell: set `$env:BACKUP_TARGET_PATH` first, or substitute the path literally.

A healthy install has **at least one snapshot** in `storage` and `mysql` after
the initial cycle.

---

## 3. Restore after a crash (pick a version)

> Stop the portal stack before overwriting live data, or restore onto a fresh
> machine / empty directories.

### Recommended: interactive version picker

Lists the newest backups **5 at a time** with date/time. Enter `1`–`5` to
choose, `n` for older pages, `p` for newer, `q` to quit. Confirms before
restoring.

```bash
cd ops/backup
chmod +x interactive_restore.sh   # once
./interactive_restore.sh --force
```

What it does:

1. Reads snapshot times from the **storage** restic repo (each backup cycle)
2. Lets you pick a version by number
3. Restores **storage / documents / assets / templates / MySQL** to the
   snapshots closest to that time (`--as-of`)
4. Writes `ops/backup/restored_<db>.sql` for MySQL import

Then import MySQL into the live container:

```bash
# from repo root, with portal mysql running
docker compose --env-file .env.docker exec -T mysql \
  mysql -u root -p"$MYSQL_ROOT_PASSWORD" < ops/backup/restored_ece_dept_portal.sql

docker compose --env-file .env.docker exec backend alembic upgrade head
```

### Non-interactive (always latest)

```bash
cd ops/backup
sh restore_from_backup.sh \
  --base-dir ../../backend/storage \
  --documents-dir ../../backend/documents \
  --assets-dir ../../data/assets \
  --templates-dir ../../data/templates \
  --force
```

Or restore a known timestamp:

```bash
sh restore_from_backup.sh \
  --base-dir ../../backend/storage \
  --documents-dir ../../backend/documents \
  --assets-dir ../../data/assets \
  --templates-dir ../../data/templates \
  --as-of "2026-07-29T16:24:28.000000000Z" \
  --force
```

### After restore — verify

1. `/health` returns ok
2. Admin login works
3. Faculty directory counts look sane
4. Spot-check one CO-PO result, one project, one allocation semester
5. Open a meeting minutes document that has an attachment

---

## 4. Manual mysqldump (without restic)

Still useful for quick one-off dumps:

```bash
docker compose --env-file .env.docker exec -T mysql \
  mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines --triggers \
  ece_dept_portal > ece_portal_$(date +%F).sql
```

Restore:

```bash
docker compose --env-file .env.docker exec -T mysql \
  mysql -u root -p"$MYSQL_ROOT_PASSWORD" ece_dept_portal < ece_portal_YYYY-MM-DD.sql
docker compose --env-file .env.docker exec backend alembic upgrade head
```

---

## 5. Operational notes

- **Never commit** `bac.env`, `db.env`, `RESTIC_PASSWORD`, or `backup-data/`.
- Keep a **printed / offline copy** of `RESTIC_PASSWORD`. Loss = unrecoverable backups.
- The MySQL Docker **named volume** (`mysql_data`) is covered via logical dumps,
  not by copying the volume files directly.
- `hf_cache` (embedding models) is optional to back up; models re-download on demand.
- Env files (`.env.docker`) should be backed up **offline**, not inside the restic
  repo on the same disk if you can avoid it.

---

## 6. Troubleshooting

| Symptom | Fix |
|---------|-----|
| Cannot connect to MySQL | Ensure main compose is up; backup joins `portal-app`; `MYSQL_HOST=mysql` |
| Network not found | `docker compose --env-file .env.docker up -d` first (creates `portal-app` / `portal-shared`) |
| Wrong password | Align `ops/backup/db.env` with `.env.docker` |
| No snapshots after hours | Check logs; confirm initial cycle finished; clock / `BACKUP_START_TIME` |
| Restore refuses non-empty dirs | Pass `--force` (destructive) |
