import { Link } from "react-router-dom";

import { catalog } from "@/api/endpoints";
import { Card, EmptyState, ErrorState, Loading } from "@/components/ui";
import { useAsync } from "@/lib/useAsync";
import { practisedElsewhere } from "@/lib/modules";
import { useAuth } from "@/auth/useAuth";

/** Module picker, scoped to the service the student is preparing for. */
export function Practice() {
  const { user } = useAuth();

  const { data, error, loading, refetch } = useAsync(async () => {
    const services = await catalog.services();
    const target =
      services.find((service) => service.code === user?.target_service) ??
      services.find((service) => service.code !== "common") ??
      services[0];
    if (!target) return { service: null, modules: [] };
    const modules = await catalog.modules({ service_id: target.id });
    return { service: target, modules };
  }, [user?.target_service]);

  if (loading) return <Loading label="Loading modules" />;
  if (error) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-12">
        <ErrorState error={error} onRetry={refetch} />
      </div>
    );
  }

  const all = data?.modules ?? [];
  // Three buckets, not two: drillable, practised somewhere else, and genuinely
  // not ready yet. Collapsing the middle one into "coming soon" was telling
  // students the ISSB suite did not exist.
  const elsewhere = all
    .map((module) => ({ module, destination: practisedElsewhere(module.slug) }))
    .filter((entry) => entry.destination !== null);
  const elsewhereSlugs = new Set(elsewhere.map((entry) => entry.module.slug));
  const modules = all.filter(
    (module) => module.approved_question_count > 0 && !elsewhereSlugs.has(module.slug),
  );
  const upcoming = all.filter(
    (module) => module.approved_question_count === 0 && !elsewhereSlugs.has(module.slug),
  );

  return (
    <div className="mx-auto max-w-6xl px-4 py-12">
      <h1 className="font-display text-3xl font-bold text-ink-900">Practice</h1>
      <p className="mt-2 text-ink-500">
        {data?.service ? `Modules for the ${data.service.name}.` : "Choose a module to drill."}
      </p>

      {modules.length === 0 ? (
        <div className="mt-8">
          <EmptyState
            title="No questions are live yet"
            body="The question bank is still being filled. Check back shortly, or explore the ISSB simulation in the meantime."
          />
        </div>
      ) : (
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {modules.map((module) => (
            <Link key={module.id} to={`/modules/${module.id}`}>
              <Card className="h-full p-5 transition hover:ring-2 hover:ring-army-500">
                <h2 className="font-semibold text-ink-900">{module.title}</h2>
                {module.subtitle && (
                  <p className="mt-1 line-clamp-2 text-sm text-ink-500">{module.subtitle}</p>
                )}
                <p className="mt-3 text-xs text-ink-500">
                  {module.approved_question_count} questions · about{" "}
                  {module.default_duration_min} min
                </p>
              </Card>
            </Link>
          ))}
        </div>
      )}

      {elsewhere.length > 0 && (
        <section className="mt-12">
          <h2 className="font-display text-xl font-bold text-ink-900">
            Practised in the simulation suite
          </h2>
          <p className="mt-1 text-sm text-ink-500">
            These stages are not answered as written questions, so they have their own
            screens.
          </p>
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {elsewhere.map(({ module, destination }) => (
              <Link key={module.id} to={destination!.to}>
                <Card className="h-full p-5 transition hover:ring-2 hover:ring-army-500">
                  <h3 className="font-semibold text-ink-900">{module.title}</h3>
                  <p className="mt-1 text-sm text-ink-500">{destination!.note}</p>
                  <p className="mt-3 text-sm font-medium text-army-600">
                    {destination!.action}
                  </p>
                </Card>
              </Link>
            ))}
          </div>
        </section>
      )}

      {upcoming.length > 0 && (
        <section className="mt-12">
          <h2 className="font-display text-lg font-bold text-ink-900">Coming soon</h2>
          <p className="mt-1 text-sm text-ink-500">
            These modules exist in the syllabus but have no approved questions yet.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            {upcoming.map((module) => (
              <span key={module.id} className="rounded-full bg-ink-100 px-3 py-1 text-sm text-ink-500">
                {module.title}
              </span>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
