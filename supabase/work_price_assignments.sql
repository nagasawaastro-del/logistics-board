-- ============================================================
-- 作業単価マスタの「得意先・計算単位」の設定(ロジリンクで編集する)
-- ============================================================
-- kintone 作業単価アプリ(501)から取り込んだ項目(work_price_master)ごとに、
-- どの得意先に当てはめ、どの単位(ピース・ケース・件・明細)で計算するかを保存する。
-- work_price_master は kintone との同期で作り直されるため、設定はこの別テーブルに分けて持つ
-- (同期してもここは消えない。kintoneで削除された項目の設定は残るが、画面には出ない)。
-- 参照は manager 以上、変更は admin のみ(unit_prices と同じ)。
-- Supabaseダッシュボード → SQL Editor に貼り付けて実行してください。何度実行しても同じ状態になります。

create table if not exists public.work_price_assignments (
  kintone_record_id text primary key,                          -- work_price_master.kintone_record_id
  all_customers     boolean not null default false,            -- true: 全得意先共通
  customer_names    text[]  not null default '{}',             -- 当てはめる得意先名(得意先・作業枠マスターの得意先名)
  calc_unit         text,                                      -- 計算単位(未設定は null)。下の制約で値を限定する
  updated_at        timestamptz not null default now(),
  updated_by        uuid default auth.uid()
);

-- 計算単位: 才 = ケースで出荷した数 × 商品台帳の才数(2026-09-30 追加)。既に作成済みのテーブルもこの制約に置き換える
alter table public.work_price_assignments drop constraint if exists work_price_assignments_calc_unit_check;
alter table public.work_price_assignments add constraint work_price_assignments_calc_unit_check
  check (calc_unit is null or calc_unit in ('ピース','ケース','件','明細','才'));

alter table public.work_price_assignments enable row level security;

drop policy if exists wpa_select_manager on public.work_price_assignments;
create policy wpa_select_manager on public.work_price_assignments
  for select using (public.has_role('manager'));

drop policy if exists wpa_insert_admin on public.work_price_assignments;
create policy wpa_insert_admin on public.work_price_assignments
  for insert with check (public.has_role('admin'));

drop policy if exists wpa_update_admin on public.work_price_assignments;
create policy wpa_update_admin on public.work_price_assignments
  for update using (public.has_role('admin')) with check (public.has_role('admin'));

drop policy if exists wpa_delete_admin on public.work_price_assignments;
create policy wpa_delete_admin on public.work_price_assignments
  for delete using (public.has_role('admin'));

-- 未ログイン(anon)には一切の権限を与えない。ログイン中のユーザーの可否は上のポリシーで決まる
revoke all on public.work_price_assignments from anon, authenticated;
grant select, insert, update, delete on public.work_price_assignments to authenticated;
