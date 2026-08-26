"""The generation console: article in, reviewable questions out."""

from __future__ import annotations

import pytest

ARTICLE_BODY = """
Pakistan Navy commissioned PNS Hangor at Karachi on 25 June 2024, marking the delivery of the
first of eight Hangor-class submarines. The submarine was built under an agreement worth
5 billion dollars signed in 2015 between Pakistan and China. Admiral Naveed Ashraf is the Chief
of Naval Staff of Pakistan. The vessel can remain submerged for 30 days and carries a crew of
38 sailors. The Ministry of Defence said the programme will create 2,500 jobs in the domestic
shipbuilding sector. The Hangor class displaces 2,800 tonnes and has a range of 12,000
kilometres. Naval officials stated that the class will replace the ageing Agosta 90B fleet
by 2030.
"""


@pytest.fixture
async def article_id(client, admin) -> int:
    response = await client.post(
        "/admin/articles",
        headers=admin["headers"],
        json={
            "title": "Pakistan Navy commissions PNS Hangor",
            "body": ARTICLE_BODY,
            "category": "defence",
            "service": "navy",
            "status": "approved",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


class TestEngineStatus:
    async def test_reports_the_live_backend(self, client, admin):
        response = await client.get("/agent/status", headers=admin["headers"])
        assert response.status_code == 200
        body = response.json()
        assert body["engine"] in {"rules", "spacy"}
        assert body["uses_external_api"] is False

    async def test_students_cannot_see_it(self, client, student, seeded):
        response = await client.get("/agent/status", headers=student["headers"])
        assert response.status_code == 403


class TestArticles:
    async def test_duplicate_body_is_detected(self, client, admin, article_id):
        response = await client.post(
            "/admin/articles",
            headers=admin["headers"],
            json={"title": "A different headline entirely", "body": ARTICLE_BODY},
        )
        assert response.status_code == 409
        assert str(article_id) in response.json()["detail"]

    async def test_unpublished_articles_are_not_public(self, client, admin):
        created = await client.post(
            "/admin/articles",
            headers=admin["headers"],
            json={"title": "Draft piece", "body": ARTICLE_BODY.replace("Hangor", "Tughril")},
        )
        slug = created.json()["slug"]
        assert (await client.get(f"/articles/{slug}")).status_code == 404


class TestGeneration:
    async def test_dry_run_writes_nothing(self, client, admin, article_id):
        before = (await client.get("/admin/questions", headers=admin["headers"])).json()["total"]
        response = await client.post(
            f"/agent/articles/{article_id}/generate",
            headers=admin["headers"],
            json={"mcq": 5, "true_false": 2, "dry_run": True},
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["persisted"] is False
        assert body["questions"]

        bank = await client.get("/admin/questions", headers=admin["headers"])
        assert bank.json()["total"] == before, "a dry run must not add anything"

    async def test_generates_into_the_review_queue(self, client, admin, article_id):
        response = await client.post(
            f"/agent/articles/{article_id}/generate",
            headers=admin["headers"],
            json={"mcq": 5, "true_false": 3, "fill_blank": 2},
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["persisted"] is True
        assert body["run"]["status"] in {"succeeded", "partial"}
        assert body["run"]["facts_found"] > 0
        assert body["run"]["accepted"] > 0

        # Drafts, not live questions -- a human decides.
        queue = (await client.get("/admin/questions/queue", headers=admin["headers"])).json()
        assert queue["total"] == body["run"]["accepted"]
        assert all(q["status"] == "draft" for q in queue["items"])
        assert all(q["origin"] == "agent" for q in queue["items"])
        assert all(q["source_article_id"] == article_id for q in queue["items"])

        # Nothing *generated* is visible to students yet -- the seeded starter
        # bank is, which is the point of shipping one.
        public = (await client.get("/questions")).json()
        assert all(item["id"] not in {q["id"] for q in queue["items"]} for item in public["items"])

    async def test_the_trace_explains_the_run(self, client, admin, article_id):
        body = (
            await client.post(
                f"/agent/articles/{article_id}/generate",
                headers=admin["headers"],
                json={"mcq": 4},
            )
        ).json()
        agents = [step["agent"] for step in body["run"]["trace"]]
        assert agents[:3] == ["extract", "summarise", "write"]
        assert "critique" in agents
        assert body["run"]["duration_ms"] >= 0

    async def test_rerunning_produces_no_duplicates(self, client, admin, article_id):
        config = {"mcq": 5, "true_false": 3}
        first = (
            await client.post(
                f"/agent/articles/{article_id}/generate", headers=admin["headers"], json=config
            )
        ).json()
        second = (
            await client.post(
                f"/agent/articles/{article_id}/generate", headers=admin["headers"], json=config
            )
        ).json()

        assert first["run"]["accepted"] > 0
        assert second["run"]["accepted"] == 0
        assert second["run"]["duplicates"] > 0

        queue = (await client.get("/admin/questions/queue", headers=admin["headers"])).json()
        assert queue["total"] == first["run"]["accepted"]

    async def test_approving_publishes_to_students(self, client, admin, student, article_id):
        before = (await client.get("/questions")).json()["total"]
        await client.post(
            f"/agent/articles/{article_id}/generate",
            headers=admin["headers"],
            json={"mcq": 5},
        )
        queue = (await client.get("/admin/questions/queue", headers=admin["headers"])).json()
        ids = [q["id"] for q in queue["items"]]

        approve = await client.post(
            "/admin/questions/review",
            headers=admin["headers"],
            json={"ids": ids, "status": "approved", "note": "Checked against the source."},
        )
        assert approve.status_code == 200

        public = (await client.get("/questions")).json()
        assert public["total"] == before + len(ids)
        assert all("answer_keys" not in item for item in public["items"])

    async def test_generates_issb_items_too(self, client, admin, article_id):
        body = (
            await client.post(
                f"/agent/articles/{article_id}/generate",
                headers=admin["headers"],
                json={"mcq": 2, "sct": 3, "srt": 3, "interview": 2},
            )
        ).json()
        assert len(body["psych_items"]) == 6
        assert len(body["interview_questions"]) == 2
        assert {i["test_type"] for i in body["psych_items"]} == {"sct", "srt"}

    async def test_preview_needs_no_article(self, client, admin):
        response = await client.post(
            "/agent/preview",
            headers=admin["headers"],
            json={"text": ARTICLE_BODY, "mcq": 4},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["persisted"] is False
        assert body["questions"]
        assert (await client.get("/agent/runs", headers=admin["headers"])).json()["total"] == 0

    async def test_short_article_fails_cleanly(self, client, admin):
        created = await client.post(
            "/admin/articles",
            headers=admin["headers"],
            json={"title": "Too brief", "body": "One short sentence about nothing much at all."},
        )
        response = await client.post(
            f"/agent/articles/{created.json()['id']}/generate",
            headers=admin["headers"],
            json={"mcq": 5},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["run"]["status"] == "failed"
        assert "too short" in body["run"]["error"].lower()
        assert body["questions"] == []

    async def test_only_super_admins_may_generate(self, client, student, seeded, admin):
        created = await client.post(
            "/admin/articles",
            headers=admin["headers"],
            json={"title": "Another piece", "body": ARTICLE_BODY.replace("Navy", "Force")},
        )
        response = await client.post(
            f"/agent/articles/{created.json()['id']}/generate",
            headers=student["headers"],
            json={"mcq": 3},
        )
        assert response.status_code == 403


class TestNewsIngestion:
    """Reading public RSS feeds -- parsing and storage, without the network."""

    RSS = """<?xml version="1.0"?>
    <rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
      <channel>
        <item>
          <title>Pakistan Navy commissions new frigate at Karachi</title>
          <link>https://example.pk/story-1</link>
          <pubDate>Wed, 26 Aug 2026 08:00:00 +0500</pubDate>
          <description>The ship joins the fleet after trials.</description>
          <content:encoded><![CDATA[<p>The Pakistan Navy commissioned a new frigate at
          Karachi on 26 August 2026. The vessel displaces 4,000 tonnes and carries a crew
          of 200 sailors. The contract was worth 500 million dollars and was signed in
          2021. Officials said two more ships follow by 2028.</p>]]></content:encoded>
        </item>
        <item>
          <title>Short item</title>
          <link>https://example.pk/story-2</link>
          <description>Too short to generate from.</description>
        </item>
      </channel>
    </rss>"""

    def test_parses_rss_with_dates_and_bodies(self):
        from app.services import news_service

        items = news_service.parse_feed(self.RSS, "Example")
        assert len(items) == 2
        first = items[0]
        assert first.title.startswith("Pakistan Navy commissions")
        assert first.source == "Example"
        assert first.published is not None
        assert first.published.year == 2026
        # content:encoded is richer than the description, so it wins.
        assert "4,000 tonnes" in first.text
        assert "<p>" not in first.text, "markup must be stripped"

    def test_parses_atom(self):
        from app.services import news_service

        atom = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <title>An atom headline</title>
            <link href="https://example.pk/a"/>
            <published>2026-08-26T08:00:00Z</published>
            <summary>Some summary text for the entry.</summary>
          </entry>
        </feed>"""
        items = news_service.parse_feed(atom, "Atom Source")
        assert len(items) == 1
        assert items[0].title == "An atom headline"
        assert items[0].link == "https://example.pk/a"

    def test_malformed_xml_returns_nothing_rather_than_raising(self):
        from app.services import news_service

        assert news_service.parse_feed("<rss><channel><item>", "Broken") == []
        assert news_service.parse_feed("", "Empty") == []

    def test_recency_window_excludes_old_stories(self):
        from datetime import UTC, datetime, timedelta

        from app.services.news_service import FeedItem, _within_window

        fresh = FeedItem("t", "s", "l", "src", datetime.now(UTC) - timedelta(days=2))
        stale = FeedItem("t", "s", "l", "src", datetime.now(UTC) - timedelta(days=40))
        undated = FeedItem("t", "s", "l", "src", None)

        assert _within_window(fresh, 7)
        assert not _within_window(stale, 7)
        assert _within_window(undated, 7), "undated items are usually the newest"


class TestDemoAccess:
    async def test_demo_accounts_are_offered_and_work(self, client, seeded):
        response = await client.get("/auth/demo")
        assert response.status_code == 200
        body = response.json()
        assert body["enabled"] is True
        assert len(body["accounts"]) == 2

        for account in body["accounts"]:
            login = await client.post(
                "/auth/login", json={"email": account["email"], "password": account["password"]}
            )
            assert login.status_code == 200, f"{account['label']} could not sign in"

        roles = set()
        for account in body["accounts"]:
            login = await client.post(
                "/auth/login", json={"email": account["email"], "password": account["password"]}
            )
            roles.add(login.json()["user"]["role"])
        assert "student" in roles and "super_admin" in roles

    async def test_production_never_advertises_credentials(self, client, seeded, monkeypatch):
        """The guard is environment *and* flag, so a forgotten flag is not enough."""
        from app.core.config import settings

        monkeypatch.setattr(settings, "ENV", "production")
        response = await client.get("/auth/demo")
        assert response.json() == {"enabled": False, "accounts": []}


class TestServicePatterns:
    """The three services differ, and the platform has to say how."""

    async def test_each_service_carries_its_own_pattern(self, client, seeded):
        patterns = {}
        for code in ("army", "air_force", "navy"):
            response = await client.get(f"/catalog/services/{code}")
            assert response.status_code == 200
            patterns[code] = response.json()["service"]["test_pattern"]

        assert all(p.get("sections") for p in patterns.values())
        # They must not be identical -- that was the complaint.
        shapes = {code: [s["name"] for s in p["sections"]] for code, p in patterns.items()}
        assert shapes["army"] != shapes["air_force"] != shapes["navy"]

    async def test_paf_has_physics_and_no_general_knowledge(self, client, seeded):
        pattern = (await client.get("/catalog/services/air_force")).json()["service"]["test_pattern"]
        names = " ".join(s["name"] for s in pattern["sections"]).lower()
        assert "physics" in names
        assert "general knowledge" not in names

    async def test_army_tests_general_knowledge_and_islamiat(self, client, seeded):
        pattern = (await client.get("/catalog/services/army")).json()["service"]["test_pattern"]
        covers = " ".join(
            " ".join(s.get("covers", [])) for s in pattern["sections"]
        ).lower()
        assert "general knowledge" in covers
        assert "islamiat" in covers

    async def test_navy_intelligence_is_weighted_to_non_verbal(self, client, seeded):
        pattern = (await client.get("/catalog/services/navy")).json()["service"]["test_pattern"]
        intelligence = next(s for s in pattern["sections"] if "Intelligence" in s["name"])
        assert intelligence["split"]["non_verbal"] > intelligence["split"]["verbal"] * 2

    async def test_mock_tests_follow_their_service_pattern(self, client, seeded):
        tests = (await client.get("/tests")).json()
        paf = next(t for t in tests if t["slug"] == "paf-gd-pilot-mock")
        army = next(t for t in tests if t["slug"] == "army-initial-test-mock")

        paf_modules = {s["module_slug"] for s in paf["sections"]}
        army_modules = {s["module_slug"] for s in army["sections"]}
        assert "physics" in paf_modules
        assert "general-knowledge" not in paf_modules
        assert "general-knowledge" in army_modules
        assert "islamiat" in army_modules


class TestDatabaseFrugality:
    """The free tier is the constraint, so these are correctness tests.

    A student shares 0.5 GB between the seed, their own attempts and every story
    the platform has ever seen. Anything stored that nobody re-reads is taking
    space from something that matters.
    """

    def _story(self, news_service, title, source, link, body):
        return news_service.FeedItem(
            title=title, summary="", link=link, source=source, published=None, body=body
        )

    async def test_reading_the_news_writes_nothing(self, client, db, seeded, monkeypatch):
        from sqlalchemy import func, select

        from app.models.content import Article
        from app.services import news_service

        async def fake(days=None, limit=None):
            return [self._story(
                news_service, "A headline", "Example", "https://example.pk/a",
                "Pakistan Navy commissioned a frigate at Karachi on 26 August 2026. "
                "The vessel displaces 4,000 tonnes and carries a crew of 200 sailors.",
            )]

        monkeypatch.setattr(news_service, "live_items", fake)

        before = await db.scalar(select(func.count()).select_from(Article))
        response = await client.get("/news")
        assert response.status_code == 200
        assert response.json()["stored"] is False
        assert response.json()["items"]
        after = await db.scalar(select(func.count()).select_from(Article))
        assert after == before, "reading the news must not write to the database"

    async def test_generating_keeps_questions_not_stories(
        self, client, db, admin, seeded, monkeypatch
    ):
        from sqlalchemy import func, select

        from app.models.content import AgentRun, Article
        from app.models.question import Question
        from app.services import news_service

        async def fake(days=None, limit=None):
            return [self._story(
                news_service, "PAF inducts new radar systems", "Example Post",
                "https://example.pk/b",
                "Pakistan Air Force inducted three long-range radar systems at Sargodha on "
                "12 March 2024. The systems were procured under a contract worth 250 million "
                "dollars signed in 2021. Each radar tracks targets at a range of 450 "
                "kilometres. The Ministry of Defence said it covers 80 percent of the corridor.",
            )]

        monkeypatch.setattr(news_service, "live_items", fake)

        articles = await db.scalar(select(func.count()).select_from(Article))
        runs = await db.scalar(select(func.count()).select_from(AgentRun))
        questions = await db.scalar(select(func.count()).select_from(Question))

        response = await client.post("/admin/news/generate", headers=admin["headers"])
        assert response.status_code == 200, response.text
        assert response.json()["articles_stored"] == 0
        assert response.json()["questions_drafted"] > 0

        assert await db.scalar(select(func.count()).select_from(Article)) == articles
        assert await db.scalar(select(func.count()).select_from(AgentRun)) == runs
        assert await db.scalar(select(func.count()).select_from(Question)) > questions

        # Provenance survives on the question, without an article to point at.
        newest = await db.scalar(
            select(Question).where(Question.origin == "agent").order_by(Question.id.desc())
        )
        assert newest.source_article_id is None
        provenance = (newest.generation_meta or {}).get("provenance", {})
        assert provenance.get("source") == "Example Post"

    async def test_a_syllabus_question_is_stored_once_for_all_services(self, db, seeded):
        from sqlalchemy import func, select

        from app.models.catalog import Module
        from app.models.question import Question

        modules = list(
            await db.scalars(select(Module).where(Module.slug == "verbal-intelligence"))
        )
        assert len(modules) == 3, "one module row per service"

        counts = {m.approved_question_count for m in modules}
        assert len(counts) == 1, "every service must report the same count"
        visible = counts.pop()
        assert visible > 0

        stored = await db.scalar(
            select(func.count())
            .select_from(Question)
            .where(Question.module_id.in_([m.id for m in modules]))
        )
        assert stored == visible, "stored once, visible to all three"

    async def test_every_service_can_still_draw_a_drill(self, client, student, seeded):
        for service_id in (1, 2, 3):
            modules = (
                await client.get("/catalog/modules", params={"service_id": service_id})
            ).json()
            verbal = next(m for m in modules if m["slug"] == "verbal-intelligence")
            assert verbal["approved_question_count"] > 0

            response = await client.post(
                "/attempts",
                headers=student["headers"],
                json={"module_id": verbal["id"], "count": 5, "mode": "module"},
            )
            assert response.status_code == 201, f"service {service_id}: {response.text}"
            assert response.json()["questions"], f"service {service_id} drew nothing"
            await client.post(
                f"/attempts/{response.json()['id']}/abandon", headers=student["headers"]
            )
