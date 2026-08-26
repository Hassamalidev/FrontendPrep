import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "@/api/client";
import { issb } from "@/api/endpoints";
import type { GtoResult } from "@/api/types";
import { AnalysisPanel } from "@/components/AnalysisPanel";
import { Clock, Users } from "@/components/icons";
import { Alert, Badge, Button, Card, CardHeader, ErrorState, Loading, TextArea } from "@/components/ui";
import { useAsync } from "@/lib/useAsync";
import { TASK_LABELS } from "./labels";
import { formatDuration } from "@/lib/format";


const VENUES = [
  {
    venue: "indoor" as const,
    heading: "Indoor tasks",
    blurb:
      "Verbal and written, judged on how you think and how you put it across. These are the " +
      "half you can genuinely rehearse alone at a desk.",
  },
  {
    venue: "outdoor" as const,
    heading: "Outdoor tasks",
    blurb:
      "Physical and equipment-bound, judged on how you organise a group over an obstacle. " +
      "Alone you can still plan them, and the plan is most of the mark.",
  },
];

export function GtoTasks() {
  const { data, error, loading, refetch } = useAsync(() => issb.gtoTasks({}), []);

  if (loading) return <Loading label="Loading tasks" />;
  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12">
        <ErrorState error={error} onRetry={refetch} />
      </div>
    );
  }

  const tasks = data?.items ?? [];

  return (
    <div className="mx-auto max-w-4xl px-4 py-12">
      <h1 className="font-display text-3xl font-bold text-ink-900">GTO tasks</h1>
      <p className="mt-2 max-w-2xl text-ink-500">
        The series runs in two halves over days three and four. A genuine group task needs a
        group; what can be practised alone is the part the assessor actually scores -- whether
        your plan sets priorities, allocates people and resources, and survives its own
        constraints.
      </p>

      {VENUES.map(({ venue, heading, blurb }) => {
        const inVenue = tasks.filter((task) => task.venue === venue);
        if (inVenue.length === 0) return null;

        return (
          <section key={venue} aria-labelledby={`${venue}-heading`} className="mt-10">
            <div className="flex items-baseline gap-3">
              <h2
                id={`${venue}-heading`}
                className="font-display text-xl font-bold text-ink-900"
              >
                {heading}
              </h2>
              <span className="text-sm text-ink-500">{inVenue.length} tasks</span>
            </div>
            <p className="mt-1 max-w-2xl text-sm text-ink-500">{blurb}</p>

            <div className="mt-4 space-y-4">
              {inVenue.map((task) => (
                <Link key={task.id} to={`/issb/gto/${task.id}`} className="block">
                  <Card className="p-5 transition hover:ring-2 hover:ring-army-500">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <Badge>{TASK_LABELS[task.task_type] ?? task.task_type}</Badge>
                        <h3 className="mt-2 font-semibold text-ink-900">{task.title}</h3>
                        <p className="mt-1 line-clamp-2 text-sm text-ink-500">{task.brief}</p>
                      </div>
                      <div className="shrink-0 space-y-1 text-right text-xs text-ink-500">
                        <p className="flex items-center justify-end gap-1">
                          <Clock size={14} /> {Math.round(task.planning_seconds / 60)} min to plan
                        </p>
                        <p className="flex items-center justify-end gap-1">
                          <Users size={14} />{" "}
                          {task.group_size === 1 ? "on your own" : `group of ${task.group_size}`}
                        </p>
                      </div>
                    </div>
                  </Card>
                </Link>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}

export function GtoTask() {
  const { id } = useParams<{ id: string }>();
  const taskId = Number(id);

  const { data: task, error, loading, refetch } = useAsync(() => issb.gtoTask(taskId), [taskId]);

  const [plan, setPlan] = useState("");
  const [startedAt] = useState(() => Date.now());
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [result, setResult] = useState<GtoResult | null>(null);

  async function submit() {
    setSubmitting(true);
    setSubmitError(null);
    try {
      setResult(
        await issb.submitGto(taskId, {
          body: plan,
          duration_sec: Math.max(1, Math.floor((Date.now() - startedAt) / 1000)),
        }),
      );
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (caught) {
      setSubmitError(caught instanceof ApiError ? caught.message : "Could not submit your plan.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <Loading label="Loading the brief" />;
  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <ErrorState error={error} onRetry={refetch} />
      </div>
    );
  }
  if (!task) return null;

  if (result) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <p className="text-sm font-medium text-army-600">
          {TASK_LABELS[result.task.task_type] ?? result.task.task_type}
        </p>
        <h1 className="mt-1 font-display text-3xl font-bold text-ink-900">{result.task.title}</h1>

        <div className="mt-8">
          <AnalysisPanel
            analysis={result.analysis}
            summary={<p>{formatDuration(result.duration_sec)} spent planning</p>}
          />
        </div>

        <Card className="mt-6">
          <CardHeader title="Your plan" />
          <p className="whitespace-pre-wrap p-5 text-ink-800">{result.body}</p>
        </Card>

        {result.task.model_solution && (
          <Card className="mt-6">
            <CardHeader
              title="A worked solution"
              subtitle="One good answer, not the only one - compare it against your priorities"
            />
            <p className="whitespace-pre-wrap p-5 text-ink-800">{result.task.model_solution}</p>
          </Card>
        )}

        {result.task.rubric.length > 0 && (
          <Card className="mt-6">
            <CardHeader title="What an assessor looks for" />
            <ul className="divide-y divide-ink-100">
              {result.task.rubric.map((entry, index) => {
                const row = entry as { olq?: string; look_for?: string };
                return (
                  <li key={index} className="px-5 py-3">
                    {row.olq && (
                      <p className="text-xs font-medium uppercase text-army-600">
                        {row.olq.replace(/_/g, " ")}
                      </p>
                    )}
                    <p className="mt-0.5 text-sm text-ink-700">{row.look_for}</p>
                  </li>
                );
              })}
            </ul>
          </Card>
        )}

        <div className="mt-10 flex flex-wrap gap-3">
          <Button onClick={() => setResult(null)}>Try again</Button>
          <Link to="/issb/gto">
            <Button variant="secondary">Other tasks</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <div className="flex flex-wrap items-center gap-2">
        <Badge>{TASK_LABELS[task.task_type] ?? task.task_type}</Badge>
        <Badge tone={task.venue === "indoor" ? "neutral" : "amber"}>
          {task.venue === "indoor" ? "Indoor" : "Outdoor"}
        </Badge>
      </div>
      <h1 className="mt-2 font-display text-3xl font-bold text-ink-900">{task.title}</h1>

      <Card className="mt-6">
        <CardHeader
          title="The brief"
          subtitle={`${Math.round(task.planning_seconds / 60)} minutes to plan`}
        />
        <div className="space-y-5 p-5">
          <p className="whitespace-pre-line leading-relaxed text-ink-800">{task.brief}</p>

          {task.constraints.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-ink-900">Constraints</h3>
              <ul className="mt-2 space-y-1.5">
                {task.constraints.map((constraint, index) => (
                  <li key={index} className="flex gap-2 text-sm text-ink-700">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-danger-500" />
                    <span>{String(constraint)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {task.resources.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-ink-900">Resources</h3>
              <div className="mt-2 flex flex-wrap gap-2">
                {task.resources.map((resource, index) => (
                  <span key={index} className="rounded-full bg-ink-100 px-3 py-1 text-sm text-ink-700">
                    {String(resource)}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </Card>

      <Card className="mt-6">
        <CardHeader title="Your plan" subtitle="Write it as you would present it to the GTO" />
        <div className="space-y-4 p-5">
          {submitError && <Alert tone="error">{submitError}</Alert>}
          <TextArea
            name="plan"
            rows={12}
            value={plan}
            onChange={(event) => setPlan(event.target.value)}
            placeholder="One decision per line."
          />
          <p className="text-xs text-ink-500">
            Each line is read separately, so put one decision on each.
          </p>
          <Button
            size="lg"
            loading={submitting}
            disabled={plan.trim().length < 10}
            onClick={() => void submit()}
          >
            Submit plan
          </Button>
        </div>
      </Card>
    </div>
  );
}
