/**
 * Session state.
 *
 * Holds the signed-in user and keeps it in step with the HTTP layer: when a
 * refresh fails deep inside some unrelated request, `onSessionExpired` fires and
 * the provider clears the user, so every guarded route reacts at once instead of
 * each page discovering the dead session on its own.
 */

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { onSessionExpired } from "@/api/client";
import { auth as authApi } from "@/api/endpoints";
import { tokens } from "@/api/tokens";
import type { LoginIn, RegisterIn, UserPublic } from "@/api/types";
import { AuthContext, type AuthState } from "./context";

const STAFF_ROLES = new Set(["instructor", "admin", "super_admin"]);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserPublic | null>(null);
  const [loading, setLoading] = useState(true);

  // Restore the session on first load. A stored token may be expired, in which
  // case the client refreshes it transparently; only a failure lands us signed out.
  useEffect(() => {
    let cancelled = false;

    async function restore() {
      if (!tokens.has()) {
        setLoading(false);
        return;
      }
      try {
        const me = await authApi.me();
        if (!cancelled) setUser(me);
      } catch {
        if (!cancelled) {
          tokens.clear();
          setUser(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void restore();
    return () => {
      cancelled = true;
    };
  }, []);

  // The HTTP layer is the only thing that knows a refresh failed.
  useEffect(() => onSessionExpired(() => setUser(null)), []);

  const login = useCallback(async (credentials: LoginIn) => {
    const result = await authApi.login(credentials);
    tokens.save(result.tokens);
    setUser(result.user);
    return result.user;
  }, []);

  const register = useCallback(async (details: RegisterIn) => {
    const result = await authApi.register(details);
    tokens.save(result.tokens);
    setUser(result.user);
    return result.user;
  }, []);

  const logout = useCallback(async () => {
    const refresh = tokens.refresh();
    // Clear locally first: signing out must work even if the request fails.
    tokens.clear();
    setUser(null);
    if (refresh) {
      try {
        await authApi.logout(refresh);
      } catch {
        /* the token is already gone from this browser */
      }
    }
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      user,
      loading,
      isAuthenticated: Boolean(user),
      isStaff: Boolean(user && STAFF_ROLES.has(user.role)),
      login,
      register,
      logout,
      applyUser: setUser,
    }),
    [user, loading, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
