/**
 * Picture Perception & Description Test -- screening day, before the group
 * discussion, and the test that decides whether a candidate stays past day one.
 *
 * What makes it PPDT rather than "TAT with a form": the proforma is filled in
 * *before* the story, and an assessor reads the two together. A story that
 * contradicts its own proforma -- a "determined" hero who does nothing, three
 * characters who never appear -- is the most common avoidable fault, so the
 * platform checks exactly that and says which line gave it away.
 *
 * The picture is shown for 30 seconds and then hidden, because that is how it
 * is run; practising with it in view teaches the wrong habit.
 */

import { useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { ApiError } from "@/api/client";
import { ppdt } from "@/api/endpoints";
import type { PpdtResult, PsychItem } from "@/api/types";
import { AnalysisPanel } from "@/components/AnalysisPanel";
import { Countdown } from "@/components/Countdown";
import { Alert, Button, Card, CardHeader, ErrorState, Field, Loading, TextArea } from "@/components/ui";
import { useAsync } from "@/lib/useAsync";

const MOODS = ["determined", "confident", "calm", "hopeful", "worried", "afraid", "angry", "sad"];
const PERCEIVE_SECONDS = 30;

type Phase = "brief" | "perceive" | "proforma" | "story" | "done";

export function Ppdt() {
  const { data: pictures, error, loading, refetch } = useAsync(() => ppdt.pictures(), []);
  const [phase, setPhase] = useState<Phase>("brief");

  // Chosen once per mount and derived during render: an effect that picked the
  // picture would set state on the very first paint for no reason.
  const [seed] = useState(() => Math.random());
  const picture: PsychItem | null = useMemo(
    () => (pictures?.length ? (pictures[Math.floor(seed * pictures.length)] ?? null) : null),
    [pictures, seed],
  );

  const [perception, setPerception] = useState({
    characters: 1,
    main_age: 22,
    main_sex: "male",
    main_mood: "determined",
    action: "",
  });
  const [story, setStory] = useState("");
  const [result, setResult] = useState<PpdtResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const startedAt = useRef(0);

  async function submit() {
    if (!picture) return;
    setBusy(true);
    setSubmitError(null);
    try {
      setResult(
        await ppdt.submit({
          item_id: picture.id,
          perception,
          story,
          duration_sec: Math.max(1, Math.floor((Date.now() - startedAt.current) / 1000)),
        }),
      );
      setPhase("done");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (caught) {
      setSubmitError(caught instanceof ApiError ? caught.message : "Could not submit your story.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <Loading label="Loading pictures" />;
  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <ErrorState error={error} onRetry={refetch} />
      </div>
    );
  }
  if (!picture) return null;

  if (phase === "done" && result) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <h1 className="font-display text-3xl font-bold text-ink-900">Your PPDT read-out</h1>

        <Card className="mt-6">
          <CardHeader
            title="Consistency"
            subtitle="Does your story match the proforma you filled in?"
          />
          <ul className="space-y-3 p-5">
            {result.consistency.map((note, index) => (
              <li key={index} className="flex gap-3 text-sm text-ink-700">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-army-500" />
                <span>{note}</span>
              </li>
            ))}
          </ul>
        </Card>

        <div className="mt-6">
          <AnalysisPanel analysis={result.analysis} />
        </div>

        <Card className="mt-6">
          <CardHeader title="The picture you were shown" />
          <div className="space-y-3 p-5">
            <p className="text-ink-800">{result.item.prompt}</p>
            {result.item.perception_hint && (
              <div className="rounded-lg bg-gold-50 px-3 py-2">
                <p className="text-xs font-medium uppercase text-ink-600">
                  What candidates usually see
                </p>
                <p className="mt-1 text-sm text-ink-700">{result.item.perception_hint}</p>
              </div>
            )}
          </div>
        </Card>

        <Card className="mt-6">
          <CardHeader title="Your story" />
          <p className="whitespace-pre-wrap p-5 text-ink-800">{result.story}</p>
        </Card>

        <div className="mt-10 flex flex-wrap gap-3">
          <Link to="/issb">
            <Button variant="secondary">Back to the suite</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <p className="text-sm font-medium text-army-600">PPDT</p>
      <h1 className="mt-1 font-display text-3xl font-bold text-ink-900">
        Picture Perception and Description
      </h1>

      {phase === "brief" && (
        <Card className="mt-8 p-6">
          <p className="text-ink-700">
            You will see a hazy picture for {PERCEIVE_SECONDS} seconds. It then disappears, and
            you record what you saw before writing the story, exactly as on screening day.
          </p>
          <div className="mt-4">
            <Alert>
              The story and the proforma are read together. Whatever you record, your story has
              to carry out.
            </Alert>
          </div>
          <Button
            size="lg"
            className="mt-5"
            onClick={() => {
              startedAt.current = Date.now();
              setPhase("perceive");
            }}
          >
            Show the picture
          </Button>
        </Card>
      )}

      {phase === "perceive" && (
        <Card className="mt-8 p-6">
          <div className="flex justify-end">
            <Countdown seconds={PERCEIVE_SECONDS} onExpire={() => setPhase("proforma")} />
          </div>
          <p className="mt-6 rounded-lg bg-ink-100 px-5 py-10 text-center text-lg leading-relaxed text-ink-800">
            {picture.prompt}
          </p>
          <p className="mt-4 text-sm text-ink-500">
            Look, do not write. The picture disappears when the clock runs out.
          </p>
        </Card>
      )}

      {phase === "proforma" && (
        <Card className="mt-8">
          <CardHeader title="What did you see?" subtitle="Fill this in before writing the story" />
          <div className="space-y-4 p-5">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field
                label="Number of characters"
                name="characters"
                type="number"
                min={0}
                max={12}
                value={perception.characters}
                onChange={(e) =>
                  setPerception({ ...perception, characters: Number(e.target.value) || 0 })
                }
              />
              <Field
                label="Age of the main character"
                name="main_age"
                type="number"
                min={1}
                max={99}
                value={perception.main_age}
                onChange={(e) =>
                  setPerception({ ...perception, main_age: Number(e.target.value) || 0 })
                }
              />
              <div>
                <label htmlFor="sex" className="mb-1.5 block text-sm font-medium text-ink-700">
                  Sex
                </label>
                <select
                  id="sex"
                  value={perception.main_sex}
                  onChange={(e) => setPerception({ ...perception, main_sex: e.target.value })}
                  className="w-full rounded-lg border border-ink-200 bg-white px-3 py-2"
                >
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                </select>
              </div>
              <div>
                <label htmlFor="mood" className="mb-1.5 block text-sm font-medium text-ink-700">
                  Mood
                </label>
                <select
                  id="mood"
                  value={perception.main_mood}
                  onChange={(e) => setPerception({ ...perception, main_mood: e.target.value })}
                  className="w-full rounded-lg border border-ink-200 bg-white px-3 py-2"
                >
                  {MOODS.map((mood) => (
                    <option key={mood} value={mood}>
                      {mood}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <Field
              label="What is the main character doing?"
              name="action"
              value={perception.action}
              onChange={(e) => setPerception({ ...perception, action: e.target.value })}
              placeholder="organising a rescue party"
              hint="Your story must actually carry this out."
            />

            <Button
              size="lg"
              disabled={!perception.action.trim()}
              onClick={() => setPhase("story")}
            >
              Write the story
            </Button>
          </div>
        </Card>
      )}

      {phase === "story" && (
        <Card className="mt-8">
          <CardHeader
            title="Write the story"
            subtitle="Four minutes. A past, a present, and how it ends."
          />
          <div className="space-y-4 p-5">
            {submitError && <Alert tone="error">{submitError}</Alert>}
            <div className="rounded-lg bg-ink-50 px-3 py-2 text-sm text-ink-600">
              You recorded {perception.characters} character
              {perception.characters === 1 ? "" : "s"}; main character {perception.main_age},{" "}
              {perception.main_sex}, {perception.main_mood}, {perception.action}.
            </div>
            <TextArea
              name="story"
              rows={12}
              value={story}
              onChange={(event) => setStory(event.target.value)}
              placeholder="Who the hero is, what led up to this, what they do, and how it ends."
            />
            <p className="text-xs text-ink-500">
              {story.trim().split(/\s+/).filter(Boolean).length} words
            </p>
            <Button
              size="lg"
              loading={busy}
              disabled={story.trim().length < 20}
              onClick={() => void submit()}
            >
              Submit
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
