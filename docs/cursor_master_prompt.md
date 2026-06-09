# Cursor Master Prompt — Portal Feature Updates

You are working on an academic portal (likely built with a web framework + PostgreSQL). Below are 8 clearly scoped feature requests. Implement them one by one, carefully, without breaking existing functionality. Read all existing relevant files before making any changes.

---

## 1. CO-PO Attainment Graphs on Generator Dashboard

**Context:**
The Analytics tab already shows CO and PO attainment graphs, pulling data from the `copo_run_analytics_snapshots` table. The Generator/Dashboard page runs CO-PO evaluations and currently only shows attainment tables after a run.

**What to do:**
- After a CO-PO attainment generation/evaluation run completes on the Generator Dashboard, render the same attainment graphs (CO attainment bar chart + PO attainment bar chart) immediately below or beside the attainment tables for that specific evaluation run.
- Reuse the same charting components and data-fetching logic already used in the Analytics tab — do not duplicate logic, just pass the relevant `run_id` or snapshot data.
- Query `copo_run_analytics_snapshots` filtered by the current evaluation run's ID to get graph data.
- Graphs are for display only (no interactivity required beyond what already exists in Analytics).
- Ensure graphs appear only after a successful generation, not before.

---

## 2. Colour Coding: Blue → Red Gradient (Analytics Tab)

**Context:**
The Analytics tab currently uses greenish-blue shades throughout all graphs and heatmaps, making it hard to distinguish high vs low values visually.

**What to do:**
- Replace the existing monochromatic greenish-blue colour scheme in the Analytics tab with a **blue → red diverging colour scale**:
  - Low values → Blue
  - Mid values → White or Yellow (neutral midpoint)
  - High values → Red
