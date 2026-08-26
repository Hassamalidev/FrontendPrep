"""Shared vocabulary for the ISSB domain.

Stored as VARCHAR + CHECK (``native_enum=False``) rather than PG ENUM types:
adding a value then costs one constraint swap instead of an ``ALTER TYPE``
that cannot run inside a transaction on some managed Postgres providers.
"""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    STUDENT = "student"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

    @property
    def rank(self) -> int:
        return _ROLE_RANK[self]


_ROLE_RANK = {
    Role.STUDENT: 0,
    Role.INSTRUCTOR: 10,
    Role.ADMIN: 20,
    Role.SUPER_ADMIN: 30,
}


class UserStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class ServiceCode(StrEnum):
    ARMY = "army"
    AIR_FORCE = "air_force"
    NAVY = "navy"
    COMMON = "common"  # shared material (GK, English, current affairs)


class StageCode(StrEnum):
    """The selection funnel, in order."""

    REGISTRATION = "registration"
    INITIAL_TEST = "initial_test"
    PHYSICAL = "physical"
    MEDICAL = "medical"
    PRELIM_INTERVIEW = "prelim_interview"
    ISSB_SCREENING = "issb_screening"
    ISSB_PSYCHOLOGICAL = "issb_psychological"
    ISSB_GTO = "issb_gto"
    ISSB_INTERVIEW = "issb_interview"
    ISSB_CONFERENCE = "issb_conference"
    FINAL_MEDICAL = "final_medical"
    MERIT = "merit"


class QuestionType(StrEnum):
    MCQ = "mcq"
    MULTI_SELECT = "multi_select"
    TRUE_FALSE = "true_false"
    FILL_BLANK = "fill_blank"
    MATCHING = "matching"
    ORDERING = "ordering"
    SHORT_ANSWER = "short_answer"
    NON_VERBAL = "non_verbal"  # figure/series questions carrying image refs


class ContentStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

    @property
    def weight(self) -> float:
        return {"easy": 1.0, "medium": 1.5, "hard": 2.0}[self.value]


class Origin(StrEnum):
    HUMAN = "human"
    AGENT = "agent"
    IMPORT = "import"


class PsychTestType(StrEnum):
    """The ISSB psychological battery."""

    WAT = "wat"    # Word Association Test
    SCT = "sct"    # Sentence Completion Test
    SRT = "srt"    # Situation Reaction Test
    TAT = "tat"    # Thematic Apperception Test
    PSW = "psw"    # Picture Story Writing (screening day)
    PPDT = "ppdt"  # Picture Perception & Description Test (screening day 1)
    SELF_DESCRIPTION = "self_description"
    PIQ = "piq"    # Personal Information Questionnaire


class GtoTaskType(StrEnum):
    """Group Testing Officer series, day 3-4."""

    GROUP_DISCUSSION = "group_discussion"
    GROUP_PLANNING = "group_planning"          # military planning exercise
    PROGRESSIVE_GROUP_TASK = "progressive_group_task"
    HALF_GROUP_TASK = "half_group_task"
    INDIVIDUAL_OBSTACLES = "individual_obstacles"
    COMMAND_TASK = "command_task"
    SNAKE_RACE = "snake_race"
    FINAL_GROUP_TASK = "final_group_task"
    LECTURETTE = "lecturette"


class ResponseSource(StrEnum):
    """How a set of responses reached the platform.

    Candidates are told to practise on paper because that is how they sit the
    real thing, so an uploaded sheet is a first-class source rather than an
    import quirk -- and the analyser records which one it read, since a
    transcription carries the transcriber's errors as well as the candidate's.
    """

    ONLINE = "online"          # typed into the timed runner
    SHEET = "sheet"            # photographed answer sheet, transcribed
    IMPORT = "import"          # bulk loaded


class GtoVenue(StrEnum):
    """Where a GTO task is conducted.

    The series splits in two, and candidates prepare for the halves differently:
    indoor tasks are verbal and written, judged on how you think and speak, and
    they can be rehearsed alone at a desk. Outdoor tasks are physical and
    equipment-bound, judged on how you organise a group over an obstacle.

    Sources disagree about where the planning exercise belongs -- it uses a
    sand model or sketch map and is sometimes run under a shade outside. It is
    filed as indoor here because nothing about it is physical: it is written
    individually, then discussed and presented, which is the indoor pattern.
    """

    INDOOR = "indoor"
    OUTDOOR = "outdoor"


# The split as the series is actually conducted.
GTO_VENUE: dict[str, GtoVenue] = {
    "group_discussion": GtoVenue.INDOOR,
    "lecturette": GtoVenue.INDOOR,
    "group_planning": GtoVenue.INDOOR,
    "progressive_group_task": GtoVenue.OUTDOOR,
    "half_group_task": GtoVenue.OUTDOOR,
    "individual_obstacles": GtoVenue.OUTDOOR,
    "command_task": GtoVenue.OUTDOOR,
    "snake_race": GtoVenue.OUTDOOR,
    "final_group_task": GtoVenue.OUTDOOR,
}

GTO_TASK_LABELS: dict[str, str] = {
    "group_discussion": "Group Discussion",
    "lecturette": "Lecturette",
    "group_planning": "Group Planning Exercise",
    "progressive_group_task": "Progressive Group Task",
    "half_group_task": "Half Group Task",
    "individual_obstacles": "Individual Obstacles",
    "command_task": "Command Task",
    "snake_race": "Snake Race",
    "final_group_task": "Final Group Task",
}


class AttemptStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    EXPIRED = "expired"
    ABANDONED = "abandoned"


class AgentRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"


class OLQ(StrEnum):
    """The fifteen Officer Like Qualities the board scores candidates against.

    Grouped as: Planning & Organising, Social Adjustment, Social Effectiveness,
    and Dynamic factors.
    """

    EFFECTIVE_INTELLIGENCE = "effective_intelligence"
    REASONING_ABILITY = "reasoning_ability"
    ORGANISING_ABILITY = "organising_ability"
    POWER_OF_EXPRESSION = "power_of_expression"
    SOCIAL_ADAPTABILITY = "social_adaptability"
    COOPERATION = "cooperation"
    SENSE_OF_RESPONSIBILITY = "sense_of_responsibility"
    INITIATIVE = "initiative"
    SELF_CONFIDENCE = "self_confidence"
    SPEED_OF_DECISION = "speed_of_decision"
    ABILITY_TO_INFLUENCE = "ability_to_influence_group"
    LIVELINESS = "liveliness"
    DETERMINATION = "determination"
    COURAGE = "courage"
    STAMINA = "stamina"


OLQ_LABELS: dict[str, str] = {
    OLQ.EFFECTIVE_INTELLIGENCE: "Effective Intelligence",
    OLQ.REASONING_ABILITY: "Reasoning Ability",
    OLQ.ORGANISING_ABILITY: "Organising Ability",
    OLQ.POWER_OF_EXPRESSION: "Power of Expression",
    OLQ.SOCIAL_ADAPTABILITY: "Social Adaptability",
    OLQ.COOPERATION: "Cooperation",
    OLQ.SENSE_OF_RESPONSIBILITY: "Sense of Responsibility",
    OLQ.INITIATIVE: "Initiative",
    OLQ.SELF_CONFIDENCE: "Self Confidence",
    OLQ.SPEED_OF_DECISION: "Speed of Decision",
    OLQ.ABILITY_TO_INFLUENCE: "Ability to Influence the Group",
    OLQ.LIVELINESS: "Liveliness",
    OLQ.DETERMINATION: "Determination",
    OLQ.COURAGE: "Courage",
    OLQ.STAMINA: "Stamina",
}
