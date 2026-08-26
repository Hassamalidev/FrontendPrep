import { useState } from "react";

import { ApiError } from "@/api/client";
import { admin, catalog } from "@/api/endpoints";
import type { ContentStatus, Difficulty, QuestionAdmin } from "@/api/types";
import { Alert, Badge, Button, Card, EmptyState, ErrorState, Field, Loading } from "@/components/ui";
import { useAsync } from "@/lib/useAsync";

const STATUSES: ContentStatus[] = ["draft", "in_review", "approved", "rejected", "archived"];
const LEVELS: Difficulty[] = ["easy", "medium", "hard"];

export function QuestionBank() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<ContentStatus | "">("approved");
  const [difficulty, setDifficulty] = useState<Difficulty | "">("");
  const [moduleId, setModuleId] = useState<number | "">("");
  const [actionError, setActionError] = useState<string | null>(null);

  const { data: modules } = useAsync(() => catalog.modules({}), []);
  const { data, error, loading, refetch } = useAsync(
    () =>
      admin.questions({
        page,
        size: 20,
        q: query || undefined,
        status: status || undefined,
        difficulty: difficulty || undefined,
        module_id: moduleId === "" ? undefined : Number(moduleId),
      }),
    [page, query, status, difficulty, moduleId],
  );

  async function remove(question: QuestionAdmin) {
    if (!window.confirm("Delete this question permanently?")) return;
    setActionError(null);
    try {
      await admin.deleteQuestion(question.id);
      refetch();
    } catch (caught) {
      setActionError(caught instanceof ApiError ? caught.message : "Could not delete it.");
    }
  }

  async function setStatusOf(question: QuestionAdmin, next: ContentStatus) {
    setActionError(null);
    try {
      await admin.review(question.id, { status: next });
      refetch();
    } catch (caught) {
      setActionError(caught instanceof ApiError ? caught.message : "Could not update it.");
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="font-display text-3xl font-bold text-ink-900">Question bank</h1>

      <Card className="mt-6 p-4">
        <form
          className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"
          onSubmit={(event) => {
            event.preventDefault();
            setPage(1);
            setQuery(search.trim());
          }}
        >
          <Field
            label="Search"
            name="q"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Words in the question"
          />

          <div>
            <label htmlFor="status" className="mb-1.5 block text-sm font-medium text-ink-700">
              Status
            </label>
            <select
              id="status"
              value={status}
              onChange={(event) => {
                setPage(1);
                setStatus(event.target.value as ContentStatus | "");
              }}
              className="w-full rounded-lg border border-ink-200 bg-white px-3 py-2"
            >
              <option value="">Any</option>
              {STATUSES.map((option) => (
                <option key={option} value={option}>
                  {option.replace(/_/g, " ")}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="difficulty" className="mb-1.5 block text-sm font-medium text-ink-700">
              Difficulty
            </label>
            <select
              id="difficulty"
              value={difficulty}
              onChange={(event) => {
                setPage(1);
                setDifficulty(event.target.value as Difficulty | "");
              }}
              className="w-full rounded-lg border border-ink-200 bg-white px-3 py-2"
            >
              <option value="">Any</option>
              {LEVELS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="module" className="mb-1.5 block text-sm font-medium text-ink-700">
              Module
            </label>
            <select
              id="module"
              value={moduleId}
              onChange={(event) => {
                setPage(1);
                setModuleId(event.target.value === "" ? "" : Number(event.target.value));
              }}
              className="w-full rounded-lg border border-ink-200 bg-white px-3 py-2"
            >
              <option value="">Any</option>
              {(modules ?? []).map((module) => (
                <option key={module.id} value={module.id}>
                  {module.title}
                </option>
              ))}
            </select>
          </div>

          <Button type="submit" className="sm:col-span-2 lg:col-span-1">
            Search
          </Button>
        </form>
      </Card>

      {actionError && (
        <div className="mt-4">
          <Alert tone="error">{actionError}</Alert>
        </div>
      )}

      {loading && <Loading label="Loading questions" />}
      {error && (
        <div className="mt-6">
          <ErrorState error={error} onRetry={refetch} />
        </div>
      )}

      {!loading && !error && <Results data={data} page={page} setPage={setPage} onRemove={remove} onSetStatus={setStatusOf} />}
    </div>
  );
}

function Results({
  data,
  page,
  setPage,
  onRemove,
  onSetStatus,
}: {
  data: { items: QuestionAdmin[]; total: number; page: number; pages: number } | null;
  page: number;
  setPage: (updater: (previous: number) => number) => void;
  onRemove: (question: QuestionAdmin) => void;
  onSetStatus: (question: QuestionAdmin, status: ContentStatus) => void;
}) {
  const items = data?.items ?? [];

  return (
    <>
      <p className="mt-6 text-sm text-ink-500">{data?.total ?? 0} matching</p>

      {items.length === 0 ? (
        <div className="mt-4">
          <EmptyState title="Nothing matches" body="Try widening the filters." />
        </div>
      ) : (
        <ul className="mt-4 space-y-3">
          {items.map((question) => (
            <li key={question.id}>
              <Card className="p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <p className="min-w-0 text-ink-900">{question.stem}</p>
                  <div className="flex shrink-0 flex-wrap gap-2">
                    <Badge
                      tone={
                        question.status === "approved"
                          ? "green"
                          : question.status === "rejected"
                            ? "red"
                            : "amber"
                      }
                    >
                      {question.status}
                    </Badge>
                    <Badge>{question.difficulty}</Badge>
                    <Badge>{question.origin}</Badge>
                  </div>
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-ink-500">
                  <span>#{question.id}</span>
                  {question.times_served > 0 && (
                    <span>
                      served {question.times_served}, correct {question.times_correct}
                      {question.facility !== null && question.facility !== undefined
                        ? ` (facility ${question.facility})`
                        : ""}
                    </span>
                  )}
                </div>

                <div className="mt-3 flex flex-wrap gap-2">
                  {question.status !== "approved" && (
                    <Button size="sm" onClick={() => onSetStatus(question, "approved")}>
                      Approve
                    </Button>
                  )}
                  {question.status !== "archived" && (
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => onSetStatus(question, "archived")}
                    >
                      Archive
                    </Button>
                  )}
                  <Button size="sm" variant="danger" onClick={() => onRemove(question)}>
                    Delete
                  </Button>
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}

      {(data?.pages ?? 1) > 1 && (
        <div className="mt-8 flex items-center justify-between">
          <Button variant="secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            Previous
          </Button>
          <p className="text-sm text-ink-500">
            Page {data?.page} of {data?.pages}
          </p>
          <Button
            variant="secondary"
            disabled={page >= (data?.pages ?? 1)}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </>
  );
}
