"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { apiGet, apiRequest, errorMessage, HubApiError, UNAUTHORIZED_EVENT } from "./api";
import type { Me, Role, SetupStatus } from "./types";

export type SessionState =
  | { status: "loading" }
  | { status: "setup" }
  | { status: "anon"; uitgelogd?: boolean }
  | { status: "auth"; me: Me }
  | { status: "error"; error: HubApiError };

interface SessionCtx {
  state: SessionState;
  refresh: () => Promise<SessionState>;
  logout: () => Promise<void>;
}

const Ctx = createContext<SessionCtx | null>(null);

export const ROLE_RANK: Record<Role, number> = { kind: 0, viewer: 1, operator: 2, admin: 3 };
export const ROLE_LABEL: Record<Role, string> = {
  admin: "beheerder",
  operator: "operator",
  viewer: "kijker",
  kind: "kinderprofiel",
};

export function hasRole(role: Role | undefined, min: Role): boolean {
  return role !== undefined && ROLE_RANK[role] >= ROLE_RANK[min];
}

export async function loadSession(): Promise<SessionState> {
  try {
    const setup = await apiGet<SetupStatus>("/api/v1/setup/status");
    if (setup.setup_vereist) return { status: "setup" };
    try {
      const me = await apiGet<Me>("/api/v1/auth/me");
      return { status: "auth", me };
    } catch (e) {
      if (e instanceof HubApiError && e.status === 401) return { status: "anon" };
      throw e;
    }
  } catch (e) {
    return { status: "error", error: e instanceof HubApiError ? e : new HubApiError(0, "onbekend", errorMessage(e)) };
  }
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<SessionState>({ status: "loading" });

  const refresh = useCallback(async () => {
    const next = await loadSession();
    setState(next);
    return next;
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiRequest("/api/v1/auth/logout", { method: "POST" });
    } finally {
      setState({ status: "anon", uitgelogd: true });
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    void loadSession().then((s) => {
      if (!cancelled) setState(s);
    });
    const onUnauthorized = () => setState({ status: "anon" });
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => {
      cancelled = true;
      window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    };
  }, []);

  const value = useMemo(() => ({ state, refresh, logout }), [state, refresh, logout]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSession(): SessionCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useSession buiten SessionProvider");
  return ctx;
}

/** Rol van de aangemelde gebruiker (undefined als niet aangemeld). */
export function useRole(): Role | undefined {
  const { state } = useSession();
  return state.status === "auth" ? state.me.user.role : undefined;
}
