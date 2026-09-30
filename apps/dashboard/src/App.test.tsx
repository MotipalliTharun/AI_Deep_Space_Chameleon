import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { AppRoutes } from "./App";
import { AuthProvider } from "./auth/AuthContext";
import { ME, mockFetch } from "./test/fetchMock";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("auth flow", () => {
  it("redirects anonymous users to sign-in", async () => {
    mockFetch(() => ({ status: 401 }));
    renderAt("/team");
    expect(await screen.findByRole("heading", { name: /sign in/i })).toBeInTheDocument();
    expect(screen.queryByText(/session expired/i)).not.toBeInTheDocument();
  });

  it("tells a signed-in user when their session expires", async () => {
    document.cookie = "sc_csrf=tok; path=/";
    let live = true;
    mockFetch(({ url }) => {
      if (url === "/v1/auth/me") return { status: 200, body: ME };
      if (url === "/v1/users" && live) {
        live = false;
        return { status: 401 };
      }
      return { status: 401 };
    });
    renderAt("/team");
    expect(await screen.findByText(/session expired/i)).toBeInTheDocument();
  });

  it("signs in and lands on the originally requested page", async () => {
    let signedIn = false;
    const calls = mockFetch(({ url }) => {
      if (url === "/v1/auth/login") {
        signedIn = true;
        return { status: 200, body: { ...ME, csrf_token: "c", access_token_expires_at: "" } };
      }
      if (url === "/v1/auth/me") return signedIn ? { status: 200, body: ME } : { status: 401 };
      if (url === "/v1/users") return { status: 200, body: [ME.user] };
      return { status: 401 };
    });
    renderAt("/team");
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText(/work email/i), "owner@acme.com");
    await user.type(screen.getByLabelText(/^password$/i), "correct horse battery staple");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByRole("heading", { name: "Team" })).toBeInTheDocument();
    const login = calls.find((c) => c.url === "/v1/auth/login");
    expect(login?.body).toEqual({ email: "owner@acme.com", password: "correct horse battery staple" });
  });

  it("shows a generic error and clears the password on bad credentials", async () => {
    mockFetch(({ url }) =>
      url === "/v1/auth/login"
        ? { status: 401, body: { detail: { code: "invalid_credentials", message: "x" } } }
        : { status: 401 },
    );
    renderAt("/login");
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText(/work email/i), "a@b.com");
    const pw = screen.getByLabelText(/^password$/i);
    await user.type(pw, "nope nope nope");
    await user.click(screen.getByRole("button", { name: /sign in/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password.");
    expect(pw).toHaveValue("");
  });

  it("hides admin navigation from agents and blocks admin pages", async () => {
    const agent = { ...ME, user: { ...ME.user, role: "agent" } };
    mockFetch(({ url }) => (url === "/v1/auth/me" ? { status: 200, body: agent } : { status: 200, body: [] }));
    renderAt("/team");
    expect(await screen.findByRole("heading", { name: /access denied/i })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Team" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Agent inbox" })).toBeInTheDocument();
  });

  it("signs out", async () => {
    let signedIn = true;
    mockFetch(({ url }) => {
      if (url === "/v1/auth/logout") {
        signedIn = false;
        return { status: 204 };
      }
      if (url === "/v1/auth/login") {
        return { status: 200, body: { ...ME, csrf_token: "c", access_token_expires_at: "" } };
      }
      if (url === "/v1/auth/me") return signedIn ? { status: 200, body: ME } : { status: 401 };
      return { status: 200, body: [] };
    });
    renderAt("/team");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: /sign out/i }));
    await waitFor(() => expect(screen.getByRole("heading", { name: /sign in/i })).toBeInTheDocument());

    // The next sign-in must not be sent back to the previous user's page.
    await user.type(screen.getByLabelText(/work email/i), "owner@acme.com");
    await user.type(screen.getByLabelText(/^password$/i), "correct horse battery staple");
    signedIn = true;
    await user.click(screen.getByRole("button", { name: /sign in/i }));
    expect(await screen.findByRole("heading", { name: "AgentInbox" })).toBeInTheDocument();
  });

  it("sends a new workspace owner to Setup after sign-up", async () => {
    let signedIn = false;
    mockFetch(({ url }) => {
      if (url === "/v1/auth/signup") {
        signedIn = true;
        return { status: 201, body: { ...ME, csrf_token: "c", access_token_expires_at: "" } };
      }
      if (url === "/v1/auth/me") return signedIn ? { status: 200, body: ME } : { status: 401 };
      return { status: 200, body: [] };
    });
    renderAt("/signup");
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText(/company name/i), "Acme");
    await user.type(screen.getByLabelText(/your name/i), "Olive");
    await user.type(screen.getByLabelText(/work email/i), "o@acme.com");
    await user.type(screen.getByLabelText(/^password$/i), "correct horse battery staple");
    await user.click(screen.getByRole("button", { name: /create workspace/i }));
    expect(await screen.findByRole("heading", { name: "Setup" })).toBeInTheDocument();
  });

  it("validates password length on sign-up before calling the API", async () => {
    const calls = mockFetch(() => ({ status: 401 }));
    renderAt("/signup");
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText(/company name/i), "Acme");
    await user.type(screen.getByLabelText(/your name/i), "Olive");
    await user.type(screen.getByLabelText(/work email/i), "o@acme.com");
    await user.type(screen.getByLabelText(/^password$/i), "short");
    await user.click(screen.getByRole("button", { name: /create workspace/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/at least 12 characters/);
    expect(calls.some((c) => c.url === "/v1/auth/signup")).toBe(false);
  });
});