- Apply this to all heatmaps, bar charts, and any colour-coded cells/tables in the Analytics tab.
- Use a well-known diverging palette (e.g., D3's `RdYlBu` reversed, or CSS/Tailwind equivalent). Be consistent across all chart types.
- Do not change colours anywhere outside the Analytics tab unless explicitly mentioned elsewhere in this prompt.

---

## 3. SDG Assignment — Confidence Threshold Logic

**Context:**
Currently the portal picks and displays only the top 5 SDGs for each project. The Review SDGs tab shows these SDGs. When SDGs are added/confirmed, they are stored without confidence rates being visible.

**What to do:**

### Backend:
- Change the SDG assignment logic: instead of selecting only top 5, assign **all SDGs with a confidence score ≥ 50%** to the project.
- There is no fixed upper limit — a project could have 1 SDG or 10, depending on the model's output.

### Review SDGs Tab:
- Display **all 17 SDGs** that were evaluated, along with their confidence percentages.
- Clearly distinguish which ones are above the 50% threshold (i.e., auto-assigned) vs below (for reference).
- Allow the reviewer to manually override — add or remove SDGs regardless of threshold.

### After SDG is Added/Confirmed:
- Wherever SDGs are displayed (project cards, project detail pages, faculty directory, etc.), show the **confidence rate (%)** alongside each SDG label/badge.
- Example: `SDG 4: Quality Education (78%)`

### Important:
- Do not break existing SDG storage or display logic — extend it.
- Confidence values must be persisted in the database alongside the SDG assignment (add a `confidence` column to the SDG-project mapping table if not already present).

---

## 4. Faculty Awards — Add `exact_year` and `awarded_by` Columns

**Context:**
The `faculty_awards` table in the database is missing two columns: `exact_year` and `awarded_by`. The file `data/assets/faculty_awards.csv` contains these columns with values filled for all existing entries.

**What to do:**

### Database Migration:
- Add `exact_year` (integer or varchar) and `awarded_by` (varchar/text) columns to the `faculty_awards` table.
- Write a migration script that reads `data/assets/faculty_awards.csv` and backfills these two columns for all existing rows, matching on a reliable unique key (e.g., faculty ID + award name or row order — inspect the CSV and table to determine the best join key).
- Do not delete or alter any existing columns.

### Backend:
- Update all queries, models, and serializers that reference `faculty_awards` to include `exact_year` and `awarded_by`.

### Frontend — Faculty Awards Dashboard:
- Display `awarded_by` as a new column labelled **"Awarding Agency / Awarded By"** in the awards table.
- Display `exact_year` as a new column labelled **"Year"**.
- Add a **year filter** (dropdown or range selector) to allow filtering awards by `exact_year` — apply this filter to both the table view and any export functionality.

### Frontend — Analytics Dashboard (Awards section):
- Reflect the new columns in any awards-related analytics views.
- If there is a chart or breakdown by year, ensure it uses `exact_year` (not a derived or approximate year field).

### Export:
- Ensure CSV/Excel exports of faculty awards include `exact_year` and `awarded_by` columns.
- The year filter should also affect what gets exported (i.e., export respects active filters).

---

## 5. Analytics — SDG & Theme Improvements for ECE Department (Projects Tab)

**Context:**
The Projects tab in the Analytics Dashboard currently has a "theme" analytics graph with generic labels (e.g., "learning", "development"). There is no SDG-level analytics yet.

**What to do:**

### SDG Analytics (New):
- Add a new chart/graph in the Projects analytics tab: **"Projects by SDG"**
- Show all 17 SDGs on the X-axis (or as horizontal bars), with the count of projects mapped to each SDG on the Y-axis.
- Use the SDG-project mapping table as the data source.
- Use official SDG colours or the blue→red scheme from Feature #2 — be consistent with the rest of the Analytics tab post-update.

### Theme Analytics (Update):
- Review the existing theme labels used in the theme analytics graph.
- Replace generic labels like "learning", "development", "technology" etc. with **ECE-relevant themes**, such as:
  - VLSI & Embedded Systems
  - Signal Processing & Communications
  - Power Electronics & Energy Systems
  - IoT & Wireless Networks
  - Control Systems & Robotics
  - Analog & Digital Circuits
  - RF & Microwave Engineering
  - Machine Learning for ECE Applications
  - Biomedical Electronics
  - Semiconductor Devices
- Map existing projects to these new theme labels. If themes are stored in the DB, update the seed/reference data. If they are hardcoded in the frontend, update the labels there.
- Do not remove existing project-theme associations — re-map them to the new label set.

---

## 6. Rename "Venue" → "Venue / Journal" Across the Portal

**Context:**
The term "Venue" is used throughout the portal (publications sections, analytics dashboards, faculty directory, etc.) but is only semantically correct for conferences. For journals, the correct term is "Journal". The unified correct label is **"Venue / Journal"**.

**What to do:**
- Do a thorough find-and-replace across the **frontend only** (labels, column headers, filter labels, form field labels, export headers, placeholder text):
  - Replace all display instances of `"Venue"` (case-insensitive, standalone label) with `"Venue / Journal"` in:
    - Publications tab / table
    - Analytics Dashboard (publications section)
    - Faculty Directory (publications view)
    - Any export column headers
    - Any form inputs or filters labelled "Venue"
- Do **not** rename database columns, API field names, or variable names in backend code — only user-facing display strings.
- Be careful not to replace occurrences of "venue" that are part of unrelated strings.

---

## 7. Remove Notifications Tab for Admin Login (Keep Faculty Login Unchanged)

**Context:**
- **Faculty login**: Has a Notifications tab — keep it exactly as-is, no changes.
- **Admin login**: Has two tabs — "Notifications" and "Send Notifications". The "Notifications" tab for admin is redundant. The homepage notification button for admin currently links to the Notifications tab.

**What to do:**
- Remove the **"Notifications" tab** from the admin navigation/sidebar — admin should only see "Send Notifications".
- Update the **homepage notification button/icon** for admin so it links directly to the **Send Notifications** page instead of the now-removed Notifications tab.
- Do not touch anything related to the faculty login's notification UI, routes, or logic.
- Ensure no broken links or missing routes remain after removal.

---

## 8. Notification Templates for Admin — Send Notifications Page

**Context:**
The admin's "Send Notifications" page currently requires the admin to type out reminder messages manually when emailing faculty.

**What to do:**
- Add a **"Use a Template"** section or button on the Send Notifications page.
- When clicked, show a modal or dropdown with the following pre-written templates (editable before sending):

---

**Template 1 — Request for Raw Mark Sheets**
> Subject: Request for Raw Mark Sheets — [Semester / Course Name]
>
> Dear [Faculty Name],
>
> This is a reminder to please submit the raw mark sheets for [Course Code / Semester] at your earliest convenience. These are required for the CO-PO attainment process.
>
> Kindly upload them to the portal or send them to the department office by [Deadline Date].
>
> Thank you.

---

**Template 2 — Request for CO-PO Attainment Data**
> Subject: CO-PO Attainment Data Submission — [Academic Year]
>
> Dear [Faculty Name],
>
> We require the CO-PO attainment data for your courses for the academic year [Year]. Please log in to the portal and complete the attainment generation for all your assigned courses.
>
> Deadline: [Date]
>
> Please reach out if you need any assistance.

---

**Template 3 — Request for Signature on Document**
> Subject: Signature Required — [Document Name]
>
> Dear [Faculty Name],
>
> Kindly review and sign the attached document: [Document Name]. This is required for [Purpose / Context].
>
> Please return the signed copy to [Contact / Office] by [Date].
>
> Thank you for your prompt attention.

---

**Template 4 — Profile / Publication Update Reminder**
> Subject: Reminder to Update Your Faculty Profile
>
> Dear [Faculty Name],
>
> This is a gentle reminder to update your faculty profile on the portal, including any recent publications, awards, funded projects, or professional achievements.
>
> Keeping your profile current ensures accurate departmental reports and accreditation data.
>
> Please complete your updates by [Date].

---

**Template 5 — Upcoming Deadline Reminder**
> Subject: Upcoming Deadline — [Task / Submission Name]
>
> Dear [Faculty Name],
>
> This is a reminder that the deadline for [Task Description] is approaching on [Date]. Please ensure that all required submissions are completed on time through the portal.
>
> Contact the admin office if you have any questions.

---

**Template 6 — NBA / Accreditation Data Request**
> Subject: Data Submission Required for NBA/Accreditation
>
> Dear [Faculty Name],
>
> As part of our ongoing NBA/Accreditation preparation, we require the following data from you: [List of required items].
>
> Please submit this through the portal or directly to the department office by [Deadline].
>
> Your timely cooperation is highly appreciated.

---

**Implementation Notes for Templates:**
- Templates should be selectable from a list; clicking one populates the message body (and subject if applicable) in the compose area.
- Placeholders like `[Faculty Name]`, `[Date]`, `[Course Code]` should be highlighted or marked so the admin knows what to fill in.
- Admin must be able to edit the template freely before sending.
- Templates should not auto-send — they just pre-fill the form.
- Optionally, store templates in the DB or as a config file so they can be updated without a code deployment.

---

## General Instructions for All Changes

- **Read before writing**: Before modifying any file, read the existing implementation to understand the current structure.
- **No regressions**: Do not break any existing functionality while implementing these features.
- **Consistent UI**: Match the existing design system (spacing, font sizes, component library) unless explicitly told to change it.
- **Database migrations**: Write proper migration scripts (not raw SQL patches) for any schema changes.
- **Comments**: Add short inline comments for any non-obvious logic you add.
- **Test edge cases**: Consider empty states (no awards, no SDGs above threshold, no runs yet) and handle them gracefully in the UI.
