from __future__ import annotations

import html
import math

import pandas as pd
import plotly.express as px
import streamlit as st

from data_clean import CLEAN_KEY, CLEAN_SOURCE_KEY
from data_view import DATA_KEY, META_KEY

AGGREGATIONS = {
    "均值": "mean",
    "中位数": "median",
    "求和": "sum",
    "计数（非空）": "count",
}
TOP_CATEGORIES = 15
TOP_GROUPS = 20


class StatisticsError(Exception):
    """统计分析无法完成时抛出的业务异常。"""


STATS_STYLE = """
<style>
.ds-page-head {
    margin: 0.2rem 0 1.25rem;
}

.ds-kicker {
    color: #0d9488;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.16em;
    text-transform: uppercase;
}

.ds-title {
    margin: 0.28rem 0 0.5rem;
    color: #0b1f2a;
    font-size: 2rem;
    line-height: 1.25;
    letter-spacing: -0.03em;
}

.ds-subtitle {
    max-width: 800px;
    margin: 0;
    color: #5d7471;
    font-size: 0.9rem;
    line-height: 1.8;
}

.ds-source-card {
    padding: 1.1rem 1.2rem;
    border: 1px solid #cfe7e1;
    border-radius: 14px;
    background: linear-gradient(120deg, #f0fdfa, #ffffff);
}

.ds-source-label {
    color: #0d9488;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.13em;
    text-transform: uppercase;
}

.ds-source-name {
    margin-top: 0.25rem;
    color: #0b1f2a;
    font-size: 1.16rem;
    font-weight: 700;
    line-height: 1.4;
    overflow-wrap: anywhere;
}

.ds-source-meta {
    margin-top: 0.3rem;
    color: #5d7471;
    font-size: 0.78rem;
    line-height: 1.65;
}

.ds-badge {
    display: inline-block;
    margin-left: 0.45rem;
    padding: 0.16rem 0.5rem;
    border-radius: 999px;
    font-size: 0.65rem;
    font-weight: 600;
    vertical-align: middle;
}

.ds-badge.clean {
    background: #dcfce7;
    color: #166534;
}

.ds-badge.raw {
    background: #f1f5f9;
    color: #475569;
}

.ds-metric {
    min-height: 108px;
    padding: 0.9rem 1rem;
    border: 1px solid #dbe7e3;
    border-top: 3px solid #0d9488;
    border-radius: 12px;
    background: #ffffff;
    box-shadow: 0 6px 18px rgba(11, 31, 42, 0.035);
}

.ds-metric-label {
    color: #5d7471;
    font-size: 0.72rem;
    letter-spacing: 0.04em;
}

.ds-metric-value {
    margin-top: 0.28rem;
    color: #0b1f2a;
    font-size: 1.45rem;
    font-weight: 700;
    line-height: 1.2;
}

.ds-metric-hint {
    margin-top: 0.14rem;
    color: #829590;
    font-size: 0.7rem;
}

.ds-section-head {
    margin: 1.5rem 0 0.7rem;
}

.ds-section-kicker {
    color: #0d9488;
    font-size: 0.66rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
}

.ds-section-title {
    margin: 0.2rem 0 0.25rem;
    color: #0b1f2a;
    font-size: 1.35rem;
    letter-spacing: -0.015em;
}

.ds-section-copy {
    margin: 0;
    color: #657b77;
    font-size: 0.82rem;
    line-height: 1.7;
}

.ds-note {
    margin-top: 0.3rem;
    color: #829590;
    font-size: 0.72rem;
    line-height: 1.65;
}

.ds-empty {
    padding: 1.7rem 1.6rem;
    border: 1px solid #dbe7e3;
    border-radius: 16px;
    background: linear-gradient(145deg, #f7fcfb, #ffffff);
}

.ds-empty-kicker {
    color: #0f766e;
    font-size: 0.66rem;
    font-weight: 700;
    letter-spacing: 0.14em;
}

.ds-empty h3 {
    margin: 0.4rem 0;
    color: #0b1f2a;
    font-size: 1.25rem;
}

.ds-empty p {
    max-width: 720px;
    margin: 0 0 0.7rem;
    color: #5d7471;
    font-size: 0.86rem;
    line-height: 1.8;
}

.ds-footer {
    margin-top: 2rem;
    padding-top: 1rem;
    border-top: 1px solid #dbe7e3;
    color: #849793;
    font-size: 0.74rem;
}

@media (max-width: 760px) {
    .ds-title {
        font-size: 1.7rem;
    }

    .ds-empty {
        padding: 1.2rem 1.1rem;
    }
}
</style>
"""


