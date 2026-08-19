-- 物流センター作業割り当てボード用のテーブル定義
-- Supabaseダッシュボード → SQL Editor に貼り付けて実行してください。

create table if not exists kv_store (
  key text primary key,
  value text not null,
  updated_at timestamptz not null default now()
);

-- 更新日時を自動更新するトリガー
create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists kv_store_set_updated_at on kv_store;
create trigger kv_store_set_updated_at
  before update on kv_store
  for each row
  execute function set_updated_at();

-- Row Level Security を有効化
alter table kv_store enable row level security;

-- 注意: このアプリにはログイン機能がありません。
-- 下記のポリシーは「anon(匿名)キーを持つ全員」に読み書きを許可します。
-- これはフロントエンドに埋め込まれる公開キーなので、
-- URLとこのキーを知っていれば誰でもデータの閲覧・変更が可能になります。
-- 社内限定での利用を想定し、リポジトリやURLの共有範囲にご注意ください。
-- より厳格に制限したい場合は、Supabase Authでログインを追加し、
-- ポリシーを auth.uid() ベースに変更することをおすすめします。

drop policy if exists "kv_store anon select" on kv_store;
create policy "kv_store anon select" on kv_store for select using (true);

drop policy if exists "kv_store anon insert" on kv_store;
create policy "kv_store anon insert" on kv_store for insert with check (true);

drop policy if exists "kv_store anon update" on kv_store;
create policy "kv_store anon update" on kv_store for update using (true);

drop policy if exists "kv_store anon delete" on kv_store;
create policy "kv_store anon delete" on kv_store for delete using (true);
