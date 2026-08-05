import { FormEvent, useEffect, useState } from "react";
import PasswordField from "../components/PasswordField";
import {
  activateUser,
  createUser,
  deactivateUser,
  listUsers,
  removeUserProfile,
  updateUser,
  type User,
  type UserCreate,
} from "../services/api";
import { useAuth } from "../modules/auth/AuthContext";
import { listFaculty } from "../modules/publications/services/publicationsApi";
import type { Faculty } from "../modules/publications/types/publications";

function roleLabel(role: User["role"]): string {
  if (role === "hod") return "Faculty · HoD";
  if (role === "admin") return "Admin";
  return "Faculty";
}

export default function AdminUsersPage() {
  const { user } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [facultyOptions, setFacultyOptions] = useState<Faculty[]>([]);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [form, setForm] = useState<UserCreate>({
    email: "",
    full_name: "",
    password: "",
    role: "faculty",
    send_welcome_email: true,
    faculty_id: null,
  });

  async function refresh() {
    try {
      setUsers(await listUsers());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load users");
    }
  }

  async function loadFacultyOptions() {
    try {
      // API enforces page_size <= 200; requesting more caused a silent 422 and empty dropdowns.
      const first = await listFaculty({ page: 1, page_size: 200, include_inactive: false });
      let items = [...first.items];
      const total = first.pagination?.total ?? items.length;
      if (total > items.length) {
        const second = await listFaculty({ page: 2, page_size: 200, include_inactive: false });
        items = items.concat(second.items);
      }
      items.sort((a, b) => a.name.localeCompare(b.name));
      setFacultyOptions(items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load faculty directory for linking");
      setFacultyOptions([]);
    }
  }

  useEffect(() => {
    if (user?.role === "admin") {
      refresh();
      loadFacultyOptions();
    }
  }, [user]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSuccess("");
    try {
      const payload = {
        ...form,
        role: form.role === "admin" ? ("admin" as const) : ("faculty" as const),
        faculty_id: form.faculty_id || null,
      };
      const created = await createUser(payload);
      const emailNote = created.welcome_email_sent
        ? "Welcome email sent with temporary password."
        : "Welcome email not sent (SMTP disabled or failed) — share password manually.";
      const linkNote = form.faculty_id
        ? " Linked to faculty directory for data scoping."
        : " No faculty link — they will not see personal teaching/project data until linked.";
      setSuccess(`Created account for ${form.email}. ${emailNote}${linkNote}`);
      setForm({ email: "", full_name: "", password: "", role: "faculty", send_welcome_email: true, faculty_id: null });
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    }
  }

  if (user?.role !== "admin") {
    return <p className="text-red-700">Admin access only.</p>;
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <section className="bg-white border rounded-xl p-6">
        <h2 className="text-xl font-semibold">Portal accounts</h2>
        <ol className="text-sm text-slate-600 mt-2 leading-relaxed list-decimal list-inside space-y-1">
          <li>Add the person&apos;s institutional email and full name.</li>
          <li>
            Optionally link the account to an existing faculty directory record (recommended for faculty). Data scoping
            uses this link — not the email or an exact name match.
          </li>
          <li>Set a portal password (min. 8 characters) — separate from Gmail/Microsoft.</li>
          <li>
            Create accounts as Faculty or Admin only. Use <strong>Mark HoD</strong> in the list below to give a faculty
            member the HoD designation (only one at a time; they remain a faculty account with HoD privileges).
          </li>
        </ol>
      </section>

      {error && <p className="text-sm text-red-700 bg-red-50 rounded px-3 py-2">{error}</p>}
      {success && <p className="text-sm text-green-800 bg-green-50 rounded px-3 py-2">{success}</p>}

      <form onSubmit={onSubmit} className="bg-white border rounded-xl p-6 space-y-3">
        <h3 className="font-medium">Add user</h3>
        <input
          type="email"
          required
          placeholder="Email (e.g. faculty@iiitd.ac.in)"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
          className="w-full border rounded-lg px-3 py-2 text-sm"
        />
        <input
          required
          placeholder="Full name"
          value={form.full_name}
          onChange={(e) => setForm({ ...form, full_name: e.target.value })}
          className="w-full border rounded-lg px-3 py-2 text-sm"
        />
        <PasswordField
          required
          minLength={8}
          placeholder="Portal password (min 8 chars)"
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
          className="text-sm"
          autoComplete="new-password"
        />
        <select
          value={form.role === "admin" ? "admin" : "faculty"}
          onChange={(e) => setForm({ ...form, role: e.target.value as "faculty" | "admin" })}
          className="w-full border rounded-lg px-3 py-2 text-sm"
        >
          <option value="faculty">Faculty</option>
          <option value="admin">Admin</option>
        </select>
        <div>
          <label className="text-xs text-slate-500">Link to faculty directory (optional)</label>
          <select
            value={form.faculty_id ?? ""}
            onChange={(e) =>
              setForm({ ...form, faculty_id: e.target.value ? Number(e.target.value) : null })
            }
            className="w-full border rounded-lg px-3 py-2 text-sm"
          >
            <option value="">— Not linked (staff / other access) —</option>
            {facultyOptions.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
                {f.department ? ` · ${f.department}` : ""}
              </option>
            ))}
          </select>
          {!facultyOptions.length && (
            <p className="text-xs text-amber-700 mt-1">
              No faculty directory names loaded. Check Faculty Admin / CSV sync, then refresh this page.
            </p>
          )}
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.send_welcome_email !== false}
            onChange={(e) => setForm({ ...form, send_welcome_email: e.target.checked })}
          />
          Send welcome email with temporary password (requires SMTP in .env)
        </label>
        <button type="submit" className="rounded bg-indigo-700 text-white px-4 py-2 text-sm font-medium">
          Create account
        </button>
      </form>

      <section className="bg-white border rounded-xl p-6 overflow-x-auto">
        <h3 className="font-medium mb-3">Existing users</h3>
        <table className="w-full text-sm min-w-[720px]">
          <thead>
            <tr className="text-left border-b text-slate-500">
              <th className="py-1">Name</th>
              <th>Email</th>
              <th>Role</th>
              <th className="min-w-[12rem]">Faculty link</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b align-top">
                <td className="py-2">{u.full_name}</td>
                <td>{u.email}</td>
                <td>{roleLabel(u.role)}</td>
                <td className="py-2">
                  {u.id === user?.id ? (
                    <span className="text-xs text-slate-400">—</span>
                  ) : (
                    <select
                      className="border rounded px-2 py-1 text-xs w-full max-w-[14rem]"
                      value={u.faculty_id ?? ""}
                      onChange={async (e) => {
                        setError("");
                        try {
                          if (!e.target.value) {
                            await updateUser(u.id, { clear_faculty_id: true });
                          } else {
                            await updateUser(u.id, { faculty_id: Number(e.target.value) });
                          }
                          setSuccess(`Updated faculty link for ${u.email}.`);
                          refresh();
                        } catch (err) {
                          setError(err instanceof Error ? err.message : "Link update failed");
                        }
                      }}
                    >
                      <option value="">No faculty link</option>
                      {facultyOptions.map((f) => (
                        <option key={f.id} value={f.id}>
                          {f.name}
                        </option>
                      ))}
                    </select>
                  )}
                </td>
                <td>{u.is_active ? "Active" : "Inactive"}</td>
                <td className="py-2 text-right">
                  {u.id !== user?.id && (
                    <div className="flex flex-wrap justify-end gap-2">
                      {u.role !== "admin" &&
                        (u.role !== "hod" ? (
                          <button
                            type="button"
                            className="text-indigo-700 text-xs hover:underline"
                            onClick={async () => {
                              if (
                                !window.confirm(
                                  `Mark ${u.full_name} as HoD? They keep faculty access and gain HoD designation. Any existing HoD is cleared.`
                                )
                              ) {
                                return;
                              }
                              setError("");
                              setSuccess("");
                              try {
                                await updateUser(u.id, { role: "hod" });
                                setSuccess(`${u.full_name} is now Faculty · HoD.`);
                                refresh();
                              } catch (err) {
                                setError(err instanceof Error ? err.message : "Update failed");
                              }
                            }}
                          >
                            Mark HoD
                          </button>
                        ) : (
                          <button
                            type="button"
                            className="text-slate-600 text-xs hover:underline"
                            onClick={async () => {
                              try {
                                await updateUser(u.id, { role: "faculty" });
                                setSuccess(`${u.full_name} is now Faculty only (HoD cleared).`);
                                refresh();
                              } catch (err) {
                                setError(err instanceof Error ? err.message : "Update failed");
                              }
                            }}
                          >
                            Clear HoD
                          </button>
                        ))}
                      {u.is_active ? (
                        <button
                          type="button"
                          className="text-amber-700 text-xs hover:underline"
                          onClick={async () => {
                            if (!window.confirm(`Deactivate ${u.full_name}? They cannot log in until reactivated.`)) {
                              return;
                            }
                            setError("");
                            setSuccess("");
                            try {
                              await deactivateUser(u.id);
                              setSuccess(`Deactivated ${u.email}.`);
                              refresh();
                            } catch (err) {
                              setError(err instanceof Error ? err.message : "Deactivate failed");
                            }
                          }}
                        >
                          Deactivate
                        </button>
                      ) : (
                        <button
                          type="button"
                          className="text-teal-700 text-xs hover:underline"
                          onClick={async () => {
                            setError("");
                            setSuccess("");
                            try {
                              await activateUser(u.id);
                              setSuccess(`Activated ${u.email}.`);
                              refresh();
                            } catch (err) {
                              setError(err instanceof Error ? err.message : "Activate failed");
                            }
                          }}
                        >
                          Activate
                        </button>
                      )}
                      <button
                        type="button"
                        className="text-red-700 text-xs hover:underline"
                        onClick={async () => {
                          if (
                            !window.confirm(
                              `Remove profile for ${u.full_name} (${u.email})? Personal data is deleted and login is disabled, but CO-PO uploads and runs are kept. The same email can be registered again later.`
                            )
                          ) {
                            return;
                          }
                          setError("");
                          setSuccess("");
                          try {
                            await removeUserProfile(u.id);
                            setSuccess(`Removed profile for ${u.email}.`);
                            refresh();
                          } catch (err) {
                            setError(err instanceof Error ? err.message : "Remove failed");
                          }
                        }}
                      >
                        Remove
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
