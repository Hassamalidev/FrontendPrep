"""The ISSB simulation suite, end to end against seeded content."""

from __future__ import annotations

STRONG_SRT = (
    "I informed the JCO, divided the party in two and cleared the route by 0900"
)
WEAK_SRT = "I would feel worried and maybe try again later"


class TestPsychSessions:
    async def test_wat_sitting_full_cycle(self, client, student, seeded):
        start = await client.post(
            "/issb/psych/sessions",
            headers=student["headers"],
            json={"test_type": "wat", "count": 10},
        )
        assert start.status_code == 201, start.text
        session = start.json()
        assert session["item_count"] == 10
        assert len(session["items"]) == 10
        assert session["total_seconds"] == 10 * 15

        # Items must not leak the model answer while the clock is running.
        assert all("model_answer" not in item for item in session["items"])

        submit = await client.post(
            f"/issb/psych/sessions/{session['id']}/submit",
            headers=student["headers"],
            json={
                "responses": [
                    {"item_id": item["id"], "text": "I work hard and help my team", "ms": 6000}
                    for item in session["items"]
                ],
                "duration_sec": 90,
            },
        )
        assert submit.status_code == 200, submit.text
        result = submit.json()
        assert result["answered_count"] == 10
        assert result["analysis"]["overall_score"] > 0
        assert len(result["analysis"]["olq_scores"]) == 15
        assert result["analysis"]["feedback"]
        assert len(result["responses"]) == 10
        # Review mode may now show the guidance.
        assert "model_answer" in result["responses"][0]["item"]

    async def test_srt_quality_moves_the_score(self, client, student, seeded):
        scores = {}
        for label, text in (("strong", STRONG_SRT), ("weak", WEAK_SRT)):
            session = (
                await client.post(
                    "/issb/psych/sessions",
                    headers=student["headers"],
                    json={"test_type": "srt", "count": 8},
                )
            ).json()
            result = (
                await client.post(
                    f"/issb/psych/sessions/{session['id']}/submit",
                    headers=student["headers"],
                    json={
                        "responses": [
                            {"item_id": i["id"], "text": text, "ms": 9000}
                            for i in session["items"]
                        ],
                        "duration_sec": 120,
                    },
                )
            ).json()
            scores[label] = result["analysis"]["overall_score"]

        assert scores["strong"] > scores["weak"] + 10

    async def test_skipped_items_are_called_out(self, client, student, seeded):
        session = (
            await client.post(
                "/issb/psych/sessions",
                headers=student["headers"],
                json={"test_type": "sct", "count": 6},
            )
        ).json()
        result = (
            await client.post(
                f"/issb/psych/sessions/{session['id']}/submit",
                headers=student["headers"],
                json={
                    "responses": [
                        {"item_id": session["items"][0]["id"], "text": "I will finish the task"}
                    ],
                    "duration_sec": 30,
                },
            )
        ).json()
        assert result["answered_count"] == 1
        assert any("blank" in note for note in result["analysis"]["feedback"])

    async def test_cannot_submit_twice(self, client, student, seeded):
        session = (
            await client.post(
                "/issb/psych/sessions",
                headers=student["headers"],
                json={"test_type": "wat", "count": 5},
            )
        ).json()
        body = {"responses": [], "duration_sec": 10}
        first = await client.post(
            f"/issb/psych/sessions/{session['id']}/submit", headers=student["headers"], json=body
        )
        assert first.status_code == 200
        second = await client.post(
            f"/issb/psych/sessions/{session['id']}/submit", headers=student["headers"], json=body
        )
        assert second.status_code == 409

    async def test_sessions_are_private(self, client, student, seeded):
        session = (
            await client.post(
                "/issb/psych/sessions",
                headers=student["headers"],
                json={"test_type": "wat", "count": 5},
            )
        ).json()
        other = await client.post(
            "/auth/register",
            json={"email": "b@example.pk", "password": "Kakul2026!", "full_name": "Other"},
        )
        headers = {"Authorization": f"Bearer {other.json()['tokens']['access_token']}"}
        response = await client.get(f"/issb/psych/sessions/{session['id']}", headers=headers)
        assert response.status_code == 404


