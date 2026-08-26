/**
 * Mock tests.
 *
 * A template resolves into concrete questions at start time rather than being a
 * fixed paper, so a mock stays valid as the bank grows. The section counts here
 * are therefore a target: a thin bank yields a shorter paper rather than an
 * error, and the start call reports what it could not fill.
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError } from "@/api/client";
import { practice } from "@/api/endpoints";
import type { TestTemplate } from "@/api/types";
import { Clock } from "@/components/icons";
import { Alert, Badge, Button, Card, EmptyState, ErrorState, Loading } from "@/components/ui";
import { useAsync } from "@/lib/useAsync";

export function Tests() {
  const navigate = useNavigate();
  const { data, error, loading, refetch } = useAsync(() => practice.tests(), []);
  const [starting, setStarting] = useState<number | null>(null);
  const [startError, setStartError] = useState<string | null>(null);

  async function start(template: TestTemplate) {
    setStarting(template.id);
    setStartError(null);
    try {
      const attempt = await practice.start({
        template_id: template.id,
        module_id: null,
        topic_id: null,
        count: template.total_questions || 20,
        difficulty: null,
        mode: "mock",
        only_weak: false,
      });
      navigate(`/attempts/${attempt.id}`, { state: { attempt } });
    } catch (caught) {
      setStartError(caught instanceof ApiError ? caught.message : "Could not start that test.");
    } finally {
      setStarting(null);
    }
  }

  if (loading) return <Loading label="Loading tests" />;
  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12">
        <ErrorState error={error} onRetry={refetch} />
      </div>
    );
  }

  const templates = data ?? [];

  return (
    <div className="mx-auto max-w-4xl px-4 py-12">
      <h1 className="font-display text-3xl font-bold text-ink-900">Mock tests</h1>
      <p className="mt-2 max-w-2xl text-ink-500">
        Full-length papers in the pattern of the real initial written test, section by
        section and against the clock.
      </p>

      {startError && (
        <div className="mt-6">
          <Alert tone="error">{startError}</Alert>
        </div>
      )}

      {templates.length === 0 ? (
        <div className="mt-8">
          <EmptyState
            title="No tests published yet"
            body="Mock papers appear here once an administrator publishes them."
          />
        </div>
      ) : (
        <div className="mt-8 space-y-4">
          {templates.map((template) => {
            const sections = (template.sections ?? []) as {
              title?: string;
              module_slug: string;
              count: number;
              minutes?: number;
            }[];
            return (
              <Card key={template.id} className="p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h2 className="font-semibold text-ink-900">{template.title}</h2>
                    {template.description && (
                      <p className="mt-1 text-sm text-ink-500">{template.description}</p>
                    )}
                  </div>
                  <div className="flex shrink-0 flex-wrap gap-2">
                    {template.is_mock && <Badge tone="amber">Full mock</Badge>}
                    <Badge>{template.total_questions} questions</Badge>
                  </div>
                </div>

                {sections.length > 0 && (
                  <ol className="mt-4 grid gap-2 sm:grid-cols-2">
                    {sections.map((section, index) => (
                      <li
                        key={index}
                        className="flex items-center justify-between gap-3 rounded-lg bg-ink-50 px-3 py-2 text-sm"
                      >
                        <span className="text-ink-700">
                          {section.title ?? section.module_slug.replace(/-/g, " ")}
                        </span>
                        <span className="shrink-0 text-ink-500">
                          {section.count} Qs
                          {section.minutes ? ` / ${section.minutes} min` : ""}
                        </span>
                      </li>
                    ))}
                  </ol>
                )}

                <div className="mt-4 flex flex-wrap items-center gap-4">
                  <Button loading={starting === template.id} onClick={() => void start(template)}>
                    Start test
                  </Button>
                  <p className="flex items-center gap-1.5 text-sm text-ink-500">
                    <Clock size={16} /> {template.duration_min} minutes
                  </p>
                  <p className="text-sm text-ink-500">Pass mark {template.pass_percentage}%</p>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
