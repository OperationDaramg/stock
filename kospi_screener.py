"""KOSPI 카테고리별 스크리닝 도구.

5개 카테고리로 코스피 종목을 필터링하여 docs/YYYYMMDD/ 폴더에 결과를 저장한다.
- A: 저평가 가치주 (저PER + 고ROE)
- B: 고배당주 (배당수익률 상위)
- C: 대형 우량주 (시총 상위)
- D: 모멘텀 (5일 내 골든크로스 + 거래량 급증)
- E: 과매도 반등 (RSI14 < 30)

데이터 소스:
- FinanceDataReader: 코스피 종목 리스트 + 시총/거래량/현재가 + 개별 OHLCV
- 네이버 금융 시가총액 페이지: PER, ROE
- 네이버 금융 배당 페이지: 배당수익률

본 결과는 단순 조건 필터링이며 투자 추천이 아니다.
"""

import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import FinanceDataReader as fdr
import pandas as pd
import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
sys.stderr.reconfigure(encoding="utf-8")


TOP_N = 10
MIN_MARKET_CAP_BIL = 1000  # 1000억(억 단위) 미만 컷
TECH_UNIVERSE_SIZE = 150  # 기술적 지표 계산은 시총 상위 N개로 제한
VOL_SURGE_RATIO = 1.5

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


# ----- 영업일 결정 -----

def get_target_date() -> str:
    """삼성전자 OHLCV가 존재하는 가장 최근 영업일."""
    today = datetime.now()
    end = today
    start = end - timedelta(days=15)
    df = fdr.DataReader("005930", start, end)
    if df.empty:
        raise RuntimeError("최근 15일 내 영업일을 찾을 수 없습니다.")
    return df.index[-1].strftime("%Y%m%d")


# ----- 종목 리스트 + 시총/거래량 (FDR) -----

def load_kospi_listing() -> pd.DataFrame:
    print("[1/5] 코스피 종목 리스트 로딩 (FDR)...")
    df = fdr.StockListing("KOSPI")
    df = df[["Code", "Name", "Close", "Marcap", "Volume"]].copy()
    df = df.rename(columns={"Marcap": "시가총액", "Volume": "거래량", "Close": "종가", "Name": "종목명"})
    df["시총_억"] = (df["시가총액"] / 100_000_000).round(0).astype("Int64")
    df = df[df["시가총액"].notna() & (df["시가총액"] > 0)]
    df["Code"] = df["Code"].astype(str).str.zfill(6)
    return df


# ----- 네이버 시가총액 페이지 스크래핑: PER, ROE -----

def fetch_naver_marketcap_page(page: int) -> list[dict]:
    url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok=0&page={page}"
    r = requests.get(url, headers=UA, timeout=10)
    r.encoding = "euc-kr"
    soup = BeautifulSoup(r.text, "lxml")
    out = []
    for tr in soup.select("table.type_2 tr"):
        a = tr.select_one("a.tltle")
        if not a:
            continue
        m = re.search(r"code=(\d{6})", a.get("href", ""))
        if not m:
            continue
        code = m.group(1)
        cells = [td.get_text(strip=True) for td in tr.select("td")]
        # cells: 0=순위, 1=종목명, 2=현재가, 3=전일비, 4=등락률, 5=액면가,
        #        6=시가총액, 7=상장주식수, 8=외국인비율, 9=거래량, 10=PER, 11=ROE
        def num(s):
            s = s.replace(",", "").replace("%", "")
            if s in ("", "N/A", "-"):
                return None
            try:
                return float(s)
            except ValueError:
                return None
        per = num(cells[10]) if len(cells) > 10 else None
        roe = num(cells[11]) if len(cells) > 11 else None
        out.append({"Code": code, "PER": per, "ROE": roe})
    return out


def load_per_roe(max_pages: int = 25) -> pd.DataFrame:
    print(f"[2/5] 네이버 시가총액 페이지에서 PER/ROE 로딩 (최대 {max_pages}p)...")
    rows = []
    for page in range(1, max_pages + 1):
        try:
            page_rows = fetch_naver_marketcap_page(page)
        except Exception as e:
            print(f"  → page {page} 오류: {e}")
            continue
        if not page_rows:
            break
        rows.extend(page_rows)
        time.sleep(0.15)
    df = pd.DataFrame(rows).drop_duplicates(subset=["Code"])
    print(f"  → 총 {len(df)}개 종목 수집")
    return df


# ----- 네이버 배당 페이지 스크래핑: 배당수익률 -----

