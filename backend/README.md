# Frontline Prep — Backend

FastAPI + PostgreSQL backend for a Pakistani armed-forces selection preparation
platform. It covers the whole funnel — initial written test, physical and
medical standards, and a full ISSB simulation suite (WAT, SCT, SRT, TAT, GTO,
lecturette and the IO interview) — for the Army, Air Force and Navy.

## Two constraints shaped everything here

**1. No LLM API key.** Question generation is a local multi-agent pipeline in
[`app/agents/`](app/agents/): rules, lexicons and regular expressions, with an
*optional* spaCy backend that the code detects at import and silently does
without. Paste an article, and five agents run in sequence:

```
extract → summarise → write → critique → select
```

Every stage records what it received, what it produced and how long it took, so
the generation console can explain why 29 candidates became 10 questions rather
than presenting a black box. The critic is the valuable part: it *vetoes*
questions whose answer leaks into the stem, whose stem opens with a pronoun and
needs the previous sentence, whose options are duplicates, or whose answer is a
generic title. On a well-formed news article it accepts about a third of what
was drafted; on incoherent text it rejects almost everything.

**2. The database must stay small.** Deployment targets are free tiers — Vercel,
Render (512 MB), Neon (0.5 GB). The consequences are visible in the schema:

- options and answers live in JSONB on the parent row, not in child tables
  (a 60-word WAT sitting is one row, not sixty; 1 000 students × 12 mock tests
  is 12 000 attempt rows instead of 1.2 M answer rows);
- per-user statistics are denormalised into `user_stats`, so a dashboard costs
  one primary-key lookup instead of an aggregate scan;
- spaced-repetition cards are only created for questions a student got *wrong*,
  so the table tracks mistakes rather than mirroring the whole bank;
- [`app/services/retention.py`](app/services/retention.py) prunes agent traces,
  raw article bodies and old attempt detail — dropping detail only, never scores.

## Running it

```bash
python -m venv .venv && .venv/Scripts/activate     # or source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env                                # then set DATABASE_URL and JWT_SECRET

alembic upgrade head                                # create the schema
python -m app.seed --demo                           # catalog, ISSB content, admin
uvicorn app.main:app --reload
```

API docs at `http://localhost:8000/docs`. The seed is idempotent — re-run it
after adding catalog entries.

`--demo` additionally runs four sample articles through the real generation
pipeline, producing about 38 approved questions spread across the three service
hubs. Without it the catalog is complete but the question bank is empty, so
every practice screen shows an empty state. Drop the flag for a production seed.

Optional NLP layer (adds ~120 MB RAM; the engine works without it):

```bash
pip install -r requirements-nlp.txt
python -m spacy download en_core_web_sm
```

`GET /api/v1/agent/status` reports which backend is actually live.

## Tests

```bash
pytest
```

The suite runs against in-memory SQLite — which is why the models use
`JSONB().with_variant(JSON(), "sqlite")` and VARCHAR-backed enums. The migration
still emits proper PostgreSQL DDL, including the partial index on approved
questions.

## The frontend

The client lives in [`../frontend`](../frontend) — Vite + React 19 + TypeScript +
Tailwind v4, with its types generated from this API's own OpenAPI document.

## Layout

```
app/
  core/        config, async engine, JWT + Argon2, dependencies, enums
  models/      27 SQLAlchemy tables
  schemas/     Pydantic request/response models
  services/    business logic — grading, retention, generation, ISSB analysis
  agents/      the local question engine and the OLQ analyser
  api/v1/      routers (82 endpoints)
  seed/        idempotent catalog and ISSB content
alembic/       migrations
tests/
```

## Notes on the domain logic

- **Papers are frozen at start.** Question ids, answer keys, marks and the
  shuffled option order are copied into `Attempt.blueprint`, so grading never
  re-reads the question table and editing a question later cannot retroactively
  change a submitted paper.
- **Projective tests are not graded, they are described.** WAT/SCT/SRT/TAT, GTO
  plans and interview answers go through
  [`app/agents/olq.py`](app/agents/olq.py), which measures observable properties
  of the writing — completion, speed, positivity, decisiveness, whether the
  candidate *acts* or merely observes, whether other people appear — and maps
  them onto the fifteen Officer Like Qualities. It is a coaching signal, not a
  personality verdict, and the feedback is worded that way.
- **Answer keys never reach a student.** `QuestionOut` has no `answer_keys`
  field at all; the key only appears in `QuestionReviewOut`, after submission.
