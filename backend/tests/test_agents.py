"""The local question engine: extraction, generation, critique, OLQ analysis.

These are pure functions, so they need no database and run in milliseconds --
which is the point of keeping the pipeline free of persistence.
"""

from __future__ import annotations

from app.agents import critic, distractors, facts, nlp, olq, pipeline, writers
from app.core.enums import Difficulty, QuestionType

ARTICLE = """
Pakistan Navy commissioned PNS Hangor at Karachi on 25 June 2024, marking the delivery of the
first of eight Hangor-class submarines. The submarine was built under an agreement worth
5 billion dollars signed in 2015 between Pakistan and China. Admiral Naveed Ashraf is the Chief
of Naval Staff of Pakistan. The vessel can remain submerged for 30 days and carries a crew of
38 sailors. The Ministry of Defence said the programme will create 2,500 jobs in the domestic
shipbuilding sector. The Hangor class displaces 2,800 tonnes and has a range of 12,000
kilometres. Naval officials stated that the class will replace the ageing Agosta 90B fleet
by 2030.
"""


class TestNlp:
    def test_works_without_spacy(self):
        """The engine must never require an optional dependency to function."""
        doc = nlp.analyse(ARTICLE)
        assert doc.backend in {"rules", "spacy"}
        assert len(doc.sentences) >= 5
        assert doc.content_words

    def test_entities_have_no_line_breaks(self):
        doc = nlp.analyse("Karachi Shipyard and Engineering\nWorks built the hull.")
        for values in doc.entities.values():
            for value in values:
                assert "\n" not in value

    def test_empty_input_is_not_an_error(self):
        doc = nlp.analyse("")
        assert doc.sentences == []


class TestFacts:
    def test_extracts_numbers_dates_and_roles(self):
        found, _ = facts.extract(ARTICLE)
        kinds = {f.kind for f in found}
        assert facts.FactKind.NUMERIC in kinds
        assert facts.FactKind.DATE in kinds
        assert facts.FactKind.ROLE in kinds

    def test_role_keeps_the_source_preposition(self):
        found, _ = facts.extract(
            "The Chairman is the head of the National Commission for Human Development."
        )
        roles = [f for f in found if f.kind is facts.FactKind.ROLE]
        assert roles and "for Human Development" in roles[0].relation

    def test_salience_prefers_the_lead(self):
        found, _ = facts.extract(ARTICLE)
        assert found == sorted(found, key=lambda f: (-f.salience, f.index))

    def test_blanking_replaces_the_answer(self):
        found, _ = facts.extract(ARTICLE)
        fact = next(f for f in found if f.answer in f.sentence)
        assert "______" in fact.blanked
        assert fact.answer not in fact.blanked


class TestDistractors:
    def test_numeric_keeps_units_and_magnitude(self):
        out = distractors.build("5 billion", kind="numeric")
        assert len(out) == 3
        assert all("billion" in o for o in out)
        assert "5 billion" not in out

    def test_dates_shift_within_a_believable_window(self):
        out = distractors.build("2015", kind="date")
        assert len(out) == 3
        assert all(o.isdigit() and 2000 < int(o) < 2035 for o in out)

    def test_entities_come_from_the_same_pool(self):
        out = distractors.build(
            "Pakistan Navy", kind="entity", label="ORG", pool=["Pakistan Army", "Pakistan Air Force"]
        )
        assert "Pakistan Navy" not in out
        assert len(out) == 3

    def test_never_returns_the_answer(self):
        for kind, answer in (("numeric", "30 days"), ("date", "25 June 2024"), ("entity", "Karachi")):
            assert answer not in distractors.build(answer, kind=kind)


class TestCritic:
    def _candidate(self, **overrides) -> writers.Candidate:
        base: dict = {}
        base.update(
            qtype=QuestionType.MCQ,
            stem="Complete the statement with the correct figure: The vessel carries ______ sailors.",
            options=[
                {"key": "a", "text": "38"},
                {"key": "b", "text": "42"},
                {"key": "c", "text": "30"},
                {"key": "d", "text": "50"},
            ],
            answer_keys=["a"],
            salience=0.9,
        )
        base.update(overrides)
        return writers.Candidate(**base)

    def test_a_good_question_passes(self):
        assert critic.judge(self._candidate()).score >= 0.8

    def test_pronoun_stem_is_vetoed(self):
        """A stem needing the previous sentence is unanswerable, not merely weak."""
        verdict = critic.judge(
            self._candidate(stem="Complete the statement: It rose by ______ last year.")
        )
        assert verdict.score == 0.0
        assert any("pronoun" in r for r in verdict.reasons)

    def test_leaked_answer_is_vetoed(self):
        verdict = critic.judge(
            self._candidate(stem="The vessel carries 38 sailors. How many sailors does it carry?")
        )
        assert verdict.score == 0.0

    def test_duplicate_options_are_vetoed(self):
        verdict = critic.judge(
            self._candidate(
                options=[
                    {"key": "a", "text": "38"},
                    {"key": "b", "text": "38"},
                    {"key": "c", "text": "30"},
                    {"key": "d", "text": "50"},
                ]
            )
        )
        assert verdict.score == 0.0

    def test_generic_answer_is_vetoed(self):
        verdict = critic.judge(
            self._candidate(
                stem="Who is the head of the commission?",
                options=[
                    {"key": "a", "text": "The Chairman"},
                    {"key": "b", "text": "General Asim Munir"},
                    {"key": "c", "text": "Admiral Naveed Ashraf"},
                    {"key": "d", "text": "Karachi"},
                ],
            )
        )
        assert verdict.score == 0.0


