-- A door into the mentor directory, which until now had none.
--
-- THE DEFECT. `table("mentors")` appears exactly once in the backend, at the
-- read in GET /mentors. There is no write path anywhere: no signup page, no
-- endpoint, no script. The directory's empty state tells a student it "will
-- fill with mentors who have agreed in writing to hear from students" — and
-- nothing could ever make that true. It was not empty because nobody had
-- applied. There was nowhere to apply.
--
-- WHY APPLICATIONS ARE A SEPARATE TABLE, NOT A `pending` FLAG ON mentors.
-- public.mentors is rendered to minors with a mailto: link. If a public form
-- could insert there, a stranger could put their address in front of children
-- and the only thing standing between them would be a boolean nobody checks.
-- Writes from the open internet must not be able to reach that table at all,
-- so they land here instead and a human moves them across. The separation is
-- the safeguard; a status column would not be.
--
-- APPROVAL IS DELIBERATELY MANUAL AND MUST STAY MANUAL. There is no automated
-- promotion path, and none should be added. Someone offering to talk to
-- teenagers is a decision a person makes, with the evidence in front of them,
-- and the consent they gave recorded.

create table if not exists public.mentor_applications (
    id uuid primary key default gen_random_uuid(),

    name text not null,
    email text not null,
    -- What they do and what they are offering. Shown to the reviewer, never
    -- to a student from this table.
    bio text not null default '',
    expertise text[] not null default '{}',
    link text,

    -- The consent, recorded as a fact with a time, not as a tick that was
    -- true once. 20260922090000 removed 25 invented mentors precisely because
    -- nobody could tell afterwards which had agreed to anything.
    consented_at timestamptz,
    consent_text text,

    -- Review. Both NULL means nobody has looked yet.
    reviewed_at timestamptz,
    reviewed_outcome text check (reviewed_outcome in ('approved', 'declined')),
    reviewer_note text,

    -- Where it came from, for spotting a flood from one source.
    source text not null default 'web',
    created_at timestamptz not null default now()
);

comment on table public.mentor_applications is
    'Offers to mentor, awaiting a human. Separate from public.mentors because '
    'that table is rendered to minors with a mailto: link, and nothing writable '
    'from the open internet may reach it. Promotion is manual on purpose.';

comment on column public.mentor_applications.consented_at is
    'When this person agreed, in writing, to be listed and contacted by '
    'students. NULL means they did not, and the application cannot be '
    'approved — see the check below.';

-- An approval without a recorded consent is the thing that must never happen.
alter table public.mentor_applications
    drop constraint if exists mentor_application_approved_needs_consent;
alter table public.mentor_applications
    add constraint mentor_application_approved_needs_consent
    check (reviewed_outcome is distinct from 'approved' or consented_at is not null);

create index if not exists mentor_applications_pending_idx
    on public.mentor_applications (created_at desc)
    where reviewed_at is null;

alter table public.mentor_applications enable row level security;

-- No policies at all: neither anon nor authenticated may read or write this
-- table. The application endpoint runs as the service role, and the reviewer
-- reads it in the dashboard. An application contains an adult's email and an
-- unreviewed self-description; students have no business seeing either.
revoke all on public.mentor_applications from anon;
revoke all on public.mentor_applications from authenticated;
