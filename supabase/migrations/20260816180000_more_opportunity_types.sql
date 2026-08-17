-- More opportunity types, mirroring how ecdatabase.org categorizes:
-- internships, volunteer roles, and journals are distinct kinds a student
-- filters on, not all "programs". Additive to the existing enum
-- (program, scholarship, competition, mentorship); nothing reclassifies.

alter type public.opportunity_type add value if not exists 'internship';
alter type public.opportunity_type add value if not exists 'volunteer';
alter type public.opportunity_type add value if not exists 'journal';
