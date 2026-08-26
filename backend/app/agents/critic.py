"""Agent 4: judge candidates and throw most of them away.

Generation is cheap; the value is in rejection. Every check here encodes a way
a template-written question goes wrong in practice:

* the answer is visible in the stem (cloze over a repeated phrase),
* the correct option is conspicuously the longest or the only specific one,
* two options mean the same thing, so there is no single right answer,
* the stem needs the previous sentence to make sense ("It rose by 5%"),
* the blank could be filled by more than one option.

Each check returns a 0..1 sub-score; the weighted mean is the quality score the
super admin sees, and anything below ``AGENT_MIN_QUALITY`` never reaches the
review queue.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.agents.writers import Candidate
from app.core.enums import QuestionType

_LEADING_PRONOUN = re.compile(r"^(?:he|she|it|they|them|this|that|these|those|there)\b", re.I)
_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'-]*")

# Weights sum to 1.0; ordering here is the order shown in the trace.
WEIGHTS = {
    "answerable": 0.24,
    "no_leak": 0.20,
    "options": 0.20,
    "self_contained": 0.22,
    "readability": 0.14,
}

# Some faults are not "lower quality", they are "not a question". A stem that
# opens with a pronoun, or whose answer is printed inside it, cannot be rescued
# by scoring well elsewhere -- on weights alone a 0.2 on one check still clears
# a 0.55 threshold. These floors reject outright.
VETO_BELOW = {
    "answerable": 0.4,
    "no_leak": 0.3,
    "options": 0.4,
    "self_contained": 0.4,
}


@dataclass(slots=True)
class Verdict:
    score: float
    breakdown: dict[str, float]
    reasons: list[str]

    @property
    def accepted_at(self) -> float:
        return self.score


def _words(text: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(text)]


# Titles that name a post rather than a person. "The Chairman is the head of X"
# parses as a role fact, but "Who is the head of X? -> The Chairman" is circular.
GENERIC_ANSWERS = frozenset(
    """
    chairman chairperson president director head chief secretary minister spokesman spokesperson
    government ministry committee commission board authority council court official officer
    department agency organisation organization company management team group member public
    """.split()
)


def _answerable(candidate: Candidate) -> tuple[float, str | None]:
    stem_words = len(candidate.stem.split())

    answer = (candidate.answer_text or " ".join(candidate.answer_keys)).strip()
    bare = answer[4:] if answer.lower().startswith("the ") else answer
    if bare.lower() in GENERIC_ANSWERS:
        return 0.2, f"the answer is a generic title ({answer})"

    if candidate.qtype is QuestionType.TRUE_FALSE:
        if stem_words < 8:
            return 0.3, "statement too short to judge"
        return (1.0, None) if stem_words <= 45 else (0.6, "statement is long for true/false")

    has_blank = "______" in candidate.stem
    is_question = candidate.stem.rstrip().endswith("?")
    if not has_blank and not is_question:
        return 0.2, "stem is neither a question nor a cloze"
    if stem_words < 7:
        return 0.35, "stem too short to be answerable"
    if stem_words > 55:
        return 0.5, "stem is very long"
    return 1.0, None


def _no_leak(candidate: Candidate) -> tuple[float, str | None]:
    """The correct answer must not appear in the stem."""
    answer = candidate.answer_text if candidate.options else " ".join(candidate.answer_keys)
    if not answer:
        return 1.0, None

    stem_lower = candidate.stem.lower()
    answer_lower = answer.lower().strip()

    if candidate.qtype is QuestionType.TRUE_FALSE:
        return 1.0, None
    if answer_lower and answer_lower in stem_lower:
        return 0.0, "the answer appears in the stem"

    # Partial leak: most of the answer's content words already in the stem.
    answer_words = [w for w in _words(answer) if len(w) > 3]
    if answer_words:
        overlap = sum(1 for w in answer_words if w in stem_lower) / len(answer_words)
        if overlap >= 0.8:
            return 0.25, "the answer is largely present in the stem"
        if overlap >= 0.5:
            return 0.6, "part of the answer appears in the stem"
    return 1.0, None


def _options(candidate: Candidate) -> tuple[float, str | None]:
    if candidate.qtype in {QuestionType.FILL_BLANK, QuestionType.SHORT_ANSWER}:
        answer = " ".join(candidate.answer_keys).strip()
        if not answer:
            return 0.0, "no answer recorded"
        if len(answer.split()) > 6:
            return 0.5, "free-text answer is long enough to be marked inconsistently"
        return 1.0, None

    texts = [str(o.get("text", "")).strip() for o in candidate.options]
    if len(texts) < 2:
        return 0.0, "fewer than two options"
    if any(not t for t in texts):
        return 0.0, "an option is empty"

    lowered = [t.lower() for t in texts]
    if len(set(lowered)) != len(lowered):
        return 0.0, "duplicate options"

    if candidate.qtype is QuestionType.TRUE_FALSE:
        return 1.0, None

    score = 1.0
    reason: str | None = None

    # One option containing another is usually two shades of the same answer.
    for i, a in enumerate(lowered):
        for j, b in enumerate(lowered):
            if i != j and len(a) > 3 and a in b:
                score = min(score, 0.45)
                reason = "one option contains another"

    # Length cue: candidates learn to pick the longest option.
    answer_key = candidate.answer_keys[0] if candidate.answer_keys else None
    by_key = {o.get("key"): str(o.get("text", "")) for o in candidate.options}
    answer_text = by_key.get(answer_key, "")
    if answer_text and len(texts) > 2:
        lengths = [len(t) for t in texts]
        longest = max(lengths)
        if len(answer_text) == longest and longest > min(lengths) * 1.6:
            score = min(score, 0.55)
            reason = reason or "the correct option is conspicuously the longest"

    # Mixed types (a year against a name) makes the odd one out obvious.
    numeric_flags = [bool(re.fullmatch(r"[^A-Za-z]*\d[\d,.\s%A-Za-z]*", t)) for t in texts]
    if len(set(numeric_flags)) > 1:
        score = min(score, 0.5)
        reason = reason or "options mix numbers with names"

    return score, reason


def _self_contained(candidate: Candidate) -> tuple[float, str | None]:
    """A stem that depends on the previous sentence cannot be asked alone."""
    body = candidate.stem
    for lead_in in ("Complete the statement with the correct figure:",
                    "Complete the statement with the correct date:",
                    "Complete the statement:",
                    "Fill in the blank:",
                    "True or false:"):
        if body.startswith(lead_in):
            body = body[len(lead_in):].strip()
            break

    if _LEADING_PRONOUN.match(body):
        return 0.2, "stem opens with a pronoun and needs the previous sentence"
    if body.startswith("______"):
        return 0.55, "the blank is the first thing in the sentence"
    if re.search(r"\b(?:the (?:above|following|latter|former)|as mentioned|above[- ]mentioned)\b", body, re.I):
        return 0.3, "stem refers to text the student cannot see"
    return 1.0, None


def _readability(candidate: Candidate) -> tuple[float, str | None]:
    text = candidate.stem
    words = text.split()
    if not words:
        return 0.0, "empty stem"

    score = 1.0
    reason: str | None = None

    if text.count("______") > 1:
        score = min(score, 0.4)
        reason = "more than one blank"
    if len([w for w in words if len(w) > 14]) > 2:
        score = min(score, 0.7)
        reason = reason or "several very long words"
    if text.count(",") > 5:
        score = min(score, 0.7)
        reason = reason or "heavily sub-claused sentence"
    if re.search(r"\bhttps?://", text):
        score = min(score, 0.3)
        reason = reason or "stem contains a URL"
    if re.search(r"[\"\u201c\u201d]", text) and candidate.qtype is not QuestionType.TRUE_FALSE:
        score = min(score, 0.85)
        reason = reason or "quoted speech in the stem"
    return score, reason


CHECKS = {
    "answerable": _answerable,
    "no_leak": _no_leak,
    "options": _options,
    "self_contained": _self_contained,
    "readability": _readability,
}


def judge(candidate: Candidate) -> Verdict:
    breakdown: dict[str, float] = {}
    reasons: list[str] = []

    for name, check in CHECKS.items():
        score, reason = check(candidate)
        breakdown[name] = round(score, 3)
        if reason:
            reasons.append(f"{name}: {reason}")

    vetoed = [name for name, floor in VETO_BELOW.items() if breakdown[name] < floor]
    if vetoed:
        reasons.insert(0, f"vetoed by {', '.join(vetoed)}")
        total = 0.0
    else:
        total = sum(breakdown[name] * weight for name, weight in WEIGHTS.items())
        # Salience is a tie-breaker, not a gate: a well-formed question about a
        # minor sentence is still a usable question.
        total = total * 0.9 + candidate.salience * 0.1

    verdict = Verdict(score=round(min(1.0, total), 3), breakdown=breakdown, reasons=reasons)
    candidate.quality = verdict.score
    candidate.critique = {"breakdown": breakdown, "reasons": reasons}
    return verdict
