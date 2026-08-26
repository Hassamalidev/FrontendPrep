/**
 * The measurable properties behind an OLQ read-out, as meters.
 *
 * Each signal is a single ratio against a limit, which the form heuristic puts
 * squarely on a meter rather than a chart. The track is a lighter step of the
 * same ramp so the unfilled remainder still reads as part of the measure.
 *
 * Only the interpretable signals are shown. The raw counts the analyser also
 * emits (word totals, response counts) are facts about the sitting, not
 * qualities of the writing, so they belong in the summary line above.
 */

import type { Analysis } from "@/api/types";

type SignalSpec = { key: string; label: string; help: string };

const SIGNALS: SignalSpec[] = [
  { key: "completion", label: "Completion", help: "Share of items you attempted." },
  { key: "positivity", label: "Positive tone", help: "Constructive versus negative wording." },
  { key: "decisiveness", label: "Decisiveness", help: "Committed wording versus hedging." },
  { key: "speed", label: "Speed", help: "Finishing inside the time, not at the wire." },
];

/** Rates are per-response counts rather than 0-1, so they need their own ceiling. */
const RATES: (SignalSpec & { ceiling: number })[] = [
  { key: "action_rate", label: "Concrete actions", ceiling: 3, help: "Action verbs per response." },
  { key: "social_rate", label: "Involving others", ceiling: 2, help: "Mentions of other people per response." },
];

function Meter({ label, help, value, display }: { label: string; help: string; value: number; display: string }) {
  const percent = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-sm font-medium text-ink-700">{label}</span>
        <span className="font-mono text-sm tabular-nums text-ink-600">{display}</span>
      </div>
      <div
        className="mt-1.5 h-2.5 w-full overflow-hidden rounded-sm bg-army-200/40"
        role="meter"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label}
      >
        <div className="h-full rounded-r-[4px] bg-army-500" style={{ width: `${percent}%` }} />
      </div>
      <p className="mt-1 text-xs text-ink-500">{help}</p>
    </div>
  );
}

export function Signals({ analysis }: { analysis: Analysis }) {
  const signals = (analysis.signals ?? {}) as Record<string, number>;

  return (
    <div className="grid gap-5 sm:grid-cols-2">
      {SIGNALS.map((signal) => {
        const value = Number(signals[signal.key] ?? 0);
        return (
          <Meter
            key={signal.key}
            label={signal.label}
            help={signal.help}
            value={value}
            display={`${Math.round(value * 100)}%`}
          />
        );
      })}

      {RATES.map((rate) => {
        const raw = Number(signals[rate.key] ?? 0);
        return (
          <Meter
            key={rate.key}
            label={rate.label}
            help={rate.help}
            value={raw / rate.ceiling}
            display={raw.toFixed(1)}
          />
        );
      })}
    </div>
  );
}
