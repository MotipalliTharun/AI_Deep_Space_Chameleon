import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useAuth } from "../auth/AuthContext";
import { api } from "../lib/api";
import type { SessionInfo } from "../lib/types";
import { Alert, Button, PasswordField, errorMessage } from "../components/ui";
import { MIN_PASSWORD_LENGTH } from "./Signup";

function describeAgent(ua: string): string {
  if (!ua) return "Unknown device";
  const browser = /Edg\//.test(ua) ? "Edge" : /Chrome\//.test(ua) ? "Chrome" : /Firefox\//.test(ua) ? "Firefox" : /Safari\//.test(ua) ? "Safari" : "Browser";
  const os = /Mac OS X/.test(ua) ? "macOS" : /Windows/.test(ua) ? "Windows" : /Android/.test(ua) ? "Android" : /iPhone|iPad/.test(ua) ? "iOS" : /Linux/.test(ua) ? "Linux" : "";
  return os ? `${browser} on ${os}` : browser;
}

function ChangePassword() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [msg, setMsg] = useState<{ kind: "error" | "info"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setMsg(null);
    setBusy(true);
    try {
      await api.post("/v1/auth/change-password", { current_password: current, new_password: next });
      setCurrent("");
      setNext("");
      setMsg({ kind: "info", text: "Password changed. Other devices were signed out." });
    } catch (err) {
      setMsg({ kind: "error", text: errorMessage(err) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="pw-heading" className="rounded-lg border bg-white p-5">
      <h2 id="pw-heading" className="text-base font-semibold">Change password</h2>
      <form onSubmit={onSubmit} className="mt-4 max-w-sm space-y-4">
        {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}
        <PasswordField label="Current password" autoComplete="current-password" required value={current} onChange={(e) => setCurrent(e.target.value)} />
        <PasswordField label="New password" autoComplete="new-password" required minLength={MIN_PASSWORD_LENGTH} hint={`At least ${MIN_PASSWORD_LENGTH} characters.`} value={next} onChange={(e) => setNext(e.target.value)} />
        <Button type="submit" loading={busy} disabled={!current || next.length < MIN_PASSWORD_LENGTH}>
          Update password
        </Button>
      </form>
    </section>
  );
}

function Sessions() {
  const { logout } = useAuth();
  const [sessions, setSessions] = useState<SessionInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setSessions(await api.get<SessionInfo[]>("/v1/auth/sessions"));
    } catch (err) {
      setError(errorMessage(err));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function revoke(id: string) {
    try {
      await api.delete(`/v1/auth/sessions/${id}`);
      await load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function signOutEverywhere() {
    await api.post("/v1/auth/logout-all").catch(() => undefined);
    await logout();
  }

  return (
    <section aria-labelledby="sessions-heading" className="rounded-lg border bg-white p-5">
      <div className="flex items-center justify-between">
        <h2 id="sessions-heading" className="text-base font-semibold">Active sessions</h2>
        <Button variant="secondary" onClick={signOutEverywhere}>Sign out everywhere</Button>
      </div>
      {error && <div className="mt-3"><Alert>{error}</Alert></div>}
      {!sessions ? (
        <p className="mt-4 text-sm text-gray-500">Loading…</p>
      ) : (
        <ul className="mt-4 divide-y">
          {sessions.map((s) => (
            <li key={s.id} className="flex items-center justify-between py-3 text-sm">
              <div>
                <p className="font-medium">
                  {describeAgent(s.user_agent)}
                  {s.current && <span className="ml-2 rounded bg-emerald-100 px-1.5 py-0.5 text-xs text-emerald-800">This device</span>}
                </p>
                <p className="text-gray-500">
                  {s.ip_address || "Unknown IP"} · last active {new Date(s.last_used_at).toLocaleString()}
                </p>
              </div>
              {!s.current && (
                <Button variant="secondary" onClick={() => revoke(s.id)}>Revoke</Button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function Account() {
  const { user, tenant } = useAuth();
  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Account</h1>
        <p className="text-sm text-gray-500">
          {user?.full_name} · {user?.email} · {user?.role} at {tenant?.name}
        </p>
      </div>
      <ChangePassword />
      <Sessions />
    </div>
  );
}
