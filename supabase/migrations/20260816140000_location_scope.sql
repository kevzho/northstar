-- Location scope: is an opportunity US-based, international, or global?
--
-- Distinct from the existing free-text `location` (a place name like
-- "Cambridge, MA"). This is the coarse eligibility axis a student filters
-- on: 'global' means open regardless of country (most online programs and
-- hackathons), 'us' means US-based, 'international' means outside the US.
-- Students state a preference; matching gives a small boost, never a hard
-- filter, so a preference can't empty the shelf.

create type public.location_scope as enum ('us', 'international', 'global');
create type public.location_pref as enum ('us', 'international', 'either');

-- The catalog is US high-school programs today, so 'us' is the honest
-- default; the scraper and reviewer refine from there.
alter table public.opportunities
    add column if not exists location_scope public.location_scope
        not null default 'us';

alter table public.students
    add column if not exists location_pref public.location_pref
        not null default 'either';

comment on column public.opportunities.location_scope is
    'Coarse eligibility: us | international | global (open to all).';
comment on column public.students.location_pref is
    'Where the student wants opportunities: us | international | either.';
