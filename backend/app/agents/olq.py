"""Heuristic Officer Like Quality analyser for the projective tests.

WAT, SCT, SRT, TAT, GTO plans and interview answers have no answer key, so this
module does what a psychologist does mechanically: it measures observable
properties of the writing -- how much was attempted, how fast, how positive,
how decisive, whether the candidate acts or merely observes, whether other
people appear in the response -- and maps those signals onto the fifteen OLQs.

It is explicitly **not** a personality verdict, and the wording of the feedback
says so. What it can honestly do is show a candidate the difference between
"I would think about the problem" and "I informed the JCO, split the party in
two and cleared the route by 0900" -- which is most of what WAT/SRT coaching is.

No model, no API key: lexicons plus counting.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.enums import OLQ, OLQ_LABELS, PsychTestType

_WORD = re.compile(r"[A-Za-z][A-Za-z'-]*")

# --- Lexicons --------------------------------------------------------------
# Small and hand-picked. Every term is one a Pakistani candidate plausibly
# writes in a WAT/SRT answer; that matters more than raw vocabulary size.

POSITIVE = frozenset("""
    able achieve achieved accomplish advance ambition appreciate best better brave calm capable
    care cheerful clear complete confident cooperate courage courageous dedicate determined
    devotion discipline duty eager earn effective efficient effort encourage energy enjoy
    excellent fair faith focus friend generous glad good grateful hard-work help helped helpful
    honest honour hope improve improved inspire integrity joy keen kind lead leader learn
    loyal manage motivate optimistic organise organize patriotic peace persevere plan positive
    practice prepare progress proud punctual ready resolve respect responsible sacrifice safe
    satisfy secure serve service sincere skill smart solve strength strong succeed success
    support sure sympathy team teamwork thorough tolerant trust truth useful valour victory
    welcome willing win wise work
""".split())

NEGATIVE = frozenset("""
    afraid angry anxious avoid bad blame bored careless cheat confuse coward cry danger defeat
    delay depress despair difficult disappoint dishonest doubt dull escape fail failure fear
    fight foolish forget frustrate give-up guilty hate helpless hopeless idle ignore impossible
    incapable inferior insult lazy leave lie lonely lose loss mistake nervous never nothing
    panic poor problem quarrel quit refuse regret reject revenge rude sad scared selfish shame
    sorry stop stress stupid suffer tension tired trouble unable unfair unhappy useless waste
    weak worry worthless wrong
""".split())

DECISIVE = frozenset("""
    at-once decide decided decision definitely determined finalise finalize first immediately
    instantly must now once promptly quickly rapidly right-away straight swiftly then without-delay
""".split())

HEDGING = frozenset("""
    maybe perhaps possibly probably sometimes somewhat might could would-be seems appears
    hopefully try attempt guess suppose think-about consider maybe-later if-possible
""".split())

ACTION_VERBS = frozenset("""
    act adapt address alert allocate analyse analyze arrange assign assist attack brief build
    calculate call carry check clear climb collect command communicate complete conduct
    construct
    contact control coordinate cover create cross deal defend deliver deploy detect direct
    dispatch distribute divide do drive establish evacuate execute finish fix form gather guide
    handle help implement inform initiate inspect install instruct join jump lead lift line-up
    maintain make manage march mobilise mobilize monitor move negotiate observe obtain operate
    organise organize perform persuade pick plan position prepare present prevent proceed
    protect provide pull push reach rebuild reconnoitre record recover reduce regroup rehearse
    remove repair report rescue reserve resolve respond restore retrieve rush save search
    secure select send set settle shift signal solve sort start supervise supply support
    survey take tackle teach tell train transport treat verify visit warn
""".split())

SOCIAL = frozenset("""
    all brother colleague comrade company crew everyone family friend group he her him his
    house-mate juniors leader mate member neighbour others our parents partner people platoon
    section seniors she society soldier squad staff student subordinate team teammate their
    them they together troop unit us villagers we jco jcos nco ncos men boys girls party
    batch candidates crowd public victim patient injured passengers driver guard officer
