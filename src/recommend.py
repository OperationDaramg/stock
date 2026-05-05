"""시장 분위기 기반 통합 종목 후보 (cross-category recommendations).

각 카테고리의 종목을 카테고리 내 백분위로 정규화한 뒤,
시장 분위기에 따른 카테고리 적합도 가중치를 곱해 종합 점수를 산출.
모든 카테고리를 합쳐 상위 N개를 반환한다.

종합점수 = 카테고리 내 순위 백분위(1.0 ~ 0.0) × 시장 적합도 가중치
"""

from pathlib import Path

import pandas as pd

from src.macro import category_market_fit


CATEGORIES = {
    "A_가치주": "💎 저평가 가치주",
    "B_배당주": "💰 고배당주",
    "C_우량주": "🏛️ 대형 우량주",
    "D_모멘텀": "🚀 모멘텀",
    "E_과매도": "📉 과매도 반등",
    "F_단기관심": "⭐ 단기 관심",
}

# 시장 적합도 배지 첫 글자 → 가중치
FIT_WEIGHT = {"◎": 1.5, "○": 1.0, "△": 0.6, "⚠": 0.2}


def _load_csv(docs_dir: Path, date: str, key: str) -> pd.DataFrame:
    f = docs_dir / date / f"{key}.csv"
    if not f.exists():
        return pd.DataFrame()
    df = pd.read_csv(f, dtype={"Code": str})
    if "Code" in df.columns:
        df["Code"] = df["Code"].str.zfill(6)
        df = df.set_index("Code")
    return df


def cross_category_recommendations(
    docs_dir: Path,
    date: str,
    market_score: int,
    top_n: int = 15,
) -> pd.DataFrame:
    """모든 카테고리 통합 + 시장 분위기 가중치 반영 종합 후보."""
    rows = []
    for cat_key, cat_title in CATEGORIES.items():
        df = _load_csv(docs_dir, date, cat_key)
        if df.empty:
            continue

        fit_badge, fit_reason = category_market_fit(market_score, cat_key)
        sym = fit_badge[0] if fit_badge else "○"
        cat_weight = FIT_WEIGHT.get(sym, 1.0)

        n = len(df)
        for i, (code, row) in enumerate(df.iterrows()):
            cat_pct = 1.0 - (i / max(n - 1, 1))  # 0번 = 1.0(최상), 마지막 = 0.0
            adj_score = cat_pct * cat_weight
            rows.append({
                "Code": code,
                "종목명": row.get("종목명", "—"),
                "섹터": row.get("섹터", "—"),
                "카테고리": cat_title,
                "카테고리적합도": fit_badge,
                "종목평가": row.get("평가", "—"),
                "카테고리순위": f"{i+1}/{n}",
                "종합점수": round(adj_score, 3),
                "_적합도이유": fit_reason,
            })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    # 같은 종목이 여러 카테고리에 등장 시 최고 점수만 유지
    df = df.sort_values("종합점수", ascending=False)
    df = df.drop_duplicates(subset=["Code"], keep="first")
    return df.head(top_n).reset_index(drop=True)
