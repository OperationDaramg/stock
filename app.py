"""KOSPI 스크리너 — 다크 모던 대시보드 (Streamlit).

상단 탭 네비게이션 + 사이드바 제거 (aion2tool 스타일).

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

from src.macro import (
    COMMODITIES, CURRENCIES, INDICES,
    category_market_fit, fetch_market_state, load_series, market_sentiment, summary_table,
)
from src.news import fetch_economic_headlines
from src.recommend import cross_category_recommendations


st.set_page_config(
    page_title="KOSPI 스크리너",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
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


# ===== 커스텀 CSS =====

CUSTOM_CSS = """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');

html, body, [class*="css"], .stMarkdown, button, input, select, textarea {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif !important;
}

/* 사이드바 완전 숨김 (상단 탭만 사용) */
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
[data-testid="stSidebarNav"] { display: none !important; }

/* 전체 배경 */
.stApp {
    background:
      radial-gradient(circle at 20% -10%, rgba(168, 85, 247, 0.15) 0%, transparent 40%),
      radial-gradient(circle at 80% 110%, rgba(6, 182, 212, 0.10) 0%, transparent 40%),
      #0E0F1A;
}

/* 메인 컨텐츠 (사이드바 없으니 풀폭) */
.block-container {
    padding-top: 1.2rem;
    padding-bottom: 3rem;
    padding-left: 2rem;
    padding-right: 2rem;
    max-width: 1500px;
}

