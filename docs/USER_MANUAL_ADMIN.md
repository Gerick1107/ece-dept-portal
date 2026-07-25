# Admin User Manual — ECE Department Smart Portal

This guide covers administration of the ECE Department Smart Portal.

## Sign in & roles

| Role | Access |
|------|--------|
| **admin** | Full portal + Admin menu |
| **hod** | Faculty-scoped data views; receives feedback email CC; only one HoD at a time |
| **faculty** | Own linked data + Feedback + Notifications |

## Admin menu

| Page | Purpose |
|------|---------|
| Publications Admin | Publication maintenance |
| Faculty Admin | Faculty directory / Scholar sync |
| **Users** | Create accounts, HoD, faculty links |
| **Send Notifications** | Templates, reminders, custom templates |
| **Requirement Tracker** | Per-faculty requirement status matrix |
| Data & Archives | Data maintenance / archives |

Also use the main **Feedback** tab to review faculty submissions.

## Users (critical for faculty data access)

Faculty **do not** see “their” data because of email or name matching alone.

Scoping uses `users.faculty_id` → `faculty.id`.

When replacing temporary accounts with institutional emails:

1. Create (or remove old and recreate) the account with the real email and a new password.
2. **Link to faculty directory** via the dropdown (optional field, but required for personal data views).
3. Slight differences in typed names are fine — pick the correct directory person from the list.
4. Leave the link empty for staff/admin helpers who should not inherit a faculty’s private teaching/project slice.

### HoD

- Use **Mark HoD** on a user (or set role to HoD when creating).
- Only one HoD is allowed; the previous HoD is demoted to faculty automatically.
- HoD is CC’d on new feedback emails when SMTP is enabled.

## Feedback

1. Faculty submit under **Feedback**.
2. Admins see faculty name, email, timestamp, and message.
3. Mark **resolved / unresolved**; faculty see that status.
4. On submit, SMTP emails go to all active **admins** and the **HoD**.

## Notifications & Requirement Tracker

1. Open **Send Notifications**.
2. Pick a built-in template or a **custom template**.
3. **+ Custom template** saves label/subject/body and creates a new `requirement_type`.
4. The Requirement Tracker gains a matching column automatically.
5. Sending with a requirement type paints recipient tracker cells red (asked); read → yellow; fulfilled → green.
6. Optional automatic email reminders until green (SMTP).

## Course allocation

### Columns

- **UG** / **PG**: each stores Core / Elective / Core/Elective (or blank if not offered at that level).
- First-year tracking has been removed.
- **No. of registered students**: empty after Excel import; **admins edit** via Add/Edit allocation. Faculty cannot change it.

### Reminder banner

For **Monsoon 2026 and later** semesters only, admins see a banner counting courses missing registered-student counts for the summary semester.

### Catalog

Edit UG/PG types on **Course Catalog**; changes propagate to matching allocation rows.

### Import / export

Excel import still derives UG/PG types from the label column; registered students stay blank. Exports include `ug_type`, `pg_type`, and `registered_students`.

## Projects and Theses

Portal table order: Serial Number → Semester → Title → Guide → Actions → remaining columns. **Exports are unchanged.**

## Branding

The product name is **ECE Department Smart Portal** (login, header, emails).

## Migrations after deploy

```powershell
cd backend
alembic upgrade head
```

Relevant revisions: `045_course_alloc_ug_pg_types`, `046_templates_feedback`.

## SMTP

Welcome emails, password resets, notification mail, and feedback alerts require `SMTP_ENABLED=true` and valid SMTP settings in `.env` / `.env.docker`.
