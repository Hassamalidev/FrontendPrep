/** The list screens: not-found, the current-affairs feed, and attempt history. */

import { Link } from "react-router-dom";

import { content, me } from "@/api/endpoints";
import { Badge, Button, Card, EmptyState, ErrorState, Loading } from "@/components/ui";
import { useAsync } from "@/lib/useAsync";
import { formatDate, formatPercent } from "@/lib/format";

export function NotFound() {
  return (
    <div className="mx-auto max-w-xl px-4 py-24 text-center">
      <p className="font-display text-5xl font-bold text-ink-300">404</p>
      <h1 className="mt-3 font-display text-2xl font-bold text-ink-900">Page not found</h1>
      <p className="mt-2 text-ink-500">That link does not lead anywhere.</p>
      <Link to="/" className="mt-6 inline-block">
        <Button>Back to home</Button>
      </Link>
    </div>
  );
}

export function Articles() {
  const { data, error, loading, refetch } = useAsync(() => content.news(7, 24), []);

  if (loading) return <Loading label="Loading current affairs" />;
  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12">
        <ErrorState error={error} onRetry={refetch} />
      </div>
    );
  }

  const stories = data?.items ?? [];

  return (
    <div className="mx-auto max-w-4xl px-4 py-12">
      <h1 className="font-display text-3xl font-bold text-ink-900">Current affairs</h1>
      <p className="mt-2 max-w-2xl text-ink-500">
        This week from Pakistani news feeds. Read the story at its source; the questions the
        board might ask about it are in your General Knowledge and Current Affairs drills.
      </p>
      <p className="mt-2 text-sm text-ink-500">
        These are fetched live and never stored, which is what keeps the platform inside a free
        database tier. Only the questions written from them are kept.
      </p>

      {stories.length === 0 ? (
        <div className="mt-8">
          <EmptyState
            title="No stories right now"
            body="The feeds could not be reached. They are read live, so this usually fixes itself."
          />
        </div>
      ) : (
        <div className="mt-8 space-y-4">
          {stories.map((story) => (
            <a
              key={story.url || story.title}
              href={story.url}
              target="_blank"
              rel="noreferrer noopener"
              className="block"
            >
              <Card className="p-5 transition hover:ring-2 hover:ring-army-500">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge>{story.source}</Badge>
                  {story.published && (
                    <span className="text-xs text-ink-500">{formatDate(story.published)}</span>
                  )}
                </div>
                <h2 className="mt-2 font-display text-lg font-bold text-ink-900">{story.title}</h2>
                {story.summary && <p className="mt-2 text-sm text-ink-500">{story.summary}</p>}
              </Card>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

export function History() {
  const { data, error, loading, refetch } = useAsync(() => me.attempts(1, 50), []);

  if (loading) return <Loading label="Loading your history" />;
  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12">
        <ErrorState error={error} onRetry={refetch} />
      </div>
    );
  }

  const attempts = data?.items ?? [];

  return (
    <div className="mx-auto max-w-4xl px-4 py-12">
      <h1 className="font-display text-3xl font-bold text-ink-900">Your papers</h1>

      {attempts.length === 0 ? (
        <div className="mt-8">
          <EmptyState
            title="Nothing here yet"
            body="Every paper you sit will be listed here with its score."
            action={
              <Link to="/practice">
                <Button>Start practising</Button>
              </Link>
            }
          />
        </div>
      ) : (
        <Card className="mt-8">
          <ul className="divide-y divide-ink-100">
            {attempts.map((attempt) => (
              <li key={attempt.id}>
                <Link
                  to={`/attempts/${attempt.id}/${attempt.status === "in_progress" ? "" : "result"}`}
                  className="flex items-center justify-between gap-4 px-5 py-4 hover:bg-ink-50"
                >
                  <div className="min-w-0">
                    <p className="font-medium capitalize text-ink-800">{attempt.mode} paper</p>
                    <p className="text-sm text-ink-500">
                      {attempt.correct}/{attempt.total_questions} correct
                      {attempt.submitted_at ? ` - ${formatDate(attempt.submitted_at)}` : " - unfinished"}
                    </p>
                  </div>
                  {attempt.status === "in_progress" ? (
                    <Badge tone="amber">In progress</Badge>
                  ) : (
                    <Badge tone={attempt.percentage >= 60 ? "green" : "red"}>
                      {formatPercent(attempt.percentage)}
                    </Badge>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
