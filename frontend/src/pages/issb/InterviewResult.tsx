import { Link, useParams } from "react-router-dom";

import { issb } from "@/api/endpoints";
import { AnalysisPanel } from "@/components/AnalysisPanel";
import { Badge, Button, Card, CardHeader, ErrorState, Loading } from "@/components/ui";
import { useAsync } from "@/lib/useAsync";
import { formatDuration } from "@/lib/format";

export function InterviewResult() {
  const { id } = useParams<{ id: string }>();
  const sessionId = Number(id);

  const { data, error, loading, refetch } = useAsync(
    () => issb.interviewResult(sessionId),
    [sessionId],
  );

  if (loading) return <Loading label="Loading your interview" />;
  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <ErrorState error={error} onRetry={refetch} />
      </div>
    );
  }
  if (!data) return null;

  const answered = data.exchanges.filter((entry) => entry.answer.trim().length > 0).length;

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="font-display text-3xl font-bold text-ink-900">Interview read-out</h1>

      <div className="mt-8">
        <AnalysisPanel
          analysis={data.analysis}
          summary={
            <ul className="space-y-1 text-right">
              <li>
                {answered} of {data.exchanges.length} answered
              </li>
              <li>{formatDuration(data.duration_sec)}</li>
            </ul>
          }
        />
      </div>

      <section className="mt-8">
        <h2 className="font-display text-xl font-bold text-ink-900">Question by question</h2>
        <p className="mt-1 text-sm text-ink-500">
          Your answer, what to change, and what a board is listening for.
        </p>

        <div className="mt-4 space-y-4">
          {data.exchanges.map((entry, position) => (
            <Card key={`${entry.question.id}-${position}`}>
              <CardHeader
                title={<span className="text-base font-medium">{entry.question.question}</span>}
                action={<Badge>{entry.question.category.replace(/_/g, " ")}</Badge>}
              />
              <div className="space-y-3 p-5">
                {entry.answer.trim() ? (
                  <p className="whitespace-pre-wrap rounded-lg bg-ink-50 px-3 py-2 text-ink-800">
                    {entry.answer}
                  </p>
                ) : (
                  <p className="text-sm italic text-ink-500">You did not answer this one.</p>
                )}

                {entry.notes.length > 0 && (
                  <ul className="space-y-1.5">
                    {entry.notes.map((note, noteIndex) => (
                      <li key={noteIndex} className="flex gap-2 text-sm text-ink-600">
                        <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-ink-300" />
                        <span>{note}</span>
                      </li>
                    ))}
                  </ul>
                )}

                {entry.question.guidance && (
                  <div className="rounded-lg bg-army-50 px-3 py-2">
                    <p className="text-xs font-medium uppercase text-army-600">
                      What they are listening for
                    </p>
                    <p className="mt-1 text-sm text-ink-700">{entry.question.guidance}</p>
                  </div>
                )}

                {entry.question.follow_ups.length > 0 && (
                  <div>
                    <p className="text-xs font-medium uppercase text-ink-500">Expect these next</p>
                    <ul className="mt-1.5 space-y-1">
                      {entry.question.follow_ups.map((followUp, followIndex) => (
                        <li key={followIndex} className="text-sm text-ink-600">
                          {String(followUp)}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      </section>

      <div className="mt-10 flex flex-wrap gap-3">
        <Link to="/issb/interview">
          <Button>Run another interview</Button>
        </Link>
        <Link to="/issb">
          <Button variant="secondary">Back to the suite</Button>
        </Link>
      </div>
    </div>
  );
}
