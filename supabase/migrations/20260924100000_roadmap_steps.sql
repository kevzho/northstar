-- Turn public.actions into roadmap steps.
--
-- The table has sat at 0 rows since the v1 schema, and its action_category enum
-- is already ('project','outreach','skill','application') -- exactly the four
-- kinds of step a roadmap needs. What it lacks is ordering, provenance, and a
-- stable identity across regenerations.
--
-- WHY THE ROADMAP IS NOT BUILT FROM DEADLINES. Measured against production:
--
--   grade  eligible  with a future deadline
--     9      36/61            1
--    10      44/61            1
--    11      55/61            1
--    12      61/61            4
--
-- A 9th grader has ONE thing in the entire catalog they can apply to today. A
-- sequencer anchored on deadlines has nothing to say to them, and the only
-- "unlock" it can offer is a birthday. So the time axis is the student's grade
-- progression, and the steps that fill the near term are things available now:
-- a free resource to learn from, the spine's project, the publish step. An
-- application is a step only when it is genuinely open.
--
-- PROVENANCE IS A FOREIGN KEY, NOT A STRING. opportunity_id and resource_id
-- mean a step naming a program or a course that is not in the catalog cannot be
-- inserted at all. That is a stronger guarantee than any prompt or validation
-- layer, and it is why no model runs in the serving path.

alter table public.actions
    -- Ordering within a roadmap generation.
    add column if not exists ordinal integer not null default 0,
    add column if not exists phase_index integer not null default 0,
    -- "Fall of 11th grade" — a grade term, never a fabricated month.
    add column if not exists phase_label text not null default '',

    -- Stable across regenerations, so completing a step survives one. This is
    -- what a prior review caught: regenerating by delete-and-reinsert silently
    -- destroyed every checked-off step on a timer.
    add column if not exists step_key text not null default '',
    add column if not exists generation integer not null default 1,

    -- Provenance. set null rather than cascade: retiring an opportunity must
    -- not delete a step a student already completed.
    add column if not exists opportunity_id uuid
        references public.opportunities(id) on delete set null,
    add column if not exists resource_id uuid
        references public.learning_resources(id) on delete set null,
    add column if not exists mission_id uuid
        references public.missions(id) on delete set null,

    -- Why this step sits here. 'eligibility' and 'window' are computed calendar
    -- facts; 'artifact', 'ladder' and 'evidence' are authored generalisations
    -- and are worded as such in the UI ("a common route", never "required").
    add column if not exists edge_reason text not null default '',
    add column if not exists edge_note text not null default '',

    -- Skipping advances the sequence without pretending the step was done. A
    -- column rather than a new enum value, because enum values cannot be
    -- dropped in Postgres.
    add column if not exists skipped_at timestamptz;

-- action_timeframe is `not null` with NO default, so every insert must supply
-- it or fail. Two separate designs missed this.
alter table public.actions alter column timeframe set default 'month';

create index if not exists actions_roadmap_order_idx
    on public.actions (student_id, generation, ordinal);

-- One row per (student, generation, step). Makes completion upsert-idempotent
-- and regeneration a merge rather than a rebuild.
create unique index if not exists actions_student_gen_step_idx
    on public.actions (student_id, generation, step_key)
    where step_key <> '';

-- RLS: the existing policy is `for all`, which over PostgREST would let a
-- student rewrite their own step's title and opportunity_id — destroying the
-- provenance the foreign keys exist to guarantee. Reads stay open to the owner;
-- writes go through FastAPI on the service role, matching how missions and
-- advisor_calls are already served.
drop policy if exists "Students can manage own actions" on public.actions;

create policy "Students read own actions"
    on public.actions for select
    to anon, authenticated
    using (auth.uid() = student_id);

revoke insert, update, delete on public.actions from anon;
revoke insert, update, delete on public.actions from authenticated;
