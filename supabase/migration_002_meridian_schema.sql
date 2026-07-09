-- Meridian core schema migration
-- Adds the domain tables required for the CAC demo path beyond the Northstar V1 schema.
-- Run this in Supabase SQL Editor after schema.sql (Northstar V1) or via supabase db push.

-- 1. Extensions
-- pgvector is required for semantic mentor matching (Day 5).
create extension if not exists "vector";

-- 2. Enums
create type public.opportunity_field as enum (
    'cs', 'biology', 'math', 'physics', 'engineering', 'interdisciplinary'
);

create type public.opportunity_type as enum (
    'program', 'scholarship', 'competition', 'mentorship'
);

create type public.outcome_status as enum (
    'accepted', 'rejected', 'waitlisted', 'withdrew', 'completed'
);

-- 3. Tables
-- opportunities: crawled + curated STEM listings
create table public.opportunities (
    id uuid primary key default gen_random_uuid(),
    title text not null,
    host text not null,
    opportunity_field public.opportunity_field not null,
    type public.opportunity_type not null,
    blurb text not null default '',
    description text not null default '',
    deadline date,
    cost integer not null default 0 check (cost >= 0),
    grade_min integer not null default 9 check (grade_min between 6 and 12),
    grade_max integer not null default 12 check (grade_max between 6 and 12),
    url text not null,
    tags text[] not null default '{}',
    location text,
    created_at timestamptz not null default now()
);

-- pathway_nodes: each node is an opportunity in a particular cohort year
create table public.pathway_nodes (
    id uuid primary key default gen_random_uuid(),
    opportunity_id uuid not null references public.opportunities(id) on delete cascade,
    cohort_tag text not null default '2026',
    created_at timestamptz not null default now()
);

-- pathway_edges: directed, weighted transitions between nodes
create table public.pathway_edges (
    id uuid primary key default gen_random_uuid(),
    source_node_id uuid not null references public.pathway_nodes(id) on delete cascade,
    target_node_id uuid not null references public.pathway_nodes(id) on delete cascade,
    weight double precision not null default 1.0 check (weight >= 0),
    evidence_url text,
    created_at timestamptz not null default now(),
    check (source_node_id <> target_node_id)
);

-- mentors: volunteer mentors with expertise and embedding stub
create table public.mentors (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    email text not null unique,
    bio text not null default '',
    expertise text[] not null default '{}',
    bio_embedding vector(384),      -- for sentence-transformers similarity
    created_at timestamptz not null default now()
);

-- mentor_sessions: a booked session between a student and a mentor
create table public.mentor_sessions (
    id uuid primary key default gen_random_uuid(),
    student_id uuid not null references public.students(id) on delete cascade,
    mentor_id uuid not null references public.mentors(id) on delete cascade,
    scheduled_at timestamptz,
    status text not null default 'pending' check (status in ('pending','confirmed','completed','cancelled')),
    notes text,
    created_at timestamptz not null default now()
);

-- outcomes: student-reported results for bookmarked opportunities
create table public.outcomes (
    id uuid primary key default gen_random_uuid(),
    student_id uuid not null references public.students(id) on delete cascade,
    opportunity_id uuid not null references public.opportunities(id) on delete cascade,
    status public.outcome_status not null,
    impact_notes text,
    created_at timestamptz not null default now()
);

-- bookmarks: many-to-many between students and opportunities
create table public.bookmarks (
    id uuid primary key default gen_random_uuid(),
    student_id uuid not null references public.students(id) on delete cascade,
    opportunity_id uuid not null references public.opportunities(id) on delete cascade,
    created_at timestamptz not null default now(),
    unique(student_id, opportunity_id)
);

-- matches: persisted TF-IDF / hybrid recommendations
create table public.matches (
    id uuid primary key default gen_random_uuid(),
    student_id uuid not null references public.students(id) on delete cascade,
    opportunity_id uuid not null references public.opportunities(id) on delete cascade,
    score double precision not null check (score >= 0 and score <= 1),
    explanation text not null default '',
    created_at timestamptz not null default now(),
    unique(student_id, opportunity_id)
);

-- 4. RLS policies (Student ownership: each row belongs to the authenticated user)
--    Using auth.uid() = student_id, mirroring the Northstar V1 RLS pattern.

alter table public.opportunities      enable row level security;
alter table public.pathway_nodes      enable row level security;
alter table public.pathway_edges      enable row level security;
alter table public.mentors            enable row level security;
alter table public.mentor_sessions      enable row level security;
alter table public.outcomes           enable row level security;
alter table public.bookmarks          enable row level security;
alter table public.matches            enable row level security;

-- opportunities: anyone can read; only admins insert/update (managed outside RLS for MVP)
create policy "Opportunities are readable by anyone" on public.opportunities
    for select using (true);

create policy "Opportunities are insertable by service role" on public.opportunities
    for insert with check (true);   -- service key bypasses RLS in Supabase

-- pathway_nodes: readable by anyone
create policy "Pathway nodes are readable by anyone" on public.pathway_nodes
    for select using (true);

-- pathway_edges: readable by anyone
create policy "Pathway edges are readable by anyone" on public.pathway_edges
    for select using (true);

-- mentors: readable by anyone
create policy "Mentors are readable by anyone" on public.mentors
    for select using (true);

-- mentor_sessions: students manage their own
create policy "Students manage own mentor sessions" on public.mentor_sessions
    for all using (auth.uid() = student_id) with check (auth.uid() = student_id);

-- outcomes: students manage their own
create policy "Students manage own outcomes" on public.outcomes
    for all using (auth.uid() = student_id) with check (auth.uid() = student_id);

-- bookmarks: students manage their own
create policy "Students manage own bookmarks" on public.bookmarks
    for all using (auth.uid() = student_id) with check (auth.uid() = student_id);

-- matches: students manage their own
create policy "Students manage own matches" on public.matches
    for all using (auth.uid() = student_id) with check (auth.uid() = student_id);

-- 5. Indexes for performance

create index idx_opportunities_field    on public.opportunities (opportunity_field);
create index idx_opportunities_type     on public.opportunities (type);
create index idx_opportunities_deadline on public.opportunities (deadline);

create index idx_pathway_edges_source   on public.pathway_edges (source_node_id);
create index idx_pathway_edges_target   on public.pathway_edges (target_node_id);

create index idx_bookmarks_student      on public.bookmarks (student_id);
create index idx_bookmarks_opportunity  on public.bookmarks (opportunity_id);

create index idx_matches_student        on public.matches (student_id);
create index idx_matches_score          on public.matches (score desc);

-- pgvector index for semantic mentor search (stub — created once embeddings exist)
create index idx_mentors_bio_embedding on public.mentors
    using ivfflat (bio_embedding vector_cosine_ops)
    with (lists = 100);
