-- Profile history — shift tracking moves server-side.
--
-- Every assessment sync appends a snapshot (unless nothing changed), so
-- "your profile shifted: cs +16" is computed from durable history
-- instead of a localStorage snapshot that dies with the browser. This
-- table is the seed of the evidence timeline.

create table public.profile_history (
    id uuid primary key default gen_random_uuid(),
    student_id uuid not null references public.students(id) on delete cascade,
    trait_scores jsonb not null,
    field_scores jsonb not null,
    created_at timestamptz not null default now()
);

alter table public.profile_history enable row level security;

create policy "Students manage own profile history" on public.profile_history
    for all using (auth.uid() = student_id) with check (auth.uid() = student_id);

create index profile_history_student_time_idx
    on public.profile_history (student_id, created_at desc);
