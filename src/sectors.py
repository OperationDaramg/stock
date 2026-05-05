"""네이버 금융 업종 페이지에서 섹터(업종) 매핑 수집.

각 종목코드 → 섹터명 매핑을 만든다. 매일 매번 새로 받기보다는 캐시 활용 권장하나,
단순화를 위해 매 실행마다 가져온다(약 30초 소요).
"""

import re
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.config import UA


def _list_sectors() -> list[tuple[str, str]]:
    """(섹터명, 섹터번호) 리스트."""
    url = "https://finance.naver.com/sise/sise_group.naver?type=upjong"
    r = requests.get(url, headers=UA, timeout=10)
    r.encoding = "euc-kr"
    soup = BeautifulSoup(r.text, "lxml")
    sectors = []
    for a in soup.select("a[href*='no=']"):
        href = a.get("href", "")
        m = re.search(r"no=(\d+)", href)
        name = a.get_text(strip=True)
        if m and name and "type=upjong" in href:
            sectors.append((name, m.group(1)))
    # 중복 제거 (순서 유지)
    return list(dict.fromkeys(sectors))


def _fetch_sector_stocks(no: str) -> list[str]:
    """특정 섹터 번호의 종목코드 리스트."""
    url = f"https://finance.naver.com/sise/sise_group_detail.naver?type=upjong&no={no}"
    r = requests.get(url, headers=UA, timeout=10)
    r.encoding = "euc-kr"
    soup = BeautifulSoup(r.text, "lxml")
    codes = []
    for a in soup.select("a[href*='/item/main.naver']"):
        m = re.search(r"code=(\d{6})", a.get("href", ""))
        if m:
            codes.append(m.group(1))
    return list(dict.fromkeys(codes))


def load_sector_map() -> pd.DataFrame:
    """전체 섹터-종목 매핑을 DataFrame으로 반환.

    Returns:
        DataFrame with index=Code, columns=['섹터'].
        한 종목이 여러 섹터에 속할 수 있어 첫 매칭 섹터를 채택.
    """
    print("[섹터] 네이버 업종 목록 로딩...")
    sectors = _list_sectors()
    print(f"  → 업종 {len(sectors)}개 발견")

    rows = []
    for i, (name, no) in enumerate(sectors):
        try:
            codes = _fetch_sector_stocks(no)
            for code in codes:
                rows.append({"Code": code, "섹터": name})
        except Exception:
            continue
        time.sleep(0.1)
        if (i + 1) % 20 == 0:
            print(f"  → {i+1}/{len(sectors)} 처리됨")

    df = pd.DataFrame(rows).drop_duplicates(subset=["Code"], keep="first").set_index("Code")
    print(f"  → 종목-섹터 매핑 {len(df)}개 완성")
    return df


def attach_sector(df: pd.DataFrame, sector_map: pd.DataFrame) -> pd.DataFrame:
    """기존 종목 DataFrame에 '섹터' 컬럼 부착. 미매칭은 '기타'."""
    out = df.copy()
    out["섹터"] = out.index.map(sector_map["섹터"]).fillna("기타")
    return out


def sector_summary(df: pd.DataFrame) -> pd.DataFrame:
    """섹터별 통계: 종목 수, 평균 PER, 평균 ROE, 평균 DIV, 시총 합계."""
    grp = df.groupby("섹터").agg(
        종목수=("종목명", "count"),
        평균PER=("PER", "mean"),
        평균ROE=("ROE", "mean"),
        평균DIV=("DIV", "mean"),
        시총합_억=("시총_억", "sum"),
    )
    grp = grp.sort_values("시총합_억", ascending=False)
    grp["평균PER"] = grp["평균PER"].round(2)
    grp["평균ROE"] = grp["평균ROE"].round(2)
    grp["평균DIV"] = grp["평균DIV"].round(2)
    grp["시총합_억"] = grp["시총합_억"].astype("Int64")
    return grp
