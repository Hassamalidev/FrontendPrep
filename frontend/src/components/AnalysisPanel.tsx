/**
 * The read-out shared by every projective test.
 *
 * The framing matters as much as the numbers. This is a heuristic measurement
 * of writing, not an assessment of a person, and the copy says so plainly --
 * a candidate who reads a low "Courage" score as a verdict has been misled by
 * the interface, whatever the backend intended.
 */

import { OlqBars } from "@/components/charts/OlqBars";
import { Signals } from "@/components/charts/Signals";
import { Card, CardHeader } from "@/components/ui";
import type { Analysis } from "@/api/types";

export function AnalysisPanel({
  analysis,
  summary,
}: {
  analysis: Analysis;
  summary?: React.ReactNode;
}) {
  const score = analysis.overall_score ?? 0;

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm text-ink-500">Overall</p>
            {/* Hero figure: proportional digits, not tabular -- tabular-nums
                loosens a large standalone number. */}
            <p className="font-display text-5xl font-bold text-ink-900">{Math.round(score)}</p>
            <p className="mt-1 text-sm text-ink-500">out of 100</p>
          </div>
          {summary && <div className="text-sm text-ink-600">{summary}</div>}
        </div>

        <p className="mt-5 rounded-lg bg-ink-50 px-4 py-3 text-sm text-ink-600">
          This is a measurement of your writing — how much you attempted, how
          quickly, how decisively, and whether you described actions and other
          people. It is not an assessment of your character, and a real board
          scores you on far more than words on a page.
        </p>
      </Card>

      <Card>
        <CardHeader
          title="Officer Like Qualities"
          subtitle="What this sitting projected, strongest first"
        />
        <div className="p-5">
          <OlqBars scores={analysis.olq_scores} />
        </div>
      </Card>

      <Card>
        <CardHeader title="What was measured" subtitle="The signals behind those scores" />
        <div className="p-5">
          <Signals analysis={analysis} />
        </div>
      </Card>

      {analysis.feedback.length > 0 && (
        <Card>
          <CardHeader title="What to work on" />
          <ul className="space-y-3 p-5">
            {analysis.feedback.map((note, index) => (
              <li key={index} className="flex gap-3 text-sm text-ink-700">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-army-500" />
                <span>{note}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
