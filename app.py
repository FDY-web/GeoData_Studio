from __future__ import annotations

import streamlit as st

from data_clean import render_data_clean
from data_spatial import render_spatial
from data_stats import render_statistics
from data_view import render_data_view

APP_NAME = "GeoData Studio"
APP_VERSION = "v1.0.0"

MODULES = (
    {
        "name": "数据查看",
        "slug": "data_view",
        "code": "VIEW",
        "description": "导入 CSV 或 Excel 文件，快速查看字段、记录数量与数据预览。",
        "status": "已上线",
        "enabled": True,
    },
    {
        "name": "数据清洗",
        "slug": "data_clean",
        "code": "CLEAN",
        "description": "识别缺失值、重复记录和异常字段，为后续分析准备干净数据。",
        "status": "已上线",
        "enabled": True,
    },
    {
        "name": "统计分析",
        "slug": "statistics",
        "code": "STAT",
        "description": "汇总属性数据的主要特征，用交互式图表呈现统计结果。",
        "status": "已上线",
        "enabled": True,
    },
    {
        "name": "空间分析",
        "slug": "spatial",
        "code": "SPATIAL",
        "description": "检查经纬度字段与坐标质量，并将有效点绘制到交互式地图。",
        "status": "第一阶段",
        "enabled": True,
    },
)

NAV_ITEMS = ("首页", *[module["name"] for module in MODULES])
MODULE_BY_NAME = {module["name"]: module for module in MODULES}

