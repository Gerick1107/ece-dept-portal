import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { fetchMe, login as apiLogin, logout as apiLogout, type User } from "../../services/api";

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
