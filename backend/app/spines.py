"""
Server-side mirror of the archetype spines in frontend/lib/plan.ts.

GENERATED — do not edit by hand. Regenerate with:
    cd backend && .venv/bin/python scripts/sync_spines.py

The TypeScript file stays the single source of truth because that is where the
spines are authored and where /plan renders them signed-out. This mirror exists
so GET /roadmap can sequence without the client sending its own content, which
would let a student post any project text they liked into public.actions.
tests/test_spines_sync.py fails if the two drift.
"""

from __future__ import annotations

SPINES: dict[str, dict[str, str]] = {
    "applied-ai-builder": {
        "project": "Build a small AI tool that removes one annoyance from your own week — a study-note summarizer, a flashcard generator — and get it working end to end, however rough.",
        "publish": "Record a 60-second demo of the tool and post it where other builders will actually see it.",
        "skill": "evaluation — learn to measure whether an AI feature actually works, not just whether it runs",
        "skillKey": "evaluation"
    },
    "computational-biology-researcher": {
        "project": "Pick one public dataset (NCBI, a Kaggle bio set) and reproduce one figure or statistic from a real paper with your own code.",
        "publish": "Write a short lab-notebook post: what the data showed, what surprised you, what you would test next.",
        "skill": "statistics — the hypothesis tests behind the figure you reproduced",
        "skillKey": "statistics"
    },
    "technical-founder": {
        "project": "Interview five people about one problem you suspect they share, then build the smallest thing that addresses it.",
        "publish": "Ship a one-page site for the idea and get ten people to react to it.",
        "skill": "scoping — cutting an idea down to a one-week MVP without losing it",
        "skillKey": "scoping"
    },
    "product-minded-engineer": {
        "project": "Take a tool you already use daily and redesign the one workflow that annoys you — write the spec first, then build the improvement.",
        "publish": "Post a before/after write-up showing the redesign and the reasoning behind each change.",
        "skill": "user research — turning three real user conversations into one prioritized change",
        "skillKey": "user-research"
    },
    "civic-technology-designer": {
        "project": "Find one local problem — school, library, community org — and prototype a tool that helps, together with the people who would use it.",
        "publish": "Present the prototype to the group it serves and collect their reactions in writing.",
        "skill": "accessibility — making the prototype usable by everyone it is for",
        "skillKey": "accessibility"
    },
    "research-mathematician": {
        "project": "Pick one competition problem set (AMC, a past olympiad) and write full solutions to five problems — proofs, not answers.",
        "publish": "Write up your cleanest proof and post it where other math students will critique it.",
        "skill": "proof technique — induction and contradiction until they are reflexes",
        "skillKey": "proof-technique"
    },
    "experimental-physicist": {
        "project": "Design and run one tabletop experiment with real measurements — pendulum period, diffraction, cooling curves — and compare against theory.",
        "publish": "Write a short lab report: setup, data, error sources, and where theory and measurement disagreed.",
        "skill": "error analysis — knowing how much to trust every number you record",
        "skillKey": "error-analysis"
    },
    "robotics-engineer": {
        "project": "Build one mechanism that moves under its own control — a line follower, a sorting arm, a self-balancing something — however rough.",
        "publish": "Record it working (and failing) and post the build log with what broke.",
        "skill": "control basics — why the naive approach oscillates and PID doesn't",
        "skillKey": "control-basics"
    },
    "biomedical-innovator": {
        "project": "Pick one health problem someone you know actually has and prototype the smallest device, tool, or protocol that helps.",
        "publish": "Show it to one person in healthcare — a nurse, a PT, a school counselor — and write down their reaction.",
        "skill": "regulatory literacy — why medical ideas move slowly and what that means for design",
        "skillKey": "regulatory-literacy"
    },
    "data-scientist": {
        "project": "Take one public dataset about your own city or school district and answer a question nobody has asked it yet.",
        "publish": "Publish the notebook with three charts and one honest paragraph about what the data cannot say.",
        "skill": "statistical honesty — confounders, base rates, and when a trend is noise",
        "skillKey": "statistical-honesty"
    },
    "science-communicator": {
        "project": "Take one paper or result you love and produce a two-minute explanation a ninth grader would finish.",
        "publish": "Post it publicly and ask three non-STEM friends what they understood — revise until they can repeat it back.",
        "skill": "narrative structure — hook, stakes, one idea, and nothing else",
        "skillKey": "narrative-structure"
    },
    "field-research-scientist": {
        "project": "Design a four-week observation protocol for something living or changing near you — a creek, a tree line, night sky brightness — and collect real data on schedule.",
        "publish": "Publish the dataset with your protocol so someone else could repeat it.",
        "skill": "sampling discipline — why the boring schedule is the whole experiment",
        "skillKey": "sampling-discipline"
    },
    "game-designer": {
        "project": "Make one level of one mechanic — not a game, a level — and put it in front of three people who did not watch you build it.",
        "publish": "Post the level with a short note on the one change you made after watching someone play it badly.",
        "skill": "playtesting — learning to watch someone struggle without jumping in to help them",
        "skillKey": "playtesting"
    },
    "product-designer": {
        "project": "Take one screen of an app your school actually makes you use and redesign it — write down what each element is for before you move anything.",
        "publish": "Post the before, the after, and the reasoning for each change you kept and each one you abandoned.",
        "skill": "critique — separating what you like from what works, in your own designs and other people's",
        "skillKey": "design-critique"
    },
    "digital-media-artist": {
        "project": "Build one piece where the medium is the point — generative, interactive, or time-based — and get it running somewhere a stranger can open it.",
        "publish": "Publish it with a process note: what you tried first, why it failed, and what the failure taught you about the medium.",
        "skill": "colour and contrast — why a palette reads instantly to everyone or quietly excludes people",
        "skillKey": "colour-contrast"
    },
    "social-entrepreneur": {
        "project": "Pick one problem you have watched someone live with, then find the five organisations already working on it and write down honestly what is missing.",
        "publish": "Share the map — who is doing what, where the gap is, and what you would try first with no money.",
        "skill": "unit economics — working out what one unit of the change you want actually costs to deliver",
        "skillKey": "unit-economics"
    },
    "quantitative-economist": {
        "project": "Take one public dataset about something you care about and answer one question with it — then write down every reason your answer might be wrong.",
        "publish": "Post the chart, the code, and the caveats, with the caveats given as much room as the finding.",
        "skill": "causal inference — why a correlation in observational data is almost never the answer to a policy question",
        "skillKey": "causal-inference"
    },
    "investigative-journalist": {
        "project": "Find one claim being repeated locally that nobody has checked, and go check it against a primary source — a budget, a filing, a dataset.",
        "publish": "Write it up in 600 words, link every source, and state plainly what you could not confirm.",
        "skill": "public records — finding the document that already exists and that nobody has read",
        "skillKey": "public-records"
    },
    "science-policy-advocate": {
        "project": "Read one real bill that touches science or health, all the way through, and write a one-page brief on what it actually does versus what it is described as doing.",
        "publish": "Send the brief to someone whose job it is to care — a staffer, a local reporter, a teacher — and ask for one correction.",
        "skill": "legislative reading — how a bill is structured, where the money is, and which clause does the real work",
        "skillKey": "legislative-reading"
    },
    "public-health-strategist": {
        "project": "Pick one health outcome in your own county, find its rate, and compare it to the state — then work out what would have to be true for the difference to be real.",
        "publish": "Publish the comparison with the denominator stated as prominently as the number.",
        "skill": "rates and denominators — why per-100,000 and age-adjustment routinely reverse the obvious answer",
        "skillKey": "rates-denominators"
    },
    "sports-scientist": {
        "project": "Measure one thing about one athlete — yourself counts — across two weeks, on a schedule you commit to before you start.",
        "publish": "Post the data and the protocol, including the sessions you missed and what that does to the conclusion.",
        "skill": "measurement validity — checking that your instrument measures the thing you think it measures",
        "skillKey": "measurement-validity"
    },
    "bioethicist": {
        "project": "Take one live disagreement in biology or medicine and write the strongest version of the argument you disagree with, in its own terms.",
        "publish": "Publish both sides mapped out — claims, premises, and the assumption each side will not give up.",
        "skill": "argument mapping — pulling a claim apart into its premises and finding the one nobody is defending",
        "skillKey": "argument-mapping"
    },
    "edtech-creator": {
        "project": "Teach one specific thing to one specific person who does not get it yet, then rebuild your explanation after watching where they stalled.",
        "publish": "Ship the explanation as something reusable — a page, a worksheet, a small tool — and note what you cut.",
        "skill": "learning science — spacing, retrieval practice, and why re-reading feels productive and mostly is not",
        "skillKey": "learning-science"
    },
    "conservation-storyteller": {
        "project": "Document one species or one place near you over two weeks, with your own observations, and get one fact checked by someone who studies it.",
        "publish": "Publish the piece with your field notes attached, so the reader can see what you saw and what you inferred.",
        "skill": "getting the biology right — reading a species account well enough that a specialist would not wince",
        "skillKey": "species-accuracy"
    }
}


def spine_for(archetype_id: str) -> dict[str, str] | None:
    """The authored spine for an archetype, or None if there is none."""
    return SPINES.get(archetype_id)
