import { Link } from "react-router-dom";

import { me } from "@/api/endpoints";
import { Chart, Target, Trophy } from "@/components/icons";
import { Alert, Badge, Button, Card, CardHeader, EmptyState, ErrorState, Loading } from "@/components/ui";
import { useAuth } from "@/auth/useAuth";
import { useAsync } from "@/lib/useAsync";
import { formatDate, formatDuration, formatPercent } from "@/lib/format";

export function Dashboard() {
  const { user } = useAuth();
  const { data, error, loading, refetch } = useAsync(() => me.dashboard(), []);

  if (loading) return <Loading label="Loading your dashboard" />;
  if (error) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-12">
        <ErrorState error={error} onRetry={refetch} />
      </div>
    );
  }
  if (!data) return null;

  const { stats } = data;

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="font-display text-2xl font-bold text-ink-900">
        Welcome back, {user?.full_name.split(" ")[0]}
      </h1>

      {data.announcements.length > 0 && (
        <div className="mt-6 space-y-3">
          {data.announcements.map((announcement) => {
            const item = announcement as { id: number; title: string; body?: string };
            return (
              <Alert key={item.id}>
                <strong className="font-medium">{item.title}</strong>
                {item.body && <span className="ml-1">{item.body}</span>}
              </Alert>
            );
          })}
        </div>
      )}

      {data.resume_attempt_id && (
        <Card className="mt-6 border-l-4 border-l-gold-500 p-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="font-semibold text-ink-900">You have an unfinished paper</h2>
              <p className="mt-0.5 text-sm text-ink-500">Pick up where you left off.</p>
            </div>
            <Link to={`/attempts/${data.resume_attempt_id}`}>
              <Button>Resume</Button>
            </Link>
          </div>
        </Card>
      )}

      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card className="p-4">
          <p className="font-display text-2xl font-bold text-ink-900">{stats.attempts_total}</p>
          <p className="mt-0.5 text-xs text-ink-500">Papers sat</p>
        </Card>
        <Card className="p-4">
          <p className="font-display text-2xl font-bold text-ink-900">{formatPercent(stats.accuracy)}</p>
          <p className="mt-0.5 text-xs text-ink-500">Accuracy</p>
        </Card>
        <Card className="p-4">
          <p className="font-display text-2xl font-bold text-ink-900">{stats.current_streak}</p>
          <p className="mt-0.5 text-xs text-ink-500">Day streak</p>
        </Card>
        <Card className="p-4">
          <p className="font-display text-2xl font-bold text-ink-900">
            {formatDuration(stats.study_seconds)}
          </p>
          <p className="mt-0.5 text-xs text-ink-500">Time studied</p>
        </Card>
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader
              title="Recent papers"
              action={
                <Link to="/history" className="text-sm font-medium text-army-600 hover:underline">
                  See all
                </Link>
              }
            />
            {data.recent_attempts.length === 0 ? (
              <div className="p-5">
                <EmptyState
                  title="No papers yet"
                  body="Start a drill and your results will collect here."
                  action={
                    <Link to="/practice">
                      <Button>Start practising</Button>
                    </Link>
                  }
                />
              </div>
            ) : (
              <ul className="divide-y divide-ink-100">
                {data.recent_attempts.map((attempt) => {
                  const row = attempt as {
                    id: number;
                    mode: string;
                    percentage: number;
                    correct: number;
                    total_questions: number;
                    submitted_at: string;
                  };
                  const tone = row.percentage >= 60 ? "green" : row.percentage >= 40 ? "amber" : "red";
                  return (
                    <li key={row.id}>
                      <Link
                        to={`/attempts/${row.id}/result`}
                        className="flex items-center justify-between gap-4 px-5 py-4 hover:bg-ink-50"
                      >
                        <div className="min-w-0">
                          <p className="font-medium capitalize text-ink-800">{row.mode} paper</p>
                          <p className="text-sm text-ink-500">
                            {row.correct}/{row.total_questions} correct
                            {row.submitted_at ? ` - ${formatDate(row.submitted_at)}` : ""}
                          </p>
                        </div>
                        <Badge tone={tone}>{formatPercent(row.percentage)}</Badge>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}
          </Card>
        </div>

        <div className="space-y-6">
          {data.next_stage && (
            <Card className="p-5">
              <div className="flex items-center gap-2 text-army-600">
                <Target size={18} />
                <h2 className="font-semibold">Focus next</h2>
              </div>
              <p className="mt-2 font-medium text-ink-900">
                {(data.next_stage as { name: string }).name}
              </p>
              <p className="mt-1 text-sm text-ink-500">
                {(data.next_stage as { summary?: string }).summary}
              </p>
            </Card>
          )}

          {data.due_revision > 0 && (
            <Card className="p-5">
              <div className="flex items-center gap-2 text-gold-500">
                <Chart size={18} />
                <h2 className="font-semibold text-ink-900">Revision due</h2>
              </div>
              <p className="mt-2 text-sm text-ink-500">
                {data.due_revision} question{data.due_revision === 1 ? "" : "s"} you previously got
                wrong are ready to try again.
              </p>
              <Link to="/revision" className="mt-3 inline-block">
                <Button size="sm">Revise now</Button>
              </Link>
            </Card>
          )}

          {data.recommended.length > 0 && (
            <Card>
              <CardHeader title="Recommended" />
              <ul className="divide-y divide-ink-100">
                {data.recommended.map((item, position) => {
                  const entry = item as {
                    kind: string;
                    module_id?: number;
                    name: string;
                    accuracy?: number;
                    question_count?: number;
                  };
                  return (
                    <li key={position}>
                      <Link
                        to={entry.module_id ? `/modules/${entry.module_id}` : "/practice"}
                        className="flex items-center justify-between gap-3 px-5 py-3 text-sm hover:bg-ink-50"
                      >
                        <span className="min-w-0 truncate text-ink-800">{entry.name}</span>
                        {entry.kind === "weak_topic" ? (
                          <Badge tone="amber">{formatPercent(entry.accuracy)}</Badge>
                        ) : (
                          <span className="shrink-0 text-xs text-ink-500">
                            {entry.question_count} Qs
                          </span>
                        )}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </Card>
          )}

          <Card className="p-5">
            <div className="flex items-center gap-2 text-ink-700">
              <Trophy size={18} />
              <h2 className="font-semibold text-ink-900">ISSB simulation</h2>
            </div>
            <p className="mt-2 text-sm text-ink-500">
              Practise the psychological battery, GTO tasks and the interview.
            </p>
            <Link to="/issb" className="mt-3 inline-block">
              <Button size="sm" variant="secondary">
                Open the suite
              </Button>
            </Link>
          </Card>
        </div>
      </div>
    </div>
  );
}
