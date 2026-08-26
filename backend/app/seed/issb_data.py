"""Seed content for the ISSB simulation suite.

The WAT word list mixes neutral, positive and deliberately negative stimuli in
roughly the proportion a real set uses -- the negative ones are the point, since
what the board reads is how a candidate turns a difficult word into a
constructive sentence.
"""

from __future__ import annotations

# Word Association Test: 60 words, 15 seconds each.
WAT_WORDS = [
    "duty", "fear", "leader", "failure", "friend", "danger", "discipline", "lonely",
    "courage", "defeat", "family", "quarrel", "help", "weak", "honour", "mistake",
    "team", "angry", "responsibility", "hate", "practice", "tired", "trust", "problem",
    "sacrifice", "doubt", "hard work", "insult", "confidence", "delay", "respect", "loss",
    "decision", "blame", "service", "worry", "plan", "unfair", "loyalty", "argue",
    "success", "punish", "brother", "refuse", "country", "poor", "training", "hesitate",
    "command", "criticism", "future", "burden", "truth", "risk", "mother", "quit",
    "border", "shortage", "medal", "alone",
]

# Sentence Completion Test: 40 stems, 30 seconds each.
SCT_STEMS = [
    "When I am given an order I do not agree with, I",
    "My greatest fear is",
    "People who know me well say that I",
    "When my plan fails, I",
    "The hardest thing I have ever done was",
    "If I am put in charge of a group, I",
    "My family expects me to",
    "When someone criticises me in public, I",
    "I feel most confident when",
    "The quality I most want to develop is",
    "When I am tired but the work is unfinished, I",
    "My friends turn to me when",
    "If I fail this selection, I will",
    "The person I admire most is",
    "When two of my friends quarrel, I",
    "I lose my temper when",
    "The best decision I ever made was",
    "In a group I usually",
    "Money to me is",
    "When I am alone I",
    "My teachers always said that I",
    "If I had one year with no obligations, I would",
    "Discipline means",
    "The thing I regret most is",
    "When I do not know how to do something, I",
    "My weakest point is",
    "Leadership means",
    "If my subordinate makes a serious mistake, I",
    "I work best when",
    "The future of my country",
    "When I am under pressure, I",
    "I would never",
    "My ambition in life is",
    "What worries me about myself is",
    "When I see someone being treated unfairly, I",
    "Physical fitness to me",
    "The advice I would give my younger self is",
    "If I am the only one who disagrees, I",
    "Sacrifice means",
    "Ten years from now I",
]


# Situation Reaction Test: 30 situations, 30 seconds each. Each one is written
# so that a passive answer and an active answer are both plausible -- that gap
# is what the analyser measures.
SRT_SITUATIONS = [
    "He was leading a hiking party when one member sprained his ankle far from the road. He...",
    "His train was cancelled and he had an interview in another city the next morning. He...",
    "He found that a classmate had copied his assignment word for word. He...",
    "While swimming in a canal he saw a child struggling in deep water. He...",
    "He was made captain of a team whose members were all senior to him. He...",
    "During a group task two members refused to follow the agreed plan. He...",
    "He reached the examination hall and realised he had forgotten his admit card. He...",
    "His younger brother started keeping bad company and stopped studying. He...",
    "He was blamed by his officer for a mistake he had not made. He...",
    "On a dark road his motorcycle broke down and it started raining. He...",
    "He noticed smoke coming from a neighbour's kitchen window at night. He...",
    "He was offered a lift by a stranger after missing the last bus. He...",
    "His team was losing badly at half time and morale had collapsed. He...",
    "He discovered the shopkeeper had given him extra change by mistake. He...",
    "He was asked to give a speech at ten minutes' notice in front of the college. He...",
    "During a flood in his village the relief supplies were not being distributed fairly. He...",
    "His close friend asked him to hide something he knew was wrong. He...",
    "He was the only one who knew the correct route and the group wanted to go another way. He...",
    "His father fell ill the week before an important test. He...",
    "He saw a road accident on a lonely road with no other vehicle in sight. He...",
    "He was put in a group where nobody would speak during the discussion. He...",
    "He failed the physical test by two seconds on his first attempt. He...",
    "A junior complained to him about being bullied by a senior. He...",
    "He was given a task with fewer men and less time than it required. He...",
    "During a night exercise his party lost its bearings in unfamiliar terrain. He...",
    "He realised halfway through a presentation that his data was wrong. He...",
    "His teammates wanted to leave a slower member behind to finish on time. He...",
    "He was praised publicly for work that had mostly been done by someone else. He...",
    "The village elders opposed a school his group was trying to set up. He...",
    "He had prepared thoroughly but went completely blank in front of the board. He...",
]

