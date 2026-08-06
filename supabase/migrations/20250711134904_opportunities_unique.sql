-- Northstar migration 005: natural key on opportunities
--
-- Adds a UNIQUE constraint title+host so the seed_opportunities.sql file can
-- use INSERT ... ON CONFLICT (title, host) DO NOTHING for idempotent seeding.
--
-- Idempotent: safe to re-run (uses IF NOT EXISTS on the index).
-- Run after migration_002_northstar_schema.sql.

create unique index if not exists uq_opportunities_title_host
    on public.opportunities (title, host);
