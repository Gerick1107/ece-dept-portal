# Faculty User Manual — ECE Department Smart Portal

Complete reference for faculty (and HoD) accounts. Use this to navigate every feature you can access.

**Related:** [Admin User Manual](USER_MANUAL_ADMIN.md) · [User management (technical)](USER_MANAGEMENT.md)

---

## 1. Getting started

### 1.1 Sign in

1. Open the portal URL provided by the department.
2. Sign in with your **portal email and password** (this is usually *not* your Gmail/Outlook password unless the admin set it that way).
3. On first login (or after a password reset) you are redirected to **Profile** to set a new password.

### 1.2 Forgot password

On the login page, enter your email and click **Forgot password?**. If SMTP is enabled, a temporary password is emailed. Sign in and change it under **Profile**.

### 1.3 What data you can see

Your account may be **linked to a faculty directory record**. That link (`faculty_id`) — not your email spelling or display name — controls which projects, courses, awards, contributions, and similar personal records you see.

- If lists look empty or “not yours,” ask an admin to link your account to the correct faculty entry under **Admin → Users**.
- Admins see department-wide data. HoD accounts keep faculty-style personal scoping for most modules, plus HoD privileges where noted (e.g. budget write access, labs).

### 1.4 Top navigation (overview)

| Nav item | What it opens |
|----------|----------------|
| **Dashboard** | Welcome page and module shortcuts |
| **Feedback** | Send feedback; see resolved / unresolved |
| **CO-PO Attainment** | Generator, Compare, Bulk |
| **Publications** | Directory, Search, Student Publications, Exports |
| **Projects and Theses** | BTP/IP projects + ECE/EVE tab |
| **Budget** | Accumulated Income, Expenditure, Inventory |
| **Course Allocation** | Faculty-wise and Course-wise views (Catalog is admin-only) |
| **Minutes** | All Meetings + Senate / ECE Faculty / AAC / UGC / PGC |
| **Analytics** | Awards, Contributions, Analytics Dashboard |
| **LLM Insights** | AI course insights (local LLM) |
| **Notifications** | Messages from admins (admins use Admin → Send Notifications instead) |
| **Moderation** | Question papers + grading criteria |
| **Lab Seating Capacity** | Lab seats and occupancy |
| **Profile** | Change password |

---

## 2. Dashboard

- Greets you by name and shows your role.
- Shows an unread-notifications shortcut when you have unread messages.
- Module cards link into CO-PO, Publications, Projects, Budget, Course Allocation, Minutes, Analytics, LLM Insights, Moderation, Labs, and Notifications.

---

## 3. Feedback

1. Open **Feedback**.
2. Write a message and click **Submit**.
3. Active admins (and the HoD, when SMTP is on) receive an email asking them to check the portal.
4. Your list shows each submission with date/time and **Resolved** / **Unresolved** status (admins mark status).

Admins do not submit feedback here; they only review it.

---

## 4. Profile

- Change your portal password (current + new password, min 8 characters).
- Required after first login / reset when “must change password” is set.

---

## 5. CO-PO Attainment

Menu: **CO-PO Attainment**.

### 5.1 CO-PO Generator (`/copo`)

End-of-semester **Workflow A**: one consolidated marks Excel per course.

Typical steps:

1. Select (or add) the **course**.
2. Ensure the department **CO-PO mapping** for that course is available.
3. Upload **one consolidated marks `.xlsx`** (all assessments as columns).
4. Optionally set year, section, programme/branch filters, and indirect CO values.
5. Choose whether to save the run to the database and/or delete server marks after success.
6. Click generate to produce CO / PO / PSO tables and download the result Excel.
7. Open the results page for that run to review or delete evaluation data if permitted.

Also available: download a marks **template** when provided by the UI.

### 5.2 Compare Evaluation (`/copo/compare`)

Single-course QA compare:

1. Upload mapping / marks as required by the form.
2. Search and select the course.
3. Provide comparison labels/values (e.g. thresholds).
4. Generate side-by-side CO and PO comparison tables.

### 5.3 Bulk Evaluation (`/copo/bulk`)

Compare multiple courses in one session:

1. Optionally upload one custom mapping for all rows.
2. For each row: upload an input sheet (auto-detects programme/branch/COs), select course, set labels.
3. **Add another course** as needed.
4. Run bulk compare and expand per-course CO/PO tables.

---

## 6. Publications

Menu: **Publications**.

### 6.1 Faculty Directory (`/publications/faculty`)

- Browse faculty cards/list (search / filters as shown).
- Open a faculty profile for publications and related tabs.

### 6.2 Faculty profile (`/publications/faculty/:id`)

