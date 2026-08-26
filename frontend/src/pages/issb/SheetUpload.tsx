/**
 * Practise on paper, photograph the sheet, get the same analysis.
 *
 * The honest shape of this feature, and why it looks the way it does:
 *
 *  - **Handwriting recognition is not reliable.** There is no cloud OCR here by
 *    design, and tesseract reads cursive badly. So the reading is a *draft*: the
 *    candidate sees every line beside the word it answers and corrects it before
 *    anything is analysed. Silently analysing a misread sentence would produce a
 *    confident score about words the candidate never wrote.
 *  - **It works with no OCR at all.** If the server has no reader, the boxes
 *    come back empty and this becomes a fast transcription form -- still worth
 *    having, because the alternative is re-sitting the test.
 *  - **The photo is never stored.** It is read in memory server-side and
 *    dropped; only the confirmed text is kept.
 */

import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError } from "@/api/client";
import { sheets } from "@/api/endpoints";
import type { PsychItem, PsychTestType, Transcription } from "@/api/types";
import { Alert, Badge, Button, Card, CardHeader, Loading } from "@/components/ui";

const TESTS: { value: PsychTestType; label: string; count: number }[] = [
  { value: "wat", label: "Word Association Test", count: 60 },
  { value: "sct", label: "Sentence Completion Test", count: 60 },
  { value: "srt", label: "Situation Reaction Test", count: 60 },
];

type Stage = "choose" | "upload" | "confirm";

