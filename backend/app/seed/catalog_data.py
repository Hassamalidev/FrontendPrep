"""Catalog seed: services, the selection funnel, entry schemes and modules.

Figures here (age bands, height bars, run timings) follow the published
requirements for the major entry schemes. They are seed defaults an admin is
expected to confirm against the current advertisement each intake -- they are
stored as JSON on the program row precisely so they can be edited without a
migration.
"""

from __future__ import annotations

SERVICES = [
    {
        "id": 1,
        "code": "army",
        "name": "Pakistan Army",
        "short_name": "Army",
        "tagline": "Men at their best",
        "accent": "#2f5d3a",
        "sort_order": 1,
        "description": (
            "Commissioned entry through PMA Long Course, Technical Cadet Course and "
            "Lady Cadet Course, plus graduate and short-service routes."
        ),
    },
    {
        "id": 2,
        "code": "air_force",
        "name": "Pakistan Air Force",
        "short_name": "PAF",
        "tagline": "Second to none",
        "accent": "#1c3f6e",
        "sort_order": 2,
        "description": (
            "GD Pilot, Aeronautical Engineering, Air Defence and Special Duties "
            "branches, entered through the PAF selection centres."
        ),
    },
    {
        "id": 3,
        "code": "navy",
        "name": "Pakistan Navy",
        "short_name": "Navy",
        "tagline": "Silent service",
        "accent": "#12405a",
        "sort_order": 3,
        "description": (
            "Operations, Marines, Engineering, Supply and Education branches via "
            "cadet and short-service commission schemes."
        ),
    },
    {
        "id": 4,
        "code": "common",
        "name": "Common Syllabus",
        "short_name": "Common",
        "tagline": "Shared preparation",
        "accent": "#5b4a2f",
        "sort_order": 4,
        "description": (
            "Material every candidate needs regardless of service: English, "
            "general knowledge, current affairs, Islamiat and Pakistan Studies."
        ),
    },
]

STAGES = [
    (1, "registration", "Registration", "Online application, document check and roll number issue.", "clipboard", None),
    (2, "initial_test", "Initial Written Test", "Intelligence and academic test at the selection centre.", "pencil", None),
    (3, "physical", "Physical Test", "Run, push-ups, sit-ups and chin-ups against the branch standard.", "run", None),
    (4, "medical", "Preliminary Medical", "Height, weight, vision, hearing and general fitness screening.", "stethoscope", None),
    (5, "prelim_interview", "Preliminary Interview", "Board interview at the selection centre before the ISSB call.", "chat", None),
    (6, "issb_screening", "ISSB Screening", "Day 1: intelligence tests and Picture Story Writing; screened in or out.", "filter", "ISSB Day 1"),
    (7, "issb_psychological", "Psychological Tests", "Day 2: TAT, WAT, SCT, SRT and the self-description.", "brain", "ISSB Day 2"),
    (8, "issb_gto", "GTO Series", "Days 3-4: group tasks, obstacles, command task and lecturette.", "users", "ISSB Day 3-4"),
    (9, "issb_interview", "ISSB Interview", "A long interview with the Interviewing Officer.", "microphone", "ISSB Day 2-4"),
    (10, "issb_conference", "Conference", "Final day: the whole board reviews each candidate together.", "gavel", "ISSB Day 5"),
    (11, "final_medical", "Final Medical", "Detailed medical board at a CMH after recommendation.", "hospital", None),
    (12, "merit", "Merit List", "Final selection on combined merit and vacancies.", "trophy", None),
]


