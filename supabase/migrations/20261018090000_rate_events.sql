-- Rate limiting that survives a serverless cold start.
--
-- WHY A TABLE AND NOT A COUNTER IN MEMORY. The API runs on Vercel functions:
-- instances are ephemeral, parallel, and share nothing, so an in-process
-- counter limits one lambda for a few minutes and nothing else. Anything that
-- must actually hold has to be written down somewhere both instances can see.
--
-- WHAT IT PROTECTS. Until now only the two LLM endpoints had any ceiling (see
-- advisor_calls + app/advisor.py#budget_block), because those cost money. The
-- ones that cost a PERSON something had none: friend requests and reports are
-- the harassment surface on a product used by minors, handle claiming is the
-- impersonation surface, and POST /mentors/apply is unauthenticated, so
-- anybody on the internet can write to it as fast as they can loop.
--
-- One row per limited action. Rows are evidence as well as counters -- a burst
-- of friend requests from one account is exactly what a moderator would want
-- to see -- so they are kept rather than deleted on read.

create table if not exists public.rate_events (
    id uuid primary key default gen_random_uuid(),

    -- Null for unauthenticated actions (mentor applications), which are
    -- limited globally instead. Not a foreign key for that reason, and so a
    -- student deleting their account cannot erase the record of a burst.
    student_id uuid,

    -- Which ceiling this counts against. See app/limits.py POLICIES.
    action text not null,

    created_at timestamptz not null default now()
);

comment on table public.rate_events is
    'One row per rate-limited action. Counted by app/limits.py over a sliding '
    'window. Deliberately not cascaded from students: the point of the record '
    'is to survive the account that produced it.';

-- The only query shape this table has: count rows for one action, since a
-- timestamp, optionally for one student.
create index if not exists rate_events_action_time_idx
    on public.rate_events (action, created_at desc);

create index if not exists rate_events_student_action_time_idx
    on public.rate_events (student_id, action, created_at desc)
    where student_id is not null;

-- Writes go through FastAPI on the service role, like every other table since
-- 20260921120000_rls_lockdown.sql. A client that could write here could also
-- forge its own allowance, and a client that could read here could count
-- another student's activity.
alter table public.rate_events enable row level security;

revoke select, insert, update, delete on public.rate_events from anon;
revoke select, insert, update, delete on public.rate_events from authenticated;