# TAT slides. The platform ships without pictures; the caption describes what a
# candidate would see, and the perception hint is shown only after submission.
TAT_SLIDES = [
    {
        "prompt": "A young man standing at the edge of a river, looking at the far bank. A rope lies near his feet.",
        "perception_hint": "Most candidates see a crossing to be made. Strong stories name the goal, the method and the outcome.",
    },
    {
        "prompt": "Three people around a table with papers spread out; one is standing and pointing at the papers.",
        "perception_hint": "Usually read as a planning meeting. Say who leads, what is decided and what happens next.",
    },
    {
        "prompt": "A figure climbing a steep slope in poor light, with two others some distance behind.",
        "perception_hint": "Commonly a climb or a rescue. Avoid leaving the trailing figures unexplained.",
    },
    {
        "prompt": "A person sitting alone on a bench outside a building, holding a folded paper.",
        "perception_hint": "Often a result or a letter. The story should move from the news to an action.",
    },
    {
        "prompt": "A crowd gathered near a damaged wall; one person appears to be directing the others.",
        "perception_hint": "Usually an accident or collapse. Organising the crowd is the officer-like response.",
    },
    {
        "prompt": "A young woman speaking to an older couple in a small room; a suitcase is by the door.",
        "perception_hint": "Read as leaving for study or work. Show the decision being made, not just the emotion.",
    },
    {
        "prompt": "Two people pulling a heavy object with a rope while a third watches from higher ground.",
        "perception_hint": "The observer is usually taken as a supervisor. Give the watcher a role.",
    },
    {
        "prompt": "A student at a desk late at night with books open and a clock on the wall.",
        "perception_hint": "Almost always preparation. The story needs a result, not just effort.",
    },
    {
        "prompt": "Men in uniform standing beside a vehicle on a mountain road, one holding a map.",
        "perception_hint": "A movement or reconnaissance. Name the task and how it is completed.",
    },
    {
        "prompt": "A person handing something to a child outside a small shop.",
        "perception_hint": "Often help or charity. Keep it concrete -- what was given and what changed.",
    },
    {
        "prompt": "A group seated in a circle outdoors, one person standing and speaking.",
        "perception_hint": "A briefing or a discussion. Show the speaker moving the group to a decision.",
    },
    {
        "prompt": "A blank slide.",
        "perception_hint": "The last TAT slide is deliberately blank -- write any story you choose. Most candidates write their own ambition here.",
    },
]


