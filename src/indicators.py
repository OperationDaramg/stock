"""기술적 지표 계산."""

from datetime import datetime, timedelta

import FinanceDataReader as fdr
import pandas as pd


def calculate_rsi(close: pd.Series, period: int = 14) -> float | None:
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    if len(rsi) == 0:
        return None
    last = rsi.iloc[-1]
    return None if pd.isna(last) else float(last)


def fetch_ohlcv(ticker: str, end_date: str, lookback_days: int = 90) -> pd.DataFrame:
    """FinanceDataReader로 OHLCV 조회. 컬럼명 한글로 정규화."""
    end_dt = datetime.strptime(end_date, "%Y%m%d")
    start = end_dt - timedelta(days=lookback_days)
    df = fdr.DataReader(ticker, start, end_dt)
    return df.rename(columns={"Close": "종가", "Volume": "거래량"})
