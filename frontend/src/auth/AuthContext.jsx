/**
 * Auth context — bootstraps the session on load via /auth/me and exposes
 * login / register / logout. Because auth is a server-side session cookie, the
 * frontend never stores a token; it only tracks the resolved user object.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../api/client.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // On first load, ask the API who we are (cookie may already be set).
  useEffect(() => {
    let active = true;
    api
      .get("/auth/me")
      .then((u) => active && setUser(u))
      .catch(() => active && setUser(null))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(async (email, password) => {
    const u = await api.post("/auth/login", { email, password });
    setUser(u);
    return u;
  }, []);

  const register = useCallback(async (email, password, full_name) => {
    const u = await api.post("/auth/register", { email, password, full_name });
    setUser(u);
    return u;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } finally {
      setUser(null);
    }
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, register, logout }),
    [user, loading, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