GTO_TASKS = [
    {
        "task_type": "group_discussion",
        "title": "Group Discussion: Should military training be compulsory?",
        "brief": (
            "The group discusses whether one year of military training should be compulsory for "
            "every Pakistani graduate. There is no chairman and no fixed order of speaking. "
            "Speak when you have something to add, and let others finish."
        ),
        "constraints": [
            "No member may be nominated as chairman",
            "Everyone must speak at least once",
            "Twenty minutes total",
        ],
        "planning_seconds": 60,
        "execution_seconds": 1200,
        "target_olqs": ["power_of_expression", "reasoning_ability", "ability_to_influence_group", "cooperation"],
        "rubric": [
            {"olq": "power_of_expression", "look_for": "Clear argument stated in one or two sentences, no rambling"},
            {"olq": "reasoning_ability", "look_for": "Reasons and evidence rather than assertion"},
            {"olq": "ability_to_influence_group", "look_for": "Other members pick up and use the point"},
            {"olq": "cooperation", "look_for": "Builds on others rather than talking over them"},
        ],
        "model_solution": (
            "A strong contribution takes a position early, gives one concrete reason and one "
            "example, concedes the strongest opposing point, and then proposes a middle course "
            "the group can accept -- for example a shorter compulsory period with an option to "
            "extend. It does not repeat what has already been said."
        ),
    },
    {
        "task_type": "group_planning",
        "title": "Military Planning Exercise: The flooded village",
        "brief": (
            "You are a group of eight travelling by road when you reach a village cut off by "
            "flood water. Three problems present themselves at once: an injured man needs to "
            "reach the hospital eleven kilometres away, a group of thieves has been reported "
            "moving towards the relief store, and a child is missing near the canal. You have "
            "one working jeep, a tractor with a trailer, four ropes, two torches and a mobile "
            "phone with poor signal. Read the map, plan in five minutes, and be ready for one "
            "member to present the group plan."
        ),
        "constraints": [
            "The bridge on the main road is submerged",
            "The jeep seats four including the driver",
            "It will be dark in ninety minutes",
            "The tractor cannot cross the canal",
        ],
        "resources": ["One jeep", "One tractor and trailer", "Four ropes", "Two torches", "One mobile phone"],
        "planning_seconds": 300,
        "execution_seconds": 900,
        "target_olqs": ["organising_ability", "effective_intelligence", "sense_of_responsibility", "speed_of_decision"],
        "rubric": [
            {"olq": "organising_ability", "look_for": "Every problem assigned to a named party with a resource"},
            {"olq": "effective_intelligence", "look_for": "Priorities set by urgency, not by the order given"},
            {"olq": "reasoning_ability", "look_for": "Time and distance actually checked against the ninety minutes"},
            {"olq": "power_of_expression", "look_for": "Plan presented in a sequence anyone can follow"},
        ],
        "model_solution": (
            "Priority order: the missing child (life at immediate risk and daylight is running "
            "out), then the injured man, then the store. Split into three parties. Party A, four "
            "men with both torches and two ropes, searches the canal bank from the last sighting "
            "outwards. Party B takes the jeep with the injured man by the longer eastern route, "
            "phoning ahead for the hospital when signal allows. Party C, two men with the "
            "tractor, moves the relief stock into the school building and posts a watch. Regroup "
            "at the school by last light; if the child is not found by then, Party C joins the "
            "search and the village elders are asked to raise more men."
        ),
    },
]

