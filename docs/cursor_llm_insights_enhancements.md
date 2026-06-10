# Cursor Prompt — LLM Insights Enhancements (4 Tasks)

Read every relevant file in full before making any changes. Do not guess at file locations — search for them. Do not break any existing working functionality.

---

## Task 1 — Investigate & Report: Where Are CO Descriptions Coming From?

### What to do
Before writing any code, investigate and answer this question definitively by searching the codebase:

```bash
# Search for where CO descriptions/headings/titles are being sourced
grep -r "co_description" . --include="*.py" -n
grep -r "co_heading" . --include="*.py" -n
grep -r "co_title" . --include="*.py" -n
grep -r "CO1\|CO2\|CO3" . --include="*.py" -n
grep -r "course_outcome" . --include="*.py" -n
grep -r "co_name" . --include="*.py" -n

# Also search JS/TS if applicable
grep -r "co_description\|co_heading\|co_title\|course_outcome" . --include="*.js" -n
grep -r "co_description\|co_heading\|co_title\|course_outcome" . --include="*.ts" -n

# Search all asset files
find data/assets -type f | xargs grep -l "CO\|course outcome" 2>/dev/null

# Search database models
grep -r "CourseOutcome\|course_outcome\|co_description" . --include="*.py" -n
```

After running these searches:

1. **If CO descriptions are found in a file or database table** — note the exact source (file path or table name and column), confirm the data is real (not auto-generated), and use that source in the LLM prompt construction. Add a comment in the code: `# CO descriptions sourced from: <source>`

2. **If CO descriptions are NOT found anywhere** — do NOT generate or fabricate them. Instead:
   - Remove CO description lines from the LLM prompt entirely
   - In the prompt sent to the LLM, replace CO descriptions with just the CO identifiers (CO1, CO2, etc.) and their attainment values
   - Add a `TODO` comment: `# CO descriptions not found in codebase - add source when available`
   - Add a visible note in the LLM Insights UI under the AI Insights panel: *"CO descriptions not configured. Contact admin to add CO definitions for richer insights."*

3. **Under no circumstances should the LLM or the backend fabricate CO descriptions.** If they aren't in the data, they go in as blank/unknown.

---

## Task 2 — Add Visual Summary Cards to LLM Insights Page

These are simple frontend calculations — not LLM tasks. Add a visual summary section between the course selector and the CO attainment comparison table.

### Layout
A row of summary cards (similar to the Analytics tab style) showing:

**Card 1 — COs Declined**
- Count of COs where current semester < previous semester
- Red colour theme
- Icon: downward arrow or warning

**Card 2 — COs Improved**
- Count of COs where current semester > previous semester
- Green colour theme
- Icon: upward arrow

**Card 3 — Average CO Attainment (Current)**
- Mean of all CO attainment values for the current semester
- Blue colour theme
- Show as percentage

**Card 4 — Average CO Attainment (Previous)**
- Mean of all CO attainment values for the previous semester
- Grey/neutral colour theme
- Show as percentage

**Card 5 — Overall Δ Change**
- Difference between Card 3 and Card 4
- Red if negative, green if positive
- Show with ▼ or ▲ prefix

### Bar Chart
Below the summary cards, add a grouped bar chart (reuse the same charting library already used in the Analytics tab — do not introduce a new one):
- X-axis: CO labels (CO1, CO2, CO3...)
- Two bars per CO: one for previous semester, one for current semester
- Use the same blue→red colour scheme from the Analytics tab
- Chart title: "CO Attainment: {previous_semester} vs {current_semester}"
- This chart is purely frontend — data comes from the same comparison API response already being used for the table

### Notes
- These visuals use data already returned by `GET /api/v1/llm-insights/comparison` — no new API calls needed
- If only one semester of data exists, hide the "previous semester" bar and the delta card, show a note: *"Only one semester available — comparison visuals not shown"*
- Match the card and chart styling to the existing Analytics tab components as closely as possible

