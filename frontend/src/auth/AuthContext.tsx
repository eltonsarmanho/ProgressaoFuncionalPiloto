import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { ApiError, request, setCsrfToken } from "../api/client";

export type Role = "ADMIN" | "SECRETARIA" | "DOCENTE";
export type CurrentUser = { id: string; name: string; role: Role };
type Me = CurrentUser & { csrf_token: string };

type AuthState = {
  user: CurrentUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

async function fetchMe(): Promise<CurrentUser | null> {
  try {
    const me = await request<Me>("GET", "/api/auth/me");
    setCsrfToken(me.csrf_token);
    return { id: me.id, name: me.name, role: me.role };
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      setCsrfToken(null);
      return null;
    }
    throw error;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMe()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    await request("POST", "/api/auth/login", { email, password });
    setUser(await fetchMe());
  }, []);

  const logout = useCallback(async () => {
    try {
      await request("POST", "/api/auth/logout");
    } finally {
      setCsrfToken(null);
      setUser(null);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth fora de AuthProvider");
  return ctx;
}
