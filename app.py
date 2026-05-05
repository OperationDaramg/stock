"""KOSPI 스크리너 Streamlit 웹 대시보드.

실행:
    streamlit run app.py

사전 조건: kospi_screener.py를 먼저 실행하여 docs/YYYYMMDD/ 폴더에 결과가 있어야 함.
"""

from datetime import datetime, timedelta
from pathlib import Path

import FinanceDataReader as fdr
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(page_title="KOSPI 스크리너", page_icon="📈", layout="wide")

DOCS_DIR = Path(__file__).parent / "docs"

CATEGORY_FILES = {
    "A_가치주": "[A] 저평가 가치주",
    "B_배당주": "[B] 고배당주",
    "C_우량주": "[C] 대형 우량주",
    "D_모멘텀": "[D] 모멘텀",
    "E_과매도": "[E] 과매도 반등",
    "F_단기관심": "[F] 단기 관심 후보 ⭐",
}


# ===== 데이터 로딩 =====

@st.cache_data(ttl=60)
def list_dates() -> list[str]:
    if not DOCS_DIR.exists():
        return []
    return sorted([p.name for p in DOCS_DIR.iterdir() if p.is_dir()], reverse=True)


@st.cache_data(ttl=60)
def load_csv(date: str, key: str) -> pd.DataFrame:
    f = DOCS_DIR / date / f"{key}.csv"
    if not f.exists():
        return pd.DataFrame()
    df = pd.read_csv(f, dtype={"Code": str})
    if "Code" in df.columns:
        df["Code"] = df["Code"].str.zfill(6)
        df = df.set_index("Code")
    return df


@st.cache_data(ttl=300)
def load_ohlcv(code: str, days: int) -> pd.DataFrame:
    end = datetime.now()
    start = end - timedelta(days=days)
    return fdr.DataReader(code, start, end)


# ===== 차트 =====

def render_category_chart(key: str, df: pd.DataFrame) -> None:
    if df.empty:
        return
    df = df.reset_index()

    if key == "A_가치주":
        fig = px.scatter(
            df, x="PER", y="ROE", text="종목명",
            color="섹터" if "섹터" in df.columns else None,
            size="시총_억", hover_data=["점수", "평가"],
            title="PER vs ROE 분포 (낮은 PER + 높은 ROE = 저평가 가치주)",
        )
        fig.update_traces(textposition="top center")
        st.plotly_chart(fig, use_container_width=True)
    elif key == "B_배당주":
        fig = px.bar(
            df, x="종목명", y="DIV",
            color="섹터" if "섹터" in df.columns else None,
            hover_data=["DPS", "PER", "ROE"],
            title="배당수익률(%)",
        )
        st.plotly_chart(fig, use_container_width=True)
    elif key == "C_우량주":
        fig = px.bar(
            df, x="종목명", y="시총_억",
            color="섹터" if "섹터" in df.columns else None,
            hover_data=["PER", "ROE"],
            title="시가총액(억원) — 코스피 대장주",
        )
        st.plotly_chart(fig, use_container_width=True)
    elif key == "D_모멘텀":
        fig = px.bar(
            df, x="종목명", y="거래량배수",
            color="섹터" if "섹터" in df.columns else None,
            hover_data=["MA5", "MA20", "5일수익률(%)"],
            title="거래량 배수 (당일 거래량 / 20일 평균)",
        )
        fig.add_hline(y=1.5, line_dash="dash", annotation_text="기준선 1.5")
        st.plotly_chart(fig, use_container_width=True)
    elif key == "E_과매도":
        fig = px.bar(
            df, x="종목명", y="RSI14",
            color="섹터" if "섹터" in df.columns else None,
            hover_data=["PER", "ROE", "5일수익률(%)"],
            title="RSI(14) — 30 미만 과매도",
        )
        fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="과매도 기준선 30")
        st.plotly_chart(fig, use_container_width=True)
    elif key == "F_단기관심":
        fig = px.scatter(
            df, x="5일수익률(%)", y="거래량배수",
            text="종목명", size="점수",
            color="섹터" if "섹터" in df.columns else None,
            hover_data=["RSI14", "PER", "20일수익률(%)"],
            title="단기 관심 후보 — 5일 수익률 vs 거래량 배수",
        )
        fig.update_traces(textposition="top center")
        st.plotly_chart(fig, use_container_width=True)


# ===== 페이지: 카테고리 결과 =====

def page_categories(date: str) -> None:
    st.header(f"📊 카테고리 결과 — 기준일 {date}")

    tabs = st.tabs(list(CATEGORY_FILES.values()))
    for tab, (key, title) in zip(tabs, CATEGORY_FILES.items()):
        with tab:
            df = load_csv(date, key)
            if df.empty:
                st.info("조건 충족 종목 없음")
                continue

            # 섹터 필터
            if "섹터" in df.columns:
                sectors = ["전체"] + sorted(df["섹터"].dropna().unique().tolist())
                sel = st.selectbox(f"섹터 필터", sectors, key=f"sec_{key}")
                if sel != "전체":
                    df = df[df["섹터"] == sel]

            st.dataframe(df, use_container_width=True, height=400)

            col_a, col_b = st.columns([1, 4])
            with col_a:
                st.download_button(
                    label="📥 CSV 다운로드",
                    data=df.to_csv().encode("utf-8-sig"),
                    file_name=f"{key}.csv",
                    mime="text/csv",
                    key=f"dl_{key}",
                )

            render_category_chart(key, df)