---

## Task 3 — Add PO/PSO Insights to LLM Prompt

### Step 3a — Find PO/PSO descriptions in the mapping file

The CO-PO mapping sheets are in `data/assets/`. Read all files in that directory:

```bash
find data/assets -type f
```

Open each mapping file and look for:
- PO descriptions (PO1: Engineering Knowledge, PO2: Problem Analysis, etc.)
- PSO descriptions (PSO1, PSO2 — programme-specific outcomes)
- These may be in a separate sheet/tab within an Excel file, or a separate CSV, or inline in the mapping matrix

**Search pattern:**
```bash
grep -r "PO1\|PO2\|PSO1\|programme outcome\|PO description" data/assets/
```

If found:
- Extract PO and PSO label + description pairs
- Add them to the LLM prompt exactly as CO descriptions are handled (or would be handled per Task 1)

If NOT found:
- Use the standard NBA PO definitions (PO1–PO12) as fallback — these are standardised and do not need to be sourced from a file:
  ```
  PO1: Engineering Knowledge
  PO2: Problem Analysis
  PO3: Design/Development of Solutions
  PO4: Conduct Investigations of Complex Problems
  PO5: Modern Tool Usage
  PO6: The Engineer and Society
  PO7: Environment and Sustainability
  PO8: Ethics
  PO9: Individual and Team Work
  PO10: Communication
  PO11: Project Management and Finance
  PO12: Life-long Learning
  ```
- For PSOs: if not found in assets, omit PSO descriptions from the prompt (do not fabricate them — PSOs are institution/programme specific)

### Step 3b — Add PO/PSO section to LLM prompt

Extend the existing prompt string to include a PO/PSO analysis section after the CO section:

```
PO/PSO Outcome Descriptions:
{po_descriptions}
{pso_descriptions if available, else omit}

PO/PSO Attainment Comparison:
{po_rows}
(format: PO1: previous=54.7%, current=50.3%, delta=-4.3% [DECLINED])

Based on the PO/PSO attainment data above:
5. Identify which Programme Outcomes have declined and suggest course-level interventions that could improve student performance on those POs. Be specific about which teaching activities, assessments, or learning experiences map to each declining PO.
6. If PSO data is available, analyse PSO trends and suggest programme-specific improvements.
7. Note any POs that are consistently strong across both semesters.
```

### Step 3c — Add PO visual summary cards

Add a second row of summary cards below the CO cards (same style) for PO/PSO data:
- POs Declined (count, red)
- POs Improved (count, green)
- Average PO Attainment Current (blue)
- Average PO Attainment Previous (grey)
- Overall PO Δ Change (red/green)

Add a second grouped bar chart for PO attainments in the same format as the CO bar chart.

---

## Task 4 — Assessment Component Analysis via LLM

### Step 4a — Find assessment data in the database

The database stores assessment IDs for each course CO-PO evaluation run. Before writing any code, inspect the database schema:

```bash
# Find the table that stores assessment components per run
grep -r "assessment" . --include="*.py" -n | grep -i "model\|schema\|table"
grep -r "assessment_id\|component\|quiz\|assignment" . --include="*.py" -n
```

Identify:
- Which table stores assessments per run (likely linked via `run_id` or `course_id`)
- What columns are available — specifically look for:
  - Component type (assignment, quiz, midterm, lab, etc.)
  - Number of questions per component (if stored)
  - Max marks or weightage (if stored)
  - Component name/label

### Step 4b — Fetch assessment data in the generate endpoint

In the `POST /api/v1/llm-insights/generate` handler, after fetching CO/PO attainment data, also fetch the assessment components for the latest run of this course:

