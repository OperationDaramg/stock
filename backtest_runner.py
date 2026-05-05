"""백테스팅 실행 진입점.

실행:
    python backtest_runner.py

결과:
    docs/YYYYMMDD/backtest_summary.csv (카테고리별 통계)
    docs/YYYYMMDD/backtest_D.csv / backtest_E.csv / backtest_F.csv (개별 거래내역)

사전 조건:
    kospi_screener.py를 먼저 실행하여 종목 리스트가 만들어져 있어야 함
    (없으면 자동으로 다시 빌드).
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
sys.stderr.reconfigure(encoding="utf-8")

from src.backtest import run_backtest, summarize
from src.config import TECH_UNIVERSE_SIZE
from src.data_loader import build_universe, get_target_date


# 백테스팅 설정 (가벼운 디폴트, 필요시 조정)
BACKTEST_DAYS = 180  # 약 6개월(영업일)
HOLDING_DAYS = 5  # 보유 영업일 (1주)
REBALANCE_DAYS = 5  # 신호 체크 주기 (1주)
UNIVERSE_SIZE = 100  # 시총 상위 N개 (백테스팅 시간 단축)


def main() -> None:
    date = get_target_date()
    print(f"기준일: {date}\n")

    df = build_universe()
    universe = df.sort_values("시총_억", ascending=False).head(UNIVERSE_SIZE)
    codes = list(universe.index)
    code_to_name = universe["종목명"].to_dict()
    print(f"백테스팅 대상: 시총 상위 {len(codes)}종목\n")

    trades = run_backtest(
        codes, code_to_name, date,
        backtest_days=BACKTEST_DAYS,
        holding_days=HOLDING_DAYS,
        rebalance_days=REBALANCE_DAYS,
    )

    summary = summarize(trades, HOLDING_DAYS)

    out_dir = Path("docs") / date
    out_dir.mkdir(parents=True, exist_ok=True)

    summary.to_csv(out_dir / "backtest_summary.csv", index=False, encoding="utf-8-sig")
    for cat, df_cat in trades.items():
        df_cat.to_csv(out_dir / f"backtest_{cat}.csv", index=False, encoding="utf-8-sig")

    print("\n=== 백테스팅 요약 ===")
    print(summary.to_string(index=False))
    print(f"\n저장 위치: {out_dir.resolve()}")
    print("- backtest_summary.csv (카테고리별 통계)")
    print("- backtest_D.csv / backtest_E.csv / backtest_F.csv (개별 거래내역)")
    print("\n※ 백테스팅 결과는 과거 가상 시뮬레이션이며 미래 수익을 보장하지 않습니다.")


if __name__ == "__main__":
    main()