PROGRAMS = [
    {
        "service_id": 1,
        "slug": "pma-long-course",
        "name": "PMA Long Course",
        "short_name": "PMA LC",
        "summary": "The main regular commission route into the Pakistan Army, two years at Kakul.",
        "eligibility": {
            "age": {"min": 17, "max": 22},
            "education": ["FSc / FA / A-Level with at least 60%"],
            "gender": "male",
            "marital_status": "unmarried",
            "height_cm": {"male": 162.5},
            "nationality": "Pakistani",
        },
        "physical_standards": {
            "run_1600m_sec": 480,
            "push_ups": 15,
            "sit_ups": 20,
            "chin_ups": 3,
        },
        "test_blueprint": {
            "sections": ["verbal-intelligence", "non-verbal-intelligence", "academic-english", "general-knowledge"]
        },
        "sort_order": 1,
    },
    {
        "service_id": 1,
        "slug": "lady-cadet-course",
        "name": "Lady Cadet Course",
        "short_name": "LCC",
        "summary": "Direct commission for female graduates into selected Army corps.",
        "eligibility": {
            "age": {"min": 20, "max": 28},
            "education": ["Bachelor or Master in the advertised discipline"],
            "gender": "female",
            "height_cm": {"female": 152.4},
        },
        "physical_standards": {"run_1600m_sec": 660, "sit_ups": 10},
        "test_blueprint": {"sections": ["verbal-intelligence", "academic-english", "general-knowledge"]},
        "sort_order": 2,
    },
    {
        "service_id": 1,
        "slug": "technical-cadet-course",
        "name": "Technical Cadet Course",
        "short_name": "TCC",
        "summary": "Engineering stream commission, degree completed at MCE or MCS.",
        "eligibility": {
            "age": {"min": 17, "max": 21},
            "education": ["FSc Pre-Engineering with at least 70%"],
            "gender": "male",
            "height_cm": {"male": 162.5},
        },
        "physical_standards": {"run_1600m_sec": 480, "push_ups": 15, "sit_ups": 20, "chin_ups": 3},
        "test_blueprint": {
            "sections": ["verbal-intelligence", "non-verbal-intelligence", "mathematics", "physics"]
        },
        "sort_order": 3,
    },
    {
        "service_id": 2,
        "slug": "gd-pilot",
        "name": "GD (Pilot)",
        "short_name": "GD(P)",
        "summary": "General Duty Pilot -- the PAF flying branch, via Risalpur.",
        "eligibility": {
            "age": {"min": 16, "max": 22},
            "education": ["FSc Pre-Engineering / A-Level with Maths and Physics, at least 60%"],
            "gender": "male",
            "marital_status": "unmarried",
            "height_cm": {"male": 163.0},
            "vision": "6/6 without correction",
        },
        "physical_standards": {"run_1600m_sec": 510, "push_ups": 15, "sit_ups": 20, "chin_ups": 3},
        "test_blueprint": {
            "sections": ["verbal-intelligence", "non-verbal-intelligence", "mathematics", "physics", "academic-english"]
        },
        "sort_order": 1,
    },
    {
        "service_id": 2,
        "slug": "aeronautical-engineering",
        "name": "Aeronautical Engineering",
        "short_name": "AE",
        "summary": "Engineering branch covering avionics and aerospace streams.",
        "eligibility": {
            "age": {"min": 16, "max": 24},
            "education": ["FSc Pre-Engineering with at least 65%"],
            "height_cm": {"male": 163.0, "female": 152.4},
        },
        "physical_standards": {"run_1600m_sec": 540, "push_ups": 12, "sit_ups": 18},
        "test_blueprint": {"sections": ["non-verbal-intelligence", "mathematics", "physics"]},
        "sort_order": 2,
    },
    {
        "service_id": 3,
        "slug": "pn-cadet-operations",
        "name": "PN Cadet (Operations)",
        "short_name": "PN Ops",
        "summary": "Executive branch commission through PNS Rahbar and Britannia-pattern training.",
        "eligibility": {
            "age": {"min": 16, "max": 21},
            "education": ["FSc Pre-Engineering with at least 60%"],
            "gender": "male",
            "marital_status": "unmarried",
            "height_cm": {"male": 162.5},
        },
        "physical_standards": {"run_1600m_sec": 510, "push_ups": 15, "sit_ups": 20, "swim": "basic"},
        "test_blueprint": {
            "sections": ["verbal-intelligence", "non-verbal-intelligence", "mathematics", "academic-english"]
        },
        "sort_order": 1,
    },
    {
        "service_id": 3,
        "slug": "pn-short-service",
        "name": "Short Service Commission",
        "short_name": "SSC",
        "summary": "Graduate entry into supply, education, medical and IT branches.",
        "eligibility": {
            "age": {"min": 20, "max": 28},
            "education": ["Bachelor or Master in the advertised discipline"],
            "height_cm": {"male": 162.5, "female": 152.4},
        },
        "physical_standards": {"run_1600m_sec": 600, "push_ups": 12},
        "test_blueprint": {"sections": ["academic-english", "general-knowledge", "verbal-intelligence"]},
        "sort_order": 2,
    },
]


