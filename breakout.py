import os, requests, pandas as pd, yfinance as yf, time
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=+9), 'JST')

def analyze_fundamentals(t_obj):
    """急騰動意株のための財務フィルター（売上成長＋高効率）"""
    score = 0
    try:
        info = t_obj.info
        
        # 1. 【必須】売上高成長率が前年同期比で5%以上（カタリストの土台）
        rev_growth = info.get('revenueGrowth')
        if rev_growth is None or rev_growth < 0.05: return None
        score += 1
        
        # 2. 【必須】ROE 8%以上（資本効率の良さ）
        if info.get('returnOnEquity', 0) < 0.08: return None
        score += 1
        
        # 3. 営業利益率 10%以上（あれば加点）
        if info.get('operatingMargins', 0) >= 0.10: score += 1
            
        return "★" * score
    except:
        return None

def judge_breakout(ticker_code, name):
    """急騰前兆（ボリューム・ブレイクアウト）判定ロジック"""
    try:
        t_obj = yf.Ticker(f"{ticker_code}.T")
        data = t_obj.history(period='1y', interval='1d') 
        if data.empty or len(data) < 75: return None
        
        close, vol = data['Close'], data['Volume']
        p_now = float(close.iloc[-1])
        
        # --- ① 最低限の流動性フィルター ---
        avg_vol_5 = vol.tail(5).mean()
        if avg_vol_5 < 50000 and (p_now * avg_vol_5) < 50000000: return None

        # --- ② 財務チェック（増収・高ROEが必須） ---
        star = analyze_fundamentals(t_obj)
        if not star: return None

        # --- ③ 各種移動平均線の計算 ---
        ma5 = close.rolling(5).mean()
        ma25 = close.rolling(25).mean()
        ma75 = close.rolling(75).mean()
        
        # --- ④ 【核心】出来高急増（ボリューム・ブレイクアウト）の判定 ---
        avg_vol_25 = vol.tail(25).mean()
        recent_vol_3 = vol.tail(3).mean()
        # 直近3日間の平均出来高が、過去25日平均の1.5倍以上（資金流入の明確なサイン）
        if recent_vol_3 < avg_vol_25 * 1.5: return None

        # --- ⑤ 【核心】トレンド初動判定（ゴールデンクロス直後） ---
        # 5日線が25日線より上にあり、かつそのクロスが最近（5日以内）起きたかを確認
        if ma5.iloc[-1] <= ma25.iloc[-1]: return None
        
        # 5日前〜1日前のどこかで「5日線 <= 25日線」だった（＝最近ゴールデンクロスした）
        was_crossed = False
        for j in range(-2, -7, -1):
            if ma5.iloc[j] <= ma25.iloc[j]:
                was_crossed = True
                break
        if not was_crossed: return None

        # --- ⑥ 上値の軽さ確認 ---
        # 株価が75日線の上にあり、中長期の上昇気流に乗っていること
        if p_now <= ma75.iloc[-1]: return None
        
        return f"🔥【急騰前兆】{star}{ticker_code} {name}({p_now:.0f}円)"
    except:
        return None

def send_line(message):
    token, uid = os.environ.get('LINE_ACCESS_TOKEN'), os.environ.get('LINE_USER_ID')
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    for i in range(0, len(message), 4500):
        payload = {"to": uid, "messages": [{"type": "text", "text": message[i:i+4500]}]}
        requests.post(url, headers=headers, json=payload, timeout=20)
        time.sleep(1)

def main():
    if not os.path.exists("all_stocks.csv"): return
    df = pd.read_csv("all_stocks.csv", encoding='utf-8-sig')
    c_col = [c for c in df.columns if 'コード' in str(c) or 'Code' in str(c)][0]
    n_col = [c for c in df.columns if '銘柄' in str(c) or '名称' in str(c)][0]
    stocks = df[[c_col, n_col]].dropna().values.tolist()
    
    res = []
    for i, (code, name) in enumerate(stocks):
        c = str(code).strip()[:4]
        if c.isdigit():
            out = judge_breakout(c, str(name))
            if out: res.append(out)
        if (i+1)%15 == 0: time.sleep(0.05)
    
    if res:
        now_jst = datetime.now(JST)
        msg = f"⚡ 朝：急騰前兆ハンター({now_jst.strftime('%m/%d %H:%M')})\n"
        msg += "条件: 出来高1.5倍急増 / 初動GC直後 / 業績高成長株\n\n"
        msg += "\n".join(res)
        send_line(msg)

if __name__ == "__main__":
    main()
