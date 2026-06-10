# Cursor Prompt — LLM Insights Dashboard (Gemini 1.5 Flash Integration)

---

## Overview

Build a new **LLM Insights Dashboard** that allows faculty to select a course and receive AI-generated, actionable recommendations on how to improve CO and CO-PO attainments for upcoming semesters. The LLM (Google Gemini 1.5 Flash) compares attainment data across previous semesters for the same course and generates targeted teaching/learning improvement suggestions when a decline is detected.

---

## Environment Setup

Add the following to your `.env` file if not already present:

```
GEMINI_API_KEY=your_key_here
```

**Never hardcode the API key anywhere in source code.** Access it only via `process.env.GEMINI_API_KEY` (Node) or `os.environ.get("GEMINI_API_KEY")` (Python) or your framework's equivalent env accessor.

---

## Semester Ordering Logic

Semesters follow this strict alternating pattern:
```
Monsoon 2025 → Winter 2026 → Monsoon 2026 → Winter 2027 → Monsoon 2027 → Winter 2028 → ...
```

When comparing semesters for the same course:
- Parse semester labels into a sortable sequence using this rule:
  - Monsoon YYYY → sort key: `YYYY.1`
  - Winter YYYY → sort key: `YYYY.2`
- Always compare the **most recent semester** against the **immediately preceding semester** for the same course.
- If only one semester of data exists for a course, skip comparison and note "insufficient history" in the UI.

---

## Data Source

All attainment data is already available in the `copo_run_analytics_snapshots` table. This is the same table used by the Analytics Dashboard — do not create duplicate data-fetching logic, reuse existing query patterns.

Relevant fields to retrieve per course per semester run:
- `course_id` / `course_name` / `course_code`
- `semester` (e.g. "Monsoon 2026")
- `faculty_name` (if available)
- `co_attainments` — per-CO attainment values (CO1, CO2, ... CON)
- `po_attainments` — per-PO attainment values (PO1, PO2, ... PON)
- `co_po_mapping` or reference to the mapping sheet (see below)
- `run_id` — used for caching LLM responses

---

## CO-PO Mapping Sheets

The portal has CO mapping sheets stored in `data/assets/` (or equivalent assets directory). Before writing this feature:

1. **Locate the CO-PO mapping files** in `data/assets/` — these define what each CO and PO stands for per course.
2. Read these files to understand their format (CSV, JSON, or similar).
3. When constructing the LLM prompt, include the CO descriptions (e.g. "CO3: Student will be able to design a combinational circuit") and PO descriptions (e.g. "PO2: Problem Analysis") so the LLM gives course-specific, semantically meaningful suggestions rather than generic ones.
4. Load the mapping for the selected course dynamically — do not hardcode mappings.

---

## New Page: LLM Insights Dashboard

### Route
Add a new route, e.g. `/llm-insights` or `/insights`, accessible from the main navigation sidebar. Place it after the Analytics tab in the nav order.

### Access
- Available to **faculty** (sees only their own courses) and **admin** (sees all courses).
- Reuse existing auth/role logic — do not build new auth.

---

## UI Layout

### Step 1 — Course Selection
At the top of the page, show a dropdown/select input:
```
Select Course: [ Course Code — Course Name ▾ ]
```
- Populate from distinct courses available in `copo_run_analytics_snapshots` for the logged-in faculty (or all courses for admin).
- On selection, trigger data fetch and LLM call (or cache retrieval).

### Step 2 — Semester Comparison Summary (shown after course selection)

Display a clean comparison table before the AI insights:

```
┌─────────────────┬──────────────┬──────────────┬──────────┐
│ CO              │ Previous Sem │ Current Sem  │ Δ Change │
├─────────────────┼──────────────┼──────────────┼──────────┤
│ CO1             │ 72%          │ 68%          │ ▼ -4%    │
│ CO2             │ 65%          │ 70%          │ ▲ +5%    │
│ CO3             │ 80%          │ 74%          │ ▼ -6%    │
└─────────────────┴──────────────┴──────────────┴──────────┘
```

- Declining COs (negative delta): highlight row in soft red / left red border
- Improving COs (positive delta): highlight in soft green / left green border
- No change: neutral

Also show a PO attainment comparison table in the same format below the CO table.

### Step 3 — AI Insights Panel

Below the comparison tables, show an **"AI Insights"** card/panel:

```
┌─────────────────────────────────────────────────────┐
│ 🤖 AI Insights — [Course Name] ([Current Semester]) │
├─────────────────────────────────────────────────────┤
│ [Generated recommendations here]                    │
│                                                     │
│ Generated on: [timestamp]          [Regenerate ↺]  │
└─────────────────────────────────────────────────────┘
```

- Show a loading spinner while the Gemini API call is in progress.
- Show the cached response if already generated for this `run_id` (do not re-call API on page reload).
- Show a **Regenerate** button that forces a fresh API call and updates the cache.
- If the LLM call fails, show a friendly error: *"Could not generate insights at this time. Please try again."*

