# Master Cursor Prompt — IIITD ECE Portal: Analytics Dashboard

---

## OVERVIEW

Build a new **Analytics Dashboard** for the IIITD ECE department portal. The dashboard aggregates and visualizes data from four existing database tables: `btp_projects`, `faculty_awards`, `publications`, and `copo_run_analytics_snapshots`. It is a read-only, visually rich page accessible from the main sidebar navigation.

The dashboard is divided into four major sections (tabs or collapsible panels on the same page):

1. **CO/PO Attainment Analytics**
2. **BTP / IP Project Analytics**
3. **Faculty Awards Analytics**
4. **Publications Analytics**

All charts must use a consistent design system: the portal's existing color palette, clean card-based layout, smooth hover tooltips, responsive grid. Use **Recharts** (if React) or **Chart.js** for charts. All sections must have section-level filter controls and a global **Export as PDF / PNG** button per section.

Read the existing codebase thoroughly before building — understand routing, layout components, auth guards, and the API layer pattern before adding anything new.

---

## SECTION 1 — CO/PO ATTAINMENT ANALYTICS

### 1.1 Data Source

Table: `copo_run_analytics_snapshots`

Relevant columns:
- `id`, `public_id`
- `course_title` — e.g. `"ECE-548: Advanced Digital Communication (ADC)"`
- `evaluation_type` — e.g. `final_consolidated`, `mid_semester`, etc.
- `scope_summary` — text like `"Programmes: PG, UG, PhD | Branches: VLSI & ES, ECE, ECE"`
- `result_summary` — JSON blob containing CO attainment values, PO attainment values, student counts, etc. This is the primary data field.
- `run_created_at` — timestamp of when the evaluation run was created (use as the semester/period proxy for trend analysis)
- `preserved_at` — timestamp when snapshot was locked

### 1.2 Backend: Parse `result_summary`

The `result_summary` column is a JSON field. Before building the dashboard, inspect its full schema carefully by querying a few rows. It typically contains:
- Per-CO attainment percentages (e.g. `CO1: 72%, CO2: 85%, CO3: 61%` ...)
- Per-PO attainment percentages (e.g. `PO1: 68%, PO2: 74%` ...)
- Possibly: student count, pass/fail breakdown, assessment-level scores

Write a backend API endpoint `GET /api/analytics/copo` that:
1. Queries all rows from `copo_run_analytics_snapshots`
2. Parses `result_summary` JSON for each row
3. Groups rows by `course_title`
4. Within each course, sorts runs chronologically by `run_created_at` to establish a semester timeline
5. Returns a structured response suitable for the frontend charts described below

**Semester labelling**: Since the table doesn't have an explicit semester column, derive a display label from `run_created_at`:
- Jan–May → `Winter <year>`
- Jul–Nov → `Monsoon <year>`
- Jun or Dec → `Summer <year>`

### 1.3 Visualizations

#### A. Course CO Attainment Radar Chart
- One radar chart per course (show one at a time, with a course selector dropdown)
- Axes: CO1, CO2, CO3, ... (all COs for the selected course)
- Each polygon = one evaluation run / semester
- Multiple polygons overlaid with different colours to show progression
- Tooltip showing exact attainment % per CO on hover
- Legend: Monsoon 2024, Winter 2025, etc.

#### B. CO Attainment Trend (Line Chart)
- X-axis: chronological semesters (derived from `run_created_at`)
- Y-axis: attainment percentage (0–100%)
- One line per CO (CO1, CO2, CO3...)
- User can select which COs to toggle via a checkbox legend
- Shows improvement/decline of each CO over time for the selected course
- Include a dashed horizontal "target line" at a configurable threshold (default 60%)

#### C. PO Attainment Bar Chart
- Grouped bar chart for the selected course
- X-axis: PO1, PO2, PO3, ..., PO12 (standard NBA POs)
- Each group has one bar per semester run
- Colour-coded by semester
- Tooltip with exact values

#### D. CO vs PO Heatmap
- Grid: rows = COs, columns = POs
- Cell colour intensity = contribution/attainment value (light → low, dark → high)
- Shown for the most recent run of the selected course
- Course selector dropdown above

