# kintone の自動取得(GitHub Actions から15分ごとに呼ぶ)。本番では .github/scripts/kintone_sync.py に置く
# ロジリンクの設定(kv「kintone-auto-sync」: 時刻・曜日・項目)を読み、
# 設定の時刻を過ぎていて、今日その時刻より後にまだ取っていない項目だけを取る(手で取った分も「取った」に数える)。
# 失敗したときは、次の15分でやり直す(設定の時刻から3時間まで)。
# 読むのは設定と、各項目の「最後に取った時刻」(kv の updated_at)だけ(通信量を小さく)。
# 環境変数: KEY(FACTORY_CRON_KEY)・FORCE(true なら設定に関係なく全部取る)・DRY(1 なら取らずに、取る予定だけ出す)
import datetime
import json
import os
import re
import sys
import urllib.request

SUPABASE = "https://iywmunzneirtxipnpveu.supabase.co"
BASE = SUPABASE + "/functions/v1"
CONFIG_KEY = "kintone-auto-sync"
DEFAULT = {"enabled": True, "time": "06:43", "days": [1, 2, 3, 4, 5, 6],
           "items": {"outlook": True, "product": True, "report": True, "price": False}, "reportDays": 7}
# 項目: 名前・関数・最後に取った時刻の kv
ITEMS = [
    ("outlook", "見積もり・入荷予定", "sync-stock-outlook", "stock-outlook"),
    ("product", "商品台帳", "sync-product-master", "kintone-product-sync-status"),
    ("report", "作業日報", "sync-work-report", "work-report-sync-status"),
    ("price", "作業単価", "sync-work-price-master", "work-price-sync-status"),
]
RETRY_HOURS = 3

key = os.environ.get("KEY", "")
force = os.environ.get("FORCE", "") == "true"
dry = os.environ.get("DRY", "") == "1"
if not key and not dry:
    print("FACTORY_CRON_KEY が登録されていないので、何もしません")
    sys.exit(0)
m = re.search(r"sb_publishable_[A-Za-z0-9_-]+", open("config.js", encoding="utf-8").read())
anon = m.group(0)


def rest(path):
    req = urllib.request.Request(SUPABASE + "/rest/v1/" + path, headers={"apikey": anon, "Authorization": "Bearer " + anon})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def parse_ts(s):
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    s = re.sub(r"\.(\d{6})\d*", r".\1", s)
    return datetime.datetime.fromisoformat(s)


# 設定
cfg = dict(DEFAULT)
rows = rest("kv_store?key=eq." + CONFIG_KEY + "&select=value")
if rows and rows[0].get("value"):
    v = rows[0]["value"]
    try:
        v = json.loads(v) if isinstance(v, str) else v
        cfg.update({k: v[k] for k in v if k in DEFAULT})
    except Exception:
        print("設定を読めなかったので、はじめの設定で動きます")
items = dict(DEFAULT["items"]); items.update(cfg.get("items") or {})

jst = datetime.timezone(datetime.timedelta(hours=9))
now = datetime.datetime.now(jst)
hh, mm = [int(x) for x in str(cfg.get("time") or "06:43").split(":")[:2]]
due = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
dow = (now.weekday() + 1) % 7  # 0=日 … 6=土(ロジリンクと同じ)
print("今(日本時間)", now.strftime("%Y-%m-%d %H:%M"), "/ 設定", cfg.get("time"), "曜日", cfg.get("days"), "/ 項目", ",".join(k for k, on in items.items() if on), "/ 手動(全部)" if force else "")

if not force:
    if not cfg.get("enabled", True):
        print("自動取得はオフです"); sys.exit(0)
    if dow not in (cfg.get("days") or []):
        print("今日は取らない曜日です"); sys.exit(0)
    if now < due:
        print("まだ設定の時刻前です"); sys.exit(0)
    if now > due + datetime.timedelta(hours=RETRY_HOURS):
        print("設定の時刻から" + str(RETRY_HOURS) + "時間を過ぎたので、今日はもう取りません(取れていなければ手で動かしてください)"); sys.exit(0)

# 最後に取った時刻
keys = ",".join(i[3] for i in ITEMS)
last = {r["key"]: parse_ts(r.get("updated_at")) for r in rest("kv_store?key=in.(" + keys + ")&select=key,updated_at")}

failed = []
for code, label, fn, status_key in ITEMS:
    if not items.get(code):
        continue
    lt = last.get(status_key)
    if not force and lt and lt >= due:
        print("・" + label + ": 今日はもう取っています(" + lt.astimezone(jst).strftime("%H:%M") + ")")
        continue
    if code == "report":
        days = max(1, min(31, int(cfg.get("reportDays") or 7)))
        body = {"from": (now - datetime.timedelta(days=days - 1)).strftime("%Y-%m-%d"), "to": now.strftime("%Y-%m-%d")}
    else:
        body = {}
    if dry:
        print("・" + label + ": 取ります(試しなので取らない)", json.dumps(body, ensure_ascii=False)); continue
    req = urllib.request.Request(BASE + "/" + fn, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"x-cron-key": key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            res = json.loads(r.read().decode("utf-8"))
        ok = bool(res.get("ok"))
        print("・" + label + ": " + ("取りました" if ok else "失敗 " + str(res.get("error", ""))[:200]))
    except Exception as e:
        ok = False
        detail = ""
        if hasattr(e, "read"):
            try: detail = e.read().decode("utf-8")[:300]
            except Exception: pass
        print("・" + label + ": 失敗 " + str(e)[:200] + " " + detail)
    if not ok:
        failed.append(label)

if failed:
    print("失敗: " + "・".join(failed) + "(次の15分でやり直します)")
    sys.exit(1)
