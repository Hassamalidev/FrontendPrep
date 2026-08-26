import { Link } from "react-router-dom";

import { catalog } from "@/api/endpoints";
import { ChevronRight } from "@/components/icons";
import { Card, ErrorState, Loading } from "@/components/ui";
import { useAsync } from "@/lib/useAsync";
import { serviceTheme } from "@/lib/format";

export function Services() {
  const { data, error, loading, refetch } = useAsync(() => catalog.services(), []);

  if (loading) return <Loading label="Loading services" />;
  if (error) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-12">
        <ErrorState error={error} onRetry={refetch} />
      </div>
    );
  }

  const services = (data ?? []).filter((service) => service.code !== "common");

  return (
    <div className="mx-auto max-w-6xl px-4 py-12">
      <h1 className="font-display text-3xl font-bold text-ink-900">Choose your service</h1>
      <p className="mt-2 max-w-2xl text-ink-500">
        Each service has its own entry schemes, written test pattern and physical standards. Pick
        one to see the full selection funnel from registration to the merit list.
      </p>

      <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {services.map((service) => {
          const theme = serviceTheme(service.code);
          return (
            <Link
              key={service.id}
              to={`/services/${service.code}`}
              className="group rounded-card bg-white ring-1 ring-ink-200/70 transition hover:ring-2"
            >
              <div className={`h-1.5 rounded-t-card ${theme.bg}`} />
              <div className="p-5">
                <h2 className="font-display text-lg font-bold text-ink-900">{service.name}</h2>
                {service.tagline && (
                  <p className={`mt-0.5 text-sm font-medium ${theme.text}`}>{service.tagline}</p>
                )}
                {service.description && (
                  <p className="mt-3 line-clamp-3 text-sm text-ink-500">{service.description}</p>
                )}
                <span className={`mt-4 inline-flex items-center gap-1 text-sm font-medium ${theme.text}`}>
                  Explore
                  <ChevronRight size={16} className="transition group-hover:translate-x-0.5" />
                </span>
              </div>
            </Link>
          );
        })}
      </div>

      <Card className="mt-10 p-6">
        <h2 className="font-semibold text-ink-900">Not sure yet?</h2>
        <p className="mt-1 text-sm text-ink-500">
          The intelligence, English and general knowledge material is shared across all three
          services, so you can start practising before you decide.
        </p>
        <Link to="/practice" className="mt-4 inline-block text-sm font-medium text-army-600 hover:underline">
          Go to practice
        </Link>
      </Card>
    </div>
  );
}