GTO_TASKS += [
    {
        "task_type": "command_task",
        "title": "Command Task: The ammunition box",
        "brief": (
            "You are the commander. You may choose two subordinates from the group. An "
            "ammunition box weighing forty kilograms must be moved from the start line to the "
            "far platform. The ground between is out of bounds and marked in red. You have two "
            "planks, one drum, one rope and one plank-support. Explain your plan to the GTO, "
            "then execute it with your two men."
        ),
        "constraints": [
            "No member may touch the red ground",
            "The planks may not touch the red ground either",
            "The box must arrive upright",
            "Ten minutes",
        ],
        "resources": ["Two planks", "One drum", "One rope", "One plank-support"],
        "planning_seconds": 120,
        "execution_seconds": 600,
        "group_size": 3,
        "target_olqs": ["initiative", "organising_ability", "ability_to_influence_group", "determination", "courage"],
        "rubric": [
            {"olq": "initiative", "look_for": "Starts without waiting to be prompted"},
            {"olq": "ability_to_influence_group", "look_for": "Gives clear instructions the subordinates can act on"},
            {"olq": "organising_ability", "look_for": "Each man has a task at each stage, nobody stands idle"},
            {"olq": "determination", "look_for": "Adjusts and continues after a first attempt fails"},
        ],
        "model_solution": (
            "Bridge in stages rather than trying to span the whole gap. Use the drum as the "
            "midpoint support: plank one from the start line to the drum, cross with the box, "
            "then lift plank two forward from the drum to the platform. Keep one man steadying "
            "the drum, one moving the free plank, and carry the box yourself. Brief both men on "
            "the whole sequence before starting so a failure at any stage does not stop the task."
        ),
    },
    {
        "task_type": "lecturette",
        "title": "Lecturette: Choose one of four topics",
        "brief": (
            "You are given a card with four topics and three minutes to prepare. Speak for "
            "three minutes on the topic you choose, without notes. Topics: (a) Water scarcity "
            "in Pakistan, (b) The role of youth in national development, (c) CPEC, "
            "(d) Social media and its effects."
        ),
        "constraints": ["Three minutes to prepare", "Three minutes to speak", "No notes while speaking"],
        "planning_seconds": 180,
        "execution_seconds": 180,
        "group_size": 1,
        "target_olqs": ["power_of_expression", "self_confidence", "effective_intelligence", "liveliness"],
        "rubric": [
            {"olq": "power_of_expression", "look_for": "Opening, three points and a closing line"},
            {"olq": "self_confidence", "look_for": "Steady pace, no apology for lack of preparation"},
            {"olq": "effective_intelligence", "look_for": "Concrete facts and examples, not generalities"},
        ],
        "model_solution": (
            "Structure beats content in three minutes. Open with one sentence defining the "
            "topic, state that you will make three points, make them with one example each, "
            "then close by restating the position. On water scarcity: per-capita availability "
            "has fallen sharply since 1947, storage capacity is a fraction of annual flow, and "
            "most loss is in irrigation -- so the answer is storage plus lining plus pricing."
        ),
    },
    {
        "task_type": "progressive_group_task",
        "title": "Progressive Group Task: Four obstacles",
        "brief": (
            "The group crosses four obstacles of increasing difficulty, carrying its load "
            "throughout. There is no appointed leader. Each obstacle must be fully crossed by "
            "every member and the load before the next is attempted."
        ),
        "constraints": [
            "The load may not touch the ground between structures",
            "No member may touch out-of-bounds areas",
            "The whole group must cross before moving on",
            "Forty minutes",
        ],
        "resources": ["Two planks", "One rope", "One drum", "The load"],
        "planning_seconds": 120,
        "execution_seconds": 2400,
        "target_olqs": ["cooperation", "stamina", "organising_ability", "initiative", "determination"],
        "rubric": [
            {"olq": "cooperation", "look_for": "Helps weaker members across instead of racing ahead"},
            {"olq": "stamina", "look_for": "Still contributing at the fourth obstacle"},
            {"olq": "initiative", "look_for": "Offers a workable idea when the group stalls"},
        ],
        "model_solution": (
            "Send your strongest climber across first to receive the load, keep two men at the "
            "near side to pass it, and cross the weakest member in the middle of the group where "
            "help is available on both sides. Agree a single voice for each obstacle before "
            "starting it -- the common failure is four people giving directions at once."
        ),
    },
]


