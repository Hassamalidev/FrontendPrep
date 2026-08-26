/**
 * The review queue.
 *
 * Ordered worst-quality first, which is deliberate: the weakest items are the
 * ones that tell you whether the critic threshold needs moving. Approving the
 * obvious ones first would hide that.
 *
 * Bulk approve exists because a run produces a dozen items at once, but the
 * default is a per-item decision -- a "select all, approve" habit is how a bad
 * question reaches a student.
 */

import { useState } from "react";

import { ApiError } from "@/api/client";
import { admin } from "@/api/endpoints";
import type { QuestionAdmin } from "@/api/types";
import { Check, Close } from "@/components/icons";
import { Alert, Badge, Button, Card, CardHeader, EmptyState, ErrorState, Loading } from "@/components/ui";
import { useAsync } from "@/lib/useAsync";

export function ReviewQueue() {
  const [page, setPage] = useState(1);
  const { data, error, loading, refetch } = useAsync(() => admin.queue(page, 20), [page]);

  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  function toggle(id: number) {
    setSelected((previous) => {
      const next = new Set(previous);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function decide(ids: number[], status: "approved" | "rejected") {
    if (ids.length === 0) return;
    setBusy(true);
    setActionError(null);
    try {
      await admin.bulkReview({ ids, status, note: null });
      setMessage(`${ids.length} question${ids.length === 1 ? "" : "s"} ${status}.`);
      setSelected(new Set());
      refetch();
    } catch (caught) {
      setActionError(caught instanceof ApiError ? caught.message : "Could not apply that.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <Loading label="Loading the queue" />;
  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12">
        <ErrorState error={error} onRetry={refetch} />
      </div>
    );
  }

  const items = data?.items ?? [];

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="font-display text-3xl font-bold text-ink-900">Review queue</h1>
      <p className="mt-2 text-ink-500">
        {data?.total ?? 0} draft{data?.total === 1 ? "" : "s"} waiting. Weakest first — those are
        the ones that show whether the quality threshold is set right.
      </p>

      {message && (
        <div className="mt-4">
          <Alert tone="success">{message}</Alert>
        </div>
      )}
      {actionError && (
        <div className="mt-4">
          <Alert tone="error">{actionError}</Alert>
        </div>
      )}

      {items.length === 0 ? (
        <div className="mt-8">
          <EmptyState
            title="Nothing waiting"
            body="Generated questions land here before students can see them."
          />
        </div>
      ) : (
        <>
          {selected.size > 0 && (
            <Card className="sticky top-20 z-30 mt-6 flex flex-wrap items-center justify-between gap-3 p-4">
              <p className="text-sm font-medium text-ink-800">{selected.size} selected</p>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  loading={busy}
                  onClick={() => void decide([...selected], "rejected")}
                >
                  <Close size={16} /> Reject
                </Button>
                <Button size="sm" loading={busy} onClick={() => void decide([...selected], "approved")}>
                  <Check size={16} /> Approve
                </Button>
              </div>
            </Card>
          )}

          <ul className="mt-6 space-y-4">
            {items.map((question) => (
              <QueueItem
                key={question.id}
                question={question}
                checked={selected.has(question.id)}
                onToggle={() => toggle(question.id)}
                onDecide={(status) => void decide([question.id], status)}
                busy={busy}
              />
            ))}
          </ul>

          {(data?.pages ?? 1) > 1 && (
            <div className="mt-8 flex items-center justify-between">
              <Button variant="secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                Previous
              </Button>
              <p className="text-sm text-ink-500">
                Page {data?.page} of {data?.pages}
              </p>
              <Button
                variant="secondary"
                disabled={page >= (data?.pages ?? 1)}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function QueueItem({
  question,
  checked,
  onToggle,
  onDecide,
  busy,
}: {
  question: QuestionAdmin;
  checked: boolean;
  onToggle: () => void;
  onDecide: (status: "approved" | "rejected") => void;
  busy: boolean;
}) {
  const options = (question.options ?? []) as { key: string; text: string }[];
  const correct = new Set(question.answer_keys ?? []);
  const critique = (question.generation_meta?.critique ?? {}) as {
    breakdown?: Record<string, number>;
    reasons?: string[];
  };

  return (
    <li>
      <Card>
        <CardHeader
          title={
            <label className="flex cursor-pointer items-start gap-3">
              <input
                type="checkbox"
                checked={checked}
                onChange={onToggle}
                className="mt-1"
                aria-label={`Select question ${question.id}`}
              />
              <span className="text-base font-normal text-ink-900">{question.stem}</span>
            </label>
          }
          action={
            <div className="flex shrink-0 gap-2">
              <Badge>{question.qtype.replace(/_/g, " ")}</Badge>
              {question.quality_score !== null && question.quality_score !== undefined && (
                <Badge tone={question.quality_score >= 0.9 ? "green" : "amber"}>
                  {question.quality_score.toFixed(2)}
                </Badge>
              )}
            </div>
          }
        />

        <div className="space-y-4 p-5">
          {options.length > 0 && (
            <ul className="grid gap-1.5 sm:grid-cols-2">
              {options.map((option) => (
                <li
                  key={option.key}
                  className={`rounded-lg px-3 py-1.5 text-sm ring-1 ${
                    correct.has(option.key)
                      ? "bg-success-50 text-ink-800 ring-success-500/40"
                      : "text-ink-600 ring-ink-200"
                  }`}
                >
                  <span className="mr-2 font-mono uppercase text-ink-500">{option.key}</span>
                  {option.text}
                </li>
              ))}
            </ul>
          )}

          {options.length === 0 && (question.answer_keys ?? []).length > 0 && (
            <p className="text-sm text-ink-600">
              Answer:{" "}
              <span className="font-medium text-ink-800">{question.answer_keys.join(", ")}</span>
            </p>
          )}

          {question.explanation && (
            <p className="rounded-lg bg-ink-50 px-3 py-2 text-sm text-ink-600">
              {question.explanation}
            </p>
          )}

          {critique.reasons && critique.reasons.length > 0 && (
            <div>
              <p className="text-xs font-medium uppercase text-ink-500">The critic noted</p>
              <ul className="mt-1 space-y-0.5">
                {critique.reasons.map((reason, index) => (
                  <li key={index} className="text-sm text-ink-600">
                    {reason}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {critique.breakdown && (
            <dl className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-ink-500">
              {Object.entries(critique.breakdown).map(([check, score]) => (
                <div key={check} className="flex gap-1.5">
                  <dt>{check.replace(/_/g, " ")}</dt>
                  <dd className="font-mono tabular-nums text-ink-700">{Number(score).toFixed(2)}</dd>
                </div>
              ))}
            </dl>
          )}

          <div className="flex flex-wrap gap-2 pt-1">
            <Button size="sm" loading={busy} onClick={() => onDecide("approved")}>
              <Check size={16} /> Approve
            </Button>
            <Button size="sm" variant="secondary" loading={busy} onClick={() => onDecide("rejected")}>
              <Close size={16} /> Reject
            </Button>
          </div>
        </div>
      </Card>
    </li>
  );
}
