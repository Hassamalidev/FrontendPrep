/**
 * The per-item clock.
 *
 * Auto-advance is the defining property of the psychological battery: at an
 * ISSB the slide changes whether or not you have finished, and practising
 * without that pressure teaches the wrong habit. So this fires `onExpire`
 * rather than merely turning red.
 *
 * The caller gives it a `key` per item, so each item gets a fresh instance and
 * the countdown starts from its own state rather than being reset by an effect.
 */

import { useEffect, useRef, useState } from "react";

import { Clock } from "@/components/icons";

export function Countdown({
  seconds,
  onExpire,
  paused = false,
}: {
  seconds: number;
  onExpire: () => void;
  paused?: boolean;
}) {
  const [remaining, setRemaining] = useState(seconds);

  // Held in a ref so a new callback identity on the parent's re-render does not
  // tear down and restart the interval, which would make the clock drift.
  const expireRef = useRef(onExpire);
  useEffect(() => {
    expireRef.current = onExpire;
  }, [onExpire]);

  useEffect(() => {
    if (paused) return;

    const timer = window.setInterval(() => {
      setRemaining((left) => {
        if (left <= 1) {
          window.clearInterval(timer);
          // Deferred: firing the parent's state update from inside the tick
          // would update another component while this one is rendering.
          queueMicrotask(() => expireRef.current());
          return 0;
        }
        return left - 1;
      });
    }, 1000);

    return () => window.clearInterval(timer);
  }, [paused]);

  const fraction = seconds > 0 ? remaining / seconds : 0;
  const urgent = fraction <= 0.25;

  return (
    <div className="flex items-center gap-3">
      <span
        className={`flex items-center gap-1.5 font-mono text-sm tabular-nums ${
          urgent ? "text-danger-500" : "text-ink-600"
        }`}
        role="timer"
        aria-live="off"
      >
        <Clock size={16} />
        {remaining}s
      </span>
      <span className="h-1.5 w-24 overflow-hidden rounded-full bg-army-200/40">
        <span
          className={`block h-full ${urgent ? "bg-danger-500" : "bg-army-500"}`}
          style={{ width: `${fraction * 100}%`, transition: "width 1s linear" }}
        />
      </span>
    </div>
  );
}