""".split())

SELF = frozenset("i me my mine myself".split())

RESPONSIBILITY = frozenset("""
    accountable answerable charge commitment duty entrust guarantee obligation oversee own
    promise reliable responsibility responsible trustworthy undertake
""".split())

PLANNING = frozenset("""
    allocate approach arrange budget chart deadline divide estimate first method next order
    phase plan practical prepare priority procedure resource route schedule sequence step
    strategy systematic time-table timeline
""".split())

COURAGE = frozenset("""
    bold brave courage dare daring danger defend fearless fight firm front hazard heroic
    protect resist risk rescue sacrifice stand struggle valiant valour
""".split())

STAMINA = frozenset("""
    again continue endurance energy exercise fit fitness health hard keep last long marathon
    persist practice regular repeat run stamina strength strong sustain train tireless walk
""".split())

INFLUENCE = frozenset("""
    advise brief convince encourage explain guide inspire instruct lead motivate persuade
    rally suggest teach urge
""".split())

_MULTIWORD = {
    "at once": "at-once",
    "right away": "right-away",
    "without delay": "without-delay",
    "give up": "give-up",
    "hard work": "hard-work",
    "line up": "line-up",
    "think about": "think-about",
    "if possible": "if-possible",
    "would be": "would-be",
    "time table": "time-table",
}


def _words(text: str) -> list[str]:
    lowered = text.lower()
    for phrase, joined in _MULTIWORD.items():
        lowered = lowered.replace(phrase, joined)
    return _WORD.findall(lowered)


@dataclass(slots=True)
class Signals:
    """Observable properties of one batch of written responses."""

    responses: int = 0
    answered: int = 0
    words: int = 0
    avg_words: float = 0.0
    avg_seconds: float = 0.0
    positivity: float = 0.0        # positive share of sentiment-bearing words
    negativity: float = 0.0
    decisiveness: float = 0.0
    hedging: float = 0.0
    action_rate: float = 0.0       # action verbs per response
    social_rate: float = 0.0       # references to other people per response
    self_rate: float = 0.0
    responsibility: float = 0.0
    planning: float = 0.0
    courage: float = 0.0
    stamina: float = 0.0
    influence: float = 0.0
    completion: float = 0.0        # share of items attempted
    speed: float = 0.0             # 1.0 = comfortably inside the time limit

    def as_dict(self) -> dict[str, float]:
        return {
            "responses": self.responses,
            "answered": self.answered,
            "words": self.words,
            "avg_words": round(self.avg_words, 2),
            "avg_seconds": round(self.avg_seconds, 2),
            "completion": round(self.completion, 3),
            "positivity": round(self.positivity, 3),
            "negativity": round(self.negativity, 3),
            "decisiveness": round(self.decisiveness, 3),
            "hedging": round(self.hedging, 3),
            "action_rate": round(self.action_rate, 3),
            "social_rate": round(self.social_rate, 3),
            "self_rate": round(self.self_rate, 3),
            "responsibility": round(self.responsibility, 3),
            "planning": round(self.planning, 3),
            "courage": round(self.courage, 3),
            "stamina": round(self.stamina, 3),
            "influence": round(self.influence, 3),
            "speed": round(self.speed, 3),
        }


@dataclass(slots=True)
class Response:
    text: str = ""
    ms: int = 0
    seconds_allowed: int = 30
    skipped: bool = False
    notes: list[str] = field(default_factory=list)


def _variants(word: str) -> tuple[str, ...]:
    """Cheap inflection stripping so ``organised`` matches ``organise``.

    A real stemmer (or spaCy lemmas) would be better, but this has to work with
    zero optional dependencies installed, and lexicon matching is forgiving:
    over-generating candidates costs nothing because only real entries hit.
    """
    forms = [word]
    if len(word) > 4:
        if word.endswith("ies"):
            forms += [word[:-3] + "y"]
        elif word.endswith("ied"):
            forms += [word[:-3] + "y", word[:-3] + "ie"]
        elif word.endswith("ing"):
            stem = word[:-3]
            forms += [stem, stem + "e"]
            if len(stem) > 2 and stem[-1] == stem[-2]:
                forms.append(stem[:-1])
        elif word.endswith("ed"):
            stem = word[:-2]
            forms += [stem, stem + "e", word[:-1]]
            if len(stem) > 2 and stem[-1] == stem[-2]:
                forms.append(stem[:-1])
        elif word.endswith("es"):
            forms += [word[:-2], word[:-1]]
        elif word.endswith("s"):
            forms += [word[:-1]]
    return tuple(dict.fromkeys(forms))


def _hits(words: list[str], lexicon: frozenset[str]) -> int:
    return sum(1 for w in words if any(form in lexicon for form in _variants(w)))


def measure(responses: list[Response]) -> Signals:
    """Turn raw responses into normalised signals in 0..1 (mostly)."""
    total = len(responses)
    answered = [r for r in responses if r.text.strip() and not r.skipped]
    sig = Signals(responses=total, answered=len(answered))
    if not answered:
        return sig

    all_words: list[str] = []
    per_response_counts: list[dict[str, int]] = []
    seconds_used: list[float] = []
    speed_ratios: list[float] = []

    for response in answered:
        words = _words(response.text)
        all_words.extend(words)
        per_response_counts.append(
            {
                "action": _hits(words, ACTION_VERBS),
                "social": _hits(words, SOCIAL),
                "self": _hits(words, SELF),
                "responsibility": _hits(words, RESPONSIBILITY),
                "planning": _hits(words, PLANNING),
                "courage": _hits(words, COURAGE),
                "stamina": _hits(words, STAMINA),
                "influence": _hits(words, INFLUENCE),
                "decisive": _hits(words, DECISIVE),
                "hedge": _hits(words, HEDGING),
            }
        )
        used = response.ms / 1000 if response.ms else 0.0
        if used:
            seconds_used.append(used)
            if response.seconds_allowed:
                speed_ratios.append(min(2.0, used / response.seconds_allowed))

    n = len(answered)
    sig.words = len(all_words)
    sig.avg_words = sig.words / n
    sig.avg_seconds = sum(seconds_used) / len(seconds_used) if seconds_used else 0.0
    sig.completion = n / total if total else 0.0

    positive = _hits(all_words, POSITIVE)
    negative = _hits(all_words, NEGATIVE)
    sentiment_total = positive + negative
    sig.positivity = positive / sentiment_total if sentiment_total else 0.5
    sig.negativity = negative / sentiment_total if sentiment_total else 0.5

    def rate(key: str) -> float:
        return sum(c[key] for c in per_response_counts) / n

    sig.action_rate = rate("action")
    sig.social_rate = rate("social")
    sig.self_rate = rate("self")
    sig.responsibility = rate("responsibility")
    sig.planning = rate("planning")
    sig.courage = rate("courage")
    sig.stamina = rate("stamina")
    sig.influence = rate("influence")

    decisive = sum(c["decisive"] for c in per_response_counts)
    hedge = sum(c["hedge"] for c in per_response_counts)
    marker_total = decisive + hedge
    sig.decisiveness = decisive / marker_total if marker_total else 0.5
    sig.hedging = hedge / marker_total if marker_total else 0.5

    # Finishing comfortably inside the limit scores 1.0; running it to the wire
    # scores lower. Under a WAT clock, hesitation is the thing being measured.
    sig.speed = (
        max(0.0, min(1.0, 1.2 - (sum(speed_ratios) / len(speed_ratios))))
        if speed_ratios
        else 0.6
    )
    return sig


def _scale(value: float, low: float, high: float) -> float:
    """Map a raw rate onto the 1-5 board scale, clamped."""
    if high <= low:
        return 3.0
    ratio = (value - low) / (high - low)
    return round(max(1.0, min(5.0, 1.0 + 4.0 * ratio)), 2)


def score_olqs(sig: Signals) -> dict[str, float]:
    """Map signals onto the fifteen qualities.

    Each quality is a small blend rather than a single signal, so one unusual
    word cannot swing a score. The bands come from what a competent response
    looks like: roughly 2-3 action verbs, one or two mentions of other people,
    and 12-25 words for an SRT answer.
    """
    fluency = _scale(sig.avg_words, 4, 26)
    coverage = _scale(sig.completion, 0.45, 0.98)
    action = _scale(sig.action_rate, 0.4, 3.0)
    social = _scale(sig.social_rate, 0.2, 2.2)
    decisive = _scale(sig.decisiveness, 0.3, 0.85)
    positive = _scale(sig.positivity, 0.35, 0.9)
    planning = _scale(sig.planning, 0.2, 2.0)
    responsibility = _scale(sig.responsibility, 0.1, 1.2)
    courage = _scale(sig.courage, 0.1, 1.2)
    stamina = _scale(sig.stamina, 0.1, 1.2)
    influence = _scale(sig.influence, 0.1, 1.2)
    speed = _scale(sig.speed, 0.25, 0.9)

    def blend(*parts: tuple[float, float]) -> float:
        weight = sum(w for _, w in parts) or 1.0
        return round(sum(v * w for v, w in parts) / weight, 2)

    return {
        OLQ.EFFECTIVE_INTELLIGENCE: blend((action, 2), (planning, 2), (fluency, 1)),
        OLQ.REASONING_ABILITY: blend((planning, 2), (fluency, 2), (decisive, 1)),
        OLQ.ORGANISING_ABILITY: blend((planning, 3), (action, 1), (social, 1)),
        OLQ.POWER_OF_EXPRESSION: blend((fluency, 3), (positive, 1), (coverage, 1)),
        OLQ.SOCIAL_ADAPTABILITY: blend((social, 2), (positive, 2), (fluency, 1)),
        OLQ.COOPERATION: blend((social, 3), (positive, 1), (influence, 1)),
        OLQ.SENSE_OF_RESPONSIBILITY: blend((responsibility, 3), (action, 1), (coverage, 1)),
        OLQ.INITIATIVE: blend((action, 2), (decisive, 2), (speed, 1)),
        OLQ.SELF_CONFIDENCE: blend((decisive, 2), (positive, 2), (fluency, 1)),
        OLQ.SPEED_OF_DECISION: blend((speed, 2), (decisive, 2), (coverage, 1)),
        OLQ.ABILITY_TO_INFLUENCE: blend((influence, 3), (social, 1), (decisive, 1)),
        OLQ.LIVELINESS: blend((positive, 2), (fluency, 1), (speed, 1)),
        OLQ.DETERMINATION: blend((coverage, 2), (action, 1), (stamina, 1), (positive, 1)),
        OLQ.COURAGE: blend((courage, 3), (decisive, 1), (action, 1)),
        OLQ.STAMINA: blend((stamina, 3), (coverage, 1), (speed, 1)),
    }


def _feedback(sig: Signals, scores: dict[str, float], test_type: str | None) -> list[str]:
    notes: list[str] = []

    if sig.responses and sig.completion < 0.8:
        missed = sig.responses - sig.answered
        notes.append(
            f"You left {missed} of {sig.responses} items blank. On the board, an unattempted "
            "item reads as hesitation -- write something short rather than nothing."
        )
    elif sig.completion >= 0.98 and sig.responses > 4:
        notes.append("You attempted every item, which is exactly what the clock rewards.")

    if sig.avg_words < 5 and sig.answered:
        notes.append(
            "Your responses are very short. Aim for one complete thought with a subject and "
            "an action -- who did what."
        )
    elif sig.avg_words > 32:
        notes.append(
            "Your responses run long. Under a timed test, a tight sentence carries more weight "
            "than a paragraph you cannot finish."
        )

    if sig.positivity < 0.45:
        notes.append(
            "The overall tone leans negative. Where a situation is difficult, finish on what "
            "you did about it rather than on the difficulty."
        )
    elif sig.positivity > 0.75:
        notes.append("Your tone is consistently constructive.")

    if sig.action_rate < 0.8 and sig.answered:
        notes.append(
            "Few of your answers contain a concrete action. Replace \"I would think about it\" "
            "with the step you would actually take."
        )
    if sig.social_rate < 0.4 and sig.answered:
        notes.append(
            "Other people barely appear in your responses. Officer-like answers usually involve "
            "informing, organising or helping someone."
        )
    if sig.hedging > 0.6:
        notes.append(
            "There is a lot of hedging (maybe, perhaps, I would try). Commit to one course of "
            "action -- speed of decision is scored."
        )
    if test_type == PsychTestType.WAT and sig.avg_words > 12:
        notes.append(
            "WAT responses should be a single short sentence. Long answers cost you words later "
            "in the set."
        )
    if test_type == PsychTestType.SRT and sig.action_rate < 1.5:
        notes.append(
            "SRT answers are judged on the action taken. Name the step, the person you involve "
            "and the outcome."
        )

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    if ranked:
        top = ", ".join(OLQ_LABELS[OLQ(k)] for k, _ in ranked[:3])
        bottom = ", ".join(OLQ_LABELS[OLQ(k)] for k, _ in ranked[-3:])
        notes.append(f"Strongest signals in this sitting: {top}.")
        notes.append(f"Least evidence for: {bottom}. Work these into your next attempt.")

    return notes


@dataclass(slots=True)
class Analysis:
    signals: dict[str, float]
    olq_scores: dict[str, float]
    feedback: list[str]
    overall_score: float
    strengths: list[str]
    improvements: list[str]
    per_response_notes: list[list[str]]

    def as_payload(self) -> dict:
        """Shape the API returns, with labels resolved for the client."""
        ranked = sorted(self.olq_scores.items(), key=lambda kv: kv[1], reverse=True)
        return {
            "signals": self.signals,
            "olq_scores": [
                {"olq": key, "label": OLQ_LABELS[OLQ(key)], "score": value}
                for key, value in ranked
            ],
            "feedback": self.feedback,
            "overall_score": self.overall_score,
            "strengths": self.strengths,
            "improvements": self.improvements,
        }


def _response_notes(response: Response, test_type: str | None) -> list[str]:
    """Per-item hints -- the part candidates actually act on."""
    notes: list[str] = []
    text = response.text.strip()
    if not text:
        return ["Not attempted."]

    words = _words(text)
    if len(words) <= 2 and test_type != PsychTestType.WAT:
        notes.append("Too short to show anything. Add the action you would take.")
    if not _hits(words, ACTION_VERBS):
        notes.append("No concrete action -- say what you would do, not what you would feel.")
    if _hits(words, NEGATIVE) > _hits(words, POSITIVE) and _hits(words, POSITIVE) == 0:
        notes.append("Negative framing. End on the step that resolves the situation.")
    if _hits(words, HEDGING) >= 2:
        notes.append("Hedged. Pick one course of action and state it plainly.")
    if _hits(words, SOCIAL) == 0 and test_type in {PsychTestType.SRT, PsychTestType.SCT}:
        notes.append("Nobody else appears. Involving others is usually the officer-like move.")
    if not notes:
        notes.append("Clear and actionable.")
    return notes


def analyse(
    responses: list[Response], *, test_type: str | None = None, expected_items: int | None = None
) -> Analysis:
    """Full read-out for one sitting of any projective test."""
    if expected_items and expected_items > len(responses):
        # Items never reached still count against completion.
        responses = responses + [
            Response(skipped=True) for _ in range(expected_items - len(responses))
        ]

    sig = measure(responses)
    scores = score_olqs(sig)
    notes = _feedback(sig, scores, test_type)

    overall = round(sum(scores.values()) / len(scores) * 20, 1) if scores else 0.0
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)

    return Analysis(
        signals=sig.as_dict(),
        olq_scores=dict(scores),
        feedback=notes,
        overall_score=overall,
        strengths=[OLQ_LABELS[OLQ(k)] for k, _ in ranked[:4]],
        improvements=[OLQ_LABELS[OLQ(k)] for k, _ in ranked[-4:]],
        per_response_notes=[_response_notes(r, test_type) for r in responses],
    )


def merge_profiles(profiles: list[dict[str, float]]) -> dict[str, float]:
    """Average OLQ scores across sittings for the cumulative profile."""
    if not profiles:
        return {}
    totals: dict[str, list[float]] = {}
    for profile in profiles:
        for key, value in (profile or {}).items():
            if key in OLQ_LABELS or key in {o.value for o in OLQ}:
                totals.setdefault(key, []).append(float(value))
    return {k: round(sum(v) / len(v), 2) for k, v in totals.items() if v}
