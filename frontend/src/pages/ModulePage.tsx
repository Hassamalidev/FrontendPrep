import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { ApiError } from "@/api/client";
import { catalog, practice } from "@/api/endpoints";
import type { Difficulty } from "@/api/types";
import { Alert, Badge, Button, Card, CardHeader, ErrorState, Loading } from "@/components/ui";
import { useAuth } from "@/auth/useAuth";
import { useAsync } from "@/lib/useAsync";
import { practisedElsewhere } from "@/lib/modules";

const LENGTHS = [10, 20, 30];
const LEVELS: { value: Difficulty | ""; label: string }[] = [
  { value: "", label: "Mixed" },
  { value: "easy", label: "Easy" },
  { value: "medium", label: "Medium" },
  { value: "hard", label: "Hard" },
];

export function ModulePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  const { data: module, error, loading, refetch } = useAsync(
    () => catalog.module(id!),
    [id],
  );

  const [count, setCount] = useState(20);
  const [difficulty, setDifficulty] = useState<Difficulty | "">("");
  const [topicId, setTopicId] = useState<number | "">("");
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  async function start() {
    if (!module) return;
    if (!isAuthenticated) {
      navigate("/login", { state: { from: `/modules/${module.id}` } });
      return;
    }

    setStarting(true);
    setStartError(null);
    try {
      const attempt = await practice.start({
        module_id: module.id,
        count,
        mode: "module",
        difficulty: difficulty || undefined,
        topic_id: topicId === "" ? undefined : Number(topicId),
        only_weak: false,
      });
      navigate(`/attempts/${attempt.id}`, { state: { attempt } });
    } catch (caught) {
      setStartError(
        caught instanceof ApiError ? caught.message : "Could not start the drill. Try again.",
      );
    } finally {
      setStarting(false);
    }
  }

  if (loading) return <Loading label="Loading module" />;
  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12">
        <ErrorState error={error} onRetry={refetch} />
      </div>
    );
  }
  if (!module) return null;

  // Reached directly (a bookmark, a stale link): send them where the practice is
  // rather than showing a drill form that cannot start.
  const destination = practisedElsewhere(module.slug);
  if (destination) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16">
        <h1 className="font-display text-3xl font-bold text-ink-900">{module.title}</h1>
        {module.subtitle && <p className="mt-2 text-ink-500">{module.subtitle}</p>}
        <Card className="mt-8 p-6">
          <p className="text-ink-700">{destination.note}</p>
          <Link to={destination.to} className="mt-5 inline-block">
            <Button size="lg">{destination.action}</Button>
          </Link>
        </Card>
      </div>
    );
  }

  const empty = module.approved_question_count === 0;

  return (
    <div className="mx-auto max-w-4xl px-4 py-12">
      <h1 className="font-display text-3xl font-bold text-ink-900">{module.title}</h1>
      {module.subtitle && <p className="mt-2 text-ink-500">{module.subtitle}</p>}
      <p className="mt-3 text-sm text-ink-500">
        {module.approved_question_count} approved question
        {module.approved_question_count === 1 ? "" : "s"} available
      </p>

      <Card className="mt-8">
        <CardHeader title="Start a drill" subtitle="Questions are drawn fresh each time." />
        <div className="space-y-5 p-5">
          {startError && <Alert tone="error">{startError}</Alert>}
          {empty && (
            <Alert>
              No questions have been approved for this module yet. Try another module while the
              bank is being filled.
            </Alert>
          )}

          <fieldset>
            <legend className="mb-2 text-sm font-medium text-ink-700">How many questions?</legend>
            <div className="flex flex-wrap gap-2">
              {LENGTHS.map((value) => (
                <button
                  key={value}
                  type="button"
                  aria-pressed={count === value}
                  onClick={() => setCount(value)}
                  className={`rounded-lg px-4 py-2 text-sm font-medium ring-1 transition ${
                    count === value
                      ? "bg-army-500 text-white ring-army-500"
                      : "bg-white text-ink-700 ring-ink-200 hover:bg-ink-50"
                  }`}
                >
                  {value}
                </button>
              ))}
            </div>
          </fieldset>

          <fieldset>
            <legend className="mb-2 text-sm font-medium text-ink-700">Difficulty</legend>
            <div className="flex flex-wrap gap-2">
              {LEVELS.map((level) => (
                <button
                  key={level.label}
                  type="button"
                  aria-pressed={difficulty === level.value}
                  onClick={() => setDifficulty(level.value)}
                  className={`rounded-lg px-4 py-2 text-sm font-medium ring-1 transition ${
                    difficulty === level.value
                      ? "bg-army-500 text-white ring-army-500"
                      : "bg-white text-ink-700 ring-ink-200 hover:bg-ink-50"
                  }`}
                >
                  {level.label}
                </button>
              ))}
            </div>
          </fieldset>

          {module.topics.length > 0 && (
            <div>
              <label htmlFor="topic" className="mb-1.5 block text-sm font-medium text-ink-700">
                Focus on one topic (optional)
              </label>
              <select
                id="topic"
                className="w-full rounded-lg border border-ink-200 bg-white px-3 py-2 text-ink-900"
                value={topicId}
                onChange={(e) => setTopicId(e.target.value === "" ? "" : Number(e.target.value))}
              >
                <option value="">Everything in this module</option>
                {module.topics.map((topic) => (
                  <option key={topic.id} value={topic.id}>
                    {topic.name} ({topic.approved_question_count})
                  </option>
                ))}
              </select>
            </div>
          )}

          <Button size="lg" onClick={() => void start()} loading={starting} disabled={empty}>
            Start drill
          </Button>
        </div>
      </Card>

      {module.topics.length > 0 && (
        <section className="mt-10">
          <h2 className="font-display text-xl font-bold text-ink-900">Topics</h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {module.topics.map((topic) => (
              <Card key={topic.id} className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3 className="font-medium text-ink-800">{topic.name}</h3>
                    {topic.blurb && <p className="mt-1 text-sm text-ink-500">{topic.blurb}</p>}
                  </div>
                  <Badge>{topic.approved_question_count}</Badge>
                </div>
              </Card>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
