"""종목 리스트 + 펀더멘털 + 배당 데이터 통합 로딩."""

import re
import time
from datetime import datetime, timedelta

import FinanceDataReader as fdr
import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.config import UA


def get_target_date() -> str:
    """삼성전자 OHLCV가 존재하는 가장 최근 영업일."""
    today = datetime.now()
    df = fdr.DataReader("005930", today - timedelta(days=15), today)
    if df.empty:
        raise RuntimeError("최근 15일 내 영업일을 찾을 수 없습니다.")
    return df.index[-1].strftime("%Y%m%d")


# ----- FDR: 코스피 종목 리스트 -----

def load_kospi_listing() -> pd.DataFrame:
    print("[1/4] 코스피 종목 리스트 로딩 (FDR)...")
    df = fdr.StockListing("KOSPI")
    df = df[["Code", "Name", "Close", "Marcap", "Volume"]].copy()
    df = df.rename(columns={"Marcap": "시가총액", "Volume": "거래량", "Close": "종가", "Name": "종목명"})
    df["시총_억"] = (df["시가총액"] / 100_000_000).round(0).astype("Int64")
    df = df[df["시가총액"].notna() & (df["시가총액"] > 0)]
    df["Code"] = df["Code"].astype(str).str.zfill(6)
    return df


# ----- 네이버 시가총액 페이지: PER, ROE -----

def _parse_naver_marketcap_page(page: int) -> list[dict]:
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
    print(f"[2/4] 네이버 시가총액 페이지에서 PER/ROE 로딩 (최대 {max_pages}p)...")
    rows = []
    for page in range(1, max_pages + 1):
        try:
            page_rows = _parse_naver_marketcap_page(page)
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


# ----- 네이버 배당 페이지: DIV, DPS -----

def _parse_naver_dividend_page(page: int) -> list[dict]:
    url = f"https://finance.naver.com/sise/dividend_list.naver?pageIndex={page}"
    r = requests.get(url, headers=UA, timeout=10)
    r.encoding = "euc-kr"
    soup = BeautifulSoup(r.text, "lxml")
    out = []
    for tr in soup.select("table tr"):
        a = tr.select_one("a")
        if not a:
            continue
        m = re.search(r"code=(\d{6})", a.get("href", ""))
        if not m:
            continue
        code = m.group(1)
        cells = [td.get_text(strip=True) for td in tr.select("td")]
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
    print(f"[3/4] 네이버 배당 페이지에서 배당수익률 로딩 (최대 {max_pages}p)...")
    rows = []
    for page in range(1, max_pages + 1):
        try:
            page_rows = _parse_naver_dividend_page(page)
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


# ----- 통합 -----

def build_universe() -> pd.DataFrame:
    """종목 리스트 + PER/ROE + 배당을 하나로 합친 DataFrame.

    인덱스: Code (6자리). 컬럼: 종목명, 시가총액, 시총_억, 종가, 거래량, PER, ROE, DIV, DPS
    섹터는 sectors.attach_sector()로 별도 부착.
    """
    listing = load_kospi_listing()
    per_roe = load_per_roe()
    div = load_dividend()
    df = listing.merge(per_roe, on="Code", how="left").merge(div, on="Code", how="left")
    df = df.set_index("Code")
    return df
