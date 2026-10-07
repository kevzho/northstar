-- Where an opportunity actually is, structured enough to filter on.
--
-- WHY. A free chat model recalls every nationally-known programme — measured
-- 2026-10-05, it named 24 of 24 curated catalog rows correctly from memory with
-- no web access. What it structurally cannot do is locality: it cannot tell a
-- 10th grader in Bullock County which of Alabama's four ISEF-affiliated regional
-- fairs feeds theirs, when that fair's entry closes, and that a teacher has to
-- register them. That is the one axis where recall fails by construction rather
-- than by staleness, and it is the axis this catalog was throwing away.
--
-- IT WAS ALREADY BEING SCRAPED AND DISCARDED. scrape_sciencefairs.py reads the
-- Society for Science directory and extracts each fair's territory —
-- "Bullock County", "Orange County" — then passes it as `location_guess`.
-- app/verifier.py normalised that into location_scope, an enum of exactly three
-- values (us / international / global), and the county was gone. Every regional
-- fair in the catalog today reads location=NULL, location_scope='us'.
--
-- public.opportunities.location (free text, 20250711134901) already existed for
-- exactly this and has never been written. This migration adds the structured
-- half beside it, because "show me fairs in Alabama" needs a column you can
-- index, not a string you have to pattern-match.

alter table public.opportunities
    add column if not exists state text;

comment on column public.opportunities.state is
    'Two-letter US state/territory code when an opportunity is tied to one '
    'place — a regional science fair, a state governor''s school, a campus '
    'programme. NULL for anything national or online, which is most of the '
    'catalog and is the honest answer for it. Distinct from location_scope '
    '(us/international/global), which answers "may a US student enter", not '
    '"where is it".';

comment on column public.opportunities.location is
    'Free-text place as the organiser states it — "Bullock County", '
    '"Woods Hole, MA". Written from the source directory, never inferred from '
    'the title.';

-- Two letters or nothing. A half-filled code is worse than an empty one here,
-- because the filter would silently drop a student's own state.
alter table public.opportunities
    drop constraint if exists opportunities_state_is_a_code;
alter table public.opportunities
    add constraint opportunities_state_is_a_code
    check (state is null or state ~ '^[A-Z]{2}$');

-- The query this exists to serve: "what is near me, and still open".
create index if not exists opportunities_state_deadline_idx
    on public.opportunities (state, deadline)
    where retired_at is null;
