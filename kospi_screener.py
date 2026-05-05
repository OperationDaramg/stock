"""KOSPI 카테고리별 스크리닝 도구.

6개 카테고리로 코스피 종목을 필터링하여 docs/YYYYMMDD/ 폴더에 결과를 저장한다.
- A: 저평가 가치주 (저PER + 고ROE)
- B: 고배당주 (배당수익률 상위)
- C: 대형 우량주 (시총 상위)
- D: 모멘텀 (5일 내 골든크로스 + 거래량 급증)
- E: 과매도 반등 (RSI14 < 30)
- F: 단기 관심 후보 (1~4주 보유 가정, 모멘텀+거래량+RSI 정상)

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
TECH_UNIVERSE_SIZE = 200  # 기술적 지표 계산은 시총 상위 N개로 제한
VOL_SURGE_RATIO = 1.5

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


# ===== 영업일 결정 =====

def get_target_date() -> str:
    """삼성전자 OHLCV가 존재하는 가장 최근 영업일."""
    today = datetime.now()
    df = fdr.DataReader("005930", today - timedelta(days=15), today)
    if df.empty:
        raise RuntimeError("최근 15일 내 영업일을 찾을 수 없습니다.")
    return df.index[-1].strftime("%Y%m%d")


# ===== 종목 리스트 + 시총/거래량 (FDR) =====

def load_kospi_listing() -> pd.DataFrame:
    print("[1/5] 코스피 종목 리스트 로딩 (FDR)...")
    df = fdr.StockListing("KOSPI")
    df = df[["Code", "Name", "Close", "Marcap", "Volume"]].copy()
    df = df.rename(columns={"Marcap": "시가총액", "Volume": "거래량", "Close": "종가", "Name": "종목명"})
    df["시총_억"] = (df["시가총액"] / 100_000_000).round(0).astype("Int64")
    df = df[df["시가총액"].notna() & (df["시가총액"] > 0)]
    df["Code"] = df["Code"].astype(str).str.zfill(6)
    return df


# ===== 네이버 시가총액 페이지: PER, ROE =====

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


# ===== 네이버 배당 페이지: 배당수익률 =====

def fetch_naver_dividend_page(page: int) -> list[dict]:
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


def build_universe() -> pd.DataFrame:
    listing = load_kospi_listing()
    per_roe = load_per_roe()
    div = load_dividend()
    df = listing.merge(per_roe, on="Code", how="left").merge(div, on="Code", how="left")
    df = df.set_index("Code")
    return df


# ===== 평가 등급 헬퍼 =====

def grade_value(score: float) -> str:
    """A 카테고리 점수(낮을수록 좋음) → 등급."""
    if score < 0.15:
        return "◎ 매우 저평가"
    if score < 0.30:
        return "○ 저평가"
    return "△ 양호"


def grade_div(div: float) -> str:
    """B 배당수익률 → 등급."""
    if div >= 8:
        return f"◎ 초고배당({div:.1f}%)"
    if div >= 5:
        return f"○ 고배당({div:.1f}%)"
    return f"△ 일반({div:.1f}%)"


def grade_bluechip(rank: int) -> str:
    """C 시총 순위 → 등급."""
    if rank <= 3:
        return f"◎ 대장주(#{rank})"
    if rank <= 7:
        return f"○ 우량주(#{rank})"
    return f"△ 중대형(#{rank})"


def grade_momentum(vol_ratio: float) -> str:
    """D 거래량 배수 → 등급."""
    if vol_ratio >= 3:
        return f"◎ 강한신호(거래량 {vol_ratio:.1f}배)"
    if vol_ratio >= 2:
        return f"○ 양호(거래량 {vol_ratio:.1f}배)"
    return f"△ 보통(거래량 {vol_ratio:.1f}배)"


def grade_oversold(rsi: float) -> str:
    """E RSI → 등급."""
    if rsi < 20:
        return f"◎ 극과매도(RSI {rsi:.0f})"
    if rsi < 25:
        return f"○ 과매도(RSI {rsi:.0f})"
    return f"△ 약과매도(RSI {rsi:.0f})"


def grade_short_term(score: float) -> str:
    """F 단기 점수 → 등급."""
    if score >= 12:
        return "◎ 강세"
    if score >= 8:
        return "○ 양호"
    return "△ 보통"


# ===== A, B, C 스크리너 =====

def screen_value(df: pd.DataFrame) -> pd.DataFrame:
    """A. 저평가 가치주: 저PER + 고ROE."""
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
    return f[["종목명", "PER", "ROE", "종가", "시총_억", "점수", "평가"]]


def screen_dividend(df: pd.DataFrame) -> pd.DataFrame:
    """B. 고배당주."""
    f = df[
        df["DIV"].notna() & (df["DIV"] > 0)
        & (df["시총_억"] >= MIN_MARKET_CAP_BIL)
    ].copy()
    f = f.sort_values("DIV", ascending=False).head(TOP_N)
    f["평가"] = f["DIV"].apply(grade_div)
    return f[["종목명", "DIV", "DPS", "PER", "ROE", "종가", "시총_억", "평가"]]


def screen_bluechip(df: pd.DataFrame) -> pd.DataFrame:
    """C. 대형 우량주: 시총 상위 + PER 양수."""
    f = df[(df["거래량"] > 0) & (df["PER"].fillna(-1) > 0)].copy()
    f = f.sort_values("시총_억", ascending=False).head(TOP_N)
    f["평가"] = [grade_bluechip(i + 1) for i in range(len(f))]
    return f[["종목명", "시총_억", "종가", "거래량", "PER", "ROE", "DIV", "평가"]]


# ===== D, E, F 통합 (OHLCV 1회 조회) =====

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
    end_dt = datetime.strptime(end_date, "%Y%m%d")
    start = end_dt - timedelta(days=lookback_days)
    df = fdr.DataReader(ticker, start, end_dt)
    return df.rename(columns={"Close": "종가", "Volume": "거래량"})


def screen_technical(df: pd.DataFrame, date: str):
    """D(모멘텀) + E(과매도) + F(단기 관심)를 한 번의 OHLCV 조회로 동시 계산."""
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
            mcap = int(universe.loc[code, "시총_억"])
            per = universe.loc[code, "PER"]
            roe = universe.loc[code, "ROE"]
            cur = int(close.iloc[-1])

            # 공통 계산
            ma5 = close.rolling(5).mean()
            ma20 = close.rolling(20).mean()
            avg_vol_20 = volume.tail(21).head(20).mean()
            today_vol = volume.iloc[-1]
            vol_ratio = today_vol / avg_vol_20 if avg_vol_20 > 0 else 0
            rsi = calculate_rsi(close, 14)
            ret_5d = (close.iloc[-1] / close.iloc[-6] - 1) * 100 if len(close) >= 6 else None
            ret_20d = (close.iloc[-1] / close.iloc[-21] - 1) * 100 if len(close) >= 21 else None

            # D: 모멘텀
            crossed = (ma5 > ma20) & (ma5.shift(1) <= ma20.shift(1))
            if crossed.tail(5).any() and vol_ratio >= VOL_SURGE_RATIO:
                momentum_rows.append({
                    "Code": code, "종목명": name, "종가": cur,
                    "MA5": round(float(ma5.iloc[-1]), 2),
                    "MA20": round(float(ma20.iloc[-1]), 2),
                    "거래량배수": round(float(vol_ratio), 2),
                    "5일수익률(%)": round(ret_5d, 2) if ret_5d is not None else None,
                    "시총_억": mcap,
                })

            # E: 과매도
            if rsi is not None and rsi < 30:
                oversold_rows.append({
                    "Code": code, "종목명": name, "종가": cur,
                    "RSI14": round(rsi, 2),
                    "5일수익률(%)": round(ret_5d, 2) if ret_5d is not None else None,
                    "PER": per, "ROE": roe, "시총_억": mcap,
                })

            # F: 단기 관심 후보
            if (
                ret_5d is not None and ret_5d >= 3
                and ret_20d is not None and ret_20d >= -10
                and vol_ratio >= 1.5
                and rsi is not None and 30 <= rsi <= 70
                and not pd.isna(per) and per > 0
            ):
                score = ret_5d + vol_ratio
                short_term_rows.append({
                    "Code": code, "종목명": name, "종가": cur,
                    "5일수익률(%)": round(ret_5d, 2),
                    "20일수익률(%)": round(ret_20d, 2),
                    "거래량배수": round(float(vol_ratio), 2),
                    "RSI14": round(rsi, 1),
                    "PER": per, "점수": round(score, 2),
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


# ===== 출력 텍스트 =====

GUIDE_TEXT = """
📖 주요 지표 가이드 (간단 요약)
- PER (주가수익비율): 주가 / 1주당 순이익. 낮을수록 저평가. 보통 10~15, 5 이하 매우 저평가
- ROE (자기자본이익률): 회사가 자기 돈으로 얼마나 벌었나. 높을수록 좋음. 15% 이상 우수
- DIV (배당수익률): 연간 배당금 / 주가. 5% 이상 고배당주
- 시총_억: 시가총액(억원). 1조원 = 10,000억
- MA5 / MA20: 최근 5일 / 20일 평균 주가
- 골든크로스: 단기 평균(MA5)이 장기 평균(MA20)을 위로 돌파 → 상승 신호
- RSI(14): 0~100. 30 미만=과매도(반등 가능), 70 이상=과매수(하락 가능), 30~70=정상
- 거래량배수: 당일 거래량 / 20일 평균 거래량. 2배 이상이면 관심 급증