/* 헤더 */
h1 {
    background: linear-gradient(90deg, #A855F7 0%, #06B6D4 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: 800 !important;
    letter-spacing: -0.02em;
    margin-bottom: 0 !important;
}
h2, h3, h4 {
    color: #F3F4F6 !important;
    font-weight: 700 !important;
    letter-spacing: -0.01em;
}

/* 메트릭 카드 */
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
[data-testid="stMetricLabel"] { color: #9CA3AF !important; font-size: 0.85rem !important; font-weight: 500 !important; }
[data-testid="stMetricValue"] { color: #F3F4F6 !important; font-weight: 700 !important; font-size: 1.6rem !important; }

/* 데이터프레임 */
[data-testid="stDataFrame"] {
    border-radius: 12px;
    border: 1px solid rgba(168, 85, 247, 0.15);
    overflow: hidden;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
}

/* === 상단 메인 탭 (페이지 네비게이션) === */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: linear-gradient(180deg, rgba(26, 27, 46, 0.8) 0%, rgba(20, 21, 38, 0.6) 100%);
    padding: 8px;
    border-radius: 14px;
    border: 1px solid rgba(168, 85, 247, 0.18);
    backdrop-filter: blur(8px);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px;
    padding: 10px 18px;
    color: #9CA3AF;
    font-weight: 600;
    font-size: 0.95rem;
    transition: all 0.2s ease;
    border: none;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #E5E7EB;
    background: rgba(168, 85, 247, 0.10);
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(90deg, #A855F7 0%, #7C3AED 100%) !important;
    color: white !important;
    box-shadow: 0 4px 14px rgba(168, 85, 247, 0.45);
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

/* 라디오 (카테고리 내부 선택) */
.stRadio > div {
    background: rgba(26, 27, 46, 0.5);
    padding: 10px 14px;
    border-radius: 12px;
    border: 1px solid rgba(168, 85, 247, 0.18);
    flex-wrap: wrap;
    gap: 8px !important;
}
.stRadio label {
    color: #E5E7EB !important;
}
.stRadio [data-testid="stMarkdownContainer"] p {
    color: #E5E7EB !important;
}

/* 알림박스 */
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

hr {
    border-color: rgba(168, 85, 247, 0.15) !important;
    margin: 1.2rem 0 !important;
}

/* 섹션 헤더 */
.section-header {
    display: flex; align-items: center; gap: 12px;
    margin: 1rem 0 1rem;
    padding: 12px 16px;
    background: linear-gradient(90deg, rgba(168, 85, 247, 0.10) 0%, transparent 100%);
    border-left: 3px solid #A855F7;
    border-radius: 6px;
}
.section-header h2 { margin: 0 !important; font-size: 1.25rem !important; }

/* 가이드 페이지의 커스텀 박스 */
.guide-box {
    background: linear-gradient(135deg, rgba(168, 85, 247, 0.06) 0%, rgba(26, 27, 46, 0.4) 100%);
    border: 1px solid rgba(168, 85, 247, 0.20);
    border-radius: 14px;
    padding: 22px 26px;
    margin-bottom: 16px;
}
.guide-box h3 {
    color: #A855F7 !important;
    margin-top: 0 !important;
    font-size: 1.15rem !important;
}
.guide-box .formula {
    background: rgba(6, 182, 212, 0.08);
    border-left: 3px solid #06B6D4;
    padding: 8px 12px;
    border-radius: 6px;
    font-family: monospace;
    color: #06B6D4;
    margin: 8px 0;
}
.guide-table {
    width: 100%;
    border-collapse: collapse;
    margin: 8px 0;
}
.guide-table th, .guide-table td {
    padding: 8px 12px;
    text-align: left;
    border-bottom: 1px solid rgba(168, 85, 247, 0.15);
}
.guide-table th {
    color: #A855F7;
    font-weight: 600;
}
.guide-table td { color: #E5E7EB; }
.warn-box {
    background: rgba(239, 68, 68, 0.08);
    border-left: 3px solid #EF4444;
    border-radius: 8px;
    padding: 14px 18px;
    color: #FCA5A5;
}
</style>
"""

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
    dfs = {k: load_csv(date, k) for k in CATEGORY_FILES}
    sectors = load_csv(date, "Z_섹터요약")

    f_count = len(dfs.get("F_단기관심", pd.DataFrame()))
    sector_count = len(sectors) if not sectors.empty else 0

    a = dfs.get("A_가치주", pd.DataFrame())
    avg_per = a["PER"].mean() if not a.empty and "PER" in a.columns else None
    avg_roe = a["ROE"].mean() if not a.empty and "ROE" in a.columns else None

    label, _, _ = _market_state_cached()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("🌡️ 시장 분위기", label.replace("🟢", "").replace("🟡", "").replace("🟠", "").replace("🔴", "").strip(),
              delta=label.split()[0] if label else None)
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
        fig = px.bar(df, x="종목명", y="DIV",
            color="섹터" if "섹터" in df.columns else None,
            hover_data=["DPS", "PER", "ROE"], template=PLOTLY_TEMPLATE,
            title="<b>배당수익률 (%)</b>")
    elif key == "C_우량주":
        fig = px.bar(df, x="종목명", y="시총_억",
            color="섹터" if "섹터" in df.columns else None,
            hover_data=["PER", "ROE"], template=PLOTLY_TEMPLATE,
            title="<b>시가총액 (억원)</b>")
    elif key == "D_모멘텀":
        fig = px.bar(df, x="종목명", y="거래량배수",
            color="섹터" if "섹터" in df.columns else None,
            hover_data=["MA5", "MA20", "5일수익률(%)"],
            template=PLOTLY_TEMPLATE,
            title="<b>거래량 배수</b>  <span style='color:#9CA3AF'>(당일/20일평균)</span>")
        fig.add_hline(y=1.5, line_dash="dash", line_color=ACCENT_COLOR_2,
                      annotation_text="기준선 1.5", annotation_font_color=ACCENT_COLOR_2)
    elif key == "E_과매도":
        fig = px.bar(df, x="종목명", y="RSI14",
            color="섹터" if "섹터" in df.columns else None,
            hover_data=["PER", "ROE", "5일수익률(%)"],
            template=PLOTLY_TEMPLATE,
            title="<b>RSI(14)</b>  <span style='color:#9CA3AF'>(30 미만=과매도)</span>")
        fig.add_hline(y=30, line_dash="dash", line_color="#10B981",
                      annotation_text="과매도 기준 30", annotation_font_color="#10B981")
    elif key == "F_단기관심":
        fig = px.scatter(df, x="5일수익률(%)", y="거래량배수",
            text="종목명", size="점수",
            color="섹터" if "섹터" in df.columns else None,
            hover_data=["RSI14", "PER", "20일수익률(%)"],
            template=PLOTLY_TEMPLATE,
            title="<b>단기 관심 후보</b>  <span style='color:#9CA3AF'>(우상=강세)</span>")
        fig.update_traces(textposition="top center")

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_color="#E5E7EB", height=480, margin=dict(l=10, r=10, t=60, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)


# ===== 페이지: 시장 기반 종합 추천 =====

def page_recommend(date: str) -> None:
    section_header("시장 기반 종합 후보", "🎯")

    market_label, market_reasons, market_score = _market_state_cached()

    # 상단: 시장 분위기 + 가중치 안내 카드
    st.markdown(
        f'<div style="display:flex; gap:12px; flex-wrap:wrap; margin-bottom:16px">'
        f'<div style="flex:1; min-width:280px; padding:14px 18px; border-radius:12px; '
        f'background:linear-gradient(135deg, rgba(168,85,247,0.10), rgba(26,27,46,0.6)); '
        f'border:1px solid rgba(168,85,247,0.25)">'
        f'<div style="font-size:0.78rem; color:#9CA3AF">현재 시장 분위기</div>'
        f'<div style="font-size:1.3rem; font-weight:700; color:#F3F4F6; margin-top:4px">{market_label}</div>'
        f'<div style="font-size:0.78rem; color:#9CA3AF; margin-top:6px">{market_reasons}</div>'
        f'</div>'
        f'<div style="flex:1; min-width:280px; padding:14px 18px; border-radius:12px; '
        f'background:linear-gradient(135deg, rgba(6,182,212,0.10), rgba(26,27,46,0.6)); '
        f'border:1px solid rgba(6,182,212,0.25)">'
        f'<div style="font-size:0.78rem; color:#9CA3AF">점수 산출 방식</div>'
        f'<div style="font-size:0.95rem; color:#E5E7EB; margin-top:4px; line-height:1.5">'
        f'카테고리 내 순위 백분위 × 시장 가중치<br>'
        f'<span style="color:#10B981">◎ ×1.5</span> · '
        f'<span style="color:#06B6D4">○ ×1.0</span> · '
        f'<span style="color:#FBBF24">△ ×0.6</span> · '
        f'<span style="color:#EF4444">⚠ ×0.2</span>'
        f'</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    top_n = st.slider("추천 종목 수", 5, 30, 15, step=5, key="rec_top_n")
    df = cross_category_recommendations(DOCS_DIR, date, market_score, top_n=top_n)

    if df.empty:
        st.info("추천 데이터가 없습니다. 카테고리 결과가 비어 있는지 확인하세요.")
        return

    # 표시용 컬럼만 (이유는 hover로)
    display_df = df.drop(columns=["_적합도이유"], errors="ignore")
    st.dataframe(display_df, use_container_width=True, height=560)

    # 카테고리 분포 차트
    cat_counts = df["카테고리"].value_counts().reset_index()
    cat_counts.columns = ["카테고리", "종목수"]

    col1, col2 = st.columns([2, 1])
    with col1:
        fig = px.bar(
            cat_counts, x="카테고리", y="종목수",
            title=f"<b>Top {top_n} 카테고리 분포</b>",
            color="종목수", color_continuous_scale="Plasma",
            template=PLOTLY_TEMPLATE,
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#E5E7EB", height=380, margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        sec_counts = df["섹터"].value_counts().head(8).reset_index()
        sec_counts.columns = ["섹터", "종목수"]
        fig2 = px.pie(
            sec_counts, values="종목수", names="섹터",
            title="<b>섹터 분포 (Top 8)</b>", hole=0.4,
            color_discrete_sequence=px.colors.sequential.Plasma_r,
            template=PLOTLY_TEMPLATE,
        )
        fig2.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#E5E7EB", height=380, margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(fig2, use_container_width=True)

    # 다운로드
    st.download_button(
        "📥 종합 후보 CSV 다운로드",
        data=display_df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"추천_{date}.csv",
        mime="text/csv",
        key="dl_rec",
    )

    # 면책
    st.markdown(
        '<div style="margin-top:14px; padding:14px 18px; border-radius:10px; '
        'background:rgba(239,68,68,0.08); border-left:3px solid #EF4444; color:#FCA5A5">'
        '<b>⚠️ 면책</b>: 본 종합 후보는 단순 알고리즘 결과 (카테고리 내 순위 × 시장 가중치)이며 '
        '<b>투자 추천이 아닙니다</b>. 시장 분위기 판정도 룰 기반 단순 모델로 한계가 있습니다. '
        '매수/매도 결정은 본인의 추가 분석과 책임 하에 진행하세요.'
        '</div>',
        unsafe_allow_html=True,
    )


# ===== 페이지: 카테고리 결과 =====

def page_categories(date: str) -> None:
    section_header("카테고리 결과", "📊")

    cat_keys = list(CATEGORY_FILES.keys())
    cat_titles = list(CATEGORY_FILES.values())
    sel_title = st.radio(
        "카테고리 선택", cat_titles, horizontal=True,
        label_visibility="collapsed", key="cat_radio",
    )
    sel_key = cat_keys[cat_titles.index(sel_title)]

    # 시장 분위기 + 카테고리 적합도 배지
    market_label, market_reasons, market_score = _market_state_cached()
    fit_badge, fit_reason = category_market_fit(market_score, sel_key)

    fit_color = "#10B981" if "◎" in fit_badge else (
        "#06B6D4" if "○" in fit_badge else (
            "#FBBF24" if "△" in fit_badge else "#EF4444"
        )
    )

    st.markdown(
        f'<div style="display:flex; gap:12px; flex-wrap:wrap; margin: 0 0 16px 0">'
        f'<div style="flex:1; min-width:280px; padding:14px 18px; border-radius:12px; '
        f'background:linear-gradient(135deg, rgba(168,85,247,0.10), rgba(26,27,46,0.6)); '
        f'border:1px solid rgba(168,85,247,0.25)">'
        f'<div style="font-size:0.78rem; color:#9CA3AF">현재 시장 분위기</div>'
        f'<div style="font-size:1.25rem; font-weight:700; color:#F3F4F6; margin-top:2px">{market_label}</div>'
        f'<div style="font-size:0.78rem; color:#9CA3AF; margin-top:4px">{market_reasons}</div>'
        f'</div>'
        f'<div style="flex:1; min-width:280px; padding:14px 18px; border-radius:12px; '
        f'background:linear-gradient(135deg, rgba(6,182,212,0.10), rgba(26,27,46,0.6)); '
        f'border:1px solid rgba(6,182,212,0.25)">'
        f'<div style="font-size:0.78rem; color:#9CA3AF">{sel_title} 적합도 (시장 분위기 반영)</div>'
        f'<div style="font-size:1.25rem; font-weight:700; color:{fit_color}; margin-top:2px">{fit_badge}</div>'
        f'<div style="font-size:0.78rem; color:#9CA3AF; margin-top:4px">{fit_reason}</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    df = load_csv(date, sel_key)
    if df.empty:
        st.info("조건 충족 종목 없음")
        return

    col_filter, col_dl = st.columns([3, 1])
    with col_filter:
        if "섹터" in df.columns:
            sectors_list = ["전체"] + sorted(df["섹터"].dropna().unique().tolist())
            sel = st.selectbox("🏭 섹터 필터", sectors_list, key=f"sec_{sel_key}")
            if sel != "전체":
                df = df[df["섹터"] == sel]
    with col_dl:
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            "📥 CSV 다운로드",
            data=df.to_csv().encode("utf-8-sig"),
            file_name=f"{sel_key}_{date}.csv",
            mime="text/csv", key=f"dl_{sel_key}",
            use_container_width=True,
        )

    st.dataframe(df, use_container_width=True, height=420)
    render_category_chart(sel_key, df)


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
        fig = px.pie(top10, values="시총합_억", names="섹터",
            title="<b>섹터별 시총 비중 (Top 10)</b>",
            template=PLOTLY_TEMPLATE, hole=0.45,
            color_discrete_sequence=px.colors.sequential.Plasma_r)
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#E5E7EB", height=420, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        top15 = df.head(15)
        fig = px.bar(top15, x="섹터", y="평균PER",
            title="<b>섹터별 평균 PER (Top 15 시총)</b>",
            template=PLOTLY_TEMPLATE,
            color="평균PER", color_continuous_scale="Plasma_r")
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#E5E7EB", height=420, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("섹터별 평균 PER vs ROE")
    df_chart = df[df["평균PER"].between(0, 80) & df["평균ROE"].between(-30, 80)]
    fig2 = px.scatter(df_chart, x="평균PER", y="평균ROE", size="시총합_억", text="섹터",
        hover_data=["종목수", "평균DIV"], template=PLOTLY_TEMPLATE,
        color="평균ROE", color_continuous_scale="Plasma")
    fig2.update_traces(textposition="top center")
    fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_color="#E5E7EB", height=500, margin=dict(l=10, r=10, t=30, b=10))
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

    col_v, col_r = st.columns(2)
    with col_v:
        fig_v = go.Figure(go.Bar(x=df.index, y=df["Volume"], name="거래량",
            marker_color=ACCENT_COLOR, opacity=0.8))
        fig_v.update_layout(title="<b>거래량</b>", template=PLOTLY_TEMPLATE,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#E5E7EB", height=300, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig_v, use_container_width=True)
    with col_r:
        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - 100 / (1 + rs)
        fig_r = go.Figure(go.Scatter(x=df.index, y=rsi, name="RSI(14)",
            line=dict(color=ACCENT_COLOR_2, width=2)))
        fig_r.add_hline(y=70, line_dash="dash", line_color="#EF4444", annotation_text="70")
        fig_r.add_hline(y=30, line_dash="dash", line_color="#10B981", annotation_text="30")
        fig_r.update_layout(title="<b>RSI(14)</b>", template=PLOTLY_TEMPLATE,
            yaxis_range=[0, 100],
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#E5E7EB", height=300, margin=dict(l=10, r=10, t=40, b=10))
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
        fig = px.bar(summary, x="카테고리", y="평균수익률(%)",
            color="승률(%)", color_continuous_scale="Plasma",
            text="평균수익률(%)", template=PLOTLY_TEMPLATE,
            title="<b>카테고리별 평균 수익률 + 승률</b>")
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#E5E7EB", height=380, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 카테고리별 거래 내역")
    cats = ["D", "E", "F"]
    cat_titles = {"D": "🚀 [D] 모멘텀", "E": "📉 [E] 과매도 반등", "F": "⭐ [F] 단기 관심"}

    sel_cat_label = st.radio(
        "카테고리 선택", [cat_titles[c] for c in cats],
        horizontal=True, label_visibility="collapsed", key="bt_radio",
    )
    sel_cat = cats[[cat_titles[c] for c in cats].index(sel_cat_label)]

    f = DOCS_DIR / date / f"backtest_{sel_cat}.csv"
    if not f.exists():
        st.info("거래 내역 없음")
        return
    df = pd.read_csv(f)
    if df.empty:
        st.info("이 카테고리에서는 신호가 없었습니다.")
        return
    st.dataframe(df, use_container_width=True, height=400)
    fig = px.histogram(df, x="수익률(%)", nbins=30, template=PLOTLY_TEMPLATE,
        title=f"<b>{cat_titles[sel_cat]} 수익률 분포</b>  ({len(df)}건)",
        color_discrete_sequence=[ACCENT_COLOR])
    fig.add_vline(x=0, line_dash="dash", line_color="#EF4444")
    fig.add_vline(x=df["수익률(%)"].mean(), line_dash="dot", line_color=ACCENT_COLOR_2,
        annotation_text=f"평균 {df['수익률(%)'].mean():.2f}%",
        annotation_font_color=ACCENT_COLOR_2)
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_color="#E5E7EB", height=380, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig, use_container_width=True)


# ===== 페이지: 글로벌 동향 =====

@st.cache_data(ttl=600)
def _macro_summary_cached(target: str) -> pd.DataFrame:
    if target == "indices":
        return summary_table(INDICES)
    if target == "currencies":
        return summary_table(CURRENCIES)
    if target == "commodities":
        return summary_table(COMMODITIES)
    return pd.DataFrame()


@st.cache_data(ttl=600)
def _series_cached(symbol: str, days: int) -> pd.DataFrame:
    return load_series(symbol, days)


@st.cache_data(ttl=300)
def _news_cached() -> pd.DataFrame:
    return fetch_economic_headlines(30)


@st.cache_data(ttl=600)
def _market_state_cached() -> tuple[str, str, int]:
    """시장 분위기 (라벨, 이유, 점수). 10분 캐시."""
    try:
        return fetch_market_state()
    except Exception as e:
        return ("🟡 데이터 부족", str(e)[:80], 0)


def page_global() -> None:
    section_header("글로벌 동향", "🌍")

    # ---- 시장 분위기 판정 ----
    indices_df = _macro_summary_cached("indices")

    vix_level = None
    kospi_20d = None
    sp500_20d = None
    if not indices_df.empty:
        vix_row = indices_df[indices_df["심볼"] == "VIX"]
        if not vix_row.empty:
            vix_level = float(vix_row["현재값"].iloc[0])
        kospi_row = indices_df[indices_df["심볼"] == "KS11"]
        if not kospi_row.empty and "20일(%)" in kospi_row.columns:
            v = kospi_row["20일(%)"].iloc[0]
            kospi_20d = float(v) if pd.notna(v) else None
        sp_row = indices_df[indices_df["심볼"] == "US500"]
        if not sp_row.empty and "20일(%)" in sp_row.columns:
            v = sp_row["20일(%)"].iloc[0]
            sp500_20d = float(v) if pd.notna(v) else None

    label, reasons, score = market_sentiment(vix_level, kospi_20d, sp500_20d)

    st.markdown(
        f'<div style="padding:18px 22px; border-radius:14px; '
        f'background:linear-gradient(135deg, rgba(168,85,247,0.10), rgba(26,27,46,0.6)); '
        f'border:1px solid rgba(168,85,247,0.25); margin-bottom:16px">'
        f'<div style="font-size:0.85rem; color:#9CA3AF; margin-bottom:6px">시장 분위기 (룰 기반 판정)</div>'
        f'<div style="font-size:1.6rem; font-weight:800; color:#F3F4F6">{label}</div>'
        f'<div style="font-size:0.9rem; color:#9CA3AF; margin-top:6px">{reasons}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ---- 주요 지수 변동률 표 ----
    st.subheader("📊 주요 지수")
    if indices_df.empty:
        st.info("지수 데이터 로딩 실패")
    else:
        st.dataframe(indices_df, use_container_width=True, height=320)

        # 차트: 코스피/S&P500/나스닥 정규화 비교
        st.subheader("주요 지수 추이 (90일, 시작=100)")
        compare_syms = ["KS11", "US500", "IXIC", "JP225"]
        fig = go.Figure()
        for sym in compare_syms:
            try:
                s = _series_cached(sym, 120)
                if s.empty:
                    continue
                norm = s["Close"] / s["Close"].iloc[0] * 100
                fig.add_trace(go.Scatter(
                    x=s.index, y=norm, name=INDICES.get(sym, sym),
                    line=dict(width=1.8),
                ))
            except Exception:
                continue
        fig.update_layout(
            template=PLOTLY_TEMPLATE,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#E5E7EB", height=380, margin=dict(l=10, r=10, t=20, b=10),
            yaxis_title="시작일=100 기준",
        )
        st.plotly_chart(fig, use_container_width=True)

        # VIX 별도 차트
        try:
            vix = _series_cached("VIX", 180)
            if not vix.empty:
                fig_v = go.Figure()
                fig_v.add_trace(go.Scatter(
                    x=vix.index, y=vix["Close"], name="VIX",
                    line=dict(color="#EF4444", width=1.8),
                    fill="tozeroy", fillcolor="rgba(239,68,68,0.10)",
                ))
                fig_v.add_hline(y=20, line_dash="dash", line_color="#FBBF24",
                                annotation_text="20 (경계)")
                fig_v.add_hline(y=30, line_dash="dash", line_color="#EF4444",
                                annotation_text="30 (위험)")
                fig_v.update_layout(
                    title="<b>VIX (공포지수) - 180일</b>",
                    template=PLOTLY_TEMPLATE,
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#E5E7EB", height=320, margin=dict(l=10, r=10, t=50, b=10),
                )
                st.plotly_chart(fig_v, use_container_width=True)
        except Exception:
            pass

    st.markdown("---")

    # ---- 환율 ----
    st.subheader("💱 환율")
    fx_df = _macro_summary_cached("currencies")
    col_t, col_c = st.columns([1, 2])
    with col_t:
        if not fx_df.empty:
            st.dataframe(fx_df, use_container_width=True, height=200)
    with col_c:
        try:
            usd = _series_cached("USD/KRW", 180)
            if not usd.empty:
                fig = go.Figure(go.Scatter(
                    x=usd.index, y=usd["Close"], name="USD/KRW",
                    line=dict(color=ACCENT_COLOR_2, width=1.8),
                ))
                fig.update_layout(
                    title="<b>원/달러 환율 - 180일</b>",
                    template=PLOTLY_TEMPLATE,
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#E5E7EB", height=300, margin=dict(l=10, r=10, t=50, b=10),
                )
                st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass

    st.markdown("---")

    # ---- 원자재 ----
    st.subheader("🛢️ 원자재")
    cm_df = _macro_summary_cached("commodities")
    col_t2, col_c2 = st.columns([1, 2])
    with col_t2:
        if not cm_df.empty:
            st.dataframe(cm_df, use_container_width=True, height=200)
    with col_c2:
        try:
            wti = _series_cached("CL=F", 180)
            gold = _series_cached("GC=F", 180)
            fig = go.Figure()
            if not wti.empty:
                fig.add_trace(go.Scatter(
                    x=wti.index, y=wti["Close"] / wti["Close"].iloc[0] * 100,
                    name="WTI 원유", line=dict(color="#FBBF24", width=1.8),
                ))
            if not gold.empty:
                fig.add_trace(go.Scatter(
                    x=gold.index, y=gold["Close"] / gold["Close"].iloc[0] * 100,
                    name="금", line=dict(color="#A855F7", width=1.8),
                ))
            fig.update_layout(
                title="<b>원자재 추이 (180일, 시작=100)</b>",
                template=PLOTLY_TEMPLATE,
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="#E5E7EB", height=300, margin=dict(l=10, r=10, t=50, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass

    st.markdown("---")

    # ---- 경제 뉴스 헤드라인 ----
    st.subheader("📰 경제 뉴스 헤드라인 (네이버 금융)")
    news_df = _news_cached()
    if news_df.empty:
        st.info("뉴스 로딩 실패")
    else:
        for _, row in news_df.head(20).iterrows():
            title = row.get("제목", "")
            url = row.get("URL", "")
            press = row.get("출처", "")
            summary = row.get("요약", "")
            press_html = f"<span style='color:#9CA3AF; font-size:0.8rem'> · {press}</span>" if press else ""
            summary_html = f"<div style='color:#9CA3AF; font-size:0.85rem; margin-top:2px'>{summary}</div>" if summary else ""
            st.markdown(
                f'<div style="padding:10px 14px; margin:6px 0; border-radius:10px; '
                f'background:rgba(26,27,46,0.5); border-left:3px solid #A855F7">'
                f'<a href="{url}" target="_blank" style="color:#E5E7EB; text-decoration:none; font-weight:600">{title}</a>'
                f'{press_html}{summary_html}</div>',
                unsafe_allow_html=True,
            )

    st.caption("※ 뉴스는 네이버 금융 메인 뉴스 페이지에서 실시간 스크래핑하며 5분 캐시됩니다.")


# ===== 페이지: 가이드 (지표 + 면책) =====

def page_guide() -> None:
    section_header("지표 가이드 & 면책", "📖")

    st.markdown("""
이 도구에서 사용하는 모든 지표의 **상세 설명·해석 기준·한계**를 정리합니다.
주식 초심자가 결과를 정확히 이해하고 직접 판단할 수 있도록 작성되었습니다.
""")

    # ===== 펀더멘털 지표 =====
    st.markdown("## 🧮 펀더멘털 지표")

    st.markdown("""
<div class="guide-box">
<h3>1. PER (Price Earnings Ratio, 주가수익비율)</h3>
<div class="formula">PER = 주가 / 1주당 순이익(EPS)</div>
<b>의미</b>: 1주당 순이익의 몇 배 가격에 주식이 거래되는가. 이 회사가 현재 이익을 그대로 유지한다고 가정할 때 <b>투자금 회수에 몇 년 걸리는가</b>로도 해석할 수 있다.
<table class="guide-table">
<tr><th>PER</th><th>해석</th><th>주의</th></tr>
<tr><td>5 이하</td><td>매우 저평가</td><td>사양 산업, 일회성 이익, 위험 신호일 수도</td></tr>
<tr><td>5 ~ 10</td><td>저평가</td><td>가치주 영역, 안정적 산업에서 흔함</td></tr>
<tr><td>10 ~ 15</td><td>적정 (시장 평균)</td><td>한국 코스피 평균 PER 약 11~13</td></tr>
<tr><td>15 ~ 25</td><td>약간 고평가</td><td>성장주는 정상, 가치주는 비싼 편</td></tr>
<tr><td>25 이상</td><td>고평가</td><td>미래 성장 기대 반영. 고평가 위험</td></tr>
</table>
<b>한계</b>: 적자(순이익 음수) 기업은 PER이 음수가 되어 무의미. 일회성 손익(자산 매각 등)이 들어가면 왜곡됨.
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="guide-box">
<h3>2. ROE (Return on Equity, 자기자본이익률)</h3>
<div class="formula">ROE = 당기순이익 / 자기자본 × 100 (%)</div>
<b>의미</b>: 회사가 주주의 돈(자기자본)으로 1년 동안 얼마나 벌었나. <b>주주 수익률</b>이라고 볼 수 있다.
<table class="guide-table">
<tr><th>ROE</th><th>해석</th></tr>
<tr><td>5% 미만</td><td>부진 (자본 효율 낮음)</td></tr>
<tr><td>5 ~ 10%</td><td>보통 (시장 평균 수준)</td></tr>
<tr><td>10 ~ 15%</td><td>양호</td></tr>
<tr><td>15 ~ 20%</td><td>우수 (워런 버핏 선호 구간)</td></tr>
<tr><td>20% 이상</td><td>매우 우수 (지속 가능성 검증 필요)</td></tr>
</table>
<b>한계</b>: 부채 비율이 높은 회사는 자기자본이 작아 ROE가 부풀려짐 (재무 레버리지 효과). ROE가 높아도 부채 위험이 클 수 있다.
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="guide-box">
<h3>3. DIV (배당수익률, Dividend Yield)</h3>
<div class="formula">DIV = 연간 주당배당금 / 주가 × 100 (%)</div>
<b>의미</b>: 1년 동안 주식을 보유하면 배당으로 받는 돈의 비율. 은행 예금 이자율과 비교 가능.
<table class="guide-table">
<tr><th>DIV</th><th>해석</th></tr>
<tr><td>1% 미만</td><td>비배당 또는 약배당 (성장주 대부분)</td></tr>
<tr><td>1 ~ 3%</td><td>일반 배당</td></tr>
<tr><td>3 ~ 5%</td><td>안정 배당주</td></tr>
<tr><td>5 ~ 8%</td><td>고배당주</td></tr>
<tr><td>8% 이상</td><td>초고배당 (지속 가능성 의심 필요)</td></tr>
</table>
<b>한계</b>: 일시적 특별배당으로 부풀려진 경우, 주가 급락으로 배당수익률이 일시 상승한 경우 주의. <b>배당 컷 위험</b>(다음해 배당 줄어들 가능성)도 존재.
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="guide-box">
<h3>4. DPS (주당배당금, Dividend Per Share)</h3>
<div class="formula">DPS = 연간 총 배당금 / 발행주식 수 (원)</div>
<b>의미</b>: 1주당 받는 연간 배당금의 절대 금액 (원).
<br><b>활용</b>: 종목 간 비교는 DIV(%)가 적합하지만, 절대 현금 흐름을 알고 싶을 때는 DPS를 본다.
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="guide-box">
<h3>5. 시가총액 (Market Capitalization)</h3>
<div class="formula">시가총액 = 주가 × 발행주식 수</div>
<b>의미</b>: 회사 전체의 주식 시장 가치. 회사를 통째로 살 때 필요한 돈.
<table class="guide-table">
<tr><th>구분</th><th>시총</th><th>특성</th></tr>
<tr><td>대형주</td><td>1조원 이상</td><td>변동성 낮음, 유동성 높음, 외국인 선호</td></tr>
<tr><td>중형주</td><td>3,000억 ~ 1조</td><td>중간 변동성, 성장 잠재력 + 위험</td></tr>
<tr><td>소형주</td><td>3,000억 미만</td><td>변동성 높음, 호재/악재에 민감</td></tr>
</table>
<b>본 도구 컷</b>: 1,000억원 미만은 노이즈가 크고 유동성이 부족해 스크리닝에서 제외.
</div>
""", unsafe_allow_html=True)

    # ===== 기술적 지표 =====
    st.markdown("## 📈 기술적 지표 (가격·거래량 기반)")

    st.markdown("""
<div class="guide-box">
<h3>6. 이동평균선 (Moving Average, MA)</h3>
<div class="formula">MA5 = 최근 5일 종가 평균 / MA20 = 최근 20일 / MA60 = 최근 60일</div>
<b>의미</b>: 일정 기간의 평균 주가. 단기 변동성을 줄이고 추세를 보여준다.
<ul style="color:#E5E7EB; line-height:1.8">
<li><b>MA5 (1주)</b> — 단기 추세, 노이즈 많음</li>
<li><b>MA20 (1개월)</b> — 중기 추세, 가장 자주 사용됨</li>
<li><b>MA60 (3개월)</b> — 장기 추세, 안정적</li>
</ul>
<b>해석</b>:
<ul style="color:#E5E7EB; line-height:1.8">
<li>주가 > MA20: 상승 추세</li>
<li>주가 < MA20: 하락 추세</li>
<li>MA들이 위에서 아래로 정배열(주가 > MA5 > MA20 > MA60): 강한 상승</li>
<li>역배열: 강한 하락</li>
</ul>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="guide-box">
<h3>7. 골든크로스 / 데드크로스</h3>
<b>골든크로스 (Golden Cross)</b>: 단기 이동평균이 장기 이동평균을 <span style="color:#10B981">아래에서 위로 돌파</span> → 상승 신호
<br><b>데드크로스 (Dead Cross)</b>: 단기 이동평균이 장기 이동평균을 <span style="color:#EF4444">위에서 아래로 돌파</span> → 하락 신호
<br><br>
<b>본 도구 정의</b>: 최근 5거래일 내에 <b>MA5가 MA20을 상향 돌파</b>한 경우.
<br><br>
<b>한계</b>: 후행 지표 — 가격이 이미 오른 후에 신호가 발생. 횡보장에서는 잦은 거짓 신호 (whipsaw).
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="guide-box">
<h3>8. RSI (Relative Strength Index, 상대강도지수)</h3>
<div class="formula">RSI = 100 - (100 / (1 + 평균상승폭/평균하락폭)),  기간 14일</div>
<b>의미</b>: 일정 기간 가격이 얼마나 강하게 올랐는지(또는 떨어졌는지) 측정. 0~100 범위.
<table class="guide-table">
<tr><th>RSI</th><th>해석</th><th>전략적 의미</th></tr>
<tr><td>0 ~ 20</td><td>극단적 과매도</td><td>강한 반등 기대 (단, 추세적 하락 중일 수도)</td></tr>
<tr><td>20 ~ 30</td><td>과매도</td><td>단기 반등 가능성</td></tr>
<tr><td>30 ~ 50</td><td>약세 정상</td><td>하락 추세 진행</td></tr>
<tr><td>50 ~ 70</td><td>강세 정상</td><td>상승 추세 진행</td></tr>
<tr><td>70 ~ 80</td><td>과매수</td><td>단기 조정 가능성</td></tr>
<tr><td>80 ~ 100</td><td>극단적 과매수</td><td>강한 조정 기대 (단, 추세적 상승 중일 수도)</td></tr>
</table>
<b>한계</b>: 강한 추세장에서는 RSI가 70 이상 또는 30 이하에 장기간 머무를 수 있다. RSI 단독으로 매매 결정은 위험.
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="guide-box">
<h3>9. 거래량 배수</h3>
<div class="formula">거래량 배수 = 당일 거래량 / 최근 20일 평균 거래량</div>
<b>의미</b>: 평소 대비 오늘 거래가 얼마나 활발한지. 호재/악재로 시장의 관심이 모이면 거래량이 폭증한다.
<table class="guide-table">
<tr><th>배수</th><th>해석</th></tr>
<tr><td>0.5 이하</td><td>거래 부진 (관심 없음)</td></tr>
<tr><td>0.5 ~ 1.5</td><td>평소 수준</td></tr>
<tr><td>1.5 ~ 2.0</td><td>관심 증가 (본 도구 모멘텀 기준)</td></tr>
<tr><td>2.0 ~ 3.0</td><td>거래 급증</td></tr>
<tr><td>3.0 이상</td><td>매우 강한 신호 (호재 또는 악재 발생 가능)</td></tr>
</table>
<b>활용</b>: 가격 신호와 함께 봐야 의미. 거래량 급증 + 주가 상승 = 강한 매수세, 거래량 급증 + 주가 하락 = 강한 매도세.
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="guide-box">
<h3>10. N일 수익률</h3>
<div class="formula">N일 수익률 = (현재 종가 / N일 전 종가 - 1) × 100 (%)</div>
<ul style="color:#E5E7EB; line-height:1.8">
<li><b>5일 수익률</b>: 1주일 동안의 가격 변화. 단기 모멘텀 확인</li>
<li><b>20일 수익률</b>: 1개월 동안의 가격 변화. 중기 추세 확인</li>
</ul>
<b>활용</b>: 5일 +5%, 20일 +20% → 단기·중기 모두 강세. 5일 +5%, 20일 -10% → 하락 후 단기 반등 (반등 지속성 의심).
</div>
""", unsafe_allow_html=True)

    # ===== 카테고리 의미 =====
    st.markdown("## 🎯 카테고리별 의미와 사용 시나리오")

    st.markdown("""
<div class="guide-box">
<h3>[A] 저평가 가치주</h3>
<b>조건</b>: 시총 1,000억원 이상, PER 0~30, ROE 5% 초과, PER+ROE 백분위 합산 점수 최저
<br><b>의미</b>: 펀더멘털 대비 주가가 저평가된 종목. 가치 투자(value investing) 후보.
<br><b>적합한 투자자</b>: 장기 보유, 안정 추구, 가격이 본질가치로 회귀하는 데 시간이 걸려도 기다릴 수 있는 사람
<br><b>주의</b>: 저평가에는 이유가 있을 수 있음 (사양 산업, 구조적 문제). 단순 PER 낮은 게 아닌 ROE도 함께 봐야 함.
</div>

<div class="guide-box">
<h3>[B] 고배당주</h3>
<b>조건</b>: 시총 1,000억원 이상, 배당수익률 상위 10개
<br><b>의미</b>: 보유만 해도 연간 배당으로 일정 수익. 주가 변동보다는 현금 흐름 추구.
<br><b>적합한 투자자</b>: 안정적 현금 흐름 원하는 은퇴자, 배당 재투자 복리 원하는 장기 투자자
<br><b>주의</b>: 배당수익률 8% 이상은 <b>지속 가능성 의심 신호</b>. 회사 실적 악화로 주가 떨어져 일시적으로 높아 보일 수도.
</div>

<div class="guide-box">
<h3>[C] 대형 우량주</h3>
<b>조건</b>: PER 양수, BPS 양수, 시총 상위 10개
<br><b>의미</b>: 코스피 대장주들. 변동성 낮고 외국인 매수 비중 높음.
<br><b>적합한 투자자</b>: 손실 회피 중요, 거시 경제 흐름 따라가고 싶은 보수적 투자자
<br><b>주의</b>: 큰 수익률 기대 어려움. 시장 평균 추종에 가까움.
</div>

<div class="guide-box">
<h3>[D] 모멘텀</h3>
<b>조건</b>: 시총 상위 200, 최근 5거래일 내 골든크로스(MA5↑MA20) + 거래량 1.5배 이상
<br><b>의미</b>: 단기 상승 추세 진입 신호. 추세 추종 매매 후보.
<br><b>적합한 투자자</b>: 단기~중기 트레이딩, 추세 추종 전략
<br><b>주의</b>: 거짓 골든크로스(whipsaw) 위험. 진입 후 추세 꺾이면 손절 필요.
</div>

<div class="guide-box">
<h3>[E] 과매도 반등</h3>
<b>조건</b>: 시총 상위 200, RSI(14) 30 미만
<br><b>의미</b>: 단기 낙폭이 과도해 기술적 반등 기대 종목.
<br><b>적합한 투자자</b>: 역추세 매매, 단기 반등 노리는 트레이더
<br><b>주의</b>: 추세적 하락 종목은 RSI가 30 이하에 오래 머무를 수 있음. 하락 이유 확인 필수.
</div>

<div class="guide-box">
<h3>[F] 단기 관심 후보 ⭐</h3>
<b>조건</b>: 5일 +3% 이상, 20일 -10% 이상, 거래량 1.5배 이상, RSI 30~70 (정상 구간), PER > 0
<br><b>의미</b>: 1~4주 보유 가정. 단기 상승 + 거래량 증가 + 과열 아닌 종목. 가장 종합적인 단기 후보.
<br><b>점수</b>: 5일수익률(%) + 거래량 배수
<br><b>적합한 투자자</b>: 단기 트레이더, 1~4주 보유 전략
<br><b>주의</b>: 진입 시점이 이미 상승 후일 수 있음. 손절 라인 미리 정해두기 권장.
</div>
""", unsafe_allow_html=True)

    # ===== 평가 등급 =====
    st.markdown("## ⭐ 평가 등급 (◎ / ○ / △)")
    st.markdown("""
<div class="guide-box">
<table class="guide-table">
<tr><th>등급</th><th>의미</th></tr>
<tr><td style="font-size:1.3rem">◎</td><td>해당 카테고리 기준에서 <b>매우 강한 신호</b> — 가장 우선 검토할 후보</td></tr>
<tr><td style="font-size:1.3rem">○</td><td><b>양호한 신호</b> — 일반적으로 적합한 후보</td></tr>
<tr><td style="font-size:1.3rem">△</td><td><b>기준은 만족하지만 신호는 보통</b> — 다른 종목과 비교 후 결정</td></tr>
</table>
등급 기준은 카테고리마다 다름:
<ul style="color:#E5E7EB; line-height:1.8">
<li>가치주: PER+ROE 점수 (낮을수록 ◎)</li>
<li>배당주: 배당수익률 (8%↑ ◎ / 5~8% ○ / 그 외 △)</li>
<li>모멘텀: 거래량 배수 (3배↑ ◎ / 2~3배 ○ / 1.5~2배 △)</li>
<li>과매도: RSI (20 미만 ◎ / 20~25 ○ / 25~30 △)</li>
<li>단기관심: 종합 점수 (12↑ ◎ / 8~12 ○ / 그 외 △)</li>
</ul>
</div>
""", unsafe_allow_html=True)

    # ===== 면책 =====
    st.markdown("## ⚠️ 면책 조항 (Disclaimer)")
    st.markdown("""
<div class="warn-box">
<b>본 도구는 단순한 조건 필터링 결과를 제공할 뿐, 투자 자문이 아닙니다.</b><br><br>

1. <b>투자 추천 아님</b>: 본 결과는 알고리즘적 조건에 따라 종목을 분류한 것일 뿐, 매수/매도 추천이 아닙니다. 한국에서 투자자문 행위는 금융투자업 라이선스가 필요한 영역입니다.<br><br>

2. <b>본인 판단 책임</b>: 모든 투자 결정은 사용자 본인의 판단과 책임 하에 이루어져야 합니다. 본 도구의 결과만을 근거로 매매하지 마세요.<br><br>

3. <b>과거 데이터의 한계</b>: 백테스팅 결과는 과거 가상 시뮬레이션입니다. <b>과거 수익률이 미래 수익률을 보장하지 않습니다.</b> 시장 환경 변화, 유동성, 슬리피지, 세금, 거래 수수료 등이 반영되지 않았습니다.<br><br>

4. <b>데이터 정확성</b>: 데이터는 FinanceDataReader, 네이버 금융에서 수집되며, 데이터 소스의 오류·지연·중단 가능성이 존재합니다. 펀더멘털 데이터(PER, ROE, 배당)는 분기별로만 갱신되어 최신성에 한계가 있습니다.<br><br>

5. <b>위험 고지</b>: 주식 투자는 원금 손실 가능성이 있는 위험 자산입니다. 본인의 재무 상황, 투자 경험, 위험 감수 능력을 고려하여 투자하세요.<br><br>

6. <b>책임 한계</b>: 본 도구의 사용으로 인해 발생한 어떠한 손실에 대해서도 개발자/제공자는 책임지지 않습니다.<br><br>

<b>투자 시 권장 사항</b>:
<ul>
<li>여러 정보 소스를 교차 검증하세요</li>
<li>매수 전 손절 라인을 명확히 설정하세요</li>
<li>한 종목/섹터에 자산을 집중하지 마세요 (분산투자)</li>
<li>여유 자금으로만 투자하세요</li>
<li>신뢰할 수 있는 증권사/자문사와 상담을 권합니다</li>
</ul>
</div>
""", unsafe_allow_html=True)


# ===== 메인 =====

def main() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # 헤더 + 우측 기준일 셀렉트
    col_h, col_d = st.columns([4, 1])
    with col_h:
        st.title("📈 KOSPI 스크리너")
        st.markdown(
            '<p style="color:#9CA3AF; margin-top:-12px; margin-bottom:1.0rem">'
            '코스피 종목 6개 카테고리 스크리닝 · 섹터 분석 · 백테스팅</p>',
            unsafe_allow_html=True,
        )

    dates = list_dates()
    if not dates:
        st.error(
            "📭 docs 폴더에 결과 데이터가 없습니다.\n\n"
            "터미널에서 `python kospi_screener.py` 또는 `python start.py`를 먼저 실행하세요."
        )
        return

    with col_d:
        st.markdown('<div style="height: 28px"></div>', unsafe_allow_html=True)
        selected_date = st.selectbox(
            "📅 기준일", dates, key="date_sel",
            label_visibility="visible",
        )

    # KPI
    render_kpi_dashboard(selected_date)
    st.markdown("")

    # 상단 메인 탭 7개 — 추천을 첫 탭, 글로벌 동향을 맨 뒤(가이드 옆)로 배치
    tabs = st.tabs([
        "🎯 추천",
        "📊 카테고리 결과",
        "🏭 섹터 분석",
        "🔍 종목 상세 차트",
        "🔬 백테스팅 결과",
        "📖 가이드",
        "🌍 글로벌 동향",
    ])

    with tabs[0]:
        page_recommend(selected_date)
    with tabs[1]:
        page_categories(selected_date)
    with tabs[2]:
        page_sectors(selected_date)
    with tabs[3]:
        page_stock_detail(selected_date)
    with tabs[4]:
        page_backtest(selected_date)
    with tabs[5]:
        page_guide()
    with tabs[6]:
        page_global()


if __name__ == "__main__":
    main()
