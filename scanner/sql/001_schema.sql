-- NSE breakout scanner: schema.
--
-- Row level security is ENABLED on every table with NO policies, so nothing is
-- readable or writable through the anon / authenticated API roles until the read
-- policies in sql/draft/002_rls_policies.sql are applied (pending approval). The
-- scanner writes with the service-role key, which bypasses RLS.

-- ---------------------------------------------------------------- universe
create table if not exists public.universe (
  symbol       text primary key,
  yahoo_ticker text not null,
  company      text,
  industry     text,
  segment      text not null check (segment in ('N500', 'MICRO250')),
  series       text,          -- NSE series on the constituent list (EQ / BE); current only, no history
  isin         text,
  active       boolean not null default true,
  added_at     date not null default current_date
);
create index if not exists universe_segment_idx on public.universe (segment);

-- ---------------------------------------------------------------- prices
create table if not exists public.prices_daily (
  symbol text not null,
  date   date not null,
  open   double precision not null,
  high   double precision not null,
  low    double precision not null,
  close  double precision not null,
  volume bigint,               -- null when Yahoo sends none (QA flags it)
  primary key (symbol, date)   -- serves the (symbol, date) index
);
create index if not exists prices_daily_date_idx on public.prices_daily (date);

create or replace view public.price_last_dates
with (security_invoker = true) as
select symbol, max(date) as last_date, count(*) as bars
from public.prices_daily
group by symbol;

create table if not exists public.benchmarks_daily (
  ticker text not null,
  date   date not null,
  close  double precision not null,
  primary key (ticker, date)
);

-- ---------------------------------------------------------------- regime
create table if not exists public.regime_daily (
  date           date primary key,
  state          text not null check (state in ('RISK_ON', 'NEUTRAL', 'RISK_OFF')),
  bench_above_50 boolean,
  breadth_pct    double precision,
  vix_pctile     double precision,
  -- audit inputs
  bench_close    double precision,
  bench_sma      double precision,
  vix_close      double precision,
  vix_threshold  double precision,
  breadth_n      integer,
  config_hash    text
);

-- ---------------------------------------------------------------- runs
create table if not exists public.scan_runs (
  id             bigint generated always as identity primary key,
  kind           text not null default 'scan',   -- scan | history | update | qa
  started_at     timestamptz not null,
  finished_at    timestamptz,
  tickers_ok     integer,
  tickers_failed integer,
  config_hash    text,
  data_asof      date,
  notes          jsonb
);

-- ---------------------------------------------------------------- signals
create table if not exists public.signals (
  id            bigint generated always as identity primary key,
  scan_run_id   bigint references public.scan_runs (id),
  scan_date     date not null,
  symbol        text not null references public.universe (symbol),
  segment       text not null check (segment in ('N500', 'MICRO250')),
  status        text not null check (status in ('TRIGGERED', 'SETUP', 'EXTENDED', 'REJECTED')),
  grade         text check (grade in ('A', 'B', 'C')),
  score         double precision,
  pivot         double precision,
  close         double precision,
  extension_pct double precision,
  stop          double precision,
  stop_pct      double precision,
  t1            double precision,
  t2            double precision,
  vol_ratio     double precision,
  rs_rank       double precision,
  earnings_flag boolean not null default false,
  circuit_flag  boolean not null default false,
  gate_values   jsonb not null,             -- every input and threshold that produced the status
  fail_reasons  text[] not null default '{}',
  config_hash   text not null,
  created_at    timestamptz not null default now(),
  unique (scan_date, symbol)
);
create index if not exists signals_scan_date_status_idx on public.signals (scan_date, status);
create index if not exists signals_segment_idx on public.signals (segment);
create index if not exists signals_symbol_date_idx on public.signals (symbol, scan_date);

-- ---------------------------------------------------------------- config (+ history)
create table if not exists public.config (
  key           text primary key,
  value         jsonb not null,
  default_value jsonb,
  description   text,
  updated_at    timestamptz not null default now(),
  updated_by    text
);