#### E. Multi-Course CO Comparison (Stretch Feature)
- Allow comparing two courses side by side
- Since different courses have different numbers of COs, normalise to percentage (0–100%) on a common axis
- Show as a grouped bar chart: X-axis = CO index (CO1, CO2...), bars = one per selected course
- Clearly label that CO indices may not be semantically equivalent across courses
- Add a disclaimer tooltip: "CO numbering may differ across courses"
- Course A selector + Course B selector dropdowns

#### F. Summary KPI Cards (top of CO/PO section)
- Total courses evaluated
- Total evaluation runs stored
- Average CO attainment across all courses (latest run per course)
- Average PO attainment across all courses (latest run per course)

### 1.4 Filters
- Course selector (dropdown, searchable)
- Evaluation type (final_consolidated / mid_semester / all)
- Semester range (from / to)

---

## SECTION 2 — BTP / IP PROJECT ANALYTICS

### 2.1 Data Source

Table: `btp_projects` (your updated schema from the BTP module)

Relevant columns: `project_type`, `course_code`, `course_name`, `guide` (or `faculty_id`), `co_guide`, `semesters`, `student_roll_nos`, `student_names`, `credit`, `sdg_review_status`, `program_specialization` (if available), `created_at`

**Note**: `semesters` is a comma-separated string (e.g. `"Monsoon 2021, Winter 2022"`). Parse it correctly — a project spanning 3 semesters should be counted in each of those semesters individually for trend analysis.

### 2.2 Summary KPI Cards

At the top of this section, show:
- **Total projects** (unique entries)
- **Total unique students** (count distinct roll numbers across all `student_roll_nos`)
- **Total faculty guides** (count distinct guides)
- **Projects with co-guide** (count where `co_guide` is not null)
- **Thesis vs IP/IS/UR split** (two large numbers side by side, or donut chart)

### 2.3 Visualizations

#### A. Projects per Semester (Bar Chart)
- X-axis: semesters chronologically (Monsoon 2021, Winter 2022, Monsoon 2022...)
- Y-axis: project count
- Stacked bars: Thesis (bottom) + IP/IS/UR (top), colour-coded
- Shows growth/decline in research activity over time

#### B. Course Code Distribution (Donut / Pie Chart)
- Segments: BTP498, BTP499, BIP399, BIS398, BUR498, etc.
- Show count and % per segment
- Clicking a segment filters the table below (if a detailed table exists)

#### C. Faculty Load Chart (Horizontal Bar Chart)
- X-axis: number of projects guided
- Y-axis: faculty name (sorted descending by count)
- Separate bars for "as Guide" (blue) and "as Co-Guide" (grey)
- Show top 15 faculty by default, with a "Show all" toggle

#### D. Program Specialization Distribution (Pie / Donut)
- Segments: ECE, CSE, CSAM, CSD, CSAI, CSSS, CSB, etc.
- Shows which programs ECE faculty are guiding most

#### E. Multi-Semester Projects (Stacked Area or Bar)
- X-axis: semesters
- Y-axis: count
- Stacked: single-semester projects vs 2-semester vs 3+ semester
- Illustrates project complexity / long-running research trends

#### F. Credit Distribution (Histogram)
- X-axis: credit values (2, 4, 6, 8)
- Y-axis: count of projects
- Split by project type (Thesis vs IP/IS/UR) using side-by-side bars

#### G. SDG Review Status Donut
- Segments: pending_review, approved, rejected (all statuses present in db)
- With count labels

#### H. Top Research Themes (Word Cloud or Ranked List)
- Extract frequent keywords from `project_title` (exclude stop words)
- Display as a ranked horizontal bar chart (top 20 keywords by frequency)
- If a word cloud library is available, use it; otherwise use the bar chart

### 2.4 Filters
- Semester (multi-select)
- Project type (Thesis / IP/IS/UR / All)
- Course name
- Faculty guide (searchable)
- Program specialization

---

## SECTION 3 — FACULTY AWARDS ANALYTICS

### 3.1 Data Source

Table: `faculty_awards`

Columns: `faculty_name`, `year` (string like `"2023-2024"`), `award`

**Award categorisation**: On the backend, classify each award into one of these categories based on keyword matching in the `award` text. Create a reusable utility function for this:

