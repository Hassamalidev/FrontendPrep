import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { ApiError } from "@/api/client";
import { auth as authApi } from "@/api/endpoints";
import { useAuth } from "@/auth/useAuth";
import { Alert, Button, Card, Field } from "@/components/ui";
import { useAsync } from "@/lib/useAsync";

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const returnTo = (location.state as { from?: string } | null)?.from ?? "/dashboard";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  // Offered by the API only when the deployment permits it, so this section
  // simply disappears in production rather than needing its own flag here.
  const { data: demo } = useAsync(() => authApi.demo(), []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setFieldErrors({});

    try {
      await login({ email, password });
      navigate(returnTo, { replace: true });
    } catch (caught) {
      if (caught instanceof ApiError) {
        setError(caught.message);
        setFieldErrors(caught.fieldErrors);
      } else {
        setError("Could not reach the server. Check your connection and try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-md px-4 py-16">
      <h1 className="font-display text-2xl font-bold text-ink-900">Sign in</h1>
      <p className="mt-1 text-sm text-ink-500">Continue your preparation where you left off.</p>

      <Card className="mt-6 p-6">
        <form onSubmit={onSubmit} noValidate className="space-y-4">
          {error && <Alert tone="error">{error}</Alert>}

          <Field
            label="Email"
            name="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            error={fieldErrors.email}
          />
          <Field
            label="Password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            error={fieldErrors.password}
          />

          <Button type="submit" size="lg" loading={submitting} className="w-full">
            Sign in
          </Button>
        </form>
      </Card>

      {demo?.enabled && demo.accounts.length > 0 && (
        <Card className="mt-6 p-5">
          <h2 className="font-semibold text-ink-900">Try it without signing up</h2>
          <p className="mt-1 text-sm text-ink-500">
            These accounts are shared, so treat anything you save in them as public.
          </p>
          <ul className="mt-4 space-y-2">
            {demo.accounts.map((account) => (
              <li key={account.email}>
                <button
                  type="button"
                  onClick={() => {
                    setEmail(account.email);
                    setPassword(account.password);
                    setError(null);
                    setFieldErrors({});
                  }}
                  className="w-full rounded-lg px-3 py-2.5 text-left ring-1 ring-ink-200 transition hover:bg-ink-50 hover:ring-army-500"
                >
                  <span className="flex items-baseline justify-between gap-3">
                    <span className="font-medium text-ink-800">{account.label}</span>
                    <span className="font-mono text-xs text-ink-500">{account.email}</span>
                  </span>
                  <span className="mt-0.5 block text-sm text-ink-500">{account.description}</span>
                </button>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-ink-500">
            Choosing one fills the form; press Sign in to continue.
          </p>
        </Card>
      )}

      <p className="mt-6 text-center text-sm text-ink-500">
        New here?{" "}
        <Link to="/register" className="font-medium text-army-600 hover:underline">
          Create an account
        </Link>
      </p>
    </div>
  );
}
