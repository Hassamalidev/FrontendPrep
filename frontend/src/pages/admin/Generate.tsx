/**
 * The generation console.
 *
 * Paste an article and run the local pipeline. Two things this screen insists on:
 *
 *  - **Preview before you write.** The dry run scores pasted text without
 *    creating an article or a run row, so judging a source costs nothing.
 *  - **Generated items land as drafts.** Nothing reaches a student without a
 *    human decision -- that is what the review queue is for.
 */

import { useState } from "react";
import { Link } from "react-router-dom";

import { ApiError } from "@/api/client";
import { admin, agent } from "@/api/endpoints";
import type { GenerateOut } from "@/api/types";
import { AgentTrace } from "@/pages/admin/AgentTrace";
import { GeneratedItems } from "@/pages/admin/GeneratedItems";
import { Alert, Badge, Button, Card, Field, Loading, TextArea } from "@/components/ui";
import { useAsync } from "@/lib/useAsync";

type Counts = {
  mcq: number;
  true_false: number;
  fill_blank: number;
  short_answer: number;
  sct: number;
  srt: number;
  interview: number;
};

const DEFAULT_COUNTS: Counts = {
  mcq: 8,
  true_false: 4,
  fill_blank: 3,
  short_answer: 0,
  sct: 3,
  srt: 3,
  interview: 2,
};

const COUNT_FIELDS: { key: keyof Counts; label: string }[] = [
  { key: "mcq", label: "Multiple choice" },
  { key: "true_false", label: "True / false" },
  { key: "fill_blank", label: "Fill in the blank" },
  { key: "short_answer", label: "Short answer" },
  { key: "sct", label: "SCT stems" },
  { key: "srt", label: "SRT situations" },
  { key: "interview", label: "Interview questions" },
];

export function Generate() {
  const { data: status } = useAsync(() => agent.status(), []);

  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [counts, setCounts] = useState<Counts>(DEFAULT_COUNTS);
  const [autoApprove, setAutoApprove] = useState(false);
  const [busy, setBusy] = useState<"preview" | "save" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GenerateOut | null>(null);
  const [saved, setSaved] = useState(false);

  const tooShort = body.trim().length < (status?.min_article_chars ?? 320);

  async function preview() {
    setBusy("preview");
    setError(null);
    setSaved(false);
    try {
      // Fields with server-side defaults are emitted as required by the type
      // generator (right for responses, verbose for request bodies), so they
      // are spelled out rather than relied on.
      setResult(
        await agent.preview({ ...counts, text: body, auto_approve: false, dry_run: true }),
      );
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not run the pipeline.");
    } finally {
      setBusy(null);
    }
  }

  async function saveAndGenerate() {
    setBusy("save");
    setError(null);
    try {
      const article = await admin.createArticle({
        title: title.trim() || body.trim().slice(0, 60),
        body,
        category: "current_affairs",
        status: "approved",
        is_featured: false,
      });
      setResult(
        await agent.generate(article.id, { ...counts, auto_approve: autoApprove, dry_run: false }),
      );
      setSaved(true);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not save and generate.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="font-display text-3xl font-bold text-ink-900">Generate questions</h1>
      <p className="mt-2 max-w-2xl text-ink-500">
        Paste an article and the local pipeline turns it into questions. Nothing is sent to
        an external service.
      </p>

      {status && (
        <div className="mt-4 flex flex-wrap items-center gap-2 text-sm">
          <Badge tone="green">{status.engine} engine</Badge>
          {status.note && <span className="text-ink-500">{status.note}</span>}
          <span className="text-ink-500">
            quality threshold {status.min_quality}, max {status.max_questions_per_run} per run
          </span>
        </div>
      )}

      <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_18rem]">
        <div className="space-y-4">
          <Field
            label="Headline"
            name="title"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Used when you save the article"
          />
          <TextArea
            label="Article text"
            name="body"
            rows={16}
            value={body}
            onChange={(event) => setBody(event.target.value)}
            placeholder="Paste the full article here..."
          />
          <p className="text-xs text-ink-500">
            {body.trim().length.toLocaleString()} characters
            {tooShort ? ` (at least ${status?.min_article_chars ?? 320} needed)` : ""}
          </p>

          {error && <Alert tone="error">{error}</Alert>}

          <div className="flex flex-wrap gap-3">
            <Button
              variant="secondary"
              loading={busy === "preview"}
              disabled={tooShort}
              onClick={() => void preview()}
            >
              Preview only
            </Button>
            <Button
              loading={busy === "save"}
              disabled={tooShort}
              onClick={() => void saveAndGenerate()}
            >
              Save article and generate
            </Button>
          </div>
        </div>

        <Card className="h-fit p-5">
          <h2 className="font-semibold text-ink-900">What to produce</h2>
          <div className="mt-4 space-y-3">
            {COUNT_FIELDS.map((field) => (
              <label key={field.key} className="flex items-center justify-between gap-3 text-sm">
                <span className="text-ink-700">{field.label}</span>
                <input
                  type="number"
                  min={0}
                  max={40}
                  value={counts[field.key]}
                  onChange={(event) =>
                    setCounts((previous) => ({
                      ...previous,
                      [field.key]: Math.max(0, Math.min(40, Number(event.target.value) || 0)),
                    }))
                  }
                  className="w-16 rounded-lg border border-ink-200 px-2 py-1 text-right tabular-nums"
                />
              </label>
            ))}
          </div>

          <label className="mt-5 flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              checked={autoApprove}
              onChange={(event) => setAutoApprove(event.target.checked)}
              className="mt-0.5"
            />
            <span className="text-ink-700">
              Approve immediately
              <span className="block text-xs text-ink-500">
                Skips the review queue. Leave off unless you will check them yourself.
              </span>
            </span>
          </label>
        </Card>
      </div>

      {busy && <Loading label="Running the pipeline" />}

      {result && !busy && (
        <div className="mt-10 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="font-display text-2xl font-bold text-ink-900">
              {result.persisted ? "Generated" : "Preview"}
            </h2>
            {saved && (
              <Link to="/admin/queue" className="text-sm font-medium text-army-600 hover:underline">
                Go to the review queue
              </Link>
            )}
          </div>

          {!result.persisted && (
            <Alert>Nothing was written. This is what the pipeline would produce.</Alert>
          )}

          <AgentTrace run={result.run} />
          <GeneratedItems result={result} />
        </div>
      )}
    </div>
  );
}
