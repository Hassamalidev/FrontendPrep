import { useState, type FormEvent } from "react";

import { ApiError } from "@/api/client";
import { catalog, fitness, me as meApi } from "@/api/endpoints";
import type { ServiceCode } from "@/api/types";
import { Alert, Badge, Button, Card, CardHeader, ErrorState, Field, Loading } from "@/components/ui";
import { useAuth } from "@/auth/useAuth";
import { useAsync } from "@/lib/useAsync";
import { formatDate } from "@/lib/format";

const SERVICES: { value: ServiceCode; label: string }[] = [
  { value: "army", label: "Pakistan Army" },
  { value: "air_force", label: "Pakistan Air Force" },
  { value: "navy", label: "Pakistan Navy" },
];

const METRICS = [
  { key: "run_1600m_sec", label: "1600m run (seconds)" },
  { key: "push_ups", label: "Push-ups" },
  { key: "sit_ups", label: "Sit-ups" },
  { key: "chin_ups", label: "Chin-ups" },
  { key: "weight_kg", label: "Weight (kg)" },
];

export function Profile() {
  const { user, applyUser } = useAuth();
  const { data: programs } = useAsync(() => catalog.programs(), []);

  const [form, setForm] = useState({
    full_name: user?.full_name ?? "",
    phone: user?.phone ?? "",
    city: user?.city ?? "",
    date_of_birth: user?.date_of_birth ?? "",
    height_cm: user?.height_cm ?? "",
    weight_kg: user?.weight_kg ?? "",
    target_service: (user?.target_service ?? "") as ServiceCode | "",
    target_program_id: user?.target_program_id ?? ("" as number | ""),
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  async function save(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setSaved(false);
    setError(null);
    setFieldErrors({});
    try {
      const updated = await meApi.update({
        full_name: form.full_name,
        phone: form.phone || null,
        city: form.city || null,
        date_of_birth: form.date_of_birth || null,
        height_cm: form.height_cm === "" ? null : Number(form.height_cm),
        weight_kg: form.weight_kg === "" ? null : Number(form.weight_kg),
        target_service: form.target_service || null,
        target_program_id: form.target_program_id === "" ? null : Number(form.target_program_id),
      });
      applyUser(updated);
      setSaved(true);
    } catch (caught) {
      if (caught instanceof ApiError) {
        setError(caught.message);
        setFieldErrors(caught.fieldErrors);
      } else {
        setError("Could not save your profile.");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="font-display text-3xl font-bold text-ink-900">Your profile</h1>

      <Card className="mt-8">
        <CardHeader title="Details" subtitle="Used to match you against the right standards" />
        <form onSubmit={save} noValidate className="space-y-4 p-5">
          {error && <Alert tone="error">{error}</Alert>}
          {saved && <Alert tone="success">Saved.</Alert>}

          <div className="grid gap-4 sm:grid-cols-2">
            <Field
              label="Full name"
              name="full_name"
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              error={fieldErrors.full_name}
            />
            <Field
              label="Phone"
              name="phone"
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
              error={fieldErrors.phone}
            />
            <Field
              label="City"
              name="city"
              value={form.city}
              onChange={(e) => setForm({ ...form, city: e.target.value })}
            />
            <Field
              label="Date of birth"
              name="date_of_birth"
              type="date"
              value={form.date_of_birth}
              onChange={(e) => setForm({ ...form, date_of_birth: e.target.value })}
            />
            <Field
              label="Height (cm)"
              name="height_cm"
              type="number"
              step="0.1"
              value={form.height_cm}
              onChange={(e) => setForm({ ...form, height_cm: e.target.value })}
              error={fieldErrors.height_cm}
            />
            <Field
              label="Weight (kg)"
              name="weight_kg"
              type="number"
              step="0.1"
              value={form.weight_kg}
              onChange={(e) => setForm({ ...form, weight_kg: e.target.value })}
              error={fieldErrors.weight_kg}
            />

            <div>
              <label htmlFor="service" className="mb-1.5 block text-sm font-medium text-ink-700">
                Service
              </label>
              <select
                id="service"
                value={form.target_service}
                onChange={(e) =>
                  setForm({ ...form, target_service: e.target.value as ServiceCode | "" })
                }
                className="w-full rounded-lg border border-ink-200 bg-white px-3 py-2"
              >
                <option value="">Not decided</option>
                {SERVICES.map((service) => (
                  <option key={service.value} value={service.value}>
                    {service.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="program" className="mb-1.5 block text-sm font-medium text-ink-700">
                Entry scheme
              </label>
              <select
                id="program"
                value={form.target_program_id}
                onChange={(e) =>
                  setForm({
                    ...form,
                    target_program_id: e.target.value === "" ? "" : Number(e.target.value),
                  })
                }
                className="w-full rounded-lg border border-ink-200 bg-white px-3 py-2"
              >
                <option value="">Not decided</option>
                {(programs ?? []).map((program) => (
                  <option key={program.id} value={program.id}>
                    {program.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <Button type="submit" loading={saving}>
            Save
          </Button>
        </form>
      </Card>

      <FitnessLog />
    </div>
  );
}

/**
 * The physical training log.
 *
 * Measured against the standards on the student's chosen entry scheme, because
 * "15 push-ups" only means something next to the bar it has to clear. Timed
 * events pass when lower, counted events when higher -- the API decides which
 * is which, so the UI just renders the verdict.
 */
function FitnessLog() {
  const { data, error, loading, refetch } = useAsync(() => fitness.progress(), []);
  const [entry, setEntry] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [logError, setLogError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const metrics: Record<string, number> = {};
    for (const [key, value] of Object.entries(entry)) {
      if (value !== "") metrics[key] = Number(value);
    }
    if (Object.keys(metrics).length === 0) return;

    setSaving(true);
    setLogError(null);
    try {
      await fitness.log({ metrics, logged_on: null, note: null });
      setEntry({});
      refetch();
    } catch (caught) {
      setLogError(caught instanceof ApiError ? caught.message : "Could not save that entry.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <Loading label="Loading your training log" />;
  if (error) {
    return (
      <div className="mt-8">
        <ErrorState error={error} onRetry={refetch} />
      </div>
    );
  }

  const gaps = data?.gaps ?? [];

  return (
    <>
      <Card className="mt-8">
        <CardHeader title="Physical training" subtitle="Log today's session" />
        <form onSubmit={submit} className="space-y-4 p-5">
          {logError && <Alert tone="error">{logError}</Alert>}

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {METRICS.map((metric) => (
              <Field
                key={metric.key}
                label={metric.label}
                name={metric.key}
                type="number"
                step="0.1"
                value={entry[metric.key] ?? ""}
                onChange={(event) =>
                  setEntry((previous) => ({ ...previous, [metric.key]: event.target.value }))
                }
              />
            ))}
          </div>

          <Button type="submit" loading={saving}>
            Add entry
          </Button>
        </form>
      </Card>

      {data?.bmi !== null && data?.bmi !== undefined && (
        <Card className="mt-6 p-5">
          <p className="text-sm text-ink-500">Body mass index</p>
          <p className="font-display text-3xl font-bold text-ink-900">{data.bmi}</p>
          <p className="mt-1 text-sm text-ink-500">
            Selection boards use BMI as one screen among several, not as a pass mark on its own.
          </p>
        </Card>
      )}

      {gaps.length > 0 && (
        <Card className="mt-6">
          <CardHeader
            title="Against your standard"
            subtitle="The requirement for the scheme on your profile"
          />
          <ul className="divide-y divide-ink-100">
            {gaps.map((gap, index) => {
              const row = gap as {
                metric: string;
                current: number;
                target: number;
                met: boolean;
                delta: number;
              };
              return (
                <li key={index} className="flex items-center justify-between gap-4 px-5 py-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-ink-800">
                      {row.metric.replace(/_/g, " ")}
                    </p>
                    <p className="text-xs text-ink-500">
                      you {row.current} · needs {row.target}
                    </p>
                  </div>
                  <Badge tone={row.met ? "green" : "amber"}>
                    {row.met ? "Met" : `${row.delta} to go`}
                  </Badge>
                </li>
              );
            })}
          </ul>
        </Card>
      )}

      {(data?.logs ?? []).length > 0 && (
        <Card className="mt-6">
          <CardHeader title="Recent entries" />
          <ul className="divide-y divide-ink-100">
            {(data?.logs ?? []).slice(0, 10).map((log) => (
              <li key={log.id} className="px-5 py-3">
                <p className="text-sm text-ink-500">{formatDate(log.logged_on)}</p>
                <dl className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm">
                  {Object.entries(log.metrics as Record<string, number>).map(([key, value]) => (
                    <div key={key} className="flex gap-1.5">
                      <dt className="text-ink-500">{key.replace(/_/g, " ")}</dt>
                      <dd className="font-mono tabular-nums text-ink-800">{value}</dd>
                    </div>
                  ))}
                </dl>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </>
  );
}
