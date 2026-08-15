-- Phase A of the breadth expansion: the field enum grows beyond STEM.
--
-- "Unusual route" was structurally impossible when every opportunity,
-- interest, and archetype had to land in one of six STEM buckets. Four
-- new fields open the catalog to design, business/entrepreneurship,
-- humanities/communication, and health — the frontend quiz, matcher,
-- and scraper all learn them in the same change set.

alter type public.opportunity_field add value if not exists 'design';
alter type public.opportunity_field add value if not exists 'business';
alter type public.opportunity_field add value if not exists 'humanities';
alter type public.opportunity_field add value if not exists 'health';
