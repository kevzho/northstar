-- Close two policies that were scoped by comment instead of by SQL.
--
-- 1. public.opportunities carried:
--
--      create policy "Opportunities are insertable by service role"
--        on public.opportunities for insert with check (true);
--        -- service key bypasses RLS in Supabase
--
--    The comment is true and irrelevant. A policy with no `to` clause
--    applies to PUBLIC, which includes `anon` -- and the anon key ships in
--    the browser bundle (frontend/lib/supabase.ts:4). Any visitor could
--    INSERT catalog rows that every student then sees. With no .limit() on
--    the five sites that read the catalog and PostgREST's default
--    max_rows = 1000, ~1,100 injected rows would evict the real catalog.
--
--    The service-role key bypasses RLS entirely, so the backend never
--    needed this policy. Dropping it is the whole fix; the REVOKE below
--    is the second layer, because Supabase grants table-level INSERT to
--    anon/authenticated by default and RLS is only the row filter.
--
-- 2. public.mentors was `for select using (true)`, i.e. world-readable
--    over PostgREST. Nothing in the frontend queries Supabase tables
--    directly (`grep -rn "\.from(" frontend/` finds only a starfield
--    array) -- /mentors is served by the backend through the service-role
--    client in backend/app/mentors.py. Until the seeded directory is
--    replaced with mentors who have actually consented, it should not be
--    harvestable straight off the table.
--
-- Idempotent: safe to re-run, and safe to apply to a database where the
-- original migration was `migration repair`-marked rather than executed.

-- 1. opportunities: writes are service-role only ---------------------------

drop policy if exists "Opportunities are insertable by service role"
    on public.opportunities;

revoke insert, update, delete on public.opportunities from anon;
revoke insert, update, delete on public.opportunities from authenticated;

-- Public read stays: the catalog is meant to be public, and the backend
-- serves it anyway. Left explicit so the next reader sees it is deliberate.
drop policy if exists "Opportunities are readable by anyone"
    on public.opportunities;
create policy "Opportunities are readable by anyone"
    on public.opportunities for select
    to anon, authenticated
    using (true);

-- 2. mentors: not readable off the table by clients ------------------------

drop policy if exists "Mentors are readable by anyone" on public.mentors;

revoke select, insert, update, delete on public.mentors from anon;
revoke select, insert, update, delete on public.mentors from authenticated;

-- 3. The same unscoped-write shape on the other two public catalogs --------
--
-- pathway_nodes and pathway_edges are read-only reference tables with no
-- insert policy, but they do carry the default table-level grants.

revoke insert, update, delete on public.pathway_nodes from anon;
revoke insert, update, delete on public.pathway_nodes from authenticated;
revoke insert, update, delete on public.pathway_edges from anon;
revoke insert, update, delete on public.pathway_edges from authenticated;
