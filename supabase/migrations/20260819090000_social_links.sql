-- Social links on the student profile: a small allowlisted set of URLs
-- (github, website, youtube, linkedin) the student adds themselves.
--
-- Stored as jsonb; the backend validates keys against an allowlist and
-- normalizes/checks URLs before writing (app/social.py). Shown only on
-- the opt-in public profile page — private records never expose them.

alter table public.students
    add column if not exists social_links jsonb;
