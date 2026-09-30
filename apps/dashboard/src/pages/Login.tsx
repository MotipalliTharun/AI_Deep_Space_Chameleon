import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../lib/api";
import { Alert, Button, PasswordField, TextField, errorMessage } from "../components/ui";
import { AuthLayout } from "./AuthLayout";

export function Login() {
  const { login, sessionExpired } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password); // RedirectIfAuthenticated navigates on success
    } catch (err) {
      setPassword("");
      setError(
        err instanceof ApiError && err.status === 401
          ? "Invalid email or password."
          : errorMessage(err),
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout title="Sign in to your workspace">
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {sessionExpired && !error && (
          <Alert kind="info">Your session expired. Please sign in again.</Alert>
        )}
        {error && <Alert>{error}</Alert>}
        <TextField
          label="Work email"
          type="email"
          autoComplete="username"
          required
          autoFocus
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <PasswordField
          label="Password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <Button type="submit" className="w-full" loading={submitting} disabled={!email || !password}>
          Sign in
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-gray-600">
        New to Space Chameleon?{" "}
        <Link to="/signup" className="font-medium text-emerald-700 hover:underline">
          Create a workspace
        </Link>
      </p>
    </AuthLayout>
  );
}
