/**
 * The run trace.
 *
 * This is the reason the generator is built as a pipeline rather than one
 * function: an operator can see *why* 29 drafts became 10 questions, and tune
 * the threshold instead of guessing. Showing only the final count would make
 * the engine a black box, which is exactly what the no-API-key design was
 * meant to avoid.
 */

import type { AgentRun } from "@/api/types";
import { Badge, Card, CardHeader } from "@/components/ui";

const AGENT_LABELS: Record<string, string> = {
  input: "Input",
  extract: "Extract facts",
  summarise: "Summarise",
  write: "Draft questions",
  critique: "Critique and select",
  issb: "ISSB items",
};

export function AgentTrace({ run }: { run: AgentRun }) {
  const steps = (run.trace ?? []) as {
    agent: string;
    label?: string;
    in: number;
    out: number;
    ms: number;
    notes?: string[];
  }[];

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="Run summary"
          subtitle={`${run.engine} engine · ${run.duration_ms}ms`}
          action={
            <Badge
              tone={
                run.status === "succeeded" ? "green" : run.status === "failed" ? "red" : "amber"
              }
            >
              {run.status}
            </Badge>
          }
        />
        <dl className="grid grid-cols-2 gap-px bg-ink-100 sm:grid-cols-4">
          {[
            ["Facts found", run.facts_found],
            ["Drafted", run.candidates],
            ["Accepted", run.accepted],
            ["Rejected", run.rejected],
            ["Duplicates", run.duplicates],
            ["Avg quality", run.avg_quality?.toFixed(3) ?? "--"],
          ].map(([label, value]) => (
            <div key={String(label)} className="bg-white px-4 py-3">
              <dt className="text-xs text-ink-500">{label}</dt>
              <dd className="mt-0.5 font-mono text-lg tabular-nums text-ink-900">{value}</dd>
            </div>
          ))}
        </dl>
      </Card>

      {steps.length > 0 && (
        <Card>
          <CardHeader title="Pipeline" subtitle="Each agent, in the order it ran" />
          <ol className="divide-y divide-ink-100">
            {steps.map((step, index) => (
              <li key={index} className="px-5 py-4">
                <div className="flex flex-wrap items-baseline justify-between gap-3">
                  <p className="font-medium text-ink-900">
                    {AGENT_LABELS[step.agent] ?? step.agent}
                    {step.label && <span className="ml-2 text-sm text-ink-500">{step.label}</span>}
                  </p>
                  <p className="font-mono text-sm tabular-nums text-ink-600">
                    {step.in} in → {step.out} out · {step.ms}ms
                  </p>
                </div>
                {step.notes && step.notes.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {step.notes.map((note, noteIndex) => (
                      <li key={noteIndex} className="text-sm text-ink-500">
                        {note}
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ol>
        </Card>
      )}

      {(run.rejections ?? []).length > 0 && (
        <Card>
          <CardHeader
            title="Why items were rejected"
            subtitle="A sample, for tuning the quality threshold"
          />
          <ul className="divide-y divide-ink-100">
            {(run.rejections as { stem: string; score: number; reasons: string[] }[]).map(
              (rejection, index) => (
                <li key={index} className="px-5 py-3">
                  <div className="flex items-baseline justify-between gap-3">
                    <p className="min-w-0 text-sm text-ink-700">{rejection.stem}</p>
                    <span className="shrink-0 font-mono text-sm tabular-nums text-danger-500">
                      {rejection.score.toFixed(2)}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-ink-500">{rejection.reasons.join(" · ")}</p>
                </li>
              ),
            )}
          </ul>
        </Card>
      )}

      {run.error && (
        <Card className="p-5">
          <p className="text-sm font-medium text-danger-500">The run reported a problem</p>
          <p className="mt-1 text-sm text-ink-600">{run.error}</p>
        </Card>
      )}
    </div>
  );
}
