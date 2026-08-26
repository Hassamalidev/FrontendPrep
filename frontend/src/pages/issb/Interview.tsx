/**
 * The mock interview.
 *
 * Unlike the psychological battery this is deliberately *not* on a hard clock.
 * An IO interview is a conversation lasting the best part of an hour, and the
 * thing worth practising is composing a structured answer rather than beating a
 * timer -- so time is measured and reported, but never used to cut you off.
 *
 * Guidance is withheld until after submission for the same reason a real board
 * does not hand out the mark scheme.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ApiError } from "@/api/client";
import { issb } from "@/api/endpoints";
import type { InterviewSession } from "@/api/types";
import { ChevronLeft, ChevronRight, Clock } from "@/components/icons";
import { Alert, Badge, Button, Card, Loading, TextArea } from "@/components/ui";
import { formatClock } from "@/lib/format";
import { CATEGORY_LABELS } from "./labels";


export function Interview() {
  const navigate = useNavigate();
  const [session, setSession] = useState<InterviewSession | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [count, setCount] = useState(10);

  async function begin() {
    setStarting(true);
    setError(null);
    try {
      setSession(await issb.startInterview({ count }));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not start the interview.");
    } finally {
      setStarting(false);
    }
  }

  if (!session) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16">
        <h1 className="font-display text-3xl font-bold text-ink-900">Mock interview</h1>
        <p className="mt-3 text-ink-500">
          Questions arrive in the order an Interviewing Officer works through them:
          outward from you, to your family and studies, then to the wider world.
        </p>

        <Card className="mt-8 p-6">
          {error && (
            <div className="mb-4">
              <Alert tone="error">{error}</Alert>
            </div>
          )}

          <Alert>
            Take your time. This is not on a clock — how long you take is recorded and
            reported back, but nothing cuts you off.
          </Alert>

          <fieldset className="mt-5">
            <legend className="mb-2 text-sm font-medium text-ink-700">How many questions?</legend>
            <div className="flex flex-wrap gap-2">
              {[6, 10, 15, 20].map((option) => (
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
            Begin interview
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <Board
      key={session.id}
      session={session}
      onDone={(id) => navigate(`/issb/interview/result/${id}`)}
    />
  );
}

function Board({
  session,
  onDone,
}: {
  session: InterviewSession;
  onDone: (sessionId: number) => void;
}) {
  const questions = session.questions;
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, { text: string; ms: number }>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);

  const startedAt = useRef(0);
  const shownAt = useRef(0);

  useEffect(() => {
    startedAt.current = Date.now();
    shownAt.current = Date.now();
    const timer = window.setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedAt.current) / 1000));
    }, 1000);
    return () => window.clearInterval(timer);
  }, []);

  const question = questions[index];

  /** Bank the time spent on this question before moving away from it. */
  const commit = useCallback(() => {
    const current = questions[index];
    if (!current) return;
    const spent = Date.now() - shownAt.current;
    setAnswers((previous) => {
      const existing = previous[current.id] ?? { text: "", ms: 0 };
      return { ...previous, [current.id]: { ...existing, ms: existing.ms + spent } };
    });
    shownAt.current = Date.now();
  }, [index, questions]);

  function move(delta: number) {
    commit();
    setIndex((position) => Math.min(questions.length - 1, Math.max(0, position + delta)));
  }

  async function submit() {
    commit();
    setSubmitting(true);
    setError(null);
    try {
      const result = await issb.submitInterview(session.id, {
        exchanges: questions.map((q) => ({
          question_id: q.id,
          answer: answers[q.id]?.text ?? "",
          ms: answers[q.id]?.ms ?? 0,
        })),
        duration_sec: Math.max(1, Math.floor((Date.now() - startedAt.current) / 1000)),
      });
      onDone(result.id);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not submit the interview.");
      setSubmitting(false);
    }
  }

  if (submitting && !error) return <Loading label="Reading your answers" />;
  if (!question) return null;

  const answered = Object.values(answers).filter((a) => a.text.trim().length > 0).length;

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-ink-500">
          Question {index + 1} of {questions.length} · {answered} answered
        </p>
        <p className="flex items-center gap-2 font-mono text-sm tabular-nums text-ink-600">
          <Clock size={16} />
          {formatClock(elapsed)}
        </p>
      </div>

      <Card className="mt-6 p-6">
        <Badge>{CATEGORY_LABELS[question.category] ?? question.category}</Badge>
        <p className="mt-3 text-lg leading-relaxed text-ink-900">{question.question}</p>

        <TextArea
          className="mt-5"
          name={`answer-${question.id}`}
          label="Your answer"
          rows={8}
          value={answers[question.id]?.text ?? ""}
          onChange={(event) =>
            setAnswers((previous) => ({
              ...previous,
              [question.id]: {
                text: event.target.value,
                ms: previous[question.id]?.ms ?? 0,
              },
            }))
          }
          placeholder="Answer as you would out loud - a position, a reason, and an example."
        />
      </Card>

      {error && (
        <div className="mt-4">
          <Alert tone="error">{error}</Alert>
        </div>
      )}

      <div className="mt-6 flex items-center justify-between gap-3">
        <Button variant="secondary" onClick={() => move(-1)} disabled={index === 0}>
          <ChevronLeft size={16} /> Previous
        </Button>

        {index < questions.length - 1 ? (
          <Button onClick={() => move(1)}>
            Next <ChevronRight size={16} />
          </Button>
        ) : (
          <Button onClick={() => void submit()} loading={submitting}>
            Finish interview
          </Button>
        )}
      </div>

      <p className="mt-8 text-center text-sm text-ink-500">
        Guidance for each question is shown after you finish.{" "}
        <Link to="/issb" className="font-medium text-army-600 hover:underline">
          Leave the interview
        </Link>
      </p>
    </div>
  );
}
