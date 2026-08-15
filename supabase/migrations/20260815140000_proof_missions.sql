-- Proof missions v1 — the evolving profile grows by doing, not quizzing.
--
-- A mission is a small, real-world task tied to an archetype (future
-- path) and the trait it exercises. Completing one writes evidence onto
-- the student record (mission_completions), which the timeline renders
-- and later phases (readiness gaps, behavioral calibration) consume.
-- Missions are catalog content, readable by anyone; completions are the
-- student's own. unique(student_id, mission_id) makes completion
-- idempotent by construction.

create table public.missions (
    id uuid primary key default gen_random_uuid(),
    archetype_id text not null,
    title text not null,
    description text not null,
    -- TraitKey from frontend/lib/assessment.ts: builder | analyst |
    -- riskTolerance | ambiguityComfort | collaboration | executionTempo
    trait_focus text not null,
    effort text not null default 'a weekend',
    sort_order integer not null default 0,
    created_at timestamptz not null default now(),
    unique(archetype_id, title)
);

create table public.mission_completions (
    id uuid primary key default gen_random_uuid(),
    student_id uuid not null references public.students(id) on delete cascade,
    mission_id uuid not null references public.missions(id) on delete cascade,
    -- A link or one-line proof; the point is the habit of evidence.
    evidence text not null default '',
    created_at timestamptz not null default now(),
    unique(student_id, mission_id)
);

alter table public.missions enable row level security;
alter table public.mission_completions enable row level security;

create policy "Missions are readable by anyone" on public.missions
    for select using (true);
create policy "Students manage own completions" on public.mission_completions
    for all using (auth.uid() = student_id) with check (auth.uid() = student_id);

create index mission_completions_student_idx
    on public.mission_completions (student_id);

-- Seed: three missions per archetype, ordered easy -> bold.
insert into public.missions (archetype_id, title, description, trait_focus, effort, sort_order) values
('applied-ai-builder', 'Ship a tiny model demo', 'Train a small classifier on data you collected yourself and deploy it anywhere public. The model can be simple; the demo link is the proof.', 'builder', 'a weekend', 1),
('applied-ai-builder', 'Reproduce one published result', 'Pick a single figure from an accessible ML paper or blog post and reproduce it in a notebook. Write five lines on where your numbers differed and why.', 'analyst', 'a weekend', 2),
('applied-ai-builder', 'Demo to five strangers', 'Show your demo to five people outside your family. Log what confused each of them and change one thing in response.', 'riskTolerance', 'an afternoon', 3),

('computational-biology-researcher', 'Analyze a public dataset', 'Pull a dataset from NCBI or a public genomics archive and answer one concrete question with a notebook: a plot, a table, and a paragraph.', 'analyst', 'a weekend', 1),
('computational-biology-researcher', 'Interview a working scientist', 'Get twenty minutes with someone who works in a lab (email works better than you think). Publish five takeaways about what their day actually looks like.', 'collaboration', 'an afternoon', 2),
('computational-biology-researcher', 'Visualize a biological process', 'Build one clear, honest visualization of a process you find fascinating and post it where someone can critique it.', 'builder', 'a weekend', 3),

('technical-founder', 'Sell it before you build it', 'Put up a landing page for an idea and get ten real signups before writing product code. The signup list is the evidence.', 'riskTolerance', 'a weekend', 1),
('technical-founder', 'Ship an MVP in seven days', 'Scope ruthlessly and ship a working first version of anything in one week. Publish the link and what you cut to make the deadline.', 'executionTempo', 'two weeks', 2),
('technical-founder', 'Run five user interviews', 'Interview five people who have the problem you think you are solving. Document the one assumption they broke.', 'collaboration', 'a weekend', 3),

('product-minded-engineer', 'Land an open-source fix', 'Find a paper-cut bug or docs gap in a tool you actually use and submit the fix. The PR link is the evidence, merged or not.', 'builder', 'a weekend', 1),
('product-minded-engineer', 'Write a product teardown', 'Pick an app you admire and dissect its onboarding: every screen, every choice, what you would change. Publish it.', 'analyst', 'an afternoon', 2),
('product-minded-engineer', 'Change one thing from data', 'Add basic analytics to something you have built, watch it for a week, and make one change the numbers argue for.', 'executionTempo', 'two weeks', 3),

