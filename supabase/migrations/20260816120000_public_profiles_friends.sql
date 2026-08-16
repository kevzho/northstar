-- The evidence record goes social: opt-in public profiles and friendships.
--
-- handle: a chosen, unique, url-safe name (northstar.app/p/<handle>).
-- public_profile: OFF by default — minors' records are private until the
-- student explicitly shares. The public page shows highlights only
-- (positive outcomes); the full comparison is reserved for accepted
-- friends.
-- chosen_archetype/kind: the charted path, synced from the frontend so
-- "career choices" are comparable between friends.

alter table public.students
    add column if not exists handle text;

alter table public.students
    add column if not exists public_profile boolean not null default false;

alter table public.students
    add column if not exists chosen_archetype text;

alter table public.students
    add column if not exists chosen_kind text;

create unique index if not exists students_handle_key
    on public.students (lower(handle))
    where handle is not null;

create table public.friendships (
    id uuid primary key default gen_random_uuid(),
    requester uuid not null references public.students(id) on delete cascade,
    addressee uuid not null references public.students(id) on delete cascade,
    status text not null default 'pending' check (status in ('pending', 'accepted')),
    created_at timestamptz not null default now(),
    unique(requester, addressee),
    check (requester <> addressee)
);

alter table public.friendships enable row level security;

create policy "Parties see their own friendships" on public.friendships
    for select using (auth.uid() in (requester, addressee));
create policy "Students send their own requests" on public.friendships
    for insert with check (auth.uid() = requester);
create policy "Addressee accepts" on public.friendships
    for update using (auth.uid() = addressee);
create policy "Either party removes" on public.friendships
    for delete using (auth.uid() in (requester, addressee));

create index friendships_addressee_idx on public.friendships (addressee);
