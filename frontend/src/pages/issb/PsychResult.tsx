import { Link, useParams } from "react-router-dom";

import { issb } from "@/api/endpoints";
import { AnalysisPanel } from "@/components/AnalysisPanel";
import { Badge, Button, Card, CardHeader, ErrorState, Loading } from "@/components/ui";
import { useAsync } from "@/lib/useAsync";
import { formatDuration } from "@/lib/format";

export function PsychResult() {
  const { id } = useParams<{ id: string }>();
  const sessionId = Number(id);

  const { data, error, loading, refetch } = useAsync(
    () => issb.psychResult(sessionId),
    [sessionId],
  );

  if (loading) return <Loading label="Loading your read-out" />;
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
      <p className="text-sm font-medium uppercase text-army-600">{data.test_type}</p>
      <h1 className="mt-1 font-display text-3xl font-bold text-ink-900">Your read-out</h1>

      <div className="mt-8">
        <AnalysisPanel
          analysis={data.analysis}
          summary={
            <ul className="space-y-1 text-right">
              <li>
                {data.answered_count} of {data.item_count} attempted
              </li>
              <li>{data.word_count} words</li>
              <li>{formatDuration(data.duration_sec)}</li>
            </ul>
          }
        />
      </div>

      <section className="mt-8">
        <h2 className="font-display text-xl font-bold text-ink-900">Item by item</h2>
        <p className="mt-1 text-sm text-ink-500">
          What you wrote, with the specific thing to change next time.
        </p>

        <div className="mt-4 space-y-4">
          {data.responses.map((entry, position) => (
            <Card key={`${entry.item.id}-${position}`}>
              <CardHeader
                title={<span className="text-base font-medium">{entry.item.prompt}</span>}
                action={
                  entry.skipped ? <Badge tone="red">Not attempted</Badge> : <Badge>{entry.ms}ms</Badge>
                }
              />
              <div className="space-y-3 p-5">
                {entry.text ? (
                  <p className="rounded-lg bg-ink-50 px-3 py-2 text-ink-800">{entry.text}</p>
                ) : (
                  <p className="text-sm italic text-ink-500">You left this blank.</p>
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

                {entry.item.model_answer && (
                  <div className="rounded-lg bg-army-50 px-3 py-2">
                    <p className="text-xs font-medium uppercase text-army-600">A strong response</p>
                    <p className="mt-1 text-sm text-ink-700">{entry.item.model_answer}</p>
                  </div>
                )}

                {entry.item.perception_hint && (
                  <div className="rounded-lg bg-gold-50 px-3 py-2">
                    <p className="text-xs font-medium uppercase text-ink-600">
                      What candidates usually see
                    </p>
                    <p className="mt-1 text-sm text-ink-700">{entry.item.perception_hint}</p>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      </section>

      <div className="mt-10 flex flex-wrap gap-3">
        <Link to={`/issb/psych/${data.test_type}`}>
          <Button>Sit it again</Button>
        </Link>
        <Link to="/issb">
          <Button variant="secondary">Back to the suite</Button>
        </Link>
      </div>
    </div>
  );
}
