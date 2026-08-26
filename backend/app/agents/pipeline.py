"""The orchestrator: article in, reviewable items out.

Five agents run in sequence, each recording what it received, what it produced
and how long it took. That trace is the whole point of building this as a
pipeline rather than one function -- the super admin can see *why* 42 candidates
became 11 questions, and tune the thresholds instead of guessing.

    extract -> write -> critique -> dedupe -> select

Nothing here touches the database or the network. It is deterministic for a
given (text, config) pair, which makes it testable and makes a dry run mean
something.
"""

from __future__ import annotations

import hashlib
import random
import re
import time
from dataclasses import dataclass, field

from app.agents import critic, nlp, writers
from app.agents import facts as facts_agent
from app.core.config import settings
from app.core.enums import Difficulty, QuestionType

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s]")


@dataclass(slots=True)
class Step:
    agent: str
    label: str
    input: int = 0
    output: int = 0
    ms: int = 0
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "agent": self.agent,
            "label": self.label,
            "in": self.input,
            "out": self.output,
            "ms": self.ms,
            "notes": self.notes[:8],
        }


@dataclass(slots=True)
class PipelineResult:
    questions: list[writers.Candidate] = field(default_factory=list)
    psych_items: list[dict] = field(default_factory=list)
    interview_questions: list[dict] = field(default_factory=list)
    trace: list[Step] = field(default_factory=list)
    rejections: list[dict] = field(default_factory=list)
    summary: str = ""
    key_points: list[str] = field(default_factory=list)
    entities: dict[str, list[str]] = field(default_factory=dict)
    facts_found: int = 0
    candidates: int = 0
    duplicates: int = 0
    below_threshold: int = 0
    engine: str = "rules"
    duration_ms: int = 0
    error: str | None = None

    @property
    def accepted(self) -> int:
        return len(self.questions)

    @property
    def rejected(self) -> int:
        """Only items the critic actually refused -- surplus is not rejection."""
        return self.below_threshold

    @property
    def avg_quality(self) -> float | None:
        if not self.questions:
            return None
        return round(sum(c.quality for c in self.questions) / len(self.questions), 3)


def fingerprint_text(stem: str, answer: str) -> str:
    payload = _WS.sub(" ", _PUNCT.sub(" ", f"{stem} {answer}".lower())).strip()
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:40]


class _Timer:
    def __init__(self) -> None:
        self.start = time.perf_counter()

    def ms(self) -> int:
        return int((time.perf_counter() - self.start) * 1000)


def summarise(doc: nlp.Doc, top_facts: list[facts_agent.Fact], *, limit: int = 4) -> tuple[str, list[str]]:
    """Extractive summary: the highest-salience sentences, in original order.

    Abstractive summarisation needs a model. Extraction needs a ranking, which
    the fact agent has already computed -- so the summary costs nothing extra.
    """
    if not doc.sentences:
        return "", []

    ranked: dict[int, float] = {}
    for fact in top_facts:
        ranked[fact.index] = max(ranked.get(fact.index, 0.0), fact.salience)

    # A lead sentence is worth keeping even when it carried no extractable fact.
    ranked.setdefault(0, 0.7)

    chosen = sorted(ranked.items(), key=lambda kv: -kv[1])[:limit]
    order = sorted(index for index, _ in chosen)
    key_points = [doc.sentences[i] for i in order if i < len(doc.sentences)]
    summary = " ".join(key_points[:2])
    return summary[:1200], [point[:300] for point in key_points]


def _plan(config: dict) -> list[tuple[QuestionType, int]]:
    """How many of each written question type to aim for."""
    wanted = [
        (QuestionType.MCQ, int(config.get("mcq", 0) or 0)),
        (QuestionType.TRUE_FALSE, int(config.get("true_false", 0) or 0)),
        (QuestionType.FILL_BLANK, int(config.get("fill_blank", 0) or 0)),
        (QuestionType.SHORT_ANSWER, int(config.get("short_answer", 0) or 0)),
    ]
    return [(qtype, count) for qtype, count in wanted if count > 0]