('civic-technology-designer', 'Write a local problem brief', 'Talk to three people affected by one concrete local problem. Write a one-page brief: who hurts, how often, what exists already.', 'ambiguityComfort', 'a weekend', 1),
('civic-technology-designer', 'Prototype the civic fix', 'Build the smallest thing that addresses your brief - a form, a map, a text alert. Ugly is fine; real is required.', 'builder', 'two weeks', 2),
('civic-technology-designer', 'Present to a stakeholder', 'Show the prototype to someone who could actually deploy it: a librarian, a council member, a school administrator. Log their objections.', 'collaboration', 'an afternoon', 3),

('research-mathematician', 'Write up three solved problems', 'Solve three competition problems just beyond your comfort level and write full solutions someone else could learn from.', 'analyst', 'a weekend', 1),
('research-mathematician', 'Teach one proof', 'Pick a proof you love and teach it to a peer until they can reproduce it. Record the session or their write-up as evidence.', 'collaboration', 'an afternoon', 2),
('research-mathematician', 'Explore a conjecture computationally', 'Take an open or classroom conjecture and explore it with code: search for counterexamples, plot the pattern, write what you noticed.', 'ambiguityComfort', 'two weeks', 3),

('experimental-physicist', 'Measure a constant at home', 'Measure gravitational acceleration or the speed of sound with household equipment. Report the value, the uncertainty, and the setup.', 'builder', 'an afternoon', 1),
('experimental-physicist', 'Do the error analysis properly', 'Take any measurement you have made and write a real uncertainty analysis: sources, propagation, what dominates, how you would halve it.', 'analyst', 'an afternoon', 2),
('experimental-physicist', 'Replicate a classic experiment', 'Reproduce a classic - double-slit with a laser pointer, a pendulum period study - and present it as a short lab report.', 'executionTempo', 'a weekend', 3),

('robotics-engineer', 'Make something move', 'Build the smallest thing that moves under its own control: a servo arm, a line follower, a cardboard gripper. Post the video.', 'builder', 'a weekend', 1),
('robotics-engineer', 'Simulate before you build', 'Model one mechanism in any simulator before building it. Compare what the simulation predicted with what the build did.', 'analyst', 'a weekend', 2),
('robotics-engineer', 'Join one build sprint', 'Spend a working session with a robotics team or makerspace. Contribute one concrete thing and document what you built.', 'collaboration', 'an afternoon', 3),

('biomedical-innovator', 'Interview a clinician', 'Get twenty minutes with a nurse, EMT, or doctor about the most annoying broken thing in their workflow. Five documented takeaways.', 'collaboration', 'an afternoon', 1),
('biomedical-innovator', 'Prototype an assistive fix', 'Build the crudest possible version of something that helps one person with one physical difficulty. One user, one test, one photo.', 'builder', 'two weeks', 2),
('biomedical-innovator', 'Survey the literature', 'Read three papers on one condition or device and write a one-page synthesis a smart friend could follow.', 'analyst', 'a weekend', 3),

('data-scientist', 'Clean an ugly dataset', 'Find a genuinely messy public dataset and publish the cleaned version with a README describing every judgment call you made.', 'analyst', 'a weekend', 1),
('data-scientist', 'Publish one chart that changes a mind', 'Make a single visualization that made you see something differently, and post it with two sentences of honest caveats.', 'builder', 'an afternoon', 2),
('data-scientist', 'Forecast and score yourself', 'Write down ten probabilistic predictions about the next month. When the month ends, score your calibration publicly.', 'riskTolerance', 'two weeks', 3),

('science-communicator', 'Explain one hard idea', 'Take a concept you struggled with and explain it for a specific audience - a younger sibling, a grandparent - in a post or short video.', 'collaboration', 'an afternoon', 1),
('science-communicator', 'Get edited', 'Submit a piece to a school paper, newsletter, or blog that edits. Incorporate the feedback and publish both versions.', 'ambiguityComfort', 'a weekend', 2),
('science-communicator', 'Teach a live session', 'Run a fifteen-minute lesson for real students - a club, a class, a library group. The slides and one attendee quote are the evidence.', 'executionTempo', 'a weekend', 3),

('field-research-scientist', 'Keep a 30-day observation log', 'Observe one natural system daily for a month - a tree, a stream, the night sky - with dated notes and at least one surprise.', 'executionTempo', 'two weeks', 1),
('field-research-scientist', 'Contribute to community science', 'Upload twenty verified observations to iNaturalist, eBird, or a similar platform. Your contributor profile is the evidence.', 'collaboration', 'a weekend', 2),
('field-research-scientist', 'Design a field protocol', 'Write a repeatable protocol for measuring something outdoors - transects, counts, timing - and run it once end to end.', 'ambiguityComfort', 'a weekend', 3)
on conflict (archetype_id, title) do nothing;
