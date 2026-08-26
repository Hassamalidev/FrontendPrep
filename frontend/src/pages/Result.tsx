import { Link, useParams } from "react-router-dom";

import { practice } from "@/api/endpoints";
import { Check, Close, Trophy } from "@/components/icons";
import { Badge, Button, Card, CardHeader, ErrorState, Loading } from "@/components/ui";
import { useAsync } from "@/lib/useAsync";
import { formatDuration, formatPercent } from "@/lib/format";

function Stat({ label, value, tone = "" }: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded-lg bg-ink-50 px-4 py-3 text-center">
      <p className={`font-display text-2xl font-bold ${tone || "text-ink-900"}`}>{value}</p>
      <p className="mt-0.5 text-xs text-ink-500">{label}</p>
    </div>
  );
}

export function Result() {
  const { id } = useParams<{ id: string }>();
  const attemptId = Number(id);

  const { data, error, loading, refetch } = useAsync(
    () => practice.result(attemptId),
    [attemptId],
  );

  if (loading) return <Loading label="Marking your paper" />;
  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <ErrorState error={error} onRetry={refetch} />
      </div>
    );
  }
  if (!data) return null;

  const passed = data.passed ?? data.percentage >= 50;
  const unattempted = data.total_questions - data.attempted;

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <div className="text-center">
        <div
          className={`mx-auto grid h-16 w-16 place-items-center rounded-full ${
            passed ? "bg-success-50 text-success-500" : "bg-gold-50 text-gold-500"
          }`}
        >
          <Trophy size={30} />
        </div>
        <h1 className="mt-4 font-display text-3xl font-bold text-ink-900">
          {formatPercent(data.percentage)}
        </h1>
        <p className="mt-1 text-ink-500">
          {data.correct} of {data.total_questions} correct
          {data.duration_sec > 0 && ` in ${formatDuration(data.duration_sec)}`}
        </p>
      </div>

      <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Correct" value={String(data.correct)} tone="text-success-500" />
        <Stat label="Wrong" value={String(data.wrong)} tone="text-danger-500" />
        <Stat label="Skipped" value={String(unattempted)} />
        <Stat label="Score" value={`${data.score}/${data.max_score}`} />
      </div>

      {data.weak_topics.length > 0 && (
        <Card className="mt-8 p-5">
          <h2 className="font-semibold text-ink-900">Worth revisiting</h2>
          <p className="mt-1 text-sm text-ink-500">
            You scored under 60% on these topics in this paper.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {data.weak_topics.map((topic) => (
              <Badge key={topic} tone="amber">
                {topic}
              </Badge>
            ))}
          </div>
        </Card>
      )}

      {data.review.length > 0 && (
        <section className="mt-8">
          <h2 className="font-display text-xl font-bold text-ink-900">Review</h2>
          <p className="mt-1 text-sm text-ink-500">
            Every question, with the correct answer and why.
          </p>

          <div className="mt-4 space-y-4">
            {data.review.map((entry, position) => {
              const question = entry.question;
              const options = (question.options ?? []) as { key: string; text: string }[];
              const correctKeys = new Set(question.answer_keys ?? []);
              const pickedKeys = new Set(entry.picked);

              return (
                <Card key={question.id}>
                  <CardHeader
                    title={`Question ${position + 1}`}
                    action={
                      entry.correct ? (
                        <Badge tone="green">Correct</Badge>
                      ) : pickedKeys.size === 0 ? (
                        <Badge>Skipped</Badge>
                      ) : (
                        <Badge tone="red">Wrong</Badge>
                      )
                    }
                  />
                  <div className="p-5">
                    <p className="text-ink-900">{question.stem}</p>

                    <ul className="mt-4 space-y-2">
                      {options.map((option, position) => {
                        const isCorrect = correctKeys.has(option.key);
                        const wasPicked = pickedKeys.has(option.key);
                        // Same shuffle as the paper, so the same positional label.
                        const label = String.fromCharCode(97 + position);
                        return (
                          <li
                            key={option.key}
                            className={`flex items-start gap-3 rounded-lg px-3 py-2 text-sm ring-1 ${
                              isCorrect
                                ? "bg-success-50 ring-success-500/40"
                                : wasPicked
                                  ? "bg-danger-50 ring-danger-500/40"
                                  : "ring-ink-200"
                            }`}
                          >
                            <span className="mt-0.5 shrink-0">
                              {isCorrect ? (
                                <Check size={16} className="text-success-500" />
                              ) : wasPicked ? (
                                <Close size={16} className="text-danger-500" />
                              ) : (
                                <span className="inline-block w-4 text-center text-xs uppercase text-ink-500">
                                  {label}
                                </span>
                              )}
                            </span>
                            <span className="text-ink-800">{option.text}</span>
                          </li>
                        );
                      })}
                    </ul>

                    {question.explanation && (
                      <p className="mt-4 rounded-lg bg-ink-50 px-3 py-2 text-sm text-ink-600">
                        {question.explanation}
                      </p>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>
        </section>
      )}

      <div className="mt-10 flex flex-wrap gap-3">
        <Link to="/practice">
          <Button>Practise again</Button>
        </Link>
        <Link to="/dashboard">
          <Button variant="secondary">Back to dashboard</Button>
        </Link>
      </div>
    </div>
  );
}
