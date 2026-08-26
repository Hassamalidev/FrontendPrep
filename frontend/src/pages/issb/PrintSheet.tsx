/**
 * A practice sheet to print and solve by hand.
 *
 * This is the half of the loop the platform was missing. The real tests are
 * written by hand, at speed, on numbered paper -- and writing fast enough to
 * finish sixty WAT sentences is a physical skill you cannot rehearse by typing.
 * Print this, solve it under a clock, then photograph it on the upload page.
 *
 * The numbering matters twice over: it is how a candidate keeps their place,
 * and it is what lets the reader match a line back to the word it answers.
 */

import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { sheets } from "@/api/endpoints";
import type { PsychTestType } from "@/api/types";
import { Alert, Button, Card, ErrorState, Loading } from "@/components/ui";
import { useAsync } from "@/lib/useAsync";

const COUNTS = [10, 20, 30, 60];

export function PrintSheet() {
  const [params, setParams] = useSearchParams();
  const testType = (params.get("test") ?? "srt") as PsychTestType;
  const [count, setCount] = useState(Number(params.get("count") ?? 20));

  const { data, error, loading, refetch } = useAsync(
    () => sheets.plan(testType, count),
    [testType, count],
  );

  if (loading) return <Loading label="Building your sheet" />;
  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <ErrorState error={error} onRetry={refetch} />
      </div>
    );
  }
  if (!data) return null;

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      {/* Controls are hidden when printing -- only the sheet should reach paper. */}
      <div className="print:hidden">
        <h1 className="font-display text-3xl font-bold text-ink-900">{data.title}</h1>
        <p className="mt-2 text-ink-500">
          Print this, solve it under a clock, then photograph it on the upload page for the
          same analysis you would get online.
        </p>

        <Card className="mt-6 p-5">
          <div className="flex flex-wrap items-end gap-4">
            <div>
              <label htmlFor="test" className="mb-1.5 block text-sm font-medium text-ink-700">
                Test
              </label>
              <select
                id="test"
                value={testType}
                onChange={(event) => {
                  params.set("test", event.target.value);
                  setParams(params);
                }}
                className="rounded-lg border border-ink-200 bg-white px-3 py-2"
              >
                <option value="wat">Word Association</option>
                <option value="sct">Sentence Completion</option>
                <option value="srt">Situation Reaction</option>
              </select>
            </div>

            <fieldset>
              <legend className="mb-1.5 text-sm font-medium text-ink-700">Items</legend>
              <div className="flex gap-2">
                {COUNTS.map((option) => (
                  <button
                    key={option}
                    type="button"
                    aria-pressed={count === option}
                    onClick={() => setCount(option)}
                    className={`rounded-lg px-3 py-2 text-sm font-medium ring-1 transition ${
                      count === option
                        ? "bg-army-500 text-white ring-army-500"
                        : "bg-white text-ink-700 ring-ink-200 hover:bg-ink-50"
                    }`}
                  >
                    {option}
                  </button>
                ))}
              </div>
            </fieldset>

            <Button onClick={() => window.print()}>Print</Button>
            <Link to="/issb/upload">
              <Button variant="secondary">Upload a solved sheet</Button>
            </Link>
          </div>

          <div className="mt-4">
            <Alert>
              These stimuli are drawn fresh each time. Print the sheet you are about to solve —
              a different set will not line up when you upload it.
            </Alert>
          </div>
        </Card>
      </div>

      {/* --- the sheet itself ------------------------------------------- */}
      <article className="mt-8 print:mt-0">
        <header className="border-b-2 border-ink-800 pb-3">
          <h2 className="font-display text-2xl font-bold text-ink-900">{data.title}</h2>
          <div className="mt-2 flex flex-wrap gap-x-8 gap-y-1 text-sm text-ink-600">
            <span>Name: ________________________</span>
            <span>Date: ____________</span>
            <span>
              {data.items.length} items · about {data.total_minutes} minutes ·{" "}
              {data.seconds_per_item}s each
            </span>
          </div>
        </header>

        {data.instructions.length > 0 && (
          <ol className="mt-4 list-inside list-decimal space-y-1 text-sm text-ink-700">
            {data.instructions.map((line, index) => (
              <li key={index}>{line}</li>
            ))}
          </ol>
        )}

        <ol className="mt-6 space-y-5">
          {data.items.map((item, index) => (
            <li key={item.id} className="break-inside-avoid">
              <div className="flex gap-3">
                <span className="w-7 shrink-0 text-right font-mono text-sm text-ink-700">
                  {index + 1}.
                </span>
                <div className="min-w-0 flex-1">
                  <p
                    className={
                      testType === "wat"
                        ? "font-display text-lg font-bold text-ink-900"
                        : "text-ink-900"
                    }
                  >
                    {item.prompt}
                  </p>
                  {/* Ruled space to write in. Two lines for a sentence-length
                      answer, four when the answer is a short paragraph. */}
                  <div className="mt-2 space-y-4">
                    {Array.from({ length: testType === "srt" ? 2 : 1 }).map((_, line) => (
                      <div key={line} className="border-b border-ink-300" />
                    ))}
                  </div>
                </div>
              </div>
            </li>
          ))}
        </ol>

        <footer className="mt-8 border-t border-ink-200 pt-3 text-xs text-ink-500">
          Frontline Prep practice sheet. Number every answer so it can be matched back when you
          upload the photograph.
        </footer>
      </article>
    </div>
  );
}