create table if not exists public.config_history (
  id         bigint generated always as identity primary key,
  key        text not null,
  old_value  jsonb,
  new_value  jsonb,
  changed_at timestamptz not null default now(),
  changed_by text
);
create index if not exists config_history_key_idx on public.config_history (key, changed_at desc);

-- Every change to config.value is versioned in config_history.
-- AFTER triggers: with INSERT ... ON CONFLICT DO UPDATE (the seed file), BEFORE INSERT
-- triggers also fire for rows that end up as updates; AFTER INSERT fires only for rows
-- actually inserted, AFTER UPDATE only for rows actually updated.
create or replace function public.config_touch()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if new.value is distinct from old.value then
    new.updated_at := now();
  end if;
  return new;
end;
$$;

create or replace function public.config_audit()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if tg_op = 'INSERT' then
    insert into public.config_history (key, old_value, new_value, changed_by)
    values (new.key, null, new.value, new.updated_by);
  elsif tg_op = 'UPDATE' then
    if new.value is distinct from old.value then
      insert into public.config_history (key, old_value, new_value, changed_by)
      values (new.key, old.value, new.value, new.updated_by);
    end if;
  else
    insert into public.config_history (key, old_value, new_value, changed_by)
    values (old.key, old.value, null, null);
  end if;
  return null;
end;
$$;

drop trigger if exists config_touch_trg on public.config;
create trigger config_touch_trg
before update on public.config
for each row execute function public.config_touch();

drop trigger if exists config_audit_trg on public.config;
create trigger config_audit_trg
after insert or update or delete on public.config
for each row execute function public.config_audit();

-- ---------------------------------------------------------------- backtests
create table if not exists public.backtest_runs (
  id          bigint generated always as identity primary key,
  run_at      timestamptz not null default now(),
  kind        text not null,   -- baserate | strategy | benchmark | ablation | walkforward
  params      jsonb not null,  -- full config snapshot + run arguments
  metrics     jsonb not null,
  report_md   text,
  config_hash text,
  data_asof   date,
  git_sha     text
);

-- ---------------------------------------------------------------- paper trades
create table if not exists public.paper_trades (
  id           bigint generated always as identity primary key,
  signal_id    bigint references public.signals (id),
  symbol       text not null,
  segment      text not null check (segment in ('N500', 'MICRO250')),
  status       text not null default 'PENDING' check (status in ('PENDING', 'OPEN', 'CLOSED', 'SKIPPED')),
  entry_date   date,
  entry        double precision,
  stop         double precision,
  qty          integer,
  partial_date date,
  partial_exit double precision,
  partial_qty  integer,
  exit_date    date,
  exit         double precision,
  exit_reason  text,
  r_multiple   double precision,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);
create index if not exists paper_trades_signal_idx on public.paper_trades (signal_id);

-- ---------------------------------------------------------------- data quality
create table if not exists public.data_quality (
  id       bigint generated always as identity primary key,
  symbol   text not null,
  date     date not null,
  segment  text not null check (segment in ('N500', 'MICRO250')),
  issue    text not null,
  blocking boolean not null default false,   -- true = excluded from scans
  detail   jsonb,
  run_at   timestamptz not null default now()
);
create index if not exists data_quality_segment_idx on public.data_quality (segment);
create index if not exists data_quality_symbol_date_idx on public.data_quality (symbol, date);

-- ---------------------------------------------------------------- RLS on, no policies yet
alter table public.universe         enable row level security;
alter table public.prices_daily     enable row level security;
alter table public.benchmarks_daily enable row level security;
alter table public.regime_daily     enable row level security;
alter table public.scan_runs        enable row level security;
alter table public.signals          enable row level security;
alter table public.config           enable row level security;
alter table public.config_history   enable row level security;
alter table public.backtest_runs    enable row level security;
alter table public.paper_trades     enable row level security;
alter table public.data_quality     enable row level security;
