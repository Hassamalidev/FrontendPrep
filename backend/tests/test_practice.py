"""End-to-end: create questions, sit a paper, submit it, read the result."""

from __future__ import annotations

import pytest


async def _make_questions(client, admin, module_id: int, count: int = 6) -> list[int]:
    """Questions where option "a" is always correct, so answers are predictable."""
    ids = []
    for n in range(count):
        response = await client.post(
            "/admin/questions",
            headers=admin["headers"],
            json={
                "module_id": module_id,
                "stem": f"Which of these is the capital of country number {n}?",
                "options": [
                    {"key": "a", "text": f"City {n}A"},
                    {"key": "b", "text": f"City {n}B"},
                    {"key": "c", "text": f"City {n}C"},
                    {"key": "d", "text": f"City {n}D"},
                ],
                "answer_keys": ["a"],
                "explanation": f"City {n}A is the capital.",
                "difficulty": "medium",
                "status": "approved",
            },
        )
        assert response.status_code == 201, response.text
        ids.append(response.json()["id"])
    return ids


@pytest.fixture
async def module_id(client, admin, seeded) -> int:
    """A module of this test's own, empty until it fills it.

    The seeded starter bank means shared modules are no longer empty, and these
    tests assert exact counts and exact answers ("a" is always correct). Owning
    a module keeps them precise instead of loosening every assertion to a range.
    """
    response = await client.post(
        "/admin/modules",
        headers=admin["headers"],
        json={
            "service_id": 1,
            "stage_id": 2,
            "slug": "test-only-bank",
            "title": "Test Only Bank",
            "default_question_count": 20,
            "default_duration_min": 20,
            "sort_order": 900,
            "is_active": True,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.fixture
async def empty_module_id(client, admin, seeded) -> int:
    """A second module that stays empty, for the no-questions path."""
    response = await client.post(
        "/admin/modules",
        headers=admin["headers"],
        json={
            "service_id": 1,
            "stage_id": 2,
            "slug": "test-only-empty",
            "title": "Test Only Empty",
            "default_question_count": 20,
            "default_duration_min": 20,
            "sort_order": 901,
            "is_active": True,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


class TestQuestionBank:
    async def test_create_and_list(self, client, admin, module_id):
        ids = await _make_questions(client, admin, module_id, 3)
        assert len(ids) == 3
        response = await client.get("/questions", params={"module_id": module_id})
        assert response.status_code == 200
        assert response.json()["total"] == 3

    async def test_students_never_see_the_answer_key(self, client, admin, student, module_id):
        await _make_questions(client, admin, module_id, 2)
        body = (await client.get("/questions", params={"module_id": module_id})).json()
        assert body["items"]
        for item in body["items"]:
            assert "answer_keys" not in item
            assert "explanation" not in item

    async def test_identical_question_is_rejected(self, client, admin, module_id):
        payload = {
            "module_id": module_id,
            "stem": "Which of these is the capital of country number 0?",
            "options": [{"key": "a", "text": "City 0A"}, {"key": "b", "text": "City 0B"}],
            "answer_keys": ["a"],
            "status": "approved",
        }
        first = await client.post("/admin/questions", headers=admin["headers"], json=payload)
        assert first.status_code == 201
        again = await client.post("/admin/questions", headers=admin["headers"], json=payload)
        assert again.status_code == 409

    async def test_answer_key_must_be_among_the_options(self, client, admin, module_id):
        response = await client.post(
            "/admin/questions",
            headers=admin["headers"],
            json={
                "module_id": module_id,
                "stem": "A question whose key is not an option at all.",
                "options": [{"key": "a", "text": "One"}, {"key": "b", "text": "Two"}],
                "answer_keys": ["z"],
            },
        )
        assert response.status_code == 422

    async def test_approving_updates_the_module_counter(self, client, admin, module_id):
        await _make_questions(client, admin, module_id, 4)
        response = await client.get(f"/catalog/modules/{module_id}")
        assert response.json()["approved_question_count"] == 4


class TestAttemptFlow:
    async def test_full_cycle(self, client, admin, student, module_id):
        await _make_questions(client, admin, module_id, 6)

        start = await client.post(
            "/attempts",
            headers=student["headers"],
            json={"module_id": module_id, "count": 5, "mode": "practice"},
        )
        assert start.status_code == 201, start.text
        paper = start.json()
        assert paper["total_questions"] == 5
        assert len(paper["questions"]) == 5
        assert all("answer_keys" not in q for q in paper["questions"])

        answers = [{"id": q["id"], "picked": ["a"], "ms": 3000} for q in paper["questions"][:3]]
        answers += [{"id": q["id"], "picked": ["b"], "ms": 2000} for q in paper["questions"][3:]]

        submit = await client.post(
            f"/attempts/{paper['id']}/submit",
            headers=student["headers"],
            json={"answers": answers, "duration_sec": 120},
        )
        assert submit.status_code == 200, submit.text
        result = submit.json()
        assert result["correct"] == 3
        assert result["wrong"] == 2
        assert result["attempted"] == 5
        assert result["percentage"] == 60.0
        assert len(result["review"]) == 5
        assert result["review"][0]["question"]["answer_keys"] == ["a"]

    async def test_stats_are_rolled_up_on_submit(self, client, admin, student, module_id):
        await _make_questions(client, admin, module_id, 4)
        paper = (
            await client.post(
                "/attempts", headers=student["headers"], json={"module_id": module_id, "count": 4}
            )
        ).json()
        await client.post(
            f"/attempts/{paper['id']}/submit",
            headers=student["headers"],
            json={
                "answers": [{"id": q["id"], "picked": ["a"]} for q in paper["questions"]],
                "duration_sec": 90,
            },
        )
        stats = (await client.get("/me/stats", headers=student["headers"])).json()
        assert stats["attempts_total"] == 1
        assert stats["questions_answered"] == 4
        assert stats["questions_correct"] == 4
        assert stats["accuracy"] == 100.0
        assert stats["current_streak"] == 1

    async def test_cannot_submit_twice(self, client, admin, student, module_id):
        await _make_questions(client, admin, module_id, 2)
        paper = (
            await client.post(
                "/attempts", headers=student["headers"], json={"module_id": module_id, "count": 2}
            )
        ).json()
        body = {"answers": [], "duration_sec": 10}
        first = await client.post(
            f"/attempts/{paper['id']}/submit", headers=student["headers"], json=body
        )
        assert first.status_code == 200
        second = await client.post(
            f"/attempts/{paper['id']}/submit", headers=student["headers"], json=body
        )
        assert second.status_code == 409

    async def test_cannot_read_another_students_attempt(self, client, admin, student, module_id):
        await _make_questions(client, admin, module_id, 2)
        paper = (
            await client.post(
                "/attempts", headers=student["headers"], json={"module_id": module_id, "count": 2}
            )
        ).json()

        other = await client.post(
            "/auth/register",
            json={
                "email": "other@example.pk",
                "password": "Kakul2026!",
                "full_name": "Other Candidate",
            },
        )
        headers = {"Authorization": f"Bearer {other.json()['tokens']['access_token']}"}
        response = await client.get(f"/attempts/{paper['id']}", headers=headers)
        assert response.status_code == 404

    async def test_empty_module_gives_a_clear_error(self, client, student, empty_module_id):
        response = await client.post(
            "/attempts",
            headers=student["headers"],
            json={"module_id": empty_module_id, "count": 10},
        )
        assert response.status_code == 409
        assert "no approved questions" in response.json()["detail"].lower()

    async def test_wrong_answers_are_tracked_for_revision(self, client, admin, student, module_id):
        await _make_questions(client, admin, module_id, 4)
        paper = (
            await client.post(
                "/attempts", headers=student["headers"], json={"module_id": module_id, "count": 4}
            )
        ).json()
        await client.post(
            f"/attempts/{paper['id']}/submit",
            headers=student["headers"],
            json={
                "answers": [{"id": q["id"], "picked": ["b"]} for q in paper["questions"]],
                "duration_sec": 60,
            },
        )
        dashboard = (await client.get("/me/dashboard", headers=student["headers"])).json()
        assert dashboard["stats"]["questions_correct"] == 0
        assert dashboard["recent_attempts"][0]["percentage"] == 0.0
