-- Give the catalog a way to say "this is dead" and "this date is real".
--
-- The catalog shows teenagers an application deadline and an eligible grade
-- range, and they click through to apply. An audit of the 35 hand-seeded rows
-- against each program's own website found rows that are not merely stale:
--
--   Gates Millennium Scholars  -- final cohort was the class of 2016; ended.
--   Broadcom MASTERS           -- renamed Thermo Fisher Junior Innovators
--                                 Challenge in 2023, and it is a MIDDLE school
--                                 competition (grades 6-8), listed as 8-9.
--   NSF REU "High School Track" -- NSF: REU is for "Undergraduates (college and
--                                 university students)". No such track exists.
--   CERN Summer Student        -- requires bachelor's/master's enrollment.
--
-- Deleting these rows is the wrong fix twice over. outcomes, bookmarks,
-- matches and dismissals all reference opportunities(id) with `on delete
-- cascade`, so a DELETE silently destroys a student's logged history — and the
-- row is also the evidence of why it was removed. So retirement is a stamp,
-- and the read path filters on it.
--
-- `retired_at` answers "should anyone see this?". `recurrence_*` answers a
-- different question the roadmap feature needs: "may we make a claim about
-- when this opens NEXT year?" Only a human sets that, after checking the
-- program's site. Default NULL means the honest answer is "no confirmed
-- window", which is what the UI should say rather than projecting a dead
-- deadline forward.

alter table public.opportunities
    add column if not exists retired_at timestamptz,
    add column if not exists retired_reason text,
    add column if not exists verified_at timestamptz,
    add column if not exists recurrence_month smallint
        check (recurrence_month is null or recurrence_month between 1 and 12),
    add column if not exists recurrence_verified_at timestamptz;

comment on column public.opportunities.retired_at is
    'Set when a program no longer exists as listed, or cannot accept the '
    'audience it is shelved under. Rows with this set are excluded from '
    'ranking and browse; they are kept so student outcomes referencing them '
    'survive, and so the reason is auditable.';

comment on column public.opportunities.recurrence_verified_at is
    'When a human last confirmed this program still runs on this cycle. NULL '
    'means no forward-looking date claim is licensed -- the UI must say "no '
    'confirmed window" rather than project a past deadline into the future.';

-- The read path filters `retired_at is null` on every query, so index for it.
create index if not exists opportunities_live_idx
    on public.opportunities (retired_at)
    where retired_at is null;