# (category, question, guidance)
INTERVIEW_QUESTIONS = [
    ("personal", "Tell me about yourself in two minutes.",
     "Cover background, education, one strength with evidence, and why you are here. Do not recite your PIQ."),
    ("personal", "What are your three strengths and three weaknesses?",
     "Give a real weakness with what you are doing about it. A disguised strength reads as evasion."),
    ("personal", "Who has influenced you most and how?",
     "Name a specific person and one specific thing you changed because of them."),
    ("personal", "What do you do in your free time?",
     "Be honest and specific; expect follow-up questions on whatever you name."),
    ("personal", "Have you ever failed at something important? What happened?",
     "Say what you did afterwards. The recovery is what is being assessed."),
    ("family", "Describe your father and your mother.",
     "Occupation, character and relationship. Say what each has taught you."),
    ("family", "Who is the decision maker in your family, and how are disagreements settled?",
     "Show that you observe your family clearly rather than idealising it."),
    ("family", "Does your family support your joining the armed forces?",
     "If there is hesitation, say so and explain how you addressed it."),
    ("academic", "Why did you choose your current subjects?",
     "A reason of your own beats parental pressure or drift."),
    ("academic", "Which subject do you find hardest and why?",
     "Expect a technical question in that subject immediately afterwards."),
    ("academic", "Your marks dropped in one year. Why?",
     "Answer the fact, give the cause, and state the correction."),
    ("academic", "What would you have done if you had not applied here?",
     "A real alternative plan shows judgement, not disloyalty."),
    ("current_affairs", "What is the most important news story of this week?",
     "One story, three facts, one opinion. Never bluff a figure."),
    ("current_affairs", "What are the main challenges facing Pakistan today?",
     "Pick three, rank them, and say why you ranked them that way."),
    ("current_affairs", "What is CPEC and what has it delivered so far?",
     "Route, main projects, one benefit and one criticism."),
    ("current_affairs", "Explain the current state of Pakistan's economy.",
     "Inflation, growth, debt and the external account -- approximate figures are fine, invented ones are not."),
    ("current_affairs", "What is your view on the role of social media in Pakistan?",
     "Take a position and defend it with an example."),
    ("defence", "Why do you want to join the armed forces and not a civilian career?",
     "Avoid clichés about uniform and respect. Give a reason that is actually yours."),
    ("defence", "Name the current service chiefs and the Chairman Joint Chiefs.",
     "Know the current appointments. Getting this wrong is a straightforward avoidable failure."),
    ("defence", "What are the main threats to Pakistan's security?",
     "Distinguish external, internal and non-traditional threats such as water and climate."),
    ("defence", "Which corps or branch would you prefer and why?",
     "Know what the branch actually does day to day."),
    ("defence", "What do you know about the ISSB and what is it looking for?",
     "The fifteen OLQs, assessed by three assessors independently across five days."),
    ("defence", "Name three wars or operations Pakistan has fought and one lesson from each.",
     "Dates and outcomes must be right; the lesson is where you show judgement."),
    ("religion", "What do the five pillars of Islam require of you personally?",
     "Answer practically rather than reciting definitions."),
    ("religion", "How do you view religious tolerance in a diverse country?",
     "A considered position, expressed without heat."),
    ("situational", "Your section is ordered to do something you believe is unsafe. What do you do?",
     "State the concern up the chain, then carry out a lawful order. Show both, in that order."),
    ("situational", "You catch your best friend cheating in an examination. What do you do?",
     "Do not dodge. Say what you do first, and what you do if he refuses."),
    ("situational", "You are given a task and the men under you are unwilling. What do you do?",
     "Find the reason, address it, lead by example, and report only if it persists."),
    ("situational", "You make a mistake that nobody else has noticed. What do you do?",
     "Report it. Then say what you do to limit the damage."),
    ("situational", "Your junior is more competent than you at a task you have been given. What do you do?",
     "Use him and say so openly. Insecurity is what is being tested."),
    ("hobbies", "You mentioned reading. What was the last book and what did you take from it?",
     "Never list a hobby you cannot discuss for two minutes."),
    ("hobbies", "Which sport do you play and what position?",
     "Expect questions on rules, your team and your last match."),
]


# Picture Perception & Description Test -- screening day, before the group
# discussion. The candidate sees a hazy picture for 30 seconds, fills a proforma
# (characters, age, sex, mood, action), then writes the story in four minutes.
# The pictures are deliberately ambiguous; the note is what most candidates
# perceive, shown only after submission.
PPDT_PICTURES = [
    {
        "prompt": "A hazy figure standing at the mouth of a partly collapsed tunnel, with two "
                  "smaller figures further back and what may be tools on the ground.",
        "perception_hint": "Usually read as a rescue or a repair. Strong stories name what the "
                           "hero organises, not just what they feel.",
    },
    {
        "prompt": "Several indistinct people around a table by a window; one is standing with an "
                  "arm extended over the table.",
        "perception_hint": "Commonly a briefing or a plan. Say what is decided and who carries it out.",
    },
    {
        "prompt": "A figure in the foreground facing a wide stretch of water; a boat and a second "
                  "figure are faint on the far side.",
        "perception_hint": "A crossing, an errand, or a rescue. Avoid leaving the second figure "
                           "unexplained.",
    },
    {
        "prompt": "Two figures on a slope in poor light, one lower and apparently reaching upward.",
        "perception_hint": "A climb or a fall. The story should resolve whether the hero succeeds.",
    },
    {
        "prompt": "A crowd of indistinct people outside a low building; one figure stands apart, "
                  "closer to the viewer.",
        "perception_hint": "Often a queue, a protest or an announcement. The figure apart is "
                           "usually taken as the hero.",
    },
    {
        "prompt": "A person seated at a desk near a window at night, with papers and an "
                  "indistinct object beside them.",
        "perception_hint": "Preparation or a decision. Give it an outcome, not just effort.",
    },
    {
        "prompt": "Figures gathered near a stationary vehicle on an open road, one crouching.",
        "perception_hint": "A breakdown or an accident. Organising help is the officer-like move.",
    },
    {
        "prompt": "A blurred field with a fence, a figure climbing it, and two others watching "
                  "from a distance.",
        "perception_hint": "An obstacle being crossed. Say why, and what the watchers do.",
    },
]