def get_numeric_columns(frame: pd.DataFrame) -> list[str]:
    """返回可以用于数值统计的字段。"""
    return [
        column
        for column in frame.columns
        if pd.api.types.is_numeric_dtype(frame[column])
        and not pd.api.types.is_bool_dtype(frame[column])
    ]


def get_category_columns(frame: pd.DataFrame) -> list[str]:
    """返回可以用于频数或分组统计的分类字段。"""
    return [
        column
        for column in frame.columns
        if pd.api.types.is_object_dtype(frame[column])
        or pd.api.types.is_string_dtype(frame[column])
        or pd.api.types.is_bool_dtype(frame[column])
        or isinstance(frame[column].dtype, pd.CategoricalDtype)
    ]


def numeric_summary(frame: pd.DataFrame, column: str) -> dict[str, object]:
    """计算单个数值字段的描述统计。"""
    if column not in frame.columns:
        raise StatisticsError(f"字段不存在：{column}")
    if not pd.api.types.is_numeric_dtype(frame[column]):
        raise StatisticsError(f"字段“{column}”不是数值类型。")

    series = frame[column]
    valid = series.dropna()
    summary: dict[str, object] = {
        "count": int(valid.count()),
        "missing": int(series.isna().sum()),
        "mean": valid.mean(),
        "median": valid.median(),
        "std": valid.std(),
        "min": valid.min(),
        "q25": valid.quantile(0.25) if len(valid) else None,
        "q75": valid.quantile(0.75) if len(valid) else None,
        "max": valid.max(),
    }
    return summary


def format_number(value: object) -> str:
    """格式化统计数字，缺失或无法计算时显示破折号。"""
    if value is None or pd.isna(value):
        return "—"
    if isinstance(value, int):
        return f"{value:,}"
    number = float(value)
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.2f}"


def numeric_statistics_table(summary: dict[str, object]) -> pd.DataFrame:
    """把数值统计字典转换为展示表。"""
    rows = (
        ("非空值", format_number(summary["count"])),
        ("缺失值", format_number(summary["missing"])),
        ("均值", format_number(summary["mean"])),
        ("中位数", format_number(summary["median"])),
        ("标准差", format_number(summary["std"])),
        ("最小值", format_number(summary["min"])),
        ("25% 分位", format_number(summary["q25"])),
        ("75% 分位", format_number(summary["q75"])),
        ("最大值", format_number(summary["max"])),
    )
    return pd.DataFrame(rows, columns=["指标", "值"])


def category_frequencies(
    frame: pd.DataFrame,
    column: str,
    top_n: int | None = None,
) -> pd.DataFrame:
    """计算分类字段的频数和占比，缺失值单独作为一类。"""
    if column not in frame.columns:
        raise StatisticsError(f"字段不存在：{column}")

    labels = frame[column].map(
        lambda value: "(缺失)" if pd.isna(value) else str(value)
    )
    counts = labels.value_counts(dropna=False)
    result = counts.rename_axis("类别").reset_index(name="频数")
    result["占比"] = (
        result["频数"] / len(frame) if len(frame) else 0.0
    ).map(lambda ratio: f"{ratio:.2%}")

    if top_n is not None:
        result = result.head(top_n).copy()

    return result


def group_statistics(
    frame: pd.DataFrame,
    group_column: str,
    value_column: str,
    aggregation: str,
) -> pd.DataFrame:
    """按分类字段分组，对数值字段做聚合。"""
    if group_column not in frame.columns:
        raise StatisticsError(f"分组字段不存在：{group_column}")
    if value_column not in frame.columns:
        raise StatisticsError(f"统计字段不存在：{value_column}")
    if aggregation not in {"mean", "median", "sum", "count"}:
        raise StatisticsError("不支持的分组统计方式。")
    if not pd.api.types.is_numeric_dtype(frame[value_column]):
        raise StatisticsError(f"字段“{value_column}”不是数值类型。")

    group_labels = frame[group_column].map(
        lambda value: "(缺失)" if pd.isna(value) else str(value)
    )
    values = pd.to_numeric(frame[value_column], errors="coerce")
    working = pd.DataFrame({"分组": group_labels, "值": values})

    result = (
        working.groupby("分组", dropna=False)["值"]
        .agg(aggregation)
        .reset_index(name="统计值")
    )
    result = result.dropna(subset=["统计值"]).sort_values(
        "统计值", ascending=False
    ).reset_index(drop=True)
    return result


