-- DRAFT: NOT APPLIED. Needs owner approval before it is run against any project.
--
-- Intent (build spec section 7): the dashboard reads with the public anon key; only
-- the GitHub Actions job writes, with the service-role key (which bypasses RLS).
-- 001_schema.sql already enables RLS with no policies (deny-all for API roles);
-- this file adds read-only SELECT policies and nothing else.

-- ---------------------------------------------------------------- read-only dashboard access
create policy "dashboard read" on public.universe         for select to anon, authenticated using (true);
create policy "dashboard read" on public.prices_daily     for select to anon, authenticated using (true);
create policy "dashboard read" on public.benchmarks_daily for select to anon, authenticated using (true);
create policy "dashboard read" on public.regime_daily     for select to anon, authenticated using (true);
create policy "dashboard read" on public.scan_runs        for select to anon, authenticated using (true);
create policy "dashboard read" on public.signals          for select to anon, authenticated using (true);
create policy "dashboard read" on public.config           for select to anon, authenticated using (true);
create policy "dashboard read" on public.config_history   for select to anon, authenticated using (true);
create policy "dashboard read" on public.backtest_runs    for select to anon, authenticated using (true);
create policy "dashboard read" on public.paper_trades     for select to anon, authenticated using (true);
create policy "dashboard read" on public.data_quality     for select to anon, authenticated using (true);

-- No INSERT / UPDATE / DELETE policies: every API write from anon or authenticated is refused.

-- ---------------------------------------------------------------- OPEN QUESTION (decide before step 6)
-- Section 8 asks for two dashboard writes: Settings (edit config, versioned by the
-- config_audit trigger) and Paper trades (create from a signal). A read-only anon key
-- cannot do either. Options:
--
--   A (recommended): Supabase Auth magic link restricted to the owner's email, plus
--      write policies for that one user:
--
--   create policy "owner edits config" on public.config for update to authenticated
--     using ((select auth.jwt() ->> 'email') = '<owner email>')
--     with check ((select auth.jwt() ->> 'email') = '<owner email>');
--   create policy "owner creates paper trades" on public.paper_trades for insert to authenticated
--     with check ((select auth.jwt() ->> 'email') = '<owner email>');
--
--   B: Next.js server actions that hold the service-role key server-side, behind a
--      password. No extra policies, but the service key then lives in Vercel env vars.
--
-- Exit marking for paper trades stays in the GitHub Actions job (service key), so
-- the dashboard never needs UPDATE on paper_trades under either option.
