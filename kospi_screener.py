"""KOSPI 카테고리별 스크리너 — 메인 진입점.

기능별 모듈은 src/ 패키지에 분리되어 있다:
- src.data_loader: 종목 리스트 + 펀더멘털 + 배당
- src.sectors: 섹터(업종) 매핑
- src.indicators: RSI, OHLCV
- src.grading: 평가 등급 (◎/○/△)
- src.screeners: 6개 카테고리 스크리너 (A~F)
- src.output: CSV/summary 저장
- src.config: 전역 설정

본 결과는 단순 조건 필터링이며 투자 추천이 아니다.
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
sys.stderr.reconfigure(encoding="utf-8")

from src.data_loader import build_universe, get_target_date
from src.output import save_results
from src.screeners import screen_bluechip, screen_dividend, screen_technical, screen_value
from src.sectors import attach_sector, load_sector_map, sector_summary


def main() -> None:
    date = get_target_date()
    print(f"기준일: {date}\n")

    # 1) 종목 + 펀더멘털 + 배당
    df = build_universe()

    # 2) 섹터 매핑 부착
    print("[4/4] 섹터 매핑 로딩...")
    sector_map = load_sector_map()
    df = attach_sector(df, sector_map)
    print(f"통합 코스피 종목: {len(df)}개\n")

    # 3) 카테고리별 스크리닝
    print("[A] 저평가 가치주 스크리닝...")
    a = screen_value(df)
    print("[B] 고배당주 스크리닝...")
    b = screen_dividend(df)
    print("[C] 대형 우량주 스크리닝...")
    c = screen_bluechip(df)
    print("[D]+[E]+[F] 기술적 스크리닝 (시총 상위 200종목 OHLCV 1회 조회)...")
    d, e, f = screen_technical(df, date)

    categories = {
        "A_가치주": a, "B_배당주": b, "C_우량주": c,
        "D_모멘텀": d, "E_과매도": e, "F_단기관심": f,
    }

    # 4) 섹터 요약
    sector_df = sector_summary(df)

    # 5) 저장
    out_dir = Path("docs") / date
    save_results(out_dir, date, len(df), categories, sector_df)


if __name__ == "__main__":
    main()
