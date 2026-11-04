from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass

import pandas as pd
import plotly.express as px
import streamlit as st

from data_clean import CLEAN_KEY, CLEAN_SOURCE_KEY
from data_view import DATA_KEY, META_KEY

PLOT_LON = "__plot_lon__"
PLOT_LAT = "__plot_lat__"

LON_NAMES = {"lon", "lng", "longitude", "经度"}
LAT_NAMES = {"lat", "latitude", "纬度"}


class SpatialError(Exception):
    """空间分析无法完成时抛出的业务异常。"""


@dataclass
class CoordinateCheck:
    """一次经纬度质量检查的完整结果。"""

    total_rows: int
    missing_lon: int
    missing_lat: int
    missing_rows: int
    non_numeric_lon: int
    non_numeric_lat: int
    out_of_range_lon: int
    out_of_range_lat: int
    valid_count: int
    invalid_count: int
    lon_min: float | None
    lon_max: float | None
    lat_min: float | None
    lat_max: float | None
    valid_points: pd.DataFrame
    invalid_rows: pd.DataFrame


SPATIAL_STYLE = """
<style>
.sa-page-head {
    margin: 0.2rem 0 1.25rem;
}

.sa-kicker {
    color: #0d9488;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.16em;
    text-transform: uppercase;
}

.sa-title {
    margin: 0.28rem 0 0.5rem;
    color: #0b1f2a;
    font-size: 2rem;
    line-height: 1.25;
    letter-spacing: -0.03em;
}

.sa-subtitle {
    max-width: 820px;
    margin: 0;
    color: #5d7471;
    font-size: 0.9rem;
    line-height: 1.8;
}

.sa-source-card {
    padding: 1.1rem 1.2rem;
    border: 1px solid #cfe7e1;
    border-radius: 14px;
    background: linear-gradient(120deg, #f0fdfa, #ffffff);
}

.sa-source-label {
    color: #0d9488;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.13em;
    text-transform: uppercase;
}

.sa-source-name {
    margin-top: 0.25rem;
    color: #0b1f2a;
    font-size: 1.16rem;
    font-weight: 700;
    line-height: 1.4;
    overflow-wrap: anywhere;
}

.sa-source-meta {
    margin-top: 0.3rem;
    color: #5d7471;
    font-size: 0.78rem;
    line-height: 1.65;
}

.sa-badge {
    display: inline-block;
    margin-left: 0.45rem;
    padding: 0.16rem 0.5rem;
    border-radius: 999px;
    font-size: 0.65rem;
    font-weight: 600;
    vertical-align: middle;
}

.sa-badge.clean {
    background: #dcfce7;
    color: #166534;
}

.sa-badge.raw {
    background: #f1f5f9;
    color: #475569;
}

.sa-metric {
    min-height: 105px;
    padding: 0.9rem 1rem;
    border: 1px solid #dbe7e3;
    border-top: 3px solid #0d9488;
    border-radius: 12px;
    background: #ffffff;
    box-shadow: 0 6px 18px rgba(11, 31, 42, 0.035);
}

.sa-metric-label {
    color: #5d7471;
    font-size: 0.72rem;
    letter-spacing: 0.04em;
}

.sa-metric-value {
    margin-top: 0.28rem;
    color: #0b1f2a;
    font-size: 1.45rem;
    font-weight: 700;
    line-height: 1.2;
}

.sa-metric-hint {
    margin-top: 0.14rem;
    color: #829590;
    font-size: 0.7rem;
}

.st-key-spatial_coord_card {
    margin: 0.5rem 0 1.2rem;
    padding: 1.15rem 1.25rem 0.9rem;
    border: 1px solid #dbe7e3;
    border-radius: 14px;
    background: #ffffff;
    box-shadow: 0 7px 22px rgba(11, 31, 42, 0.035);
}

.sa-section-head {
    margin: 1.4rem 0 0.7rem;
}

.sa-section-kicker {
    color: #0d9488;
    font-size: 0.66rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
}

.sa-section-title {
    margin: 0.2rem 0 0.25rem;
    color: #0b1f2a;
    font-size: 1.35rem;
    letter-spacing: -0.015em;
}

.sa-section-copy {
    margin: 0;
    color: #657b77;
    font-size: 0.82rem;
    line-height: 1.7;
}

.sa-note {
    margin-top: 0.3rem;
    color: #829590;
    font-size: 0.72rem;
    line-height: 1.65;
}

.sa-range-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.65rem;
    margin-top: 0.7rem;
}

.sa-range-card {
    padding: 0.8rem 0.9rem;
    border: 1px solid #e0ebe8;
    border-radius: 10px;
    background: #fbfdfc;
}

.sa-range-label {
    color: #738883;
    font-size: 0.7rem;
}

.sa-range-value {
    margin-top: 0.18rem;
    color: #0b1f2a;
    font-family: Consolas, "Courier New", monospace;
    font-size: 0.95rem;
    font-weight: 600;
}

.sa-empty {
    padding: 1.7rem 1.6rem;
    border: 1px solid #dbe7e3;
    border-radius: 16px;
    background: linear-gradient(145deg, #f7fcfb, #ffffff);
}

.sa-empty-kicker {
    color: #0f766e;
    font-size: 0.66rem;
    font-weight: 700;
    letter-spacing: 0.14em;
}

.sa-empty h3 {
    margin: 0.4rem 0;
    color: #0b1f2a;
    font-size: 1.25rem;
}

.sa-empty p {
    max-width: 740px;
    margin: 0 0 0.7rem;
    color: #5d7471;
    font-size: 0.86rem;
    line-height: 1.8;
}

.sa-map-note {
    margin: 0.4rem 0 0.7rem;
    color: #657b77;
    font-size: 0.78rem;
    line-height: 1.65;
}

.sa-footer {
    margin-top: 2rem;
    padding-top: 1rem;
    border-top: 1px solid #dbe7e3;
    color: #849793;
    font-size: 0.74rem;
}

@media (max-width: 760px) {
    .sa-title {
        font-size: 1.7rem;
    }

    .sa-range-grid {
        grid-template-columns: 1fr 1fr;
    }
}
</style>
"""


