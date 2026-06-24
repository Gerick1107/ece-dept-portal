const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

export type User = {
  id: number;
  email: string;
  full_name: string;
  role: "faculty" | "hod" | "admin";
  is_active: boolean;
  must_change_password?: boolean;
};

export type UserCreate = {
  email: string;
  full_name: string;
  password: string;
  role: "faculty" | "hod" | "admin";
  send_welcome_email?: boolean;
};

export type UserCreateResponse = User & { welcome_email_sent?: boolean };

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function formatApiDetail(detail: unknown, fallback = "Request failed"): string {
  if (typeof detail === "string") {
    if (detail.startsWith("Internal Server Error") || detail.startsWith("<")) {
      return "Something went wrong. Please try again.";
    }
    return detail;
  }
  if (Array.isArray(detail)) {
    const message = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          const loc = "loc" in item && Array.isArray((item as { loc?: unknown }).loc)
            ? (item as { loc: unknown[] }).loc.filter((p) => typeof p === "string" && p !== "body").join(".")
            : "";
          const msg = String((item as { msg?: string }).msg ?? "");
          return loc ? `${loc}: ${msg}` : msg;
        }
        return "";
      })
      .filter(Boolean)
      .join("; ");
    return message || "Please fill in the required field(s).";
  }
  if (detail && typeof detail === "object" && "msg" in detail) {
    return String((detail as { msg?: string }).msg ?? fallback);
  }
  return fallback;
}

async function parseErrorResponse(res: Response, fallback: string): Promise<string> {
  const text = await res.text();
  if (!text) return fallback;
  const contentType = res.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    if (text.startsWith("Internal Server Error")) return "Something went wrong. Please try again.";
    return text.length > 200 ? fallback : text;
  }
  try {
    const j = JSON.parse(text) as { detail?: unknown };
    return formatApiDetail(j.detail, fallback);
  } catch {
    return fallback;
  }
}

export async function login(
  email: string,
  password: string
): Promise<{ token: string; must_change_password: boolean }> {
  const res = await fetch(`${API_BASE}/auth/login/json`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(formatApiDetail(err.detail, "Login failed"));
  }
  const data = await res.json();
  localStorage.setItem("access_token", data.access_token);
  return {
    token: data.access_token,
    must_change_password: !!data.must_change_password,
  };
}

export async function fetchMe(): Promise<User> {
  const res = await fetch(`${API_BASE}/auth/me`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Not authenticated");
  return res.json();
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(await parseErrorResponse(res, "Request failed"));
  return res.json();
}

export async function apiPostJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseErrorResponse(res, "Request failed"));
  return res.json();
}

export async function apiPostNoContent(path: string): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(await parseErrorResponse(res, "Request failed"));
}

export async function apiDelete(path: string): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(await parseErrorResponse(res, "Delete failed"));
}

export async function apiPutJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseErrorResponse(res, "Request failed"));
  return res.json();
}

export async function apiPostForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: authHeaders(),
    body: form,
  });
  if (!res.ok) throw new Error(await parseErrorResponse(res, "Request failed"));
  return res.json();
}

export async function downloadCopoFile(token: string, filename = "results.xlsx") {
  const res = await fetch(`${API_BASE}/copo/download/${token}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Download failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export async function createUser(body: UserCreate): Promise<UserCreateResponse> {
  return apiPostJson<UserCreateResponse>("/auth/users", body);
}

export async function listUsers(): Promise<User[]> {
  return apiGet<User[]>("/auth/users");
}

export async function deactivateUser(userId: number): Promise<void> {
  return apiPostNoContent(`/auth/users/${userId}/deactivate`);
}

export async function activateUser(userId: number): Promise<void> {
  return apiPostNoContent(`/auth/users/${userId}/activate`);
}

export async function removeUserProfile(userId: number): Promise<void> {
  return apiDelete(`/auth/users/${userId}`);
}

export async function forgotPassword(email: string): Promise<string> {
  const res = await fetch(`${API_BASE}/auth/forgot-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(formatApiDetail(data.detail, "Could not send reset email"));
  }
  return typeof data.detail === "string" ? data.detail : "If the account exists, a temporary password has been sent to email.";
}

export function logout() {
  localStorage.removeItem("access_token");
}