Depending on access, you may see tabs such as:

- Publications overview  
- Journals  
- Conferences  
- Book Chapters  
- Books  
- Preprints & Unlisted  
- Patents  

Also: **Affiliations** (`/publications/faculty/:id/affiliations`) for affiliation history.

**Faculty / HoD / Admin** can typically:

- Edit publication metadata (venue, pages, volume, etc.). Manual edits are preserved against future sync.
- Delete a publication (with confirmation). Deleted items are blocked from re-import.

Your own profile is editable when your account is linked to that faculty id; admins can manage more broadly.

### 6.3 Publications Search (`/publications/search`)

Global search across publications (e.g. by title or venue). Open results and edit/delete when permitted.

### 6.4 Student Publications (`/publications/student`)

Shared student publication table:

- Browse / filter the list.
- **Download Excel template** (all signed-in users).
- **Admin only:** Import Excel, add rows, delete rows, and manage dynamic columns.

### 6.5 Publication Exports (`/publications/exports`)

Export publications and/or patents:

- Choose faculty, year or date ranges, type (publications / patents / both).
- Download CSV/Excel as offered.
- **Custom template export:** upload your own header template → analyze column mapping (optional LLM assist) → confirm mapping → compile and download.

---

## 7. Projects and Theses (`/projects`)

Two tabs:

1. **Projects and Theses** (main BTP/IP-style projects)  
2. **ECE/EVE Projects**

### 7.1 Filters and list

Filter by search text, guide, co-guide, project type, semester (multi-select), course code/name, credit, etc. Paginated table.

**UI column order (portal):** Serial Number → Semester → Title → Guide → Actions → SDGs → Course Code → Course Name → Co-Guide → Student Roll → Student Name → Credit.

Excel **exports** keep the export-oriented column layout (not necessarily the same as the on-screen order).

### 7.2 SDGs

- Suggested SDGs may appear from the model (when LLM is enabled).
- **Review SDGs / Edit SDGs** from Actions: select/deselect among all 17 SDGs, accept or reject.
- Accepted / confirmed rows are highlighted.
- **Regenerate** when available to re-run suggestions.
- **Bulk accept SDGs** (when available): choose guide + semester range, preview pending projects, accept auto-suggested SDGs ≥ 50% confidence for that guide.

### 7.3 Import / export / edit

- Download import **template**.
- **Import** Excel (faculty and admin). You pick the semester tag for the file; the Semester column in Excel may be ignored as stated in the import dialog.
- **Export XLSX**.
- **Bulk accept SDGs** (when shown): guide + semester range → preview → accept suggestions ≥ 50% confidence.
- Admin: **Edit** / **Delete** individual projects; **Delete all** projects; add project via form.

### 7.4 ECE/EVE tab

Separate list of ECE/EVE projects with similar filters (guide, co-guide, semester, etc.). Data is maintained in sync with main projects where the system mirrors them.

---

## 8. Budget

Menu: **Budget**. Anyone signed in can **view**. Create / update / delete and invoice uploads generally require **HoD** (or admin).

### 8.1 Accumulated Income

Budget heads by financial year: approved amount, utilised, remaining. Optional invoice PDF upload when you have write access.

### 8.2 Expenditure Budget

Expense heads, utilisation, vendor, status, invoices. Add/edit/delete when permitted.

### 8.3 Inventory

Items, category, quantity on hand / issued, location, invoices. Manage when permitted.

---

## 9. Course Allocation

Menu: **Course Allocation**. Faculty see **Faculty-Wise** and **Course-Wise** only (your linked teaching data). **Course Catalog** is admin-only and hidden from faculty nav.

### 9.1 Faculty-Wise Allocations (`/course-allocation`)

- Summary for the selected semester (faculty teaching, course counts, UG/PG splits).
- Scope: by **semester**, by **academic year**, or **all data**.
- Search; filter **UG** type and **PG** type separately: all / Core / Elective / Core/Elective.
- Expand a faculty row to see courses: Semester, Code, Course, UG, PG, Number Of Registered Students.
- Open a faculty name for full history and charts (`/course-allocation/faculty/:id`).
- Export Excel when available.

Faculty cannot edit allocations or registered-student counts.

### 9.2 Course-Wise Allocations (`/course-allocation/courses`)

Same filters/summary idea, grouped by course. Drill into course history (`/course-allocation/course/:id`).

### 9.3 Columns to know

| Column | Meaning |
|--------|---------|
| **UG** | Type at UG level (Core / Elective / Core/Elective) or blank if not UG |
| **PG** | Type at PG level, same idea |
| **Number Of Registered Students** | Filled by admins only; blank after Excel import |

