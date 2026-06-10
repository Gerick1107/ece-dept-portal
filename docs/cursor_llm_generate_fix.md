# Cursor Fix — LLM Insights `/generate` Endpoint 404

---

## Problem

The frontend is correctly calling `POST /api/v1/llm-insights/generate` but the backend returns 404 — the route does not exist yet. The comparison endpoint `GET /api/v1/llm-insights/comparison` works fine (200 OK), so the router file exists. The generate route just needs to be added to it.

Do not touch the comparison endpoint or any other working route.

---

## Step 1 — Locate the existing router file

Find the file that registers `GET /api/v1/llm-insights/comparison`. It will be something like:
- `routers/llm_insights.py` (FastAPI)
- `routes/llmInsights.js` (Express)
- or equivalent in your framework

Read this file fully before editing.

---

## Step 2 — Check DB / migration for `llm_insights_cache` table

Before writing the endpoint, check if the `llm_insights_cache` table already exists in the database or in the migrations folder. If it does not exist, create a migration to add it:

```sql
CREATE TABLE IF NOT EXISTS llm_insights_cache (
    id SERIAL PRIMARY KEY,
    course_title VARCHAR NOT NULL,
    run_identifier VARCHAR NOT NULL,
    prompt_used TEXT,
    llm_response TEXT NOT NULL,
    generated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (course_title, run_identifier)
);
```

`run_identifier` should be a stable string derived from course + latest semester (e.g. `"ECE-230_Winter2026"`) so the cache key survives across page reloads.

---

## Step 3 — Check environment variable

Before writing the Gemini call, verify `GEMINI_API_KEY` exists in the `.env` file and is being loaded by the app. If it is missing, log a clear startup warning:
```
WARNING: GEMINI_API_KEY not set. LLM Insights generate endpoint will fail.
```

Do not hardcode the key anywhere.

---

## Step 4 — Add `POST /api/v1/llm-insights/generate`

Add this route to the existing llm-insights router. The frontend is already sending requests to this exact path — do not change the URL.

### Request body (already being sent by frontend)
```json
{
  "course_title": "ECE-230: Fields and Waves (F&W)"
}
```

### Handler logic

```
1. Parse course_title from request body.

2. Call the same data-fetching logic used by the comparison endpoint to get:
   - current semester name + CO attainment values
   - previous semester name + CO attainment values
   - PO/PSO attainment values for both semesters
   - CO descriptions for this course (from CO-PO mapping sheets in data/assets/)
   - PO descriptions (from same mapping sheets)

3. Build a run_identifier string, e.g.: f"{course_title}_{current_semester}".replace(" ", "_")

4. Check llm_insights_cache for an existing row matching (course_title, run_identifier).
   - If found: return { "insights": cached_row.llm_response, "cached": true, "generated_at": cached_row.generated_at }
   - If not found: proceed to step 5.

5. Build the prompt (see Prompt Template below).

6. Call Gemini 1.5 Flash API:
   URL: https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}
   Method: POST
   Headers: { "Content-Type": "application/json" }
   Body:
   {
     "contents": [{ "parts": [{ "text": <prompt> }] }],
     "generationConfig": { "temperature": 0.7, "maxOutputTokens": 1024 }
   }

7. Extract response text:
   result = data["candidates"][0]["content"]["parts"][0]["text"]

8. Insert into llm_insights_cache:
   (course_title, run_identifier, prompt_used, llm_response, generated_at=now)

9. Return:
   { "insights": result, "cached": false, "generated_at": <now> }
```

### Error handling
- If `GEMINI_API_KEY` is not set → return 500: `{ "error": "GEMINI_API_KEY not configured on server." }`
- If Gemini API returns non-200 → log the full error response, return 502: `{ "error": "Could not generate insights at this time. Please try again." }`
- If course has no comparison data (only 1 semester) → still call LLM but use the single-semester prompt variant (see below)
- Wrap entire handler in try/except — never let an unhandled exception reach the client

---

## Prompt Template

Build this string dynamically on the backend:

```
You are an academic course improvement advisor for an engineering college (Electronics & Communication Engineering department).

Course: {course_title}
Current semester: {current_semester}
Previous semester: {previous_semester}

Course Outcome (CO) descriptions for this course:
{co_descriptions}

Programme Outcome (PO) descriptions:
{po_descriptions}

CO Attainment Comparison:
{co_rows}

PO/PSO Attainment Comparison:
{po_rows}

Based on the data above:
1. For each CO that has DECLINED compared to the previous semester, identify likely academic/pedagogical reasons specific to that CO's topic, and suggest 3-4 concrete teaching or learning strategies the faculty can adopt next semester to improve attainment for that specific CO.
2. For each CO that has IMPROVED, briefly note what may be working well and how to sustain it.
3. Based on PO/PSO attainment trends, suggest any overall course delivery improvements.
4. Keep suggestions specific to the CO topics — do not give generic advice.
5. Format your response with a clear heading for each CO, followed by a final Overall Recommendations section.
```

### Formatting the CO and PO rows for the prompt
```
co_rows example:
CO1: previous=62.9%, current=50.9%, delta=-12.1% [DECLINED]
CO2: previous=44.8%, current=50.9%, delta=+6.0%  [IMPROVED]
CO3: previous=78.5%, current=52.6%, delta=-25.9% [DECLINED]
CO4: previous=12.9%, current=50.0%, delta=+37.1% [IMPROVED]
CO5: previous=74.1%, current=47.4%, delta=-26.7% [DECLINED]
```

### Single-semester fallback prompt (when no previous data)
If only one semester exists, replace the comparison section with:
```
Only one semester of data is available for this course. Current CO attainments:
{co_rows_single}

Based on typical attainment targets of 60%, suggest teaching and learning strategies to improve attainment for any COs currently below target.
```

### CO/PO description fallback
If the mapping sheet for this course cannot be found in `data/assets/`, use:
```
CO descriptions: Not available for this course.
PO descriptions: Standard PO1-PO12 as per NBA guidelines.
```
Do not crash — log a warning and continue with fallback text.

---

## Step 5 — Frontend: handle the response

Find the frontend component that calls `POST /api/v1/llm-insights/generate`. It is currently showing *"Could not generate insights at this time. Please try again."* because it receives a 404.

Once the endpoint exists and returns correctly, the existing error handling should clear automatically. But verify:

- The frontend is reading `response.insights` (or whatever field name the component expects) — make sure the backend response field name matches exactly what the frontend reads.
- If the frontend expects a different field name (e.g. `result`, `text`, `content`), match it — do not change both sides unnecessarily, just check and align one to the other.
- The loading spinner should show while the POST is in flight — verify it is tied to the pending state of this call specifically, not the comparison call.
- On success, render the insights text. If the response includes markdown headings (which Gemini will produce), render them properly — use a markdown renderer if one is already in the project, or at minimum convert `##` headings to `<h3>` and `**bold**` to `<strong>` so it doesn't display as raw markdown symbols.

---

## What NOT to change
- `GET /api/v1/llm-insights/comparison` — working fine, do not touch
- The comparison tables UI — already rendering correctly (visible in screenshot)
- Course selection dropdown — working fine
- Any other existing routes or components