# Self Description: written on day two, in the candidate's own hand. The board
# compares these five views for honesty and self-awareness -- a candidate whose
# self-view contradicts every other view is the thing being looked for.
SELF_DESCRIPTION_PROMPTS = [
    "What do your parents think of you? Write what they would honestly say, "
    "including what they would want you to improve.",
    "What do your teachers think of you? Give their view of your work and your conduct.",
    "What do your friends think of you? Say what they rely on you for, and what "
    "irritates them about you.",
    "What do you think of yourself? Include the weakness you are working on.",
    "What kind of person do you want to become, and what are you doing about it now?",
]


# The outdoor half of the series that was missing. Durations, group sizes and
# helping materials follow the published ISSB/SSB descriptions: the plank
# (fatta), log (balli) and rope are the standard three, red-marked ground is out
# of bounds, and the load may not touch the ground once lifted.
GTO_TASKS += [
    {
        "task_type": "half_group_task",
        "title": "Half Group Task: The broken span",
        "brief": (
            "The group is split in two and each half attempts the same single obstacle, so "
            "the GTO can watch you without the noise of the full group. Carry the load across "
            "the gap using the helping material. The rules are those of the Progressive Group "
            "Task and nothing is relaxed because the group is smaller."
        ),
        "constraints": [
            "Red-painted ground and structures are out of bounds",
            "The load may not touch the ground once it has been lifted",
            "Helping material may not be shortened, folded or thrown",
            "Every member and the load must be across before the task is complete",
        ],
        "resources": ["One plank (fatta)", "One log (balli)", "One rope", "The load"],
        "planning_seconds": 120,
        "execution_seconds": 1200,
        "group_size": 4,
        "target_olqs": ["cooperation", "initiative", "organising_ability", "self_confidence"],
        "rubric": [
            {"olq": "initiative", "look_for": "Offers a workable idea in the smaller group rather than waiting"},
            {"olq": "cooperation", "look_for": "Works with the half group instead of re-fighting the full group plan"},
            {"olq": "organising_ability", "look_for": "Assigns the plank, the rope and the load to named people"},
        ],
        "model_solution": (
            "With four people the common failure is everyone lifting and nobody planning. Fix "
            "roles before the first lift: one on the far side to receive, two carrying, one "
            "managing the helping material. Bridge in stages using the log as a midpoint "
            "support rather than trying to span the gap in one go, and keep the load moving "
            "hand to hand so it never rests on the ground."
        ),
    },
    {
        "task_type": "individual_obstacles",
        "title": "Individual Obstacles: Nine in three minutes",
        "brief": (
            "You attempt a set of nine or ten obstacles alone, in any order, inside three "
            "minutes. Each obstacle carries points by difficulty, from one up to ten. You may "
            "repeat an obstacle you have already cleared if time remains, and its points count "
            "again. Nobody helps you and nobody is watching your group."
        ),
        "constraints": [
            "Three minutes for the whole set",
            "Obstacles may be attempted in any order",
            "A cleared obstacle may be repeated for its points if time allows",
            "An obstacle you fail may be re-attempted, but the clock does not stop",
        ],
        "resources": [
            "Screen jump", "Burma bridge", "Tarzan swing", "Double ditch", "Commando walk",
            "Tiger leap", "Balance beam", "Rope climb", "Zig-zag balance",
        ],
        "planning_seconds": 30,
        "execution_seconds": 180,
        "group_size": 1,
        "difficulty": "hard",
        "target_olqs": ["courage", "stamina", "speed_of_decision", "determination", "self_confidence"],
        "rubric": [
            {"olq": "speed_of_decision", "look_for": "Starts immediately rather than surveying the whole set"},
            {"olq": "courage", "look_for": "Attempts the high-value obstacles rather than farming the easy ones"},
            {"olq": "stamina", "look_for": "Still moving at speed in the third minute"},
            {"olq": "determination", "look_for": "Re-attempts a failed obstacle instead of avoiding it"},
        ],
        "model_solution": (
            "Points, not obstacles, are what is scored. Walk the set once before you start and "
            "fix an order: clear the highest-value obstacles you are confident of first, then "
            "spend whatever remains repeating the quickest high scorer rather than fighting the "
            "one that beat you. Do not queue behind another candidate; move to the next free "
            "obstacle. Hesitating at the top of the screen jump costs more marks than falling."
        ),
    },
]

