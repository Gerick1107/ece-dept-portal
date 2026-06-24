import { apiGet, apiPostForm } from "../../../services/api";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

export type NotificationReply = {
  id: number;
  message: string;
  created_at: string | null;
  attachments: Array<{ id: number; filename: string; mime_type: string | null; file_size: number | null }>;
};

export type NotificationItem = {
  id: number;
  notification_id: number;
  title: string;
  message: string;
  created_at: string | null;
  is_read: boolean;
  read_at: string | null;
  attachments: Array<{ id: number; filename: string; mime_type: string | null; file_size: number | null }>;
  replies: NotificationReply[];
};

export function fetchNotifications() {
  return apiGet<{ items: NotificationItem[]; unread_count: number }>("/notifications");
}

export function fetchUnreadCount() {
  return apiGet<{ count: number }>("/notifications/unread-count");
}

export function markNotificationRead(recipientId: number) {
  return apiPostForm(`/notifications/${recipientId}/read`, new FormData());
}

export function markAllNotificationsRead() {
  return apiPostForm("/notifications/read-all", new FormData());
}

export async function downloadNotificationAttachment(attachmentId: number) {
  const token = localStorage.getItem("access_token");
  const res = await fetch(`${API_BASE}/notifications/attachments/${attachmentId}/download`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("Download failed");
  const blob = await res.blob();
  const cd = res.headers.get("content-disposition");
  const name = cd?.match(/filename="?([^"]+)"?/)?.[1] ?? `attachment_${attachmentId}`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

export async function downloadReplyAttachment(attachmentId: number) {
  const token = localStorage.getItem("access_token");
  const res = await fetch(`${API_BASE}/notifications/reply-attachments/${attachmentId}/download`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("Download failed");
  const blob = await res.blob();
  const cd = res.headers.get("content-disposition");
  const name = cd?.match(/filename="?([^"]+)"?/)?.[1] ?? `reply_${attachmentId}`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

export async function submitNotificationReply(recipientId: number, message: string, file?: File) {
  const fd = new FormData();
  fd.append("message", message);
  if (file) fd.append("attachment", file);
  return apiPostForm<{ id: number; message: string; created_at: string | null; attachment_count: number }>(
    `/notifications/${recipientId}/reply`,
    fd
  );
}

export type AdminNotificationSummary = {
  id: number;
  title: string;
  message: string;
  created_at: string | null;
  recipient_count: number;
  read_count: number;
  email_sent_count: number;
  email_failed_count: number;
};

export function fetchAdminNotifications() {
  return apiGet<{ items: AdminNotificationSummary[] }>("/notifications/admin/list");
}

export function fetchAdminRecipientOptions() {
  return apiGet<{ users: Array<{ id: number; full_name: string; email: string; role: string }> }>(
    "/notifications/admin/users"
  );
}

export function fetchAdminNotificationDetail(id: number) {
  return apiGet<{
    id: number;
    title: string;
    message: string;
    created_at: string | null;
    attachments: Array<{ id: number; filename: string }>;
    recipients: Array<{
      recipient_id: number;
      user_id: number;
      name: string;
      email: string;
      read_at: string | null;
      email_status: string;
      email_error: string | null;
      replies: NotificationReply[];
    }>;
  }>(`/notifications/admin/${id}`);
}

export async function sendAdminNotification(form: {
  title: string;
  message: string;
  recipientUserIds: number[];
  files: File[];
  requirementType?: string;
  reminderIntervalMinutes?: number;
}) {
  const fd = new FormData();
  fd.append("title", form.title);
  fd.append("message", form.message);
  if (form.recipientUserIds.length) {
    fd.append("recipient_user_ids", form.recipientUserIds.join(","));
  }
  if (form.requirementType) {
    fd.append("requirement_type", form.requirementType);
  }
  if (form.reminderIntervalMinutes) {
    fd.append("reminder_interval_minutes", String(form.reminderIntervalMinutes));
  }
  form.files.forEach((f) => fd.append("attachments", f));
  return apiPostForm<{ id: number; recipient_count: number; title: string }>("/notifications/admin/send", fd);
}
