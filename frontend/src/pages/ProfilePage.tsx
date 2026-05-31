import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiPostJson } from "../services/api";
import { useAuth } from "../modules/auth/AuthContext";

export default function ProfilePage() {
  const { user, refresh } = useAuth();
  const navigate = useNavigate();
  const [current, setCurrent] = useState("");
  const [newPass, setNewPass] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSuccess("");
    if (newPass !== confirm) {
      setError("New passwords do not match");
      return;
    }
    try {
      await apiPostJson("/auth/change-password", {
        current_password: current,
        new_password: newPass,
      });
      setSuccess("Password updated successfully.");
      setCurrent("");
      setNewPass("");
      setConfirm("");
      await refresh();
      if (user?.must_change_password) {
        navigate("/copo");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  }

  return (
    <div className="max-w-lg space-y-6">
      <section className="bg-white border rounded-xl p-6">
        <h2 className="text-xl font-semibold">Profile</h2>
        <p className="text-sm text-slate-600 mt-1">{user?.full_name}</p>
        <p className="text-sm text-slate-500">{user?.email} · {user?.role}</p>
        {user?.must_change_password && (
          <p className="mt-3 text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded px-3 py-2">
            You must change your temporary password before continuing.
          </p>
        )}
      </section>

      <form onSubmit={onSubmit} className="bg-white border rounded-xl p-6 space-y-4">
        <h3 className="font-medium">Change password</h3>
        {error && <p className="text-sm text-red-700 bg-red-50 rounded px-3 py-2">{error}</p>}
        {success && <p className="text-sm text-green-800 bg-green-50 rounded px-3 py-2">{success}</p>}
        <input
          type="password"
          required
          placeholder="Current password"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
          className="w-full border rounded-lg px-3 py-2 text-sm"
        />
        <input
          type="password"
          required
          minLength={8}
          placeholder="New password (min 8 characters)"
          value={newPass}
          onChange={(e) => setNewPass(e.target.value)}
          className="w-full border rounded-lg px-3 py-2 text-sm"
        />
        <input
          type="password"
          required
          minLength={8}
          placeholder="Confirm new password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          className="w-full border rounded-lg px-3 py-2 text-sm"
        />
        <button type="submit" className="rounded bg-indigo-700 text-white px-4 py-2 text-sm font-medium">
          Update password
        </button>
      </form>
    </div>
  );
}