# (slug, title, subtitle, icon, stage_code, [(topic_slug, topic_name, [keywords])])
# Modules marked service "common" are cloned onto every service at load time, so
# a student sees one coherent syllabus rather than a shared bucket they have to
# go looking for.
COMMON_MODULES = [
    (
        "verbal-intelligence",
        "Verbal Intelligence",
        "Word logic, analogies and series -- the largest part of the initial test.",
        "abc",
        "initial_test",
        [
            ("analogies", "Analogies", ["analogy", "relation", "pair"]),
            ("odd-one-out", "Odd One Out", ["odd", "different", "classification"]),
            ("word-series", "Word and Letter Series", ["series", "sequence", "next"]),
            ("synonyms-antonyms", "Synonyms and Antonyms", ["synonym", "antonym", "meaning"]),
            ("coding-decoding", "Coding and Decoding", ["code", "cipher", "decode"]),
            ("blood-relations", "Blood Relations", ["father", "brother", "family", "relation"]),
            ("direction-sense", "Direction Sense", ["north", "south", "direction", "turn"]),
            ("logical-deduction", "Logical Deduction", ["conclusion", "premise", "syllogism"]),
        ],
    ),
    (
        "non-verbal-intelligence",
        "Non-Verbal Intelligence",
        "Figures, patterns and matrices -- scored heavily on screening day.",
        "shapes",
        "initial_test",
        [
            ("figure-series", "Figure Series", ["figure", "series", "pattern"]),
            ("figure-analogy", "Figure Analogy", ["analogy", "figure"]),
            ("mirror-water-images", "Mirror and Water Images", ["mirror", "reflection", "water"]),
            ("embedded-figures", "Embedded Figures", ["embedded", "hidden", "shape"]),
            ("paper-folding", "Paper Folding and Cutting", ["fold", "cut", "punch"]),
            ("matrices", "Matrix Reasoning", ["matrix", "grid", "missing"]),
        ],
    ),
    (
        "mathematics",
        "Mathematics",
        "Arithmetic, algebra and geometry at intermediate level.",
        "calculator",
        "initial_test",
        [
            ("arithmetic", "Arithmetic", ["percentage", "ratio", "average", "profit"]),
            ("algebra", "Algebra", ["equation", "polynomial", "factor"]),
            ("geometry", "Geometry", ["triangle", "circle", "angle", "area"]),
            ("trigonometry", "Trigonometry", ["sine", "cosine", "tangent"]),
            ("data-interpretation", "Data Interpretation", ["graph", "table", "chart"]),
        ],
    ),
    (
        "physics",
        "Physics",
        "Mechanics, electricity and modern physics for technical entries.",
        "atom",
        "initial_test",
        [
            ("mechanics", "Mechanics", ["force", "motion", "newton", "momentum"]),
            ("electricity", "Electricity and Magnetism", ["current", "voltage", "magnetic"]),
            ("waves-optics", "Waves and Optics", ["wave", "light", "refraction"]),
            ("modern-physics", "Modern Physics", ["atom", "nuclear", "quantum"]),
        ],
    ),
    (
        "academic-english",
        "English",
        "Grammar, comprehension and precis -- also what the interview judges.",
        "book",
        "initial_test",
        [
            ("grammar", "Grammar and Usage", ["tense", "preposition", "article"]),
            ("vocabulary", "Vocabulary", ["meaning", "word", "idiom"]),
            ("comprehension", "Comprehension", ["passage", "paragraph"]),
            ("sentence-correction", "Sentence Correction", ["error", "correct", "sentence"]),
            ("essay-precis", "Essay and Precis", ["essay", "precis", "summary"]),
        ],
    ),
    (
        "general-knowledge",
        "General Knowledge",
        "Pakistan, the world and defence affairs.",
        "globe",
        "initial_test",
        [
            ("pakistan-affairs", "Pakistan Affairs", ["pakistan", "constitution", "province"]),
            ("world-affairs", "World Affairs", ["united nations", "world", "treaty"]),
            ("defence-affairs", "Defence and Armed Forces", ["army", "navy", "air force", "missile", "regiment"]),
            ("geography", "Geography", ["river", "mountain", "capital", "border"]),
            ("science-technology", "Everyday Science", ["science", "technology", "discovery"]),
        ],
    ),
    (
        "islamiat",
        "Islamiat",
        "Beliefs, Seerah and the fundamentals expected in the written test.",
        "mosque",
        "initial_test",
        [
            ("aqaid", "Aqaid and Ibadat", ["faith", "prayer", "pillar"]),
            ("seerah", "Seerah of the Prophet", ["prophet", "madinah", "makkah"]),
            ("quran-hadith", "Quran and Hadith", ["quran", "surah", "hadith"]),
        ],
    ),
    (
        "current-affairs",
        "Current Affairs",
        "The rolling feed the question engine generates from.",
        "newspaper",
        "initial_test",
        [
            ("national", "National", ["pakistan", "government", "assembly"]),
            ("international", "International", ["world", "summit", "agreement"]),
            ("defence-news", "Defence News", ["exercise", "induction", "missile", "deal"]),
            ("economy", "Economy", ["budget", "inflation", "imf", "growth"]),
        ],
    ),
]


