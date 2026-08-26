/**
 * The timed paper.
 *
 * Constraints that shaped this screen:
 *
 *  - **Answers survive a reload.** A dropped connection or an accidental back
 *    gesture mid-paper must not cost the sitting, so selections are mirrored to
 *    sessionStorage keyed by attempt id and restored on mount.
 *  - **Per-question timing is recorded.** The backend uses `ms` for difficulty
 *    calibration, so the clock starts when a question is shown, not when the
 *    paper starts.
 *  - **One question at a time.** On a phone, a scrolling list of thirty
 *    questions is where candidates lose track of what they have answered.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import { ApiError } from "@/api/client";
import { practice } from "@/api/endpoints";
import type { Attempt as AttemptType } from "@/api/types";
import { Check, ChevronLeft, ChevronRight, Clock, Flag } from "@/components/icons";
import { Alert, Button, Card, ErrorState, Loading } from "@/components/ui";
import { useAsync } from "@/lib/useAsync";
import { formatClock } from "@/lib/format";

type Selection = { picked: string[]; ms: number; flagged: boolean };
type Answers = Record<number, Selection>;

const storageKey = (id: number) => `issb.attempt.${id}`;

function loadSaved(id: number): Answers {
  try {
    const raw = sessionStorage.getItem(storageKey(id));
    return raw ? (JSON.parse(raw) as Answers) : {};
  } catch {
    return {};
  }
}

function persist(id: number, answers: Answers): void {
  try {
    sessionStorage.setItem(storageKey(id), JSON.stringify(answers));
  } catch {
    /* a paper that cannot be cached still works, it just cannot be resumed */
  }
}

/**
 * Loader. Kept separate from the paper below so that `Paper` can initialise its
 * state from sessionStorage with a lazy initialiser rather than an effect --
 * the attempt is guaranteed to exist by the time it mounts, and `key` gives it
 * a fresh state slot per paper.
 */
export function Attempt() {
  const { id } = useParams<{ id: string }>();
  const attemptId = Number(id);
  const location = useLocation();

  // The start call already returned the paper; reuse it rather than refetching.
  const preloaded = (location.state as { attempt?: AttemptType } | null)?.attempt;

  const { data: fetched, error, loading, refetch } = useAsync(
    () => practice.resume(attemptId),
    [attemptId],
    { enabled: !preloaded },
  );

  const attempt = preloaded ?? fetched;

  if (loading) return <Loading label="Loading your paper" />;
  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <ErrorState error={error} onRetry={refetch} />
      </div>
    );
  }
  if (!attempt) return null;

  return <Paper key={attempt.id} attempt={attempt} />;
}

