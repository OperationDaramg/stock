"""KOSPI 스크리너 — 다크 모던 대시보드 (Streamlit).

실행:
    python start.py    (권장 — 데이터 자동 갱신 + 브라우저 자동 오픈)
    또는
    streamlit run app.py
"""

from datetime import datetime, timedelta
from pathlib import Path

import FinanceDataReader as fdr
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(
    page_title="KOSPI 스크리너",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

DOCS_DIR = Path(__file__).parent / "docs"

CATEGORY_FILES = {
    "A_가치주": "💎 저평가 가치주",
    "B_배당주": "💰 고배당주",
    "C_우량주": "🏛️ 대형 우량주",
    "D_모멘텀": "🚀 모멘텀",
    "E_과매도": "📉 과매도 반등",
    "F_단기관심": "⭐ 단기 관심 후보",
}


# ===== 커스텀 CSS (aion2tool 스타일 — 다크 + 보라/시안) =====

CUSTOM_CSS = """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');

html, body, [class*="css"], .stMarkdown, button, input, select, textarea {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif !important;
}

/* 전체 배경 */
.stApp {
    background:
      radial-gradient(circle at 20% -10%, rgba(168, 85, 247, 0.15) 0%, transparent 40%),
      radial-gradient(circle at 80% 110%, rgba(6, 182, 212, 0.10) 0%, transparent 40%),
      #0E0F1A;
}

/* 메인 컨텐츠 패딩 */
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 1400px;
}

/* 헤더 - 그라데이션 텍스트 */
h1 {
    background: linear-gradient(90deg, #A855F7 0%, #06B6D4 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: 800 !important;
    letter-spacing: -0.02em;
}

h2, h3 {
    color: #F3F4F6 !important;
    font-weight: 700 !important;
    letter-spacing: -0.01em;
}

/* 사이드바 */
[data-testid="stSidebar"] {
    background: #0A0B14 !important;
    border-right: 1px solid rgba(168, 85, 247, 0.15);
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #A855F7 !important;
    -webkit-text-fill-color: #A855F7 !important;
    background: none !important;
}

/* 메트릭 카드 (st.metric) */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, rgba(168, 85, 247, 0.08) 0%, rgba(26, 27, 46, 0.6) 100%);
    border: 1px solid rgba(168, 85, 247, 0.25);
    border-radius: 14px;
    padding: 16px 20px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 32px rgba(168, 85, 247, 0.25);
}
[data-testid="stMetricLabel"] {
    color: #9CA3AF !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
}
[data-testid="stMetricValue"] {
    color: #F3F4F6 !important;
    font-weight: 700 !important;
    font-size: 1.6rem !important;
}

/* 데이터프레임 */
[data-testid="stDataFrame"] {
    border-radius: 12px;
    border: 1px solid rgba(168, 85, 247, 0.15);
    overflow: hidden;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
}

/* 탭 */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    background: rgba(26, 27, 46, 0.4);
    padding: 6px;
    border-radius: 12px;
    border: 1px solid rgba(168, 85, 247, 0.15);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    padding: 8px 16px;
    color: #9CA3AF;
    font-weight: 500;
    transition: all 0.2s ease;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #E5E7EB;
    background: rgba(168, 85, 247, 0.08);
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(90deg, #A855F7 0%, #7C3AED 100%) !important;
    color: white !important;
    box-shadow: 0 4px 12px rgba(168, 85, 247, 0.4);
}

/* 셀렉트박스 */
[data-baseweb="select"] {
    background: rgba(26, 27, 46, 0.6) !important;
    border-radius: 10px !important;
}

/* 버튼 */
.stButton > button, .stDownloadButton > button {
    background: linear-gradient(90deg, #A855F7 0%, #7C3AED 100%);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 8px 18px;
    font-weight: 600;
    transition: all 0.2s ease;
    box-shadow: 0 4px 12px rgba(168, 85, 247, 0.25);
}
.stButton > button:hover, .stDownloadButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 8px 20px rgba(168, 85, 247, 0.4);
}

/* radio 버튼 */
.stRadio > div {
    background: rgba(26, 27, 46, 0.4);
    padding: 8px;
    border-radius: 10px;
    border: 1px solid rgba(168, 85, 247, 0.15);
}
.stRadio label {
    color: #E5E7EB !important;
}

/* 정보/경고 박스 */
.stAlert {
    background: rgba(26, 27, 46, 0.6) !important;
    border-left: 3px solid #A855F7 !important;
    border-radius: 10px !important;
}

/* 슬라이더 */
.stSlider [data-baseweb="slider"] [role="slider"] {
    background: #A855F7 !important;
    border-color: #A855F7 !important;
}

/* 캡션 */
.stCaption, [data-testid="stCaptionContainer"] {
    color: #6B7280 !important;
}

/* 구분선 */
hr {
    border-color: rgba(168, 85, 247, 0.15) !important;
    margin: 1.5rem 0 !important;
}

/* 카드 컨테이너 (커스텀) */
.kpi-grid { display: grid; gap: 12px; }
.section-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 1.5rem 0 1rem;
    padding: 12px 16px;
    background: linear-gradient(90deg, rgba(168, 85, 247, 0.10) 0%, transparent 100%);
    border-left: 3px solid #A855F7;
    border-radius: 6px;
}
.section-header h2 { margin: 0 !important; font-size: 1.3rem !important; }

/* 종목 칩 */
.stock-chip {
    display: inline-block;
    padding: 4px 10px;
    margin: 2px;
    background: rgba(168, 85, 247, 0.12);
    border: 1px solid rgba(168, 85, 247, 0.3);
    border-radius: 16px;
    color: #E5E7EB;
    font-size: 0.85rem;
}
</style>
"""

# Plotly 다크 템플릿
PLOTLY_TEMPLATE = "plotly_dark"
ACCENT_COLOR = "#A855F7"
ACCENT_COLOR_2 = "#06B6D4"


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


# ===== 컴포넌트 =====

def section_header(title: str, icon: str = "📊") -> None:
    st.markdown(
        f'<div class="section-header"><span style="font-size:1.4rem">{icon}</span>'
        f'<h2>{title}</h2></div>',
        unsafe_allow_html=True,
    )


def render_kpi_dashboard(date: str) -> None:
    """상단 KPI 카드 — 모든 페이지 공통."""
    dfs = {k: load_csv(date, k) for k in CATEGORY_FILES}
    sectors = load_csv(date, "Z_섹터요약")

    total_uni = sum(len(d) for d in dfs.values() if not d.empty)
    f_count = len(dfs.get("F_단기관심", pd.DataFrame()))
    sector_count = len(sectors) if not sectors.empty else 0

    a = dfs.get("A_가치주", pd.DataFrame())
    avg_per = a["PER"].mean() if not a.empty and "PER" in a.columns else None
    avg_roe = a["ROE"].mean() if not a.empty and "ROE" in a.columns else None

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📅 기준일", date)
    c2.metric("⭐ 단기 후보", f"{f_count}종목")
    c3.metric("🏭 섹터 수", f"{sector_count}개")
    c4.metric(
        "💎 가치주 평균 PER",
        f"{avg_per:.1f}" if avg_per is not None and not pd.isna(avg_per) else "—",
    )
    c5.metric(
        "📊 가치주 평균 ROE",
        f"{avg_roe:.1f}%" if avg_roe is not None and not pd.isna(avg_roe) else "—",
    )


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
            template=PLOTLY_TEMPLATE,
            title="<b>PER vs ROE 분포</b>  <span style='color:#9CA3AF'>(좌하단=저PER+고ROE 가치주)</span>",
        )
        fig.update_traces(textposition="top center")
    elif key == "B_배당주":
        fig = px.bar(
            df, x="종목명", y="DIV",
            color="섹터" if "섹터" in df.columns else None,
            hover_data=["DPS", "PER", "ROE"],
            template=PLOTLY_TEMPLATE,
            title="<b>배당수익률 (%)</b>",
        )
    elif key == "C_우량주":
        fig = px.bar(
            df, x="종목명", y="시총_억",
            color="섹터" if "섹터" in df.columns else None,
            hover_data=["PER", "ROE"],
            template=PLOTLY_TEMPLATE,
            title="<b>시가총액 (억원)</b>",
        )
    elif key == "D_모멘텀":
        fig = px.bar(
            df, x="종목명", y="거래량배수",
            color="섹터" if "섹터" in df.columns else None,
            hover_data=["MA5", "MA20", "5일수익률(%)"],
            template=PLOTLY_TEMPLATE,
            title="<b>거래량 배수</b>  <span style='color:#9CA3AF'>(당일/20일평균)</span>",
        )
        fig.add_hline(y=1.5, line_dash="dash", line_color=ACCENT_COLOR_2,
                      annotation_text="기준선 1.5", annotation_font_color=ACCENT_COLOR_2)
    elif key == "E_과매도":
        fig = px.bar(
            df, x="종목명", y="RSI14",
            color="섹터" if "섹터" in df.columns else None,
            hover_data=["PER", "ROE", "5일수익률(%)"],
            template=PLOTLY_TEMPLATE,
            title="<b>RSI(14)</b>  <span style='color:#9CA3AF'>(30 미만=과매도)</span>",
        )
        fig.add_hline(y=30, line_dash="dash", line_color="#10B981",
                      annotation_text="과매도 기준 30", annotation_font_color="#10B981")
    elif key == "F_단기관심":
        fig = px.scatter(
            df, x="5일수익률(%)", y="거래량배수",
            text="종목명", size="점수",
            color="섹터" if "섹터" in df.columns else None,
            hover_data=["RSI14", "PER", "20일수익률(%)"],
            template=PLOTLY_TEMPLATE,
            title="<b>단기 관심 후보</b>  <span style='color:#9CA3AF'>(우상=강세)</span>",
        )
        fig.update_traces(textposition="top center")

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#E5E7EB",
        height=480,
        margin=dict(l=10, r=10, t=60, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)