# ISSB-stage modules. These carry no written question bank of their own -- the
# practice lives in the simulation endpoints -- but they exist so the funnel
# renders as one continuous syllabus rather than stopping at the written test.
ISSB_MODULES = [
    (
        "issb-screening",
        "Screening Day",
        "Intelligence tests and Picture Story Writing under time pressure.",
        "filter",
        "issb_screening",
        [
            ("screening-intelligence", "Screening Intelligence Tests", ["verbal", "non-verbal"]),
            ("picture-story-writing", "Picture Story Writing", ["picture", "story", "psw"]),
        ],
    ),
    (
        "psychological-tests",
        "Psychological Tests",
        "TAT, WAT, SCT, SRT and the self-description.",
        "brain",
        "issb_psychological",
        [
            ("tat", "Thematic Apperception Test", ["picture", "story", "tat"]),
            ("wat", "Word Association Test", ["word", "association", "wat"]),
            ("sct", "Sentence Completion Test", ["sentence", "completion", "sct"]),
            ("srt", "Situation Reaction Test", ["situation", "reaction", "srt"]),
            ("self-description", "Self Description", ["self", "parents", "teachers"]),
        ],
    ),
    (
        "gto-series",
        "GTO Series",
        "Group tasks, obstacles, command task and lecturette.",
        "users",
        "issb_gto",
        [
            ("group-discussion", "Group Discussion", ["discussion", "topic", "group"]),
            ("group-planning", "Military Planning Exercise", ["planning", "map", "problem"]),
            ("progressive-group-task", "Progressive Group Task", ["obstacle", "load", "structure"]),
            ("command-task", "Command Task", ["command", "subordinates", "leader"]),
            ("individual-obstacles", "Individual Obstacles", ["obstacle", "jump", "climb"]),
            ("lecturette", "Lecturette", ["lecture", "topic", "three minutes"]),
        ],
    ),
    (
        "interview-preparation",
        "Interview",
        "The IO interview, the PIQ and how to answer without bluffing.",
        "microphone",
        "issb_interview",
        [
            ("piq", "Personal Information Questionnaire", ["piq", "form", "personal"]),
            ("personal-questions", "Personal and Family", ["family", "parents", "hobbies"]),
            ("academic-questions", "Academic Background", ["school", "college", "subject"]),
            ("current-affairs-interview", "Current Affairs in Interview", ["news", "affairs", "opinion"]),
            ("situational-questions", "Situational Questions", ["situation", "would you", "decide"]),
        ],
    ),
    (
        "physical-preparation",
        "Physical Preparation",
        "Run timings, push-ups, sit-ups and chin-ups against your branch standard.",
        "run",
        "physical",
        [
            ("running", "Running", ["run", "mile", "timing"]),
            ("strength", "Strength", ["push-up", "chin-up", "sit-up"]),
            ("medical-readiness", "Medical Readiness", ["height", "weight", "bmi", "vision"]),
        ],
    ),
]