def _write_candidates(
    plan: list[tuple[QuestionType, int]],
    ordered_facts: list[facts_agent.Fact],
    entities: dict[str, list[str]],
    rng: random.Random,
) -> tuple[list[writers.Candidate], list[str]]:
    """Draft up to 2.5x the requested count so the critic has room to reject."""
    candidates: list[writers.Candidate] = []
    notes: list[str] = []

    for qtype, wanted in plan:
        target = min(len(ordered_facts), max(wanted * 3, wanted + 2))
        produced = 0

        for fact in ordered_facts:
            if produced >= target:
                break

            if qtype is QuestionType.MCQ:
                candidate = writers.write_mcq(fact, entities, rng)
            elif qtype is QuestionType.TRUE_FALSE:
                candidate = writers.write_true_false(fact, entities, rng)
            elif qtype is QuestionType.FILL_BLANK:
                candidate = writers.write_fill_blank(fact, rng)
            else:
                candidate = writers.write_short_answer(fact)

            if candidate is not None:
                candidates.append(candidate)
                produced += 1

        if produced < wanted:
            notes.append(
                f"{qtype.value}: only {produced} draftable from {len(ordered_facts)} facts"
            )
    return candidates, notes


# At most this many accepted items may come from the same source sentence.
# Without it one quotable sentence yields an MCQ, a cloze, a true/false and a
# short answer, and a paper asks the same fact four times.
MAX_PER_SENTENCE = 2


def _select(
    candidates: list[writers.Candidate],
    plan: list[tuple[QuestionType, int]],
    min_quality: float,
    seen_fingerprints: set[str],
) -> tuple[list[writers.Candidate], list[dict], dict[str, int]]:
    """Judge, dedupe and fill each quota best-first."""
    rejections: list[dict] = []
    counts = {"below_threshold": 0, "duplicates": 0, "over_quota": 0, "same_sentence": 0}
    by_type: dict[QuestionType, list[writers.Candidate]] = {}

    for candidate in candidates:
        verdict = critic.judge(candidate)
        if verdict.score < min_quality:
            counts["below_threshold"] += 1
            if len(rejections) < 25:  # a sample is enough to tune thresholds
                rejections.append(
                    {
                        "stem": candidate.stem[:180],
                        "score": verdict.score,
                        "reasons": verdict.reasons[:3],
                        "template": candidate.template,
                    }
                )
            continue

        fingerprint = fingerprint_text(candidate.stem, candidate.answer_text or "".join(candidate.answer_keys))
        if fingerprint in seen_fingerprints:
            counts["duplicates"] += 1
            continue
        seen_fingerprints.add(fingerprint)
        by_type.setdefault(candidate.qtype, []).append(candidate)

    accepted: list[writers.Candidate] = []
    per_sentence: dict[str, int] = {}

    for qtype, wanted in plan:
        pool = sorted(by_type.get(qtype, []), key=lambda c: -c.quality)
        taken = 0
        for candidate in pool:
            if taken >= wanted:
                counts["over_quota"] += 1
                continue
            key = candidate.source_sentence[:120]
            if per_sentence.get(key, 0) >= MAX_PER_SENTENCE:
                counts["same_sentence"] += 1
                continue
            per_sentence[key] = per_sentence.get(key, 0) + 1
            accepted.append(candidate)
            taken += 1

    accepted.sort(key=lambda c: (-c.quality, c.stem))
    return accepted[: settings.AGENT_MAX_QUESTIONS], rejections, counts