export function SheetUpload() {
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement | null>(null);

  const [stage, setStage] = useState<Stage>("choose");
  const [testType, setTestType] = useState<PsychTestType>("srt");
  const [count, setCount] = useState(20);
  const [items, setItems] = useState<PsychItem[]>([]);
  const [answers, setAnswers] = useState<string[]>([]);
  const [reading, setReading] = useState<Transcription | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [minutes, setMinutes] = useState(15);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadSheet() {
    setBusy(true);
    setError(null);
    try {
      const plan = await sheets.plan(testType, count);
      setItems(plan.items);
      setAnswers(new Array(plan.items.length).fill(""));
      setMinutes(plan.total_minutes);
      setStage("upload");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not load that sheet.");
    } finally {
      setBusy(false);
    }
  }

  async function readPhoto(file: File) {
    setBusy(true);
    setError(null);
    setPreview(URL.createObjectURL(file));
    try {
      const result = await sheets.transcribe(file, items.length);
      setReading(result);
      // Only overwrite boxes the reader actually filled; anything it could not
      // place stays empty rather than being guessed at.
      setAnswers((previous) =>
        previous.map((existing, index) => result.slots[index]?.trim() || existing),
      );
      setStage("confirm");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not read that image.");
    } finally {
      setBusy(false);
    }
  }

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const result = await sheets.submit({
        test_type: testType,
        item_ids: items.map((item) => item.id),
        responses: answers,
        duration_sec: minutes * 60,
        service: null,
        transcription: reading
          ? { engine: reading.engine, confidence: reading.mean_confidence, lines: reading.lines.length }
          : {},
      });
      navigate(`/issb/psych/result/${result.id}`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not submit the sheet.");
      setBusy(false);
    }
  }

  const answered = answers.filter((a) => a.trim()).length;

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="font-display text-3xl font-bold text-ink-900">Upload an answer sheet</h1>
      <p className="mt-2 text-ink-500">
        Sat the test on paper, the way you will on the day? Photograph the sheet and get the
        same read-out.
      </p>

      {error && (
        <div className="mt-6">
          <Alert tone="error">{error}</Alert>
        </div>
      )}

      {stage === "choose" && (
        <Card className="mt-8">
          <CardHeader title="What did you sit?" subtitle="Pick the same set you printed" />
          <div className="space-y-5 p-5">
            <div>
              <label htmlFor="test" className="mb-1.5 block text-sm font-medium text-ink-700">
                Test
              </label>
              <select
                id="test"
                value={testType}
                onChange={(event) => setTestType(event.target.value as PsychTestType)}
                className="w-full rounded-lg border border-ink-200 bg-white px-3 py-2"
              >
                {TESTS.map((test) => (
                  <option key={test.value} value={test.value}>
                    {test.label}
                  </option>
                ))}
              </select>
            </div>

            <fieldset>
              <legend className="mb-2 text-sm font-medium text-ink-700">
                How many items were on the sheet?
              </legend>
              <div className="flex flex-wrap gap-2">
                {[10, 20, 30, 60].map((option) => (
                  <button
                    key={option}
                    type="button"
                    aria-pressed={count === option}
                    onClick={() => setCount(option)}
                    className={`rounded-lg px-4 py-2 text-sm font-medium ring-1 transition ${
                      count === option
                        ? "bg-army-500 text-white ring-army-500"
                        : "bg-white text-ink-700 ring-ink-200 hover:bg-ink-50"
                    }`}
                  >
                    {option}
                  </button>
                ))}
              </div>
            </fieldset>

            <Alert>
              The stimuli are drawn fresh, so they will not match a sheet you printed earlier.
              Print from this page, solve it, then come back and upload.
            </Alert>

            <Button size="lg" loading={busy} onClick={() => void loadSheet()}>
              Continue
            </Button>
          </div>
        </Card>
      )}

      {stage === "upload" && (
        <Card className="mt-8">
          <CardHeader
            title="Photograph your sheet"
            subtitle={`${items.length} items - daylight, flat on a table, whole page in frame`}
          />
          <div className="space-y-5 p-5">
            <input
              ref={fileRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void readPhoto(file);
              }}
            />

            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              className="flex w-full flex-col items-center gap-2 rounded-card border-2 border-dashed border-ink-200 px-6 py-12 text-center transition hover:border-army-500 hover:bg-army-50"
            >
              <span className="font-medium text-ink-800">Choose a photo</span>
              <span className="text-sm text-ink-500">JPEG, PNG or WebP, up to 8 MB</span>
            </button>

            <p className="text-sm text-ink-500">
              Your photo is read on the server and discarded. It is never stored; only the text
              you confirm is kept.
            </p>

            <div className="flex flex-wrap gap-3">
              <Button variant="secondary" onClick={() => setStage("confirm")}>
                Skip the photo and type it in
              </Button>
              <Button variant="ghost" onClick={() => setStage("choose")}>
                Back
              </Button>
            </div>
          </div>
        </Card>
      )}


      {stage === "confirm" && (
        <>
          {reading && (
            <div className="mt-6">
              {reading.available ? (
                <Alert tone={reading.mean_confidence >= 70 ? "success" : "info"}>
                  Read with {reading.engine}, {Math.round(reading.mean_confidence)}% average
                  confidence over {reading.lines.length} lines.{" "}
                  <strong className="font-medium">Check every line before submitting.</strong>{" "}
                  Anything misread is analysed as though you wrote it.
                </Alert>
              ) : (
                <Alert>
                  No handwriting reader is installed on this server
                  {reading.note ? ` (${reading.note})` : ""}, so nothing was filled in
                  automatically. Type your answers below. It is still faster than sitting the
                  test again.
                </Alert>
              )}
            </div>
          )}

          <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-ink-500">
              {answered} of {items.length} filled in
            </p>
            <label className="flex items-center gap-2 text-sm text-ink-700">
              Time taken
              <input
                type="number"
                min={1}
                max={180}
                value={minutes}
                onChange={(event) => setMinutes(Math.max(1, Number(event.target.value) || 1))}
                className="w-20 rounded-lg border border-ink-200 px-2 py-1 text-right tabular-nums"
              />
              min
            </label>
          </div>

          {preview && (
            <details className="mt-4">
              <summary className="cursor-pointer text-sm font-medium text-army-600">
                Show the photo while you check
              </summary>
              <img
                src={preview}
                alt="The answer sheet you uploaded"
                className="mt-3 max-h-128 w-full rounded-card object-contain ring-1 ring-ink-200"
              />
            </details>
          )}

          <ul className="mt-6 space-y-3">
            {items.map((item, index) => (
              <li key={item.id}>
                <Card className="p-4">
                  <div className="flex items-start gap-3">
                    <span className="mt-2 w-6 shrink-0 text-right font-mono text-sm text-ink-500">
                      {index + 1}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-ink-800">{item.prompt}</p>
                      <label className="sr-only" htmlFor={`answer-${item.id}`}>
                        Your answer to item {index + 1}
                      </label>
                      <input
                        id={`answer-${item.id}`}
                        value={answers[index] ?? ""}
                        onChange={(event) =>
                          setAnswers((previous) => {
                            const next = [...previous];
                            next[index] = event.target.value;
                            return next;
                          })
                        }
                        placeholder="What you wrote on the sheet"
                        className="mt-2 w-full rounded-lg border border-ink-200 px-3 py-2 text-ink-900 placeholder:text-ink-500"
                      />
                    </div>
                  </div>
                </Card>
              </li>
            ))}
          </ul>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Button size="lg" loading={busy} disabled={answered === 0} onClick={() => void submit()}>
              Submit for analysis
            </Button>
            <Badge>
              {answered}/{items.length}
            </Badge>
            {answered === 0 && (
              <span className="text-sm text-ink-500">Fill in at least one answer.</span>
            )}
          </div>
        </>
      )}

      {busy && stage === "upload" && <Loading label="Reading your handwriting" />}
    </div>
  );
}
