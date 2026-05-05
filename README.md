# KOSPI 카테고리별 스크리너

코스피 종목을 6개 카테고리로 매일 자동 스크리닝하고, 섹터별로 분류하며, 웹 대시보드와 백테스팅까지 제공하는 도구.

> 본 결과는 단순 조건 필터링/가상 시뮬레이션이며 **투자 추천이 아닙니다.** 매수/매도 결정은 본인의 추가 분석과 책임 하에 진행하세요.

## 카테고리

| 코드 | 카테고리 | 의미 |
|---|---|---|
| A | 저평가 가치주 | PER 낮고 ROE 높은 종목 (펀더멘털 대비 저평가) |
| B | 고배당주 | 배당수익률 상위 (배당 중심 안정 수익) |
| C | 대형 우량주 | 시가총액 상위 (변동성 낮고 안정적) |
| D | 모멘텀 | 최근 5일 내 골든크로스 + 거래량 급증 |
| E | 과매도 반등 | RSI(14) < 30 (단기 낙폭 후 반등 기대) |
| F | 단기 관심 후보 | 1~4주 보유 가정. 5일 상승 + 거래량 활발 + RSI 정상 |

각 카테고리당 상위 10개 종목을 추출하며, ◎/○/△ 등급과 섹터 정보가 함께 표시됨.

## 데이터 소스

- **[FinanceDataReader](https://github.com/financedata-org/FinanceDataReader)**: 코스피 종목 리스트, 시가총액, 거래량, 개별 OHLCV
- **네이버 금융 시가총액 페이지**: PER, ROE
- **네이버 금융 배당 페이지**: 배당수익률(DIV), 주당배당금(DPS)
- **네이버 금융 업종 페이지**: 섹터(업종) 매핑

## 프로젝트 구조

```
stock/
├── kospi_screener.py        ← 스크리닝 메인 진입점
├── backtest_runner.py       ← 백테스팅 실행 진입점
├── app.py                   ← Streamlit 웹 대시보드
├── requirements.txt
├── README.md
├── .gitignore
├── src/                     ← 기능별 모듈
│   ├── config.py            (상수)
│   ├── data_loader.py       (FDR + Naver 펀더멘털/배당)
│   ├── sectors.py           (네이버 업종 매핑)
│   ├── indicators.py        (RSI, OHLCV)
│   ├── grading.py           (◎/○/△ 평가)
│   ├── screeners.py         (A~F 카테고리 함수)
│   ├── output.py            (CSV/summary 저장)
│   └── backtest.py          (백테스팅 시뮬레이션)
└── docs/                    ← 결과 (gitignore로 추적 제외)
    └── YYYYMMDD/
        ├── A_가치주.csv ~ F_단기관심.csv
        ├── Z_섹터요약.csv
        ├── backtest_summary.csv
        ├── backtest_D.csv / E.csv / F.csv
        └── summary.txt
```

## 설치

Python 3.10 이상 필요.

```powershell
pip install -r requirements.txt
```

## 사용법

### 1) 매일 스크리닝

```powershell
python kospi_screener.py
```

- 자동으로 직전 영업일 기준 `docs/YYYYMMDD/` 폴더 생성
- 6개 카테고리 CSV + 섹터 요약 + summary.txt 저장
- 첫 실행 약 4~6분 (시총 상위 200종목 OHLCV + 섹터 80여 개)

### 2) 웹 대시보드 (Streamlit)

```powershell
streamlit run app.py
```

- 브라우저에서 자동으로 `http://localhost:8501` 열림
- 4개 페이지:
  - **카테고리 결과**: 6개 카테고리 탭, 섹터 필터 드롭다운, Plotly 차트, CSV 다운로드
  - **섹터 분석**: 섹터별 시총 비중 파이차트, 평균 PER 막대, PER vs ROE 버블
  - **종목 상세 차트**: 캔들차트 + 이동평균선(MA5/20/60) + 거래량 + RSI(14) + 최근 수익률
  - **백테스팅 결과**: 카테고리별 평균 수익률/승률, 거래내역, 수익률 분포 히스토그램

### 3) 백테스팅

```powershell
python backtest_runner.py
```

- 시총 상위 100종목, 지난 6개월, 매주 신호 체크 → 5일 보유 후 매도 시뮬레이션
- D/E/F 카테고리(기술적)에 대해 가상 거래 내역 + 통계 산출
- 결과 파일: `backtest_summary.csv`, `backtest_D.csv`, `backtest_E.csv`, `backtest_F.csv`
- 약 3~5분 소요

> 펀더멘털 카테고리(A/B/C)는 시점별 PER/ROE/DIV 데이터가 필요하여 백테스팅 대상에서 제외.

## 주요 지표 요약

| 지표 | 의미 | 좋은 값 |
|---|---|---|
| PER | 주가 / 1주당 순이익 | 낮을수록 저평가 (5 이하 매우 저평가) |
| ROE | 자기자본이익률 | 높을수록 좋음 (15% 이상 우수) |
| DIV | 배당수익률 | 5% 이상 고배당 |
| RSI(14) | 0~100 가격 모멘텀 지표 | 30 미만 과매도, 70 이상 과매수 |
| 거래량배수 | 당일 거래량 / 20일 평균 | 2배 이상이면 관심 급증 |
| 골든크로스 | MA5가 MA20을 위로 돌파 | 단기 상승 신호 |

## 매개변수 (소스 상단)

`src/config.py`:

| 변수 | 기본값 | 의미 |
|---|---|---|
| `TOP_N` | 10 | 카테고리당 추출 종목 수 |
| `MIN_MARKET_CAP_BIL` | 1000 | 시총 1000억원 미만 컷 (소형주 노이즈 방지) |
| `TECH_UNIVERSE_SIZE` | 200 | 기술적 지표(D/E/F) 계산 대상 — 시총 상위 N개 |
| `VOL_SURGE_RATIO` | 1.5 | 거래량 급증 기준 (20일 평균 대비) |

`backtest_runner.py`:

| 변수 | 기본값 | 의미 |
|---|---|---|
| `BACKTEST_DAYS` | 180 | 백테스팅 기간 (영업일 기준 약 6개월) |
| `HOLDING_DAYS` | 5 | 신호 발생 후 보유 영업일 (1주) |
| `REBALANCE_DAYS` | 5 | 신호 체크 주기 (1주) |
| `UNIVERSE_SIZE` | 100 | 백테스팅 대상 — 시총 상위 N개 |

## 라이선스 / 면책

본 코드는 학습/개인 활용 목적으로 작성되었으며, **투자 자문이나 매매 추천이 아닙니다.** 사용으로 인한 손실에 대해 어떠한 책임도 지지 않습니다.