PAGE_STYLE = """
<style>
:root {
    --ink: #0b1f2a;
    --teal: #0d9488;
    --teal-dark: #0f5f58;
    --mint: #ecfdf9;
    --muted: #5d7471;
    --line: #dbe7e3;
    --paper: #ffffff;
    --amber: #b45309;
}

html, body, [class*="css"] {
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
}

[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at 90% 0%, rgba(13, 148, 136, 0.09), transparent 28rem),
        linear-gradient(180deg, #f6faf9 0%, #f8fafc 50%, #ffffff 100%);
}

[data-testid="stHeader"] {
    background: transparent;
}

[data-testid="stAppDeployButton"] {
    display: none;
}

.block-container {
    max-width: 1120px;
    padding-top: 2rem;
    padding-bottom: 3.5rem;
}

[data-testid="stSidebar"] {
    background: #0b1f2a;
    border-right: 1px solid rgba(255, 255, 255, 0.08);
}

[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.6rem;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #d9e8e4;
}

[data-testid="stSidebar"] [role="radiogroup"] label {
    padding: 0.52rem 0.7rem;
    border-radius: 8px;
    transition: background 0.15s ease;
}

[data-testid="stSidebar"] [role="radiogroup"] label:hover {
    background: rgba(255, 255, 255, 0.07);
}

[data-testid="stSidebar"] [role="radiogroup"] label p {
    color: #d9e8e4 !important;
    font-size: 0.92rem;
}

[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
    color: #8fb3ad !important;
    font-size: 0.7rem;
    letter-spacing: 0.08em;
}

[data-testid="stSidebar"] hr {
    border-color: rgba(255, 255, 255, 0.12);
}

.brand-wrap {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.5rem;
}

.brand-mark {
    display: grid;
    place-items: center;
    width: 2.5rem;
    height: 2.5rem;
    border-radius: 10px;
    background: linear-gradient(145deg, #14b8a6, #0f766e);
    color: #ffffff;
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    box-shadow: 0 6px 18px rgba(13, 148, 136, 0.25);
}

.brand-name {
    color: #f2fbf8;
    font-size: 1.02rem;
    font-weight: 700;
    letter-spacing: 0.01em;
}

.brand-subtitle {
    margin-top: 0.1rem;
    color: #8fb3ad;
    font-size: 0.66rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
}

.sidebar-note {
    margin-top: 0.3rem;
    padding: 0.85rem 0.9rem;
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.03);
    color: #a8c4be;
    font-size: 0.78rem;
    line-height: 1.7;
}

.hero {
    position: relative;
    overflow: hidden;
    padding: 2.5rem 2.6rem;
    border-radius: 20px;
    color: #f3fbf8;
    background:
        radial-gradient(circle at 92% 8%, rgba(45, 212, 191, 0.18), transparent 18rem),
        linear-gradient(125deg, #09202b 0%, #0c3b42 58%, #0f766e 100%);
    box-shadow: 0 18px 50px rgba(9, 32, 43, 0.16);
    margin-bottom: 2.2rem;
}

.hero::after {
    content: "";
    position: absolute;
    inset: 0;
    background-image:
        linear-gradient(rgba(255, 255, 255, 0.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.04) 1px, transparent 1px);
    background-size: 42px 42px;
    -webkit-mask-image: linear-gradient(90deg, rgba(0, 0, 0, 0.9), transparent 82%);
    mask-image: linear-gradient(90deg, rgba(0, 0, 0, 0.9), transparent 82%);
    pointer-events: none;
}

.hero > * {
    position: relative;
    z-index: 1;
}

.hero-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.65fr) minmax(220px, 0.55fr);
    gap: 2.4rem;
    align-items: center;
}

.eyebrow {
    color: #5eead4;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
}

.hero h1 {
    margin: 0.35rem 0 0.2rem;
    color: #f7fffc;
    font-size: 3.15rem;
    line-height: 1.06;
    font-weight: 700;
    letter-spacing: -0.035em;
}

.hero-subtitle {
    max-width: 700px;
    margin: 0.55rem 0 0;
    color: #d2e9e3;
    font-size: 1.02rem;
    line-height: 1.75;
}

.hero-copy {
    max-width: 680px;
    margin: 0.7rem 0 0;
    color: #a9c8c1;
    font-size: 0.88rem;
    line-height: 1.8;
}

.chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 1.25rem;
}

.chip {
    padding: 0.32rem 0.66rem;
    border: 1px solid rgba(204, 251, 241, 0.22);
    border-radius: 999px;
    background: rgba(204, 251, 241, 0.08);
    color: #d7f5ee;
    font-size: 0.73rem;
    letter-spacing: 0.02em;
}

.release-panel {
    padding: 1.15rem 1.2rem;
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.055);
    backdrop-filter: blur(6px);
}

.release-kicker {
    color: #8fb3ad;
    font-size: 0.63rem;
    font-weight: 600;
    letter-spacing: 0.15em;
}

.release-version {
    margin-top: 0.15rem;
    color: #f7fffc;
    font-size: 2.1rem;
    font-weight: 700;
    line-height: 1.1;
    letter-spacing: -0.03em;
}

.release-state {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin-top: 0.35rem;
    color: #a7ded4;
    font-size: 0.76rem;
}

.release-dot {
    width: 0.42rem;
    height: 0.42rem;
    border-radius: 50%;
    background: #5eead4;
    box-shadow: 0 0 0 4px rgba(94, 234, 212, 0.12);
}

.release-divider {
    height: 1px;
    margin: 1rem 0 0.75rem;
    background: rgba(255, 255, 255, 0.12);
}

.release-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.28rem 0;
    color: #a9c8c1;
    font-size: 0.76rem;
}

.release-row strong {
    color: #f2fbf8;
    font-size: 0.94rem;
}

.section-head {
    margin: 2rem 0 1.1rem;
}

.section-kicker {
    color: #0d9488;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.16em;
    text-transform: uppercase;
}

.section-title {
    margin: 0.25rem 0 0.45rem;
    color: var(--ink);
    font-size: 1.6rem;
    line-height: 1.3;
    letter-spacing: -0.02em;
}

.section-copy {
    max-width: 720px;
    margin: 0;
    color: var(--muted);
    font-size: 0.88rem;
    line-height: 1.8;
}

[class*="st-key-card_"] {
    min-height: 295px;
    margin-bottom: 0.55rem;
    padding: 1.2rem 1.25rem 0.9rem;
    border: 1px solid var(--line);
    border-radius: 16px;
    background: #ffffff;
    box-shadow: 0 9px 26px rgba(11, 31, 42, 0.04);
    transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}

[class*="st-key-card_"]:hover {
    border-color: #b9d9d2;
    box-shadow: 0 13px 30px rgba(11, 31, 42, 0.065);
    transform: translateY(-2px);
}

[class*="st-key-card_spatial"] {
    border-style: dashed;
    background: linear-gradient(180deg, #ffffff 0%, #f8faf9 100%);
}

.module-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.7rem;
}

.module-code {
    color: #0d9488;
    font-family: Consolas, "Courier New", monospace;
    font-size: 0.66rem;
    font-weight: 700;
    letter-spacing: 0.13em;
}

.module-badge {
    padding: 0.2rem 0.52rem;
    border-radius: 999px;
    font-size: 0.66rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}

.module-badge.soon {
    background: var(--mint);
    color: var(--teal-dark);
}

.module-badge.active {
    background: #dcfce7;
    color: #166534;
}

.module-badge.phase {
    background: #e0f2fe;
    color: #0369a1;
}

.module-badge.dev {
    background: #fff7ed;
    color: var(--amber);
}

.module-title {
    margin: 1rem 0 0.45rem;
    color: var(--ink);
    font-size: 1.25rem;
    line-height: 1.3;
    letter-spacing: -0.01em;
}

.module-desc {
    min-height: 3.6em;
    margin: 0;
    color: var(--muted);
    font-size: 0.86rem;
    line-height: 1.75;
}

[class*="st-key-card_"] .stButton {
    margin-top: 0.7rem;
}

[class*="st-key-card_"] .stButton > button {
    min-height: 2.35rem;
    border: 1px solid #cfe3de;
    border-radius: 9px;
    background: #f7fbfa;
    color: var(--teal-dark);
    font-size: 0.82rem;
    font-weight: 600;
    transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}

[class*="st-key-card_"] .stButton > button:hover {
    border-color: var(--teal);
    background: var(--teal);
    color: #ffffff;
}

[class*="st-key-card_"] .stButton > button:disabled {
    border-color: #e5ece9;
    background: #f2f5f4;
    color: #9aaba6;
}

.scope-note {
    display: grid;
    grid-template-columns: 180px minmax(0, 1fr);
    gap: 1.3rem;
    align-items: start;
    margin-top: 1.35rem;
    padding: 1.3rem 1.4rem;
    border: 1px solid #c7e7df;
    border-radius: 14px;
    background: linear-gradient(115deg, #f0fdfa, #f8fafc);
}

.scope-label {
    color: #0d9488;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
}

.scope-title {
    margin: 0.25rem 0 0;
    color: var(--ink);
    font-size: 1.02rem;
    white-space: nowrap;
}

.scope-copy {
    margin: 0.1rem 0 0;
    color: var(--muted);
    font-size: 0.84rem;
    line-height: 1.8;
}

.subpage {
    padding: 2.4rem 2.6rem;
    border: 1px solid var(--line);
    border-radius: 18px;
    background: #ffffff;
    box-shadow: 0 12px 34px rgba(11, 31, 42, 0.045);
}

.subpage h1 {
    margin: 0.35rem 0 0.55rem;
    color: var(--ink);
    font-size: 2.5rem;
    letter-spacing: -0.03em;
}

.subpage-copy {
    max-width: 720px;
    margin: 0;
    color: var(--muted);
    font-size: 0.92rem;
    line-height: 1.85;
}

.back-note {
    margin-top: 1.1rem;
    color: #849793;
    font-size: 0.78rem;
}

.footer {
    margin-top: 2.2rem;
    padding-top: 1rem;
    border-top: 1px solid var(--line);
    color: #849793;
    font-size: 0.74rem;
    letter-spacing: 0.02em;
}

@media (max-width: 900px) {
    .block-container {
        padding-top: 1.2rem;
    }

    .hero {
        padding: 1.8rem 1.4rem;
    }

    .hero-grid {
        grid-template-columns: 1fr;
        gap: 1.4rem;
    }

    .hero h1 {
        font-size: 2.35rem;
    }

    .release-panel {
        max-width: 320px;
    }

    .scope-note {
        grid-template-columns: 1fr;
        gap: 0.5rem;
    }

    .subpage {
        padding: 1.6rem 1.4rem;
    }
}
</style>
"""