class TestPipeline:
    def test_produces_usable_questions(self):
        result = pipeline.run(ARTICLE, {"mcq": 5, "true_false": 3, "fill_blank": 2})
        assert result.error is None
        assert result.questions
        assert result.avg_quality and result.avg_quality > 0.5

        for candidate in result.questions:
            assert candidate.stem
            if candidate.qtype in {QuestionType.MCQ, QuestionType.TRUE_FALSE}:
                keys = {o["key"] for o in candidate.options}
                assert len(keys) == len(candidate.options)   # unique option keys
                assert set(candidate.answer_keys) <= keys    # answer is among them
                assert candidate.answer_keys                 # and there is one

    def test_is_deterministic(self):
        config = {"mcq": 5, "true_false": 2}
        first = pipeline.run(ARTICLE, config, seed="fixed")
        second = pipeline.run(ARTICLE, config, seed="fixed")
        assert [c.stem for c in first.questions] == [c.stem for c in second.questions]

    def test_trace_explains_the_run(self):
        result = pipeline.run(ARTICLE, {"mcq": 4})
        agents = [step.agent for step in result.trace]
        assert agents[:3] == ["extract", "summarise", "write"]
        assert all(step.ms >= 0 for step in result.trace)

    def test_short_input_is_refused_not_crashed(self):
        result = pipeline.run("Too short.", {"mcq": 5})
        assert result.error is not None
        assert result.questions == []

    def test_junk_input_is_mostly_rejected(self):
        junk = (
            "It rose by 5 percent last year across the region. They said the figure of "
            "12 percent was reached. He confirmed that the total was 340 million rupees. "
            "That figure was revised again afterwards. This was mentioned in the above "
            "report by the committee. It fell again later that year according to them. "
            "They noted that the change of 8 percent was within the expected range. "
            "He added that the above mentioned committee would meet again shortly."
        )
        result = pipeline.run(junk, {"mcq": 6, "fill_blank": 4})
        assert result.below_threshold > len(result.questions)

    def test_one_sentence_cannot_fill_a_paper(self):
        result = pipeline.run(ARTICLE, {"mcq": 8, "true_false": 8, "fill_blank": 8})
        by_sentence: dict[str, int] = {}
        for candidate in result.questions:
            by_sentence[candidate.source_sentence] = by_sentence.get(candidate.source_sentence, 0) + 1
        assert max(by_sentence.values()) <= pipeline.MAX_PER_SENTENCE

    def test_no_network_or_api_key_involved(self):
        """The whole point of the engine: it must work with no credentials."""
        import inspect

        for module in (pipeline, writers, critic, facts, distractors, nlp):
            source = inspect.getsource(module)
            for banned in ("api_key", "openai", "anthropic", "requests.post", "httpx.post"):
                assert banned not in source.lower(), f"{module.__name__} references {banned}"


