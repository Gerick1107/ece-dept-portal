import { FormEvent, useEffect, useState } from "react";
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

  useEffect(() => {
    if (user?.role === "admin") {
      refresh();
      listFaculty({ page: 1, page_size: 300, include_inactive: false })
        .then((r) => setFacultyOptions(r.items))
        .catch(() => {});
    }
  }, [user]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSuccess("");
    try {
      const payload = {
        ...form,
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

  const facultyNameById = Object.fromEntries(facultyOptions.map((f) => [f.id, f.name]));

  return (
    <div className="space-y-6 max-w-4xl">
      <section className="bg-white border rounded-xl p-6">
        <h2 className="text-xl font-semibold">Portal accounts</h2>
        <ol className="text-sm text-slate-600 mt-2 leading-relaxed list-decimal list-inside space-y-1">
          <li>Add the person&apos;s institutional email and full name.</li>
          <li>
            Optionally link the account to an existing faculty directory record (recommended for faculty). Data scoping
            uses this <code className="text-xs bg-slate-100 px-1 rounded">faculty_id</code> link — not the email or an
            exact name match — so spelling differences in names do not matter once linked.
          </li>
          <li>Set a portal password (min. 8 characters) — separate from Gmail/Microsoft.</li>
          <li>Only one user can be HoD at a time; marking someone as HoD demotes the previous HoD to faculty.</li>
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
        <input
          type="password"
          required
          minLength={8}
          placeholder="Portal password (min 8 chars)"
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
          className="w-full border rounded-lg px-3 py-2 text-sm"
        />
        <select
          value={form.role}
          onChange={(e) => setForm({ ...form, role: e.target.value as UserCreate["role"] })}
          className="w-full border rounded-lg px-3 py-2 text-sm"
        >
          <option value="faculty">Faculty</option>
          <option value="hod">HoD (only one at a time)</option>
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

      <section className="bg-white border rounded-xl p-6">
        <h3 className="font-medium mb-3">Existing users</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left border-b text-slate-500">
              <th className="py-1">Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Faculty link</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b align-top">
                <td className="py-2">{u.full_name}</td>
                <td>{u.email}</td>
                <td className="capitalize">{u.role}</td>
                <td className="text-xs text-slate-600">
                  {u.faculty_id ? facultyNameById[u.faculty_id] || `Faculty #${u.faculty_id}` : "—"}
                </td>
                <td>{u.is_active ? "Active" : "Inactive"}</td>
                <td className="py-2 text-right">
                  {u.id !== user?.id && (
                    <div className="flex flex-wrap justify-end gap-2">
                      {u.role !== "hod" ? (
                        <button
                          type="button"
                          className="text-indigo-700 text-xs hover:underline"
                          onClick={async () => {
                            if (
                              !window.confirm(
                                `Mark ${u.full_name} as HoD? Any existing HoD will be demoted to faculty.`
                              )
                            ) {
                              return;
                            }
                            setError("");
                            setSuccess("");
                            try {
                              await updateUser(u.id, { role: "hod" });
                              setSuccess(`${u.full_name} is now HoD.`);
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
                              setSuccess(`${u.full_name} demoted from HoD to faculty.`);
                              refresh();
                            } catch (err) {
                              setError(err instanceof Error ? err.message : "Update failed");
                            }
                          }}
                        >
                          Clear HoD
                        </button>
                      )}
                      <select
                        className="text-xs border rounded px-1 py-0.5 max-w-[10rem]"
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
