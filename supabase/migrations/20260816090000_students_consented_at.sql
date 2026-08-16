-- Fix-forward: the live students table was missing consented_at.
--
-- The column exists in 20250711134902_student_consent.sql, but that
-- migration was reconciled into remote history during the CLI linking
-- (supabase migration repair marks SQL as applied without running it),
-- so production never got the column and every /me select 400'd —
-- surfaced by the first real sign-in on 2026-08-16. add column if not
-- exists makes this safe everywhere: no-op where the original ran.

alter table public.students
    add column if not exists consented_at timestamptz;