def fetch_naver_dividend_page(page: int) -> list[dict]:
    url = f"https://finance.naver.com/sise/dividend_list.naver?pageIndex={page}"
    r = requests.get(url, headers=UA, timeout=10)
    r.encoding = "euc-kr"
    soup = BeautifulSoup(r.text, "lxml")
    out = []
    # 배당 테이블에는 <a href="/item/main.naver?code=XXXXXX">종목명</a> 형태
    for tr in soup.select("table tr"):
        a = tr.select_one("a")
        if not a:
            continue
        href = a.get("href", "")
        m = re.search(r"code=(\d{6})", href)
        if not m:
            continue
        code = m.group(1)
        cells = [td.get_text(strip=True) for td in tr.select("td")]
        # cells: 종목명, 현재가, 기준월, 배당금, 배당수익률, 배당성향, ROE, PER, ...
        if len(cells) < 5:
            continue
        try:
            div = float(cells[4].replace(",", "").replace("%", ""))
        except ValueError:
            continue
        try:
            dps = float(cells[3].replace(",", ""))
        except ValueError:
            dps = None
        out.append({"Code": code, "DIV": div, "DPS": dps})
    return out


def load_dividend(max_pages: int = 20) -> pd.DataFrame:
    print(f"[3/5] 네이버 배당 페이지에서 배당수익률 로딩 (최대 {max_pages}p)...")
    rows = []
    for page in range(1, max_pages + 1):
        try:
            page_rows = fetch_naver_dividend_page(page)
        except Exception as e:
            print(f"  → page {page} 오류: {e}")
            continue
        if not page_rows:
            break
        rows.extend(page_rows)
        time.sleep(0.15)
    df = pd.DataFrame(rows).drop_duplicates(subset=["Code"])
    print(f"  → 총 {len(df)}개 종목 수집")
    return df


# ----- 펀더멘털 통합 -----

def build_universe() -> pd.DataFrame:
    listing = load_kospi_listing()
    per_roe = load_per_roe()
    div = load_dividend()
    df = listing.merge(per_roe, on="Code", how="left").merge(div, on="Code", how="left")
    df = df.set_index("Code")
    return df


# ----- 카테고리별 스크리너 -----

def screen_value(df: pd.DataFrame) -> pd.DataFrame:
    """A. 저평가 가치주: 저PER + 고ROE."""
    f = df[
        df["PER"].notna() & df["ROE"].notna()
        & (df["PER"] > 0) & (df["PER"] < 30)
        & (df["ROE"] > 5)
        & (df["시총_억"] >= MIN_MARKET_CAP_BIL)
    ].copy()
    f["PER_pct"] = f["PER"].rank(pct=True)            # 낮을수록 좋음
    f["ROE_pct"] = f["ROE"].rank(pct=True, ascending=False)  # 높을수록 좋음 → 낮은 pct
    f["점수"] = (f["PER_pct"] + f["ROE_pct"]).round(3)
    f = f.sort_values("점수").head(TOP_N)
    return f[["종목명", "PER", "ROE", "종가", "시총_억", "점수"]]


def screen_dividend(df: pd.DataFrame) -> pd.DataFrame:
    """B. 고배당주."""
    f = df[
        df["DIV"].notna()
        & (df["DIV"] > 0)
        & (df["시총_억"] >= MIN_MARKET_CAP_BIL)
    ].copy()
    f = f.sort_values("DIV", ascending=False).head(TOP_N)
    return f[["종목명", "DIV", "DPS", "PER", "ROE", "종가", "시총_억"]]


def screen_bluechip(df: pd.DataFrame) -> pd.DataFrame:
    """C. 대형 우량주: 시총 상위 + 거래량 양수 + PER 양수."""
    f = df[
        (df["거래량"] > 0)
        & (df["PER"].fillna(-1) > 0)
    ].copy()
    f = f.sort_values("시총_억", ascending=False).head(TOP_N)
    return f[["종목명", "시총_억", "종가", "거래량", "PER", "ROE", "DIV"]]


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
    """FinanceDataReader로 OHLCV 조회. 컬럼명을 한글로 정규화."""
    end_dt = datetime.strptime(end_date, "%Y%m%d")
    start = end_dt - timedelta(days=lookback_days)
    df = fdr.DataReader(ticker, start, end_dt)
    return df.rename(columns={"Close": "종가", "Volume": "거래량"})