def style_figure(figure, title: str) -> object:
    """统一 Plotly 图表的布局和颜色。"""
    figure.update_layout(
        title=dict(text=title, font=dict(size=14, color="#0b1f2a")),
        height=360,
        margin=dict(l=12, r=12, t=52, b=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Segoe UI, Microsoft YaHei", color="#425b57"),
        colorway=["#0d9488"],
        showlegend=False,
    )
    figure.update_xaxes(gridcolor="#e8f0ed", zeroline=False)
    figure.update_yaxes(gridcolor="#e8f0ed", zeroline=False)
    return figure


def resolve_analysis_data() -> tuple[pd.DataFrame | None, dict[str, object]]:
    """选择统计使用的数据：优先当前有效的清洗副本。"""
    original = st.session_state.get(DATA_KEY)
    if not isinstance(original, pd.DataFrame):
        return None, {}

    metadata = st.session_state.get(META_KEY, {})
    clean_frame = st.session_state.get(CLEAN_KEY)
    clean_source = st.session_state.get(CLEAN_SOURCE_KEY)
    current_signature = str(
        metadata.get("signature")
        or f"{metadata.get('file_name', 'dataset')}:{original.shape[0]}x{original.shape[1]}"
    )

    source_info: dict[str, object] = {
        "file_name": metadata.get("file_name", "未命名数据"),
        "is_clean": False,
        "note": "当前使用原始数据；如需先处理缺失值或重复记录，请进入数据清洗。",
    }

    if isinstance(clean_frame, pd.DataFrame):
        if clean_source == current_signature:
            source_info.update(
                {
                    "is_clean": True,
                    "note": "当前使用数据清洗后的副本；如需修改，请回到数据清洗页面。",
                }
            )
            return clean_frame, source_info

        source_info["warning"] = (
            "检测到清洗副本与当前上传文件不一致，本页暂时使用原始数据。"
            "请进入数据清洗页面重新创建清洗副本。"
        )

    return original, source_info


def go_to_data_view() -> None:
    """按钮回调：跳转到数据查看。"""
    st.session_state.nav_page = "数据查看"


def render_header() -> None:
    """渲染统计页面标题。"""
    st.markdown(
        """
        <div class="ds-page-head">
            <div class="ds-kicker">Workspace / Statistics</div>
            <h1 class="ds-title">统计分析</h1>
            <p class="ds-subtitle">
                从当前数据中计算描述统计、分类频数和分组结果，
                并用交互式图表呈现。所有结果都由真实字段实时计算。
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state() -> None:
    """没有数据时显示提示。"""
    st.markdown(
        """
        <section class="ds-empty">
            <div class="ds-empty-kicker">NO DATA YET</div>
            <h3>还没有可分析的数据</h3>
            <p>
                统计分析需要先通过“数据查看”读取 CSV 或 Excel 文件。
                如果已经完成数据清洗，统计页会优先使用清洗后的副本。
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.button(
        "前往数据查看",
        key="stats_go_to_data_view",
        type="primary",
        on_click=go_to_data_view,
    )


def render_source_and_metrics(
    frame: pd.DataFrame,
    source_info: dict[str, object],
) -> None:
    """显示分析数据来源和字段概况。"""
    file_name = html.escape(str(source_info.get("file_name", "未命名数据")))
    is_clean = bool(source_info.get("is_clean"))
    badge_text = "清洗后数据" if is_clean else "原始数据"
    badge_class = "clean" if is_clean else "raw"

    st.markdown(
        f"""
        <div class="ds-source-card">
            <div class="ds-source-label">
                ANALYSIS SOURCE
                <span class="ds-badge {badge_class}">{badge_text}</span>
            </div>
            <div class="ds-source-name">{file_name}</div>
            <div class="ds-source-meta">
                {len(frame):,} 行 × {frame.shape[1]:,} 列 ·
                {len(get_numeric_columns(frame)):,} 个数值字段 ·
                {len(get_category_columns(frame)):,} 个分类字段
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(str(source_info.get("note", "")))
    if source_info.get("warning"):
        st.warning(str(source_info["warning"]))

    metrics = (
        ("数据行数", f"{len(frame):,}", "条记录"),
        ("字段数量", f"{frame.shape[1]:,}", "列"),
        ("数值字段", f"{len(get_numeric_columns(frame)):,}", "可用于数值统计"),
        ("分类字段", f"{len(get_category_columns(frame)):,}", "可用于频数和分组"),
    )
    columns = st.columns(4, gap="medium")
    for column, (label, value, hint) in zip(columns, metrics):
        with column:
            st.markdown(
                f"""
                <div class="ds-metric">
                    <div class="ds-metric-label">{label}</div>
                    <div class="ds-metric-value">{value}</div>
                    <div class="ds-metric-hint">{hint}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_numeric_tab(frame: pd.DataFrame, numeric_columns: list[str]) -> None:
    """数值字段描述统计与图表。"""
    if not numeric_columns:
        st.info("当前数据没有可用于数值统计的字段。")
        return

    selected = st.selectbox(
        "选择数值字段",
        options=numeric_columns,
        format_func=str,
        key="stats_numeric_field",
    )
    summary = numeric_summary(frame, selected)

    left, right = st.columns([1, 1.25], gap="large")
    with left:
        st.markdown(
            """
            <div class="ds-section-kicker">DESCRIPTIVE STATISTICS</div>
            <h3 class="ds-section-title">描述统计</h3>
            """,
            unsafe_allow_html=True,
        )
        st.dataframe(
            numeric_statistics_table(summary),
            width="stretch",
            hide_index=True,
            height=350,
        )

    with right:
        st.markdown(
            """
            <div class="ds-section-kicker">DISTRIBUTION</div>
            <h3 class="ds-section-title">分布图</h3>
            """,
            unsafe_allow_html=True,
        )
        values = frame[selected].dropna()
        if values.empty:
            st.info("该字段没有可绘制的非空数值。")
            return

        bin_count = min(30, max(8, int(math.sqrt(len(values)))))
        histogram = px.histogram(
            frame,
            x=selected,
            nbins=bin_count,
            labels={selected: str(selected)},
        )
        histogram.update_traces(marker_color="#0d9488")
        st.plotly_chart(
            style_figure(histogram, f"{selected} 的分布"),
            width="stretch",
            config={"displaylogo": False},
        )

    box_plot = px.box(
        frame,
        y=selected,
        points="outliers",
        labels={selected: str(selected)},
    )
    box_plot.update_traces(marker_color="#0f766e", line_color="#0f766e")
    st.plotly_chart(
        style_figure(box_plot, f"{selected} 的箱线图"),
        width="stretch",
        config={"displaylogo": False},
    )
    st.markdown(
        '<div class="ds-note">统计计算自动忽略缺失值；箱线图仅显示离群点。</div>',
        unsafe_allow_html=True,
    )


def render_category_tab(frame: pd.DataFrame, category_columns: list[str]) -> None:
    """分类字段频数表和柱状图。"""
    if not category_columns:
        st.info("当前数据没有可用于分类统计的字段。")
        return

    selected = st.selectbox(
        "选择分类字段",
        options=category_columns,
        format_func=str,
        key="stats_category_field",
    )
    frequencies = category_frequencies(frame, selected, top_n=TOP_CATEGORIES)
    unique_count = int(frame[selected].nunique(dropna=True))
    missing_count = int(frame[selected].isna().sum())

    st.caption(
        f"非缺失类别：{unique_count:,} 个 · 缺失值：{missing_count:,} 个 · "
        f"表格和图表显示频数最高的 {min(len(frequencies), TOP_CATEGORIES)} 个类别。"
    )
    if unique_count > TOP_CATEGORIES:
        st.warning("类别数量较多，当前只展示频数最高的 15 个类别。")

    if frequencies.empty:
        st.info("该字段没有可统计的类别。")
        return

    table_column, chart_column = st.columns([1, 1.25], gap="large")
    with table_column:
        st.dataframe(
            frequencies,
            width="stretch",
            hide_index=True,
            height=min(420, 42 + len(frequencies) * 32),
        )

    with chart_column:
        chart_data = frequencies.sort_values("频数", ascending=True)
        chart = px.bar(
            chart_data,
            x="频数",
            y="类别",
            orientation="h",
            labels={"频数": "频数", "类别": "类别"},
        )
        chart.update_traces(marker_color="#0d9488")
        st.plotly_chart(
            style_figure(chart, f"{selected} 的类别频数"),
            width="stretch",
            config={"displaylogo": False},
        )


def render_group_tab(
    frame: pd.DataFrame,
    numeric_columns: list[str],
    category_columns: list[str],
) -> None:
    """分类字段 × 数值字段的分组统计。"""
    if not numeric_columns or not category_columns:
        st.info("分组统计需要至少一个分类字段和一个数值字段。")
        return

    control_left, control_middle, control_right = st.columns(3, gap="medium")
    with control_left:
        group_column = st.selectbox(
            "分组字段",
            options=category_columns,
            format_func=str,
            key="stats_group_field",
        )
    with control_middle:
        value_column = st.selectbox(
            "统计字段",
            options=numeric_columns,
            format_func=str,
            key="stats_group_value",
        )
    with control_right:
        aggregation_label = st.selectbox(
            "统计方式",
            options=list(AGGREGATIONS),
            key="stats_group_aggregation",
        )

    try:
        grouped = group_statistics(
            frame,
            group_column,
            value_column,
            AGGREGATIONS[aggregation_label],
        )
    except StatisticsError as exc:
        st.error(str(exc))
        return

    if grouped.empty:
        st.info("所选字段组合没有可计算的统计结果。")
        return

    grouped_table = grouped.head(TOP_GROUPS).copy()
    grouped_table["统计值"] = grouped_table["统计值"].map(format_number)
    grouped_table = grouped_table.rename(columns={"统计值": aggregation_label})

    st.caption(
        f"按“{group_column}”分组，对“{value_column}”计算{aggregation_label}。"
        f"表格和图表最多显示 {TOP_GROUPS} 个分组。"
    )
    st.markdown(
        '<div class="ds-note">'
        "均值、中位数和求和会忽略组内缺失值；“计数（非空）”统计非空值数量。"
        "</div>",
        unsafe_allow_html=True,
    )

    table_column, chart_column = st.columns([1, 1.25], gap="large")
    with table_column:
        st.dataframe(
            grouped_table,
            width="stretch",
            hide_index=True,
            height=min(440, 42 + len(grouped_table) * 32),
        )

    with chart_column:
        chart_data = grouped.head(TOP_CATEGORIES).sort_values("统计值", ascending=True)
        chart = px.bar(
            chart_data,
            x="统计值",
            y="分组",
            orientation="h",
            labels={"统计值": aggregation_label, "分组": "分组"},
        )
        chart.update_traces(marker_color="#0d9488")
        st.plotly_chart(
            style_figure(chart, f"{value_column} 按 {group_column} 分组"),
            width="stretch",
            config={"displaylogo": False},
        )


def render_statistics() -> None:
    """统计分析页面入口。"""
    st.markdown(STATS_STYLE, unsafe_allow_html=True)
    render_header()

    frame, source_info = resolve_analysis_data()
    if frame is None:
        render_empty_state()
        return

    render_source_and_metrics(frame, source_info)
    numeric_columns = get_numeric_columns(frame)
    category_columns = get_category_columns(frame)

    st.markdown(
        """
        <div class="ds-section-head">
            <div class="ds-section-kicker">ANALYSIS TOOLS</div>
            <h2 class="ds-section-title">统计工作台</h2>
            <p class="ds-section-copy">按字段类型选择统计方式。图表和表格都由当前数据实时计算。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    numeric_tab, category_tab, group_tab = st.tabs(
        ["数值统计", "分类统计", "分组统计"]
    )
    with numeric_tab:
        render_numeric_tab(frame, numeric_columns)
    with category_tab:
        render_category_tab(frame, category_columns)
    with group_tab:
        render_group_tab(frame, numeric_columns, category_columns)

    st.markdown(
        '<p class="ds-footer">GeoData Studio · 统计分析 · 结果来自当前会话中的真实数据</p>',
        unsafe_allow_html=True,
    )
