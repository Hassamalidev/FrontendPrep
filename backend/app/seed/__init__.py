"""Idempotent database seeding.

Run it as often as you like: every row is matched on its natural key (service
code, module slug, item fingerprint) and updated rather than duplicated. That
matters because this is also how a deployed instance gets new catalog entries.

    python -m app.seed            # catalog + ISSB content + bootstrap admin
    python -m app.seed --reset    # drop and recreate first (local only)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.pipeline import fingerprint_text
from app.core.config import settings
from app.core.enums import ContentStatus, Difficulty, PsychTestType, Role, ServiceCode, UserStatus
from app.core.security import hash_password
from app.models.assessment import TestTemplate
from app.models.catalog import Module, Program, Service, Stage, Topic
from app.models.content import Article
from app.models.issb import GtoTask, InterviewQuestion, PsychItem
from app.models.user import User, UserStats
from app.seed import catalog_data as cd
from app.seed import issb_data as issb
from app.services import catalog_service

log = logging.getLogger("issb.seed")


def _now_utc() -> datetime:
    return datetime.now(UTC)


async def _upsert(db: AsyncSession, model, match: dict, values: dict, insert_only: dict | None = None):
    """Fetch by natural key, update in place, or insert. Returns the row.

    ``insert_only`` carries fields that must be set on creation but never
    overwritten afterwards -- primary keys for the fixed lookup tables, where a
    stable id is worth pinning rather than leaving to a sequence.
    """
    stmt = select(model)
    for field, value in match.items():
        stmt = stmt.where(getattr(model, field) == value)
    row = await db.scalar(stmt)

    if row is None:
        row = model(**match, **values, **(insert_only or {}))
        db.add(row)
        await db.flush()
        return row

    for field, value in values.items():
        setattr(row, field, value)
    return row


async def seed_services(db: AsyncSession) -> dict[str, Service]:
    out: dict[str, Service] = {}
    for entry in cd.SERVICES:
        data = dict(entry)
        code = data.pop("code")
        service_id = data.pop("id")
        # The initial test pattern differs by service; carrying it on the service
        # row is what lets the hub say *how* rather than just listing modules.
        if code in cd.TEST_PATTERNS:
            data["test_pattern"] = cd.TEST_PATTERNS[code]
        out[code] = await _upsert(
            db, Service, {"code": code}, data, insert_only={"id": service_id}
        )
    log.info("services: %d", len(out))
    return out


async def seed_stages(db: AsyncSession) -> dict[str, Stage]:
    out: dict[str, Stage] = {}
    for order, (stage_id, code, name, summary, icon, day_hint) in enumerate(cd.STAGES, start=1):
        out[code] = await _upsert(
            db,
            Stage,
            {"code": code},
            {
                "name": name,
                "summary": summary,
                "icon": icon,
                "day_hint": day_hint,
                "sort_order": order,
            },
            insert_only={"id": stage_id},
        )
    log.info("stages: %d", len(out))
    return out


async def seed_programs(db: AsyncSession) -> int:
    for entry in cd.PROGRAMS:
        data = dict(entry)
        slug = data.pop("slug")
        await _upsert(db, Program, {"slug": slug}, data)
    log.info("programs: %d", len(cd.PROGRAMS))
    return len(cd.PROGRAMS)


async def seed_modules(db: AsyncSession, services: dict, stages: dict) -> int:
    """Every service gets its own copy of the syllabus.

    Sharing one 'common' module across services would be smaller, but then a
    student browsing the Navy hub sees modules filed under a service that is not
    theirs. The duplication is a few dozen rows and the navigation is worth it.
    """
    count = 0
    for service_code in ("army", "air_force", "navy"):
        service = services[service_code]
        order = 0
        for group in (cd.COMMON_MODULES, cd.ISSB_MODULES):
            for slug, title, subtitle, icon, stage_code, topics in group:
                order += 1
                module = await _upsert(
                    db,
                    Module,
                    {"service_id": service.id, "slug": slug},
                    {
                        "stage_id": stages[stage_code].id,
                        "title": title,
                        "subtitle": subtitle,
                        "icon": icon,
                        "sort_order": order,
                        "is_active": True,
                    },
                )
                count += 1
                for topic_order, (topic_slug, topic_name, keywords) in enumerate(topics, start=1):
                    await _upsert(
                        db,
                        Topic,
                        {"module_id": module.id, "slug": topic_slug},
                        {"name": topic_name, "keywords": list(keywords), "sort_order": topic_order},
                    )
    log.info("modules: %d", count)
    return count


async def seed_psych_items(db: AsyncSession) -> int:
    """WAT, SCT, SRT and TAT stimuli, keyed by fingerprint so re-runs are free."""
    count = 0

    batches: list[tuple[PsychTestType, list, int, list[str]]] = [
        (PsychTestType.WAT, issb.WAT_WORDS, 15, ["power_of_expression", "self_confidence"]),
        (PsychTestType.SCT, issb.SCT_STEMS, 30, ["power_of_expression", "social_adaptability"]),
        (
            PsychTestType.SRT,
            issb.SRT_SITUATIONS,
            30,
            ["initiative", "speed_of_decision", "sense_of_responsibility", "organising_ability"],
        ),
    ]

    for test_type, prompts, seconds, olqs in batches:
        for order, prompt in enumerate(prompts, start=1):
            await _upsert(
                db,
                PsychItem,
                {"fingerprint": fingerprint_text(prompt, str(test_type))},
                {
                    "test_type": test_type,
                    "prompt": prompt,
                    "seconds": seconds,
                    "target_olqs": olqs,
                    "status": ContentStatus.APPROVED,
                    "difficulty": Difficulty.MEDIUM,
                    "sort_order": order,
                },
            )
            count += 1

    for order, prompt in enumerate(issb.SELF_DESCRIPTION_PROMPTS, start=1):
        await _upsert(
            db,
            PsychItem,
            {"fingerprint": fingerprint_text(prompt, "self_description")},
            {
                "test_type": PsychTestType.SELF_DESCRIPTION,
                "prompt": prompt,
                "seconds": 300,
                "target_olqs": ["social_adaptability", "sense_of_responsibility", "self_confidence"],
                "status": ContentStatus.APPROVED,
                "sort_order": order,
            },
        )
        count += 1

    for order, picture in enumerate(issb.PPDT_PICTURES, start=1):
        await _upsert(
            db,
            PsychItem,
            {"fingerprint": fingerprint_text(picture["prompt"], "ppdt")},
            {
                "test_type": PsychTestType.PPDT,
                "prompt": picture["prompt"],
                "perception_hint": picture["perception_hint"],
                # 30 seconds to perceive, four minutes to write.
                "seconds": 270,
                "target_olqs": ["effective_intelligence", "initiative", "organising_ability"],
                "status": ContentStatus.APPROVED,
                "sort_order": order,
            },
        )
        count += 1

    for order, slide in enumerate(issb.TAT_SLIDES, start=1):
        await _upsert(
            db,
            PsychItem,
            {"fingerprint": fingerprint_text(slide["prompt"], "tat")},
            {
                "test_type": PsychTestType.TAT,
                "prompt": slide["prompt"],
                "perception_hint": slide["perception_hint"],
                "seconds": 270,  # 30s to perceive, 4 minutes to write
                "target_olqs": ["effective_intelligence", "initiative", "determination"],
                "status": ContentStatus.APPROVED,
                "sort_order": order,
            },
        )
        count += 1

    log.info("psych items: %d", count)
    return count


async def seed_gto_tasks(db: AsyncSession) -> int:
    from app.core.enums import GTO_VENUE

    # Sort order runs indoor first, then outdoor, and within each half in the
    # order the series is actually conducted -- so the list reads as a schedule
    # rather than as whatever order the seed file happens to be in.
    order_within = {
        "group_discussion": 1, "lecturette": 2, "group_planning": 3,
        "progressive_group_task": 4, "half_group_task": 5, "individual_obstacles": 6,
        "command_task": 7, "snake_race": 8, "final_group_task": 9,
    }

    for task in issb.GTO_TASKS:
        data = dict(task)
        title = data.pop("title")
        task_type = data["task_type"]
        await _upsert(
            db,
            GtoTask,
            {"title": title},
            {
                **data,
                "venue": GTO_VENUE[task_type],
                "status": ContentStatus.APPROVED,
                "sort_order": order_within.get(task_type, 99),
            },
        )
    log.info("gto tasks: %d", len(issb.GTO_TASKS))
    return len(issb.GTO_TASKS)


async def seed_interview_questions(db: AsyncSession) -> int:
    for category, question, guidance in issb.INTERVIEW_QUESTIONS:
        await _upsert(
            db,
            InterviewQuestion,
            {"fingerprint": fingerprint_text(question, category)},
            {
                "category": category,
                "question": question,
                "guidance": guidance,
                "status": ContentStatus.APPROVED,
                "is_active": True,
            },
        )
    log.info("interview questions: %d", len(issb.INTERVIEW_QUESTIONS))
    return len(issb.INTERVIEW_QUESTIONS)


async def seed_test_templates(db: AsyncSession, services: dict, stages: dict) -> int:
    for entry in cd.TEST_TEMPLATES:
        data = dict(entry)
        slug = data.pop("slug")
        service_code = data.pop("service_code", None)
        stage_code = data.pop("stage_code", None)
        sections = data.pop("sections")

        await _upsert(
            db,
            TestTemplate,
            {"slug": slug},
            {
                **data,
                "sections": sections,
                "service_id": services[service_code].id if service_code else None,
                "stage_id": stages[stage_code].id if stage_code else None,
                "total_questions": sum(int(s.get("count", 0)) for s in sections),
                "status": ContentStatus.APPROVED,
            },
        )
    log.info("test templates: %d", len(cd.TEST_TEMPLATES))
    return len(cd.TEST_TEMPLATES)


async def seed_admin(db: AsyncSession) -> User:
    """Create the bootstrap super admin if it does not exist.

    An existing account is never re-passworded here -- a seed run must not
    silently reset a live administrator's credentials.
    """
    email = settings.BOOTSTRAP_ADMIN_EMAIL.lower().strip()
    user = await db.scalar(select(User).where(User.email == email))
    if user is not None:
        if user.role != Role.SUPER_ADMIN:
            user.role = Role.SUPER_ADMIN
            log.info("promoted existing account to super admin: %s", email)
        return user

    user = User(
        email=email,
        password_hash=hash_password(settings.BOOTSTRAP_ADMIN_PASSWORD),
        full_name=settings.BOOTSTRAP_ADMIN_NAME,
        role=Role.SUPER_ADMIN,
        status=UserStatus.ACTIVE,
        email_verified=True,
    )
    user.stats = UserStats()
    db.add(user)
    await db.flush()
    log.warning(
        "created bootstrap super admin %s -- change this password immediately", email
    )
    return user


async def seed_starter_questions(db: AsyncSession, admin: User) -> int:
    """Hand-written questions for the syllabus modules the generator cannot serve.

    The agent pipeline writes current-affairs questions from articles; it cannot
    invent an analogy or a figure series. Without these the seeded mock tests
    point at empty modules and cannot assemble a paper at all.
    """
    from app.core.enums import ContentStatus as CS
    from app.core.enums import Difficulty, Origin, QuestionType
    from app.models.catalog import Module
    from app.models.question import Question
    from app.seed.question_data import STARTER_QUESTIONS
    from app.services import question_service

    rows = (await db.execute(select(Module.id, Module.service_id, Module.slug))).all()
    by_slug: dict[str, list[tuple[int, int]]] = {}
    for module_id, service_id, slug in rows:
        by_slug.setdefault(slug, []).append((module_id, service_id))

    created = 0
    for slug, questions in STARTER_QUESTIONS.items():
        # One copy per slug, filed under the first service's module. Sampling
        # resolves siblings by slug, so all three services draw from it -- three
        # copies would triple the largest table for no extra information.
        for module_id, service_id in by_slug.get(slug, [])[:1]:
            for stem, choices, answer_key, explanation, difficulty in questions:
                options = [
                    {"key": key, "text": text}
                    for key, text in zip("abcd", choices, strict=False)
                ]
                fingerprint = question_service.fingerprint(stem, [answer_key], options)
                if await db.scalar(select(Question.id).where(Question.fingerprint == fingerprint)):
                    continue

                db.add(
                    Question(
                        service_id=service_id,
                        module_id=module_id,
                        qtype=QuestionType.MCQ,
                        stem=stem,
                        options=options,
                        answer_keys=[answer_key],
                        explanation=explanation,
                        difficulty=Difficulty(difficulty),
                        status=CS.APPROVED,
                        origin=Origin.HUMAN,
                        fingerprint=fingerprint,
                        reviewed_by_id=admin.id,
                        reviewed_at=_now_utc(),
                    )
                )
                created += 1
            await db.flush()

    log.info("starter questions: %d", created)
    return created


async def seed_demo_content(db: AsyncSession, admin: User) -> dict[str, int]:
    """Fill the question bank by running the real pipeline over sample articles.

    A fresh install otherwise has a complete catalog and zero questions, so every
    practice screen shows an empty state and the app looks broken. Generating the
    demo bank through the actual engine -- rather than inserting hand-written
    rows -- means what a new operator sees on day one is exactly what the
    generator produces, warts included.
    """
    from app.core.enums import ContentStatus as CS
    from app.models.catalog import Module, Service
    from app.schemas.content import ArticleIn, GenerateIn
    from app.seed.demo_data import DEMO_ARTICLES
    from app.services import content_service, generation_service

    # One current-affairs module per service, keyed by service code. An article
    # is filed under its own service so the demo bank is spread across the three
    # hubs rather than piling up under whichever service happened to be first.
    rows = (
        await db.execute(
            select(Module.id, Service.code)
            .join(Service, Service.id == Module.service_id)
            .where(Module.slug == "current-affairs")
        )
    ).all()
    module_by_service = {str(code): module_id for module_id, code in rows}
    if not module_by_service:
        log.warning("no current-affairs module found; skipping demo generation")
        return {}

    # Prefixed keys: the base seed already reports psych_items and
    # interview_questions, and merging these in unprefixed silently replaced
    # "142 seeded" with "16 generated" in the summary.
    report = {
        "demo_articles": 0,
        "demo_questions": 0,
        "demo_psych_items": 0,
        "demo_interview_questions": 0,
    }

    for entry in DEMO_ARTICLES:
        existing = await db.scalar(
            select(Article).where(Article.body_hash == content_service.body_hash(entry["body"]))
        )
        if existing is not None:
            continue  # already generated on a previous run

        article = await content_service.create_article(
            db,
            ArticleIn(
                title=entry["title"],
                body=entry["body"],
                category=entry["category"],
                service=entry["service"],
                source_name=entry["source_name"],
                status=CS.APPROVED,
            ),
            author=admin,
        )
        report["demo_articles"] += 1

        # A service-specific article goes to that service; a general one goes to
        # the army module, which is the busiest hub.
        target = module_by_service.get(str(entry["service"] or "army")) or next(
            iter(module_by_service.values())
        )

        # Approve automatically: this is demo content, and leaving forty drafts
        # in the review queue would defeat the point of seeding it.
        result = await generation_service.generate(
            db,
            article,
            # Deliberately small. This exists to show the generator works, not
            # to fill the bank -- and every row here is one a student never asked
            # for on a database budget they are sharing with their own attempts.
            GenerateIn(
                mcq=3,
                true_false=1,
                fill_blank=1,
                sct=1,
                srt=1,
                interview=1,
                module_id=target,
                auto_approve=True,
            ),
            actor=admin,
        )
        report["demo_questions"] += len(result["questions"])
        report["demo_psych_items"] += len(result["psych_items"])
        report["demo_interview_questions"] += len(result["interview_questions"])

    log.info(
        "demo content: %d article(s), %d question(s)", report["demo_articles"], report["demo_questions"]
    )
    return report


async def seed_demo_student(db: AsyncSession) -> User | None:
    """A ready-made student account, so the app can be tried without signing up.

    Only created when demo access is enabled, which is never the case on a
    production deployment.
    """
    if not settings.demo_enabled:
        return None

    email = settings.DEMO_STUDENT_EMAIL.lower().strip()
    existing = await db.scalar(select(User).where(User.email == email))
    if existing is not None:
        return existing

    user = User(
        email=email,
        password_hash=hash_password(settings.DEMO_STUDENT_PASSWORD),
        full_name=settings.DEMO_STUDENT_NAME,
        role=Role.STUDENT,
        status=UserStatus.ACTIVE,
        email_verified=True,
        target_service=ServiceCode.ARMY,
        city="Rawalpindi",
    )
    user.stats = UserStats()
    db.add(user)
    await db.flush()
    log.info("demo student available: %s", email)
    return user


async def run(db: AsyncSession, *, demo: bool = False) -> dict[str, int]:
    """Seed everything, in dependency order."""
    services = await seed_services(db)
    stages = await seed_stages(db)
    await db.flush()

    report = {
        "services": len(services),
        "stages": len(stages),
        "programs": await seed_programs(db),
        "modules": await seed_modules(db, services, stages),
        "psych_items": await seed_psych_items(db),
        "gto_tasks": await seed_gto_tasks(db),
        "interview_questions": await seed_interview_questions(db),
        "test_templates": await seed_test_templates(db, services, stages),
    }
    admin = await seed_admin(db)
    await seed_demo_student(db)
    await db.flush()

    # The starter bank is part of the base seed, not the demo: a fresh install
    # with an empty question bank looks broken on every practice screen. It is
    # deliberately small -- one copy per question, shared across all three
    # services -- because the database budget is shared with the student's own
    # attempts.
    report["starter_questions"] = await seed_starter_questions(db, admin)

    if demo:
        # --demo additionally demonstrates the generator by running it over a
        # few sample articles. Those articles are the only ones ever stored.
        report.update(await seed_demo_content(db, admin))

    await catalog_service.refresh_question_counts(db)
    return report
