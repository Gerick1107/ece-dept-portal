/** Stable row keys; works on HTTP (non-secure) origins where crypto.randomUUID is unavailable. */
export function generateId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    try {
      return crypto.randomUUID();
    } catch {
      /* fall through */
    }
  }
  return `id-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}
