-- How a student actually gets in, which is not always "apply".
--
-- Seven rows on the high-school shelf carry an application deadline for
-- something you cannot apply to. Verified against each programme's own site:
--
--   USA Mathematical Olympiad        qualify via AMC 10/12 -> AIME
--   Physics Olympiad Summer Camp     qualify via the F=ma exam
--   Regeneron ISEF                   advance from an affiliated regional fair
--   Math Prize for Girls             qualify by AMC score
--   Simons Summer Research           nominated/competitive, junior year only
--   MIT Beaver Works (BWSI)          admission by prior coursework + selection
--   Lemelson-MIT InvenTeams          a TEACHER applies for a team grant
--
-- A student who "applies by the deadline" to any of these does nothing. That is
-- the same shape of defect as the nine programmes retired in 20260923120000 --
-- a listing that sends someone somewhere they cannot go -- except these are
-- real, reachable opportunities being described wrongly. So they are corrected
-- rather than retired.
--
-- The roadmap cares too: app/roadmap.py emits an "Apply to X" step for any row
-- that is open and grade-eligible. Without this column it would tell a student
-- to apply to USAMO.

create type public.entry_gate as enum (
    'apply',      -- a student applies directly. The default and the common case.
    'qualify',    -- they must first place in a prior exam or contest
    'advance',    -- they advance from a lower-level fair or competition
    'nominate',   -- a teacher, school or third party puts them forward
    'teacher'     -- an adult applies on the students' behalf
);

alter table public.opportunities
    add column if not exists entry_gate public.entry_gate not null default 'apply',
    -- One line a student can act on: what to do INSTEAD of applying.
    add column if not exists entry_note text not null default '';

comment on column public.opportunities.entry_gate is
    'How a student gets in. Anything other than ''apply'' means a listed '
    'deadline is not an application deadline, and the UI must not say "apply '
    'by" -- see entry_note for what to do instead.';

create index if not exists opportunities_entry_gate_idx
    on public.opportunities (entry_gate)
    where entry_gate <> 'apply' and retired_at is null;
