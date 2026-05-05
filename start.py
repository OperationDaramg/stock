"""KOSPI 스크리너 통합 런처.

한 번 실행으로:
  1. 최근 영업일 데이터가 없으면 kospi_screener.py 자동 실행
  2. Streamlit 대시보드 시작 (브라우저 자동 오픈)
  3. 코드/데이터 변경 시 자동 reload (.streamlit/config.toml의 runOnSave)

실행:
    python start.py

옵션:
    python start.py --skip-screen   # 데이터가 없어도 스크리너를 건너뜀
    python start.py --refresh       # 데이터가 있어도 스크리너를 다시 실행
    python start.py --backtest      # 백테스팅도 함께 실행
"""

import argparse
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).parent
DOCS = ROOT / "docs"


def has_recent_data(max_days: int = 7) -> bool:
    if not DOCS.exists():
        return False
    today = datetime.now()
    for i in range(max_days):
        d = (today - timedelta(days=i)).strftime("%Y%m%d")
        if (DOCS / d / "summary.txt").exists():
            return True
    return False


def run_step(args: list[str], label: str) -> int:
    print(f"\n{'=' * 60}\n▶ {label}\n{'=' * 60}")
    proc = subprocess.run([sys.executable, *args], cwd=ROOT)
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="KOSPI 스크리너 런처")
    parser.add_argument("--skip-screen", action="store_true", help="스크리너 실행 건너뛰기")
    parser.add_argument("--refresh", action="store_true", help="데이터가 있어도 스크리너 재실행")
    parser.add_argument("--backtest", action="store_true", help="백테스팅도 함께 실행")
    cli_args = parser.parse_args()

    need_screen = not cli_args.skip_screen and (cli_args.refresh or not has_recent_data())

    if need_screen:
        print("📊 최근 데이터를 갱신합니다 (약 4~6분 소요)...")
        rc = run_step(["kospi_screener.py"], "스크리너 실행")
        if rc != 0:
            print(f"❌ 스크리너 실패 (exit {rc}). 그래도 대시보드를 시작합니다...")
    else:
        print("✅ 최근 데이터 발견, 스크리너 실행 건너뜀.")

    if cli_args.backtest:
        rc = run_step(["backtest_runner.py"], "백테스팅 실행")
        if rc != 0:
            print(f"❌ 백테스팅 실패 (exit {rc}). 그래도 대시보드를 시작합니다...")

    # Streamlit 시작 — config.toml의 headless=false 덕분에 브라우저 자동 오픈
    print("\n" + "=" * 60)
    print("🚀 웹 대시보드를 시작합니다 — 브라우저가 자동으로 열립니다")
    print("=" * 60)
    print("(중지하려면 Ctrl+C)\n")

    try:
        # 로컬 실행 전용 옵션: 브라우저 자동 오픈 + 코드 변경 자동 reload
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.port", "8501",
            "--server.headless=false",
            "--server.runOnSave=true",
        ], cwd=ROOT)
    except KeyboardInterrupt:
        print("\n👋 대시보드를 종료합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
