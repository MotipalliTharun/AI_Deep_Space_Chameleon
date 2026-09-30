import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { ApiError, api, setSessionExpiredHandler } from "../lib/api";
import type { AuthResponse, MeResponse, Role, Tenant, User } from "../lib/types";

type Status = "loading" | "authenticated" | "anonymous";

export interface SignupInput {
  company_name: string;
  full_name: string;
  email: string;
  password: string;
}

interface AuthContextValue {
  status: Status;
  user: User | null;
  tenant: Tenant | null;
  sessionExpired: boolean;
  /** True after the user clicked "Sign out" (vs. an expired session or first visit). */
  signedOutByUser: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (input: SignupInput) => Promise<void>;
  logout: () => Promise<void>;
  reload: () => Promise<void>;
  hasRole: (...roles: Role[]) => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");
  const [me, setMe] = useState<MeResponse | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [signedOutByUser, setSignedOutByUser] = useState(false);
  // Read inside the session-expired callback without re-registering it.
  const statusRef = useRef<Status>("loading");
  statusRef.current = status;

  const signedIn = useCallback((data: MeResponse) => {
    setMe({ user: data.user, tenant: data.tenant });
    setSessionExpired(false);
    setSignedOutByUser(false);
    setStatus("authenticated");
  }, []);

  const signedOut = useCallback(() => {
    setMe(null);
    setStatus("anonymous");
  }, []);

  const reload = useCallback(async () => {
    try {
      signedIn(await api.get<MeResponse>("/v1/auth/me"));
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) signedOut();
      else throw err;
    }
  }, [signedIn, signedOut]);

  useEffect(() => {
    setSessionExpiredHandler(() => {
      // Only a session that was live can "expire"; a first visit is just anonymous.
      if (statusRef.current === "authenticated") setSessionExpired(true);
      signedOut();
    });
    reload().catch(() => signedOut());
    return () => setSessionExpiredHandler(null);
  }, [reload, signedOut]);

  const login = useCallback(
    async (email: string, password: string) => {
      signedIn(await api.post<AuthResponse>("/v1/auth/login", { email, password }));
    },
    [signedIn],
  );

  const signup = useCallback(
    async (input: SignupInput) => {
      signedIn(await api.post<AuthResponse>("/v1/auth/signup", input));
    },
    [signedIn],
  );

  const logout = useCallback(async () => {
    try {
      await api.post("/v1/auth/logout");
    } finally {
      setSignedOutByUser(true);
      signedOut();
    }
  }, [signedOut]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user: me?.user ?? null,
      tenant: me?.tenant ?? null,
      sessionExpired,
      signedOutByUser,
      login,
      signup,
      logout,
      reload,
      hasRole: (...roles) => (me ? roles.includes(me.user.role) : false),
    }),
    [status, me, sessionExpired, signedOutByUser, login, signup, logout, reload],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
