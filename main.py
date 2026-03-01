import os
import time
import pandas as pd
import pandas_ta as ta
import mojito
from dotenv import load_dotenv
from datetime import datetime

# 1. .env 파일 로드
load_dotenv()

# 2. 환경 변수에서 설정값 가져오기
KEY = os.getenv("KIS_API_KEY")
SECRET = os.getenv("KIS_API_SECRET")
ACC_NO = os.getenv("KIS_ACC_NO")

# 접속 객체 생성
broker = mojito.KoreaInvestment(
    api_key=KEY,
    api_secret=SECRET,
    acc_no=ACC_NO,
    mock=False  # 테스트 완료 후 실제 매매 시 False로 변경
)


def get_weekly_data(symbol):
    """주봉 데이터를 가져와 지표를 계산합니다."""
    res = broker.fetch_ohlcv(symbol, timeframe='W', adj_price=True)
    df = pd.DataFrame(res['output2'])

    # 데이터 전처리 (문자열 -> 숫자형 변환)
    df[['close', 'high', 'low', 'open', 'vol']] = \
        df[['stck_clpr', 'stck_hgpr', 'stck_lwpr', 'stck_oprc', 'acml_vol']].apply(pd.to_numeric)

    # 지표 계산을 위해 과거->현재 순으로 정렬
    df = df.iloc[::-1].reset_index(drop=True)

    # 전략 지표 추가
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['ma5'] = ta.sma(df['close'], length=5)
    df['vola'] = ((df['high'] - df['low']) / df['low']) * 100  # 주봉 변동성

    return df


def execute_strategy(symbol):
    print(f"\n[분석 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 종목: {symbol}")

    try:
        df = get_weekly_data(symbol)
        curr = df.iloc[-1]  # 현재(이번 주)
        prev = df.iloc[-2]  # 직전(지난 주)

        # 최근 10주 최저가 (지지선)
        support_price = df['low'].tail(10).min()

        # --- 사용자 매매 전략 조건 ---
        # 1. RSI 35 미만 (과매도 진입)
        cond_rsi = curr['rsi'] < 35
        # 2. 주봉 변동성 10% 미만 (에너지 응축)
        cond_narrow = curr['vola'] < 10
        # 3. 거래량 증가 트리거 (전주 대비 20% 이상)
        cond_vol_up = curr['vol'] > prev['vol'] * 1.2
        # 4. 추세 전환 (주가 > 주봉 5선)
        cond_trend = curr['close'] > curr['ma5']
        # 5. 지지선 부근 매수 (최저가 대비 5% 이내)
        cond_at_support = curr['close'] <= support_price * 1.05

        # 모든 조건 충족 시
        if cond_rsi and cond_narrow and cond_vol_up and cond_trend and cond_at_support:
            print(f"✅ 매수 신호 포착! ({symbol})")

            # 잔고 조회 및 수량 계산
            balance = broker.fetch_balance()
            # D+2 예수금 추출 (라이브러리 응답 구조 확인 필요)
            cash = int(balance['output2'][0]['n_dr_p_rcv_amt_evat'])

            # 예수금의 20% 투입
            budget = cash * 0.2
            qty = int(budget // curr['close'])

            if qty > 0:
                # 시장가 매수 주문
                order_res = broker.create_market_buy_order(symbol, qty)
                print(f"🚀 주문 실행 완료: {qty}주 매수 / 응답코드: {order_res.get('rt_cd')}")
            else:
                print("⚠️ 잔고가 부족하여 주문을 생성할 수 없습니다.")
        else:
            # 조건 미충족 시 로그 출력
            print(f"❌ 조건 미충족 - RSI: {curr['rsi']:.1f}, 변동성: {curr['vola']:.1f}%, 거래량: {curr['vol']}")

    except Exception as e:
        print(f"❗ 에러 발생 ({symbol}): {e}")


# --- 실행부 ---
if __name__ == "__main__":
    # 감시 종목 리스트
    target_list = ["005930", "000660", "035420"]

    for stock in target_list:
        execute_strategy(stock)
        time.sleep(1)  # API 초당 호출 제한 방지