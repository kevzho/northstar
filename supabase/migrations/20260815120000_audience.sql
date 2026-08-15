-- Audience: who an opportunity serves and which shelf a student browses.
--
-- Northstar expands beyond high school; opportunities and students each
-- declare an audience and the matcher only ranks same-audience rows.
-- Everything existing is high_school, so both columns default to it and
-- no backfill is needed. The grade_min/grade_max columns keep their 6-12
-- meaning for high_school rows; the matcher skips the grade boost for
-- college students rather than overloading those columns with years.

create type public.audience as enum ('high_school', 'college');

alter table public.opportunities
    add column if not exists audience public.audience not null default 'high_school';

alter table public.students
    add column if not exists audience public.audience not null default 'high_school';

comment on column public.opportunities.audience is
    'Who this opportunity serves; matched against students.audience.';
comment on column public.students.audience is
    'Which catalog shelf this student browses (high_school | college).';