---

## Backend — LLM Call

### API Endpoint
Create a new backend endpoint, e.g.:
```
POST /api/llm-insights/generate
Body: { course_id, run_id }
```

### Caching
- Before calling Gemini, check if a cached response exists in the DB for this `run_id`.
- Store cache in a new table `llm_insights_cache`:
  ```sql
  CREATE TABLE llm_insights_cache (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR NOT NULL UNIQUE,
    course_id VARCHAR NOT NULL,
    prompt_used TEXT,
    llm_response TEXT NOT NULL,
    generated_at TIMESTAMP DEFAULT NOW()
  );
  ```
- If cached: return cached response immediately.
- If not cached: call Gemini, store response, return it.

### Gemini API Call
```javascript
const response = await fetch(
  `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${process.env.GEMINI_API_KEY}`,
  {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
      generationConfig: {
        temperature: 0.7,
        maxOutputTokens: 1024,
      }
    })
  }
);
const data = await response.json();
const result = data.candidates?.[0]?.content?.parts?.[0]?.text ?? "No response generated.";
```

---

## Prompt Construction

Build the prompt dynamically on the backend using real data. Structure it as follows:

```
You are an academic course improvement advisor for an engineering college.

Course: {course_code} — {course_name}
Department: {department}
Faculty: {faculty_name}
Semester being reviewed: {current_semester}
Previous semester: {previous_semester}

Course Outcome Descriptions:
{co_descriptions}
(e.g. CO1: Understand the fundamentals of digital logic design
      CO2: Apply Boolean algebra to simplify logic circuits
      ...)

Programme Outcome Descriptions:
{po_descriptions}
(e.g. PO1: Engineering Knowledge
      PO2: Problem Analysis
      ...)

CO Attainment Comparison:
{co_comparison_table}
(e.g. CO1: previous=72%, current=68%, delta=-4% [DECLINED]
      CO2: previous=65%, current=70%, delta=+5% [IMPROVED]
      CO3: previous=80%, current=74%, delta=-6% [DECLINED]
      ...)

PO Attainment Comparison:
{po_comparison_table}
(same format as above)

Based on the above data:
1. Identify which Course Outcomes have declined and explain likely academic reasons for each decline in the context of the specific CO description.
2. For each declined CO, suggest 3–5 concrete, specific teaching and learning strategies the faculty can adopt in the upcoming semester to improve attainment. These must be relevant to the specific CO topic — not generic advice.
3. Identify which COs have improved and briefly note what may be working well for those.
4. Suggest any overall course delivery improvements based on the PO attainment trends.
5. Keep the tone professional and constructive. Be specific — reference the CO topics directly.

Format your response with clear headings for each CO and a final summary section.
```

**Prompt construction rules:**
- Always populate CO and PO descriptions from the mapping sheets in `data/assets/` for the specific course.
- If a CO mapping is not found for a particular CO number, use "CO{N}: Description not available" as fallback.
- Clearly mark which COs declined vs improved in the prompt text.
- If there is no previous semester data (first run for this course), modify the prompt to ask for general improvement strategies based on current attainment levels vs typical thresholds (e.g. 60% target).
- Trim whitespace and sanitise all values before inserting into the prompt string.

---

## Edge Cases to Handle

| Scenario | Behaviour |
|---|---|
| Only 1 semester of data for course | Show current attainments only, prompt asks for general improvement strategies, note "No previous semester available for comparison" in UI |
| All COs improved | Show insights anyway — note what's working and how to maintain/further improve |
| Gemini API key missing from env | Throw a clear server error: "GEMINI_API_KEY not configured" |
| Gemini API rate limit hit | Return error to frontend: "AI service temporarily unavailable, please try again in a moment" |
| CO mapping file not found for course | Use generic CO descriptions as fallback, log a warning |
| run_id has cached response | Return cached, show "Generated on: {date}" — do not re-call API |

---

## Navigation

- Add **"LLM Insights"** to the main sidebar nav (for both faculty and admin).
- Place it after the Send Notifications tab for admin and Notification tab for faculty.
- Use a brain/sparkle icon (🧠 or ✨) or equivalent from your existing icon library.
- For both admin and faculty login: show a course dropdown with all courses across all semesters.

---

## General Reminders

- Read all existing files before writing new ones — reuse query patterns from Analytics dashboard.
- Do not expose `GEMINI_API_KEY` in any frontend code, API response, or log.
- The CO-PO mapping sheet reading logic should be a shared utility, not inline in the endpoint.
- Run the DB migration for `llm_insights_cache` as a proper migration file, not raw SQL.
- Handle the case where `copo_run_analytics_snapshots` has multiple runs for the same course+semester — use the most recent run (latest `created_at` or `run_id`).
