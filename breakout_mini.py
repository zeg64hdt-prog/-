import os
import pandas as pd
import yfinance as yf
import requests

# --- 設定 ---
# 監視対象となる株ミニのリストファイル
CSV_FILE = "kabumini.csv" 
# LINE通知用設定（GitHub Actionsのenvから取得）
LINE_TOKEN = os.environ.get("LINE_ACCESS_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID") # ※Messaging APIを使用する場合

def send_line_notify(message):
    """LINE Notify または Messaging API を使って通知を送信する関数"""
    if not LINE_TOKEN:
        print("LINE_ACCESS_TOKEN が設定されていません。")
        return
    
    # 簡易的な LINE Notify を使用する場合の例
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {LINE_TOKEN}"}
    payload = {"message": message}
    
    try:
        response = requests.post(url, headers=headers, data=payload)
        if response.status_code == 200:
            print("LINE通知を送信しました。")
        else:
            print(f"LINE通知失敗: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"LINE送信エラー: {e}")

def check_breakout(ticker_symbol):
    """指定された銘柄がブレイクアウトしているか判定する関数"""
    # Yahoo Finance用のシンボル形式に変換 (例: 7203 -> 7203.T)
    symbol = f"{ticker_symbol}.T"
    
    try:
        # 過去20日間の日足データを取得
        df = yf.download(symbol, period="20d", interval="1d", progress=False)
        if df.empty or len(df) < 20:
            return None
        
        # 直近の終値と、過去19日間の最高値を取得
        latest_close = df['Close'].iloc[-1]
        highest_prev = df['High'].iloc[:-1].max()
        
        # 【判定ロジック例】当日の終値が過去19日間の最高値を上回ったらブレイクアウト
        if latest_close > highest_prev:
            return {
                "symbol": ticker_symbol,
                "close": latest_close,
                "highest": highest_prev
            }
    except Exception as e:
        print(f"銘柄 {ticker_symbol} のデータ取得エラー: {e}")
    return None

def main():
    print("夕方の株ミニスキャンを開始します...")
    
    # 1. kabumini.csv の読み込み
    if not os.path.exists(CSV_FILE):
        print(f"エラー: {CSV_FILE} が見つかりません。")
        return
        
    try:
        # CSVに「code」または「コード」という列があることを想定
        df_mini = pd.read_csv(CSV_FILE)
        # 列名に合わせて適宜変更してください（ここでは最初の列をコードとみなす例）
        code_column = df_mini.columns[0]
        tickers = df_mini[code_column].dropna().astype(str).tolist()
    except Exception as e:
        print(f"CSVの読み込みに失敗しました: {e}")
        return

    # 2. 各銘柄のブレイクアウトチェック
    breakout_signals = []
    for ticker in tickers:
        # 4桁の数字コードのみを抽出（余計な文字排除）
        clean_ticker = "".join(filter(str.isdigit, ticker))
        if not clean_ticker:
            continue
            
        print(f"チェック中: {clean_ticker}")
        result = check_breakout(clean_ticker)
        if result:
            breakout_signals.append(result)

    # 3. 結果の通知
    if breakout_signals:
        msg = "\n【株ミニ・夕方スキャン結果】\nブレイクアウトを検知しました！\n"
        for sig in breakout_signals:
            msg += f"\n・証券コード: {sig['symbol']}\n  本日終値: {sig['close']:.1f}円 (過去最高値: {sig['highest']:.1f}円)\n"
        
        print(msg)
        send_line_notify(msg)
    else:
        print("本日ブレイクアウトした株ミニ銘柄はありませんでした。")

if __name__ == "__main__":
    main()
