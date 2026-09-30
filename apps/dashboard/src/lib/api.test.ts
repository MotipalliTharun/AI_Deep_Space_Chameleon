import { describe, expect, it, vi } from "vitest";
import { ApiError, api, setSessionExpiredHandler } from "./api";
import { mockFetch } from "../test/fetchMock";

describe("api client", () => {
  it("sends the CSRF cookie as a header on unsafe methods only", async () => {
    document.cookie = "sc_csrf=tok123; path=/";
    const calls = mockFetch(() => ({ status: 200, body: {} }));
    await api.get("/v1/x");
    await api.post("/v1/y", { a: 1 });
    expect(calls[0]!.headers.get("X-CSRF-Token")).toBeNull();
    expect(calls[1]!.headers.get("X-CSRF-Token")).toBe("tok123");
    expect(calls[1]!.headers.get("Content-Type")).toBe("application/json");
  });

  it("does not attempt a refresh without a session cookie", async () => {
    const calls = mockFetch(() => ({ status: 401 }));
    await expect(api.get("/v1/auth/me")).rejects.toBeInstanceOf(ApiError);
    expect(calls.map((c) => c.url)).toEqual(["/v1/auth/me"]);
  });

  it("refreshes once on 401 and retries the request", async () => {
    document.cookie = "sc_csrf=tok; path=/";
    let authed = false;
    const calls = mockFetch(({ url }) => {
      if (url === "/v1/auth/refresh") {
        authed = true;
        return { status: 200, body: {} };
      }
      return authed ? { status: 200, body: { ok: true } } : { status: 401 };
    });
    await expect(api.get("/v1/users")).resolves.toEqual({ ok: true });
    expect(calls.map((c) => c.url)).toEqual(["/v1/users", "/v1/auth/refresh", "/v1/users"]);
  });

  it("shares one refresh between concurrent 401s", async () => {
    document.cookie = "sc_csrf=tok; path=/";
    let authed = false;
    const calls = mockFetch(({ url }) => {
      if (url === "/v1/auth/refresh") {
        authed = true;
        return { status: 200, body: {} };
      }
      return authed ? { status: 200, body: {} } : { status: 401 };
    });
    await Promise.all([api.get("/v1/a"), api.get("/v1/b"), api.get("/v1/c")]);
    expect(calls.filter((c) => c.url === "/v1/auth/refresh")).toHaveLength(1);
  });

  it("reports session expiry when refresh fails", async () => {
    const expired = vi.fn();
    setSessionExpiredHandler(expired);
    document.cookie = "sc_csrf=tok; path=/";
    mockFetch(() => ({ status: 401, body: { detail: { code: "invalid_refresh", message: "gone" } } }));
    await expect(api.get("/v1/users")).rejects.toBeInstanceOf(ApiError);
    expect(expired).toHaveBeenCalledOnce();
    setSessionExpiredHandler(null);
  });

  it("does not try to refresh on a failed login", async () => {
    const calls = mockFetch(() => ({
      status: 401,
      body: { detail: { code: "invalid_credentials", message: "Invalid email or password." } },
    }));
    const err = await api.post("/v1/auth/login", {}).catch((e: unknown) => e);
    expect(err).toMatchObject({ status: 401, code: "invalid_credentials" });
    expect(calls).toHaveLength(1);
  });

  it("flattens FastAPI validation errors", async () => {
    mockFetch(() => ({
      status: 422,
      body: { detail: [{ loc: ["body", "email"], msg: "value is not a valid email address" }] },
    }));
    await expect(api.post("/v1/auth/signup", {})).rejects.toThrow(
      "email: value is not a valid email address",
    );
  });
});
