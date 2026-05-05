"""결과 CSV/Markdown/Summary 출력."""

from pathlib import Path

import pandas as pd


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


CATEGORY_TITLES = {
    "A_가치주": ("[A] 저평가 가치주", "PER 낮고 ROE 높은 종목 (펀더멘털 대비 저평가)"),
    "B_배당주": ("[B] 고배당주", "배당수익률 상위 (배당 중심 안정 수익)"),
    "C_우량주": ("[C] 대형 우량주", "시가총액 상위 (변동성 낮고 안정적)"),
    "D_모멘텀": ("[D] 모멘텀", "최근 5일 내 골든크로스 + 거래량 급증 (상승 추세 진입)"),
    "E_과매도": ("[E] 과매도 반등", "RSI14 < 30 (단기 낙폭 후 반등 기대)"),
    "F_단기관심": ("[F] 단기 관심 후보 ⭐", "1~4주 보유 가정. 5일 상승 + 거래량 + RSI 정상 종목"),
}


def format_table(df: pd.DataFrame, title: str, subtitle: str = "") -> str:
    header = f"\n{'=' * 100}\n{title}"
    if subtitle:
        header += f"\n  ↳ {subtitle}"
    header += f"\n{'=' * 100}\n"
    if df.empty:
        return header + "(조건 충족 종목 없음)\n"
    return header + df.to_string() + "\n"


def save_results(
    out_dir: Path,
    date: str,
    universe_size: int,
    categories: dict,
    sector_summary_df: pd.DataFrame,
) -> None:
    """카테고리별 CSV + 섹터 요약 + summary.txt 저장."""
    out_dir.mkdir(parents=True, exist_ok=True)
    from datetime import datetime as _dt

    summary_lines = [
        "=" * 100,
        "  KOSPI 카테고리별 스크리닝 결과",
        "=" * 100,
        f"  기준일: {date}",
        f"  실행 시각: {_dt.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"  통합 종목 수: {universe_size}개",
        f"  데이터 소스: FinanceDataReader + Naver Finance",
        "",
        GUIDE_TEXT,
    ]

    for key, result in categories.items():
        csv_path = out_dir / f"{key}.csv"
        result.to_csv(csv_path, encoding="utf-8-sig")
        title, subtitle = CATEGORY_TITLES[key]
        table = format_table(result, title, subtitle)
        print(table)
        summary_lines.append(table)

    # 섹터 요약 저장
    sector_csv = out_dir / "Z_섹터요약.csv"
    sector_summary_df.to_csv(sector_csv, encoding="utf-8-sig")
    sector_table = format_table(
        sector_summary_df.head(20),
        "[Z] 섹터 요약 (상위 20개, 시총 합계 기준)",
        "각 섹터별 종목 수와 평균 지표",
    )
    print(sector_table)
    summary_lines.append(sector_table)

    summary_path = out_dir / "summary.txt"
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")
    print(f"\n저장 위치: {out_dir.resolve()}")
    print("- 카테고리별 CSV 6개 (A_가치주.csv ~ F_단기관심.csv)")
    print("- Z_섹터요약.csv (전체 섹터 통계)")
    print("- summary.txt (지표 가이드 + 6개 카테고리 + 섹터 요약)")
