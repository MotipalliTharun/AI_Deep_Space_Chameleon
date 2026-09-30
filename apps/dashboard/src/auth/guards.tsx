import { Navigate, Outlet, useLocation } from "react-router-dom";
import type { Role } from "../lib/types";
import { useAuth } from "./AuthContext";

function FullPageSpinner() {
  return (
    <div className="flex h-screen items-center justify-center" role="status" aria-live="polite">
      <span className="text-sm text-gray-500">Loading…</span>
    </div>
  );
}

/** Renders child routes only for signed-in users; otherwise redirects to /login. */
export function RequireAuth() {
  const { status, signedOutByUser } = useAuth();
  const location = useLocation();
  if (status === "loading") return <FullPageSpinner />;
  if (status === "anonymous") {
    // After an explicit sign-out, the next person to sign in starts fresh.
    const state = signedOutByUser ? undefined : { from: location.pathname + location.search };
    return <Navigate to="/login" replace state={state} />;
  }
  return <Outlet />;
}

/**
 * Keeps signed-in users away from /login and /signup, and owns the redirect
 * after signing in: back to the page they were bounced from, or to Setup for
 * a brand-new workspace.
 */
export function RedirectIfAuthenticated() {
  const { status } = useAuth();
  const location = useLocation();
  if (status === "loading") return <FullPageSpinner />;
  if (status === "authenticated") {
    const from = (location.state as { from?: string } | null)?.from;
    const fallback = location.pathname === "/signup" ? "/setup" : "/";
    return <Navigate to={from ?? fallback} replace />;
  }
  return <Outlet />;
}

export function RequireRole({ roles }: { roles: readonly Role[] }) {
  const { hasRole } = useAuth();
  if (!hasRole(...roles)) {
    return (
      <div role="alert">
        <h1 className="text-xl font-semibold">Access denied</h1>
        <p className="mt-1 text-gray-500">You don&apos;t have permission to view this page.</p>
      </div>
    );
  }
  return <Outlet />;
}