GTO_TASKS += [
    {
        "task_type": "snake_race",
        "title": "Snake Race: Carrying the load against the clock",
        "brief": (
            "Teams race simultaneously over a series of six obstacles carrying a rolled tent -- "
            "the snake -- which must be held clear of the ground from the start line to the "
            "finish. It is the only task where you are openly competing with another group, and "
            "the GTO is watching what competition does to your team spirit."
        ),
        "constraints": [
            "Once lifted at the start line, the snake may not touch the ground until the finish",
            "The snake must be carried roughly parallel to the ground, never dragged",
            "At least three members must be holding it while crossing an obstacle",
            "Red-painted portions of every obstacle are out of bounds",
            "The whole team finishes together or the team has not finished",
        ],
        "resources": ["A rolled tent (the snake)", "Six obstacles in sequence"],
        "planning_seconds": 60,
        "execution_seconds": 600,
        "group_size": 8,
        "target_olqs": ["stamina", "cooperation", "determination", "liveliness", "courage"],
        "rubric": [
            {"olq": "cooperation", "look_for": "Adjusts pace so the slowest member keeps up, rather than dropping them"},
            {"olq": "stamina", "look_for": "Still carrying weight at the fifth and sixth obstacle"},
            {"olq": "liveliness", "look_for": "Lifts the team when the other group pulls ahead"},
            {"olq": "determination", "look_for": "Finishes properly rather than abandoning the rules to win"},
        ],
        "model_solution": (
            "Racing is the trap. A team that breaks the rules to get ahead is marked down harder "
            "than one that finishes second cleanly, because the GTO is scoring how you behave "
            "under competitive pressure, not who wins. Distribute the weight before the start so "
            "the strongest carry the middle, keep three hands on it at every obstacle, and call "
            "a rhythm out loud so the group moves as one body. If someone tires, rotate them to "
            "the front rather than leaving them behind."
        ),
    },
    {
        "task_type": "final_group_task",
        "title": "Final Group Task: The last crossing",
        "brief": (
            "The full group reunites for one final obstacle, run under exactly the rules of the "
            "Progressive Group Task. It is the last thing the GTO sees you do, and it is where "
            "everything you have learned over the series is expected to show: a group that has "
            "worked together for two days should not still be arguing at the start line."
        ),
        "constraints": [
            "Red-painted ground and structures are out of bounds",
            "The load may not touch the ground once lifted",
            "Helping material may not be shortened, folded or thrown",
            "Every member and the load must be across",
        ],
        "resources": ["One plank (fatta)", "One log (balli)", "One rope", "The load"],
        "planning_seconds": 180,
        "execution_seconds": 900,
        "group_size": 8,
        "target_olqs": ["cooperation", "organising_ability", "ability_to_influence_group", "determination"],
        "rubric": [
            {"olq": "cooperation", "look_for": "Supports whoever has the workable idea instead of pushing their own"},
            {"olq": "ability_to_influence_group", "look_for": "The group adopts their suggestion without being argued into it"},
            {"olq": "determination", "look_for": "Keeps working after a failed attempt late in a tiring series"},
        ],
        "model_solution": (
            "By this task the GTO already knows who talks and who works. The marks left are for "
            "settling the plan quickly and finishing cleanly. Agree the method in the first "
            "minute, name who does what, and get the load moving. If a better idea appears "
            "mid-task, take it visibly -- adopting someone else's plan at the end of the series "
            "reads as judgement, not weakness."
        ),
    },
]