# The initial written test differs by service, and the differences are the whole
# point of preparing for one rather than "the forces test". Published patterns
# (2026 intakes) -- an admin is expected to confirm against the current
# advertisement, which is why they live in data rather than in code:
#
#   Army (PMA Long Course)   verbal 60 + non-verbal ~64 (30 min) + academic 50
#                            (30 min). Academic spans English, Maths, Pak
#                            Studies, Islamiat and General Knowledge.
#   PAF (GD Pilot)           one combined intelligence paper of 100 (40 min),
#                            then English / Maths / Physics at 25 questions and
#                            10 minutes each. No General Knowledge at all.
#   Navy (PN Cadet)          intelligence 100 (40 min) but weighted to
#                            non-verbal: 25 verbal, 75 non-verbal. Academic
#                            75-100 (30-40 min) over English, Maths/Physics and
#                            General Knowledge.
#
# All three are computer-based with no negative marking and a 50% sectional
# pass mark.
TEST_PATTERNS: dict[str, dict] = {
    "army": {
        "label": "PMA Long Course",
        "sections": [
            {"name": "Verbal Intelligence", "questions": 60, "minutes": 30},
            {"name": "Non-Verbal Intelligence", "questions": 64, "minutes": 30},
            {"name": "Academic", "questions": 50, "minutes": 30,
             "covers": ["English", "Mathematics", "Pakistan Studies", "Islamiat", "General Knowledge"]},
        ],
        "negative_marking": False,
        "sectional_pass": 50,
        "distinctive": "The only service that tests General Knowledge, Pakistan Studies and Islamiat.",
    },
    "air_force": {
        "label": "GD Pilot",
        "sections": [
            {"name": "Intelligence (verbal and non-verbal)", "questions": 100, "minutes": 40},
            {"name": "English", "questions": 25, "minutes": 10},
            {"name": "Mathematics", "questions": 25, "minutes": 10},
            {"name": "Physics", "questions": 25, "minutes": 10},
        ],
        "negative_marking": False,
        "sectional_pass": 50,
        "distinctive": "No General Knowledge paper. Physics is compulsory, and each academic subject is its own timed paper.",
    },
    "navy": {
        "label": "PN Cadet",
        "sections": [
            {"name": "Intelligence", "questions": 100, "minutes": 40,
             "split": {"verbal": 25, "non_verbal": 75}},
            {"name": "Academic", "questions": 85, "minutes": 35,
             "covers": ["English", "Mathematics or Physics", "General Knowledge"]},
        ],
        "negative_marking": False,
        "sectional_pass": 50,
        "distinctive": "Intelligence is weighted three to one towards non-verbal -- 75 of the 100 questions.",
    },
}

