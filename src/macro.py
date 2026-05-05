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


def sentiment_bucket(score: int) -> str:
    """점수 → 5단계 분위기 키."""
    if score >= 4:
        return "strong_bull"
    if score >= 1:
        return "bull"
    if score >= -1:
        return "neutral"
    if score >= -3:
        return "bear"
    return "strong_bear"


# 카테고리 × 시장분위기 → (적합도 배지, 이유)
_FIT_TABLE: dict[tuple[str, str], tuple[str, str]] = {
    # A 저평가 가치주 — 시장 무관 안정, 약세에서 더 빛남
    ("A", "strong_bull"): ("○ 무난", "강세장은 성장주 선호 경향"),
    ("A", "bull"): ("○ 무난", "가치주는 추세 영향 적음"),
    ("A", "neutral"): ("○ 적합", "중립장에서 안정적 후보"),
    ("A", "bear"): ("◎ 매우 적합", "약세장 방어 자산으로 선호"),
    ("A", "strong_bear"): ("◎ 매우 적합", "약세장에서 가치 회복 기대"),

    # B 고배당주 — 약세에서 현금흐름 매력 ↑
    ("B", "strong_bull"): ("△ 평이", "강세장은 성장주 선호"),
    ("B", "bull"): ("○ 무난", "안정 수익 추구"),
    ("B", "neutral"): ("○ 적합", "배당이 안정성 기여"),
    ("B", "bear"): ("◎ 매우 적합", "배당이 손실 완충"),
    ("B", "strong_bear"): ("◎ 매우 적합", "현금흐름 가치 부각"),

    # C 대형 우량주 — 모든 환경에서 무난
    ("C", "strong_bull"): ("○ 무난", "대형주는 시장 추종"),
    ("C", "bull"): ("○ 무난", "대형주 안정"),
    ("C", "neutral"): ("○ 적합", "중립장 선호"),
    ("C", "bear"): ("○ 적합", "약세장 방어"),
    ("C", "strong_bear"): ("○ 적합", "약세장 방어"),

    # D 모멘텀 — 강세장 친화, 약세장 위험
    ("D", "strong_bull"): ("◎ 매우 적합", "강세장은 모멘텀의 시기"),
    ("D", "bull"): ("◎ 매우 적합", "추세 추종에 우호적"),
    ("D", "neutral"): ("○ 무난", "중립장에서는 신중히"),
    ("D", "bear"): ("△ 주의", "약세장에서 거짓 신호 위험"),
    ("D", "strong_bear"): ("⚠ 비권장", "약세장 모멘텀은 함정 가능"),

    # E 과매도 반등 — 약세장에서는 추세적 하락 가능
    ("E", "strong_bull"): ("△ 평이", "강세장 RSI<30은 일시적"),
    ("E", "bull"): ("○ 무난", "단기 반등 기대"),
    ("E", "neutral"): ("○ 적합", "기술적 반등 가능 구간"),
    ("E", "bear"): ("△ 주의", "약세장에서 추세 하락 위험"),
    ("E", "strong_bear"): ("⚠ 비권장", "약세장 RSI<30은 추세적 하락 신호일 수 있음"),

    # F 단기 관심 — 강세장 친화, 약세장 위험
    ("F", "strong_bull"): ("◎ 매우 적합", "강세장 단기 트레이딩 최적"),
    ("F", "bull"): ("◎ 매우 적합", "우호적 환경"),
    ("F", "neutral"): ("○ 무난", "중립장에서는 신중히"),
    ("F", "bear"): ("△ 주의", "약세장 추세 반전 위험"),
    ("F", "strong_bear"): ("⚠ 비권장", "약세장 단기 매매는 위험"),
}


def category_market_fit(score: int, category_key: str) -> tuple[str, str]:
    """시장 점수에 따른 카테고리 적합도.

    Args:
        score: market_sentiment의 점수 (-6 ~ +6)
        category_key: 'A_가치주', 'B_배당주', ..., 'F_단기관심'

    Returns:
        (배지, 이유). 예: ('◎ 매우 적합', '강세장은 모멘텀의 시기')
    """
    cat = category_key[:1]  # A/B/C/D/E/F
    bucket = sentiment_bucket(score)
    return _FIT_TABLE.get((cat, bucket), ("○ 무난", ""))


def fetch_market_state() -> tuple[str, str, int]:
    """시장 분위기 라벨/이유/점수를 한 번에 계산. 캐시는 호출자 측에서."""
    indices = summary_table(INDICES, days=60)
    vix_level = None
    kospi_20d = None
    sp500_20d = None
    if not indices.empty:
        for _, r in indices.iterrows():
            if r["심볼"] == "VIX":
                vix_level = float(r["현재값"])
            if r["심볼"] == "KS11" and "20일(%)" in indices.columns:
                v = r.get("20일(%)")
                kospi_20d = float(v) if v is not None and not pd.isna(v) else None
            if r["심볼"] == "US500" and "20일(%)" in indices.columns:
                v = r.get("20일(%)")
                sp500_20d = float(v) if v is not None and not pd.isna(v) else None
    return market_sentiment(vix_level, kospi_20d, sp500_20d)
