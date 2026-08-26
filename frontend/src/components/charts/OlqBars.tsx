/**
 * The Officer Like Quality profile: fifteen nominal categories, one measure.
 *
 * Design decisions, and why:
 *  - **Horizontal bars.** The job is "compare magnitude across categories" and
 *    the category names are long ("Ability to Influence the Group"), which
 *    columns cannot label without rotating text.
 *  - **One hue for every bar.** The qualities are nominal, not ordered, so
 *    colouring bars by their own value would re-encode what bar length already
 *    shows and spend the identity channel for nothing.
 *  - **No legend.** A single series; the heading says what is plotted.
 *  - **A table view.** Identity and value are never colour-only, and the exact
 *    numbers stay available to a screen reader.
 */

import { useId, useState } from "react";

import type { OlqProfile } from "@/api/types";

type Score = OlqProfile["scores"][number];

const MAX = 5;

export function OlqBars({
  scores,
  caption = "Scored 1 to 5 from the language of your responses.",
}: {
  scores: Score[];
  caption?: string;
}) {
  const [showTable, setShowTable] = useState(false);
  const tableId = useId();

  if (scores.length === 0) return null;

  return (
    <figure className="m-0">
      <figcaption className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="text-sm text-ink-500">{caption}</span>
        <button
          type="button"
          onClick={() => setShowTable((open) => !open)}
          aria-expanded={showTable}
          aria-controls={tableId}
          className="text-sm font-medium text-army-600 hover:underline"
        >
          {showTable ? "Hide table" : "View as table"}
        </button>
      </figcaption>

      <ul className="mt-4 space-y-2.5">
        {scores.map((entry) => {
          const width = Math.max(2, (entry.score / MAX) * 100);
          return (
            <li key={entry.olq} className="grid grid-cols-[minmax(0,11rem)_1fr_2.5rem] items-center gap-3">
              <span className="truncate text-sm text-ink-700" title={entry.label}>
                {entry.label}
              </span>

              {/* Track is a lighter step of the same ramp; the fill is the mark. */}
              <span className="h-3.5 w-full overflow-hidden rounded-sm bg-army-200/40">
                <span
                  className="block h-full rounded-r-[4px] bg-army-500"
                  style={{ width: `${width}%` }}
                  title={`${entry.label}: ${entry.score.toFixed(2)} of ${MAX}`}
                />
              </span>

              {/* Value at the tip, in a text token -- never the data colour. */}
              <span className="text-right font-mono text-sm tabular-nums text-ink-600">
                {entry.score.toFixed(1)}
              </span>
            </li>
          );
        })}
      </ul>

      {showTable && (
        <div id={tableId} className="mt-5 overflow-x-auto">
          <table className="w-full text-sm">
            <caption className="sr-only">Officer Like Quality scores, out of 5</caption>
            <thead>
              <tr className="border-b border-ink-200 text-left text-ink-500">
                <th scope="col" className="py-2 pr-4 font-medium">Quality</th>
                <th scope="col" className="py-2 text-right font-medium">Score</th>
              </tr>
            </thead>
            <tbody>
              {scores.map((entry) => (
                <tr key={entry.olq} className="border-b border-ink-100 last:border-0">
                  <th scope="row" className="py-2 pr-4 font-normal text-ink-700">
                    {entry.label}
                  </th>
                  <td className="py-2 text-right font-mono tabular-nums text-ink-700">
                    {entry.score.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </figure>
  );
}
