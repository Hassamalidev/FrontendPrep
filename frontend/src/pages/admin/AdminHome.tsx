import { Link } from "react-router-dom";

import { admin, agent } from "@/api/endpoints";
import { Badge, Card, CardHeader, ErrorState, Loading } from "@/components/ui";
import { useAsync } from "@/lib/useAsync";

const SECTIONS = [
  {
    to: "/admin/generate",
    title: "Generate questions",
    body: "Paste an article and run the local pipeline. Preview first, then save.",
  },
  {
    to: "/admin/queue",
    title: "Review queue",
    body: "Approve or reject what the generator produced. Weakest first.",
  },
  {
    to: "/admin/questions",
    title: "Question bank",
    body: "Search, filter and edit everything that has been published.",
  },
  {
    to: "/admin/articles",
    title: "Articles",
    body: "The source material, and which of it has been generated from.",
  },
  { to: "/admin/users", title: "Users", body: "Accounts, roles and status." },
  {
    to: "/admin/maintenance",
    title: "Maintenance",
    body: "Row counts against the free-tier budget, and the retention job.",
  },
];

export function AdminHome() {
  const { data: size, error, loading, refetch } = useAsync(() => admin.size(), []);
  const { data: engine } = useAsync(() => agent.status(), []);
  const { data: queue } = useAsync(() => admin.queue(1, 1), []);

  if (loading) return <Loading label="Loading" />;
  if (error) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-12">
        <ErrorState error={error} onRetry={refetch} />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="font-display text-3xl font-bold text-ink-900">Administration</h1>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        {engine && <Badge tone="green">Question engine: {engine.engine}</Badge>}
        {engine && !engine.uses_external_api && <Badge>No external AI service</Badge>}
        {(queue?.total ?? 0) > 0 && (
          <Link to="/admin/queue">
            <Badge tone="amber">{queue?.total} awaiting review</Badge>
          </Link>
        )}
      </div>

      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {SECTIONS.map((section) => (
          <Link key={section.to} to={section.to}>
            <Card className="h-full p-5 transition hover:ring-2 hover:ring-army-500">
              <h2 className="font-semibold text-ink-900">{section.title}</h2>
              <p className="mt-1 text-sm text-ink-500">{section.body}</p>
            </Card>
          </Link>
        ))}
      </div>

      {size && (
        <Card className="mt-10">
          <CardHeader
            title="What is in the database"
            subtitle="The tables that grow. The deployment budget is 0.5 GB."
          />
          <dl className="grid grid-cols-2 gap-px bg-ink-100 sm:grid-cols-4">
            {Object.entries(size).map(([table, count]) => (
              <div key={table} className="bg-white px-4 py-3">
                <dt className="text-xs text-ink-500">{table.replace(/_/g, " ")}</dt>
                <dd className="mt-0.5 font-mono text-lg tabular-nums text-ink-900">
                  {count.toLocaleString()}
                </dd>
              </div>
            ))}
          </dl>
        </Card>
      )}
    </div>
  );
}
