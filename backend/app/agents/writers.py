"""Agent 3: turn facts into question candidates.

Each writer is a template with a narrow contract: given a fact whose answer span
is known, produce a stem that is answerable from the passage alone, a correct
option, and same-type distractors. Templates are boring on purpose -- a stem
that reads like every other test-prep book is a feature, and it keeps the output
defensible without a language model.

Nothing here touches the database. The pipeline scores and persists.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from app.agents import distractors
from app.agents.facts import Fact, FactKind
from app.core.enums import Difficulty, QuestionType

# Spans that parse as entities but cannot stand in for a discussion subject.
_NOT_A_TOPIC = frozenset(
    """
    january february march april may june july august september october november december
    monday tuesday wednesday thursday friday saturday sunday percent million billion
    trillion crore lakh tonnes kilometres kilometers metres meters dollars rupees
    figures growth report reports official officials source sources statement
    """.split()
)

OPTION_KEYS = ("a", "b", "c", "d", "e")

_LEAD_IN = {
    FactKind.NUMERIC: "Complete the statement with the correct figure:",
    FactKind.DATE: "Complete the statement with the correct date:",
    FactKind.ROLE: "Complete the statement:",
    FactKind.DEFINITION: "Complete the statement:",
    FactKind.ENTITY: "Complete the statement:",
    FactKind.EVENT: "Complete the statement:",
}

_DISTRACTOR_KIND = {
    FactKind.NUMERIC: "numeric",
    FactKind.DATE: "date",
    FactKind.ROLE: "entity",
    FactKind.DEFINITION: "entity",
    FactKind.ENTITY: "entity",
    FactKind.EVENT: "entity",
}


@dataclass(slots=True)
class Candidate:
    """A question before the critic has judged it."""

    qtype: QuestionType
    stem: str
    options: list[dict] = field(default_factory=list)
    answer_keys: list[str] = field(default_factory=list)
    explanation: str = ""
    difficulty: Difficulty = Difficulty.MEDIUM
    tags: list[str] = field(default_factory=list)
    source_sentence: str = ""
    template: str = ""
    salience: float = 0.0
    quality: float = 0.0
    critique: dict = field(default_factory=dict)

    @property
    def answer_text(self) -> str:
        by_key = {o["key"]: o["text"] for o in self.options}
        return " / ".join(by_key.get(k, k) for k in self.answer_keys)

    def as_dict(self) -> dict:
        return {
            "qtype": str(self.qtype),
            "stem": self.stem,
            "options": self.options,
            "answer_keys": self.answer_keys,
            "explanation": self.explanation,
            "difficulty": str(self.difficulty),
            "tags": self.tags,
            "quality_score": round(self.quality, 3),
            "generation_meta": {
                "template": self.template,
                "salience": round(self.salience, 3),
                "source_sentence": self.source_sentence[:400],
                "critique": self.critique,
            },
        }


def _difficulty_for(fact: Fact) -> Difficulty:
    """Longer, later, less salient sentences make harder questions.

    The bands are tighter than they look: a lead sentence with a headline
    number is genuinely easy, and almost everything a news article yields sits
    in the middle. Widening EASY here produces papers that are entirely easy,
    which then starves the difficulty mix at sampling time.
    """
    words = len(fact.sentence.split())
    if fact.salience >= 0.92 and words <= 22:
        return Difficulty.EASY
    if fact.salience < 0.72 or words > 32:
        return Difficulty.HARD
    return Difficulty.MEDIUM


def _shuffle_options(answer: str, wrong: list[str], rng: random.Random) -> tuple[list[dict], list[str]]:
    texts = [answer, *wrong]
    rng.shuffle(texts)
    options = [{"key": OPTION_KEYS[i], "text": text} for i, text in enumerate(texts)]
    keys = [o["key"] for o in options if o["text"] == answer]
    return options, keys[:1]


def _pool_for(fact: Fact, entities: dict[str, list[str]]) -> tuple[list[str], str]:
    """Same-label alternatives from this article, plus the label to fall back on."""
    answer_lower = fact.answer.lower()
    for label in ("PERSON", "ORG", "GPE", "PROPER", "EVENT"):
        values = entities.get(label, [])
        # Containment, not equality: the extractor may hold "Naveed Ashraf"
        # while the fact answer is "Admiral Naveed Ashraf". Requiring an exact
        # match here is what silently drops a question to generic distractors.
        if any(v.lower() in answer_lower or answer_lower in v.lower() for v in values):
            return [
                v
                for v in values
                if v.lower() not in answer_lower and answer_lower not in v.lower()
            ], label
    # Not recognised as any particular type: offer every proper noun we saw.
    everything = [
        v
        for label, values in entities.items()
        if label not in {"NUM", "DATE"}
        for v in values
        if v.lower() != answer_lower
    ]
    return everything, "PROPER"


def write_mcq(fact: Fact, entities: dict[str, list[str]], rng: random.Random) -> Candidate | None:
    pool, label = _pool_for(fact, entities)
    wrong = distractors.build(
        fact.answer,
        kind=_DISTRACTOR_KIND[fact.kind],
        pool=pool,
        label=label,
        count=3,
        forbid=fact.sentence,
        seed=f"{fact.sentence}|{fact.answer}",
    )
    if len(wrong) < 3:
        return None

    # A role fact supports a real question rather than a cloze.
    if fact.kind is FactKind.ROLE and fact.relation:
        article = "the " if not fact.relation.lower().startswith("the ") else ""
        stem = f"Who is {article}{fact.relation}?"
        template = "role_who"
    else:
        blanked = fact.blanked
        if "______" not in blanked:
            return None
        stem = f"{_LEAD_IN[fact.kind]} {blanked}"
        template = f"cloze_{fact.kind.value}"

    options, keys = _shuffle_options(fact.answer, wrong, rng)
    if not keys:
        return None

    return Candidate(
        qtype=QuestionType.MCQ,
        stem=stem,
        options=options,
        answer_keys=keys,
        explanation=f"From the source: {fact.sentence}",
        difficulty=_difficulty_for(fact),
        source_sentence=fact.sentence,
        template=template,
        salience=fact.salience,
    )


def write_true_false(fact: Fact, entities: dict[str, list[str]], rng: random.Random) -> Candidate | None:
    """Half the items assert the fact; half assert a corrupted version."""
    make_false = rng.random() < 0.5
    statement = fact.sentence

    if make_false:
        pool, label = _pool_for(fact, entities)
        wrong = distractors.build(
            fact.answer,
            kind=_DISTRACTOR_KIND[fact.kind],
            pool=pool,
            label=label,
            count=1,
            forbid=fact.sentence,
            seed=f"tf|{fact.sentence}|{fact.answer}",
        )
        if not wrong:
            return None
        from app.agents.facts import replace_span

        statement = replace_span(fact.sentence, fact.answer, wrong[0])
        if statement == fact.sentence:
            return None

    answer = "false" if make_false else "true"
    options = [{"key": "a", "text": "True"}, {"key": "b", "text": "False"}]
    return Candidate(
        qtype=QuestionType.TRUE_FALSE,
        stem=f"True or false: {statement}",
        options=options,
        answer_keys=["a" if answer == "true" else "b"],
        explanation=(
            f"The passage states: {fact.sentence}"
            if not make_false
            else f"False. The passage states: {fact.sentence}"
        ),
        difficulty=Difficulty.EASY if not make_false else _difficulty_for(fact),
        source_sentence=fact.sentence,
        template="true_false_corrupted" if make_false else "true_false_direct",
        salience=fact.salience,
    )


def write_fill_blank(fact: Fact, rng: random.Random) -> Candidate | None:
    blanked = fact.blanked
    if "______" not in blanked:
        return None
    return Candidate(
        qtype=QuestionType.FILL_BLANK,
        stem=f"Fill in the blank: {blanked}",
        options=[],
        answer_keys=[fact.answer],
        explanation=f"From the source: {fact.sentence}",
        difficulty=_difficulty_for(fact),
        source_sentence=fact.sentence,
        template=f"blank_{fact.kind.value}",
        salience=fact.salience,
    )


_QUESTION_WORD = {
    FactKind.NUMERIC: "What figure does the passage give",
    FactKind.DATE: "What date does the passage give",
    FactKind.ROLE: "Who does the passage identify",
    FactKind.DEFINITION: "What does the passage describe",
    FactKind.ENTITY: "Which name does the passage give",
    FactKind.EVENT: "What does the passage report",
}


def write_short_answer(fact: Fact) -> Candidate | None:
    if fact.kind is FactKind.ROLE and fact.relation:
        stem = f"Who is {fact.relation}? Answer in a few words."
    else:
        blanked = fact.blanked
        if "______" not in blanked:
            return None
        stem = f"{_QUESTION_WORD[fact.kind]} in place of the blank? {blanked}"

    return Candidate(
        qtype=QuestionType.SHORT_ANSWER,
        stem=stem,
        options=[],
        answer_keys=[fact.answer],
        explanation=f"From the source: {fact.sentence}",
        difficulty=_difficulty_for(fact),
        source_sentence=fact.sentence,
        template=f"short_{fact.kind.value}",
        salience=fact.salience,
    )


# --- ISSB item writers -----------------------------------------------------
#
# These are not graded, so they are held to a different bar: the stimulus only
# has to be neutral, on-topic and open enough that a candidate can project onto
# it. Templates are seeded with the article's own subject matter so the current
# affairs the student is reading and the psych practice they do stay connected.

_SCT_TEMPLATES = (
    "When I read about {topic}, I",
    "My view on {topic} is",
    "If I were responsible for {topic}, I would",
    "The people involved in {topic}",
    "{topic} makes me",
    "The best way to handle {topic} is",
    "My duty towards {topic}",
    "Others believe {topic} is",
)

_SRT_TEMPLATES = (
    "You are leading a group visiting a site connected with {topic} when a member is injured "
    "and no transport is available. You...",
    "During a discussion on {topic}, two of your team members start arguing loudly in front of "
    "your seniors. You...",
    "You are told to prepare a briefing on {topic} in one hour, but the notes you were given "
    "are incomplete. You...",
    "While travelling to a camp, you overhear people spreading false information about {topic}. "
    "You...",
    "Your team is assigned a task related to {topic} and the deadline is moved forward by a day. "
    "You...",
    "You notice a junior struggling with duties connected to {topic} and falling behind. You...",
)

_INTERVIEW_TEMPLATES = (
    ("current_affairs", "What do you know about {topic}? Explain in your own words."),
    ("current_affairs", "Why is {topic} significant for Pakistan?"),
    ("defence", "How does {topic} affect our national security?"),
    ("situational", "If you were asked to brief your seniors on {topic}, what would you cover?"),
    ("personal", "What is your personal opinion on {topic}, and what shaped it?"),
    ("current_affairs", "What are the arguments on both sides of {topic}?"),
)


def _topics_from(
    doc_entities: dict[str, list[str]],
    noun_phrases: list[str],
    limit: int,
    *,
    include_people: bool = False,
) -> list[str]:
    """Pick subjects worth projecting onto: named entities first, then phrases.

    ``include_people`` is off for the projective templates and on for interview
    questions. "What do you know about Air Chief Marshal X?" is a real interview
    question; "If I were responsible for Air Chief Marshal X, I would" is not a
    sentence anyone can complete.
    """
    seen: set[str] = set()
    topics: list[str] = []

    def clean(value: str) -> str:
        # "My view on The Ministry of Defence is" reads badly; drop the article.
        return value[4:] if value.lower().startswith("the ") else value

    def usable(value: str) -> bool:
        """A topic has to be a subject someone can discuss.

        Dates, bare numbers and model designations are not: substituted into an
        SCT stem or an SRT situation they produce items like "During a
        discussion on July..." -- which reads as broken software to a candidate,
        and is worse than producing nothing.
        """
        stripped = value.strip()
        if len(stripped) < 4 or any(ch.isdigit() for ch in stripped):
            return False
        # Word-wise, not whole-phrase: "million dollars" carries no digits and
        # is not itself in the list, but it is still not something you can hold
        # a discussion about.
        return not any(word.lower().strip(".,") in _NOT_A_TOPIC for word in stripped.split())

    # PROPER is the extractor's "a capitalised run I could not classify" bucket,
    # so a sentence-initial common noun lands there -- and produced items like
    # "During a discussion on Headline". A single word is only trusted from a
    # label that carries evidence; from PROPER it must be a multi-word name.
    def trusted(label: str, value: str) -> bool:
        return label != "PROPER" or len(value.split()) >= 2

    # Excluding the PERSON *label* is not enough: the extractor files a name
    # under PROPER as well, so the name would come back through that door.
    # Exclude the values themselves.
    people = {v.lower() for v in doc_entities.get("PERSON", [])} if not include_people else set()

    labels = ("EVENT", "ORG", "GPE", "PROPER") + (("PERSON",) if include_people else ())
    for label in labels:
        for raw in doc_entities.get(label, []):
            value = clean(raw)
            key = value.lower()
            if key in seen or not usable(value) or not trusted(label, value):
                continue
            if any(key == person or key in person or person in key for person in people):
                continue
            seen.add(key)
            topics.append(value)
            if len(topics) >= limit:
                return topics

    for raw in noun_phrases:
        phrase = clean(raw)
        key = phrase.lower()
        # Noun "chunks" from the rule extractor are approximate and sometimes
        # swallow a verb ("Headline figures showed growth"). Two or three words
        # is the band that reliably reads as a subject.
        if key in seen or not 2 <= len(phrase.split()) <= 3 or not usable(phrase):
            continue
        seen.add(key)
        topics.append(phrase)
        if len(topics) >= limit:
            break
    return topics


def write_sct_items(topics: list[str], count: int, rng: random.Random) -> list[dict]:
    out: list[dict] = []
    for index in range(count):
        if not topics:
            break
        topic = topics[index % len(topics)]
        template = _SCT_TEMPLATES[index % len(_SCT_TEMPLATES)]
        out.append(
            {
                "test_type": "sct",
                "prompt": template.format(topic=topic),
                "seconds": 30,
                "target_olqs": ["power_of_expression", "social_adaptability"],
                "tags": [topic],
            }
        )
    return out


def write_srt_items(topics: list[str], count: int, rng: random.Random) -> list[dict]:
    out: list[dict] = []
    for index in range(count):
        if not topics:
            break
        topic = topics[index % len(topics)]
        template = _SRT_TEMPLATES[index % len(_SRT_TEMPLATES)]
        out.append(
            {
                "test_type": "srt",
                "prompt": template.format(topic=topic),
                "seconds": 30,
                "target_olqs": [
                    "initiative",
                    "speed_of_decision",
                    "sense_of_responsibility",
                    "organising_ability",
                ],
                "tags": [topic],
            }
        )
    return out


def write_interview_items(topics: list[str], count: int, rng: random.Random) -> list[dict]:
    out: list[dict] = []
    for index in range(count):
        if not topics:
            break
        topic = topics[index % len(topics)]
        category, template = _INTERVIEW_TEMPLATES[index % len(_INTERVIEW_TEMPLATES)]
        out.append(
            {
                "category": category,
                "question": template.format(topic=topic),
                "guidance": (
                    "Give a structured answer: what it is, why it matters, and your own view "
                    "with a reason. Do not bluff a figure you are unsure of."
                ),
                "follow_ups": [
                    f"What is the counter-argument on {topic}?",
                    f"Where did you read about {topic}?",
                ],
                "target_olqs": ["effective_intelligence", "power_of_expression", "reasoning_ability"],
            }
        )
    return out