# (slug, title, service_slug or None, stage_code, sections, minutes, is_mock)
TEST_TEMPLATES = [
    {
        "slug": "army-initial-test-mock",
        "title": "PMA Long Course -- Full Initial Test",
        "description": (
            "The Army pattern: verbal and non-verbal intelligence, then a single academic "
            "paper spanning English, Maths, Pakistan Studies, Islamiat and General Knowledge."
        ),
        "service_code": "army",
        "stage_code": "initial_test",
        "sections": [
            {"module_slug": "verbal-intelligence", "count": 60, "minutes": 30, "title": "Verbal Intelligence"},
            {"module_slug": "non-verbal-intelligence", "count": 64, "minutes": 30, "title": "Non-Verbal Intelligence"},
            {"module_slug": "academic-english", "count": 15, "minutes": 9, "title": "Academic: English"},
            {"module_slug": "mathematics", "count": 15, "minutes": 9, "title": "Academic: Mathematics"},
            {"module_slug": "general-knowledge", "count": 12, "minutes": 7, "title": "Academic: General Knowledge"},
            {"module_slug": "islamiat", "count": 8, "minutes": 5, "title": "Academic: Islamiat"},
        ],
        "duration_min": 90,
        "is_mock": True,
        "sort_order": 1,
    },
    {
        "slug": "paf-gd-pilot-mock",
        "title": "PAF GD Pilot -- Full Initial Test",
        "description": (
            "The PAF pattern: one combined intelligence paper, then English, Maths and "
            "Physics as separate timed papers. No General Knowledge."
        ),
        "service_code": "air_force",
        "stage_code": "initial_test",
        "sections": [
            {"module_slug": "verbal-intelligence", "count": 40, "minutes": 16, "title": "Intelligence: Verbal"},
            {"module_slug": "non-verbal-intelligence", "count": 60, "minutes": 24, "title": "Intelligence: Non-Verbal"},
            {"module_slug": "academic-english", "count": 25, "minutes": 10, "title": "English"},
            {"module_slug": "mathematics", "count": 25, "minutes": 10, "title": "Mathematics"},
            {"module_slug": "physics", "count": 25, "minutes": 10, "title": "Physics"},
        ],
        "duration_min": 70,
        "is_mock": True,
        "sort_order": 2,
    },
    {
        "slug": "navy-cadet-mock",
        "title": "PN Cadet -- Full Initial Test",
        "description": (
            "The Navy pattern: intelligence weighted three to one towards non-verbal, then "
            "an academic paper over English, Maths or Physics, and General Knowledge."
        ),
        "service_code": "navy",
        "stage_code": "initial_test",
        "sections": [
            {"module_slug": "verbal-intelligence", "count": 25, "minutes": 10, "title": "Intelligence: Verbal"},
            {"module_slug": "non-verbal-intelligence", "count": 75, "minutes": 30, "title": "Intelligence: Non-Verbal"},
            {"module_slug": "academic-english", "count": 30, "minutes": 12, "title": "Academic: English"},
            {"module_slug": "mathematics", "count": 30, "minutes": 12, "title": "Academic: Mathematics"},
            {"module_slug": "general-knowledge", "count": 25, "minutes": 11, "title": "Academic: General Knowledge"},
        ],
        "duration_min": 75,
        "is_mock": True,
        "sort_order": 3,
    },
    {
        "slug": "daily-current-affairs",
        "title": "Daily Current Affairs Drill",
        "description": "Fifteen questions from the last few weeks of news.",
        "service_code": None,
        "stage_code": "initial_test",
        "sections": [
            {"module_slug": "current-affairs", "count": 15, "minutes": 10, "title": "Current Affairs"}
        ],
        "duration_min": 10,
        "is_mock": False,
        "sort_order": 4,
    },
]
