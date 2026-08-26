"""Answer-sheet upload, transcription alignment and PPDT."""

from __future__ import annotations

import pytest

from app.agents import ocr


class TestOcrFallback:
    def test_reports_its_own_absence(self):
        """The feature must work without the binary, and say so."""
        if ocr.available():
            pytest.skip("tesseract is installed here; the fallback path is not exercised")
        assert ocr.note()
        result = ocr.transcribe(b"whatever")
        assert result.engine == "none"
        assert result.lines == []

    def test_junk_bytes_do_not_raise(self):
        result = ocr.transcribe(b"\x00\x01\x02 not an image")
        assert result.lines == []

    def test_empty_upload_does_not_raise(self):
        assert ocr.transcribe(b"").lines == []


class TestAlignment:
    """Aligning transcribed lines to answer slots -- pure logic, always testable."""

    def _transcription(self, lines):
        return ocr.Transcription(
            lines=[ocr.Line(index=i, text=t, confidence=90.0) for i, t in lines]
        )

    def test_uses_the_numbers_the_candidate_wrote(self):
        transcription = self._transcription([(1, "duty first"), (3, "I helped him")])
        assert ocr.align(transcription, 4) == ["duty first", "", "I helped him", ""]

    def test_out_of_range_numbers_are_dropped_not_wrapped(self):
        transcription = self._transcription([(99, "stray line"), (2, "kept")])
        assert ocr.align(transcription, 3) == ["", "kept", ""]

    def test_unnumbered_lines_fill_in_reading_order(self):
        transcription = ocr.Transcription(
            lines=[ocr.Line(index=None, text=t) for t in ("first", "second")]
        )
        assert ocr.align(transcription, 3) == ["first", "second", ""]

    def test_never_mixes_numbered_and_positional_filling(self):
        """The dangerous case: a half-numbered sheet must not be guessed at.

        Filling the gaps positionally would attribute a line to the wrong
        stimulus, and the candidate could not tell from the result.
        """
        transcription = ocr.Transcription(
            lines=[
                ocr.Line(index=1, text="numbered one"),
                ocr.Line(index=None, text="loose line"),
            ]
        )
        assert ocr.align(transcription, 3) == ["numbered one", "", ""]

    def test_more_lines_than_slots_is_safe(self):
        transcription = self._transcription([(1, "a"), (2, "b"), (3, "c")])
        assert ocr.align(transcription, 2) == ["a", "b"]


class TestPpdtConsistency:
    """The proforma and the story must agree -- that is half the assessment."""

    def _check(self, perception, story):
        from app.services.issb_service import _ppdt_consistency

        return " ".join(_ppdt_consistency(perception, story))

    def test_action_absent_from_the_story_is_flagged(self):
        notes = self._check(
            {"characters": 1, "main_mood": "determined", "action": "organising a rescue party"},
            "He stood on the hill and thought about the weather for a long while afterwards.",
        )
        assert "never carries out the action" in notes

    def test_mood_contradicted_by_the_story_is_flagged(self):
        notes = self._check(
            {"characters": 1, "main_mood": "confident", "action": "rescue"},
            "He was afraid and hopeless, and the rescue seemed impossible to him.",
        )
        assert "opposite" in notes

    def test_extra_characters_who_never_appear_are_flagged(self):
        notes = self._check(
            {"characters": 4, "main_mood": "calm", "action": "climbing the slope"},
            "Climbing the slope steadily, he reached the top before dark and rested there calmly.",
        )
        assert "only the hero appears" in notes

    def test_a_short_story_is_flagged(self):
        notes = self._check({"characters": 1, "action": "helping"}, "He was helping.")
        assert "short for four minutes" in notes

    def test_a_consistent_story_passes(self):
        notes = self._check(
            {"characters": 2, "main_mood": "determined", "action": "organising the rescue"},
            "The village was cut off after the flood and the bridge had gone with it. "
            "Determined to reach the families on the far bank, he was organising the rescue "
            "within the hour. He divided his friends into two parties, sent one along the road "
            "for rope and a tractor, and led the other down to the water to look for a crossing. "
            "They found a shallow stretch below the mill and worked a line across it. By dusk "
            "they had carried the injured man to the road, and the doctor reached him in time. "
            "The villagers agreed to keep a watch on the water through the night.",
        )
        assert "consistent with the perception" in notes


