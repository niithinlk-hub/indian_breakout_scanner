-- Checks for the DRAFT read policies on a THROWAWAY local Postgres (see run_local.sh).
\set ON_ERROR_STOP on

set role anon;
do $$
declare t text;
begin
  foreach t in array array['universe', 'prices_daily', 'benchmarks_daily', 'regime_daily', 'scan_runs', 'signals',
                           'config', 'config_history', 'backtest_runs', 'paper_trades', 'data_quality'] loop
    execute format('select count(*) from public.%I', t);
  end loop;
  if (select count(*) from public.universe) <> 1 then
    raise exception 'anon cannot read universe with the read policy';
  end if;
  begin
    insert into public.universe (symbol, yahoo_ticker, segment) values ('X', 'X.NS', 'N500');
    raise exception 'anon insert succeeded with read-only policies';
  exception when insufficient_privilege then null;
  end;
  begin
    update public.config set value = '1'::jsonb where key = 'rs.min_rank';
    if found then raise exception 'anon update of config succeeded'; end if;
  exception when insufficient_privilege then null;
  end;
  if (select value from public.config where key = 'rs.min_rank') <> '85'::jsonb then
    raise exception 'anon changed config';
  end if;
end $$;
reset role;

set role service_role;
insert into public.universe (symbol, yahoo_ticker, segment) values ('SVC', 'SVC.NS', 'N500');
reset role;

\echo 'RLS draft checks passed (anon reads every table, cannot write; service_role writes)'
