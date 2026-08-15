-- Idempotent outcome writes.
--
-- A double-clicked "log outcome" used to insert two identical rows, which
-- double-fired the edge-weight trigger and polluted the ALS training
-- data — corruption of the exact record the product is built on. The same
-- (student, opportunity, status) is one fact; POST /outcomes becomes an
-- upsert against this key. Existing duplicates are collapsed to the
-- earliest row first.

delete from public.outcomes o
using public.outcomes keeper
where o.student_id = keeper.student_id
  and o.opportunity_id = keeper.opportunity_id
  and o.status = keeper.status
  and o.created_at > keeper.created_at;

create unique index if not exists uq_outcomes_student_opp_status
    on public.outcomes (student_id, opportunity_id, status);
