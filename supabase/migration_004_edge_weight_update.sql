-- Meridian migration 004: outcome-triggered edge-weight update
--
-- When a student logs an outcome (accepted/completed/rejected/withdrew), we
-- nudge the weights of pathway_edges that connect nodes with shared tags,
-- reinforcing traversal paths that lead to successful outcomes.
--
-- ARCHITECTURE.md §4 — This is the student-owned outcome feedback loop.
-- Hermes provides the SQL trigger plumbing; the update rule logic is yours.
--
-- Idempotent: safe to re-run (uses CREATE OR REPLACE).

-- 1. Edge-weight update function
create or replace function public.update_edge_weights_from_outcome()
returns trigger
language plpgsql
as $$
declare
  shared_count integer;
  delta        double precision := 0.0;
  rec          record;
begin
  -- Determine the direction and magnitude of the weight nudge.
  -- Positive outcomes (accepted, completed) strengthen the path;
  -- negative outcomes (rejected, withdrew) weaken it slightly.
  -- The magnitude is proportional to the outcome status but stays
  -- small so the graph evolves gradually over many logged outcomes.
  case new.status
    when 'accepted'   then delta := +0.10;
    when 'completed'  then delta := +0.08;
    when 'waitlisted' then delta := +0.02;
    when 'rejected'   then delta := -0.05;
    when 'withdrew'   then delta := -0.03;
    else return new;
  end case;

  -- Each edge connects source_node → target_node; both reference
  -- opportunity_id. We find edges where either the source or the target
  -- node's opportunity shares at least one tag with the logged opportunity,
  -- then apply the delta (clamped to [0, ∞) since the check constraint on
  -- pathway_edges requires weight >= 0).
  for rec in
    select pe.id, pe.weight
    from public.pathway_edges pe
    join public.pathway_nodes pn_src on pe.source_node_id = pn_src.id
    join public.opportunities o_src  on pn_src.opportunity_id = o_src.id
    join public.opportunities o_log  on o_log.id = new.opportunity_id
    where o_src.tags && o_log.tags   -- any tag overlap
  loop
    update public.pathway_edges
      set weight = greatest(0, rec.weight + delta)
      where id = rec.id;
  end loop;

  return new;
end;
$$;

-- 2. Trigger — fires after each outcome INSERT
drop trigger if exists trg_outcome_edge_update on public.outcomes;
create trigger trg_outcome_edge_update
  after insert on public.outcomes
  for each row
  execute function public.update_edge_weights_from_outcome();