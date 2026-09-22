# Post-MVP roadmap — the longitudinal decision system

Captured 2026-08-15 from Kevin's product direction. This document governs
what gets built after the CAC submission. The thesis:

> Don't add generic resume tools, a chat tab, or a giant opportunity
> directory. Northstar becomes a **longitudinal decision system**: it
> observes choices, tests assumptions, shows tradeoffs, and turns a
> student's stated future into weekly evidence.

Ordered by product leverage, not coolness. Continuous guidance and
milestone tracking beat a one-time career quiz.

## The core moat: a living model

### 1. Behavioral calibration loops
Periodically test whether the profile is right instead of presenting trait
scores as truth: "You said you like open-ended building. This week, try a
25-minute ambiguous product task. Did it energize or drain you?"

- **Micro-experiments**: mini research prompt, debugging task, design
  brief, outreach challenge, data-analysis task.
- **Self-report after the task**: energy, difficulty, pride, desire to
  continue.
- **Behavioral telemetry**: completion, time taken, retries, optional
  artifacts.
- **Trait updates with provenance**: "Your independent execution score
  increased because you repeatedly completed open-ended tasks without
  external structure."

The single best differentiation: an adaptive hypothesis-testing system,
not a personality quiz. Never claim it "knows who you are" — it is an
evolving model with confidence ranges.

### 2. "Prove the path" missions
Every recommended path requires evidence, not just "I'm interested."
Each future path gets a compact 7-day proof mission:

| Path | 7-day proof mission | Signal learned |
|---|---|---|
| ML engineer | Train and explain a small classifier on a real dataset | Technical iteration, debugging stamina, model curiosity |
| Computational biologist | Reproduce one notebook on biological data, write findings | Scientific reasoning, data patience, domain interest |
| Product builder | Interview 3 users and ship a tiny prototype | Initiative, user empathy, execution |
| Researcher | Read one paper, identify its claim, propose an experiment | Abstraction, evidence reasoning, persistence |
| Designer/creator | Turn a brief into 3 visual directions, defend one | Creative exploration, communication, taste |

Close the loop: "Your confidence in this path changed from 62% to 74%
because you completed the experiment, rated it highly, and chose to
extend it."

## Future simulation that isn't fake

### 3. Counterfactual path simulator (flagship visual)
Compare two or three plausible routes (research-heavy / builder-heavy /
exploration-first). Each route shows: time per week, cost and access
constraints, prerequisite skills, likely milestones, common failure
points, what the student gives up, and a confidence range. Product
language: "This is not a prediction. It is a planning model based on your
current signals and stated constraints." Grounded in actual student
experiments and constraint-aware pathways.

### 4. Decision journal + hindsight engine
Capture every major choice: what was chosen, the alternatives, the why,
confidence, expected outcome, constraints at the time. Revisit at 3/6
months: did it work, what surprised you, same choice again? Produce real
insight: "You tend to underestimate projects requiring external
coordination, but consistently overperform on self-directed technical
work." Creates longitudinal behavioral data that is hard to clone.

## Northstar-specific features

### 5. Opportunity-to-readiness gap analysis
"You are 2 evidence pieces away from being ready for this." Per
opportunity: what it selects for, current evidence, missing evidence, and
the smallest next move that closes one gap. Transforms discovery into
action.

### 6. Deadline-aware opportunity routing
Prioritize by what must happen before the deadline, not just match score:
reverse-plan from deadlines, detect conflicts, recommend a portfolio of
applications (not one lottery ticket), track task completion, flag
stalled paths, explain why a recommendation changed.

### 7. Mentor matching with an agenda
Not "LinkedIn for mentors." Match on the current path, the exact blocker,
shared context (first-gen, region, school type), availability and past
helpfulness. Generate a one-page meeting brief: the decision at hand,
relevant artifacts, three questions to ask, a post-meeting action list.
The defensible feature is better mentor conversations with measurable
next actions.

### 8. Warm-introduction graph
Permissioned network layer over mentors/alumni/chapters: "You have two
warm paths to someone who did this program." Opt-in only, no private
contact exposure, request-based intros, transparent relationship
explanations.

## Student-facing "wow" features

### 9. Portfolio evidence graph
Not a resume builder — an evidence map: projects, coursework, clubs,
awards, writing → skills demonstrated → claims supported → future paths
strengthened. Tells the student what artifact is missing next.

### 10. Narrative stress test
A personal evidence auditor, not an essay generator: "You say you are
interested in biomedical AI. Show the evidence." Finds unsupported
claims, weak/repeated evidence, missing proof, and the next smallest
artifact that strengthens the narrative.

### 11. Parent / counselor co-pilot
Constrained, privacy-respecting view: chosen goals, near-term deadlines,
stalled items, the student's requested support. Never raw behavioral
answers or journal content. Framing: "Kevin needs an introduction to a
computational-biology mentor — not another reminder to 'work harder.'"

## What to avoid (unless users directly require it)

- A general chatbot named "Ask Northstar"
- Resume bullets generated from a prompt
- Generic college-major quizzes
- Fake salary predictions with unwarranted precision
- A huge scraped directory without verification
- Personality labels presented as diagnosis or destiny
- "AI predicts you will become X"

Easy to clone, low-trust, generic-AI-wrapper energy.

## Build order

| Phase | Build | Why |
|---|---|---|
| First after MVP | Calibration loops + proof missions | The adaptive moat |
| Next | Readiness gaps + deadline routing | Converts insight into outcomes |
| Then | Decision journal + hindsight engine | Longitudinal individual signal |
| Next | Mentor agenda + warm-intro graph | Makes the network actionable |
| Later | Evidence graph + narrative stress test | Application/portfolio value |
| Mature | Constraint-aware counterfactual simulator | The distinctive surface |

If only one post-MVP feature gets built: **proof missions + calibration.**
The honest claim: Northstar does not merely recommend a future; it helps
students run small experiments to discover which future to pursue.
