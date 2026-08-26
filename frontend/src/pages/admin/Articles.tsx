import { useState } from "react";
import { Link } from "react-router-dom";

import { ApiError } from "@/api/client";
import { admin } from "@/api/endpoints";
import { Alert, Badge, Button, Card, EmptyState, ErrorState, Loading } from "@/components/ui";
import { useAsync } from "@/lib/useAsync";
import { formatDate } from "@/lib/format";

export function AdminArticles() {
  const [page, setPage] = useState(1);
  const { data, error, loading, refetch } = useAsync(
    () => admin.articles({ page, size: 20 }),
    [page],
  );
  const [actionError, setActionError] = useState<string | null>(null);

  async function remove(id: number, title: string) {
    if (!window.confirm(`Delete "${title}"? Questions generated from it are kept.`)) return;
    setActionError(null);
    try {
      await admin.deleteArticle(id);
      refetch();
    } catch (caught) {
      setActionError(caught instanceof ApiError ? caught.message : "Could not delete it.");
    }
  }

  if (loading) return <Loading label="Loading articles" />;
  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12">
        <ErrorState error={error} onRetry={refetch} />
      </div>
    );
  }

  const items = data?.items ?? [];

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-3xl font-bold text-ink-900">Articles</h1>
        <Link to="/admin/generate">
          <Button>Add and generate</Button>
        </Link>
      </div>
      <p className="mt-2 text-ink-500">
        Source material for the question engine. Bodies are dropped automatically once
        questions have been generated and the retention window passes.
      </p>

      {actionError && (
        <div className="mt-4">
          <Alert tone="error">{actionError}</Alert>
        </div>
      )}

      {items.length === 0 ? (
        <div className="mt-8">
          <EmptyState
            title="No articles yet"
            body="Paste one into the generation console to get started."
            action={
              <Link to="/admin/generate">
                <Button>Open the console</Button>
              </Link>
            }
          />
        </div>
      ) : (
        <ul className="mt-8 space-y-3">
          {items.map((article) => (
            <li key={article.id}>
              <Card className="p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h2 className="font-semibold text-ink-900">{article.title}</h2>
                    <p className="mt-1 text-sm text-ink-500">
                      {article.category.replace(/_/g, " ")}
                      {article.source_name ? ` - ${article.source_name}` : ""}
                      {article.published_on ? ` - ${formatDate(article.published_on)}` : ""}
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-wrap gap-2">
                    <Badge tone={article.status === "approved" ? "green" : "amber"}>
                      {article.status}
                    </Badge>
                    {article.generated && (
                      <Badge tone="green">{article.generated_count} generated</Badge>
                    )}
                    {article.body_pruned && <Badge>body pruned</Badge>}
                  </div>
                </div>

                {article.summary && (
                  <p className="mt-3 line-clamp-2 text-sm text-ink-600">{article.summary}</p>
                )}

                <div className="mt-4">
                  <Button
                    size="sm"
                    variant="danger"
                    onClick={() => void remove(article.id, article.title)}
                  >
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
    </div>
  );
}
