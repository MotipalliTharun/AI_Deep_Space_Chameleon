import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import type { AuditEvent, AuditPage } from "../lib/types";
import { Alert, Button, errorMessage } from "../components/ui";

export function AuditLog() {
  const [items, setItems] = useState<AuditEvent[]>([]);
  const [next, setNext] = useState<string | null>(null);
  const [action, setAction] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (before: string | null) => {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams({ limit: "50" });
      if (action) params.set("action", action);
      if (before) params.set("before", before);
      try {
        const page = await api.get<AuditPage>(`/v1/audit-events?${params}`);
        setItems((prev) => (before ? [...prev, ...page.items] : page.items));
        setNext(page.next_before);
      } catch (err) {
        setError(errorMessage(err));
      } finally {
        setLoading(false);
      }
    },
    [action],
  );

  useEffect(() => {
    void load(null);
  }, [load]);

  return (
    <div className="max-w-5xl space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold">Audit log</h1>
          <p className="text-sm text-gray-500">Security-relevant activity in this workspace.</p>
        </div>
        <div>
          <label htmlFor="audit-filter" className="block text-xs font-medium text-gray-600">Action</label>
          <select id="audit-filter" className="mt-1 rounded border border-gray-300 px-2 py-1 text-sm" value={action} onChange={(e) => setAction(e.target.value)}>
            <option value="">All</option>
            {["auth.login", "auth.login_failed", "auth.logout", "auth.password_changed", "auth.refresh_reuse_detected", "user.created", "user.updated"].map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>
        </div>
      </div>
      {error && <Alert>{error}</Alert>}
      <div className="overflow-hidden rounded-lg border bg-white">
        <table className="min-w-full divide-y text-sm">
          <thead className="bg-gray-50 text-left text-gray-600">
            <tr>
              <th scope="col" className="px-4 py-2 font-medium">When</th>
              <th scope="col" className="px-4 py-2 font-medium">Action</th>
              <th scope="col" className="px-4 py-2 font-medium">Target</th>
              <th scope="col" className="px-4 py-2 font-medium">IP</th>
              <th scope="col" className="px-4 py-2 font-medium">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y font-mono text-xs">
            {items.map((e) => (
              <tr key={e.id}>
                <td className="whitespace-nowrap px-4 py-2 font-sans">{new Date(e.created_at).toLocaleString()}</td>
                <td className="px-4 py-2">{e.action}</td>
                <td className="px-4 py-2">{e.target_type ? `${e.target_type}:${e.target_id?.slice(0, 8)}` : "—"}</td>
                <td className="px-4 py-2">{e.ip_address || "—"}</td>
                <td className="max-w-xs truncate px-4 py-2" title={JSON.stringify(e.details)}>
                  {Object.keys(e.details).length ? JSON.stringify(e.details) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && items.length === 0 && <p className="p-4 text-sm text-gray-500">No events yet.</p>}
      </div>
      {next && (
        <Button variant="secondary" loading={loading} onClick={() => load(next)}>Load more</Button>
      )}
    </div>
  );
}
