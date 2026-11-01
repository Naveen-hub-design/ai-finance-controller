import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, setAuthToken, setUnauthorizedHandler } from "../lib/api";
import type { LoginResponse, Role, User } from "../lib/types";

const TOKEN_KEY = "ai_finance_access_token";
const USER_KEY = "ai_finance_current_user";

export interface AuthContextValue {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<Role>;
  demoLogin: (role: Role) => Promise<Role>;
  logout: () => void;
  updateProfile: (input: {
    email: string;
    full_name: string | null;
  }) => Promise<User>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function readStoredToken(): string | null {
  return window.localStorage.getItem(TOKEN_KEY);
}

function readStoredUser(): User | null {
  try {
    const raw = window.localStorage.getItem(USER_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as unknown;
    if (
      typeof parsed !== "object" ||
      parsed === null ||
      typeof (parsed as User).id !== "string" ||
      typeof (parsed as User).email !== "string"
    ) {
      return null;
    }
    const user = parsed as User;
    // localStorage is not trusted authority. The role shown in the UI is
    // cosmetic gating only (the backend enforces authorization). Normalize a
    // cached role to a safe default so a stale/tampered store can never
    // present itself as PLATFORM_ADMIN in the sidebar.
    if (
      user.role !== "PLATFORM_ADMIN" &&
      user.role !== "MERCHANT" &&
      user.role !== "FINANCE_MANAGER"
    ) {
      user.role = "MERCHANT";
    }
    return user;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const storedToken = readStoredToken();
    const storedUser = readStoredUser();
    if (storedToken && storedUser) {
      setAuthToken(storedToken);
      setToken(storedToken);
      setUser(storedUser);
    }
    setIsLoading(false);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      window.localStorage.removeItem(TOKEN_KEY);
      window.localStorage.removeItem(USER_KEY);
      setAuthToken(null);
      setToken(null);
      setUser(null);
      if (window.location.pathname !== "/login") {
        window.location.assign("/login");
      }
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  const establishSession = useCallback((res: LoginResponse): Role => {
    const newToken = res.access_token;
    const newUser = res.user;
    window.localStorage.setItem(TOKEN_KEY, newToken);
    window.localStorage.setItem(USER_KEY, JSON.stringify(newUser));
    setAuthToken(newToken);
    setToken(newToken);
    setUser(newUser);
    return newUser.role;
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.post<LoginResponse>("/users/login", {
      email,
      password,
    });
    return establishSession(res);
  }, [establishSession]);

  const demoLogin = useCallback(async (role: Role) => {
    // Dev-only: the backend guards /users/demo-login so it is never available
    // in production. It returns the same session shape as normal login, so we
    // reuse the identical persistence path.
    const res = await api.post<LoginResponse>("/users/demo-login", { role });
    return establishSession(res);
  }, [establishSession]);

  const logout = useCallback(() => {
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(USER_KEY);
    setAuthToken(null);
    setToken(null);
    setUser(null);
  }, []);

  const updateProfile = useCallback(
    async (input: { email: string; full_name: string | null }) => {
      if (!user) throw new Error("You must be signed in to update your profile.");
      const updated = await api.put<User>(`/users/${user.id}`, {
        email: input.email,
        full_name: input.full_name,
      });
      window.localStorage.setItem(USER_KEY, JSON.stringify(updated));
      setUser(updated);
      return updated;
    },
    [user]
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      isAuthenticated: user !== null && token !== null,
      isLoading,
      login,
      demoLogin,
      logout,
      updateProfile,
    }),
    [user, token, isLoading, login, demoLogin, logout, updateProfile]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
