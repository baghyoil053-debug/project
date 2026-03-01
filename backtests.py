import pandas as pd
import pandas_ta as ta
import requests
import json
import time
import matplotlib.pyplot as plt
import os
from dotenv import load_dotenv

load_dotenv()

# 1. 인증 정보 (입력하신 모의투자 정보 유지)
APP_KEY =  os.getenv("KIS_API_KEY")
APP_SECRET = os.getenv("KIS_API_SECRET")
URL_BASE = "https://openapivts.koreainvestment.com:29443"


def get_access_token():
    headers = {"content-type": "application/json"}
    body = {"grant_type": "client_credentials", "appkey": APP_KEY, "appsecret": APP_SECRET}
    res = requests.post(f"{URL_BASE}/oauth2/tokenP", headers=headers, data=json.dumps(body))
    if res.status_code == 200:
        return res.json().get('access_token')
    return None


def get_ohlcv_long(symbol, start_date, end_date, token):
    path = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
    headers = {
        "Content-Type": "application/json", "authorization": f"Bearer {token}",
        "appkey": APP_KEY, "appsecret": APP_SECRET, "tr_id": "FHKST03010100"
    }
    all_df = []
    current_end = end_date
    while True:
        params = {
            "FID_COND_MRKT_DIV_CODE": "J", "FID_COND_SCR_DIV_MS": "J",
            "FID_INPUT_ISCD": symbol, "FID_INPUT_DATE_1": start_date,
            "FID_INPUT_DATE_2": current_end, "FID_PERIOD_DIV_CODE": "D", "FID_ORG_ADJ_PRC": "1"
        }
        res = requests.get(f"{URL_BASE}{path}", headers=headers, params=params)
        data = res.json().get('output2', [])
        if not data: break
        df = pd.DataFrame(data)
        all_df.append(df)
        last_date = df.iloc[-1]['stck_bsop_date']
        if int(last_date) <= int(start_date) or len(data) < 100: break
        current_end = str(int(last_date) - 1)
        time.sleep(0.1)

    final_df = pd.concat(all_df).drop_duplicates()
    final_df = final_df[['stck_bsop_date', 'stck_clpr', 'stck_hgpr', 'stck_lwpr', 'stck_oprc']]
    final_df.columns = ['Date', 'Close', 'High', 'Low', 'Open']
    final_df[['Close', 'High', 'Low', 'Open']] = final_df[['Close', 'High', 'Low', 'Open']].astype(float)
    final_df['Date'] = pd.to_datetime(final_df['Date'])
    return final_df.sort_values('Date').set_index('Date')


# --- 핵심: 매매 전략 및 시뮬레이션 함수 ---
def run_kis_backtest(symbols, start_date, end_date, initial_capital=10000000.0):
    token = get_access_token()
    if not token:
        print("토큰 발급에 실패했습니다.")
        return

    summary_results = []

    for symbol in symbols:
        try:
            df = get_ohlcv_long(symbol, start_date, end_date, token)
            if df.empty or len(df) < 20:
                print(f"[{symbol}] 데이터가 부족합니다.")
                continue

            # 지표 계산
            df['rsi'] = ta.rsi(df['Close'], length=14)
            df['ma3'] = ta.sma(df['Close'], length=3)
            df['vola'] = ((df['High'] - df['Low']) / df['Low']) * 100
            df['support'] = df['Low'].rolling(window=10).min()

            capital = float(initial_capital)
            position = 0.0
            df['total_assets'] = float(initial_capital)
            buys, sells = [], []
            trades, win_trades = 0, 0
            holding, half_sold = False, False
            buy_price = 0.0

            # 시뮬레이션 루프
            for i in range(15, len(df)):
                curr = df.iloc[i]
                rsi_val, close_val, ma3_val, support_val, vola_val = \
                    float(curr['rsi']), float(curr['Close']), float(curr['ma3']), float(curr['support']), float(
                        curr['vola'])

                # 매수 조건
                cond_buy = (rsi_val < 50 and vola_val < 20 and close_val > ma3_val and close_val <= support_val * 1.10)

                if not holding and cond_buy:
                    buy_price = close_val
                    position = capital // buy_price
                    capital -= position * buy_price
                    holding, half_sold = True, False
                    buys.append(df.index[i])
                    trades += 1

                elif holding:
                    # 익절 1: RSI 70 돌파 시 절반 매도
                    if rsi_val > 70 and not half_sold:
                        capital += (position // 2) * close_val
                        position -= (position // 2)
                        half_sold = True

                    # 매도/손절 조건
                    stop_loss = close_val < (support_val * 0.85)
                    trend_end = (half_sold and close_val < ma3_val)
                    overheat = (not half_sold and rsi_val > 85)

                    if stop_loss or trend_end or overheat:
                        if close_val > buy_price: win_trades += 1
                        capital += position * close_val
                        position, holding = 0, False
                        sells.append(df.index[i])

                df.loc[df.index[i], 'total_assets'] = float(capital + (position * close_val))

            # 결과 계산
            final_assets = float(df['total_assets'].iloc[-1])
            profit_amt = final_assets - initial_capital
            final_ret = (profit_amt / initial_capital) * 100
            win_rate = (win_trades / trades * 100) if trades > 0 else 0

            summary_results.append({
                'Sym': symbol, 'Ret': final_ret, 'Profit': profit_amt, 'Win': win_rate, 'Trades': trades
            })

            # 그래프 시뮬레이션
            plt.figure(figsize=(12, 8))
            ax1 = plt.subplot(2, 1, 1)
            plt.plot(df.index, df['Close'], color='gray', alpha=0.4, label='Price')
            if buys: plt.scatter(buys, df.loc[buys, 'Close'], marker='^', color='red', s=80, label='BUY')
            if sells: plt.scatter(sells, df.loc[sells, 'Close'], marker='v', color='blue', s=80, label='SELL')
            plt.title(f"{symbol} Backtest | Profit: {profit_amt:,.0f} KRW")
            plt.legend();
            plt.grid(True, alpha=0.2)

            ax2 = plt.subplot(2, 1, 2, sharex=ax1)
            plt.plot(df.index, df['total_assets'], color='green', label='Asset Flow')
            plt.ylabel("Asset Value");
            plt.legend();
            plt.grid(True, alpha=0.2)
            plt.tight_layout();
            plt.show()

        except Exception as e:
            print(f"[{symbol}] 에러 발생: {e}")

    # 결과 요약 출력
    print(f"\n===== 백테스트 결과 요약 ({start_date} ~ {end_date}) =====")
    print(f"{'종목':<10} | {'수익률':>9} | {'수익금액':>14} | {'승률':>7} | {'횟수':>4}")
    print("-" * 65)
    for r in summary_results:
        print(f"{r['Sym']:<10} | {r['Ret']:>8.2f}% | {r['Profit']:>12,.0f}원 | {r['Win']:>6.1f}% | {r['Trades']:>5}")
    print("=" * 65)


# 실행
target_stocks = ["005930", "000660"]
run_kis_backtest(target_stocks, "20240101", "20260227")
