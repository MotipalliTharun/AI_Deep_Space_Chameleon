import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useAuth } from "../auth/AuthContext";
import { api } from "../lib/api";
import type { Role, User } from "../lib/types";
import { Alert, Button, PasswordField, TextField, errorMessage } from "../components/ui";
import { MIN_PASSWORD_LENGTH } from "./Signup";

const ROLE_LABEL: Record<Role, string> = { owner: "Owner", admin: "Admin", agent: "Agent" };

function AddUserForm({ onCreated }: { onCreated: () => void }) {
  const { hasRole } = useAuth();
  const assignable: Role[] = hasRole("owner") ? ["agent", "admin", "owner"] : ["agent", "admin"];
  const empty = { email: "", full_name: "", role: "agent" as Role, password: "" };
  const [form, setForm] = useState(empty);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await api.post("/v1/users", form);
      setForm(empty);
      onCreated();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="rounded-lg border bg-white p-5" aria-labelledby="add-user-heading">
      <h2 id="add-user-heading" className="text-base font-semibold">Add a teammate</h2>
      <p className="mt-1 text-sm text-gray-500">
        Share the temporary password securely; they can change it under Account.
      </p>
      {error && <div className="mt-3"><Alert>{error}</Alert></div>}
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <TextField label="Name" required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
        <TextField label="Email" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <div>
          <label htmlFor="new-user-role" className="block text-sm font-medium text-gray-700">Role</label>
          <select id="new-user-role" className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as Role })}>
            {assignable.map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
          </select>
        </div>
        <PasswordField label="Temporary password" autoComplete="new-password" required minLength={MIN_PASSWORD_LENGTH} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
      </div>
      <Button type="submit" className="mt-4" loading={busy}>Add user</Button>
    </form>
  );
}

export function Team() {
  const { user: me, hasRole } = useAuth();
  const [users, setUsers] = useState<User[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setUsers(await api.get<User[]>("/v1/users"));
    } catch (err) {
      setError(errorMessage(err));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function patch(id: string, body: Partial<Pick<User, "role" | "is_active">>) {
    setError(null);
    try {
      await api.patch(`/v1/users/${id}`, body);
      await load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  const canEdit = (u: User) => u.id !== me?.id && (hasRole("owner") || u.role !== "owner");
  const roleOptions: Role[] = hasRole("owner") ? ["agent", "admin", "owner"] : ["agent", "admin"];

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Team</h1>
        <p className="text-sm text-gray-500">Admins manage settings and people; agents work the inbox.</p>
      </div>
      {error && <Alert>{error}</Alert>}
      <div className="overflow-hidden rounded-lg border bg-white">
        <table className="min-w-full divide-y text-sm">
          <thead className="bg-gray-50 text-left text-gray-600">
            <tr>
              <th scope="col" className="px-4 py-2 font-medium">Name</th>
              <th scope="col" className="px-4 py-2 font-medium">Role</th>
              <th scope="col" className="px-4 py-2 font-medium">Last sign-in</th>
              <th scope="col" className="px-4 py-2 font-medium"><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {users?.map((u) => (
              <tr key={u.id} className={u.is_active ? "" : "bg-gray-50 text-gray-400"}>
                <td className="px-4 py-3">
                  <p className="font-medium">{u.full_name || u.email}{u.id === me?.id && " (you)"}</p>
                  <p className="text-gray-500">{u.email}</p>
                </td>
                <td className="px-4 py-3">
                  {canEdit(u) ? (
                    <select aria-label={`Role for ${u.email}`} className="rounded border border-gray-300 px-2 py-1" value={u.role} onChange={(e) => patch(u.id, { role: e.target.value as Role })}>
                      {roleOptions.map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
                    </select>
                  ) : (
                    ROLE_LABEL[u.role]
                  )}
                </td>
                <td className="px-4 py-3">{u.last_login_at ? new Date(u.last_login_at).toLocaleString() : "Never"}</td>
                <td className="px-4 py-3 text-right">
                  {canEdit(u) && (
                    <Button variant={u.is_active ? "secondary" : "primary"} onClick={() => patch(u.id, { is_active: !u.is_active })}>
                      {u.is_active ? "Deactivate" : "Reactivate"}
                    </Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!users && !error && <p className="p-4 text-sm text-gray-500">Loading…</p>}
      </div>
      <AddUserForm onCreated={load} />
    </div>
  );
}
