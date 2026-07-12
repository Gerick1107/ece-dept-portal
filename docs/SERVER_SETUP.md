# Deploying the ECE Portal on the institute server

This is a step-by-step runbook for putting the portal on the server you were given
(**IP address + username + password**, with Docker access). It covers:

1. Connecting to the server from VS Code (Remote-SSH)
2. Getting the code onto the server (`git clone` / `git pull`)
3. The files you must copy over **manually** (they are not in Git)
4. Bringing the stack up with Docker
5. Giving `admin-ece` admin access
6. What your collaborator does to work the same way

> Throughout, replace `SERVER_IP`, `USERNAME`, and paths with your real values.
> The shell examples are for the server (Linux). Run the "from your laptop"
> commands in PowerShell on Windows.

---



## Part 0 — What "SSH extension + add server + git pull" means

Your contact was describing the normal workflow:

- **SSH extension** = the **Remote - SSH** extension for VS Code / Cursor. It lets
you open a folder *on the server* and edit/run things there as if it were local.
- **Add server** = save an SSH host entry so you can reconnect with one click.
- **git pull** = the code lives in a Git repo; on the server you `git clone` once,
then `git pull` each time to get new changes. You do **not** copy the whole
project by hand — only the few files Git intentionally does not track (Part 3).

---



## Part 1 — Connect to the server from VS Code / Cursor (Remote-SSH)

1. Install the **Remote - SSH** extension (Extensions panel → search "Remote - SSH").
2. Press `F1` → **Remote-SSH: Add New SSH Host…**
3. Enter:
  ```
   ssh USERNAME@SERVER_IP
  ```
   Choose to save it in your user SSH config (`C:\Users\<you>\.ssh\config`).
4. Press `F1` → **Remote-SSH: Connect to Host…** → pick the server → enter the
  password when prompted.
