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
