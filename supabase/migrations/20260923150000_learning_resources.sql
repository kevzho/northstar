-- Free learning resources: the missing middle of a student's roadmap.
--
-- Northstar tells a student what to learn and never where. frontend/lib/plan.ts
-- gives each archetype a three-rung spine -- project, publish, skill -- and the
-- skill rung is a bare string: "statistics -- the hypothesis tests behind the
-- figure you reproduced". No link, no course, no book. A student who already
-- knows where to learn statistics did not need the instruction; a student who
-- does not is told to learn statistics.
--
-- It also fixes the structural hole in the opportunity-only roadmap. Of 61
-- live high-school opportunities, 4 have a usable future deadline and 31 are
-- locked behind a grade the student has not reached. So a 9th grader sees a
-- list of things they cannot do yet and nothing they can do today, and the
-- only "unlock" the sequencer can offer them is a birthday. A free course is
-- a real prerequisite: it is available now, it costs nothing, and finishing it
-- is what makes the locked program winnable in two years.
--
-- Deliberately a separate table from public.opportunities. These are not
-- programs: no deadline, no application, no eligibility, no host to apply to.
-- Conflating them would put "work through CS50" in a list sorted by deadline.
--
-- Every row carries verified_at and the evidence that it is free, because
-- this product has been burned: an audit of the 35 hand-authored opportunity
-- rows against each program's own website found ONE accurate. Nine were
-- retired. A resource catalog aimed at students with no money cannot afford a
-- paywalled link, so "free" is a checked claim with a quote behind it, not an
-- assumption.

create table if not exists public.learning_resources (
    id uuid primary key default gen_random_uuid(),

    title text not null,
    host text not null,               -- the institution or org behind it
    url text not null,

    kind text not null check (kind in (
        'course', 'textbook', 'pdf', 'interactive',
        'problem-set', 'video-series', 'documentation'
    )),

    -- What this teaches. skill_key matches the spine rung it serves (see
    -- frontend/lib/plan.ts SPINES[].skill); opportunity_field lets the matcher
    -- reach resources by a student's field interest as well as by archetype.
    skill_key text not null,
    skill_label text not null,
    opportunity_field public.opportunity_field,

    -- Honest effort, in a student's units: "a weekend", "4 weeks at 3h/week".
    effort text not null default 'a weekend',
    prerequisite text not null default 'none',
    why_this_one text not null,       -- why this over the alternatives

    -- The free claim, and its receipt. free_evidence quotes what the page
    -- actually says. A row with no evidence should not be shown.
    is_free boolean not null default true,
    free_evidence text not null default '',

    verified_at timestamptz,
    verified_note text,

    -- Same retirement contract as opportunities: stamp, never delete, so a
    -- student's completed step keeps its title.
    retired_at timestamptz,
    retired_reason text,

    added_by text not null default 'seed' check (added_by in ('seed', 'human', 'ai')),
    created_at timestamptz not null default now(),

    unique (url)
);

comment on table public.learning_resources is
    'Free, always-available material a student can start today, alone, for $0. '
    'Distinct from public.opportunities, which are programs with deadlines and '
    'eligibility. Rows are only shown when is_free is true, free_evidence is '
    'non-empty, and retired_at is null.';

create index if not exists learning_resources_skill_idx
    on public.learning_resources (skill_key)
    where retired_at is null;

create index if not exists learning_resources_field_idx
    on public.learning_resources (opportunity_field)
    where retired_at is null;

-- Read-only to clients, like opportunities. Writes go through FastAPI on the
-- service role. 20260921120000_rls_lockdown.sql established this stance after
-- an unscoped `for insert with check (true)` let anon write to the catalog;
-- this table starts there rather than arriving there later.
alter table public.learning_resources enable row level security;

create policy "Learning resources are readable by anyone"
    on public.learning_resources for select
    to anon, authenticated
    using (true);

revoke insert, update, delete on public.learning_resources from anon;
revoke insert, update, delete on public.learning_resources from authenticated;
