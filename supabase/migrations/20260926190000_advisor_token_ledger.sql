-- Record what each advisor call actually cost, not just that it happened.
--
-- public.advisor_calls has been both ledger and cache since 20260822090000, and
-- it counts CALLS. That was right while the ceiling was 150 a day: every call
-- was roughly the same size and "rows today" was a fair proxy for spend.
--
-- It stops being right at hundreds of users. A call measured on gpt-6-luna is
-- ~640 prompt + ~285 completion tokens, but a student pasting a long goal
-- statement with twelve matched sources costs several times a one-line
-- question, and the provider bills tokens. A budget denominated in calls
-- therefore cannot answer the only question that matters — how much is left —
-- and a cap set low enough to be safe for the worst call is far too low for the
-- median one.
--
-- Nullable on purpose. Every row written before this migration has an unknown
-- cost, and guessing a number for them would make the ledger lie about history.
-- The budget treats NULL as "unknown, not free" by falling back to a
-- conservative per-call estimate.

alter table public.advisor_calls
    add column if not exists prompt_tokens integer,
    add column if not exists completion_tokens integer,
    add column if not exists total_tokens integer;

comment on column public.advisor_calls.total_tokens is
    'Tokens billed for this call, from the provider''s usage block. NULL for '
    'rows written before 20260926190000, and for providers that return no '
    'usage; the budget treats NULL as an estimate rather than as zero.';

-- The budget sums today's tokens on every request, so index the shape it reads:
-- recent rows, newest first.
create index if not exists advisor_calls_recent_idx
    on public.advisor_calls (created_at desc);

-- Sum the day's spend in Postgres, not in Python.
--
-- The first version of the budget did
--     select total_tokens where created_at >= since
-- and summed the rows in the application. That is fine at 150 calls a day and
-- indefensible at scale: 1,000 students at the per-student cap is ~10,000 rows,
-- and the budget is consulted on EVERY advisor request, so each question would
-- drag the whole day's ledger over the wire to add it up. The cost of asking
-- "may I spend?" would grow with how much had already been spent.
--
-- COALESCE on two levels, deliberately:
--   - sum() over zero rows returns NULL, which must read as 0 spent, not as
--     "unknown" — an empty day is a genuinely empty day.
--   - a NULL total_tokens on an individual row means the call was never priced
--     (written before this migration, or a provider that returned no usage
--     block). Those are charged p_assumed rather than skipped, because counting
--     unknown as free would let an unmeasured provider spend without limit.
create or replace function public.advisor_tokens_since(
    p_since timestamptz,
    p_assumed integer default 1200
)
returns bigint
language sql
stable
security invoker
set search_path = public
as $$
    select coalesce(sum(coalesce(total_tokens, p_assumed)), 0)::bigint
    from public.advisor_calls
    where created_at >= p_since;
$$;

comment on function public.advisor_tokens_since(timestamptz, integer) is
    'Tokens billed since p_since, pricing un-measured rows at p_assumed rather '
    'than treating them as free. Used by the advisor daily token budget so the '
    'check is one aggregate rather than a full-day row scan per request.';

-- security invoker, not definer: the caller is the service role, and the
-- function should never grant a student the ability to read the whole ledger.
revoke all on function public.advisor_tokens_since(timestamptz, integer) from public;
grant execute on function public.advisor_tokens_since(timestamptz, integer) to service_role;