def run(
    text: str,
    config: dict | None = None,
    *,
    known_fingerprints: set[str] | None = None,
    seed: str | None = None,
) -> PipelineResult:
    """Execute the full pipeline. Never raises: failures land in ``result.error``."""
    config = dict(config or {})
    result = PipelineResult(engine=nlp.backend_name())
    overall = _Timer()
    rng = random.Random(seed or (text[:200] if text else "issb"))
    seen = set(known_fingerprints or ())

    text = (text or "").strip()
    if len(text) < settings.AGENT_MIN_ARTICLE_CHARS:
        result.error = (
            f"Article is too short to generate from "
            f"({len(text)} chars, minimum {settings.AGENT_MIN_ARTICLE_CHARS})."
        )
        result.duration_ms = overall.ms()
        return result
    if len(text) > settings.AGENT_MAX_ARTICLE_CHARS:
        text = text[: settings.AGENT_MAX_ARTICLE_CHARS]
        result.trace.append(
            Step(agent="input", label="truncate", input=1, output=1, notes=["article truncated"])
        )

    try:
        # 1. Extract -----------------------------------------------------
        timer = _Timer()
        found, doc = facts_agent.extract(text)
        result.entities = doc.entities
        result.facts_found = len(found)
        note = nlp.backend_note()
        result.trace.append(
            Step(
                agent="extract",
                label=f"facts ({result.engine})",
                input=len(doc.sentences),
                output=len(found),
                ms=timer.ms(),
                notes=[note] if note else [],
            )
        )

        # 2. Summarise ---------------------------------------------------
        timer = _Timer()
        result.summary, result.key_points = summarise(doc, found)
        result.trace.append(
            Step(
                agent="summarise",
                label="key points",
                input=len(doc.sentences),
                output=len(result.key_points),
                ms=timer.ms(),
            )
        )

        if not found:
            result.error = "No extractable facts were found in this article."
            result.duration_ms = overall.ms()
            return result

        # 3. Write -------------------------------------------------------
        plan = _plan(config)
        timer = _Timer()
        drafted, notes = _write_candidates(plan, found, doc.entities, rng)
        result.candidates = len(drafted)
        result.trace.append(
            Step(
                agent="write",
                label="draft questions",
                input=len(found),
                output=len(drafted),
                ms=timer.ms(),
                notes=notes,
            )
        )

        # 4. Critique + dedupe + select ----------------------------------
        min_quality = float(config.get("min_quality") or settings.AGENT_MIN_QUALITY)
        timer = _Timer()
        accepted, rejections, counts = _select(drafted, plan, min_quality, seen)
        result.questions = accepted
        result.rejections = rejections
        result.duplicates = counts["duplicates"]
        result.below_threshold = counts["below_threshold"]
        result.trace.append(
            Step(
                agent="critique",
                label=f"quality >= {min_quality}",
                input=len(drafted),
                output=len(accepted),
                ms=timer.ms(),
                notes=[
                    f"{counts['below_threshold']} below threshold",
                    f"{counts['duplicates']} duplicate(s)",
                    f"{counts['same_sentence']} capped at {MAX_PER_SENTENCE}/sentence",
                    f"{counts['over_quota']} surplus beyond the requested counts",
                ],
            )
        )

        # 5. ISSB items --------------------------------------------------
        sct = int(config.get("sct", 0) or 0)
        srt = int(config.get("srt", 0) or 0)
        interview = int(config.get("interview", 0) or 0)
        if sct or srt or interview:
            timer = _Timer()
            wanted = max(8, sct + srt + interview)
            # Two lists: a person is a fine interview subject and a poor SCT stem.
            subjects = writers._topics_from(doc.entities, doc.noun_phrases, wanted)
            interview_topics = writers._topics_from(
                doc.entities, doc.noun_phrases, wanted, include_people=True
            )
            topics = subjects
            result.psych_items = [
                *writers.write_sct_items(subjects, sct, rng),
                *writers.write_srt_items(subjects, srt, rng),
            ]
            result.interview_questions = writers.write_interview_items(
                interview_topics, interview, rng
            )
            result.trace.append(
                Step(
                    agent="issb",
                    label="projective items",
                    input=len(topics),
                    output=len(result.psych_items) + len(result.interview_questions),
                    ms=timer.ms(),
                    notes=[] if topics else ["no usable topics found"],
                )
            )

        if config.get("difficulty"):
            wanted = Difficulty(str(config["difficulty"]))
            for candidate in result.questions:
                candidate.difficulty = wanted

    except Exception as exc:  # a generation failure must not take the request down
        result.error = f"{type(exc).__name__}: {exc}"

    result.duration_ms = overall.ms()
    return result