def screen_technical(df: pd.DataFrame, date: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """D(모멘텀) + E(과매도)를 한 번의 OHLCV 조회로 동시 계산."""
    universe = df.sort_values("시총_억", ascending=False).head(TECH_UNIVERSE_SIZE)
    print(f"  → 기술적 지표 계산 대상: {len(universe)}개 (OHLCV 1회 조회 후 D, E 동시 산출)")

    momentum_rows = []
    oversold_rows = []

    for i, code in enumerate(universe.index):
        try:
            ohlcv = fetch_ohlcv(code, date, 90)
            if len(ohlcv) < 25:
                continue
            close = ohlcv["종가"]
            volume = ohlcv["거래량"]

            # D: 모멘텀
            ma5 = close.rolling(5).mean()
            ma20 = close.rolling(20).mean()
            crossed = (ma5 > ma20) & (ma5.shift(1) <= ma20.shift(1))
            if crossed.tail(5).any():
                avg_vol_20 = volume.tail(21).head(20).mean()
                today_vol = volume.iloc[-1]
                if avg_vol_20 > 0:
                    vol_ratio = today_vol / avg_vol_20
                    if vol_ratio >= VOL_SURGE_RATIO:
                        momentum_rows.append({
                            "Code": code,
                            "종목명": universe.loc[code, "종목명"],
                            "종가": int(close.iloc[-1]),
                            "MA5": round(float(ma5.iloc[-1]), 2),
                            "MA20": round(float(ma20.iloc[-1]), 2),
                            "거래량배수": round(float(vol_ratio), 2),
                            "시총_억": int(universe.loc[code, "시총_억"]),
                        })

            # E: 과매도 반등
            rsi = calculate_rsi(close, 14)
            if rsi is not None and rsi < 30:
                oversold_rows.append({
                    "Code": code,
                    "종목명": universe.loc[code, "종목명"],
                    "종가": int(close.iloc[-1]),
                    "RSI14": round(rsi, 2),
                    "PER": universe.loc[code, "PER"],
                    "ROE": universe.loc[code, "ROE"],
                    "시총_억": int(universe.loc[code, "시총_억"]),
                })
        except Exception:
            continue
        if (i + 1) % 25 == 0:
            print(f"  → {i+1}/{len(universe)} 처리됨")

    mom = pd.DataFrame(momentum_rows).set_index("Code").sort_values("거래량배수", ascending=False).head(TOP_N) if momentum_rows else pd.DataFrame()
    over = pd.DataFrame(oversold_rows).set_index("Code").sort_values("RSI14").head(TOP_N) if oversold_rows else pd.DataFrame()
    return mom, over


# ----- 출력 -----

def format_table(df: pd.DataFrame, title: str) -> str:
    if df.empty:
        return f"\n{'=' * 90}\n{title}\n{'=' * 90}\n(조건 충족 종목 없음)\n"
    return f"\n{'=' * 90}\n{title}\n{'=' * 90}\n{df.to_string()}\n"


def main():
    date = get_target_date()
    print(f"기준일: {date}\n")

    df = build_universe()
    print(f"통합 코스피 종목: {len(df)}개\n")

    out_dir = Path("docs") / date
    out_dir.mkdir(parents=True, exist_ok=True)

    titles = {
        "A_가치주": "[A] 저평가 가치주 (저PER + 고ROE)",
        "B_배당주": "[B] 고배당주 (배당수익률 상위)",
        "C_우량주": "[C] 대형 우량주 (시총 상위)",
        "D_모멘텀": "[D] 모멘텀 (최근 5일 내 골든크로스 + 거래량 급증)",
        "E_과매도": "[E] 과매도 반등 (RSI14 < 30)",
    }

    print("[A] 저평가 가치주 스크리닝...")
    a = screen_value(df)
    print("[B] 고배당주 스크리닝...")
    b = screen_dividend(df)
    print("[C] 대형 우량주 스크리닝...")
    c = screen_bluechip(df)
    print(f"[4/5+5/5] [D]+[E] 기술적 스크리닝 (시총 상위 {TECH_UNIVERSE_SIZE}종목 OHLCV 조회)...")
    d, e = screen_technical(df, date)

    categories = {"A_가치주": a, "B_배당주": b, "C_우량주": c, "D_모멘텀": d, "E_과매도": e}

    summary_lines = [
        "KOSPI 카테고리별 스크리닝 결과",
        f"기준일: {date}",
        f"실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"통합 종목 수: {len(df)}개",
        "",
        "데이터 소스: FinanceDataReader(시총/거래량/OHLCV) + Naver Finance(PER/ROE/DIV)",
        "※ 본 결과는 단순 조건 필터링이며 투자 추천이 아닙니다.",
    ]

    for key, result in categories.items():
        csv_path = out_dir / f"{key}.csv"
        result.to_csv(csv_path, encoding="utf-8-sig")
        table = format_table(result, titles[key])
        print(table)
        summary_lines.append(table)

    summary_path = out_dir / "summary.txt"
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")

    print(f"\n저장 위치: {out_dir.resolve()}")
    print("- 카테고리별 CSV 5개 (A_가치주.csv ~ E_과매도.csv)")
    print("- summary.txt (통합 콘솔 출력)")


if __name__ == "__main__":
    main()
