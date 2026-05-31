# User management

Portal accounts are stored in the `users` table. CO-PO uploads and evaluation runs reference `user_id` and are **never deleted** when an account is deactivated or removed.

## Roles

| Role | Access |
|------|--------|
| `faculty` | CO-PO, publications (own views), BTP/IP projects |
| `hod` | Same as faculty (department views as configured) |
| `admin` | All modules + user management |

## Admin actions (UI: Admin → Users)

### Create account

- Set email, full name, portal password (min 8 characters).
- Optional welcome email (requires `SMTP_ENABLED=true` in `backend/.env`).
- Faculty accounts are prompted to change password on first login (Profile).

### Deactivate

- Sets `is_active=false`.
- User cannot log in; name and email remain in the user list.
- **Activate** restores login with the same password.

### Remove profile

- Permanently removes personal data from the portal account:
  - Email replaced with an internal `removed.{id}.*@portal.removed` address (frees the original email).
  - Full name set to `Removed user`.
  - Password invalidated; account hidden from the user list.
- **CO-PO uploads, runs, and files are retained** (linked by the same internal `user_id`).
- The same institutional email and name can be used to **create a new account** later.

### Restrictions

- Admins cannot deactivate, activate, or remove **their own** account.
- The **only remaining admin** cannot be deactivated or removed.

## Forgot password (login page)

1. User enters a **valid email** (browser validation, same as sign-in).
2. Clicks **Forgot password?**
3. If the account exists and is active, the API sets a temporary password and emails it (SMTP required).
4. Response is always generic: *"If the account exists, a temporary password has been sent to email."*
5. User signs in with the temporary password and changes it under **Profile**.

## API reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/auth/users` | Create user (admin) |
| `GET` | `/api/v1/auth/users` | List active portal accounts (admin) |
| `POST` | `/api/v1/auth/users/{id}/deactivate` | Deactivate |
| `POST` | `/api/v1/auth/users/{id}/activate` | Activate |
| `DELETE` | `/api/v1/auth/users/{id}` | Remove profile (anonymize) |
| `POST` | `/api/v1/auth/forgot-password` | Email temporary password |

## Database migration

User removal tracking uses column `users.profile_removed` (migration **005**).

```powershell
cd backend
alembic upgrade head
```
