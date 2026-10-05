/* 通信量の目安(2026-10-05)
   Supabase から受け取ったデータ量をこの端末で数え、端末(localStorage)に日ごとに貯めて、
   10分に1回だけ kv_store の「usage:YYYY-MM:端末ID」に書く(書くのは小さな JSON だけ)。
   トップページ・設定→システムで、全端末の合計を「今月の通信量(目安)」として表示する。
   Supabase の請求の数字とは少しずれる(ヘッダーなどは推定)。正確な値は Supabase の Usage 画面で見る。
   index.html と factory.html の両方で使う。 */
(function(){
  "use strict";
  var DEV_KEY = 'logilink-device-id';
  var HEADER_BYTES = 300; // 1回の応答のヘッダーなど(推定)
  function pad(n){ return String(n).padStart(2,'0'); }
  function monthStr(d){ return d.getFullYear()+'-'+pad(d.getMonth()+1); }
  function dayStr(d){ return monthStr(d)+'-'+pad(d.getDate()); }
  function deviceId(){
    try{
      var id = localStorage.getItem(DEV_KEY);
      if(!id){ id = Math.random().toString(36).slice(2,10)+Date.now().toString(36).slice(-4); localStorage.setItem(DEV_KEY, id); }
      return id;
    }catch(e){ return 'nostorage'; }
  }
  function deviceKind(){
    var ua = (typeof navigator!=='undefined' && navigator.userAgent) || '';
    if(/iPad|Macintosh.*Mobile/.test(ua) || (/Macintosh/.test(ua) && typeof navigator!=='undefined' && navigator.maxTouchPoints>1)) return 'iPad';
    if(/iPhone/.test(ua)) return 'iPhone';
    if(/Android/.test(ua)) return /Mobile/.test(ua) ? 'Androidスマホ' : 'Androidタブレット';
    if(/Windows/.test(ua)) return 'Windows';
    if(/Macintosh/.test(ua)) return 'Mac';
    return 'その他';
  }
  /* opts: { lsKey: 端末に貯める場所, suffix: 端末IDのうしろに付ける文字(ページごとに分ける), label(): 端末の説明 } */
  function create(opts){
    var pending = 0, client = null;
    function add(n){ if(n>0) pending += n; }
    function merge(){
      if(!pending) return;
      try{
        var now = new Date(), m = monthStr(now), d = dayStr(now);
        var u = JSON.parse(localStorage.getItem(opts.lsKey)||'null');
        if(!u || u.month!==m) u = { month: m, days: {} };
        u.days[d] = (u.days[d]||0) + pending;
        pending = 0;
        localStorage.setItem(opts.lsKey, JSON.stringify(u));
      }catch(e){ pending = 0; }
    }
    async function flush(){
      merge();
      if(!client) return;
      try{
        var u = JSON.parse(localStorage.getItem(opts.lsKey)||'null');
        if(!u) return;
        var sig = u.month+JSON.stringify(u.days);
        if(localStorage.getItem(opts.lsKey+'-sent')===sig) return; // 前回から増えていない
        var label = deviceKind()+(opts.label ? ' ・ '+(opts.label()||'') : '');
        var r = await client.from('kv_store').upsert({ key: 'usage:'+u.month+':'+deviceId()+(opts.suffix||''), value: JSON.stringify({ label: label, days: u.days, at: new Date().toISOString() }) }, { onConflict: 'key' });
        if(!r.error) localStorage.setItem(opts.lsKey+'-sent', sig);
      }catch(e){}
    }
    function countingFetch(input, init){
      return fetch(input, init).then(function(res){
        try{
          var len = Number(res.headers.get('content-length'));
          if(len>0) add(len+HEADER_BYTES);
          else if(res.body && res.status!==204) res.clone().arrayBuffer().then(function(b){ add(b.byteLength+HEADER_BYTES); }).catch(function(){});
          else add(HEADER_BYTES);
        }catch(e){}
        return res;
      });
    }
    setInterval(merge, 30000);
    setInterval(flush, 600000);
    setTimeout(flush, 60000);
    return { fetch: countingFetch, setClient: function(c){ client = c; }, flush: flush, add: add };
  }
  /* 今月の全端末の合計を読む(小さな行を数件) */
  async function loadSummary(client, now){
    now = now || new Date();
    var m = monthStr(now);
    var r = await client.from('kv_store').select('key,value').like('key', 'usage:'+m+':%');
    if(r.error) throw r.error;
    var devices = [], byDay = {}, total = 0;
    (r.data||[]).forEach(function(row){
      var v; try{ v = JSON.parse(row.value); }catch(e){ return; }
      if(!v || !v.days) return;
      var t = 0;
      Object.keys(v.days).forEach(function(d){ var n = Number(v.days[d])||0; t += n; byDay[d] = (byDay[d]||0)+n; });
      total += t;
      devices.push({ id: row.key.slice(('usage:'+m+':').length), label: v.label||'', total: t, today: Number(v.days[dayStr(now)])||0, at: v.at||'' });
    });
    devices.sort(function(a,b){ return b.total-a.total; });
    var daysInMonth = new Date(now.getFullYear(), now.getMonth()+1, 0).getDate();
    var elapsed = now.getDate()-1 + (now.getHours()*60+now.getMinutes())/1440;
    var projected = elapsed>0.5 ? total/elapsed*daysInMonth : null; // 月の初めは見込みを出さない
    return { month: m, total: total, byDay: byDay, devices: devices, projected: projected };
  }
  window.LogiUsageMeter = { create: create, loadSummary: loadSummary, FREE_BYTES: 5e9, dayStr: dayStr };
})();
