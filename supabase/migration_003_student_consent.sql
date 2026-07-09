-- Meridian migration 003: IRB consent persistence
--
-- Adds ``consented_at`` to ``public.students``. The onboarding form's consent
-- checkbox now persists; NULL/old rows default to no consent. A separate
-- ``consent`` boolean is intentionally avoided — the presence of a timestamp
-- is a stronger audit trail than a boolean flip back to false.
--
-- Idempotent: safe to re-run.
-- Run after supabase/schema.sql + migration_002_meridian_schema.sql.

alter table public.students
    add column if not exists consented_at timestamptz;
