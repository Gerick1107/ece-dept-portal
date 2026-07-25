# User management

Portal accounts are stored in the `users` table. CO-PO uploads and evaluation runs reference `user_id` and are **never deleted** when an account is deactivated or removed.

## Roles

| Role | Access |
|------|--------|
| `faculty` | Own linked faculty data across modules; Feedback; Notifications |
| `hod` | Same scoping as faculty for data views; only one HoD at a time; CC on feedback emails |
| `admin` | All modules + user management + feedback resolution |

## Faculty data scoping (important)

Accounts see personal teaching/project/publication slices through **`users.faculty_id`** (FK to `faculty.id`), resolved in `get_faculty_scope`.

- Email is only for login identity.
- Display name is not used for scoping.
- When migrating from temporary emails to institutional emails, **link the new account to the correct faculty directory row** (Users UI dropdown). Name spelling differences do not matter once `faculty_id` is set.
- Leave `faculty_id` empty for non-faculty portal users.

## Admin actions (UI: Admin → Users)

### Create account

- Set email, full name, portal password (min 8 characters).
- Optional role: Faculty / HoD / Admin.
- Optional **faculty directory link**.
- Optional welcome email (requires `SMTP_ENABLED=true`).
- Faculty/HoD accounts are prompted to change password on first login (Profile).
- Creating/marking HoD demotes any existing HoD to faculty.

### Update link / HoD

- Per-user dropdown to set or clear faculty link.
- **Mark HoD** / **Clear HoD** actions.

### Deactivate / Remove profile

Unchanged: deactivate blocks login; remove anonymizes personal fields while retaining CO-PO history by `user_id`.

## Feedback

Faculty submit under `/feedback`. Admins resolve items. SMTP notifies admins + HoD.

## API reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/auth/users` | Create user (admin); accepts `faculty_id` |
| `PATCH` | `/api/v1/auth/users/{id}` | Update role / faculty link / name |
| `GET` | `/api/v1/auth/users` | List active portal accounts (admin) |
| `POST` | `/api/v1/auth/users/{id}/deactivate` | Deactivate |
| `POST` | `/api/v1/auth/users/{id}/activate` | Activate |
| `DELETE` | `/api/v1/auth/users/{id}` | Remove profile (anonymize) |
| `POST` | `/api/v1/auth/forgot-password` | Email temporary password |
| `GET/POST/PATCH` | `/api/v1/feedback` | Feedback list / submit / resolve |

## Database migrations

```powershell
cd backend
alembic upgrade head
```

User–faculty link: migration **034**. Feedback + custom notification templates: **046**.