class TestGto:
    async def test_task_brief_withholds_the_model_solution(self, client, student, seeded):
        tasks = (await client.get("/issb/gto/tasks", headers=student["headers"])).json()
        assert tasks["total"] >= 4
        task = tasks["items"][0]
        assert "model_solution" not in task
        assert "rubric" not in task

        detail = await client.get(f"/issb/gto/tasks/{task['id']}", headers=student["headers"])
        assert "model_solution" not in detail.json()

    async def test_submitting_a_plan_returns_the_solution_and_rubric_gaps(
        self, client, student, seeded
    ):
        tasks = (
            await client.get(
                "/issb/gto/tasks", headers=student["headers"], params={"task_type": "group_planning"}
            )
        ).json()
        task_id = tasks["items"][0]["id"]

        response = await client.post(
            f"/issb/gto/tasks/{task_id}/submit",
            headers=student["headers"],
            json={
                "body": (
                    "First I will divide the group into three parties.\n"
                    "Party A searches the canal bank for the child with torches.\n"
                    "Party B takes the injured man by jeep on the eastern route.\n"
                    "Party C moves the relief stock and posts a guard."
                ),
                "duration_sec": 240,
            },
        )
        assert response.status_code == 201, response.text
        result = response.json()
        assert result["task"]["model_solution"]
        assert result["task"]["rubric"]
        assert result["analysis"]["olq_scores"]
        assert result["analysis"]["overall_score"] > 0

    async def test_a_vague_plan_is_told_what_it_missed(self, client, student, seeded):
        tasks = (
            await client.get(
                "/issb/gto/tasks", headers=student["headers"], params={"task_type": "group_planning"}
            )
        ).json()
        task_id = tasks["items"][0]["id"]

        result = (
            await client.post(
                f"/issb/gto/tasks/{task_id}/submit",
                headers=student["headers"],
                json={"body": "I will try to help everyone as much as possible.", "duration_sec": 60},
            )
        ).json()
        feedback = " ".join(result["analysis"]["feedback"]).lower()
        assert "rubric" in feedback or "constraint" in feedback


class TestInterview:
    async def test_full_cycle(self, client, student, seeded):
        start = await client.post(
            "/issb/interview/sessions", headers=student["headers"], json={"count": 6}
        )
        assert start.status_code == 201, start.text
        session = start.json()
        assert len(session["questions"]) == 6
        # Guidance is coaching, not something to read while answering.
        assert all("guidance" not in q for q in session["questions"])

        submit = await client.post(
            f"/issb/interview/sessions/{session['id']}/submit",
            headers=student["headers"],
            json={
                "exchanges": [
                    {
                        "question_id": q["id"],
                        "answer": "I organised my college team, briefed them and we finished first.",
                        "ms": 30000,
                    }
                    for q in session["questions"]
                ],
                "duration_sec": 400,
            },
        )
        assert submit.status_code == 200, submit.text
        result = submit.json()
        assert len(result["exchanges"]) == 6
        assert result["exchanges"][0]["question"]["guidance"]
        assert result["analysis"]["overall_score"] > 0

    async def test_questions_are_ordered_outward_from_the_candidate(self, client, student, seeded):
        session = (
            await client.post(
                "/issb/interview/sessions", headers=student["headers"], json={"count": 20}
            )
        ).json()
        order = {
            "personal": 0, "family": 1, "academic": 2, "hobbies": 3,
            "current_affairs": 4, "defence": 5, "religion": 6, "situational": 7,
        }
        ranks = [order.get(q["category"], 9) for q in session["questions"]]
        assert ranks == sorted(ranks)


class TestOlqProfile:
    async def test_accumulates_across_sittings(self, client, student, seeded):
        empty = (await client.get("/issb/olq-profile", headers=student["headers"])).json()
        assert empty["sessions_counted"] == 0

        for _ in range(2):
            session = (
                await client.post(
                    "/issb/psych/sessions",
                    headers=student["headers"],
                    json={"test_type": "srt", "count": 5},
                )
            ).json()
            await client.post(
                f"/issb/psych/sessions/{session['id']}/submit",
                headers=student["headers"],
                json={
                    "responses": [
                        {"item_id": i["id"], "text": STRONG_SRT, "ms": 9000}
                        for i in session["items"]
                    ],
                    "duration_sec": 60,
                },
            )

        profile = (await client.get("/issb/olq-profile", headers=student["headers"])).json()
        assert profile["sessions_counted"] == 2
        assert len(profile["scores"]) == 15
        assert profile["strongest"] and profile["weakest"]
        assert all(1.0 <= entry["score"] <= 5.0 for entry in profile["scores"])


