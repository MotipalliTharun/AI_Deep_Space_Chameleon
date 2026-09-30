import { vi } from "vitest";

export interface Call {
  url: string;
  method: string;
  headers: Headers;
  body: unknown;
}

type Handler = (call: Call) => { status: number; body?: unknown } | undefined;

/** Routes fetch() calls to `handler`; records every call. */
export function mockFetch(handler: Handler) {
  const calls: Call[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const call: Call = {
      url: String(input),
      method: (init?.method ?? "GET").toUpperCase(),
      headers: new Headers(init?.headers),
      body: init?.body ? JSON.parse(String(init.body)) : undefined,
    };
    calls.push(call);
    const res = handler(call) ?? { status: 404, body: { detail: "not mocked" } };
    return new Response(res.status === 204 ? null : JSON.stringify(res.body ?? {}), {
      status: res.status,
      headers: { "Content-Type": "application/json" },
    });
  });
  return calls;
}

export const ME = {
  user: {
    id: "u1",
    tenant_id: "t1",
    email: "owner@acme.com",
    full_name: "Olive Owner",
    role: "owner",
    is_active: true,
    last_login_at: null,
    created_at: "2026-09-30T00:00:00Z",
  },
  tenant: { id: "t1", name: "Acme Inc", slug: "acme-inc", plan: "starter" },
};
