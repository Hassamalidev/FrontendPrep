"""Optional NLP backend with a pure-Python fallback.

The platform must run with **no LLM API key and no mandatory model download**.
So every linguistic operation the pipeline needs is defined twice: once against
spaCy when it happens to be installed, and once in plain Python.

``analyse(text)`` returns the same ``Doc`` shape either way, so nothing
downstream needs to know which backend answered. Import is attempted once and
cached; a missing spaCy is a normal, expected state rather than an error.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from app.core.config import settings

# --- Backend detection -----------------------------------------------------

_SPACY_ERROR: str | None = None


@lru_cache(maxsize=1)
def _load_spacy() -> Any | None:
    """Return a loaded spaCy pipeline, or None if unavailable."""
    global _SPACY_ERROR

    if not settings.AGENT_USE_NLP:
        _SPACY_ERROR = "disabled by AGENT_USE_NLP"
        return None
    try:
        import spacy  # noqa: PLC0415 -- optional dependency, imported lazily
    except ImportError:
        _SPACY_ERROR = "spacy is not installed"
        return None

    for model in ("en_core_web_sm", "en_core_web_md"):
        try:
            return spacy.load(model, disable=["lemmatizer"])
        except Exception:  # model not downloaded
            continue

    try:  # last resort: a blank pipeline still gives a decent sentencizer
        blank = spacy.blank("en")
        blank.add_pipe("sentencizer")
        _SPACY_ERROR = "no trained model; using blank English pipeline"
        return blank
    except Exception as exc:
        _SPACY_ERROR = f"spacy unusable: {exc}"
        return None


def backend_name() -> str:
    return "spacy" if _load_spacy() is not None else "rules"


def backend_note() -> str | None:
    _load_spacy()
    return _SPACY_ERROR


# --- Shared document shape -------------------------------------------------


@dataclass(slots=True)
class Token:
    text: str
    lower: str
    is_stop: bool = False
    is_alpha: bool = True
    pos: str = ""


@dataclass(slots=True)
class Doc:
    text: str
    sentences: list[str] = field(default_factory=list)
    tokens: list[Token] = field(default_factory=list)
    # {"PERSON": [...], "ORG": [...], "GPE": [...], "DATE": [...], "NUM": [...]}
    entities: dict[str, list[str]] = field(default_factory=dict)
    noun_phrases: list[str] = field(default_factory=list)
    backend: str = "rules"

    @property
    def content_words(self) -> list[str]:
        return [t.lower for t in self.tokens if t.is_alpha and not t.is_stop and len(t.text) > 2]


# --- Rule-based fallback ---------------------------------------------------

STOP_WORDS: frozenset[str] = frozenset(
    """
    a about above after again against all am an and any are as at be because been before being
    below between both but by can cannot could did do does doing down during each few for from
    further had has have having he her here hers herself him himself his how i if in into is it
    its itself me more most my myself no nor not of off on once only or other ought our ours
    ourselves out over own same she should so some such than that the their theirs them themselves
    then there these they this those through to too under until up very was we were what when
    where which while who whom why will with would you your yours yourself yourselves also may
    might must shall upon among within without said says say new one two three first second
    """.split()
)

# Sentence boundary that tolerates common abbreviations and initials.
_ABBREV = r"(?<!\b[A-Z])(?<!\bMr)(?<!\bMrs)(?<!\bDr)(?<!\bNo)(?<!\bSgt)(?<!\bLt)(?<!\bGen)(?<!\bCol)"
_SENT_SPLIT = re.compile(rf"{_ABBREV}(?<=[.!?])[\"')\]]*\s+(?=[A-Z0-9])")
_WORD = re.compile(r"[A-Za-z][A-Za-z'-]*|\d[\d,.]*")

_TITLES = (
    r"(?:Mr|Mrs|Ms|Dr|Prof|Gen|General|Lt|Lieutenant|Col|Colonel|Maj|Major|Capt|Captain|Sgt|"
    r"Brig|Brigadier|Commodore|Vice Admiral|Rear Admiral|Air Chief Marshal|Air Marshal|"
    r"Air Vice Marshal|Wing Commander|Group Captain|Squadron Leader|Admiral|President|"
    r"Prime Minister|PM|Chief|Justice|Senator|Minister)"
)
_PERSON = re.compile(rf"\b{_TITLES}\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){{0,2}})")
_PROPER_RUN = re.compile(r"\b(?:[A-Z][a-z]{2,}|[A-Z]{2,})(?:\s+(?:of|the|and|for)?\s*(?:[A-Z][a-z]{2,}|[A-Z]{2,}))*\b")
_DATE = re.compile(
    r"\b(?:\d{1,2}\s+)?(?:January|February|March|April|May|June|July|August|September|October|"
    r"November|December)(?:\s+\d{1,2})?(?:,?\s+\d{4})?\b|\b(?:19|20)\d{2}\b"
)
_NUMBER = re.compile(r"\b\d[\d,]*(?:\.\d+)?\s?(?:%|percent|million|billion|crore|lakh|km|kg|MW|GW)?\b")

_MONTH_NAMES = frozenset(
    """
    january february march april may june july august september october november december
    jan feb mar apr jun jul aug sep sept oct nov dec monday tuesday wednesday thursday
    friday saturday sunday
    """.split()
)

_ORG_HINTS = (
    "ministry", "army", "navy", "air force", "commission", "authority", "board", "united",
    "organisation", "organization", "council", "bank", "university", "academy", "corps",
    "government", "assembly", "senate", "court", "agency", "force", "command", "institute",
)


def split_sentences(text: str) -> list[str]:
    parts = [s.strip() for s in _SENT_SPLIT.split(text.replace("\r", "")) if s.strip()]
    out: list[str] = []
    for part in parts:
        # Paragraph breaks are sentence breaks too when punctuation is missing.
        out.extend(chunk.strip() for chunk in part.split("\n\n") if chunk.strip())
    return [s for s in out if len(s.split()) >= 3]


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    for match in _WORD.finditer(text):
        word = match.group(0)
        lower = word.lower()
        tokens.append(
            Token(
                text=word,
                lower=lower,
                is_stop=lower in STOP_WORDS,
                is_alpha=word[0].isalpha(),
            )
        )
    return tokens


def _rule_entities(text: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}

    def add(label: str, value: str) -> None:
        # Article text arrives hard-wrapped; a span caught across a line break
        # would otherwise become an option with a newline inside it.
        value = " ".join(value.split()).strip(" ,.;:")
        if len(value) < 3:
            return
        bucket = found.setdefault(label, [])
        if value not in bucket and len(bucket) < 25:
            bucket.append(value)

    for match in _PERSON.finditer(text):
        add("PERSON", match.group(0))   # "Admiral Naveed Ashraf"
        add("PERSON", match.group(1))   # "Naveed Ashraf"
    for match in _DATE.finditer(text):
        add("DATE", match.group(0))
    for match in _NUMBER.finditer(text):
        value = match.group(0).strip()
        if any(ch.isdigit() for ch in value) and len(value) > 1:
            add("NUM", value)

    for match in _PROPER_RUN.finditer(text):
        phrase = match.group(0).strip()
        if phrase.lower() in STOP_WORDS or len(phrase) < 4:
            continue
        # A bare month is a date, and it is already captured as one. Left in
        # PROPER it became a "topic" downstream, producing SRT items like
        # "During a discussion on July...".
        if phrase.lower() in _MONTH_NAMES:
            continue
        label = "ORG" if any(h in phrase.lower() for h in _ORG_HINTS) else "PROPER"
        add(label, phrase)

    return found


def _rule_noun_phrases(sentences: list[str]) -> list[str]:
    """Approximate noun chunks: runs of capitalised or non-stop words."""
    phrases: list[str] = []
    for sentence in sentences:
        run: list[str] = []
        for token in tokenize(sentence):
            if token.is_alpha and not token.is_stop and len(token.text) > 2:
                run.append(token.text)
            else:
                if 1 <= len(run) <= 4:
                    phrases.append(" ".join(run))
                run = []
        if 1 <= len(run) <= 4:
            phrases.append(" ".join(run))

    seen: set[str] = set()
    unique: list[str] = []
    for phrase in phrases:
        key = phrase.lower()
        if key not in seen:
            seen.add(key)
            unique.append(phrase)
    return unique[:60]


def _rule_doc(text: str) -> Doc:
    sentences = split_sentences(text)
    return Doc(
        text=text,
        sentences=sentences,
        tokens=tokenize(text),
        entities=_rule_entities(text),
        noun_phrases=_rule_noun_phrases(sentences),
        backend="rules",
    )


# --- spaCy path ------------------------------------------------------------

_SPACY_LABELS = {
    "PERSON": "PERSON",
    "ORG": "ORG",
    "GPE": "GPE",
    "LOC": "GPE",
    "NORP": "ORG",
    "DATE": "DATE",
    "EVENT": "EVENT",
    "CARDINAL": "NUM",
    "QUANTITY": "NUM",
    "PERCENT": "NUM",
    "MONEY": "NUM",
    "FAC": "ORG",
}


def _spacy_doc(text: str, pipeline: Any) -> Doc:
    parsed = pipeline(text)

    entities: dict[str, list[str]] = {}
    for ent in getattr(parsed, "ents", []):
        label = _SPACY_LABELS.get(ent.label_)
        if not label:
            continue
        bucket = entities.setdefault(label, [])
        value = " ".join(ent.text.split()).strip()
        if value and value not in bucket and len(bucket) < 25:
            bucket.append(value)

    tokens = [
        Token(
            text=t.text,
            lower=t.lower_,
            is_stop=bool(t.is_stop) or t.lower_ in STOP_WORDS,
            is_alpha=bool(t.is_alpha),
            pos=getattr(t, "pos_", ""),
        )
        for t in parsed
        if not t.is_space and not t.is_punct
    ]

    sentences = [s.text.strip() for s in parsed.sents] if parsed.has_annotation("SENT_START") else []
    if not sentences:
        sentences = split_sentences(text)

    try:
        noun_phrases = [c.text.strip() for c in parsed.noun_chunks][:60]
    except (NotImplementedError, ValueError):  # blank pipeline has no parser
        noun_phrases = _rule_noun_phrases(sentences)

    doc = Doc(
        text=text,
        sentences=[s for s in sentences if len(s.split()) >= 3],
        tokens=tokens,
        entities=entities,
        noun_phrases=noun_phrases,
        backend="spacy",
    )
    # spaCy misses plain numeric facts the question writer leans on; the regex
    # pass is cheap and additive, so run it either way.
    for label, values in _rule_entities(text).items():
        if label in {"NUM", "DATE"}:
            bucket = doc.entities.setdefault(label, [])
            for value in values:
                if value not in bucket and len(bucket) < 25:
                    bucket.append(value)
    return doc


def analyse(text: str) -> Doc:
    """Parse ``text`` with whichever backend is available."""
    text = (text or "").strip()
    if not text:
        return Doc(text="", backend=backend_name())

    pipeline = _load_spacy()
    if pipeline is None:
        return _rule_doc(text)
    try:
        return _spacy_doc(text, pipeline)
    except Exception:
        # A model failure must degrade to rules, never take the request down.
        return _rule_doc(text)
