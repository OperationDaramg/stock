"""간단한 백테스팅 모듈.

기술적 카테고리(D 모멘텀, E 과매도, F 단기 관심)에 대해
과거 시점에서 신호가 발생한 종목을 N일 후 매도했을 때의 가상 수익률을 계산한다.

펀더멘털 카테고리(A, B, C)는 시점별 PER/ROE/DIV 데이터가 필요하여 본 모듈에서는 제외.

본 백테스팅 결과는 과거 가상 시뮬레이션이며 미래 수익을 보장하지 않습니다.
"""

from datetime import datetime, timedelta

import FinanceDataReader as fdr
import pandas as pd

from src.indicators import calculate_rsi


def _fetch_long_ohlcv(code: str, end_date: str, days: int = 365) -> pd.DataFrame:
    end_dt = datetime.strptime(end_date, "%Y%m%d")
    start = end_dt - timedelta(days=days)
    return fdr.DataReader(code, start, end_dt)


def _detect_signals_at(close: pd.Series, volume: pd.Series, idx: int) -> dict:
    """idx 시점까지의 데이터로 D/E/F 신호를 계산. idx 이후 데이터 사용 금지(look-ahead 방지)."""
    if idx < 25:
        return {"D": False, "E": False, "F": False}

    win_close = close.iloc[: idx + 1]
    win_volume = volume.iloc[: idx + 1]

    ma5 = win_close.rolling(5).mean()
    ma20 = win_close.rolling(20).mean()

    if len(win_volume) < 21:
        return {"D": False, "E": False, "F": False}

    avg_vol_20 = win_volume.iloc[-21:-1].mean()
    today_vol = win_volume.iloc[-1]
    vol_ratio = today_vol / avg_vol_20 if avg_vol_20 > 0 else 0

    rsi = calculate_rsi(win_close, 14)

    # D: 모멘텀 (최근 5일 내 골든크로스 + 거래량 1.5배)
    crossed = (ma5 > ma20) & (ma5.shift(1) <= ma20.shift(1))
    d_signal = bool(crossed.tail(5).any()) and vol_ratio >= 1.5

    # E: 과매도 반등 (RSI < 30)
    e_signal = rsi is not None and rsi < 30

    # F: 단기 관심 (5일+3% & 20일-10% 이상 & 거래량 1.5배 & RSI 30~70)
    if len(win_close) >= 21:
        ret_5d = (win_close.iloc[-1] / win_close.iloc[-6] - 1) * 100
        ret_20d = (win_close.iloc[-1] / win_close.iloc[-21] - 1) * 100
        f_signal = (
            ret_5d >= 3 and ret_20d >= -10
            and vol_ratio >= 1.5
            and rsi is not None and 30 <= rsi <= 70
        )
    else:
        f_signal = False

    return {"D": d_signal, "E": e_signal, "F": f_signal}


def run_backtest(
    universe_codes: list[str],
    code_to_name: dict[str, str],
    end_date: str,
    backtest_days: int = 180,
    holding_days: int = 5,
    rebalance_days: int = 5,
) -> dict[str, pd.DataFrame]:
    """카테고리별 가상 거래 내역 DataFrame 반환.

    Args:
        universe_codes: 시뮬레이션 대상 종목 코드 리스트
        code_to_name: 종목코드 → 종목명 매핑
        end_date: 백테스팅 종료일 (YYYYMMDD)
        backtest_days: 백테스팅 기간 (영업일 기준 약 N일)
        holding_days: 신호 발생 후 보유 영업일
        rebalance_days: 신호 체크 주기 (영업일)

    Returns:
        {'D': DataFrame, 'E': DataFrame, 'F': DataFrame} 형식. 각 DataFrame은 매수일/매도일/수익률 등.
    """
    print(f"[백테스팅] 대상 {len(universe_codes)}종목, 기간 {backtest_days}일, 보유 {holding_days}일")
    trades = {"D": [], "E": [], "F": []}

    for i, code in enumerate(universe_codes):
        try:
            df = _fetch_long_ohlcv(code, end_date, backtest_days + 100)
            if len(df) < 50:
                continue
            close = df["Close"]
            volume = df["Volume"]
            name = code_to_name.get(code, code)

            start_idx = max(25, len(df) - backtest_days)

            for idx in range(start_idx, len(df) - holding_days, rebalance_days):
                signals = _detect_signals_at(close, volume, idx)
                exit_idx = idx + holding_days
                if exit_idx >= len(df):
                    break
                buy = float(close.iloc[idx])
                sell = float(close.iloc[exit_idx])
                if buy <= 0:
                    continue
                ret = (sell / buy - 1) * 100
                for cat in ("D", "E", "F"):
                    if signals.get(cat):
                        trades[cat].append({
                            "Code": code,
                            "종목명": name,
                            "매수일": df.index[idx].strftime("%Y-%m-%d"),
                            "매도일": df.index[exit_idx].strftime("%Y-%m-%d"),
                            "매수가": int(buy),
                            "매도가": int(sell),
                            "수익률(%)": round(ret, 2),
                        })
        except Exception:
            continue
        if (i + 1) % 25 == 0:
            print(f"  → {i+1}/{len(universe_codes)} 처리됨")

    return {cat: pd.DataFrame(rows) for cat, rows in trades.items()}


def summarize(trades: dict[str, pd.DataFrame], holding_days: int) -> pd.DataFrame:
    """카테고리별 백테스팅 통계 요약."""
    rows = []
    cat_names = {"D": "[D] 모멘텀", "E": "[E] 과매도", "F": "[F] 단기관심"}

    for cat, df in trades.items():
        if df.empty:
            rows.append({"카테고리": cat_names[cat], "거래수": 0})
            continue
        ret = df["수익률(%)"]
        wins = (ret > 0).sum()
        rows.append({
            "카테고리": cat_names[cat],
            "거래수": len(df),
            "평균수익률(%)": round(ret.mean(), 2),
            "승률(%)": round(wins / len(df) * 100, 1),
            "최대수익(%)": round(ret.max(), 2),
            "최대손실(%)": round(ret.min(), 2),
            "표준편차": round(ret.std(), 2),
            "보유기간": f"{holding_days}일",
        })
    return pd.DataFrame(rows)
