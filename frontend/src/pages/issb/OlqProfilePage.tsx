import { Link } from "react-router-dom";

import { issb, progress } from "@/api/endpoints";
import { OlqBars } from "@/components/charts/OlqBars";
import { ProgressLine } from "@/components/charts/ProgressLine";
import { Button, Card, CardHeader, EmptyState, ErrorState, Loading } from "@/components/ui";
import { useAsync } from "@/lib/useAsync";
import { formatDate } from "@/lib/format";

export function OlqProfilePage() {
  const { data, error, loading, refetch } = useAsync(() => issb.olqProfile(), []);
  const { data: trend } = useAsync(() => progress.olqTrend(20), []);

  if (loading) return <Loading label="Loading your profile" />;
  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <ErrorState error={error} onRetry={refetch} />
      </div>
    );
  }
  if (!data) return null;

  if (data.sessions_counted === 0) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16">
        <h1 className="font-display text-3xl font-bold text-ink-900">Your OLQ profile</h1>
        <div className="mt-8">
          <EmptyState
            title="Nothing measured yet"
            body="Sit a psychological test, plan a GTO task or run a mock interview, and your profile builds from those sittings."
            action={
              <Link to="/issb">
                <Button>Open the ISSB suite</Button>
              </Link>
            }
          />
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="font-display text-3xl font-bold text-ink-900">Your OLQ profile</h1>
      <p className="mt-2 text-ink-500">
        Averaged across {data.sessions_counted} sitting{data.sessions_counted === 1 ? "" : "s"}
        {data.updated_at ? `, last updated ${formatDate(data.updated_at)}` : ""}.
      </p>

      <Card className="mt-8">
        <CardHeader
          title="All fifteen qualities"
          subtitle="Strongest first, on the board's 1 to 5 scale"
        />
        <div className="p-5">
          <OlqBars
            scores={data.scores}
            caption="Averaged over every projective test you have sat."
          />
        </div>
      </Card>

      {trend && trend.length >= 2 && (
        <Card className="mt-6">
          <CardHeader
            title="Progress"
            subtitle="Overall score per sitting, oldest first"
          />
          <div className="p-5">
            <ProgressLine points={trend} />
          </div>
        </Card>
      )}

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <Card className="p-5">
          <h2 className="font-semibold text-ink-900">Coming through clearly</h2>
          <ul className="mt-3 space-y-1.5">
            {data.strongest.map((label) => (
              <li key={label} className="flex gap-2 text-sm text-ink-700">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-army-500" />
                {label}
              </li>
            ))}
          </ul>
        </Card>

        <Card className="p-5">
          <h2 className="font-semibold text-ink-900">Least evidence so far</h2>
          <p className="mt-1 text-xs text-ink-500">
            Not weaknesses. These are qualities your writing has not yet shown.
          </p>
          <ul className="mt-3 space-y-1.5">
            {data.weakest.map((label) => (
              <li key={label} className="flex gap-2 text-sm text-ink-700">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-ink-300" />
                {label}
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <div className="mt-10">
        <Link to="/issb">
          <Button variant="secondary">Back to the suite</Button>
        </Link>
      </div>
    </div>
  );
}
