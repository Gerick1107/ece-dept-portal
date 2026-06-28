# Cursor Task — Local LLM Integration + Provider Toggle + Model Migration

> Paste this whole file into Cursor as the task brief. It assumes Cursor has access to the
> existing FastAPI backend (RAG pipeline over meeting-minutes PDFs, MySQL + SQLAlchemy,
> sentence-transformers embeddings) and whatever frontend serves the chatbot/insights UI.
> Do the three parts **in order** — each is a checkpoint, not a single giant change.

---

## 0. Why this is happening (context for Cursor, not a task)

The team has been told: no paid APIs, no LLM that's "free today, paid tomorrow." Everything
LLM-related must run **locally and stay free forever**. Separately, `llama-3.3-70b-versatile`
on Groq is being deprecated — Groq announced on June 17, 2026 that it shuts down on
**August 16, 2026**, so it cannot be the long-term default even on the cloud path.
(Notice: https://console.groq.com/docs/deprecations)

The fix has three parts:
1. Stop hardcoding a dying Groq model — make the model name config-driven everywhere.
2. Stand up a real local LLM via **Ollama**, which exposes an OpenAI-compatible API at
   `http://localhost:11434/v1`, so it's close to a drop-in swap for the existing Groq client
   code (same `chat.completions.create(...)` shape, OpenAI SDK works against either backend
   unchanged — only `base_url`, `api_key`, and `model` differ).
3. Add a `provider` choice in the UI (`groq` vs `local`) for every LLM-touching action, so the
   user decides per-query whether to use the cloud model or the local one, and the backend
   routes the request to the right client accordingly.

---

## PART 1 — Fix the model deprecation (cloud path)

**Goal:** Nothing in the codebase hardcodes `llama-3.3-70b-versatile` or any other model string.
The Groq path keeps working past August 16, 2026 with zero code changes — only `.env` changes.

**Do this:**
1. Search the entire repo for `llama-3.3-70b-versatile` (and any other hardcoded Groq model
   strings) and replace every usage with a read from config (e.g. `settings.GROQ_MODEL`).
2. Add `GROQ_MODEL` to `.env` / `.env.example` with default `openai/gpt-oss-120b` (Groq's
   recommended replacement for the 70b-versatile model, same vendor, OpenAI-compatible
   endpoint, no other code changes needed).
3. Confirm there is exactly **one** place in the codebase that constructs the Groq client
   (one `OpenAI(base_url=..., api_key=...)` instantiation, or equivalent). If there are
   multiple scattered instantiations, consolidate into a single factory function/module
   (e.g. `app/llm/groq_client.py`) and have every caller (RAG answer generation, insight
   generation, anything else using the LLM) import from there. This is required groundwork
   for Part 3.
4. Run a smoke test: confirm a basic chat completion still returns a valid response with the
   new model.

**Acceptance:** `grep -ri "llama-3.3-70b-versatile"` returns nothing in source files. One
config var controls the Groq model. One shared client factory for Groq exists.

---

## PART 2 — Integrate a local LLM via Ollama

**Goal:** A fully working, fully free, fully local LLM backend that can answer the same kinds
of queries (RAG question-answering, insight generation) as the Groq path, runnable on a normal
laptop with no dedicated GPU.

**Install & download (do this on the dev machine, and document it in the README):**
1. Install Ollama (https://ollama.com) — free, MIT-licensed, runs as a local background
   service exposing both a native API (`/api/chat`) and an **OpenAI-compatible API**
   (`/v1/chat/completions`) on `http://localhost:11434`.
2. Pull a small, CPU-friendly instruction model. Do **not** default to a large model — this
   needs to run acceptably on a normal laptop with no strong GPU. Pull and benchmark these,
   in this order of preference for this RAG use case (mostly summarizing retrieved chunks,
   not deep multi-step reasoning, so a smaller model is fine):
   - `ollama pull llama3.2:3b` (fast, good default, ~2GB)
   - `ollama pull phi3:mini` (similar size/speed, alternative to compare against)
   - `ollama pull mistral:7b-instruct-q4_K_M` (heavier but better quality; confirm it's the
     **quantized Q4 GGUF**, not full fp16 — full precision is what causes multi-minute
     response times on CPU-only machines; Q4 quantization is required for acceptable speed)
   - Optional, only if quality testing shows the above are insufficient:
     `ollama pull qwen2.5:7b`
3. Verify each pulled model responds in a reasonable time (seconds, not minutes) with:
   `curl http://localhost:11434/v1/chat/completions -d '{"model":"llama3.2:3b","messages":[{"role":"user","content":"Hello"}]}'`
   If any model takes multiple minutes to respond, something is misconfigured (e.g. accidentally
   pulled a non-quantized variant, or insufficient RAM causing swap) — diagnose before proceeding,
   don't just accept it.
4. Decide on **one default local model** based on the benchmark (recommend `llama3.2:3b` unless
   testing shows another is clearly better for this RAG task) and put it in config as
   `LOCAL_LLM_MODEL` (e.g. default `"llama3.2:3b"`).

**Backend integration:**
1. Add `app/llm/local_client.py` mirroring the structure of the existing Groq client factory
   from Part 1: an OpenAI SDK client with `base_url="http://localhost:11434/v1"` and
   `api_key="ollama"` (any non-empty string — Ollama ignores it but the SDK requires the field).
2. Add config: `LOCAL_LLM_BASE_URL` (default `http://localhost:11434/v1`), `LOCAL_LLM_MODEL`
   (from step 4 above). Never hardcode the URL or model name outside config.
3. Both the Groq client and the local client should expose the **same interface** (e.g. a
   `chat(messages, **kwargs) -> str` function or similar) so calling code doesn't need to know
   which provider it's talking to — see Part 3 for how the provider is selected.
4. Add a basic health-check endpoint or startup check that confirms Ollama is reachable and the
   configured local model is pulled, with a clear error message if not (e.g. "Ollama is not
   running — start it with `ollama serve`" or "Model llama3.2:3b not found — run
   `ollama pull llama3.2:3b`"). Fail gracefully, not with a raw connection-refused stack trace.
5. Test the local path end-to-end through the existing RAG pipeline: same retrieval step
   (unchanged — sentence-transformers embeddings stay exactly as they are, only the
   generation/answer step swaps), but generation routed to the local Ollama client instead
   of Groq. Confirm it produces a coherent answer from retrieved PDF chunks.
6. Note for the team: a 3B–7B local model is weaker than the 70B-class cloud model at complex
   reasoning. If local-model answer quality is noticeably worse on harder questions, that's
   expected — it's a tradeoff for zero cost / fully offline, not a bug to "fix" by changing
   integration code.

**Acceptance:** With Ollama running and the model pulled, a request through the local-LLM path
returns a real answer in a reasonable time (seconds, not minutes) on a normal laptop CPU, using
the same RAG retrieval as the Groq path.

---

## PART 3 — UI provider toggle (Groq vs Local) before every LLM action

**Goal:** Anywhere the app currently calls an LLM — RAG question-answering over the meeting
PDFs, and LLM-generated insights, and any other LLM-touching feature — the user must be shown
a choice **in the UI** between "Cloud (Groq)" and "Local (Offline)" before the request runs,
and the backend must honor that choice per-request.

**Backend:**
1. Every API endpoint that triggers an LLM call must accept a `provider` field
   (`"groq"` or `"local"`) in its request body/params. No endpoint should default silently to
   one provider without the frontend having sent an explicit choice.
2. Add a single dispatch function (e.g. `app/llm/dispatch.py`) that takes `provider` and routes
   to the Groq client (Part 1) or local client (Part 2) accordingly, using the shared interface
   from Part 2 step 3. All LLM call sites (RAG answering, insight generation, etc.) should call
   through this dispatcher — no call site should instantiate a client directly.
3. If `provider="local"` is requested but Ollama isn't reachable or the model isn't pulled,
   return a clear, actionable error (not a 500/stack trace) that the frontend can display —
   e.g. `{"error": "local_llm_unavailable", "message": "Ollama isn't running. Start it and make sure llama3.2:3b is pulled."}`.
4. Same for `provider="groq"` if the Groq API key is missing/invalid — clear actionable error.

**Frontend:**
1. Wherever the user triggers an LLM action — asking a question in the RAG chat interface,
   requesting an LLM-generated insight, or any other such action — add a simple UI control
   (radio buttons, toggle, or dropdown) labeled clearly, e.g.:
   - "Cloud (Groq — fast, online)"
   - "Local (Offline — free, runs on this machine)"
2. This choice must be made **before** the action runs, not changeable mid-generation. Default
   selection is up to you (suggest defaulting to whichever the team uses most, with the other
   always one click away) — but the user must always be able to see and change it, not have it
   hidden in settings only.
3. Persist the last-chosen provider per session (e.g. local component state or a simple
   localStorage-equivalent appropriate to the framework in use) so the user isn't forced to
   reselect every single query, while still being able to switch anytime.
4. Surface backend errors from step 3/4 above clearly in the UI (e.g. "Local LLM isn't running —
   switch to Cloud or start Ollama on your machine") rather than a generic failure message.
5. Apply this toggle to **every** LLM-touching feature in the app, not just the RAG chat —
   audit the whole frontend for any place that currently calls an LLM-backed endpoint and add
   the same control consistently.

**Acceptance:** From the UI, the user can pick Groq or Local before asking a PDF question or
generating an insight, gets a real answer from whichever was selected, and gets a clear, friendly
error (not a crash) if the selected provider is unavailable.

---

## Final checklist before calling this done

- [ ] No hardcoded Groq model strings anywhere; `GROQ_MODEL` defaults to `openai/gpt-oss-120b`.
- [ ] Ollama installed, a quantized small model pulled, response time is seconds not minutes.
- [ ] `LOCAL_LLM_BASE_URL` / `LOCAL_LLM_MODEL` in config, never hardcoded.
- [ ] One shared dispatch point routes every LLM call to Groq or Local based on `provider`.
- [ ] Every LLM-triggering UI action has a visible provider selector, not a hidden default.
- [ ] Clear, non-crashing error messages when either provider is unavailable.
- [ ] `.env.example` updated with all new variables and short comments explaining each.
- [ ] README updated with: how to install Ollama, which model(s) to pull, and how to switch
      providers in both the API and the UI.

Do not silently expand scope beyond these three parts — if you notice other unrelated issues
while working, note them at the end of your summary instead of fixing them inline.
