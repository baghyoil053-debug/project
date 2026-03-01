import pandas as pd
import pandas_ta as ta
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime


def run_advanced_backtest_with_period(symbols, start_date="2021-01-01", end_date=None, initial_capital=10000000.0):
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')

    summary_results = []

    for symbol in symbols:
        df = yf.download(symbol, start=start_date, end=end_date, interval="1d", progress=False) #시작날짜와 끝나는 날짜+분석할 그래프 차트(일,주,년봉)

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if df.empty or len(df) < 20:
            print(f"[{symbol}] 데이터가 부족하거나 가져오지 못했습니다.")
            continue

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

        for i in range(15, len(df)):
            curr = df.iloc[i]
            rsi_val, close_val, ma3_val, support_val, vola_val = \
                float(curr['rsi']), float(curr['Close']), float(curr['ma3']), float(curr['support']), float(
                    curr['vola'])
            # 내 매매전략이 들어간부분, rsi값과 매매량부분은 종목 특성에 따라 조정이 필요할듯.
            cond_buy = (rsi_val < 50 and vola_val < 20 and close_val > ma3_val and close_val <= support_val * 1.10)

            if not holding and cond_buy:
                buy_price = close_val
                position = capital // buy_price
                capital -= position * buy_price
                holding, half_sold = True, False
                buys.append(df.index[i])
                trades += 1

            elif holding:
                if rsi_val > 70 and not half_sold:
                    capital += (position // 2) * close_val
                    position -= (position // 2)
                    half_sold = True
                # 익절 2 & 손절: 추세 이탈(3주선) 또는 손절선(지지선 15%) 이탈
                # (RSI가 85을 넘는 과열 시에도 일단 전량 탈출)
                stop_loss = close_val < (support_val * 0.85)
                trend_end = (half_sold and close_val < ma3_val)
                overheat = (not half_sold and rsi_val > 85)

                if stop_loss or trend_end or overheat:
                    if close_val > buy_price: win_trades += 1
                    capital += position * close_val
                    position, holding = 0, False
                    sells.append(df.index[i])

            df.loc[df.index[i], 'total_assets'] = float(capital + (position * close_val))

        # --- 수익금액 및 성적 계산 ---
        final_assets = float(df['total_assets'].iloc[-1])
        profit_amt = final_assets - initial_capital  # 수익금액 계산
        final_ret = (profit_amt / initial_capital) * 100
        win_rate = (win_trades / trades * 100) if trades > 0 else 0

        summary_results.append({
            'Sym': symbol,
            'Ret': final_ret,
            'Profit': profit_amt,  # 수익금액 저장
            'Win': win_rate,
            'Trades': trades
        })

        # 그래프 시뮬레이션
        plt.figure(figsize=(12, 8))
        ax1 = plt.subplot(2, 1, 1)
        plt.plot(df.index, df['Close'], color='gray', alpha=0.4, label='Price')
        if buys: plt.scatter(buys, df.loc[buys, 'Close'], marker='^', color='red', s=80, label='BUY')
        if sells: plt.scatter(sells, df.loc[sells, 'Close'], marker='v', color='blue', s=80, label='SELL')
        plt.title(f"{symbol} ({start_date} ~ {end_date}) | Profit: {profit_amt:,.0f} KRW")
        plt.legend()
        plt.grid(True, alpha=0.2)

        ax2 = plt.subplot(2, 1, 2, sharex=ax1)
        plt.plot(df.index, df['total_assets'], color='green', label='Asset Flow')
        plt.ylabel("Asset Value")
        plt.legend()
        plt.grid(True, alpha=0.2)
        plt.tight_layout()
        plt.show()
        plt.close()

    # 최종 결과표 출력 (수익금액 컬럼 추가)
    print(f"\n===== 백테스트 결과 요약 ({start_date} ~ {end_date}) =====")
    print(f"{'종목':<10} | {'수익률':>9} | {'수익금액':>14} | {'승률':>7} | {'횟수':>4}")
    print("-" * 65)
    for r in summary_results:
        # 수익금액에 천단위 콤마 추가
        print(f"{r['Sym']:<10} | {r['Ret']:>8.2f}% | {r['Profit']:>12,.0f}원 | {r['Win']:>6.1f}% | {r['Trades']:>5}")
    print("=" * 65)


# --- 설정값 ---
target_stocks = ["QQQ", "NVDA", "TSLA", "005930.KS", "000660.KS"]
my_start = "2024-01-01"
my_end = "2026-02-27"

run_advanced_backtest_with_period(target_stocks, start_date=my_start, end_date=my_end)