def _coordinate_role(column: object) -> str | None:
    """根据字段名给出经度/纬度候选角色，仅用于提示。"""
    name = str(column).lower()
    tokens = set(re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", name))
    normalized = re.sub(r"[\s_\-()\[\]{}.,/]+", "", name)

    if (
        "经度" in normalized
        or "longitude" in normalized
        or tokens & {"lon", "lng"}
    ):
        return "lon"
    if "纬度" in normalized or "latitude" in normalized or "lat" in tokens:
        return "lat"
    return None


def detect_coordinate_columns(
    frame: pd.DataFrame,
) -> tuple[object | None, object | None]:
    """自动推荐经纬度字段，优先使用数值字段。"""
    lon_candidates = [
        column for column in frame.columns if _coordinate_role(column) == "lon"
    ]
    lat_candidates = [
        column for column in frame.columns if _coordinate_role(column) == "lat"
    ]

    def preferred(candidates: list[object]) -> object | None:
        if not candidates:
            return None
        numeric_candidates = [
            column
            for column in candidates
            if pd.api.types.is_numeric_dtype(frame[column])
        ]
        return numeric_candidates[0] if numeric_candidates else candidates[0]

    return preferred(lon_candidates), preferred(lat_candidates)


def _format_samples(values: list[object]) -> str:
    """把少量异常值格式化为可读提示。"""
    samples = [str(value) for value in values[:3]]
    return "、".join(f"“{sample}”" for sample in samples)


def validate_coordinates(
    frame: pd.DataFrame,
    lon_column: object,
    lat_column: object,
) -> CoordinateCheck:
    """检查经纬度字段，返回有效点、无效记录和统计结果。"""
    if lon_column == lat_column:
        raise SpatialError("经度字段和纬度字段不能是同一个字段。")
    if lon_column not in frame.columns:
        raise SpatialError(f"经度字段不存在：{lon_column}")
    if lat_column not in frame.columns:
        raise SpatialError(f"纬度字段不存在：{lat_column}")

    lon_raw = frame[lon_column]
    lat_raw = frame[lat_column]
    lon_numeric = pd.to_numeric(lon_raw, errors="coerce")
    lat_numeric = pd.to_numeric(lat_raw, errors="coerce")

    lon_missing_mask = lon_raw.isna()
    lat_missing_mask = lat_raw.isna()
    lon_non_numeric_mask = lon_numeric.isna() & ~lon_missing_mask
    lat_non_numeric_mask = lat_numeric.isna() & ~lat_missing_mask
    lon_out_of_range_mask = lon_numeric.notna() & ~lon_numeric.between(-180, 180)
    lat_out_of_range_mask = lat_numeric.notna() & ~lat_numeric.between(-90, 90)

    valid_mask = (
        lon_numeric.notna()
        & lat_numeric.notna()
        & lon_numeric.between(-180, 180)
        & lat_numeric.between(-90, 90)
    )
    invalid_mask = ~valid_mask

    valid_points = frame.loc[valid_mask].copy()
    valid_points[PLOT_LON] = lon_numeric.loc[valid_mask].astype(float)
    valid_points[PLOT_LAT] = lat_numeric.loc[valid_mask].astype(float)

    invalid_rows = frame.loc[invalid_mask].copy()
    reasons: list[str] = []
    for index in invalid_rows.index:
        row_reasons: list[str] = []

        if pd.isna(lon_raw.loc[index]):
            row_reasons.append("经度缺失")
        elif pd.isna(lon_numeric.loc[index]):
            row_reasons.append("经度非数值")
        elif bool(lon_out_of_range_mask.loc[index]):
            row_reasons.append("经度超出 -180~180")

        if pd.isna(lat_raw.loc[index]):
            row_reasons.append("纬度缺失")
        elif pd.isna(lat_numeric.loc[index]):
            row_reasons.append("纬度非数值")
        elif bool(lat_out_of_range_mask.loc[index]):
            row_reasons.append("纬度超出 -90~90")

        reasons.append("；".join(row_reasons) if row_reasons else "坐标无效")

    if len(invalid_rows):
        invalid_rows.insert(0, "记录索引", list(invalid_rows.index))
        invalid_rows.insert(1, "无效原因", reasons)

    valid_lon = lon_numeric.loc[valid_mask]
    valid_lat = lat_numeric.loc[valid_mask]

    return CoordinateCheck(
        total_rows=int(len(frame)),
        missing_lon=int(lon_missing_mask.sum()),
        missing_lat=int(lat_missing_mask.sum()),
        missing_rows=int((lon_missing_mask | lat_missing_mask).sum()),
        non_numeric_lon=int(lon_non_numeric_mask.sum()),
        non_numeric_lat=int(lat_non_numeric_mask.sum()),
        out_of_range_lon=int(lon_out_of_range_mask.sum()),
        out_of_range_lat=int(lat_out_of_range_mask.sum()),
        valid_count=int(valid_mask.sum()),
        invalid_count=int(invalid_mask.sum()),
        lon_min=float(valid_lon.min()) if len(valid_lon) else None,
        lon_max=float(valid_lon.max()) if len(valid_lon) else None,
        lat_min=float(valid_lat.min()) if len(valid_lat) else None,
        lat_max=float(valid_lat.max()) if len(valid_lat) else None,
        valid_points=valid_points,
        invalid_rows=invalid_rows,
    )


def _map_zoom(valid_points: pd.DataFrame) -> int:
    """根据有效点范围选择一个初始地图缩放级别。"""
    lon_span = float(valid_points[PLOT_LON].max() - valid_points[PLOT_LON].min())
    lat_span = float(valid_points[PLOT_LAT].max() - valid_points[PLOT_LAT].min())
    span = max(lon_span, lat_span)

    if span <= 0.02:
        return 11
    if span <= 0.1:
        return 10
    if span <= 0.5:
        return 9
    if span <= 2:
        return 8
    if span <= 10:
        return 6
    if span <= 40:
        return 4
    return 2


def build_map_figure(
    valid_points: pd.DataFrame,
    hover_fields: list[object],
):
    """构建只包含有效点的交互式地图。"""
    if valid_points.empty:
        raise SpatialError("没有有效坐标点，无法绘制地图。")

    center = {
        "lat": float(valid_points[PLOT_LAT].mean()),
        "lon": float(valid_points[PLOT_LON].mean()),
    }
    hover_data = {PLOT_LON: ":.6f", PLOT_LAT: ":.6f"}
    for field in hover_fields:
        if field in valid_points.columns:
            hover_data[field] = True

    figure = px.scatter_map(
        valid_points,
        lat=PLOT_LAT,
        lon=PLOT_LON,
        hover_data=hover_data,
        labels={PLOT_LON: "经度", PLOT_LAT: "纬度"},
        center=center,
        zoom=_map_zoom(valid_points),
        map_style="open-street-map",
        height=560,
    )
    figure.update_traces(
        marker=dict(size=13, color="#dc2626", opacity=0.9)
    )
    figure.update_layout(
        title=dict(text="有效坐标点地图", font=dict(size=14, color="#0b1f2a")),
        margin=dict(l=0, r=0, t=48, b=0),
        font=dict(family="Segoe UI, Microsoft YaHei", color="#425b57"),
    )
    return figure


def build_offline_figure(
    valid_points: pd.DataFrame,
    hover_fields: list[object],
):
    """构建不加载底图的经纬度平面散点图。"""
    if valid_points.empty:
        raise SpatialError("没有有效坐标点，无法绘制坐标视图。")

    hover_data = {PLOT_LON: ":.6f", PLOT_LAT: ":.6f"}
    for field in hover_fields:
        if field in valid_points.columns:
            hover_data[field] = True

    figure = px.scatter(
        valid_points,
        x=PLOT_LON,
        y=PLOT_LAT,
        hover_data=hover_data,
        labels={PLOT_LON: "经度", PLOT_LAT: "纬度"},
        height=500,
    )
    figure.update_traces(
        marker=dict(size=13, color="#dc2626", opacity=0.9)
    )
    figure.update_yaxes(
        scaleanchor="x",
        scaleratio=1,
        gridcolor="#e8f0ed",
        zeroline=False,
    )
    figure.update_xaxes(gridcolor="#e8f0ed", zeroline=False)
    figure.update_layout(
        title=dict(text="离线坐标视图", font=dict(size=14, color="#0b1f2a")),
        margin=dict(l=12, r=12, t=52, b=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Segoe UI, Microsoft YaHei", color="#425b57"),
    )
    return figure


def resolve_spatial_data() -> tuple[pd.DataFrame | None, dict[str, object]]:
    """选择空间分析使用的数据：优先当前有效的清洗副本。"""
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
        "note": "当前使用原始数据；如需先处理异常记录，请进入数据清洗。",
    }

    if isinstance(clean_frame, pd.DataFrame):
        if clean_source == current_signature:
            source_info.update(
                {
                    "is_clean": True,
                    "note": "当前使用数据清洗后的副本；本页不会修改这些数据。",
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


def _widget_suffix() -> str:
    """为当前数据源生成稳定的控件后缀。"""
    metadata = st.session_state.get(META_KEY, {})
    raw = str(metadata.get("signature") or "default")
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]


def render_header() -> None:
    """渲染空间分析页面标题。"""
    st.markdown(
        """
        <div class="sa-page-head">
            <div class="sa-kicker">Workspace / Spatial Analysis</div>
            <h1 class="sa-title">空间分析</h1>
            <p class="sa-subtitle">
                识别经纬度字段，检查坐标缺失、类型和范围，并把通过检查的有效点绘制到交互式地图。
                本阶段只做坐标检查与点地图，不进行空间连接、缓冲区或坐标转换。
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state() -> None:
    """没有数据时的提示。"""
    st.markdown(
        """
        <section class="sa-empty">
            <div class="sa-empty-kicker">NO DATA YET</div>
            <h3>还没有可进行空间分析的数据</h3>
            <p>
                本页需要包含经纬度字段的 DataFrame。请先在“数据查看”模块上传
                CSV 或 Excel 文件；如果已经完成数据清洗，空间分析会优先使用清洗副本。
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.button(
        "前往数据查看",
        key="spatial_go_to_data_view",
        type="primary",
        on_click=go_to_data_view,
    )


def render_source_card(frame: pd.DataFrame, source_info: dict[str, object]) -> None:
    """显示分析数据来源。"""
    file_name = html.escape(str(source_info.get("file_name", "未命名数据")))
    is_clean = bool(source_info.get("is_clean"))
    badge_text = "清洗后数据" if is_clean else "原始数据"
    badge_class = "clean" if is_clean else "raw"

    st.markdown(
        f"""
        <div class="sa-source-card">
            <div class="sa-source-label">
                SPATIAL SOURCE
                <span class="sa-badge {badge_class}">{badge_text}</span>
            </div>
            <div class="sa-source-name">{file_name}</div>
            <div class="sa-source-meta">
                {len(frame):,} 行 × {frame.shape[1]:,} 列 · 只读分析
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(str(source_info.get("note", "")))
    if source_info.get("warning"):
        st.warning(str(source_info["warning"]))


def render_coordinate_selector(frame: pd.DataFrame) -> tuple[object | None, object | None]:
    """渲染经纬度字段选择器，返回用户选择。"""
    detected_lon, detected_lat = detect_coordinate_columns(frame)
    suffix = _widget_suffix()
    options = [None, *list(frame.columns)]

    with st.container(key="spatial_coord_card"):
        st.markdown(
            """
            <div class="sa-section-kicker">COORDINATE FIELDS</div>
            <h3 class="sa-section-title">选择经纬度字段</h3>
            <p class="sa-section-copy">
                系统会根据字段名给出建议，但字段名不能证明坐标参考系。
                本阶段按 WGS84 经纬度数值范围检查，不做投影转换。
            </p>
            """,
            unsafe_allow_html=True,
        )

        left, right = st.columns(2, gap="large")
        with left:
            lon_index = options.index(detected_lon) if detected_lon in options else 0
            lon_column = st.selectbox(
                "经度字段",
                options=options,
                index=lon_index,
                format_func=lambda value: "请选择字段" if value is None else str(value),
                key=f"spatial_lon_{suffix}",
            )
        with right:
            lat_index = options.index(detected_lat) if detected_lat in options else 0
            lat_column = st.selectbox(
                "纬度字段",
                options=options,
                index=lat_index,
                format_func=lambda value: "请选择字段" if value is None else str(value),
                key=f"spatial_lat_{suffix}",
            )

        if detected_lon is None and detected_lat is None:
            st.info("没有自动识别到经纬度字段，请手动选择。")
        else:
            detected_text = "、".join(
                part
                for part in (
                    f"经度：{detected_lon}" if detected_lon is not None else "",
                    f"纬度：{detected_lat}" if detected_lat is not None else "",
                )
                if part
            )
            st.caption(f"自动建议（仅供参考）：{detected_text}")

        st.markdown(
            '<div class="sa-note">'
            "自动识别仅基于字段名，不代表坐标参考系已经确认；请根据数据来源核对字段。"
            "</div>",
            unsafe_allow_html=True,
        )

    return lon_column, lat_column


def render_quality_check(check: CoordinateCheck) -> None:
    """显示坐标质量统计、有效范围和无效记录。"""
    st.markdown(
        """
        <div class="sa-section-head">
            <div class="sa-section-kicker">QUALITY CHECK</div>
            <h2 class="sa-section-title">坐标质量检查</h2>
            <p class="sa-section-copy">无效记录只展示，不会自动删除，也不会参与地图绘制。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metrics = (
        ("总记录数", f"{check.total_rows:,}", "当前数据全部记录"),
        ("有效坐标点", f"{check.valid_count:,}", "可绘制到地图"),
        ("无效坐标点", f"{check.invalid_count:,}", "未通过坐标检查"),
        ("缺失坐标记录", f"{check.missing_rows:,}", "经度或纬度缺失"),
    )
    columns = st.columns(4, gap="medium")
    for column, (label, value, hint) in zip(columns, metrics):
        with column:
            st.markdown(
                f"""
                <div class="sa-metric">
                    <div class="sa-metric-label">{label}</div>
                    <div class="sa-metric-value">{value}</div>
                    <div class="sa-metric-hint">{hint}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    def format_coordinate(value: float | None) -> str:
        return "—" if value is None else f"{value:.6f}"

    st.markdown(
        f"""
        <div class="sa-range-grid">
            <div class="sa-range-card">
                <div class="sa-range-label">经度最小值</div>
                <div class="sa-range-value">{format_coordinate(check.lon_min)}</div>
            </div>
            <div class="sa-range-card">
                <div class="sa-range-label">经度最大值</div>
                <div class="sa-range-value">{format_coordinate(check.lon_max)}</div>
            </div>
            <div class="sa-range-card">
                <div class="sa-range-label">纬度最小值</div>
                <div class="sa-range-value">{format_coordinate(check.lat_min)}</div>
            </div>
            <div class="sa-range-card">
                <div class="sa-range-label">纬度最大值</div>
                <div class="sa-range-value">{format_coordinate(check.lat_max)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    quality_table = pd.DataFrame(
        {
            "检查项": ["缺失数量", "非数值数量", "超出范围数量"],
            "经度": [
                check.missing_lon,
                check.non_numeric_lon,
                check.out_of_range_lon,
            ],
            "纬度": [
                check.missing_lat,
                check.non_numeric_lat,
                check.out_of_range_lat,
            ],
        }
    )
    st.dataframe(quality_table, width="stretch", hide_index=True)
    st.markdown(
        '<div class="sa-note">'
        "经度有效范围是 -180 到 180，纬度有效范围是 -90 到 90。"
        "范围检查只针对数值坐标，不代表已经确认坐标参考系。"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sa-section-kicker" style="margin-top:1rem;">INVALID RECORDS</div>',
        unsafe_allow_html=True,
    )
    if check.invalid_count == 0:
        st.success("所有记录都通过坐标检查，没有无效坐标点。")
        return

    display_rows = check.invalid_rows.head(50)
    st.warning(
        f"发现 {check.invalid_count:,} 条无效记录。它们不会被自动删除，也不会绘制到地图。"
    )
    display_rows = display_rows.copy()
    for column in display_rows.columns:
        if pd.api.types.is_object_dtype(display_rows[column]):
            display_rows[column] = display_rows[column].map(
                lambda value: "" if pd.isna(value) else str(value)
            )
    st.dataframe(
        display_rows,
        width="stretch",
        hide_index=True,
        height=min(420, 42 + len(display_rows) * 32),
    )
    if check.invalid_count > len(display_rows):
        st.caption(f"仅显示前 {len(display_rows)} 条无效记录，共 {check.invalid_count:,} 条。")


def render_map(
    check: CoordinateCheck,
    frame: pd.DataFrame,
    lon_column: object,
    lat_column: object,
) -> None:
    """显示有效点地图和离线坐标视图。"""
    st.markdown(
        """
        <div class="sa-section-head">
            <div class="sa-section-kicker">POINT MAP</div>
            <h2 class="sa-section-title">交互式点地图</h2>
            <p class="sa-section-copy">只有通过坐标检查的有效点会出现在地图中。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if check.valid_count == 0:
        st.info("没有通过检查的有效坐标点，暂不绘制地图。")
        return

    metadata_fields = [
        column
        for column in frame.columns
        if column not in {lon_column, lat_column}
    ]
    suffix = _widget_suffix()
    coordinate_key = hashlib.sha1(
        f"{lon_column}|{lat_column}".encode("utf-8")
    ).hexdigest()[:8]

    hover_fields = st.multiselect(
        "地图悬停时显示的属性字段",
        options=metadata_fields,
        default=metadata_fields[:3],
        format_func=str,
        key=f"spatial_hover_{suffix}_{coordinate_key}",
    )

    try:
        map_figure = build_map_figure(check.valid_points, hover_fields)
        offline_figure = build_offline_figure(check.valid_points, hover_fields)
    except SpatialError as exc:
        st.error(str(exc))
        return
    except Exception as exc:
        st.error(f"地图构建失败：{exc}")
        return

    map_tab, offline_tab = st.tabs(["交互式地图", "离线坐标视图"])
    with map_tab:
        st.markdown(
            '<div class="sa-map-note">'
            "底图使用 OpenStreetMap 免费瓦片，不需要 token；如果当前网络无法加载底图，"
            "请切换到“离线坐标视图”。"
            "</div>",
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            map_figure,
            width="stretch",
            config={"displaylogo": False, "scrollZoom": True},
        )
    with offline_tab:
        st.markdown(
            '<div class="sa-map-note">'
            "不加载任何外部底图，仅用经纬度绘制点，适合离线环境。"
            "</div>",
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            offline_figure,
            width="stretch",
            config={"displaylogo": False, "scrollZoom": True},
        )

    st.caption(
        f"地图包含 {check.valid_count:,} 个有效点。无效记录不会自动删除，也不会被绘制。"
    )


def render_spatial() -> None:
    """空间分析第一阶段页面入口。"""
    st.markdown(SPATIAL_STYLE, unsafe_allow_html=True)
    render_header()

    frame, source_info = resolve_spatial_data()
    if frame is None:
        render_empty_state()
        return

    render_source_card(frame, source_info)
    lon_column, lat_column = render_coordinate_selector(frame)

    if lon_column is None or lat_column is None:
        st.info("请同时选择经度字段和纬度字段，才能进行坐标检查。")
        return

    if lon_column == lat_column:
        st.error("经度字段和纬度字段不能是同一个字段，请重新选择。")
        return

    try:
        check = validate_coordinates(frame, lon_column, lat_column)
    except SpatialError as exc:
        st.error(str(exc))
        return

    render_quality_check(check)
    render_map(check, frame, lon_column, lat_column)

    st.markdown(
        '<p class="sa-footer">GeoData Studio · 空间分析第一阶段 · 坐标检查与点地图</p>',
        unsafe_allow_html=True,
    )