# ===== 페이지: 카테고리 결과 =====

def page_categories(date: str) -> None:
    section_header(f"카테고리 결과", "📊")

    tabs = st.tabs(list(CATEGORY_FILES.values()))
    for tab, (key, title) in zip(tabs, CATEGORY_FILES.items()):
        with tab:
            df = load_csv(date, key)
            if df.empty:
                st.info("조건 충족 종목 없음")
                continue

            col_filter, col_dl = st.columns([3, 1])
            with col_filter:
                if "섹터" in df.columns:
                    sectors_list = ["전체"] + sorted(df["섹터"].dropna().unique().tolist())
                    sel = st.selectbox("🏭 섹터 필터", sectors_list, key=f"sec_{key}")
                    if sel != "전체":
                        df = df[df["섹터"] == sel]
            with col_dl:
                st.markdown("<br>", unsafe_allow_html=True)
                st.download_button(
                    "📥 CSV 다운로드",
                    data=df.to_csv().encode("utf-8-sig"),
                    file_name=f"{key}_{date}.csv",
                    mime="text/csv",
                    key=f"dl_{key}",
                    use_container_width=True,
                )

            st.dataframe(df, use_container_width=True, height=400)
            render_category_chart(key, df)


# ===== 페이지: 섹터 분석 =====