5. Once connected (bottom-left shows `SSH: SERVER_IP`), open a terminal
  (`Ctrl+``). You are now on the server.

**Tip (password-less login, optional but recommended):** from your laptop
PowerShell:

```powershell
ssh-keygen -t ed25519            # press Enter through the prompts if you have no key yet
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh USERNAME@SERVER_IP "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

---



## Part 2 — Confirm Docker works on the server

In the server terminal:

```bash
docker ps            # should list running containers (may be empty)
docker compose version
```

If `docker ps` gives a permissions error, prefix with `sudo` or ask the admin to
add you to the `docker` group.

---



## Part 3 — Get the code + the non-tracked files onto the server



### 3a. Clone the repository (first time only)

```bash
cd ~                                   # or /opt if you have rights: cd /opt
git clone <YOUR_REPO_URL> ece-portal
cd ece-portal
```

For later updates you just run:

```bash
cd ~/ece-portal
git pull
```



### 3b. Files you MUST copy manually (NOT in Git)

`git pull` will **not** bring these — they are deliberately excluded (`.gitignore`)
because they contain data or secrets. Copy them from your laptop into the matching
folder on the server. Create folders if they don't exist.


| What                                                         | Server folder it goes in                           | Notes                                                                                                                                                                                     |
| ------------------------------------------------------------ | -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.env.docker`                                                | repo root (`~/ece-portal/.env.docker`)             | Secrets: `SECRET_KEY`, DB passwords, `BOOTSTRAP_ADMIN_*`, SerpAPI keys. **Never commit.**                                                                                                 |
| `data/assets/` (all CSV/XLSX + `Links.txt`)                  | `~/ece-portal/data/assets/`                        | ~25 files (faculty_master.csv, course_allocations.csv, `Monsoon YYYY.csv`, `Winter YYYY.csv`, mapping xlsx, etc). See [DATA_ASSETS.md](DATA_ASSETS.md).                                   |
| `backend/documents/**/*.pdf`                                 | `~/ece-portal/backend/documents/<same subfolder>/` | The meeting minutes PDFs (~365 files) under `ece-faculty-meets/`, `senate-minutes/`, `aac-meetings/`, `pgc-meetings/`, `ugc-meetings/`. The folder structure IS in Git; the PDFs are not. |
| `backend/storage/` (if you have runtime uploads to preserve) | `~/ece-portal/backend/storage/`                    | Only needed if migrating existing uploads/CO-PO results. Fresh installs can skip.                                                                                                         |
| A **MySQL dump** of your current data (recommended)          | copy anywhere, e.g. `~/dump.sql`                   | So the server starts with the same data instead of empty tables. Create it on your laptop — see 3c.                                                                                       |
| `certs/` (`fullchain.pem`, `privkey.pem`)                    | `~/ece-portal/certs/`                              | Only if enabling HTTPS with the SSL nginx config. Can be generated on the server instead.                                                                                                 |


**Copy from your laptop (PowerShell), examples:**

```powershell
# From the repo root on your laptop:
scp .env.docker USERNAME@SERVER_IP:~/ece-portal/.env.docker
scp -r data/assets USERNAME@SERVER_IP:~/ece-portal/data/
scp -r backend/documents USERNAME@SERVER_IP:~/ece-portal/backend/
```

(You can also drag-and-drop files in the VS Code Remote explorer.)

### 3c. Create + restore a MySQL dump (recommended, keeps your data)

On your laptop, with the local Docker stack running, export current data:

```powershell
docker compose --env-file .env.docker exec -T mysql `
  mysqldump -u portal_user -p"<MYSQL_PASSWORD>" ece_dept_portal > dump.sql
```

Copy it up:

```powershell
scp dump.sql USERNAME@SERVER_IP:~/ece-portal/dump.sql
```

You'll import it after the DB container is up (Part 4, step 3).

---



## Part 4 — Bring the stack up with Docker (on the server)

```bash
cd ~/ece-portal

# 1. Make sure .env.docker is present and correct. If starting from the template:
#    cp .env.docker.example .env.docker  && edit it.
#    Set: SECRET_KEY (openssl rand -hex 32), MYSQL_* passwords,
#         BOOTSTRAP_ADMIN_EMAIL / BOOTSTRAP_ADMIN_PASSWORD,
#         PORTAL_FRONTEND_URL=http://SERVER_IP:8080 (or your domain),
#         CORS_ORIGINS=http://SERVER_IP:8080

# 2. Build and start everything (MySQL + backend + frontend):
docker compose --env-file .env.docker up -d --build

# 3. (If you made a dump) import your data:
docker compose --env-file .env.docker exec -T mysql \
  mysql -u portal_user -p"<MYSQL_PASSWORD>" ece_dept_portal < dump.sql

# 4. Apply any pending DB migrations (safe to run anytime):
docker compose --env-file .env.docker exec backend alembic upgrade head

# 5. Check health:
docker compose --env-file .env.docker ps
docker compose --env-file .env.docker logs -f backend
```

Open `http://SERVER_IP:8080` in a browser (or the `PORTAL_HTTP_PORT` you set).

> The backend runs `alembic upgrade head` automatically on startup too, so a fresh
> DB gets the schema even without a dump — it will just start empty (aside from the
> bootstrap admin).

---



## Part 5 — Give `admin-ece` admin access

The first admin is created automatically from `.env.docker`
(`BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD`) on first backend start.

**Option A — make** `admin-ece` **the bootstrap admin (before first start):**
set in `.env.docker`:

```
BOOTSTRAP_ADMIN_EMAIL=admin-ece@iiitd.ac.in
BOOTSTRAP_ADMIN_PASSWORD=<a strong temporary password>
```

Then bring the stack up. Log in and change the password immediately.

**Option B — promote/create** `admin-ece` **on a running stack:**
Log in as the existing admin → **User Management** → create the user
`admin-ece@iiitd.ac.in` with role **admin** (or edit an existing user's role to
admin). See [USER_MANAGEMENT.md](USER_MANAGEMENT.md).

**Option C — from the server shell (if you can't log in):**

```bash
docker compose --env-file .env.docker exec backend python -c "
from app.database.session import SessionLocal
from app.database.models.user import User, UserRole
from app.auth.security import hash_password
db=SessionLocal()
u=db.query(User).filter(User.email=='admin-ece@iiitd.ac.in').first()
if u: u.role=UserRole.admin
else:
    db.add(User(email='admin-ece@iiitd.ac.in', full_name='ECE Admin',
                hashed_password=hash_password('CHANGE_ME_NOW'), role=UserRole.admin,
                must_change_password=True))
db.commit(); print('done')
"
```

Then log in as `admin-ece` and change the password.

---



## Part 6 — What your collaborator does (to work like you do)

Your friend does **not** re-deploy the server. They develop the same way and share
the server. Two common setups:

### 6a. Both of you edit ON the server (simplest)

1. Ask the admin to create an SSH account for your friend (their own
  `USERNAME`/password) on the same server, or share access per institute policy.
2. Your friend installs **Remote - SSH**, adds the same `SERVER_IP`, connects, and
  opens `~/ece-portal` (or wherever it's cloned).
3. You both `git pull` before starting and `git push` small commits often so you
  don't overwrite each other. Only one person runs
   `docker compose ... up -d --build` at a time.



### 6b. Each develops locally, deploys via Git

1. Friend clones the repo on their own laptop, copies the same **non-tracked files**
  (Part 3b) from you out-of-band (secure copy / shared drive), and runs the local
   Docker stack (`docker compose --env-file .env.docker up -d --build`).
2. You share the same `.env.docker` values if you want identical login/JWT behaviour.
3. Workflow: edit → commit → push. On the server: `git pull` →
  `docker compose --env-file .env.docker up -d --build` →
   `... exec backend alembic upgrade head`.
4. One person owns the canonical MySQL dump; the other imports it when schema/seed
  data changes (see 3c and [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)).

**Golden rules for collaboration**

- Never commit `.env.docker`, `data/assets/`, PDFs, SQL dumps, or `storage/`.
- `git pull` before you start; push small commits frequently.
- After pulling code that changes the DB, always run `alembic upgrade head`.

---



## Quick reference (server, from `~/ece-portal`)

```bash
git pull                                                        # get latest code
docker compose --env-file .env.docker up -d --build            # (re)build & start
docker compose --env-file .env.docker exec backend alembic upgrade head
docker compose --env-file .env.docker logs -f backend          # watch logs
docker compose --env-file .env.docker ps                       # status
docker compose --env-file .env.docker down                     # stop (keeps data)
```

See also: [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md), [DATA_ASSETS.md](DATA_ASSETS.md),
[SECURITY.md](SECURITY.md), [USER_MANAGEMENT.md](USER_MANAGEMENT.md).