import { useCallback, useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import {
  fetchAdminNotificationDetail,
  fetchAdminNotifications,
  fetchAdminRecipientOptions,
  sendAdminNotification,
  type AdminNotificationSummary,
} from "../services/notificationsApi";
import { NOTIFICATION_TEMPLATES } from "../notificationTemplates";

export default function AdminNotificationsPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<AdminNotificationSummary[]>([]);
  const [users, setUsers] = useState<Array<{ id: number; full_name: string; email: string }>>([]);
  const [selectedUsers, setSelectedUsers] = useState<number[]>([]);
  const [title, setTitle] = useState("");
  const [message, setMessage] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [detailId, setDetailId] = useState<number | null>(null);
  const [detail, setDetail] = useState<Awaited<ReturnType<typeof fetchAdminNotificationDetail>> | null>(null);
  const [error, setError] = useState("");
  const [messageOk, setMessageOk] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const [list, opts] = await Promise.all([fetchAdminNotifications(), fetchAdminRecipientOptions()]);
    setItems(list.items);
    setUsers(opts.users);
  }, []);

  useEffect(() => {
    load().catch((e) => setError(e instanceof Error ? e.message : "Load failed"));
  }, [load]);

  useEffect(() => {
    if (detailId == null) {
      setDetail(null);
      return;
    }
    fetchAdminNotificationDetail(detailId).then(setDetail).catch(() => setDetail(null));
  }, [detailId]);

  async function onSend() {
    setBusy(true);
    setError("");
    setMessageOk("");
    try {
      const r = await sendAdminNotification({
        title,
        message,
        recipientUserIds: selectedUsers,
        files,
      });
      setMessageOk(`Sent to ${r.recipient_count} faculty member(s).`);
      setTitle("");
      setMessage("");
      setFiles([]);
      setSelectedUsers([]);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Send failed");
    } finally {
      setBusy(false);
    }
  }

  if (user?.role !== "admin") {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Send notifications</h2>
        <p className="text-sm text-slate-600 mt-1">
          Create and send reminders to faculty. Email is sent when SMTP is enabled. Faculty view messages under{" "}
          <Link to="/notifications" className="text-teal-700 underline">
            Notifications
          </Link>
          .
        </p>
      </div>

      {messageOk && <p className="text-sm text-teal-800 bg-teal-50 border border-teal-200 rounded-lg px-3 py-2">{messageOk}</p>}
      {error && <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>}

      <section className="bg-white border rounded-xl p-6 space-y-3">
        <div>
          <p className="text-sm font-medium text-slate-700 mb-2">Use a template</p>
          <div className="flex flex-wrap gap-2">
            {NOTIFICATION_TEMPLATES.map((tpl) => (
              <button
                key={tpl.id}
                type="button"
                className="text-xs px-2 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50"
                onClick={() => {
                  setTitle(tpl.subject);
                  setMessage(tpl.body);
                }}
              >
                {tpl.label}
              </button>
            ))}
          </div>
          <p className="text-xs text-slate-500 mt-2">
            Placeholders like <span className="font-mono bg-amber-50 px-1 rounded">[Faculty Name]</span> and{" "}
            <span className="font-mono bg-amber-50 px-1 rounded">[Date]</span> are shown in brackets — replace them before sending.
          </p>
        </div>
        <input
          className="w-full border rounded-lg px-3 py-2 text-sm"
          placeholder="Title / Subject"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <textarea
          className="w-full border rounded-lg px-3 py-2 text-sm min-h-[160px] font-mono text-[13px]"
          placeholder="Message"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
        />
        <div>
          <label className="text-xs text-slate-500">Recipients (empty = all faculty &amp; HOD)</label>
          <select
            multiple
            className="w-full border rounded-lg px-3 py-2 text-sm mt-1 min-h-[120px]"
            value={selectedUsers.map(String)}
            onChange={(e) => setSelectedUsers(Array.from(e.target.selectedOptions).map((o) => Number(o.value)))}
          >
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.full_name} ({u.email})
              </option>
            ))}
          </select>
        </div>
        <input
          type="file"
          multiple
          className="text-sm"
          onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
        />
        <button
          type="button"
          disabled={busy || !title.trim() || !message.trim()}
          onClick={onSend}
          className="rounded-lg bg-teal-700 text-white px-4 py-2 text-sm disabled:opacity-50"
        >
          Send notification
        </button>
      </section>

      <section className="bg-white border rounded-xl overflow-hidden">
        <h3 className="font-medium px-4 py-3 border-b bg-slate-50">Sent notifications</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500 border-b">
              <th className="px-4 py-2">Title</th>
              <th className="px-4 py-2">Sent</th>
              <th className="px-4 py-2">Read</th>
              <th className="px-4 py-2">Email</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {items.map((row) => (
              <tr key={row.id} className="border-b border-slate-100">
                <td className="px-4 py-2">{row.title}</td>
                <td className="px-4 py-2">{row.created_at ? new Date(row.created_at).toLocaleString() : "—"}</td>
                <td className="px-4 py-2">
                  {row.read_count}/{row.recipient_count}
                </td>
                <td className="px-4 py-2">
                  {row.email_sent_count} sent
                  {row.email_failed_count > 0 && `, ${row.email_failed_count} failed`}
                </td>
                <td className="px-4 py-2">
                  <button type="button" className="text-xs text-teal-700" onClick={() => setDetailId(row.id)}>
                    Details
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {detail && (
        <section className="bg-white border rounded-xl p-4 space-y-2">
          <h3 className="font-medium">{detail.title}</h3>
          <p className="text-sm whitespace-pre-wrap">{detail.message}</p>
          <table className="w-full text-xs mt-2">
            <thead>
              <tr className="text-slate-500">
                <th className="text-left py-1">Faculty</th>
                <th className="text-left py-1">Read</th>
                <th className="text-left py-1">Email</th>
              </tr>
            </thead>
            <tbody>
              {detail.recipients.map((r) => (
                <tr key={r.user_id} className="border-t">
                  <td className="py-1">{r.name}</td>
                  <td className="py-1">{r.read_at ? "Yes" : "No"}</td>
                  <td className="py-1">
                    {r.email_status}
                    {r.email_error ? ` (${r.email_error})` : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
