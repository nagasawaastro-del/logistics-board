-- ============================================================
-- スタッフごとの時給(人件費の計算用。スタッフ設定の画面で編集する)
-- ============================================================
-- staff_id はスタッフ一覧(kv_store の roster)のスタッフID。staff_id = '__default__' の行は「標準時給」
-- (時給を設定していないスタッフに使う)。
-- スタッフ一覧(kv_store)は公開用のキーで読めるため、時給はそこに入れず、このテーブルに分けて保護する。
-- 参照は manager 以上、変更は admin のみ(labor_costs と同じ)。未ログイン(anon)には一切の権限を与えない。
-- Supabaseダッシュボード → SQL Editor に貼り付けて実行してください。何度実行しても同じ状態になります。

create table if not exists public.staff_wages (
  staff_id    text primary key,
  hourly_wage numeric not null check (hourly_wage >= 0),
  updated_at  timestamptz not null default now(),
  updated_by  uuid default auth.uid()
);

alter table public.staff_wages enable row level security;

drop policy if exists sw_select_manager on public.staff_wages;
create policy sw_select_manager on public.staff_wages
  for select using (public.has_role('manager'));

drop policy if exists sw_insert_admin on public.staff_wages;
create policy sw_insert_admin on public.staff_wages
  for insert with check (public.has_role('admin'));

drop policy if exists sw_update_admin on public.staff_wages;
create policy sw_update_admin on public.staff_wages
  for update using (public.has_role('admin')) with check (public.has_role('admin'));

drop policy if exists sw_delete_admin on public.staff_wages;
create policy sw_delete_admin on public.staff_wages
  for delete using (public.has_role('admin'));

revoke all on public.staff_wages from anon, authenticated;
grant select, insert, update, delete on public.staff_wages to authenticated;