| Category | Keywords to match (case-insensitive) |
|---|---|
| Best Paper / Demo / Poster | `best paper`, `best demo`, `best poster`, `best tutorial` |
| Teaching Excellence | `teaching excellence`, `educator award`, `outstanding educator` |
| Research & Fellowship | `research excellence`, `fellowship`, `serb`, `dean`, `chair position`, `institute chair` |
| Conference Leadership | `chair`, `panelist`, `keynote`, `invited speaker`, `session co-chair`, `organiz` |
| Competitive Award & Grant | `winner`, `first place`, `scholarship`, `grant`, `felicitation`, `qualify`, `runners up`, `3rd prize` |
| Membership & Elevation | `senior member`, `elevated`, `fellow` |

A single award can only belong to one category (use first match in priority order above).

### 3.2 Summary KPI Cards
- Total awards across all faculty
- Number of faculty with at least one award
- Most awarded faculty (name + count)
- Year with most awards
- Most common award category

### 3.3 Visualizations

#### A. Awards per Faculty (Horizontal Bar Chart)
- X-axis: award count
- Y-axis: faculty name (sorted by count descending)
- Colour bars by award category (stacked — each category a different colour)
- Tooltip showing breakdown by category per faculty

#### B. Awards Over Time (Line + Bar Combo)
- X-axis: academic year (2022-2023, 2023-2024, 2024-2025)
- Bar: total awards per year (by category, stacked)
- Line: cumulative total (secondary Y-axis)
- Shows whether ECE department recognition is growing year-over-year

#### C. Award Category Breakdown (Donut Chart)
- 6 segments, one per category above
- Count + percentage in tooltip

#### D. Faculty Awards Timeline (Horizontal Swimlane / Gantt-style)
- Y-axis: faculty name
- X-axis: academic year
- Dots/markers on the lane for each award, coloured by category
- Hovering a dot shows the full award text in a tooltip
- Gives a quick visual of which faculty are consistently awarded vs occasional

#### E. Award Heatmap (Faculty × Year)
- Grid: rows = faculty names, columns = academic years
- Cell colour = number of awards that year (0 = white, 1 = light, 3+ = dark)
- Instant visual overview of recognition concentration

### 3.4 Filters
- Faculty (multi-select)
- Year (multi-select: 2022-2023, 2023-2024, 2024-2025)
- Category (multi-select)

---

## SECTION 4 — PUBLICATIONS ANALYTICS

### 4.1 Data Source

Table: `publications`

Columns: `title`, `authors`, `publication_year`, `publisher`, `citation_count`, `conference`, `journal`, `book`, `is_iiitd_publication`, `is_patent`, `inventors`, `patent_number`, `publication_date`, `pages`, `volume`, `issue`

**Important**: The publications table is currently empty in the sample data provided. Build the analytics section to gracefully handle an empty state — show an empty-state illustration with text like "No publications data available yet. Publications will appear here once the database is populated." All charts must render correctly once data is present.

### 4.2 Summary KPI Cards (shown even if 0)
- Total publications
- Total patents
- Total citations (sum of `citation_count`)
- IIITD publications (where `is_iiitd_publication = true`)
- Average citations per publication

### 4.3 Visualizations (render when data is present)

#### A. Publications per Year (Bar Chart)
- X-axis: `publication_year`
- Y-axis: count
- Stacked: Journal (green) + Conference (blue) + Book (orange) + Patent (purple)

#### B. Journal vs Conference vs Patent Split (Donut)
- Based on which of `journal`, `conference`, `book`, `is_patent` is populated

#### C. Top Publishers / Conferences / Journals (Horizontal Bar)
- Separate tabs: "Top Conferences" | "Top Journals" | "Top Publishers"
- X-axis: count of publications
- Y-axis: venue name (top 10)

#### D. Citation Distribution (Histogram)
- X-axis: citation count buckets (0, 1–10, 11–50, 51–100, 100+)
- Y-axis: number of publications
- Helps understand impact profile

#### E. Top Cited Papers (Ranked Table)
- Columns: Title, Authors, Year, Venue, Citations
- Sortable by citations descending
- Top 20 by default, with pagination

#### F. IIITD vs External Publications (Pie)
- `is_iiitd_publication` true vs false

---

## BACKEND API ENDPOINTS REQUIRED

Create the following new API endpoints, following the existing route and middleware patterns in the codebase:

