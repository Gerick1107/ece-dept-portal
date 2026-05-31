import { FormEvent, useEffect, useState } from "react";
import {
  activateUser,
  createUser,
  deactivateUser,
  listUsers,
  removeUserProfile,
  type User,
  type UserCreate,
} from "../services/api";
import { useAuth } from "../modules/auth/AuthContext";

export default function AdminUsersPage() {
  const { user } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [form, setForm] = useState<UserCreate>({
    email: "",
    full_name: "",
    password: "",
    role: "faculty",
    send_welcome_email: true,
  });

  async function refresh() {
    try {
      setUsers(await listUsers());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load users");
    }
  }

  useEffect(() => {
    if (user?.role === "admin") refresh();
  }, [user]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSuccess("");
    try {
      const created = await createUser(form);
      const emailNote = created.welcome_email_sent
        ? "Welcome email sent with temporary password."
        : "Welcome email not sent (SMTP disabled or failed) — share password manually.";
      setSuccess(`Created account for ${form.email}. ${emailNote}`);
      setForm({ email: "", full_name: "", password: "", role: "faculty", send_welcome_email: true });
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
        <h2 className="text-xl font-semibold">Faculty accounts</h2>
        <ol className="text-sm text-slate-600 mt-2 leading-relaxed list-decimal list-inside space-y-1">
          <li>Add the faculty member&apos;s institutional email and full name.</li>
          <li>Set a portal password here (min. 8 characters) — this is separate from Gmail/Microsoft.</li>
          <li>
            Tick &quot;Send welcome email&quot; if SMTP is configured in <code className="text-xs bg-slate-100 px-1 rounded">.env</code>;
            otherwise note the password and share it with them manually.
          </li>
          <li>On first login, faculty accounts are asked to change this password under Profile.</li>
          <li>
            <strong>Deactivate</strong> blocks login but keeps the account visible. <strong>Remove profile</strong> deletes
            name/email from the portal (CO-PO data is kept) so the same email can be registered again.
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
          <option value="admin">Admin</option>
        </select>
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
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b">
                <td className="py-2">{u.full_name}</td>
                <td>{u.email}</td>
                <td className="capitalize">{u.role}</td>
                <td>{u.is_active ? "Active" : "Inactive"}</td>
                <td className="py-2 text-right">
                  {u.id !== user?.id && (
                    <div className="flex flex-wrap justify-end gap-2">
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
                            setSuccess(`Removed profile for ${u.email}. CO-PO data was retained.`);
                            refresh();
                          } catch (err) {
                            setError(err instanceof Error ? err.message : "Remove profile failed");
                          }
                        }}
                      >
                        Remove profile
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