def page_sectors(date: str) -> None:
    section_header("섹터 분석", "🏭")
    df = load_csv(date, "Z_섹터요약")
    if df.empty:
        st.info("섹터 요약 데이터 없음")
        return
    df = df.reset_index()

    col1, col2 = st.columns(2)
    with col1:
        top10 = df.head(10)
        fig = px.pie(
            top10, values="시총합_억", names="섹터",
            title="<b>섹터별 시총 비중 (Top 10)</b>",
            template=PLOTLY_TEMPLATE, hole=0.45,
            color_discrete_sequence=px.colors.sequential.Plasma_r,
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#E5E7EB", height=420, margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        top15 = df.head(15)
        fig = px.bar(
            top15, x="섹터", y="평균PER",
            title="<b>섹터별 평균 PER (Top 15 시총)</b>",
            template=PLOTLY_TEMPLATE,
            color="평균PER", color_continuous_scale="Plasma_r",
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#E5E7EB", height=420, margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("섹터별 평균 PER vs ROE")
    df_chart = df[df["평균PER"].between(0, 80) & df["평균ROE"].between(-30, 80)]
    fig2 = px.scatter(
        df_chart, x="평균PER", y="평균ROE", size="시총합_억", text="섹터",
        hover_data=["종목수", "평균DIV"],
        template=PLOTLY_TEMPLATE,
        color="평균ROE", color_continuous_scale="Plasma",
    )
    fig2.update_traces(textposition="top center")
    fig2.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_color="#E5E7EB", height=500, margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("전체 섹터 데이터")
    st.dataframe(df, use_container_width=True, height=500)


# ===== 페이지: 종목 상세 차트 =====

def page_stock_detail(date: str) -> None:
    section_header("종목 상세 차트", "🔍")

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
    col_a, col_b = st.columns([3, 1])
    with col_a:
        sel = st.selectbox("📌 종목 선택 (스크리닝에 포함된 종목)", options)
    with col_b:
        days = st.slider("기간 (일)", 30, 730, 180, step=30)

    code = sel.rsplit("(", 1)[-1].rstrip(")")
    name = all_codes[code]

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

    # 최근 통계 (상단 메트릭)
    if len(df) >= 21:
        cur = float(df["Close"].iloc[-1])
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("현재가", f"{cur:,.0f} 원")
        m2.metric("5일 수익률", f"{(cur / df['Close'].iloc[-6] - 1) * 100:+.2f}%")
        m3.metric("20일 수익률", f"{(cur / df['Close'].iloc[-21] - 1) * 100:+.2f}%")
        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - 100 / (1 + rs)
        m4.metric("RSI(14)", f"{rsi.iloc[-1]:.1f}")

    # 캔들 차트
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        name="일봉",
        increasing=dict(line=dict(color="#10B981")),
        decreasing=dict(line=dict(color="#EF4444")),
    ))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA5"], name="MA5",
                              line=dict(width=1.2, color="#FBBF24")))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA20"], name="MA20",
                              line=dict(width=1.2, color=ACCENT_COLOR)))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA60"], name="MA60",
                              line=dict(width=1.2, color="#9CA3AF")))
    fig.update_layout(
        title=f"<b>{name}</b> ({code}) — 캔들차트 + 이동평균",
        template=PLOTLY_TEMPLATE,
        xaxis_rangeslider_visible=False,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_color="#E5E7EB", height=520, margin=dict(l=10, r=10, t=50, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

    # 거래량 + RSI 2열
    col_v, col_r = st.columns(2)
    with col_v:
        fig_v = go.Figure(go.Bar(
            x=df.index, y=df["Volume"], name="거래량",
            marker_color=ACCENT_COLOR, opacity=0.8,
        ))
        fig_v.update_layout(
            title="<b>거래량</b>",
            template=PLOTLY_TEMPLATE,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#E5E7EB", height=300, margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(fig_v, use_container_width=True)

    with col_r:
        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - 100 / (1 + rs)
        fig_r = go.Figure(go.Scatter(
            x=df.index, y=rsi, name="RSI(14)",
            line=dict(color=ACCENT_COLOR_2, width=2),
        ))
        fig_r.add_hline(y=70, line_dash="dash", line_color="#EF4444", annotation_text="70")
        fig_r.add_hline(y=30, line_dash="dash", line_color="#10B981", annotation_text="30")
        fig_r.update_layout(
            title="<b>RSI(14)</b>",
            template=PLOTLY_TEMPLATE, yaxis_range=[0, 100],
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#E5E7EB", height=300, margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(fig_r, use_container_width=True)


# ===== 페이지: 백테스팅 결과 =====

def page_backtest(date: str) -> None:
    section_header("백테스팅 결과", "🔬")

    summary_path = DOCS_DIR / date / "backtest_summary.csv"
    if not summary_path.exists():
        st.warning(
            "백테스팅 결과 파일이 없습니다. 터미널에서 다음을 먼저 실행하세요:\n\n"
            "```\npython backtest_runner.py\n```"
        )
        return

    summary = pd.read_csv(summary_path)
    st.subheader("📊 카테고리별 요약")

    # 메트릭 카드 (4개)
    if not summary.empty and "거래수" in summary.columns:
        cols = st.columns(len(summary))
        for col, (_, row) in zip(cols, summary.iterrows()):
            ret = row.get("평균수익률(%)")
            win = row.get("승률(%)")
            label = row["카테고리"]
            ret_str = f"{ret:+.2f}%" if pd.notna(ret) else "—"
            delta_str = f"승률 {win:.1f}%" if pd.notna(win) else None
            col.metric(label, ret_str, delta=delta_str)

    st.dataframe(summary, use_container_width=True)

    if "평균수익률(%)" in summary.columns and not summary["평균수익률(%)"].isna().all():
        fig = px.bar(
            summary, x="카테고리", y="평균수익률(%)",
            color="승률(%)", color_continuous_scale="Plasma",
            text="평균수익률(%)",
            template=PLOTLY_TEMPLATE,
            title="<b>카테고리별 평균 수익률 + 승률</b>",
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#E5E7EB", height=380, margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 카테고리별 거래 내역")
    cats = ["D", "E", "F"]
    cat_titles = {"D": "🚀 [D] 모멘텀", "E": "📉 [E] 과매도 반등", "F": "⭐ [F] 단기 관심"}
    tabs = st.tabs([cat_titles[c] for c in cats])
    for tab, cat in zip(tabs, cats):
        with tab:
            f = DOCS_DIR / date / f"backtest_{cat}.csv"
            if not f.exists():
                st.info("거래 내역 없음")
                continue
            df = pd.read_csv(f)
            if df.empty:
                st.info("이 카테고리에서는 신호가 없었습니다.")
                continue
            st.dataframe(df, use_container_width=True, height=400)
            fig = px.histogram(
                df, x="수익률(%)", nbins=30,
                template=PLOTLY_TEMPLATE,
                title=f"<b>{cat_titles[cat]} 수익률 분포</b>  ({len(df)}건)",
                color_discrete_sequence=[ACCENT_COLOR],
            )
            fig.add_vline(x=0, line_dash="dash", line_color="#EF4444")
            fig.add_vline(
                x=df["수익률(%)"].mean(), line_dash="dot",
                line_color=ACCENT_COLOR_2,
                annotation_text=f"평균 {df['수익률(%)'].mean():.2f}%",
                annotation_font_color=ACCENT_COLOR_2,
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="#E5E7EB", height=380, margin=dict(l=10, r=10, t=50, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)


# ===== 메인 =====

def main() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    st.title("📈 KOSPI 스크리너")
    st.markdown(
        '<p style="color:#9CA3AF; margin-top:-12px; margin-bottom:1.2rem">'
        '코스피 종목 6개 카테고리 스크리닝 · 섹터 분석 · 백테스팅 · 다크 모던 대시보드</p>',
        unsafe_allow_html=True,
    )

    dates = list_dates()
    if not dates:
        st.error(
            "📭 docs 폴더에 결과 데이터가 없습니다.\n\n"
            "터미널에서 `python kospi_screener.py` 또는 `python start.py`를 먼저 실행하세요."
        )
        return

    with st.sidebar:
        st.markdown("## ⚙️ 설정")
        selected_date = st.selectbox("📅 기준일", dates, key="date_sel")

        st.markdown("---")
        st.markdown("## 📑 페이지")
        page = st.radio(
            "이동",
            [
                "📊 카테고리 결과",
                "🏭 섹터 분석",
                "🔍 종목 상세 차트",
                "🔬 백테스팅 결과",
            ],
            label_visibility="collapsed",
        )

        st.markdown("---")
        st.markdown("""
### 📖 지표 가이드
- **PER**: 낮을수록 저평가
- **ROE**: 15% 이상 우수
- **DIV**: 5% 이상 고배당
- **RSI(14)**: 30 미만 과매도
- **거래량배수**: 2배 이상 관심

### ⚠️ 면책
본 결과는 단순 조건 필터링이며 **투자 추천이 아닙니다**.
""")

    # 상단 KPI 카드 (모든 페이지 공통)
    render_kpi_dashboard(selected_date)
    st.markdown("---")

    if "카테고리" in page:
        page_categories(selected_date)
    elif "섹터" in page:
        page_sectors(selected_date)
    elif "종목" in page:
        page_stock_detail(selected_date)
    else:
        page_backtest(selected_date)


if __name__ == "__main__":
    main()
