import { Link, useParams } from "react-router-dom";

import { catalog } from "@/api/endpoints";
import type { Module, ServiceCode } from "@/api/types";
import { Badge, Card, CardHeader, ErrorState, Loading } from "@/components/ui";
import { useAsync } from "@/lib/useAsync";
import { practisedElsewhere } from "@/lib/modules";
import { serviceTheme } from "@/lib/format";
import { ServiceAvatar } from "@/components/ServiceAvatar";

export function ServiceHub() {
  const { code } = useParams<{ code: string }>();
  const serviceCode = code as ServiceCode;

  const { data, error, loading, refetch } = useAsync(
    () => catalog.service(serviceCode),
    [serviceCode],
  );

  if (loading) return <Loading label="Loading service" />;
  if (error) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-12">
        <ErrorState error={error} onRetry={refetch} />
      </div>
    );
  }
  if (!data) return null;

  const { service, programs, stages, modules } = data;
  const theme = serviceTheme(service.code);
  const pattern = (service.test_pattern ?? {}) as {
    label?: string;
    distinctive?: string;
    negative_marking?: boolean;
    sectional_pass?: number;
    sections?: {
      name: string;
      questions: number;
      minutes: number;
      covers?: string[];
      split?: { verbal: number; non_verbal: number };
    }[];
  };

  // Modules are filed against a stage. Grouping them here presents the syllabus
  // as the funnel a candidate actually walks, instead of one flat list of
  // thirteen study units with no sense of order.
  const byStage = new Map<number, Module[]>();
  for (const module of modules) {
    const bucket = byStage.get(module.stage_id) ?? [];
    bucket.push(module);
    byStage.set(module.stage_id, bucket);
  }

  return (
    <div>
      <div className={`${theme.bg} text-white`}>
        <div className="mx-auto grid max-w-6xl items-end gap-6 px-4 py-12 sm:grid-cols-[1fr_auto]">
          <div>
            <p className="text-sm opacity-80">{service.tagline}</p>
            <h1 className="font-display text-3xl font-bold sm:text-4xl">{service.name}</h1>
            {service.description && (
              <p className="mt-3 max-w-2xl text-white/90">{service.description}</p>
            )}
          </div>
          <span className="hidden h-36 w-36 place-items-center justify-self-end overflow-hidden rounded-full bg-white/10 ring-2 ring-white/25 sm:grid">
            <ServiceAvatar service={service.code} size={132} />
          </span>
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-4 py-10">
        <section aria-labelledby="programs-heading">
          <h2 id="programs-heading" className="font-display text-xl font-bold text-ink-900">
            Entry schemes
          </h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {programs.map((program) => {
              const age = program.eligibility?.age as { min?: number; max?: number } | undefined;
              return (
                <Card key={program.id} className="p-5">
                  <h3 className="font-semibold text-ink-900">{program.name}</h3>
                  {program.summary && <p className="mt-1 text-sm text-ink-500">{program.summary}</p>}
                  {age?.min !== undefined && (
                    <p className="mt-3 text-sm text-ink-600">
                      Age {age.min}-{age.max}
                    </p>
                  )}
                </Card>
              );
            })}
          </div>
        </section>

        {pattern.sections && pattern.sections.length > 0 && (
          <section aria-labelledby="pattern-heading" className="mt-12">
            <h2 id="pattern-heading" className="font-display text-xl font-bold text-ink-900">
              The initial written test
            </h2>
            <p className="mt-1 max-w-2xl text-sm text-ink-500">
              {pattern.label ? `${pattern.label} pattern. ` : ""}
              {pattern.distinctive}
            </p>

            <Card className="mt-4 overflow-hidden">
              <table className="w-full text-sm">
                <caption className="sr-only">
                  {service.name} initial written test sections
                </caption>
                <thead>
                  <tr className="border-b border-ink-200 bg-ink-50 text-left text-ink-600">
                    <th scope="col" className="px-5 py-2.5 font-medium">Section</th>
                    <th scope="col" className="px-5 py-2.5 text-right font-medium">Questions</th>
                    <th scope="col" className="px-5 py-2.5 text-right font-medium">Minutes</th>
                  </tr>
                </thead>
                <tbody>
                  {pattern.sections.map((section, index) => (
                    <tr key={index} className="border-b border-ink-100 last:border-0">
                      <th scope="row" className="px-5 py-2.5 text-left font-normal text-ink-800">
                        {section.name}
                        {section.covers && (
                          <span className="block text-xs text-ink-500">
                            {section.covers.join(" · ")}
                          </span>
                        )}
                        {section.split && (
                          <span className="block text-xs text-ink-500">
                            {section.split.verbal} verbal · {section.split.non_verbal} non-verbal
                          </span>
                        )}
                      </th>
                      <td className="px-5 py-2.5 text-right font-mono tabular-nums text-ink-700">
                        {section.questions}
                      </td>
                      <td className="px-5 py-2.5 text-right font-mono tabular-nums text-ink-700">
                        {section.minutes}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="border-t border-ink-100 px-5 py-3 text-xs text-ink-500">
                {pattern.negative_marking ? "Negative marking applies." : "No negative marking."}
                {pattern.sectional_pass
                  ? ` A sectional pass of ${pattern.sectional_pass}% is required.`
                  : ""}{" "}
                Confirm against the current advertisement before you sit it.
              </p>
            </Card>
          </section>
        )}

        <section aria-labelledby="funnel-heading" className="mt-12">
          <h2 id="funnel-heading" className="font-display text-xl font-bold text-ink-900">
            The selection funnel
          </h2>
          <p className="mt-1 text-sm text-ink-500">
            Every stage, in order, with the study modules filed under it.
          </p>

          <ol className="mt-6 space-y-4">
            {stages.map((stage, index) => {
              const stageModules = byStage.get(stage.id) ?? [];
              return (
                <li key={stage.id}>
                  <Card>
                    <CardHeader
                      title={
                        <span className="flex items-center gap-3">
                          <span
                            className={`grid h-7 w-7 shrink-0 place-items-center rounded-full text-xs font-bold text-white ${theme.bg}`}
                          >
                            {index + 1}
                          </span>
                          {stage.name}
                        </span>
                      }
                      subtitle={stage.summary ?? undefined}
                      action={stage.day_hint ? <Badge>{stage.day_hint}</Badge> : undefined}
                    />
                    {stageModules.length > 0 && (
                      <div className="grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-3">
                        {stageModules.map((module) => {
                          // An ISSB-stage module has no question bank by design;
                          // sending the student to a drill page that cannot run,
                          // labelled "0 questions", reads as a broken feature.
                          const destination = practisedElsewhere(module.slug);
                          return (
                            <Link
                              key={module.id}
                              to={destination ? destination.to : `/modules/${module.id}`}
                              className="rounded-lg p-3 ring-1 ring-ink-200 transition hover:bg-ink-50"
                            >
                              <p className="font-medium text-ink-800">{module.title}</p>
                              {module.subtitle && (
                                <p className="mt-0.5 line-clamp-2 text-sm text-ink-500">
                                  {module.subtitle}
                                </p>
                              )}
                              <p
                                className={`mt-2 text-xs ${
                                  destination ? "font-medium text-army-600" : "text-ink-500"
                                }`}
                              >
                                {destination
                                  ? destination.action
                                  : `${module.approved_question_count} question${
                                      module.approved_question_count === 1 ? "" : "s"
                                    }`}
                              </p>
                            </Link>
                          );
                        })}
                      </div>
                    )}
                  </Card>
                </li>
              );
            })}
          </ol>
        </section>
      </div>
    </div>
  );
}
