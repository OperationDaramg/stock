"""전역 설정."""

TOP_N = 10  # 카테고리당 추출 종목 수
MIN_MARKET_CAP_BIL = 1000  # 시총 1000억(억 단위) 미만 컷
TECH_UNIVERSE_SIZE = 200  # 기술적 지표 계산 대상: 시총 상위 N개
VOL_SURGE_RATIO = 1.5  # 거래량 급증 기준 (20일 평균 대비)

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
