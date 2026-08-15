-- The evolving profile, part 1: the assessment moves server-side, and
-- students get a way to say "not for me".
--
-- trait_scores / field_scores hold the quiz outputs (six 0-100 trait
-- signals; six field-interest shares summing to 100) so matching can
-- weight the field boost by how strongly a field actually leads, and so
-- the profile survives a device change. jsonb because the shapes are
-- owned by frontend/lib/scoring.ts and evolve with the question bank.
--
-- dismissals mirror bookmarks: the cheapest negative signal there is.
-- A dismissed opportunity is excluded from /match until undismissed.

alter table public.students
    add column if not exists trait_scores jsonb;

alter table public.students
    add column if not exists field_scores jsonb;

comment on column public.students.trait_scores is
    'Assessment trait signals (0-100 each), synced from the quiz.';
comment on column public.students.field_scores is
    'Field-interest shares summing to 100, synced from the quiz.';

create table public.dismissals (
    id uuid primary key default gen_random_uuid(),
    student_id uuid not null references public.students(id) on delete cascade,
    opportunity_id uuid not null references public.opportunities(id) on delete cascade,
    created_at timestamptz not null default now(),
    unique(student_id, opportunity_id)
);

alter table public.dismissals enable row level security;

create policy "Students manage own dismissals" on public.dismissals
    for all using (auth.uid() = student_id) with check (auth.uid() = student_id);

create index dismissals_student_idx on public.dismissals (student_id);
