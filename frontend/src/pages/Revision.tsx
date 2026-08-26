/**
 * Spaced-repetition drill.
 *
 * Cards exist only for questions answered wrong or flagged, so this is a
 * backlog of mistakes rather than a second copy of the bank. Starting with
 * `only_weak` draws whatever is due today.
 */

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ApiError } from "@/api/client";
import { me, practice } from "@/api/endpoints";
import { Alert, Button, Card, EmptyState, Loading } from "@/components/ui";
import { useAsync } from "@/lib/useAsync";

export function Revision() {
  const navigate = useNavigate();
  const { data, loading } = useAsync(() => me.dashboard(), []);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const due = data?.due_revision ?? 0;

  async function start() {
    setStarting(true);
    setError(null);
    try {
      const attempt = await practice.start({
        template_id: null,
        module_id: null,
        topic_id: null,
        count: Math.min(20, Math.max(1, due)),
        difficulty: null,
        mode: "practice",
        only_weak: true,
      });
      navigate(`/attempts/${attempt.id}`, { state: { attempt } });
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not start the drill.");
    } finally {
      setStarting(false);
    }
  }

  if (loading) return <Loading label="Checking your backlog" />;

  return (
    <div className="mx-auto max-w-2xl px-4 py-16">
      <h1 className="font-display text-3xl font-bold text-ink-900">Revision</h1>
      <p className="mt-2 text-ink-500">
        Questions you got wrong come back on a schedule: one day, then six, then further
        apart each time you get them right.
      </p>

      {error && (
        <div className="mt-6">
          <Alert tone="error">{error}</Alert>
        </div>
      )}

      {due === 0 ? (
        <div className="mt-8">
          <EmptyState
            title="Nothing due today"
            body="Sit a drill, and anything you get wrong will appear here tomorrow."
            action={
              <Link to="/practice">
                <Button>Go to practice</Button>
              </Link>
            }
          />
        </div>
      ) : (
        <Card className="mt-8 p-6">
          <p className="font-display text-4xl font-bold text-ink-900">{due}</p>
          <p className="mt-1 text-ink-500">question{due === 1 ? "" : "s"} ready to try again</p>
          <Button size="lg" className="mt-6" loading={starting} onClick={() => void start()}>
            Start revision
          </Button>
        </Card>
      )}
    </div>
  );
}