class TestSheetSubmission:
    """The end-to-end paper route: transcribe, confirm, submit, analyse."""

    async def _sheet_items(self, client, headers, test_type="srt", count=4):
        response = await client.get(
            "/issb/psych/sheet", headers=headers, params={"test_type": test_type, "count": count}
        )
        assert response.status_code == 200, response.text
        return response.json()

    async def test_printable_sheet_carries_instructions(self, client, student, seeded):
        sheet = await self._sheet_items(client, student["headers"], "wat", 10)
        assert sheet["items"]
        assert sheet["instructions"], "a printed sheet must state how the test is run"
        assert sheet["seconds_per_item"] == 15
        assert all("model_answer" not in item for item in sheet["items"])

    async def test_transcribe_degrades_without_ocr(self, client, student, seeded):
        response = await client.post(
            "/issb/psych/transcribe",
            headers=student["headers"],
            files={"file": ("sheet.png", b"\x89PNG\r\n\x1a\n fake", "image/png")},
            data={"item_count": "5"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["item_count"] == 5
        assert len(body["slots"]) == 5
        # Without OCR the slots come back empty for the candidate to type into.
        if not body["available"]:
            assert body["note"]
            assert body["slots"] == ["", "", "", "", ""]

    async def test_rejects_a_non_image(self, client, student, seeded):
        response = await client.post(
            "/issb/psych/transcribe",
            headers=student["headers"],
            files={"file": ("notes.pdf", b"%PDF-1.4", "application/pdf")},
            data={"item_count": "5"},
        )
        assert response.status_code == 415

    async def test_rejects_an_empty_upload(self, client, student, seeded):
        response = await client.post(
            "/issb/psych/transcribe",
            headers=student["headers"],
            files={"file": ("sheet.png", b"", "image/png")},
            data={"item_count": "5"},
        )
        assert response.status_code == 400

    async def test_submitting_a_paper_sitting_is_analysed(self, client, student, seeded):
        sheet = await self._sheet_items(client, student["headers"], "srt", 4)
        item_ids = [item["id"] for item in sheet["items"]]

        response = await client.post(
            "/issb/psych/sheet",
            headers=student["headers"],
            json={
                "test_type": "srt",
                "item_ids": item_ids,
                "responses": [
                    "I informed the JCO, divided the party and cleared the route by 0900",
                    "He organised his team, briefed them quickly and finished the task safely",
                    "I helped the injured man and carried him to the vehicle",
                    "",
                ],
                "duration_sec": 120,
                "transcription": {"engine": "tesseract", "confidence": 62.0},
            },
        )
        assert response.status_code == 201, response.text
        result = response.json()
        assert result["answered_count"] == 3
        assert result["item_count"] == 4
        assert len(result["analysis"]["olq_scores"]) == 15
        # The read-out must say the words were transcribed, not typed on a clock.
        feedback = " ".join(result["analysis"]["feedback"]).lower()
        assert "transcribed" in feedback
        assert "62%" in feedback or "confident" in feedback

    async def test_a_blank_sheet_is_refused(self, client, student, seeded):
        sheet = await self._sheet_items(client, student["headers"], "srt", 3)
        response = await client.post(
            "/issb/psych/sheet",
            headers=student["headers"],
            json={
                "test_type": "srt",
                "item_ids": [i["id"] for i in sheet["items"]],
                "responses": ["", "  ", ""],
                "duration_sec": 60,
            },
        )
        assert response.status_code == 400

    async def test_items_from_another_test_are_refused(self, client, student, seeded):
        srt = await self._sheet_items(client, student["headers"], "srt", 2)
        wat = await self._sheet_items(client, student["headers"], "wat", 2)
        response = await client.post(
            "/issb/psych/sheet",
            headers=student["headers"],
            json={
                "test_type": "srt",
                "item_ids": [srt["items"][0]["id"], wat["items"][0]["id"]],
                "responses": ["one", "two"],
                "duration_sec": 60,
            },
        )
        assert response.status_code == 400


class TestPpdt:
    async def test_pictures_withhold_the_perception_hint(self, client, student, seeded):
        response = await client.get("/issb/ppdt/pictures", headers=student["headers"])
        assert response.status_code == 200
        pictures = response.json()
        assert pictures
        assert all("perception_hint" not in p for p in pictures)

    async def test_submission_returns_consistency_notes(self, client, student, seeded):
        pictures = (await client.get("/issb/ppdt/pictures", headers=student["headers"])).json()
        response = await client.post(
            "/issb/ppdt/submit",
            headers=student["headers"],
            json={
                "item_id": pictures[0]["id"],
                "perception": {
                    "characters": 3,
                    "main_age": 22,
                    "main_sex": "male",
                    "main_mood": "determined",
                    "action": "organising the rescue",
                },
                "story": "He was determined to reach them.",
                "duration_sec": 240,
            },
        )
        assert response.status_code == 201, response.text
        result = response.json()
        assert result["consistency"]
        assert result["item"]["perception_hint"], "the hint is revealed after submission"
        assert result["analysis"]["olq_scores"]


class TestOlqTrend:
    async def test_trend_is_oldest_first(self, client, student, seeded):
        for _ in range(2):
            session = (
                await client.post(
                    "/issb/psych/sessions",
                    headers=student["headers"],
                    json={"test_type": "wat", "count": 3},
                )
            ).json()
            await client.post(
                f"/issb/psych/sessions/{session['id']}/submit",
                headers=student["headers"],
                json={
                    "responses": [
                        {"item_id": i["id"], "text": "I helped my team finish the task", "ms": 5000}
                        for i in session["items"]
                    ],
                    "duration_sec": 40,
                },
            )

        trend = (await client.get("/issb/olq-trend", headers=student["headers"])).json()
        assert len(trend) == 2
        assert trend[0]["submitted_at"] <= trend[1]["submitted_at"]
        assert all(point["source"] == "online" for point in trend)
