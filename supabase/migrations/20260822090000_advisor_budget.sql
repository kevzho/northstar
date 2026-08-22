-- Advisor spend control: a hard budget and a shared response cache.
--
-- /advisor is the only user-facing feature that spends LLM credits, and the
-- free NVIDIA NIM tier is a fixed pool of calls (~1,000), not a monthly
-- allowance. Nothing capped it: one signed-in student, or a retry loop in
-- the frontend, could drain the whole pool in about 25 minutes at the
-- provider's 40 requests/minute ceiling.
--
-- One row per BILLED model call. Cache hits deliberately do not insert, so
-- count(rows) is exactly "credits spent" — the ledger and the cache are the
-- same table, and the caps count the thing that actually costs money.
--
-- Why this lives in Postgres and not in process memory: the API runs on
-- serverless functions. An in-process counter resets on every cold start
-- and is per-instance, so concurrent lambdas would each grant a full quota
-- — which is no budget at all. app/projects.py's in-process cache is fine
-- because a stale miss only costs a GitHub call; here a miss costs credits.

create table public.advisor_calls (
    id uuid primary key default gen_random_uuid(),
    student uuid not null references public.students(id) on delete cascade,
    -- sha256 over the normalized question, the sources it was grounded in,
    -- and the model name. See app/advisor.py:cache_key.
    cache_key text not null,
    question text not null,
    answer text not null,
    sources jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now()
);

alter table public.advisor_calls enable row level security;

-- No policy, on purpose: this is service-role only. A student who could
-- read it would read other students' questions; a student who could delete
-- from it could reset their own quota.

-- Per-student daily quota.
create index advisor_calls_student_time_idx
    on public.advisor_calls (student, created_at desc);

-- Global daily budget and the per-minute burst guard.
create index advisor_calls_time_idx
    on public.advisor_calls (created_at desc);

-- Cache lookup: newest live answer for a key.
create index advisor_calls_cache_idx
    on public.advisor_calls (cache_key, created_at desc);
