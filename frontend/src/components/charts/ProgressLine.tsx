/**
 * Overall score per sitting, oldest first.
 *
 * Form: trend over time on a single series, so a line -- one hue, 2px, round
 * caps, an end dot with a surface ring, and a recessive hairline grid. No
 * legend (one series; the heading names it) and labels only on the extremes,
 * because a number on every point is noise.
 *
 * Drawn as inline SVG rather than pulling in a chart library: it is one
 * polyline, and the dependency would cost more than the code.
 */

import { useId, useState } from "react";

import type { TrendPoint } from "@/api/types";
import { formatDate } from "@/lib/format";

const WIDTH = 640;
const HEIGHT = 200;
const PAD = { top: 16, right: 20, bottom: 28, left: 34 };

export function ProgressLine({ points }: { points: TrendPoint[] }) {
  const [hovered, setHovered] = useState<number | null>(null);
  const titleId = useId();

  if (points.length < 2) return null;

  const plotWidth = WIDTH - PAD.left - PAD.right;
  const plotHeight = HEIGHT - PAD.top - PAD.bottom;

  // Fixed 0-100 scale: the score is already a percentage-like figure, and a
  // rescaled axis would make a two-point wobble look like a transformation.
  const x = (index: number) => PAD.left + (index / (points.length - 1)) * plotWidth;
  const y = (score: number) => PAD.top + (1 - Math.max(0, Math.min(100, score)) / 100) * plotHeight;

  const path = points.map((p, i) => `${i === 0 ? "M" : "L"} ${x(i)} ${y(p.overall_score)}`).join(" ");
  const best = points.reduce((a, b) => (b.overall_score > a.overall_score ? b : a));
  const bestIndex = points.indexOf(best);
  const last = points.length - 1;

  return (
    <figure className="m-0">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="w-full"
        role="img"
        aria-labelledby={titleId}
      >
        <title id={titleId}>
          Overall score across {points.length} sittings, from{" "}
          {Math.round(points[0].overall_score)} to {Math.round(points[last].overall_score)} out of 100
        </title>

        {[0, 25, 50, 75, 100].map((tick) => (
          <g key={tick}>
            <line
              x1={PAD.left}
              x2={WIDTH - PAD.right}
              y1={y(tick)}
              y2={y(tick)}
              stroke="var(--color-ink-200)"
              strokeWidth={1}
            />
            <text
              x={PAD.left - 8}
              y={y(tick) + 4}
              textAnchor="end"
              className="fill-ink-500"
              style={{ fontSize: 10 }}
            >
              {tick}
            </text>
          </g>
        ))}

        <path d={path} fill="none" stroke="var(--color-army-500)" strokeWidth={2}
              strokeLinecap="round" strokeLinejoin="round" />

        {points.map((point, index) => (
          <g key={point.id}>
            {/* Hit target larger than the mark, per the interaction spec. */}
            <circle
              cx={x(index)}
              cy={y(point.overall_score)}
              r={12}
              fill="transparent"
              onMouseEnter={() => setHovered(index)}
              onMouseLeave={() => setHovered(null)}
            />
            <circle
              cx={x(index)}
              cy={y(point.overall_score)}
              r={index === last || index === hovered ? 5 : 3.5}
              fill="var(--color-army-500)"
              stroke="white"
              strokeWidth={2}
            />
          </g>
        ))}

        {/* Selective direct labels: the best sitting and the latest one. */}
        {[bestIndex, last].filter((v, i, a) => a.indexOf(v) === i).map((index) => (
          <text
            key={index}
            x={x(index)}
            y={y(points[index].overall_score) - 12}
            textAnchor={index === last ? "end" : "middle"}
            className="fill-ink-700"
            style={{ fontSize: 11, fontWeight: 600 }}
          >
            {Math.round(points[index].overall_score)}
          </text>
        ))}
      </svg>

      <figcaption className="mt-2 flex items-baseline justify-between gap-3 text-sm text-ink-500">
        <span>{formatDate(points[0].submitted_at)}</span>
        <span>
          {hovered !== null
            ? `${points[hovered].test_type.toUpperCase()} — ${Math.round(points[hovered].overall_score)} of 100 (${points[hovered].answered}/${points[hovered].items} attempted)`
            : `${points.length} sittings`}
        </span>
        <span>{formatDate(points[last].submitted_at)}</span>
      </figcaption>
    </figure>
  );
}
