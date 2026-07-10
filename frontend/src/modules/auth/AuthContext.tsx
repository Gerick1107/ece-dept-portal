import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { fetchMe, login as apiLogin, logout as apiLogout, type User } from "../../services/api";

// Auto-logout after this many minutes of no user activity (mouse/keyboard/etc).
const INACTIVITY_MINUTES = Number(import.meta.env.VITE_INACTIVITY_MINUTES ?? 30);

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  mustChangePassword: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [mustChangePassword, setMustChangePassword] = useState(false);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setUser(null);
      setMustChangePassword(false);
      setLoading(false);
      return;
    }
    try {
      const me = await fetchMe();
      setUser(me);
      setMustChangePassword(me.must_change_password ?? false);
    } catch {
      apiLogout();
      setUser(null);
      setMustChangePassword(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(async (email: string, password: string) => {
    const { must_change_password } = await apiLogin(email, password);
    setMustChangePassword(must_change_password);
    setUser(await fetchMe());
  }, []);

  const logout = useCallback(() => {
    apiLogout();
    setUser(null);
    setMustChangePassword(false);
  }, []);

  // Inactivity auto-logout: reset a timer on any user activity while logged in.
  const idleTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (!user || INACTIVITY_MINUTES <= 0) return;
    const timeoutMs = INACTIVITY_MINUTES * 60 * 1000;
    const reset = () => {
      if (idleTimer.current) clearTimeout(idleTimer.current);
      idleTimer.current = setTimeout(() => {
        logout();
        window.alert(`You were signed out after ${INACTIVITY_MINUTES} minutes of inactivity.`);
      }, timeoutMs);
    };
    const events = ["mousedown", "keydown", "scroll", "touchstart", "click", "visibilitychange"];
    events.forEach((e) => window.addEventListener(e, reset, { passive: true }));
    reset();
    return () => {
      if (idleTimer.current) clearTimeout(idleTimer.current);
      events.forEach((e) => window.removeEventListener(e, reset));
    };
  }, [user, logout]);

  const value = useMemo(
    () => ({ user, loading, mustChangePassword, login, logout, refresh }),
    [user, loading, mustChangePassword, login, logout, refresh]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
