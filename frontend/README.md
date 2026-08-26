# Frontline Prep — Frontend

Vite + React 19 + TypeScript + Tailwind v4 client for the [backend](../backend).

## Running it

The backend must be up first — the dev server proxies `/api` to
`http://127.0.0.1:8000`, so the browser never sees CORS and token handling
behaves exactly as it will behind a single domain in production.

```bash
# terminal 1 — backend, with a starter question bank
cd ../backend
python -m app.seed --demo
uvicorn app.main:app --reload

# terminal 2 — this app
npm install
npm run dev            # http://localhost:5173
```

| Script | What it does |
|---|---|
| `npm run dev` | Dev server with the `/api` proxy |
| `npm run build` | Typecheck (`tsc -b`) then production build |
| `npm run typecheck` | Types only, no emit |
| `npm run gen:api` | Regenerate `src/api/schema.d.ts` from `openapi.json` |
| `npm run lint` | oxlint |

## Types come from the backend

`src/api/schema.d.ts` is **generated**, not written. Refresh it whenever the API
changes shape:

```bash
cd ../backend && python -c "import json; from app.main import app; json.dump(app.openapi(), open('openapi.json','w'), indent=2)"
cp ../backend/openapi.json openapi.json
npm run gen:api
```

`src/api/types.ts` contains only aliases onto that generated file. Renaming a
field in a Pydantic model then breaks `npm run typecheck` rather than breaking a
page in a user's browser. Nothing else in the app should declare a payload shape
by hand.

## How the HTTP layer behaves

`src/api/client.ts` handles three things so no page has to:

- **Transparent refresh.** A 401 triggers one refresh and one retry.
  Concurrent 401s share a single in-flight refresh promise — important because
  the backend revokes the whole session family if a rotated refresh token is
  replayed, so a stampede would sign the user out.
- **Error normalisation.** FastAPI's `{detail}` and `{detail, errors[]}` both
  arrive as one `ApiError` carrying a `fieldErrors` map that forms read directly.
- **Session expiry.** When a refresh genuinely fails, tokens are cleared once and
  `AuthProvider` reacts, so every guarded route responds together.

Tokens live in `localStorage` (see `src/api/tokens.ts` for why, and what
mitigates it).

## What is built

**Done:**

- the shell — layout, routing, guarded routes;
- auth — register, sign in, session restore, transparent refresh, sign out;
- the catalog — services → selection funnel → module;
- the practice slice — drill setup, the timed paper, the marked result with
  per-question review;
- **the ISSB simulation suite** — PPDT with the screening-day proforma, the
  psychological battery (WAT, SCT, SRT, TAT) under a per-item clock that advances
  by itself, GTO briefs with a plan editor scored against the rubric and a worked
  solution, the mock interview, and the cumulative OLQ profile with a progress
  line across sittings;
- **the paper loop** — a printable practice sheet, and photograph-and-upload with
  an OCR-assisted transcription the candidate corrects before anything is
  analysed.

- mock tests, the spaced-repetition revision drill, the article reader, the
  profile with its physical-training log, about and contact;
- **the staff app** — the generation console (paste an article, preview, inspect
  the pipeline trace, save), the review queue, the question bank with filters,
  articles, users, and maintenance.

Nothing is stubbed. Every route resolves to a real screen backed by a real
endpoint.

**Not verified:** visual layout. There is no browser in the build environment, so
these screens have been checked by typecheck, lint, build and end-to-end data
paths, but not looked at.

## The ISSB screens

Two decisions there are deliberate and worth keeping:

- **The psychological battery advances on the clock, not on a button.** At a
  board the slide changes whether or not you have finished, and there is no going
  back. A Next-button-only version teaches a habit that costs marks on the day,
  so `Countdown` fires `onExpire` and the runner banks whatever was typed.
- **The mock interview is deliberately *not* timed.** An IO interview runs the
  best part of an hour; what is worth practising is composing a structured answer,
  not beating a clock. Time is measured and reported, never used to cut you off.

Charts follow the project's dataviz method: the OLQ profile is one hue across all
fifteen nominal categories (colouring bars by their own value would re-encode what
bar length already shows), no legend for a single series, a table view for
screen readers, and meters for the 0–1 signals. Colour choices were validated for
contrast rather than eyeballed — which is how `text-ink-400` was caught at 3.10:1
against white, below the 4.5:1 floor, and moved to `ink-500`.

## Notes

- **No icon package.** `src/components/icons.tsx` inlines the ~20 glyphs used.
  The usual library ships 1,500 files and made `npm install` fail repeatedly on
  Windows with ENOTEMPTY.
- **TypeScript is pinned to 5.x.** The Vite template installs 6.x, which
  `openapi-typescript` does not yet support.
- **The paper survives a reload.** Selections are mirrored to `sessionStorage`
  keyed by attempt id, so a dropped connection mid-test does not cost the sitting.
- **Per-question timing is recorded**, because the backend uses it for difficulty
  calibration — the clock starts when a question is shown, not when the paper does.
