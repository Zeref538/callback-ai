-- Run once in the Supabase dashboard: SQL Editor -> New query -> paste -> Run.
-- Safe to re-run: every statement checks before creating.
--
-- One row per finished interview. The page writes to this table directly with
-- the publishable key; the row-level security policies below are the only
-- thing stopping one user from reading another's rows, so never disable them.

create table if not exists public.interviews (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null default auth.uid() references auth.users (id) on delete cascade,
  entry      jsonb not null,                       -- the report, delta and trace the page shows
  created_at timestamptz not null default now(),
  -- a report is tens of KB; this stops one account filling the free-tier database
  constraint entry_size check (pg_column_size(entry) < 1000000)
);

-- Serves the sidebar: "this user's newest 30 interviews".
create index if not exists interviews_user_newest on public.interviews (user_id, created_at desc);

alter table public.interviews enable row level security;

grant select, insert, delete on public.interviews to authenticated;

drop policy if exists "read own interviews" on public.interviews;
create policy "read own interviews" on public.interviews
  for select to authenticated using ((select auth.uid()) = user_id);

drop policy if exists "add own interviews" on public.interviews;
create policy "add own interviews" on public.interviews
  for insert to authenticated with check ((select auth.uid()) = user_id);

drop policy if exists "delete own interviews" on public.interviews;
create policy "delete own interviews" on public.interviews
  for delete to authenticated using ((select auth.uid()) = user_id);
