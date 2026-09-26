-- Checks for 001_schema.sql + 003_seed_config.sql (+ the RLS draft) on a THROWAWAY local
-- Postgres that mimics Supabase's API roles. Never run against the real project.
-- Usage: scanner/sql/verify/run_local.sh "host=127.0.0.1 port=54329 user=postgres"
\set ON_ERROR_STOP on

-- ---------------------------------------------------------------- config versioning
do $$
declare n_config int; n_hist int;
begin
  select count(*) into n_config from public.config;
  select count(*) into n_hist from public.config_history;
  if n_config <> n_hist then
    raise exception 'after first seed: % config rows but % history rows', n_config, n_hist;
  end if;
end $$;

-- re-running the seed must not create history rows (AFTER triggers, value unchanged)
\ir ../003_seed_config.sql
do $$
declare n_config int; n_hist int;
begin
  select count(*) into n_config from public.config;
  select count(*) into n_hist from public.config_history;
  if n_config <> n_hist then
    raise exception 'seed re-run wrote spurious history: % config rows, % history rows', n_config, n_hist;
  end if;
end $$;

-- an edit is versioned with old and new values and bumps updated_at
update public.config set value = '85'::jsonb, updated_by = 'verify' where key = 'rs.min_rank';
do $$
declare h record;
begin
  select * into h from public.config_history where key = 'rs.min_rank' order by id desc limit 1;
  if h.old_value <> '80.0'::jsonb or h.new_value <> '85'::jsonb or h.changed_by <> 'verify' then
    raise exception 'unexpected history row: % -> % by %', h.old_value, h.new_value, h.changed_by;
  end if;
  if (select updated_at from public.config where key = 'rs.min_rank') <
     (select changed_at from public.config_history where key = 'rs.min_rank' order by id desc limit 1) - interval '1 second' then
    raise exception 'updated_at not bumped';
  end if;
end $$;

-- a no-op update (same value) is not versioned
update public.config set value = '85'::jsonb where key = 'rs.min_rank';
do $$
begin
  if (select count(*) from public.config_history where key = 'rs.min_rank') <> 2 then
    raise exception 'no-op update was versioned';
  end if;
end $$;

-- ---------------------------------------------------------------- RLS: deny-all before policies
insert into public.universe (symbol, yahoo_ticker, segment) values ('TEST', 'TEST.NS', 'N500');
set role anon;
do $$
begin
  if (select count(*) from public.universe) <> 0 then
    raise exception 'anon can read universe before policies';
  end if;
  begin
    insert into public.universe (symbol, yahoo_ticker, segment) values ('X', 'X.NS', 'N500');
    raise exception 'anon insert succeeded before policies';
  exception when insufficient_privilege then null;
  end;
end $$;
reset role;

\echo 'schema checks passed (config seed idempotent, edits versioned, RLS deny-all without policies)'
