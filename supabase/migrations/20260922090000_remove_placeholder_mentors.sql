-- Remove the 25 fabricated mentors, and make them unrepresentable.
--
-- Where they came from: scripts/seed_mentors.sql landed in the initial
-- commit as scaffolding for the mentor-matching feature -- its own header
-- calls them "25 real-style STEM mentor profiles." Whoever wrote them chose
-- RFC 2606 reserved addresses (aisha.patel@mit.example,
-- marcus.chen@stanford.example), which is the correct way to mark data as
-- fake. The problem is what happened next: on 2026-08-15 the live database
-- was found empty, the seed files were folded into
-- 20260815090000_seed_catalog.sql to fix that, and placeholder scaffolding
-- was promoted to production data. The UI then rendered it as real --
-- a computed "% fit" badge, the instruction "Reach out to mentors you want
-- to work with," and a working mailto to an address that cannot receive
-- mail. Nothing on the page said it was sample data.
--
-- Twenty-five invented people attributed to MIT, Stanford, Google, CERN and
-- the Broad is a fabricated-data problem anywhere, and this product is being
-- submitted to a federal competition and shown to high schoolers who would
-- have emailed them.
--
-- Deleting the rows is not enough on its own: the seed lives in an applied
-- migration, so a `supabase db reset` would replay it. The CHECK constraint
-- is the durable half -- it makes the seed fail loudly instead of silently
-- repopulating, and it is why scripts/seed_mentors.sql is deleted in the
-- same commit.
--
-- Real mentors, with a written opt-in, are tracked separately. An empty
-- directory that says so is worth more than a full one that is invented.

-- 1. Remove the fabricated rows. Verified before writing this: all 25 live
--    mentors carry a reserved-TLD address, none are real, and
--    mentor_sessions is empty, so the FK cascade destroys nothing.
delete from public.mentors
where email ~* '\.(example|test|invalid|localhost)$'
   or email ~* '@example\.(com|net|org)$';

-- 2. Make it unrepresentable. RFC 2606 / RFC 6761 reserve these names
--    precisely so they can never be real, which makes "is this address
--    fake?" a question SQL can answer.
alter table public.mentors
    drop constraint if exists mentors_email_not_placeholder;

alter table public.mentors
    add constraint mentors_email_not_placeholder
    check (
        email !~* '\.(example|test|invalid|localhost)$'
        and email !~* '@example\.(com|net|org)$'
    );

comment on constraint mentors_email_not_placeholder on public.mentors is
    'Mentors are shown to students with a mailto. A reserved-TLD address '
    'means the person is invented, so the row must not exist.';
