"""네이버 금융 경제 뉴스 헤드라인 스크래핑."""

import re

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.config import UA


def fetch_economic_headlines(max_items: int = 30) -> pd.DataFrame:
    """네이버 금융 메인 뉴스 페이지에서 헤드라인 수집.

    Returns:
        DataFrame with columns: 제목, URL, 출처, 시각
    """
    url = "https://finance.naver.com/news/mainnews.naver"
    rows = []
    try:
        r = requests.get(url, headers=UA, timeout=10)
        r.encoding = "euc-kr"
        soup = BeautifulSoup(r.text, "lxml")

        for li in soup.select("ul.newsList li"):
            a = li.select_one("a")
            if not a:
                continue
            href = a.get("href", "")
            title = a.get_text(strip=True)
            if not title or not href:
                continue
            if not href.startswith("http"):
                href = "https://finance.naver.com" + href

            # 출처(언론사) + 시각
            press_el = li.select_one(".press") or li.select_one(".info") or li.select_one(".date")
            press = press_el.get_text(" ", strip=True) if press_el else ""

            # 요약(간단)
            summary_el = li.select_one(".articleSummary") or li.select_one("p")
            summary = summary_el.get_text(strip=True) if summary_el else ""

            rows.append({"제목": title, "URL": href, "요약": summary[:140], "출처": press})
    except Exception as e:
        return pd.DataFrame([{"제목": f"네이버 뉴스 로딩 실패: {e}", "URL": "", "요약": "", "출처": ""}])

    df = pd.DataFrame(rows).drop_duplicates(subset=["제목"]).head(max_items)
    return df


def fetch_market_news(max_items: int = 20) -> pd.DataFrame:
    """네이버 금융 - 증시 뉴스 헤드라인."""
    url = "https://finance.naver.com/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=258"
    rows = []
    try:
        r = requests.get(url, headers=UA, timeout=10)
        r.encoding = "euc-kr"
        soup = BeautifulSoup(r.text, "lxml")
        for dd in soup.select("dl.newsList dd, .articleSubject"):
            a = dd.select_one("a") if dd.name != "a" else dd
            if not a:
                continue
            title = a.get_text(strip=True)
            href = a.get("href", "")
            if not title or not href:
                continue
            if not href.startswith("http"):
                href = "https://finance.naver.com" + href
            rows.append({"제목": title, "URL": href})
    except Exception:
        pass

    df = pd.DataFrame(rows).drop_duplicates(subset=["제목"]).head(max_items)
    return df
