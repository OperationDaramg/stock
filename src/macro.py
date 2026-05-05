"""글로벌 거시 지표 로딩 (주가 지수, 환율, 원자재)."""

from datetime import datetime, timedelta

import FinanceDataReader as fdr
import pandas as pd


INDICES = {
    "KS11": "코스피",
    "KQ11": "코스닥",
    "US500": "S&P 500",
    "IXIC": "나스닥",
    "DJI": "다우존스",
    "JP225": "닛케이225",
    "HSI": "항셍",
    "VIX": "VIX (공포지수)",
}

CURRENCIES = {
    "USD/KRW": "원/달러",
    "USD/JPY": "엔/달러",
    "USD/EUR": "유로/달러",
}

COMMODITIES = {
    "CL=F": "WTI 원유",
    "GC=F": "금",
    "SI=F": "은",
}


def load_series(symbol: str, days: int = 90) -> pd.DataFrame:
    end = datetime.now()
    start = end - timedelta(days=days)
    return fdr.DataReader(symbol, start, end)


def summary_table(symbols_dict: dict, days: int = 90) -> pd.DataFrame:
    """각 심볼의 최근값 + 1일/5일/20일 변동률 표."""
    rows = []
    for sym, name in symbols_dict.items():
        try:
            df = load_series(sym, days)
            if df.empty:
                continue
            close = df["Close"]
            cur = float(close.iloc[-1])
            row = {"심볼": sym, "이름": name, "현재값": round(cur, 2)}
            if len(close) >= 2:
                row["1일(%)"] = round((cur / float(close.iloc[-2]) - 1) * 100, 2)
            if len(close) >= 6:
                row["5일(%)"] = round((cur / float(close.iloc[-6]) - 1) * 100, 2)
            if len(close) >= 21:
                row["20일(%)"] = round((cur / float(close.iloc[-21]) - 1) * 100, 2)
            rows.append(row)
        except Exception:
            continue
    return pd.DataFrame(rows)


def market_sentiment(
    vix_level: float | None,
    kospi_20d_change: float | None,
    sp500_20d_change: float | None,
) -> tuple[str, str, int]:
    """간단한 룰 기반 시장 분위기 판정.

    Returns:
        (등급_라벨, 설명, 점수)
    """
    score = 0
    reasons = []

    if vix_level is not None:
        if vix_level < 15:
            score += 2; reasons.append(f"VIX {vix_level:.1f} (매우 낮음)")
        elif vix_level < 20:
            score += 1; reasons.append(f"VIX {vix_level:.1f} (낮음)")
        elif vix_level < 25:
            score -= 1; reasons.append(f"VIX {vix_level:.1f} (다소 높음)")
        else:
            score -= 2; reasons.append(f"VIX {vix_level:.1f} (높음)")

    if kospi_20d_change is not None:
        if kospi_20d_change > 5:
            score += 2; reasons.append(f"코스피 20일 +{kospi_20d_change:.1f}%")
        elif kospi_20d_change > 0:
            score += 1; reasons.append(f"코스피 20일 +{kospi_20d_change:.1f}%")
        elif kospi_20d_change > -5:
            score -= 1; reasons.append(f"코스피 20일 {kospi_20d_change:.1f}%")
        else:
            score -= 2; reasons.append(f"코스피 20일 {kospi_20d_change:.1f}%")

    if sp500_20d_change is not None:
        if sp500_20d_change > 3:
            score += 1; reasons.append(f"S&P500 20일 +{sp500_20d_change:.1f}%")
        elif sp500_20d_change < -3:
            score -= 1; reasons.append(f"S&P500 20일 {sp500_20d_change:.1f}%")

    if score >= 4:
        label = "🟢 강세장 (Risk-On)"
    elif score >= 1:
        label = "🟢 우호적"
    elif score >= -1:
        label = "🟡 중립"
    elif score >= -3:
        label = "🟠 약세 우려"
    else:
        label = "🔴 약세장 (Risk-Off)"

    return label, " · ".join(reasons), score
