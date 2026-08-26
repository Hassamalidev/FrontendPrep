"""Agent 1 of the pipeline: pull checkable facts out of an article.

A "fact" here is deliberately modest -- a sentence plus the span inside it that
could be asked about, and what kind of span it is. That is enough to write a
fill-in-the-blank, an MCQ or a true/false item, and it is achievable with
regular expressions and a part-of-speech-free heuristic, which is what the
no-API-key constraint leaves us.

Salience decides what gets asked. Sentences early in the article, containing a
number, a date or a named entity, and of a moderate length, score highest --
the same things a human question-setter reaches for first.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

from app.agents import nlp


class FactKind(StrEnum):
    NUMERIC = "numeric"        # a quantity, percentage or measurement
    DATE = "date"              # a year or calendar date
    ROLE = "role"              # X is the Y of Z
    DEFINITION = "definition"  # X is a Y
    ENTITY = "entity"          # a named actor in an event sentence
    EVENT = "event"            # subject-verb-object with no better handle


@dataclass(slots=True)
class Fact:
    kind: FactKind
    sentence: str
    answer: str              # the span a question would ask for
    subject: str = ""        # what the sentence is about
    relation: str = ""       # the connecting phrase, when one was matched
    salience: float = 0.0
    index: int = 0           # sentence position, 0 = first
    tags: list[str] = field(default_factory=list)

    @property
    def blanked(self) -> str:
        """The sentence with the answer replaced by a blank."""
        return replace_span(self.sentence, self.answer, "______")


_ROLE = re.compile(
    r"^(?P<subject>[A-Z][\w.'-]*(?:\s+[\w.'-]+){0,5}?)\s+"
    r"(?:is|was|has been|became|remains)\s+"
    r"(?:the|a|an)\s+"
    r"(?P<relation>[A-Za-z][\w-]*(?:\s+[\w-]+){0,4})\s+"
    r"(?P<prep>of|for|in|at)\s+"
    r"(?P<object>[A-Z][\w.'-]*(?:\s+[\w.'-]+){0,4})",
)

_DEFINITION = re.compile(
    r"^(?P<subject>[A-Z][\w.'-]*(?:\s+[\w.'-]+){0,4})\s+"
    r"(?:is|are|was|were)\s+(?:the|a|an)\s+"
    r"(?P<object>[a-z][\w-]*(?:\s+[\w-]+){0,6})",
)

_NUM = re.compile(
    r"\b\d[\d,]*(?:\.\d+)?\s?(?:%|percent|per cent|million|billion|trillion|crore|lakh|"
    r"km|kilometres|kilometers|miles|kg|tonnes|tons|MW|GW|metres|meters|feet|ft)\b",
    re.IGNORECASE,
)
# Plain counts ("38 sailors", "30 days"). Kept apart from _NUM because that
# unit list is unambiguous, while this one needs a plural noun to avoid firing
# on every stray digit.
_COUNT = re.compile(
    r"\b\d[\d,]*\s+(?:days?|weeks?|months?|years?|hours?|minutes?|sailors?|soldiers?|"
    r"officers?|cadets?|personnel|troops?|aircraft|ships?|submarines?|tanks?|seats?|"
    r"votes?|medals?|points?|marks?|candidates?|students?|districts?|countries|nations?|"
    r"members?|units?|squadrons?|regiments?|battalions?)\b",
    re.IGNORECASE,
)
_YEAR = re.compile(r"\b(?:1[5-9]\d{2}|20\d{2})\b")
_FULL_DATE = re.compile(
    r"\b(?:\d{1,2}\s+)?(?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December)(?:\s+\d{1,2})?(?:,?\s+\d{4})?\b"
)
_PROPER = re.compile(r"\b(?:[A-Z][a-z]{2,}|[A-Z]{2,})(?:\s+(?:[A-Z][a-z]{2,}|[A-Z]{2,})){0,3}\b")


def replace_span(sentence: str, span: str, replacement: str) -> str:
    """Replace the first whole-word occurrence of ``span``."""
    if not span:
        return sentence
    pattern = re.compile(rf"(?<!\w){re.escape(span)}(?!\w)")
    replaced, count = pattern.subn(replacement, sentence, count=1)
    return replaced if count else sentence.replace(span, replacement, 1)


_LEAD_STOPWORDS = ("however", "moreover", "meanwhile", "also", "in addition", "furthermore")


def _clean(sentence: str) -> str:
    text = " ".join(sentence.split())
    lowered = text.lower()
    for lead in _LEAD_STOPWORDS:
        if lowered.startswith(lead):
            text = text[len(lead) :].lstrip(" ,")
            break
    return text


def _salience(sentence: str, index: int, total: int, kind: FactKind) -> float:
    """How worth asking about this sentence is, in 0..1."""
    words = len(sentence.split())

    # Position: the lead carries the article. Decay, but never to zero.
    position = 1.0 - (index / max(total, 1)) * 0.55

    # Length: 12-30 words is the sweet spot for a self-contained question.
    if words < 8:
        length = 0.35
    elif words <= 30:
        length = 1.0
    elif words <= 45:
        length = 0.7
    else:
        length = 0.35

    kind_weight = {
        FactKind.NUMERIC: 1.0,
        FactKind.DATE: 0.95,
        FactKind.ROLE: 0.95,
        FactKind.DEFINITION: 0.8,
        FactKind.ENTITY: 0.75,
        FactKind.EVENT: 0.55,
    }[kind]

    # A sentence that opens with a pronoun depends on the previous one, so it
    # cannot stand alone as a question stem.
    standalone = 0.45 if re.match(r"^(he|she|it|they|this|that|these|those)\b", sentence, re.I) else 1.0

    return round(min(1.0, position * 0.35 + length * 0.25 + kind_weight * 0.4) * standalone, 3)


def _first(pattern: re.Pattern[str], sentence: str) -> str | None:
    match = pattern.search(sentence)
    return match.group(0).strip() if match else None


def extract(text: str, *, limit: int = 60) -> tuple[list[Fact], nlp.Doc]:
    """Return salient facts, highest first, plus the parsed document."""
    doc = nlp.analyse(text)
    sentences = doc.sentences
    total = len(sentences)
    facts: list[Fact] = []

    for index, raw in enumerate(sentences):
        sentence = _clean(raw)
        if len(sentence.split()) < 6:
            continue

        found_here: list[Fact] = []

        # 1. Quantities -- the most reliably checkable thing in any article.
        quantity = _first(_NUM, sentence) or _first(_COUNT, sentence)
        if quantity:
            found_here.append(
                Fact(kind=FactKind.NUMERIC, sentence=sentence, answer=quantity, index=index)
            )

        # 2. Dates.
        date_span = _first(_FULL_DATE, sentence) or _first(_YEAR, sentence)
        if date_span and date_span != quantity:
            found_here.append(
                Fact(kind=FactKind.DATE, sentence=sentence, answer=date_span, index=index)
            )

        # 3. "X is the chief of Y" -- the best MCQ source in the set.
        role = _ROLE.match(sentence)
        if role:
            found_here.append(
                Fact(
                    kind=FactKind.ROLE,
                    sentence=sentence,
                    answer=role.group("subject").strip(),
                    subject=role.group("subject").strip(),
                    relation=(
                        # Keep the preposition the source used: rewriting
                        # "Commission for Human Development" as "... of ..."
                        # quietly changes the name of the organisation.
                        f"{role.group('relation').strip(' .,')} {role.group('prep')} "
                        f"{role.group('object').strip(' .,')}"
                    ),
                    index=index,
                )
            )
        else:
            definition = _DEFINITION.match(sentence)
            if definition:
                found_here.append(
                    Fact(
                        kind=FactKind.DEFINITION,
                        sentence=sentence,
                        answer=definition.group("subject").strip(),
                        subject=definition.group("subject").strip(),
                        relation=definition.group("object").strip(" .,"),
                        index=index,
                    )
                )

        # 4. Named actors, when nothing sharper was found.
        if not found_here:
            for match in _PROPER.finditer(sentence):
                candidate = match.group(0).strip()
                if match.start() == 0 and len(candidate.split()) == 1:
                    continue  # the capitalised first word is not evidence
                if candidate.lower() in nlp.STOP_WORDS or len(candidate) < 4:
                    continue
                found_here.append(
                    Fact(kind=FactKind.ENTITY, sentence=sentence, answer=candidate, index=index)
                )
                break

        for fact in found_here:
            fact.salience = _salience(sentence, index, total, fact.kind)
            facts.append(fact)

    facts.sort(key=lambda f: (-f.salience, f.index))
    return facts[:limit], doc
