-- Semantic matching: fix the failure TF-IDF cannot fix.
--
-- app/match.py scores lexically. Measured against the live catalog, a student
-- who writes "I want to help people with cancer" gets:
--
--     0.650  Foundation Communities Volunteer Impact Fair
--     0.050  MIT PRIMES
--     0.050  Congressional App Challenge          <- noise
--     0.050  Amazon Future Engineer Scholarship   <- noise
--
-- Everything after the first row is pinned at the booster floor: no shared
-- tokens, so no signal. Stanford Institutes of Medicine Summer Research — the
-- actually relevant row — never appears. With embeddings it does.
--
-- DESIGN NOTES, both forced by measurement rather than preference.
--
-- 1. THE VECTORS NEVER LEAVE POSTGRES. nvidia/nemotron-3-embed-1b returns 2048
--    dimensions and refuses any other size ("dimensions must be one of 2048").
--    Shipping 2048 floats per row to the API would put ~1.2 MB on every /match
--    call and undo 20260923's egress work, which took the payload from 106 KB
--    to 52 KB. So similarity is computed here and only (id, score) is returned.
--
-- 2. NO INDEX. pgvector's ivfflat and hnsw both cap at 2000 dimensions, and
--    this model gives 2048, so neither can be built. That is fine at this
--    scale: an exact scan over 61 high-school rows (144 total) is microseconds.
--    If the catalog reaches thousands, the fix is an embedding model that
--    supports Matryoshka truncation to <=2000, not a bigger machine.

alter table public.opportunities
    add column if not exists embedding vector(2048),
    add column if not exists embedded_at timestamptz;

alter table public.students
    add column if not exists profile_embedding vector(2048),
    add column if not exists profile_embedded_at timestamptz;

comment on column public.opportunities.embedding is
    'nvidia/nemotron-3-embed-1b, input_type=passage, over title + blurb. '
    'Written nightly by backend/scripts/embed_catalog.py for rows where it is '
    'NULL. Deliberately unindexed: pgvector indexes cap at 2000 dimensions.';

comment on column public.students.profile_embedding is
    'Same model, input_type=query, over interests + goals. Written when the '
    'profile or assessment changes — roughly once per student, not per request.';

-- Only rows that HAVE an embedding are worth scanning.
create index if not exists opportunities_embedded_idx
    on public.opportunities (embedded_at)
    where embedding is not null and retired_at is null;

-- One round trip, one float per opportunity.
--
-- Returns cosine similarity in [0,1] for every live opportunity on the
-- student's shelf that has an embedding. A student with no profile embedding
-- gets an empty set, and the caller falls back to lexical scoring alone — the
-- feature degrades to today's behaviour rather than failing.
create or replace function public.semantic_scores(p_student uuid)
returns table (opportunity_id uuid, similarity double precision)
language sql
stable
as $$
    with me as (
        select profile_embedding, coalesce(audience, 'high_school') as shelf
        from public.students
        where id = p_student
    )
    select
        o.id,
        -- pgvector's <=> is cosine DISTANCE; 1 - d is similarity. Clamped
        -- because floating point can put it a hair outside [0,1].
        greatest(0.0, least(1.0, 1.0 - (o.embedding <=> me.profile_embedding)))
    from public.opportunities o, me
    where me.profile_embedding is not null
      and o.embedding is not null
      and o.retired_at is null
      and o.audience = me.shelf;
$$;

comment on function public.semantic_scores(uuid) is
    'Cosine similarity between a student profile embedding and every live '
    'opportunity on their shelf. Computed in the database so 2048-float '
    'vectors never cross the wire — see 20260925090000 for the measurement.';

revoke all on function public.semantic_scores(uuid) from public;
revoke all on function public.semantic_scores(uuid) from anon;
revoke all on function public.semantic_scores(uuid) from authenticated;