def apply_page_style() -> None:
    """把统一视觉样式注入页面。"""
    st.markdown(PAGE_STYLE, unsafe_allow_html=True)


def ensure_navigation_state() -> None:
    """保证侧边栏导航状态存在且指向有效页面。"""
    if st.session_state.get("nav_page") not in NAV_ITEMS:
        st.session_state.nav_page = "首页"


def navigate_to(page_name: str) -> None:
    """按钮回调：在控件实例化前切换导航页面。"""
    st.session_state.nav_page = page_name


def render_sidebar() -> str:
    """渲染品牌区与导航，返回当前选中的页面名称。"""
    with st.sidebar:
        st.markdown(
            """
            <div class="brand-wrap">
                <div class="brand-mark">GS</div>
                <div>
                    <div class="brand-name">GeoData Studio</div>
                    <div class="brand-subtitle">GIS Data Workbench</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        selected_page = st.radio(
            "功能导航",
            NAV_ITEMS,
            key="nav_page",
            label_visibility="collapsed",
        )

        st.divider()
        st.caption(f"{APP_VERSION} · LOCAL BUILD")
        st.markdown(
            """
            <div class="sidebar-note">
                数据查看、数据清洗和统计分析已开放。<br>
                空间分析第一阶段：坐标检查与点地图。
            </div>
            """,
            unsafe_allow_html=True,
        )

    return selected_page


def render_module_card(module: dict) -> None:
    """渲染单个功能入口卡片，不包含实际数据处理逻辑。"""
    if module["status"] == "开发中":
        badge_class = "dev"
    elif module["status"] == "已上线":
        badge_class = "active"
    elif module["status"] == "第一阶段":
        badge_class = "phase"
    else:
        badge_class = "soon"

    with st.container(key=f"card_{module['slug']}"):
        st.markdown(
            f"""
            <div class="module-meta">
                <span class="module-code">{module['code']}</span>
                <span class="module-badge {badge_class}">{module['status']}</span>
            </div>
            <h3 class="module-title">{module['name']}</h3>
            <p class="module-desc">{module['description']}</p>
            """,
            unsafe_allow_html=True,
        )

        if module["enabled"]:
            st.button(
                "进入模块 →",
                key=f"open_{module['slug']}",
                width="stretch",
                on_click=navigate_to,
                args=(module["name"],),
            )
        else:
            st.button(
                "开发中",
                key=f"open_{module['slug']}",
                width="stretch",
                disabled=True,
            )


def render_home() -> None:
    """渲染 GeoData Studio V1.0 首页。"""
    module_count = len(MODULES)
    pending_count = sum(1 for module in MODULES if module["status"] != "已上线")

    st.markdown(
        f"""
        <section class="hero">
            <div class="hero-grid">
                <div>
                    <div class="eyebrow">Geospatial Data Workbench · V1.0</div>
                    <h1>GeoData Studio</h1>
                    <p class="hero-subtitle">
                        面向 GIS 学生、科研人员和空间数据分析初学者的空间数据处理平台。
                    </p>
                    <p class="hero-copy">
                        从数据查看、清洗到统计与空间分析，把分散的处理步骤整理成
                        清晰、可复现的浏览器工作流。
                    </p>
                    <div class="chips">
                        <span class="chip">Python + Streamlit</span>
                        <span class="chip">本地运行</span>
                        <span class="chip">V1.0 · 首页</span>
                    </div>
                </div>
                <aside class="release-panel">
                    <div class="release-kicker">CURRENT RELEASE</div>
                    <div class="release-version">V1.0</div>
                    <div class="release-state">
                        <span class="release-dot"></span>
                        空间分析第一阶段已上线
                    </div>
                    <div class="release-divider"></div>
                    <div class="release-row">
                        <span>功能入口</span>
                        <strong>{module_count:02d}</strong>
                    </div>
                    <div class="release-row">
                        <span>待完善</span>
                        <strong>{pending_count:02d}</strong>
                    </div>
                </aside>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="section-head">
            <div class="section-kicker">Workspace / 01</div>
            <h2 class="section-title">选择一个功能入口</h2>
            <p class="section-copy">
                从数据检查开始，逐步进入清洗、统计与空间分析。
                数据查看、清洗、统计分析和空间分析第一阶段均已开放。
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for row_start in range(0, len(MODULES), 2):
        columns = st.columns(2, gap="large")
        for column, module in zip(columns, MODULES[row_start : row_start + 2]):
            with column:
                render_module_card(module)

    st.markdown(
        """
        <section class="scope-note">
            <div>
                <div class="scope-label">V1.0 Scope</div>
                <h3 class="scope-title">当前版本范围</h3>
            </div>
            <p class="scope-copy">
                当前版本已实现首页、数据查看、数据清洗、统计分析和空间分析第一阶段：
                支持坐标字段识别、坐标质量检查和交互式点地图。
                空间连接、缓冲区、坐标转换与栅格分析尚未实现。
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<p class="footer">GeoData Studio · V1.0 首页 · 本地运行，不调用收费 API</p>',
        unsafe_allow_html=True,
    )


def render_placeholder(module_name: str) -> None:
    """为尚未实现的模块提供明确说明，避免暗示功能已经可用。"""
    module = MODULE_BY_NAME[module_name]
    status_copy = (
        "空间分析正在开发中。当前版本只提供入口展示，不包含坐标转换、"
        "空间连接或叠加分析功能。"
        if module["status"] == "开发中"
        else "该模块已列入后续开发计划。当前版本只提供入口展示，不包含数据处理功能。"
    )

    st.markdown(
        f"""
        <section class="subpage">
            <div class="eyebrow">{module['code']} / MODULE</div>
            <h1>{module['name']}</h1>
            <p class="subpage-copy">{status_copy}</p>
            <div class="chips">
                <span class="chip" style="border-color:#c7e7df;background:#f0fdfa;color:#0f766e;">
                    {module['status']}
                </span>
                <span class="chip" style="border-color:#e5ece9;background:#f8fafc;color:#5d7471;">
                    当前版本仅展示入口
                </span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.button(
        "← 返回首页",
        key="back_home",
        type="primary",
        on_click=navigate_to,
        args=("首页",),
    )

    st.markdown(
        '<p class="back-note">当前只实现首页，未加载任何数据文件。</p>',
        unsafe_allow_html=True,
    )


def main() -> None:
    """应用入口：配置页面、渲染导航与当前页面。"""
    st.set_page_config(
        page_title="GeoData Studio | GIS 数据处理平台",
        page_icon="🌐",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_page_style()
    ensure_navigation_state()

    selected_page = render_sidebar()
    if selected_page == "首页":
        render_home()
    elif selected_page == "数据查看":
        render_data_view()
    elif selected_page == "数据清洗":
        render_data_clean()
    elif selected_page == "统计分析":
        render_statistics()
    elif selected_page == "空间分析":
        render_spatial()
    else:
        render_placeholder(selected_page)


if __name__ == "__main__":
    main()
