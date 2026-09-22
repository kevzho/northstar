-- Make "mentors who have opted in" a fact the schema enforces.
--
-- /mentors tells students these people agreed to hear from them, and the page
-- hands out a mailto. Until now nothing recorded that agreement -- the claim
-- rested on whoever inserted the row remembering. The previous occupants of
-- this table were 25 invented people, so "someone will remember" is not a
-- control this feature has earned.
--
-- consented_at is the gate: GET /mentors returns only rows that have it, so a
-- mentor inserted without recorded consent is invisible rather than emailed.
-- The column is nullable on purpose -- a row can exist while outreach is in
-- progress, it just does not surface.

alter table public.mentors
    add column if not exists consented_at timestamptz;

comment on column public.mentors.consented_at is
    'When this mentor agreed in writing to hear from students. NULL means no '
    'recorded consent, and GET /mentors filters the row out. Set it only from '
    'an actual written reply.';

create index if not exists idx_mentors_consented
    on public.mentors (consented_at)
    where consented_at is not null;
