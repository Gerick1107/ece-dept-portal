import { useCallback, useEffect, useState } from "react";
import {
  downloadNotificationAttachment,
  downloadReplyAttachment,
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  submitNotificationReply,
  type NotificationItem,
} from "../services/notificationsApi";

export default function NotificationsPage() {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unread, setUnread] = useState(0);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState<number | null>(null);
  const [replyText, setReplyText] = useState<Record<number, string>>({});
  const [replyFile, setReplyFile] = useState<Record<number, File | null>>({});
  const [submitting, setSubmitting] = useState<number | null>(null);

  const load = useCallback(async () => {
    setError("");
    try {
      const r = await fetchNotifications();
      setItems(r.items);
      setUnread(r.unread_count);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load notifications");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function openItem(item: NotificationItem) {
    setExpanded(item.id);
    if (!item.is_read) {
      await markNotificationRead(item.id);
      await load();
    }
  }

  async function sendReply(item: NotificationItem) {
    const message = (replyText[item.id] ?? "").trim();
    if (!message) {
      setError("Please enter a reply message.");
      return;
    }
    setSubmitting(item.id);
    setError("");
    try {
      await submitNotificationReply(item.id, message, replyFile[item.id] ?? undefined);
      setReplyText((prev) => ({ ...prev, [item.id]: "" }));
      setReplyFile((prev) => ({ ...prev, [item.id]: null }));
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to send reply");
    } finally {
      setSubmitting(null);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">Notifications</h2>
          <p className="text-sm text-slate-600 mt-1">
            Department announcements and reminders {unread > 0 && `(${unread} unread)`}
          </p>
        </div>
        {unread > 0 && (
          <button
            type="button"
            className="text-sm border rounded-lg px-3 py-2 hover:bg-slate-50"
            onClick={async () => {
              await markAllNotificationsRead();
              await load();
            }}
          >
            Mark all read
          </button>
        )}
      </div>

      {error && <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>}

      <div className="space-y-2">
        {items.map((item) => (
          <article
            key={item.id}
            className={`bg-white border rounded-xl p-4 shadow-sm ${!item.is_read ? "border-teal-300 bg-teal-50/30" : "border-slate-200"}`}
          >
            <button type="button" className="w-full text-left" onClick={() => openItem(item)}>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-medium text-slate-900">{item.title}</p>
                  <p className="text-xs text-slate-500 mt-1">
                    {item.created_at ? new Date(item.created_at).toLocaleString() : ""}
                    {!item.is_read && <span className="ml-2 text-teal-700 font-medium">New</span>}
                  </p>
                </div>
              </div>
            </button>
            {expanded === item.id && (
              <div className="mt-3 pt-3 border-t border-slate-100 space-y-3">
                <p className="text-sm text-slate-700 whitespace-pre-wrap">{item.message}</p>
                {item.attachments.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {item.attachments.map((a) => (
                      <button
                        key={a.id}
                        type="button"
                        className="text-xs px-2 py-1 rounded bg-slate-100 hover:bg-slate-200"
                        onClick={() => downloadNotificationAttachment(a.id).catch(() => setError("Download failed"))}
                      >
                        {a.filename}
                      </button>
                    ))}
                  </div>
                )}

                {item.replies.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-xs font-medium text-slate-600 uppercase tracking-wide">Your replies</p>
                    {item.replies.map((reply) => (
                      <div key={reply.id} className="rounded-lg bg-slate-50 border border-slate-100 p-3 text-sm">
                        <p className="text-slate-700 whitespace-pre-wrap">{reply.message}</p>
                        <p className="text-xs text-slate-500 mt-1">
                          {reply.created_at ? new Date(reply.created_at).toLocaleString() : ""}
                        </p>
                        {reply.attachments.length > 0 && (
                          <div className="flex flex-wrap gap-2 mt-2">
                            {reply.attachments.map((a) => (
                              <button
                                key={a.id}
                                type="button"
                                className="text-xs px-2 py-1 rounded bg-white border hover:bg-slate-100"
                                onClick={() => downloadReplyAttachment(a.id).catch(() => setError("Download failed"))}
                              >
                                {a.filename}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                <div className="rounded-lg border border-slate-200 p-3 space-y-2 bg-white">
                  <p className="text-sm font-medium text-slate-800">Reply to this notification</p>
                  <p className="text-xs text-slate-500">
                    Attach a file to auto-mark the related requirement as fulfilled (green). Text-only replies stay
                    yellow for admin review.
                  </p>
                  <textarea
                    className="w-full border rounded-lg px-3 py-2 text-sm min-h-[80px]"
                    placeholder="Your response…"
                    value={replyText[item.id] ?? ""}
                    onChange={(e) => setReplyText((prev) => ({ ...prev, [item.id]: e.target.value }))}
                  />
                  <div className="flex flex-wrap items-center gap-3">
                    <input
                      type="file"
                      className="text-sm"
                      onChange={(e) =>
                        setReplyFile((prev) => ({ ...prev, [item.id]: e.target.files?.[0] ?? null }))
                      }
                    />
                    <button
                      type="button"
                      disabled={submitting === item.id}
                      className="rounded-lg bg-teal-800 text-white px-3 py-2 text-sm hover:bg-teal-700 disabled:opacity-60"
                      onClick={() => sendReply(item)}
                    >
                      {submitting === item.id ? "Sending…" : "Send reply"}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </article>
        ))}
        {!items.length && <p className="text-center text-slate-500 py-12">No notifications yet.</p>}
      </div>
    </div>
  );
}
