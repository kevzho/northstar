-- Northstar migration 006: onboarding completion flag
--
-- ``public.students`` (schema.sql) never had an ``onboarded`` column, but
-- three layers already assume one:
--   * backend/app/schemas.py      StudentProfile / StudentProfileCreate
--   * backend/app/main.py         POST /students upserts the field
--   * frontend/lib/types.ts       StudentProfile.onboarded
--
-- Without the column PostgREST rejects every POST /students upsert with
-- "column onboarded of relation students does not exist", which means a
-- student can never finish onboarding and the dashboard's stub-profile
-- creation fails too. This migration closes that gap.
--
-- Idempotent: safe to re-run.
-- Run after supabase/schema.sql + migration_002 + migration_003.

alter table public.students
    add column if not exists onboarded boolean not null default false;

-- Backfill: anyone who already supplied interests and goals finished the
-- three-step wizard before this column existed.
update public.students
   set onboarded = true
 where onboarded = false
   and coalesce(array_length(interests, 1), 0) > 0
   and coalesce(goals, '') <> '';
