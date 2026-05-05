"""6개 카테고리 스크리너. 각 카테고리는 universe DataFrame을 입력받아 상위 종목을 반환."""

import pandas as pd

from src.config import MIN_MARKET_CAP_BIL, TECH_UNIVERSE_SIZE, TOP_N, VOL_SURGE_RATIO
from src.grading import (
    grade_bluechip,
    grade_div,
    grade_momentum,
    grade_oversold,
    grade_short_term,
    grade_value,
)
from src.indicators import calculate_rsi, fetch_ohlcv


# ---- A: 저평가 가치주 ----

def screen_value(df: pd.DataFrame) -> pd.DataFrame:
    f = df[
        df["PER"].notna() & df["ROE"].notna()
        & (df["PER"] > 0) & (df["PER"] < 30)
        & (df["ROE"] > 5)
        & (df["시총_억"] >= MIN_MARKET_CAP_BIL)
    ].copy()
    f["PER_pct"] = f["PER"].rank(pct=True)
    f["ROE_pct"] = f["ROE"].rank(pct=True, ascending=False)
    f["점수"] = (f["PER_pct"] + f["ROE_pct"]).round(3)
    f = f.sort_values("점수").head(TOP_N)
    f["평가"] = f["점수"].apply(grade_value)
    return f[["종목명", "섹터", "PER", "ROE", "종가", "시총_억", "점수", "평가"]]


# ---- B: 고배당주 ----

def screen_dividend(df: pd.DataFrame) -> pd.DataFrame:
    f = df[
        df["DIV"].notna() & (df["DIV"] > 0)
        & (df["시총_억"] >= MIN_MARKET_CAP_BIL)
    ].copy()
    f = f.sort_values("DIV", ascending=False).head(TOP_N)
    f["평가"] = f["DIV"].apply(grade_div)
    return f[["종목명", "섹터", "DIV", "DPS", "PER", "ROE", "종가", "시총_억", "평가"]]


# ---- C: 대형 우량주 ----

def screen_bluechip(df: pd.DataFrame) -> pd.DataFrame:
    f = df[(df["거래량"] > 0) & (df["PER"].fillna(-1) > 0)].copy()
    f = f.sort_values("시총_억", ascending=False).head(TOP_N)
    f["평가"] = [grade_bluechip(i + 1) for i in range(len(f))]
    return f[["종목명", "섹터", "시총_억", "종가", "거래량", "PER", "ROE", "DIV", "평가"]]


# ---- D, E, F: OHLCV 1회 조회로 동시 계산 ----

def screen_technical(df: pd.DataFrame, date: str):
    universe = df.sort_values("시총_억", ascending=False).head(TECH_UNIVERSE_SIZE)
    print(f"  → 기술적 지표 계산 대상: {len(universe)}개 (OHLCV 1회 → D/E/F 동시 산출)")

    momentum_rows, oversold_rows, short_term_rows = [], [], []

    for i, code in enumerate(universe.index):
        try:
            ohlcv = fetch_ohlcv(code, date, 90)
            if len(ohlcv) < 25:
                continue
            close = ohlcv["종가"]
            volume = ohlcv["거래량"]
            name = universe.loc[code, "종목명"]
            sector = universe.loc[code, "섹터"]
            mcap = int(universe.loc[code, "시총_억"])
            per = universe.loc[code, "PER"]
            roe = universe.loc[code, "ROE"]
            cur = int(close.iloc[-1])

            ma5 = close.rolling(5).mean()
            ma20 = close.rolling(20).mean()
            avg_vol_20 = volume.tail(21).head(20).mean()
            today_vol = volume.iloc[-1]
            vol_ratio = today_vol / avg_vol_20 if avg_vol_20 > 0 else 0
            rsi = calculate_rsi(close, 14)
            ret_5d = (close.iloc[-1] / close.iloc[-6] - 1) * 100 if len(close) >= 6 else None
            ret_20d = (close.iloc[-1] / close.iloc[-21] - 1) * 100 if len(close) >= 21 else None

            crossed = (ma5 > ma20) & (ma5.shift(1) <= ma20.shift(1))
            if crossed.tail(5).any() and vol_ratio >= VOL_SURGE_RATIO:
                momentum_rows.append({
                    "Code": code, "종목명": name, "섹터": sector, "종가": cur,
                    "MA5": round(float(ma5.iloc[-1]), 2),
                    "MA20": round(float(ma20.iloc[-1]), 2),
                    "거래량배수": round(float(vol_ratio), 2),
                    "5일수익률(%)": round(ret_5d, 2) if ret_5d is not None else None,
                    "시총_억": mcap,
                })

            if rsi is not None and rsi < 30:
                oversold_rows.append({
                    "Code": code, "종목명": name, "섹터": sector, "종가": cur,
                    "RSI14": round(rsi, 2),
                    "5일수익률(%)": round(ret_5d, 2) if ret_5d is not None else None,
                    "PER": per, "ROE": roe, "시총_억": mcap,
                })

            if (
                ret_5d is not None and ret_5d >= 3
                and ret_20d is not None and ret_20d >= -10
                and vol_ratio >= 1.5
                and rsi is not None and 30 <= rsi <= 70
                and not pd.isna(per) and per > 0
            ):
                short_term_rows.append({
                    "Code": code, "종목명": name, "섹터": sector, "종가": cur,
                    "5일수익률(%)": round(ret_5d, 2),
                    "20일수익률(%)": round(ret_20d, 2),
                    "거래량배수": round(float(vol_ratio), 2),
                    "RSI14": round(rsi, 1),
                    "PER": per, "점수": round(ret_5d + vol_ratio, 2),
                    "시총_억": mcap,
                })
        except Exception:
            continue
        if (i + 1) % 25 == 0:
            print(f"  → {i+1}/{len(universe)} 처리됨")

    mom = pd.DataFrame(momentum_rows).set_index("Code") if momentum_rows else pd.DataFrame()
    if not mom.empty:
        mom = mom.sort_values("거래량배수", ascending=False).head(TOP_N)
        mom["평가"] = mom["거래량배수"].apply(grade_momentum)

    over = pd.DataFrame(oversold_rows).set_index("Code") if oversold_rows else pd.DataFrame()
    if not over.empty:
        over = over.sort_values("RSI14").head(TOP_N)
        over["평가"] = over["RSI14"].apply(grade_oversold)

    short = pd.DataFrame(short_term_rows).set_index("Code") if short_term_rows else pd.DataFrame()
    if not short.empty:
        short = short.sort_values("점수", ascending=False).head(TOP_N)
        short["평가"] = short["점수"].apply(grade_short_term)

    return mom, over, short