```python
# Pseudocode — adapt to actual ORM/query style used in this codebase
assessments = db.query(AssessmentTable).filter(
    AssessmentTable.run_id == latest_run_id
).all()

# Build a summary dict:
# {
#   "Assignment": { "count": 3, "total_questions": 45 },
#   "Quiz": { "count": 4, "total_questions": 20 },
#   "Midterm": { "count": 1, "total_questions": 10 },
#   ...
# }
```

Group components by type and count:
- How many of each component type exist
- Total questions across all components of each type (if question count is stored)
- If question count is not stored, just report the count of components

### Step 4c — Add assessment section to LLM prompt

Add a new section to the prompt after the PO section:

```
Assessment Structure for This Course (latest semester):
{assessment_summary}

Example format:
- Assignments: 3 components, 45 total questions
- Quizzes: 4 components, 20 total questions  
- Midterm Exam: 1 component, 10 questions
- Lab Practicals: 2 components

Note: CO-to-assessment mappings are not available, so analyse this purely from a pedagogical and workload perspective.

Based on the assessment structure above and the CO/PO attainment trends:
8. Evaluate whether the current assessment structure is appropriate for the number of COs being assessed.
9. Suggest whether any component types should be added, removed, or reweighted (e.g. "consider adding one more quiz to reinforce CO3 which has shown consistent decline").
10. For components with a high number of questions, suggest whether reducing question count might improve quality of assessment without reducing coverage.
11. For components with very few questions, suggest whether increasing question count could provide more reliable attainment measurement.
12. If a component type is entirely missing that could benefit learning outcomes (e.g. no lab component for a circuits course), suggest adding it.
13. Keep all suggestions grounded in the attainment data — do not suggest generic best practices without connecting them to the actual CO/PO performance shown.
```

### Step 4d — Add assessment summary cards to UI

Add a third visual section on the LLM Insights page: **Assessment Overview**

Simple display cards (no LLM needed, pure data):
- One card per component type showing: component name, count, total questions (if available)
- Style consistently with the CO/PO summary cards above
- Label the section: "Assessment Structure (Current Semester)"
- If no assessment data is found for this course/run, show: *"No assessment data available for this course."* and omit this section from the LLM prompt

---

## Step 5 — Caching: Invalidate When New Data Added

The `llm_insights_cache` currently caches by `(course_title, run_identifier)`. Since we are now adding assessment data to the prompt, a cached response generated before this update will not include assessment insights.

Add a `prompt_version` column to `llm_insights_cache`:
```sql
ALTER TABLE llm_insights_cache ADD COLUMN IF NOT EXISTS prompt_version INTEGER DEFAULT 1;
```

Bump the version to `2` in the generate endpoint. When checking cache, only use a cached response if `prompt_version = 2`. This forces one-time regeneration per course with the new richer prompt, then caches again.

---

## Step 6 — Verify Everything Works End to End

After all changes:

### 6a — Log what CO/PO source was found
```python
print(f"CO descriptions source: {co_source or 'NOT FOUND — omitted from prompt'}")
print(f"PO descriptions source: {po_source}")
print(f"Assessment data found: {len(assessments)} components")
```

### 6b — Test the full generate endpoint
```bash
curl -X POST http://localhost:8000/api/v1/llm-insights/generate \
  -H "Content-Type: application/json" \
  -d '{"course_title": "ECE-230: Fields and Waves (F&W)"}'
```

Confirm the response JSON contains `insights` with text that includes:
- CO-level analysis (with or without descriptions depending on Task 1 finding)
- PO-level analysis
- Assessment structure recommendations

### 6c — Check frontend renders correctly
- Summary cards for CO, PO, and assessments all visible
- Bar charts render without errors
- AI Insights text renders formatted (not raw markdown)
- No console errors in browser

Fix any errors found during verification before marking complete.

---

## What NOT to change
- Groq API call implementation (just changed from Gemini — do not touch)
- Caching logic (except the prompt_version addition in Step 5)
- Comparison endpoint (`GET /api/v1/llm-insights/comparison`)
- Any other dashboard or page outside LLM Insights
