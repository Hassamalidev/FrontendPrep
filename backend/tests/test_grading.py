"""The grading function.

``grade`` is pure and synchronous precisely so the marking rules can be pinned
down here without a database, a paper or a logged-in user.
"""

from __future__ import annotations

from app.services.attempt_service import _merge_topic_mastery, grade

BLUEPRINT = [
    {"id": 1, "keys": ["a"], "marks": 1.0, "neg": 0.25, "topic_id": 7},
    {"id": 2, "keys": ["b"], "marks": 1.0, "neg": 0.25, "topic_id": 7},
    {"id": 3, "keys": ["c"], "marks": 2.0, "neg": 0.5, "topic_id": 9},
    {"id": 4, "keys": ["a", "c"], "marks": 2.0, "neg": 0.0, "topic_id": 9},
]


class TestGrade:
    def test_all_correct(self):
        answers = [
            {"id": 1, "picked": ["a"]},
            {"id": 2, "picked": ["b"]},
            {"id": 3, "picked": ["c"]},
            {"id": 4, "picked": ["a", "c"]},
        ]
        result = grade(BLUEPRINT, answers)
        assert result["correct"] == 4
        assert result["wrong"] == 0
        assert result["score"] == 6.0
        assert result["max_score"] == 6.0
        assert result["percentage"] == 100.0

    def test_nothing_attempted_scores_zero_without_penalty(self):
        result = grade(BLUEPRINT, [])
        assert result["attempted"] == 0
        assert result["score"] == 0.0
        assert result["percentage"] == 0.0

    def test_negative_marking_applies_to_wrong_answers_only(self):
        result = grade(BLUEPRINT, [{"id": 1, "picked": ["b"]}, {"id": 2, "picked": ["b"]}])
        # +1 for Q2, -0.25 for Q1
        assert result["score"] == 0.75
        assert result["wrong"] == 1
        assert result["attempted"] == 2

    def test_score_never_goes_negative(self):
        answers = [{"id": q["id"], "picked": ["z"]} for q in BLUEPRINT]
        result = grade(BLUEPRINT, answers)
        assert result["score"] == 0.0
        assert result["wrong"] == 4

    def test_multi_select_requires_the_exact_set(self):
        partial = grade(BLUEPRINT, [{"id": 4, "picked": ["a"]}])
        exact = grade(BLUEPRINT, [{"id": 4, "picked": ["c", "a"]}])
        assert partial["correct"] == 0
        assert exact["correct"] == 1  # order does not matter, membership does

    def test_unknown_question_ids_are_ignored(self):
        result = grade(BLUEPRINT, [{"id": 999, "picked": ["a"]}, {"id": 1, "picked": ["a"]}])
        assert result["correct"] == 1
        assert result["attempted"] == 1

    def test_topic_breakdown_counts_every_served_question(self):
        result = grade(BLUEPRINT, [{"id": 1, "picked": ["a"]}, {"id": 3, "picked": ["a"]}])
        assert result["topic_stats"]["7"] == {"seen": 2, "correct": 1}
        assert result["topic_stats"]["9"] == {"seen": 2, "correct": 0}

    def test_per_question_detail_is_complete(self):
        result = grade(BLUEPRINT, [{"id": 1, "picked": ["a"], "ms": 4200, "flagged": True}])
        first = result["per_question"][0]
        assert first["correct"] is True
        assert first["marks_awarded"] == 1.0
        assert first["ms"] == 4200
        assert first["flagged"] is True
        assert len(result["per_question"]) == len(BLUEPRINT)

    def test_empty_paper_does_not_divide_by_zero(self):
        result = grade([], [])
        assert result["percentage"] == 0.0
        assert result["max_score"] == 0.0


class TestTopicMastery:
    def test_merges_counts(self):
        merged = _merge_topic_mastery(
            {"7": {"seen": 5, "correct": 3}}, {"7": {"seen": 2, "correct": 2}}
        )
        assert merged["7"] == {"seen": 7, "correct": 5}

    def test_caps_the_blob_and_keeps_the_weakest(self):
        """The panel exists to surface weak areas, so those must survive the cap."""
        from app.services.attempt_service import TOPIC_MASTERY_CAP

        current = {str(i): {"seen": 10, "correct": 10} for i in range(TOPIC_MASTERY_CAP + 20)}
        current["weakest"] = {"seen": 10, "correct": 0}
        merged = _merge_topic_mastery(current, {})
        assert len(merged) == TOPIC_MASTERY_CAP
        assert "weakest" in merged