```
GET  /api/analytics/copo
     Query params: courseTitle?, evaluationType?, fromDate?, toDate?
     Returns: parsed CO/PO attainment data grouped by course, with semester timeline

GET  /api/analytics/projects
     Query params: semester?, projectType?, courseName?, guideId?, specialization?
     Returns: aggregated project stats (counts by semester, faculty load, credit dist, etc.)

GET  /api/analytics/awards
     Query params: facultyName?, year?, category?
     Returns: awards with computed category labels, grouped by faculty and year

GET  /api/analytics/publications
     Query params: year?, type?, isPatent?
     Returns: publication stats grouped by year, type, venue
```

All endpoints:
- Apply existing authentication middleware (same as other protected routes)
- Return JSON with a consistent envelope: `{ success: true, data: {...} }`
- Handle empty results gracefully (return empty arrays, not 404)
- Use parameterised queries / ORM — no raw string interpolation

---

## DASHBOARD PAGE LAYOUT

### URL / Route
`/analytics` — add to sidebar nav with a chart icon, visible to all authenticated users

### Page Structure
```
┌─────────────────────────────────────────────────────┐
│  Analytics Dashboard          [Export PDF]           │
│  Last updated: <timestamp>                           │
├─────────────────────────────────────────────────────┤
│  [Tab: CO/PO] [Tab: Projects] [Tab: Awards] [Tab: Publications] │
├─────────────────────────────────────────────────────┤
│  ┌── KPI Cards Row ──────────────────────────────┐  │
│  │  Card  Card  Card  Card  Card                 │  │
│  └───────────────────────────────────────────────┘  │
│  ┌── Filters Row ────────────────────────────────┐  │
│  │  [Dropdown] [Dropdown] [Date Range] [Reset]   │  │
│  └───────────────────────────────────────────────┘  │
│  ┌── Chart Grid ─────────────────────────────────┐  │
│  │  ┌─────────────┐  ┌─────────────┐             │  │
│  │  │  Chart A    │  │  Chart B    │             │  │
│  │  └─────────────┘  └─────────────┘             │  │
│  │  ┌─────────────────────────────┐              │  │
│  │  │  Chart C (full width)       │              │  │
│  │  └─────────────────────────────┘              │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### Design Requirements
- All charts in **card containers** with a title, optional subtitle, and a "⋯" kebab menu (Download PNG, View Data Table)
- KPI cards: large number, label below, small trend indicator (↑↓ vs previous period) where applicable
- Loading skeleton shimmer while API calls are in-flight
- Empty state illustration + message for sections with no data
- Color palette: use the portal's existing CSS variables — do not hardcode hex values
- Charts must be **responsive** — they resize correctly on window resize
- Tooltips on all data points with clear labels and units
- All charts have accessible `aria-label` attributes

---

## TECHNICAL IMPLEMENTATION NOTES

### Chart Library
Use whatever charting library is already installed in the project. If none exists, install **Recharts** (React) — it is lightweight, composable, and responsive. Do not install both Recharts and Chart.js.

For the heatmap (awards and CO/PO), use either a custom SVG grid or `react-heat-map` package. For the word cloud (project themes), use `react-wordcloud` or fall back to a ranked bar chart if the package causes bundle issues.

### Data Fetching
- Use the existing data-fetching pattern in the codebase (SWR, React Query, useEffect+fetch — whichever is standard)
- Cache analytics responses for 5 minutes client-side — analytics data does not need to be real-time
- Show a subtle "Refreshing..." indicator when re-fetching

### CO/PO result_summary Parsing
The `result_summary` column likely contains a deeply nested JSON structure. Write a dedicated parser utility `parseCoPoResultSummary(json)` that:
1. Extracts CO attainment as `{ CO1: 72, CO2: 85, ... }` (numeric, 0–100)
2. Extracts PO attainment as `{ PO1: 68, PO2: 74, ... }`
3. Returns `null` gracefully if the structure is unexpected
4. Logs a warning (not an error) if keys are missing

Expose this parser in the backend so the API always returns clean, pre-parsed data — the frontend should never need to parse raw JSON blobs.

### Performance
- Analytics queries can be expensive — add a database index on `copo_run_analytics_snapshots(course_title, run_created_at)` if it doesn't already exist
- Similarly index `btp_projects(semesters)` and `faculty_awards(faculty_name, year)`
- Consider a materialized view for frequently queried aggregates if the dataset grows large