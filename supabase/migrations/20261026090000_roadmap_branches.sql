-- Sub-steps a student asked for, under one step of their own plan.
--
-- WHAT THIS IS FOR. The roadmap says "Build a simple web app that lets a local
-- business calculate break-even". For a student who has never shipped
-- anything, that is one instruction with a cliff in the middle of it. The plan
-- could not be interrogated: you could regenerate the whole spine or accept it
-- as written, and nothing in between.
--
-- A branch is the in-between. Point at any step and get two or three concrete
-- moves that make up that step, written from the same profile and the same
-- matched opportunities as the plan they hang off.
--
-- ONE ROW PER (student, parent step), replaced in place. A student who asks
-- twice wants a different answer, not a second list -- and an unbounded
-- children table behind a button on a diagram is how a plan becomes a
-- thousand-item outline nobody reads.

create table if not exists public.roadmap_branches (
    user_id uuid not null
        references auth.users (id) on delete cascade,

    -- The step this hangs under: a step_key from app/roadmap.py, e.g.
    -- "spine:project" or "apply:<uuid>". Not a foreign key -- roadmap steps
    -- are computed per request and have no table of their own.
    parent_step_key text not null,

    -- [{title, detail}], 2-3 of them. Validated by app/branch_generation.py
    -- before it ever gets here: no urls, no named programmes, no empty prose,
    -- length capped, duplicates refused.
    steps jsonb not null,

    model text,
    created_at timestamptz not null default now(),

    primary key (user_id, parent_step_key)
);

comment on table public.roadmap_branches is
    'Model-written sub-steps under one step of a student plan. One row per '
    '(student, parent step), replaced on regeneration. See '
    'app/branch_generation.py for what is refused before a row exists.';

create index if not exists roadmap_branches_user_idx
    on public.roadmap_branches (user_id);

-- Writes go through FastAPI on the service role, like every other table since
-- 20260921120000_rls_lockdown.sql. A client that could write here could put
-- arbitrary text inside a student's own plan.
alter table public.roadmap_branches enable row level security;

revoke select, insert, update, delete on public.roadmap_branches from anon;
revoke select, insert, update, delete on public.roadmap_branches from authenticated;