---

## 10. Minutes (meeting documents)

Menu: **Minutes**.

| Page | Path |
|------|------|
| All Meetings | `/all-meetings` |
| Senate Meetings | `/senate-minutes` |
| ECE Faculty Meetings | `/ece-faculty-meets` |
| AAC Meetings | `/aac-meetings` |
| UGC Meetings | `/ugc-meetings` |
| PGC Meetings | `/pgc-meetings` |

Common features:

- Browse meetings grouped by **year**.
- Download **agenda** and/or **minutes** PDFs when present.
- **Ask questions** (RAG chat) against the document set for that meeting type — multi-turn Q&A with sources/chunks when the local LLM is configured.
- Admins upload/replace PDFs and meeting metadata (title, date, description).

---

## 11. Analytics group

### 11.1 Faculty Awards (`/awards`)

- Browse awards grouped by faculty.
- Filter by search, year, exact year, faculty.
- Export Excel (optional year range / faculty selection in the export dialog).
- Admin: add / edit / delete awards.

Faculty typically view (and may be scoped); admins maintain records.

### 11.2 Faculty Contributions (`/contributions`)

Sub-tabs (examples):

- Resource Person (STTP/FDP)  
- MOOC / SWAYAM Development  
- Dept. Organized FDPs/STPs  
- Student Project Support  
- Internships / Collaborations  
- Professional Memberships  
- Faculty Services  
- PhD Students  

Per tab: search, year filters, faculty filter, Excel export. Admin add/edit/delete and name resolution where shown. Legacy `/fdps` redirects here.

### 11.3 Analytics Dashboard (`/analytics`)

Tabs such as:

- **CO-PO** — attainment analytics / run comparisons  
- **Projects** — theme and guide distributions, filters by project type  
- **ECE/EVE Projects** — related analytics  
- **Awards** — category charts and tables  
- **Publications** — publication KPIs and tables  

Use filters/charts as shown on each tab.

---

## 12. LLM Insights (`/llm-insights`)

1. Select a **course** that has stored evaluation data.
2. Choose **current** and optional **previous** semester (and section if offered).
3. Review assessment structure used for the prompt.
4. **Generate** AI recommendations (local Ollama). Cached insights may load automatically.
5. Switch LLM provider only if the page exposes a provider selector and your deployment allows it.

Requires the local LLM stack to be running as configured by IT.

---

## 13. Notifications (`/notifications`)

Faculty inbox (admins send from **Admin → Send Notifications**).

1. Open a message to read it (tracker may move Red → Yellow).
2. Download attachments.
3. **Reply** with text and optional file (≤ 10 MB typical limit).
   - Reply **with attachment** often marks the related requirement **green** (fulfilled).
   - Text-only reply often marks **yellow** (read / awaiting review).
4. Mark all read when available.
5. Unread count appears on the dashboard.

Automatic email reminders may repeat until the Requirement Tracker cell is green (SMTP).

---

## 14. Moderation (`/moderation`)

Two tabs:

### 14.1 Question papers

- List courses used for moderation.
- Open a course to see uploaded papers (`/moderation/courses/:courseId`).
- Faculty / HoD / Admin: **upload** question papers (metadata as required).
- Admin: delete papers / manage courses as shown.

### 14.2 Grade summary

- Define / edit **grading criteria** per course (faculty / HoD / Admin).
- Admin may have extra delete controls.

---

## 15. Lab Seating Capacity (`/labs`)

- View labs: name, location, faculty in charge, total / allotted / remaining seats, occupancy bar, remarks.
- Filter by faculty or search.
- Summary KPIs: total labs, seats, allotted, remaining, occupancy %.
- **Admin / HoD:** add or edit labs.
- **Admin:** delete labs.

---

## 16. HoD notes (if you are marked HoD)

Your role displays as **Faculty · HoD**. In practice:

- You still have a faculty directory link for personal data scoping.
- You receive **feedback** notification emails (CC) when SMTP is on.
- You typically have **write** access on Budget and can manage Labs (with admin).
- Only one HoD exists at a time; admins assign this from **Users**.

---

## 17. Quick troubleshooting

| Symptom | What to try |
|---------|-------------|
| Empty projects / courses / awards | Ask admin to set your **faculty link** |
| Login works but forced to Profile | Change the temporary password |
| Forgot password does nothing useful | SMTP may be off — contact admin for a reset |
| Notifications not emailed | SMTP configuration; portal inbox still works |
| LLM Insights / Minutes Q&A fail | Local LLM (Ollama) may be down |
| Cannot edit budget / labs | Need HoD or Admin privileges |

---

*End of Faculty User Manual.*
