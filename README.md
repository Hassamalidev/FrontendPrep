# Frontline Prep

A preparation platform for Pakistani armed-forces selection — the Army, Air
Force and Navy — covering the whole funnel from the initial written test through
the five days at an ISSB centre.

```
backend/           FastAPI + SQLAlchemy + Alembic on Neon PostgreSQL
frontend/          Vite + React 19 + TypeScript + Tailwind v4
AcademyFrontend/   the previous JS client, kept only as a reference and asset source
```

Deploying to Neon + Render + Vercel: see **[DEPLOY.md](DEPLOY.md)**.

## Getting it running

```bash
# 1. API
cd backend
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements-dev.txt
cp .env.example .env                 # set DATABASE_URL and JWT_SECRET
alembic upgrade head
python -m app.seed --demo            # catalog, ISSB content, admin, sample question bank
uvicorn app.main:app --reload        # http://localhost:8000/docs

# 2. Client
cd ../frontend
npm install
npm run dev                          # http://localhost:5173
```

## The two constraints that shaped the design

**No LLM API key.** Question generation is a local multi-agent pipeline —
rules, lexicons and regular expressions, with an *optional* spaCy backend the
code detects at import and does without if absent. Five agents run in sequence
(`extract → summarise → write → critique → select`) and record a trace, so the
admin console can explain why 29 drafts became 10 questions. See
[`backend/app/agents/`](backend/app/agents/).

**The database must stay small.** Free tiers throughout (Vercel, Render 512 MB,
Neon 0.5 GB), so options and answers live in JSONB on parent rows rather than
child tables, per-user stats are denormalised, spaced-repetition cards exist only
for questions answered *wrong*, and a retention job prunes agent traces, raw
article bodies and old attempt detail — dropping detail only, never scores.

## State

| Area | Status |
|---|---|
| Backend | 27 tables, 82 endpoints, 101 tests, lint clean |
| Student app | Catalog, practice, mock tests, revision, results, profile and fitness log |
| ISSB suite | PPDT, psych battery (auto-advancing clock), the full nine-task GTO series split indoor/outdoor, mock interview, OLQ profile + progress |
| On paper | Printable practice sheets, and photograph-and-upload with OCR-assisted transcription |
| Staff app | Generation console with the run trace, review queue, question bank, articles, users, maintenance |

Every screen has been exercised against a live backend. The one thing not
verified is visual layout — there is no browser in the build environment, so
spacing and alignment have not been eyeballed.

Each package has its own README with the detail.

## The three services are not interchangeable

The initial written test genuinely differs, and the platform now says how:

| | Intelligence | Academic |
|---|---|---|
| **Army** (PMA Long Course) | Verbal 60, Non-verbal 64 | 50 over English, Maths, Pak Studies, Islamiat, **General Knowledge** |
| **PAF** (GD Pilot) | 100 combined, 40 min | English / Maths / **Physics**, 25 each, 10 min each — **no General Knowledge** |
| **Navy** (PN Cadet) | 100, but **75 non-verbal** to 25 verbal | ~85 over English, Maths or Physics, General Knowledge |

All three are computer-based, no negative marking, 50% sectional pass. The mock
tests follow these patterns section for section. Figures are seed data an admin
should confirm against the current advertisement each intake.

## Staying inside a free tier

This is built to run on free hosting a student can afford, which makes database
size a correctness concern rather than an optimisation:

- **Current affairs are never stored.** They are read live from public RSS,
  cached in process memory for 30 minutes, and dropped. Storing a dozen stories
  a day would add ~11 MB a year of body text for content nobody re-reads.
  `GET /news` returns `"stored": false` — the API states it plainly.
- **Generating from news keeps the questions, not the stories.** No article row,
  no agent-run row; the headline and outlet travel on the question's
  `generation_meta`. Eight live stories produce ~40 questions and **zero** new
  articles.
- **A syllabus question is stored once, not once per service.** The three
  services each have their own module rows so the catalog reads as one funnel
  each, but sampling resolves across modules sharing a slug. That took the seed
  from 256 rows to 66 with every service still seeing every question.
- **No photographs.** Service figures are inline SVG avatars — a few hundred
  bytes against 2.2 MB of PNG, which is bandwidth a free tier pays for on every
  cold visit.

A fresh install is **49 questions and 0 articles**. `--demo` adds four sample
articles purely to demonstrate the generator.

## Current affairs come from live feeds

`POST /admin/news/fetch` reads public RSS from Dawn, The News, Tribune, Geo and
Business Recorder, stores headline / summary / source / link, and — with
`generate=true` — runs each story through the question pipeline into the review
queue. A typical run turns a dozen stories into ~70 drafted questions.

It reads **syndication feeds**, which publishers provide for exactly this. It
does not copy other coaching sites' question banks: that is someone else's
copyrighted content, and the platform writes its own questions from the news
instead.

## The GTO series

Nine tasks over days three and four, in two halves that candidates prepare for
differently:

| Indoor — verbal and written | Outdoor — physical and equipment-bound |
|---|---|
| Group Discussion | Progressive Group Task |
| Lecturette | Half Group Task |
| Group/Military Planning Exercise | Individual Obstacles |
| | Command Task |
| | Snake Race |
| | Final Group Task |

The indoor half is the part you can genuinely rehearse alone at a desk. For the
outdoor half you can still write the plan, and the plan is most of the mark —
each brief carries its real constraints (red ground out of bounds, the load never
touching the ground, helping material that may not be shortened or thrown), a
worked solution, and the assessor rubric.

Sources disagree about where the planning exercise belongs, since it uses a sand
model and is sometimes run outside under a shade. It is filed as indoor here
because nothing about it is physical: written individually, then discussed and
presented.

## Practising on paper

The real tests are written by hand, at speed, on numbered paper — and writing
fast enough to finish sixty WAT sentences is a physical skill you cannot
rehearse by typing. So the platform closes that loop:

1. **Print a sheet** (`/issb/sheet`) — numbered, ruled, with the instructions as
   they are read out on the day.
2. **Solve it under a clock**, on paper.
3. **Photograph it and upload** (`/issb/upload`). The handwriting is read into a
   *draft transcription* which you correct line by line, then it is analysed
   exactly as a typed sitting is.

Two things are deliberate and worth knowing:

- **The transcription is always confirmed by the candidate.** Handwriting
  recognition is not a solved problem, there is no cloud OCR here by design, and
  tesseract reads cursive badly. Silently analysing a misread sentence would
  produce a confident score about words nobody wrote. OCR fills the boxes; the
  human confirms them. With no OCR installed at all the boxes come back empty
  and it becomes a fast transcription form — still better than re-sitting.
- **The photo is never stored.** It is decoded in memory, read, and dropped.
  Only the confirmed text is kept, which also keeps candidate handwriting out of
  the database and a 0.5 GB budget viable.

OCR is optional in exactly the way spaCy is — see `requirements-nlp.txt`.

## Where to start reading

- [`backend/app/agents/`](backend/app/agents/) — the question engine and the OLQ analyser
- [`backend/app/services/attempt_service.py`](backend/app/services/attempt_service.py) — how a paper is frozen and graded
- [`frontend/src/pages/issb/PsychRunner.tsx`](frontend/src/pages/issb/PsychRunner.tsx) — the timed battery
- [`frontend/src/pages/admin/Generate.tsx`](frontend/src/pages/admin/Generate.tsx) — the generation console
#   F r o n t e n d P r e p  
 