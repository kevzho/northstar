-- Northstar V1 database schema
-- Paste this into Supabase SQL Editor and run it once.

create extension if not exists "pgcrypto";

create type public.behaviour_event_type as enum ('scenario', 'microtask');
create type public.future_path_type as enum ('safe', 'ambitious', 'unconventional');
create type public.action_timeframe as enum ('week', 'month');
create type public.action_category as enum ('project', 'outreach', 'skill', 'application');
create type public.action_status as enum ('planned', 'in_progress', 'done');

create table public.students (
  id uuid primary key references auth.users(id) on delete cascade,
  name text,
  email text,
  grade text,
  interests text[] not null default '{}',
  goals text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.behaviour_events (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students(id) on delete cascade,
  event_type public.behaviour_event_type not null,
  prompt_id text not null,
  choice_id text,
  raw_response jsonb not null default '{}'::jsonb,
  duration_ms integer check (duration_ms is null or duration_ms >= 0),
  created_at timestamptz not null default now()
);

create table public.latent_profiles (
  student_id uuid primary key references public.students(id) on delete cascade,
  builder double precision not null default 0 check (builder >= 0 and builder <= 100),
  analyst double precision not null default 0 check (analyst >= 0 and analyst <= 100),
  risk_tolerance double precision not null default 0 check (risk_tolerance >= 0 and risk_tolerance <= 100),
  ambiguity_comfort double precision not null default 0 check (ambiguity_comfort >= 0 and ambiguity_comfort <= 100),
  collaboration double precision not null default 0 check (collaboration >= 0 and collaboration <= 100),
  execution_tempo double precision not null default 0 check (execution_tempo >= 0 and execution_tempo <= 100),
  updated_at timestamptz not null default now()
);

create table public.future_paths (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students(id) on delete cascade,
  label text not null,
  path_type public.future_path_type not null,
  suitability_score double precision not null default 0 check (suitability_score >= 0 and suitability_score <= 100),
  risk_score double precision not null default 0 check (risk_score >= 0 and risk_score <= 100),
  summary text not null,
  created_at timestamptz not null default now()
);

create table public.actions (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students(id) on delete cascade,
  future_path_id uuid references public.future_paths(id) on delete cascade,
  title text not null,
  timeframe public.action_timeframe not null,
  category public.action_category not null,
  status public.action_status not null default 'planned',
  due_date date,
  completed_at timestamptz,
  created_at timestamptz not null default now()
);

create index behaviour_events_student_created_idx
  on public.behaviour_events (student_id, created_at desc);

create index future_paths_student_created_idx
  on public.future_paths (student_id, created_at desc);

create index actions_student_status_idx
  on public.actions (student_id, status);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger students_set_updated_at
before update on public.students
for each row execute function public.set_updated_at();

create trigger latent_profiles_set_updated_at
before update on public.latent_profiles
for each row execute function public.set_updated_at();

alter table public.students enable row level security;
alter table public.behaviour_events enable row level security;
alter table public.latent_profiles enable row level security;
alter table public.future_paths enable row level security;
alter table public.actions enable row level security;

create policy "Students can read own profile"
on public.students for select
using (auth.uid() = id);

create policy "Students can insert own profile"
on public.students for insert
with check (auth.uid() = id);

create policy "Students can update own profile"
on public.students for update
using (auth.uid() = id)
with check (auth.uid() = id);

create policy "Students can manage own behaviour events"
on public.behaviour_events for all
using (auth.uid() = student_id)
with check (auth.uid() = student_id);

create policy "Students can manage own latent profile"
on public.latent_profiles for all
using (auth.uid() = student_id)
with check (auth.uid() = student_id);

create policy "Students can manage own future paths"
on public.future_paths for all
using (auth.uid() = student_id)
with check (auth.uid() = student_id);

create policy "Students can manage own actions"
on public.actions for all
using (auth.uid() = student_id)
with check (auth.uid() = student_id);
