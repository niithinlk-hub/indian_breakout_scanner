#!/usr/bin/env bash
# Verify the schema, config seed and the DRAFT RLS policies on a THROWAWAY local
# Postgres (15+). Creates a scratch database, mimics Supabase's API roles and default
# grants, runs the checks, then drops the database. Never point this at Supabase.
#
#   scanner/sql/verify/run_local.sh "host=127.0.0.1 port=54329 user=postgres"
set -euo pipefail
DSN="${1:?usage: run_local.sh <libpq connection string to a throwaway server>}"
HERE="$(cd "$(dirname "$0")" && pwd)"
DB="nsescan_verify_$$"

psql "$DSN dbname=postgres" -qAt -c "create database $DB"
trap 'psql "$DSN dbname=postgres" -qAt -c "drop database if exists $DB" >/dev/null' EXIT
run() { psql "$DSN dbname=$DB" -v ON_ERROR_STOP=1 -q "$@"; }

run <<'SQL'
do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then create role anon nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then create role authenticated nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'service_role') then create role service_role nologin bypassrls; end if;
end $$;
grant usage on schema public to anon, authenticated, service_role;
alter default privileges in schema public grant all on tables to anon, authenticated, service_role;
alter default privileges in schema public grant all on sequences to anon, authenticated, service_role;
SQL
run -f "$HERE/../001_schema.sql"
run -f "$HERE/../003_seed_config.sql"
run -f "$HERE/verify_schema.sql"
run -f "$HERE/../draft/002_rls_policies.sql"
run -f "$HERE/verify_rls_draft.sql"