class TestServiceScoping:
    """Shared content (service = NULL) must survive a service filter.

    ``column.in_([value, None])`` renders as ``IN (value, NULL)``, which never
    matches a NULL row -- so filtering by service used to hide every item that
    applies to all three services.
    """

    async def test_interview_questions_survive_a_service_filter(self, client, student, seeded):
        response = await client.post(
            "/issb/interview/sessions",
            headers=student["headers"],
            json={"service": "navy", "count": 5},
        )
        assert response.status_code == 201, response.text
        assert len(response.json()["questions"]) == 5

    async def test_gto_tasks_survive_a_service_filter(self, client, student, seeded):
        response = await client.get(
            "/issb/gto/tasks", headers=student["headers"], params={"service": "air_force"}
        )
        assert response.status_code == 200
        assert response.json()["total"] >= 4

    async def test_announcements_survive_a_service_filter(self, client, seeded):
        response = await client.get("/announcements", params={"service": "army"})
        assert response.status_code == 200


class TestGtoVenues:
    """The series splits in two, and candidates prepare for the halves differently."""

    async def test_every_task_is_classified(self, client, student, seeded):
        response = await client.get(
            "/issb/gto/tasks", headers=student["headers"], params={"size": 50}
        )
        assert response.status_code == 200
        tasks = response.json()["items"]
        assert tasks
        assert all(task["venue"] in {"indoor", "outdoor"} for task in tasks)

    async def test_indoor_is_the_verbal_half(self, client, student, seeded):
        response = await client.get(
            "/issb/gto/tasks", headers=student["headers"], params={"venue": "indoor", "size": 50}
        )
        kinds = {task["task_type"] for task in response.json()["items"]}
        assert kinds <= {"group_discussion", "lecturette", "group_planning"}
        assert "group_discussion" in kinds

    async def test_outdoor_is_the_physical_half(self, client, student, seeded):
        response = await client.get(
            "/issb/gto/tasks", headers=student["headers"], params={"venue": "outdoor", "size": 50}
        )
        kinds = {task["task_type"] for task in response.json()["items"]}
        assert "progressive_group_task" in kinds
        assert "individual_obstacles" in kinds
        assert not kinds & {"group_discussion", "lecturette", "group_planning"}

    async def test_the_two_halves_partition_the_series(self, client, student, seeded):
        both = await client.get(
            "/issb/gto/tasks", headers=student["headers"], params={"size": 50}
        )
        indoor = await client.get(
            "/issb/gto/tasks", headers=student["headers"], params={"venue": "indoor", "size": 50}
        )
        outdoor = await client.get(
            "/issb/gto/tasks", headers=student["headers"], params={"venue": "outdoor", "size": 50}
        )
        assert indoor.json()["total"] + outdoor.json()["total"] == both.json()["total"]
        assert indoor.json()["total"] >= 3
        assert outdoor.json()["total"] >= 6

    async def test_tasks_are_listed_in_the_order_they_are_conducted(self, client, student, seeded):
        response = await client.get(
            "/issb/gto/tasks", headers=student["headers"], params={"size": 50}
        )
        order = [task["task_type"] for task in response.json()["items"]]
        # Group discussion opens the series; the final group task closes it.
        assert order.index("group_discussion") < order.index("progressive_group_task")
        assert order.index("final_group_task") == len(order) - 1

    async def test_an_outdoor_brief_still_withholds_its_solution(self, client, student, seeded):
        tasks = (
            await client.get(
                "/issb/gto/tasks",
                headers=student["headers"],
                params={"venue": "outdoor", "size": 50},
            )
        ).json()["items"]
        detail = await client.get(
            f"/issb/gto/tasks/{tasks[0]['id']}", headers=student["headers"]
        )
        assert "model_solution" not in detail.json()
        assert detail.json()["venue"] == "outdoor"
