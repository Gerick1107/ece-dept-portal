# Cursor Task — Fix Docker networking & volume issues breaking Groq, Local LLM, and document access

## Context
Everything worked when the backend ran natively on Windows. After dockerizing, three things broke
simultaneously: Groq cloud calls fail, the new Local (Ollama) provider fails, and documents under
backend/documents are reported "missing on disk" even though they exist on the host machine.
This is almost certainly NOT three separate bugs — it's Docker networking/volume fundamentals that
don't carry over automatically when code moves from running natively to running inside a container.

## Fix 1 — Local LLM (Ollama) unreachable from inside the container
Ollama runs on the Windows HOST machine, not inside any Docker container. Code that points at
`http://localhost:11434/v1` works when the backend runs natively, but inside a Docker container
`localhost` refers to the container itself, not the host — so the local LLM client currently has
no way to reach Ollama.

- Find every place `LOCAL_LLM_BASE_URL` (or equivalent) is set to `http://localhost:11434/v1`.
- For the Dockerized backend, this must become `http://host.docker.internal:11434/v1` —
  Docker Desktop's special DNS name that resolves to the host machine from inside a container.
- Make this configurable via `.env.docker` (e.g. `LOCAL_LLM_BASE_URL=http://host.docker.internal:11434/v1`)
  rather than hardcoded, so running the backend natively (non-Docker) can still use `localhost` via a
  different .env file. Do not hardcode either value in source.
- Confirm `docker-compose.yml`'s backend service can resolve `host.docker.internal` — on Docker
  Desktop for Windows this works out of the box; if using Linux Docker Engine, add
  `extra_hosts: ["host.docker.internal:host-gateway"]` to the backend service to make it work there too.
- Test: from inside the running backend container (`docker compose exec backend sh`), run
  `curl http://host.docker.internal:11434/v1/models` and confirm it returns the pulled Ollama models.

## Fix 2 — Groq (cloud) unreachable
This is a different failure mode (Groq is outbound internet, not host-machine-local), but broke at
the same time, so check both of these in order:

1. Confirm `GROQ_API_KEY` is actually present inside the running container's environment, not just
   in some `.env` file that isn't the one being loaded:
   `docker compose exec backend env | grep GROQ`
   If it's missing, check that `.env.docker` (the file referenced by `--env-file .env.docker` in the
   up/build command) actually contains `GROQ_API_KEY` and that `docker-compose.yml`'s backend service
   has `env_file: .env.docker` or equivalent `environment:` passthrough — don't assume the same .env
   that worked natively is the one Docker is reading.
2. Confirm outbound internet access works from inside the container at all:
   `docker compose exec backend curl -I https://api.groq.com`
   If this fails/times out, it's a Docker network configuration issue (e.g. a custom Docker network
   without internet egress, or a corporate/firewall rule blocking the container's network namespace
   specifically) — diagnose and fix the network config rather than the application code.
3. Once both confirm fine, re-test the actual Groq-backed endpoint and confirm the error is gone.

## Fix 3 — "File missing on disk" for backend/documents
Files exist on the host machine but are invisible to the dockerized backend. This means the host
folder is not mounted into the container — the container has its own separate filesystem and only
sees folders explicitly declared as volumes in docker-compose.yml.

- Find the existing `volumes:` section for the `backend` service in `docker-compose.yml`.
- Confirm there's a bind mount (or named volume populated correctly) covering wherever
  `backend/documents` (or whatever the actual configured documents path is) lives, e.g.:
  ```
  volumes:
    - ./backend/documents:/app/documents
  ```
  (adjust left/right paths to match the actual host folder and the path the application code expects
  inside the container — check the application's config for the exact expected path, don't guess).
- If a volume mount already exists but paths don't match (e.g. host path is right but container path
  doesn't match what the app code reads from, or vice versa), fix the mismatch rather than adding a
  duplicate mount.
- After fixing, rebuild and confirm: `docker compose exec backend ls /app/documents` (or whatever the
  correct container path is) shows the actual files, then re-test the "All Meetings" file view in the UI.

## General verification steps to run after all three fixes
1. `docker compose --env-file .env.docker up -d --build`
2. Confirm Groq path works (ask an LLM Insights question with Cloud selected).
3. Confirm Local path works (same question with Local selected) — should return an answer in
   seconds, not minutes, and not "Request failed".
4. Confirm a document under "All Meetings" opens/displays correctly, not "File missing on disk".
5. Report back exactly what `docker compose exec backend env | grep -E "GROQ|LOCAL_LLM"` and the
   actual `volumes:` block for the backend service look like, so we can confirm config is correct
   going forward — don't just fix and move on silently, show the resulting config.

Do not change retrieval/RAG logic, the planning engine, or anything unrelated to these three
connectivity/path issues — this is a Docker configuration fix, not a feature change.
