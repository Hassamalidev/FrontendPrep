import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ApiError } from "@/api/client";
import type { ServiceCode } from "@/api/types";
import { useAuth } from "@/auth/useAuth";
import { Alert, Button, Card, Field } from "@/components/ui";

const SERVICES: { value: ServiceCode; label: string }[] = [
  { value: "army", label: "Pakistan Army" },
  { value: "air_force", label: "Pakistan Air Force" },
  { value: "navy", label: "Pakistan Navy" },
];

export function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    city: "",
    target_service: "army" as ServiceCode,
  });
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  function update<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((previous) => ({ ...previous, [key]: value }));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setFieldErrors({});

    try {
      await register(form);
      navigate("/dashboard", { replace: true });
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
      <h1 className="font-display text-2xl font-bold text-ink-900">Create your account</h1>
      <p className="mt-1 text-sm text-ink-500">Free, and your progress is saved as you go.</p>

      <Card className="mt-6 p-6">
        <form onSubmit={onSubmit} noValidate className="space-y-4">
          {error && <Alert tone="error">{error}</Alert>}

          <Field
            label="Full name"
            name="full_name"
            autoComplete="name"
            required
            value={form.full_name}
            onChange={(e) => update("full_name", e.target.value)}
            error={fieldErrors.full_name}
          />
          <Field
            label="Email"
            name="email"
            type="email"
            autoComplete="email"
            required
            value={form.email}
            onChange={(e) => update("email", e.target.value)}
            error={fieldErrors.email}
          />
          <Field
            label="Password"
            name="password"
            type="password"
            autoComplete="new-password"
            required
            value={form.password}
            onChange={(e) => update("password", e.target.value)}
            error={fieldErrors.password}
            hint="At least 8 characters, mixing letters with numbers or symbols."
          />
          <Field
            label="City"
            name="city"
            autoComplete="address-level2"
            value={form.city}
            onChange={(e) => update("city", e.target.value)}
            error={fieldErrors.city}
          />

          <div>
            <label htmlFor="target_service" className="mb-1.5 block text-sm font-medium text-ink-700">
              Which service are you preparing for?
            </label>
            <select
              id="target_service"
              className="w-full rounded-lg border border-ink-200 bg-white px-3 py-2 text-ink-900"
              value={form.target_service}
              onChange={(e) => update("target_service", e.target.value as ServiceCode)}
            >
              {SERVICES.map((service) => (
                <option key={service.value} value={service.value}>
                  {service.label}
                </option>
              ))}
            </select>
          </div>

          <Button type="submit" size="lg" loading={submitting} className="w-full">
            Create account
          </Button>
        </form>
      </Card>

      <p className="mt-6 text-center text-sm text-ink-500">
        Already registered?{" "}
        <Link to="/login" className="font-medium text-army-600 hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}