class TestOlq:
    WEAK = [
        olq.Response(text="I would feel sad and maybe try later", ms=14000, seconds_allowed=30),
        olq.Response(text="It is very difficult and I might fail", ms=16000, seconds_allowed=30),
        olq.Response(skipped=True),
        olq.Response(skipped=True),
    ]
    STRONG = [
        olq.Response(text="I informed the JCO, divided the party in two and cleared the route by 0900", ms=9000, seconds_allowed=30),
        olq.Response(text="He organised his team, briefed them quickly and completed the task safely", ms=8000, seconds_allowed=30),
        olq.Response(text="I helped the injured man, called for help and carried him to the vehicle", ms=10000, seconds_allowed=30),
        olq.Response(text="She planned the schedule, assigned duties to everyone and finished on time", ms=11000, seconds_allowed=30),
    ]

    def test_discriminates_between_weak_and_strong(self):
        weak = olq.analyse(self.WEAK, test_type="srt")
        strong = olq.analyse(self.STRONG, test_type="srt")
        assert strong.overall_score > weak.overall_score + 15

    def test_inflected_verbs_are_matched(self):
        """`organised` must count as an action verb, or every score collapses."""
        strong = olq.analyse(self.STRONG, test_type="srt")
        assert strong.signals["action_rate"] >= 2.0

    def test_every_olq_is_scored_in_range(self):
        from app.core.enums import OLQ

        result = olq.analyse(self.STRONG, test_type="srt")
        assert set(result.olq_scores) == {o.value for o in OLQ}
        assert all(1.0 <= v <= 5.0 for v in result.olq_scores.values())

    def test_blank_responses_lower_completion(self):
        result = olq.analyse(self.WEAK, test_type="srt")
        assert result.signals["completion"] == 0.5
        assert any("blank" in note for note in result.feedback)

    def test_unreached_items_count_against_the_candidate(self):
        partial = olq.analyse(self.STRONG, test_type="wat", expected_items=8)
        full = olq.analyse(self.STRONG, test_type="wat", expected_items=4)
        assert partial.signals["completion"] < full.signals["completion"]

    def test_per_item_notes_are_actionable(self):
        result = olq.analyse(self.WEAK, test_type="srt")
        assert result.per_response_notes[0]
        assert result.per_response_notes[2] == ["Not attempted."]

    def test_no_responses_does_not_crash(self):
        result = olq.analyse([], test_type="wat")
        assert result.overall_score >= 0
        assert result.signals["answered"] == 0

    def test_profiles_average_across_sittings(self):
        merged = olq.merge_profiles([{"courage": 4.0}, {"courage": 2.0}])
        assert merged["courage"] == 3.0


class TestWriters:
    def test_role_facts_become_who_questions(self):
        found, doc = facts.extract(ARTICLE)
        role = next(f for f in found if f.kind is facts.FactKind.ROLE)
        import random

        candidate = writers.write_mcq(role, doc.entities, random.Random(1))
        assert candidate is not None
        assert candidate.stem.startswith("Who is")
        assert candidate.answer_text == role.answer

    def test_true_false_marks_corrupted_statements_false(self):
        import random

        found, doc = facts.extract(ARTICLE)
        fact = found[0]
        for seed in range(12):
            candidate = writers.write_true_false(fact, doc.entities, random.Random(seed))
            if candidate is None:
                continue
            picked = next(o["text"] for o in candidate.options if o["key"] in candidate.answer_keys)
            corrupted = candidate.template == "true_false_corrupted"
            assert picked == ("False" if corrupted else "True")

    def test_difficulty_is_not_uniformly_easy(self):
        result = pipeline.run(ARTICLE, {"mcq": 8, "true_false": 4, "fill_blank": 4})
        levels = {c.difficulty for c in result.questions}
        assert levels <= {Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD}
        assert result.questions


class TestGeneratedTopics:
    """Projective items are substituted into templates, so a bad topic reads as
    broken software: "During a discussion on July, two of your team members..."
    """

    DATED = (
        "Pakistan Air Force inducted a squadron of JF-17 fighters at Kamra in March 2024. "
        "The contract worth 250 million dollars was signed in July 2021 between the parties. "
        "Air Chief Marshal Zaheer Ahmed Babar is the Chief of Air Staff of Pakistan. "
        "The fighter has a combat radius of 1,350 kilometres and a top speed of Mach 1.6. "
        "Officials said the programme supports 12,000 skilled jobs at Kamra and Islamabad. "
        "Two more squadrons will be delivered by December 2026 under the same arrangement."
    )

    def _topics(self):
        result = pipeline.run(self.DATED, {"mcq": 2, "sct": 6, "srt": 6, "interview": 3})
        return result.psych_items + result.interview_questions

    def test_months_never_become_topics(self):
        text = " ".join(
            item.get("prompt", "") + item.get("question", "") for item in self._topics()
        ).lower()
        for month in ("january", "march", "july", "december"):
            assert f"on {month}" not in text, f'"{month}" leaked into a generated item'
            assert f"about {month}" not in text

    def test_bare_numbers_never_become_topics(self):
        for item in self._topics():
            topic_line = item.get("prompt") or item.get("question", "")
            # A quantity substituted as a subject reads as nonsense.
            assert "discussion on 1,350" not in topic_line
            assert "responsible for 12,000" not in topic_line

    def test_months_are_still_extracted_as_dates(self):
        """Filtering topics must not cost the fact extractor its date facts."""
        found, _ = facts.extract(self.DATED)
        assert any(f.kind is facts.FactKind.DATE for f in found)