# ===== 페이지: 섹터 분석 =====

def page_sectors(date: str) -> None:
    st.header(f"🏭 섹터 분석 — {date}")
    df = load_csv(date, "Z_섹터요약")
    if df.empty:
        st.info("섹터 요약 데이터 없음")
        return
    df = df.reset_index()

    col1, col2 = st.columns(2)
    with col1:
        top10 = df.head(10)
        fig = px.pie(top10, values="시총합_억", names="섹터", title="섹터별 시총 비중 (Top 10)")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        top15 = df.head(15)
        fig = px.bar(top15, x="섹터", y="평균PER", title="섹터별 평균 PER (Top 15 시총)")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("섹터별 평균 PER vs ROE (버블 크기 = 시총합)")
    df_chart = df[df["평균PER"].between(0, 80) & df["평균ROE"].between(-30, 80)]
    fig2 = px.scatter(
        df_chart, x="평균PER", y="평균ROE", size="시총합_억", text="섹터",
        hover_data=["종목수", "평균DIV"],
    )
    fig2.update_traces(textposition="top center")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("전체 섹터 데이터")
    st.dataframe(df, use_container_width=True, height=500)


# ===== 페이지: 종목 상세 차트 =====

def page_stock_detail(date: str) -> None:
    st.header("🔍 종목 상세 차트")

    # 모든 카테고리 종목 통합 (선택지)
    all_codes: dict[str, str] = {}
    for key in CATEGORY_FILES.keys():
        df = load_csv(date, key)
        if not df.empty and "종목명" in df.columns:
            for code, row in df.iterrows():
                all_codes[code] = row["종목명"]

    if not all_codes:
        st.info("선택할 종목이 없습니다.")
        return

    options = [f"{name} ({code})" for code, name in all_codes.items()]
    sel = st.selectbox("종목 선택 (스크리닝에 포함된 종목)", options)
    code = sel.rsplit("(", 1)[-1].rstrip(")")
    name = all_codes[code]

    days = st.slider("조회 기간 (일)", 30, 730, 180, step=30)

    try:
        df = load_ohlcv(code, days)
    except Exception as e:
        st.error(f"OHLCV 조회 실패: {e}")
        return

    if df.empty:
        st.info("OHLCV 데이터 없음")
        return

    df["MA5"] = df["Close"].rolling(5).mean()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA60"] = df["Close"].rolling(60).mean()

    # 캔들 + 이평선
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        name="일봉",
    ))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA5"], name="MA5", line=dict(width=1, color="orange")))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA20"], name="MA20", line=dict(width=1, color="purple")))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA60"], name="MA60", line=dict(width=1, color="gray")))
    fig.update_layout(
        title=f"{name} ({code}) — 캔들차트 + 이동평균",
        xaxis_rangeslider_visible=False, height=500,
    )
    st.plotly_chart(fig, use_container_width=True)

    # 거래량
    fig_v = go.Figure(go.Bar(x=df.index, y=df["Volume"], name="거래량"))
    fig_v.update_layout(title="거래량", height=200)
    st.plotly_chart(fig_v, use_container_width=True)

    # RSI
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - 100 / (1 + rs)
    fig_r = go.Figure(go.Scatter(x=df.index, y=rsi, name="RSI(14)"))
    fig_r.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="과매수 70")
    fig_r.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="과매도 30")
    fig_r.update_layout(title="RSI(14)", height=250, yaxis_range=[0, 100])
    st.plotly_chart(fig_r, use_container_width=True)

    # 최근 등락 통계
    if len(df) >= 21:
        st.subheader("📊 최근 통계")
        m1, m2, m3, m4 = st.columns(4)
        cur = df["Close"].iloc[-1]
        m1.metric("종가", f"{cur:,.0f} 원")
        m2.metric("5일 수익률", f"{(cur / df['Close'].iloc[-6] - 1) * 100:+.2f}%")
        m3.metric("20일 수익률", f"{(cur / df['Close'].iloc[-21] - 1) * 100:+.2f}%")
        m4.metric("RSI(14)", f"{rsi.iloc[-1]:.1f}")


# ===== 메인 =====

def main() -> None:
    st.title("📈 KOSPI 카테고리별 스크리너")

    dates = list_dates()
    if not dates:
        st.error(
            "docs 폴더에 결과 데이터가 없습니다. "
            "터미널에서 `python kospi_screener.py`를 먼저 실행하세요."
        )
        return

    with st.sidebar:
        st.header("⚙️ 설정")
        selected_date = st.selectbox("기준일 선택", dates)
        page = st.radio("📑 페이지", [
            "카테고리 결과",
            "섹터 분석",
            "종목 상세 차트",
        ])

        st.markdown("---")
        st.markdown("""
### 📖 지표 가이드
- **PER**: 주가/순이익. 낮을수록 저평가
- **ROE**: 자기자본이익률. 15% 이상 우수
- **DIV**: 배당수익률. 5% 이상 고배당
- **RSI(14)**: 30 미만 과매도, 70 이상 과매수
- **거래량배수**: 평소 대비 거래량
- **골든크로스**: MA5↑MA20 상향 돌파

### ⚠️ 주의
본 결과는 단순 조건 필터링이며 **투자 추천이 아닙니다**. 매매 결정은 본인 책임 하에 진행하세요.
""")

    if page == "카테고리 결과":
        page_categories(selected_date)
    elif page == "섹터 분석":
        page_sectors(selected_date)
    else:
        page_stock_detail(selected_date)


if __name__ == "__main__":
    main()
