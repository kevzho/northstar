-- One student's spine, written for them instead of assigned from twenty-four.
--
-- app/roadmap.py sequences learn -> build -> publish -> apply. The middle rungs
-- came from SPINES in frontend/lib/plan.ts: twenty-four entries keyed by
-- archetype, each naming a starter project, a publish step, and a skillKey that
-- joins to public.learning_resources.
--
-- Two measured problems with that, on 2026-10-04.
--
--   1. Twenty-four buckets is a genre, not a plan. A 9th grader who has shipped
--      nothing and a 12th grader with three projects both land on
--      "applied-ai-builder" and both read the same sentence about a study-note
--      summariser.
--
--   2. Half of them are hollow. Twelve of the twenty-four name a skillKey with
--      NO resource behind it -- argument-mapping, playtesting, public-records,
--      causal-inference and eight more -- so those students' learn rung renders
--      as nothing at all, and nothing says so.
--
-- WHY THIS IS A TABLE AND NOT A CALL PER PAGE VIEW. A plan that changes between
-- two visits is not a plan. A student who read "build a case file about a
-- gene-editing trial" on Tuesday and finds a different project on Thursday
-- cannot act on either, and the roadmap's whole claim is that the steps are in
-- an order worth following. So it is generated once, stored, and re-read.
-- Regeneration is deliberate (a new assessment, a changed grade), never
-- incidental.
--
-- NULLABLE BY ABSENCE, NOT BY COLUMN. A student with no row here falls back to
-- the authored spine for their archetype. That is the designed state, not a
-- degraded one: generation is refused outright when the model picks a skill key
-- with no resources, writes a url, or returns prose that will not parse, and in
-- every one of those cases the hand-written spine is the better answer. See
-- app/spine_generation.py.

create table if not exists public.generated_spines (
    user_id uuid primary key
        references auth.users (id) on delete cascade,

    -- The two the model writes, grounded in the student's traits, grade, field
    -- and their actual matched opportunities.
    project text not null,
    publish text not null,

    -- The two it does NOT write. skill_key is CHOSEN from the keys that have
    -- verified resources; skill is then copied from that key's
    -- learning_resources.skill_label. The first version let the model phrase the
    -- skill sentence and a test student got "Rigor — a bioethics case file is
    -- only as strong as its sources" attached to the key `regulatory-literacy`,
    -- which would have printed one claim and then linked resources about
    -- another.
    skill_key text not null,
    skill text not null,

    -- Provenance, because roadmap.py already distinguishes computed calendar
    -- facts from authored generalisations and words the second kind as "a common
    -- route, not a requirement". A generated spine is a third thing: no human
    -- wrote it and no outcome data supports it. Storing the model and the moment
    -- is what lets the UI say which it is, and lets a bad batch be found later.
    model text not null,
    source_archetype text,
    generated_at timestamptz not null default now()
);

comment on table public.generated_spines is
    'Per-student roadmap spine written by the model. Absent means fall back to '
    'the authored SPINES entry for the archetype, which is a designed state: '
    'generation is refused when it would produce an empty learn rung or an '
    'unverified link. See app/spine_generation.py.';

comment on column public.generated_spines.skill_key is
    'Chosen from keys with verified rows in public.learning_resources, never '
    'invented. An unknown key renders an empty learn rung, which is the defect '
    'this table exists to fix.';

alter table public.generated_spines enable row level security;

-- A student may read their own plan and nothing else. Writes come from the
-- service role only: the spine is provenance-bearing content, and a student
-- posting their own would destroy the guarantee the `model` column is making,
-- in the same way scripts/sync_spines.py exists so the backend never sequences
-- from client-supplied text.
create policy "A student reads their own generated spine"
    on public.generated_spines for select
    to authenticated
    using (auth.uid() = user_id);

revoke insert, update, delete on public.generated_spines from anon;
revoke insert, update, delete on public.generated_spines from authenticated;
