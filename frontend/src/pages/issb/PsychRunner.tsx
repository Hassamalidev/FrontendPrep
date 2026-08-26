/**
 * The timed psychological battery: WAT, SCT, SRT and TAT in one runner.
 *
 * What makes this the real test rather than a form:
 *
 *  - **The clock advances the item, not the candidate.** At a board the slide
 *    changes on time whether or not you finished. Practising with a Next button
 *    teaches a habit that costs marks on the day.
 *  - **There is no going back.** Same reason.
 *  - **Each item's own limit is used** (WAT 15s, SCT/SRT 30s, TAT four minutes),
 *    taken from the item, not hard-coded here.
 *
 * The whole sitting is submitted at the end as one request, which is also how
 * the backend stores it -- one row with a JSONB response array.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { ApiError } from "@/api/client";
import { issb } from "@/api/endpoints";
import type { PsychSession, PsychTestType } from "@/api/types";
import { Countdown } from "@/components/Countdown";
import { Alert, Button, Card, ErrorState, Loading } from "@/components/ui";

const TEST_NAMES: Record<string, { name: string; short: string; hint: string; multiline: boolean }> = {
  wat: {
    name: "Word Association Test",
    short: "WAT",
    hint: "Write the first complete sentence the word suggests. One line is enough.",
    multiline: false,
  },
  sct: {
    name: "Sentence Completion Test",
    short: "SCT",
    hint: "Finish the sentence in your own words.",
    multiline: false,
  },
  srt: {
    name: "Situation Reaction Test",
    short: "SRT",
    hint: "Say what you would do. Name the action, not the feeling.",
    multiline: true,
  },
  tat: {
    name: "Thematic Apperception Test",
    short: "TAT",
    hint: "Write a story: who the hero is, what led up to this, what they do, and how it ends.",
    multiline: true,
  },
};

const DEFAULT_COUNTS: Record<string, number> = { wat: 15, sct: 12, srt: 10, tat: 4 };

type Response = { item_id: number; text: string; ms: number; skipped: boolean };

export function PsychRunner() {
  const { test } = useParams<{ test: string }>();
  const testType = (test ?? "wat") as PsychTestType;
  const meta = TEST_NAMES[testType] ?? TEST_NAMES.wat;
  const navigate = useNavigate();

  const [session, setSession] = useState<PsychSession | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [count, setCount] = useState(DEFAULT_COUNTS[testType] ?? 10);

  async function begin() {
    setStarting(true);
    setError(null);
    try {
      setSession(await issb.startPsych({ test_type: testType, count }));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not start the test.");
    } finally {
      setStarting(false);
    }
  }

  if (!session) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16">
        <p className="text-sm font-medium text-army-600">{meta.short}</p>
        <h1 className="mt-1 font-display text-3xl font-bold text-ink-900">{meta.name}</h1>
        <p className="mt-3 text-ink-500">{meta.hint}</p>

        <Card className="mt-8 p-6">
          {error && (
            <div className="mb-4">
              <Alert tone="error">{error}</Alert>
            </div>
          )}

          <Alert>
            Once you begin, each item is shown for a fixed time and then moves on by
            itself. You cannot go back — that is how the test is run at a board.
          </Alert>

          <fieldset className="mt-5">
            <legend className="mb-2 text-sm font-medium text-ink-700">How many items?</legend>
            <div className="flex flex-wrap gap-2">
              {[5, 10, 15, 30].map((option) => (
                <button
                  key={option}
                  type="button"
                  aria-pressed={count === option}
                  onClick={() => setCount(option)}
                  className={`rounded-lg px-4 py-2 text-sm font-medium ring-1 transition ${
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

          <Button size="lg" className="mt-6" loading={starting} onClick={() => void begin()}>
            Begin
          </Button>
        </Card>
      </div>
    );
  }

  return <Sitting key={session.id} session={session} meta={meta} onDone={(id) => navigate(`/issb/psych/result/${id}`)} />;
}

function Sitting({
  session,
  meta,
  onDone,
}: {
  session: PsychSession;
  meta: (typeof TEST_NAMES)[string];
  onDone: (sessionId: number) => void;
}) {
  const items = session.items;
  const [index, setIndex] = useState(0);
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Collected across the whole sitting; sent once at the end.
  const responses = useRef<Response[]>([]);
  const shownAt = useRef(0);
  const startedAt = useRef(0);
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement | null>(null);

  useEffect(() => {
    startedAt.current = Date.now();
    shownAt.current = Date.now();
  }, []);

  const item = items[index];
  const finished = index >= items.length;

  const submitAll = useCallback(async () => {
    setSubmitting(true);
    setError(null);
    try {
      const result = await issb.submitPsych(session.id, {
        responses: responses.current,
        duration_sec: Math.max(1, Math.floor((Date.now() - startedAt.current) / 1000)),
      });
      onDone(result.id);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not submit the sitting.");
      setSubmitting(false);
    }
  }, [session.id, onDone]);

  /** Store the current answer and move on. Called by the clock and by Enter. */
  const advance = useCallback(() => {
    const current = items[index];
    if (!current) return;

    const answer = text.trim();
    responses.current.push({
      item_id: current.id,
      text: answer,
      ms: Math.max(0, Date.now() - shownAt.current),
      skipped: answer.length === 0,
    });

    setText("");
    shownAt.current = Date.now();
    setIndex((position) => position + 1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index, items, text]);

  // Submit once the last item has been answered or timed out.
  useEffect(() => {
    if (finished && !submitting && !error) void submitAll();
  }, [finished, submitting, error, submitAll]);

  // Focus the field on each new item so a candidate can type immediately.
  useEffect(() => {
    inputRef.current?.focus();
  }, [index]);

  if (finished) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-24">
        {error ? (
          <ErrorState error={new Error(error)} onRetry={() => void submitAll()} />
        ) : (
          <Loading label="Reading your responses" />
        )}
      </div>
    );
  }
  if (!item) return null;

  const progress = ((index + 1) / items.length) * 100;

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-ink-500">
          {meta.short} · item {index + 1} of {items.length}
        </p>
        <Countdown key={item.id} seconds={item.seconds} onExpire={advance} />
      </div>

      <div
        className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-ink-200"
        role="progressbar"
        aria-valuenow={index + 1}
        aria-valuemin={0}
        aria-valuemax={items.length}
        aria-label="Progress through the sitting"
      >
        <div className="h-full rounded-full bg-army-500" style={{ width: `${progress}%` }} />
      </div>

      <Card className="mt-6 p-6">
        {item.image_url && (
          <img
            src={item.image_url}
            alt=""
            className="mb-5 max-h-72 w-full rounded-lg object-cover"
          />
        )}

        <p
          className={
            meta.short === "WAT"
              ? "text-center font-display text-4xl font-bold text-ink-900"
              : "text-lg leading-relaxed text-ink-900"
          }
        >
          {item.prompt}
        </p>

        <form
          className="mt-6"
          onSubmit={(event) => {
            event.preventDefault();
            advance();
          }}
        >
          <label htmlFor="response" className="sr-only">
            Your response
          </label>
          {meta.multiline ? (
            <textarea
              id="response"
              ref={(node) => {
                inputRef.current = node;
              }}
              rows={5}
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder="Type your response..."
              className="w-full rounded-lg border border-ink-200 px-3 py-2 text-ink-900 placeholder:text-ink-500"
            />
          ) : (
            <input
              id="response"
              ref={(node) => {
                inputRef.current = node;
              }}
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder="Type your response..."
              autoComplete="off"
              className="w-full rounded-lg border border-ink-200 px-3 py-2 text-ink-900 placeholder:text-ink-500"
            />
          )}

          <div className="mt-4 flex items-center justify-between gap-3">
            <p className="text-xs text-ink-500">{meta.hint}</p>
            <Button type="submit" variant="secondary">
              {index === items.length - 1 ? "Finish" : "Next"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
