# 物流センター 作業割り当てボード(Supabase + GitHub Pages版)

Node.jsサーバーを自前で立てず、**Supabase(データベース)+ GitHub Pages(静的ホスティング)** で動かす構成です。バックエンドサーバーは不要になります。

## 構成

```
webapp-supabase/
  index.html        ... アプリ本体(4画面: 管理者/作業登録/パート入力/モニター)
  config.js         ... SupabaseのURL・anonキーを設定するファイル(要編集)
  supabase/
    schema.sql       ... Supabaseに作成するテーブルの定義
```

データはブラウザから直接Supabaseの`kv_store`テーブルに保存されます。サーバーを自分で運用する必要はありません。

## 1. Supabase側の準備

1. Supabaseダッシュボードで新しいプロジェクトを作成(または既存のプロジェクトを流用)
2. 左メニューの **SQL Editor** を開き、`supabase/schema.sql` の中身を貼り付けて実行
   - `kv_store` テーブルが作成されます
   - RLS(Row Level Security)を有効にし、anonキーでの読み書きを許可するポリシーも一緒に設定されます
3. **Project Settings → API** を開き、以下の2つをコピー
   - **Project URL**(例: `https://abcdefgh.supabase.co`)
   - **anon public キー**(`service_role`キーではなく、`anon` `public`キーの方)

## 2. config.js を編集

`config.js` を開き、コピーした値を貼り付けます。

```js
window.SUPABASE_CONFIG = {
  url: "https://abcdefgh.supabase.co",
  anonKey: "ey....(anon public key)"
};
```

## 3. GitHubにpush

このフォルダをGitHubの新しいリポジトリにpushします。

```bash
cd webapp-supabase
git init
git add .
git commit -m "物流センター作業割り当てボード"
git branch -M main
git remote add origin https://github.com/<あなたのアカウント>/<リポジトリ名>.git
git push -u origin main
```

## 4. GitHub Pagesを有効化

1. GitHubのリポジトリページで **Settings → Pages** を開く
2. **Source** を「Deploy from a branch」、**Branch** を `main` / `/(root)` に設定して保存
3. 数分待つと `https://<あなたのアカウント>.github.io/<リポジトリ名>/` でアプリにアクセスできるようになります

このURLを、管理者用PC・パートさん用タブレット・モニター用PCなど各端末で開き、それぞれ役割を選んでください。全員が同じSupabaseデータベースを見るので、リアルタイムに状況が共有されます。

## セキュリティに関する重要な注意

- このアプリにはログイン機能がありません。`config.js` に書いたanonキーはブラウザから誰でも見える(開発者ツールで確認できる)状態になります。
- `schema.sql` のRLSポリシーは「anonキーを持つ人は誰でも読み書き可能」という設定にしています。GitHub Pagesのリポジトリを **public(公開)** にする場合、URLとこの仕組みを知っている人は誰でもデータを閲覧・変更できてしまいます。
- 社内限定での利用を想定しているため、以下のいずれかをおすすめします。
  - リポジトリを **private** にする(GitHub Pagesは有料プランでないとprivateリポジトリからの公開ができない場合があります。GitHub Pro/Team/Enterpriseをご確認ください)
  - URLを社内関係者以外に共有しない
  - より厳格にしたい場合は、Supabase Authでログイン機能を追加し、RLSポリシーを `auth.uid()` ベースに変更する(この場合は追加の実装が必要です。ご要望があればお手伝いします)

## 動作確認のポイント

- config.jsの値が正しくないと、アプリを開いたときに「Supabaseが未設定です」という案内画面が表示されます。
- Supabaseダッシュボードの **Table Editor → kv_store** で、実際にデータ(`roster`、`task-backlog`、`task-templates`、`day:YYYY-MM-DD` などのキー)が書き込まれているか確認できます。

## 更新のたびにやること

アプリの中身(index.html)を修正した場合は、GitHubにpushするだけで自動的にGitHub Pagesに反映されます(数分のタイムラグがあります)。
