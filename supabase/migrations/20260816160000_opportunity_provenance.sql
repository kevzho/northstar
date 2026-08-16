-- Provenance on opportunities: how did each row enter the catalog?
--
-- 'seed'  — the original hand-authored catalog
-- 'human' — promoted via scripts/review_candidates.py
-- 'ai'    — auto-promoted by the LLM verifier (verify_and_import.py)
--
-- This makes AI-screened rows auditable and reversible: a bad batch is
-- one `delete ... where added_by = 'ai' and created_at > ...` away, and
-- the frontend/FAQ can honestly say what's screened vs hand-reviewed.

alter table public.opportunities
    add column if not exists added_by text not null default 'seed';

comment on column public.opportunities.added_by is
    'Provenance: seed | human | ai — how the row entered the catalog.';
