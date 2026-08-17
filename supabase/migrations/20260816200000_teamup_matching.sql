-- Team up: mutual-interest collaborator / study-buddy matching, plus the
-- safety layer it requires for an audience that includes minors.
--
-- This is collaborator matching, NOT dating: the pitch is "what I'm
-- building / studying", and the payoff of a match is a connection
-- (an accepted friendship), same as everywhere else in the social layer.
--
-- Safety posture:
-- - Matching is its own opt-in (teamup_enabled, default OFF), separate
--   from public_profile. Nobody is in the pool by default.
-- - Interest is one-directional and invisible to the target; only MUTUAL
--   interest creates a connection. "Did they pick me?" is never exposed.
-- - reports: any student can flag another; triage is service-role only.
-- - blocks: a hard one-way wall that removes the friendship and hides
--   both students from each other in discover, team-up, and requests.

alter table public.students
    add column if not exists teamup_enabled boolean not null default false;

alter table public.students
    add column if not exists teamup_pitch text;

create table public.teamup_interest (
    id uuid primary key default gen_random_uuid(),
    student uuid not null references public.students(id) on delete cascade,
    target uuid not null references public.students(id) on delete cascade,
    decision text not null check (decision in ('interested', 'passed')),
    created_at timestamptz not null default now(),
    unique (student, target),
    check (student <> target)
);

alter table public.teamup_interest enable row level security;

-- A student sees and manages only their own swipes. The reciprocal row is
-- never readable, so mutual interest can only be learned from a match.
create policy "Own interest rows" on public.teamup_interest
    for all using (auth.uid() = student) with check (auth.uid() = student);

create index teamup_interest_target_idx on public.teamup_interest (target);

create table public.reports (
    id uuid primary key default gen_random_uuid(),
    reporter uuid not null references public.students(id) on delete cascade,
    reported uuid not null references public.students(id) on delete cascade,
    reason text not null check (
        reason in ('inappropriate', 'harassment', 'impersonation', 'spam', 'other')
    ),
    details text,
    status text not null default 'open' check (status in ('open', 'resolved')),
    created_at timestamptz not null default now(),
    check (reporter <> reported)
);

alter table public.reports enable row level security;

-- Insert-only for students: reports are read and resolved by moderators
-- through the service role, never by other students.
create policy "Students file their own reports" on public.reports
    for insert with check (auth.uid() = reporter);

create table public.blocks (
    id uuid primary key default gen_random_uuid(),
    blocker uuid not null references public.students(id) on delete cascade,
    blocked uuid not null references public.students(id) on delete cascade,
    created_at timestamptz not null default now(),
    unique (blocker, blocked),
    check (blocker <> blocked)
);

alter table public.blocks enable row level security;

create policy "Own blocks" on public.blocks
    for all using (auth.uid() = blocker) with check (auth.uid() = blocker);

create index blocks_blocked_idx on public.blocks (blocked);
