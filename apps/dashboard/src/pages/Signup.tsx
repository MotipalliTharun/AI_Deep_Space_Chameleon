import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { Alert, Button, PasswordField, TextField, errorMessage } from "../components/ui";
import { AuthLayout } from "./AuthLayout";

export const MIN_PASSWORD_LENGTH = 12;

export function Signup() {
  const { signup } = useAuth();
  const [form, setForm] = useState({ company_name: "", full_name: "", email: "", password: "" });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const update = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (form.password.length < MIN_PASSWORD_LENGTH) {
      setError(`Password must be at least ${MIN_PASSWORD_LENGTH} characters.`);
      return;
    }
    setSubmitting(true);
    try {
      await signup(form); // RedirectIfAuthenticated sends new workspaces to /setup
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout title="Create your workspace">
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {error && <Alert>{error}</Alert>}
        <TextField
          label="Company name"
          autoComplete="organization"
          required
          autoFocus
          value={form.company_name}
          onChange={update("company_name")}
        />
        <TextField
          label="Your name"
          autoComplete="name"
          required
          value={form.full_name}
          onChange={update("full_name")}
        />
        <TextField
          label="Work email"
          type="email"
          autoComplete="email"
          required
          value={form.email}
          onChange={update("email")}
        />
        <PasswordField
          label="Password"
          autoComplete="new-password"
          required
          minLength={MIN_PASSWORD_LENGTH}
          hint={`At least ${MIN_PASSWORD_LENGTH} characters. A short sentence works well.`}
          value={form.password}
          onChange={update("password")}
        />
        <Button type="submit" className="w-full" loading={submitting}>
          Create workspace
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-gray-600">
        Already have an account?{" "}
        <Link to="/login" className="font-medium text-emerald-700 hover:underline">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  );
}