function Paper({ attempt }: { attempt: AttemptType }) {
  const navigate = useNavigate();
  const questions = useMemo(() => attempt.questions ?? [], [attempt]);

  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Answers>(() => loadSaved(attempt.id));
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);

  // Stamped on mount rather than at render: a ref initialiser runs on every
  // render, and calling Date.now() there is impure even though the value is
  // discarded after the first pass.
  const startedAt = useRef(0);
  const shownAt = useRef(0);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    startedAt.current = Date.now();
    shownAt.current = Date.now();

    const timer = window.setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedAt.current) / 1000));
    }, 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    shownAt.current = Date.now();
  }, [index]);

  const current = questions[index];

  const record = useCallback(
    (update: (previous: Selection) => Selection) => {
      if (!current) return;
      setAnswers((previous) => {
        const existing = previous[current.id] ?? { picked: [], ms: 0, flagged: false };
        const next = { ...previous, [current.id]: update(existing) };
        persist(attempt.id, next);
        return next;
      });
    },
    [current, attempt],
  );

  function choose(key: string) {
    const spent = Date.now() - shownAt.current;
    record((previous) => ({
      ...previous,
      // Multi-select toggles; every other type replaces the selection.
      picked:
        current?.qtype === "multi_select"
          ? previous.picked.includes(key)
            ? previous.picked.filter((k) => k !== key)
            : [...previous.picked, key]
          : [key],
      ms: previous.ms + spent,
    }));
    shownAt.current = Date.now();
  }

  function toggleFlag() {
    record((previous) => ({ ...previous, flagged: !previous.flagged }));
  }

  async function submit() {
    setSubmitting(true);
    setSubmitError(null);

    try {
      await practice.submit(attempt.id, {
        answers: Object.entries(answers).map(([questionId, selection]) => ({
          id: Number(questionId),
          picked: selection.picked,
          ms: selection.ms,
          flagged: selection.flagged,
        })),
        duration_sec: Math.floor((Date.now() - startedAt.current) / 1000),
      });
      try {
        sessionStorage.removeItem(storageKey(attempt.id));
      } catch {
        /* ignore */
      }
      navigate(`/attempts/${attempt.id}/result`, { replace: true });
    } catch (caught) {
      setSubmitError(
        caught instanceof ApiError ? caught.message : "Could not submit. Check your connection.",
      );
      setConfirming(false);
    } finally {
      setSubmitting(false);
    }
  }

  if (!current) return null;

  const answeredCount = Object.values(answers).filter((a) => a.picked.length > 0).length;
  const selection = answers[current.id] ?? { picked: [], ms: 0, flagged: false };

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm text-ink-500">
            Question {index + 1} of {questions.length}
          </p>
          <p className="text-sm text-ink-500">{answeredCount} answered</p>
        </div>
        <p className="flex items-center gap-2 font-mono text-lg text-ink-700">
          <Clock size={18} />
          {formatClock(elapsed)}
        </p>
      </div>

      <div
        className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-ink-200"
        role="progressbar"
        aria-valuenow={answeredCount}
        aria-valuemin={0}
        aria-valuemax={questions.length}
        aria-label="Questions answered"
      >
        <div
          className="h-full rounded-full bg-army-500 transition-all"
          style={{ width: `${(answeredCount / questions.length) * 100}%` }}
        />
      </div>

      <Card className="mt-6 p-6">
        <div className="flex items-start justify-between gap-4">
          <p className="text-lg leading-relaxed text-ink-900">{current.stem}</p>
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleFlag}
            aria-pressed={selection.flagged}
            aria-label={selection.flagged ? "Remove flag" : "Flag for review"}
            className={selection.flagged ? "text-gold-500" : ""}
          >
            <Flag size={18} />
          </Button>
        </div>

        <div className="mt-6 space-y-2" role="group" aria-label="Answer options">
          {current.options.map((option, position) => {
            const key = String((option as { key: string }).key);
            const text = String((option as { text: string }).text);
            const picked = selection.picked.includes(key);
            // Label by position, not by key: the key is a grading handle and the
            // paper is shuffled, so showing it lettered the options D, A, C, B.
            const label = String.fromCharCode(97 + position);
            return (
              <button
                key={key}
                type="button"
                aria-pressed={picked}
                onClick={() => choose(key)}
                className={`flex w-full items-center gap-3 rounded-lg px-4 py-3 text-left ring-1 transition ${
                  picked
                    ? "bg-army-50 text-ink-900 ring-army-500"
                    : "bg-white text-ink-700 ring-ink-200 hover:bg-ink-50"
                }`}
              >
                <span
                  className={`grid h-7 w-7 shrink-0 place-items-center rounded-full text-xs font-bold uppercase ${
                    picked ? "bg-army-500 text-white" : "bg-ink-100 text-ink-600"
                  }`}
                >
                  {picked ? <Check size={14} /> : label}
                </span>
                <span>{text}</span>
              </button>
            );
          })}
        </div>
      </Card>

      {submitError && (
        <div className="mt-4">
          <Alert tone="error">{submitError}</Alert>
        </div>
      )}

      <div className="mt-6 flex items-center justify-between gap-3">
        <Button
          variant="secondary"
          onClick={() => setIndex((i) => Math.max(0, i - 1))}
          disabled={index === 0}
        >
          <ChevronLeft size={16} /> Previous
        </Button>

        {index < questions.length - 1 ? (
          <Button onClick={() => setIndex((i) => Math.min(questions.length - 1, i + 1))}>
            Next <ChevronRight size={16} />
          </Button>
        ) : (
          <Button onClick={() => setConfirming(true)}>Finish paper</Button>
        )}
      </div>

      <nav aria-label="Jump to question" className="mt-8">
        <ol className="flex flex-wrap gap-2">
          {questions.map((question, position) => {
            const state = answers[question.id];
            const isAnswered = (state?.picked.length ?? 0) > 0;
            return (
              <li key={question.id}>
                <button
                  type="button"
                  onClick={() => setIndex(position)}
                  aria-current={position === index ? "step" : undefined}
                  aria-label={`Question ${position + 1}${isAnswered ? ", answered" : ""}${
                    state?.flagged ? ", flagged" : ""
                  }`}
                  className={`h-9 w-9 rounded-lg text-sm font-medium ring-1 transition ${
                    position === index
                      ? "bg-ink-800 text-white ring-ink-800"
                      : isAnswered
                        ? "bg-army-50 text-army-600 ring-army-500"
                        : "bg-white text-ink-500 ring-ink-200"
                  } ${state?.flagged ? "ring-2 ring-gold-500" : ""}`}
                >
                  {position + 1}
                </button>
              </li>
            );
          })}
        </ol>
      </nav>

      {confirming && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-ink-900/40 p-4">
          <Card className="w-full max-w-md p-6">
            <h2 className="font-display text-lg font-bold text-ink-900">Finish this paper?</h2>
            <p className="mt-2 text-sm text-ink-500">
              You have answered {answeredCount} of {questions.length} questions.
              {answeredCount < questions.length &&
                " Unanswered questions score zero, but are not penalised."}
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <Button variant="secondary" onClick={() => setConfirming(false)} disabled={submitting}>
                Keep working
              </Button>
              <Button onClick={() => void submit()} loading={submitting}>
                Submit
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
