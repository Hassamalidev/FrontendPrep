import { useState } from "react";

import { ApiError } from "@/api/client";
import { admin } from "@/api/endpoints";
import { Alert, Button, Card, CardHeader, ErrorState, Loading } from "@/components/ui";
import { useAsync } from "@/lib/useAsync";

export function Maintenance() {
  const { data, error, loading, refetch } = useAsync(() => admin.size(), []);
  const [busy, setBusy] = useState<"prune" | "recount" | null>(null);
  const [report, setReport] = useState<Record<string, number> | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  async function prune() {
    setBusy("prune");
    setActionError(null);
    setMessage(null);
    try {
      setReport(await admin.prune());
      refetch();
    } catch (caught) {
      setActionError(caught instanceof ApiError ? caught.message : "Could not run the job.");
    } finally {
      setBusy(null);
    }
  }

  async function recount() {
    setBusy("recount");
    setActionError(null);
    setReport(null);
    try {
      const result = await admin.recount();
      setMessage(result.detail);
      refetch();
    } catch (caught) {
      setActionError(caught instanceof ApiError ? caught.message : "Could not recount.");
    } finally {
      setBusy(null);
    }
  }

  if (loading) return <Loading label="Loading" />;
  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <ErrorState error={error} onRetry={refetch} />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="font-display text-3xl font-bold text-ink-900">Maintenance</h1>
      <p className="mt-2 text-ink-500">
        The deployment targets a 0.5 GB database. The retention job is what keeps it there.
      </p>

      <Card className="mt-8">
        <CardHeader title="Row counts" subtitle="The tables that grow without bound" />
        <dl className="grid grid-cols-2 gap-px bg-ink-100 sm:grid-cols-4">
          {Object.entries(data ?? {}).map(([table, count]) => (
            <div key={table} className="bg-white px-4 py-3">
              <dt className="text-xs text-ink-500">{table.replace(/_/g, " ")}</dt>
              <dd className="mt-0.5 font-mono text-lg tabular-nums text-ink-900">
                {count.toLocaleString()}
              </dd>
            </div>
          ))}
        </dl>
      </Card>

      {actionError && (
        <div className="mt-6">
          <Alert tone="error">{actionError}</Alert>
        </div>
      )}
      {message && (
        <div className="mt-6">
          <Alert tone="success">{message}</Alert>
        </div>
      )}

      <Card className="mt-6">
        <CardHeader
          title="Retention job"
          subtitle="Drops detail only. Scores, counts and summaries are kept forever."
        />
        <div className="space-y-4 p-5">
          <ul className="space-y-1.5 text-sm text-ink-600">
            <li>Expires attempts whose clock ran out but were never submitted</li>
            <li>Keeps only the most recent agent traces</li>
            <li>Drops raw article bodies once questions have been generated from them</li>
            <li>Drops per-answer JSON from old attempts, keeping the score line</li>
            <li>Deletes dead sessions, old audit rows and resolved reports</li>
          </ul>

          <div className="flex flex-wrap gap-3">
            <Button loading={busy === "prune"} onClick={() => void prune()}>
              Run the retention job
            </Button>
            <Button variant="secondary" loading={busy === "recount"} onClick={() => void recount()}>
              Refresh question counters
            </Button>
          </div>

          {report && (
            <div className="rounded-lg bg-ink-50 p-4">
              <p className="text-sm font-medium text-ink-800">What it did</p>
              <dl className="mt-2 space-y-1">
                {Object.entries(report).map(([step, rows]) => (
                  <div key={step} className="flex justify-between gap-4 text-sm">
                    <dt className="text-ink-600">{step.replace(/_/g, " ")}</dt>
                    <dd className="font-mono tabular-nums text-ink-800">{rows}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
