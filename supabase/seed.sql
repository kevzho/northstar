-- Northstar seed data.
-- Run after supabase/schema.sql. Provides a single test student so the
-- authenticated dashboard has something to render during local dev and the
-- Day 2 schema work has a row to validate RLS policies against.
--
-- This file is idempotent: re-running it never duplicates rows.

insert into public.students (id, name, email, grade, interests, goals)
select
  '00000000-0000-0000-0000-000000000001'::uuid,
  'Northstar Demo Student',
  'demo@northstar.example',
  '11',
  array['Computer Science', 'Mathematics'],
  'I want to do computational biology research that helps patients.'
where not exists (
  select 1 from public.students where email = 'demo@northstar.example'
);