🎯 카테고리별 의미 (한 줄 설명)
- [A] 저평가 가치주: PER 낮고 ROE 높은 → 펀더멘털 대비 싸고 수익성 좋은 종목
- [B] 고배당주: 배당수익률 상위 → 배당으로 안정적 수익 추구
- [C] 대형 우량주: 시총 상위 → 변동성 낮고 안정적
- [D] 모멘텀: 골든크로스 + 거래량 급증 → 단기 상승 추세 진입
- [E] 과매도 반등: RSI 30 미만 → 단기 낙폭 후 기술적 반등 기대
- [F] 단기 관심 후보: 1~4주 보유 가정. 5일 상승 + 거래량 활발 + RSI 정상

⚠️ 평가 등급 표시
- ◎ : 해당 카테고리 기준에서 매우 강한 신호
- ○ : 양호한 신호
- △ : 기준은 만족하지만 신호는 보통

❗ 본 결과는 단순 조건 필터링이며 투자 추천이 아닙니다.
   매수/매도 결정은 본인의 추가 분석과 책임 하에 진행하세요.
""".strip()


def format_table(df: pd.DataFrame, title: str, subtitle: str = "") -> str:
    header = f"\n{'=' * 100}\n{title}"
    if subtitle:
        header += f"\n  ↳ {subtitle}"
    header += f"\n{'=' * 100}\n"
    if df.empty:
        return header + "(조건 충족 종목 없음)\n"
    return header + df.to_string() + "\n"


# ===== 메인 =====

def main():
    date = get_target_date()
    print(f"기준일: {date}\n")

    df = build_universe()
    print(f"통합 코스피 종목: {len(df)}개\n")

    out_dir = Path("docs") / date
    out_dir.mkdir(parents=True, exist_ok=True)

    titles = {
        "A_가치주": ("[A] 저평가 가치주", "PER 낮고 ROE 높은 종목 (펀더멘털 대비 저평가)"),
        "B_배당주": ("[B] 고배당주", "배당수익률 상위 (배당 중심 안정 수익)"),
        "C_우량주": ("[C] 대형 우량주", "시가총액 상위 (변동성 낮고 안정적)"),
        "D_모멘텀": ("[D] 모멘텀", "최근 5일 내 골든크로스 + 거래량 급증 (상승 추세 진입)"),
        "E_과매도": ("[E] 과매도 반등", "RSI14 < 30 (단기 낙폭 후 반등 기대)"),
        "F_단기관심": ("[F] 단기 관심 후보 ⭐", "1~4주 보유 가정. 5일 상승 + 거래량 + RSI 정상 종목"),
    }

    print("[A] 저평가 가치주 스크리닝...")
    a = screen_value(df)
    print("[B] 고배당주 스크리닝...")
    b = screen_dividend(df)
    print("[C] 대형 우량주 스크리닝...")
    c = screen_bluechip(df)
    print(f"[D]+[E]+[F] 기술적 스크리닝 (시총 상위 {TECH_UNIVERSE_SIZE}종목 OHLCV 조회)...")
    d, e, f = screen_technical(df, date)

    categories = {
        "A_가치주": a, "B_배당주": b, "C_우량주": c,
        "D_모멘텀": d, "E_과매도": e, "F_단기관심": f,
    }

    summary_lines = [
        "=" * 100,
        "  KOSPI 카테고리별 스크리닝 결과",
        "=" * 100,
        f"  기준일: {date}",
        f"  실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"  통합 종목 수: {len(df)}개",
        f"  데이터 소스: FinanceDataReader + Naver Finance",
        "",
        GUIDE_TEXT,
    ]

    for key, result in categories.items():
        csv_path = out_dir / f"{key}.csv"
        result.to_csv(csv_path, encoding="utf-8-sig")
        title, subtitle = titles[key]
        table = format_table(result, title, subtitle)
        print(table)
        summary_lines.append(table)

    summary_path = out_dir / "summary.txt"
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")

    print(f"\n저장 위치: {out_dir.resolve()}")
    print("- 카테고리별 CSV 6개 (A_가치주.csv ~ F_단기관심.csv)")
    print("- summary.txt (지표 가이드 + 6개 카테고리 통합)")


if __name__ == "__main__":
    main()
