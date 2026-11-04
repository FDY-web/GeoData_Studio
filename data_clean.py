from __future__ import annotations

import hashlib
import html
import io
import re

import pandas as pd
import streamlit as st

from data_view import DATA_KEY, META_KEY

CLEAN_KEY = "data_clean_dataframe"
CLEAN_SOURCE_KEY = "data_clean_source_signature"
CLEAN_FLASH_KEY = "data_clean_flash"

TARGET_TYPES = ("文本", "整数", "小数", "日期时间", "布尔值")
TRUE_VALUES = {"true", "1", "是", "yes", "y", "真"}
FALSE_VALUES = {"false", "0", "否", "no", "n", "假"}


class CleaningError(Exception):
    """数据清洗操作无法完成时抛出的业务异常。"""


CLEAN_STYLE = """
<style>
.dc-page-head {
    margin: 0.2rem 0 1.25rem;
}

.dc-kicker {
    color: #0d9488;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.16em;
    text-transform: uppercase;
}

.dc-title {
    margin: 0.28rem 0 0.5rem;
    color: #0b1f2a;
    font-size: 2rem;
    line-height: 1.25;
    letter-spacing: -0.03em;
}

.dc-subtitle {
    max-width: 800px;
    margin: 0;
    color: #5d7471;
    font-size: 0.9rem;
    line-height: 1.8;
}

.dc-source-card {
    padding: 1.1rem 1.2rem;
    border: 1px solid #cfe7e1;
    border-radius: 14px;
    background: linear-gradient(120deg, #f0fdfa, #ffffff);
}

.dc-source-label {
    color: #0d9488;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.13em;
    text-transform: uppercase;
}

.dc-source-name {
    margin-top: 0.25rem;
    color: #0b1f2a;
    font-size: 1.16rem;
    font-weight: 700;
    line-height: 1.4;
    overflow-wrap: anywhere;
}

.dc-source-meta {
    margin-top: 0.3rem;
    color: #5d7471;
    font-size: 0.78rem;
    line-height: 1.65;
}

.dc-badge {
    display: inline-block;
    margin-left: 0.45rem;
    padding: 0.16rem 0.5rem;
    border-radius: 999px;
    background: #dcfce7;
    color: #166534;
    font-size: 0.65rem;
    font-weight: 600;
    vertical-align: middle;
}

.st-key-clean_restore_action .stButton > button {
    min-height: 2.35rem;
    border: 1px solid #d8e5e1;
    border-radius: 9px;
    background: #ffffff;
    color: #526a66;
    font-size: 0.78rem;
    font-weight: 600;
}

.st-key-clean_restore_action .stButton > button:hover {
    border-color: #0d9488;
    background: #f0fdfa;
    color: #0f766e;
}

.dc-compare {
    min-height: 112px;
    padding: 0.9rem 1rem;
    border: 1px solid #dbe7e3;
    border-top: 3px solid #0d9488;
    border-radius: 12px;
    background: #ffffff;
    box-shadow: 0 6px 18px rgba(11, 31, 42, 0.035);
}

.dc-compare-label {
    color: #5d7471;
    font-size: 0.72rem;
    letter-spacing: 0.04em;
}

.dc-compare-nums {
    display: flex;
    align-items: baseline;
    gap: 0.4rem;
    margin-top: 0.3rem;
    color: #829590;
    font-size: 0.88rem;
}

.dc-compare-nums strong {
    color: #0b1f2a;
    font-size: 1.45rem;
    line-height: 1.1;
}

.dc-compare-note {
    margin-top: 0.18rem;
    color: #829590;
    font-size: 0.7rem;
}

.dc-section-head {
    margin: 1.8rem 0 0.8rem;
}

.dc-section-kicker {
    color: #0d9488;
    font-size: 0.66rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
}

.dc-section-title {
    margin: 0.2rem 0 0.25rem;
    color: #0b1f2a;
    font-size: 1.35rem;
    letter-spacing: -0.015em;
}

.dc-section-copy {
    margin: 0;
    color: #657b77;
    font-size: 0.82rem;
    line-height: 1.7;
}

.dc-tab-copy {
    margin: 0.1rem 0 0.8rem;
    color: #657b77;
    font-size: 0.82rem;
    line-height: 1.7;
}

.dc-note {
    margin-top: 0.35rem;
    color: #829590;
    font-size: 0.72rem;
    line-height: 1.65;
}

.dc-empty {
    padding: 1.7rem 1.6rem;
    border: 1px solid #dbe7e3;
    border-radius: 16px;
    background: linear-gradient(145deg, #f7fcfb, #ffffff);
}

.dc-empty-kicker {
    color: #0f766e;
    font-size: 0.66rem;
    font-weight: 700;
    letter-spacing: 0.14em;
}

.dc-empty h3 {
    margin: 0.4rem 0 0.4rem;
    color: #0b1f2a;
    font-size: 1.25rem;
}

.dc-empty p {
    max-width: 720px;
    margin: 0 0 0.7rem;
    color: #5d7471;
    font-size: 0.86rem;
    line-height: 1.8;
}

.dc-export-box {
    margin-top: 0.9rem;
    padding: 1rem 1.1rem;
    border: 1px solid #dbe7e3;
    border-radius: 12px;
    background: #ffffff;
}

.dc-export-label {
    color: #0d9488;
    font-size: 0.66rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}

.dc-export-copy {
    margin: 0.25rem 0 0.7rem;
    color: #657b77;
    font-size: 0.8rem;
    line-height: 1.65;
}

.dc-footer {
    margin-top: 2rem;
    padding-top: 1rem;
    border-top: 1px solid #dbe7e3;
    color: #849793;
    font-size: 0.74rem;
}

@media (max-width: 760px) {
    .dc-title {
        font-size: 1.7rem;
    }

    .dc-empty {
        padding: 1.2rem 1.1rem;
    }
}
</style>
"""


def _selected_columns(frame: pd.DataFrame, columns: list[str]) -> list[str]:
    """校验并去重用户选择的字段。"""
    if not columns:
        raise CleaningError("请至少选择一个要处理的字段。")

    selected: list[str] = []
    for column in columns:
        if column not in frame.columns:
            raise CleaningError(f"字段不存在：{column}")
        if column not in selected:
            selected.append(column)
    return selected


def _format_samples(values: list[object]) -> str:
    """把少量异常值格式化为可读提示。"""
    samples = [str(value) for value in values[:3]]
    return "、".join(f"“{sample}”" for sample in samples)


def _parse_boolean(value: object) -> bool:
    """解析常见布尔文本。"""
    key = str(value).strip().lower()
    if key in TRUE_VALUES:
        return True
    if key in FALSE_VALUES:
        return False
    raise CleaningError(f"无法把“{value}”识别为布尔值，请使用 是/否、true/false 或 1/0。")


def _coerce_fill_value(series: pd.Series, raw_value: str) -> object:
    """根据字段类型转换用户输入的填充值。"""
    if pd.api.types.is_bool_dtype(series):
        return _parse_boolean(raw_value)
    if pd.api.types.is_datetime64_any_dtype(series):
        try:
            return pd.to_datetime(raw_value, errors="raise")
        except Exception as exc:
            raise CleaningError("日期时间字段的填充值格式无效，例如应使用 2024-01-01。") from exc
    if pd.api.types.is_numeric_dtype(series):
        try:
            return pd.to_numeric(pd.Series([raw_value]), errors="raise").iloc[0]
        except Exception as exc:
            raise CleaningError("数值字段的填充值必须是有效数字。") from exc
    return raw_value


def build_missing_table(frame: pd.DataFrame) -> pd.DataFrame:
    """生成各字段缺失数量和比例。"""
    rows = []
    total_rows = len(frame)
    for column in frame.columns:
        series = frame[column]
        missing_count = int(series.isna().sum())
        missing_ratio = missing_count / total_rows if total_rows else 0.0
        rows.append(
            {
                "字段名称": str(column),
                "数据类型": str(series.dtype),
                "缺失数量": missing_count,
                "缺失比例": f"{missing_ratio:.2%}",
            }
        )
    return pd.DataFrame(rows, columns=["字段名称", "数据类型", "缺失数量", "缺失比例"])


def frame_metrics(frame: pd.DataFrame) -> dict[str, int]:
    """计算清洗前后对比所需的指标。"""
    return {
        "rows": int(frame.shape[0]),
        "columns": int(frame.shape[1]),
        "missing_cells": int(frame.isna().sum().sum()),
        "duplicate_rows": int(frame.duplicated().sum()),
    }


def delete_missing_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """删除任何字段含缺失值的行。"""
    return frame.dropna(axis=0, how="any").reset_index(drop=True).copy()


def fill_missing_with_stat(
    frame: pd.DataFrame,
    columns: list[str],
    method: str,
) -> pd.DataFrame:
    """使用均值或中位数填充所选数值字段。"""
    if method not in {"mean", "median"}:
        raise CleaningError("不支持的填充方式。")

    selected = _selected_columns(frame, columns)
    result = frame.copy(deep=True)

    for column in selected:
        if not pd.api.types.is_numeric_dtype(result[column]):
            raise CleaningError(f"字段“{column}”不是数值类型，不能使用均值或中位数填充。")

    for column in selected:
        series = result[column]
        if not series.isna().any():
            continue
        statistic = series.mean() if method == "mean" else series.median()
        if pd.isna(statistic):
            raise CleaningError(f"字段“{column}”没有可用的数值，无法计算填充值。")
        result[column] = series.astype("Float64").fillna(statistic)

    return result


def fill_missing_with_value(
    frame: pd.DataFrame,
    columns: list[str],
    raw_value: str,
) -> pd.DataFrame:
    """使用用户指定值填充所选字段。"""
    selected = _selected_columns(frame, columns)
    result = frame.copy(deep=True)

    for column in selected:
        series = result[column]
        if not series.isna().any():
            continue
        fill_value = _coerce_fill_value(series, raw_value)
        try:
            result[column] = series.fillna(fill_value)
        except Exception as exc:
            raise CleaningError(
                f"字段“{column}”无法使用该填充值，请检查字段类型和填充值是否匹配。"
            ) from exc

    return result


def drop_duplicate_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """删除完全重复记录，保留第一次出现的记录。"""
    return frame.drop_duplicates(keep="first").reset_index(drop=True).copy()


def get_text_columns(frame: pd.DataFrame) -> list[str]:
    """识别可以参与文本清理的字段。"""
    return [
        column
        for column in frame.columns
        if pd.api.types.is_object_dtype(frame[column])
        or pd.api.types.is_string_dtype(frame[column])
    ]


def count_text_changes(frame: pd.DataFrame, columns: list[str]) -> int:
    """统计所选字段中有首尾空格的文本单元格数量。"""
    total = 0
    for column in columns:
        series = frame[column]
        total += int(series.map(lambda value: isinstance(value, str) and value != value.strip()).sum())
    return total


def strip_text_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """只清理所选文本字段的首尾空格。"""
    selected = _selected_columns(frame, columns)
    result = frame.copy(deep=True)

    for column in selected:
        series = result[column]
        if not (
            pd.api.types.is_object_dtype(series)
            or pd.api.types.is_string_dtype(series)
        ):
            raise CleaningError(f"字段“{column}”不是文本类型，不能进行文本清理。")

        if isinstance(series.dtype, pd.StringDtype):
            result[column] = series.str.strip()
        else:
            result[column] = series.map(
                lambda value: value.strip() if isinstance(value, str) else value
            )

    return result


def convert_column_type(
    frame: pd.DataFrame,
    column: str,
    target_type: str,
) -> pd.DataFrame:
    """把单个字段转换为指定类型，失败时不返回部分结果。"""
    if column not in frame.columns:
        raise CleaningError(f"字段不存在：{column}")
    if target_type not in TARGET_TYPES:
        raise CleaningError("不支持的目标类型。")

    result = frame.copy(deep=True)
    series = result[column]

    try:
        if target_type == "文本":
            result[column] = series.astype("string")

        elif target_type in {"整数", "小数"}:
            if pd.api.types.is_datetime64_any_dtype(series):
                raise CleaningError("日期时间字段不能直接转换为数字，请先转换为文本。")

            numeric = pd.to_numeric(series, errors="coerce")
            invalid_mask = numeric.isna() & series.notna()
            if invalid_mask.any():
                samples = series[invalid_mask].head(3).tolist()
                raise CleaningError(
                    f"字段“{column}”有 {int(invalid_mask.sum())} 个值无法转换为数字，"
                    f"例如：{_format_samples(samples)}"
                )

            if target_type == "整数":
                non_integer_mask = numeric.dropna() % 1 != 0
                if non_integer_mask.any():
                    samples = numeric.dropna()[non_integer_mask].head(3).tolist()
                    raise CleaningError(
                        f"字段“{column}”包含小数，不能安全转换为整数，"
                        f"例如：{_format_samples(samples)}"
                    )
                result[column] = numeric.astype("Int64")
            else:
                result[column] = numeric.astype("Float64")

        elif target_type == "日期时间":
            if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
                raise CleaningError("数值字段不能直接转换为日期时间，请先转换为文本。")

            converted = pd.to_datetime(series, errors="coerce")
            invalid_mask = converted.isna() & series.notna()
            if invalid_mask.any():
                samples = series[invalid_mask].head(3).tolist()
                raise CleaningError(
                    f"字段“{column}”有 {int(invalid_mask.sum())} 个值无法转换为日期时间，"
                    f"例如：{_format_samples(samples)}"
                )
            result[column] = converted

        elif target_type == "布尔值":
            converted_values: list[object] = []
            invalid_values: list[object] = []
            for value in series:
                if pd.isna(value):
                    converted_values.append(pd.NA)
                    continue
                key = str(value).strip().lower()
                if key in TRUE_VALUES:
                    converted_values.append(True)
                elif key in FALSE_VALUES:
                    converted_values.append(False)
                else:
                    invalid_values.append(value)
                    converted_values.append(pd.NA)

            if invalid_values:
                raise CleaningError(
                    f"字段“{column}”有 {len(invalid_values)} 个值无法转换为布尔值，"
                    f"例如：{_format_samples(invalid_values)}"
                )
            result[column] = pd.Series(
                converted_values,
                index=result.index,
                dtype="boolean",
            )

    except CleaningError:
        raise
    except Exception as exc:
        raise CleaningError(f"字段“{column}”转换失败：{exc}") from exc

    return result


def dataframe_to_csv_bytes(frame: pd.DataFrame) -> bytes:
    """导出清洗后 CSV，使用带 BOM 的 UTF-8 方便 Excel 打开。"""
    return frame.to_csv(index=False).encode("utf-8-sig")


def dataframe_to_excel_bytes(frame: pd.DataFrame) -> bytes:
    """导出清洗后 Excel 工作簿。"""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        frame.to_excel(writer, sheet_name="清洗结果", index=False)
    return buffer.getvalue()


def make_export_filename(source_name: str, extension: str) -> str:
    """生成安全的清洗结果文件名。"""
    base_name = re.split(r"[\\/]", str(source_name))[-1]
    stem = base_name.rsplit(".", 1)[0] if "." in base_name else base_name
    safe_stem = re.sub(r'[<>:"/\\|?*]+', "_", stem).strip(". ") or "geodata"
    return f"{safe_stem}_cleaned.{extension.lstrip('.')}"


def restore_copy(original: pd.DataFrame) -> pd.DataFrame:
    """返回原始数据的独立深拷贝。"""
    return original.copy(deep=True)


def get_original_frame() -> pd.DataFrame | None:
    """读取数据查看模块保存的原始数据，不复制也不修改。"""
    frame = st.session_state.get(DATA_KEY)
    return frame if isinstance(frame, pd.DataFrame) else None


def get_source_signature(frame: pd.DataFrame) -> str:
    """获取当前原始数据源标识。"""
    metadata = st.session_state.get(META_KEY, {})
    signature = metadata.get("signature")
    if signature:
        return str(signature)
    file_name = metadata.get("file_name", "dataset")
    return f"{file_name}:{frame.shape[0]}x{frame.shape[1]}"


def clear_clean_state() -> None:
    """清除清洗副本及相关状态。"""
    st.session_state.pop(CLEAN_KEY, None)
    st.session_state.pop(CLEAN_SOURCE_KEY, None)
    st.session_state.pop(CLEAN_FLASH_KEY, None)


def ensure_clean_state() -> pd.DataFrame | None:
    """确保原始数据存在，并为其维护一个独立的清洗副本。"""
    original = get_original_frame()
    if original is None:
        clear_clean_state()
        return None

    signature = get_source_signature(original)
    clean_frame = st.session_state.get(CLEAN_KEY)
    if (
        not isinstance(clean_frame, pd.DataFrame)
        or st.session_state.get(CLEAN_SOURCE_KEY) != signature
    ):
        st.session_state[CLEAN_KEY] = restore_copy(original)
        st.session_state[CLEAN_SOURCE_KEY] = signature
        st.session_state[CLEAN_FLASH_KEY] = (
            "info",
            "已从数据查看模块创建独立清洗副本。原始数据保持不变。",
        )

    return st.session_state[CLEAN_KEY]


def set_flash(level: str, message: str) -> None:
    """记录下一次页面渲染要显示的提示。"""
    st.session_state[CLEAN_FLASH_KEY] = (level, message)


def show_flash() -> None:
    """显示并清除一次性提示。"""
    flash = st.session_state.pop(CLEAN_FLASH_KEY, None)
    if not flash:
        return
    level, message = flash
    if level == "success":
        st.success(message)
    elif level == "warning":
        st.warning(message)
    else:
        st.info(message)


def restore_original_callback() -> None:
    """恢复原始数据副本，不修改原始数据。"""
    original = get_original_frame()
    if original is None:
        return

    st.session_state[CLEAN_KEY] = restore_copy(original)
    st.session_state[CLEAN_SOURCE_KEY] = get_source_signature(original)
    set_flash("success", "已恢复为原始数据副本，原始数据没有被修改。")


def go_to_data_view() -> None:
    """按钮回调：跳转到数据查看。"""
    st.session_state.nav_page = "数据查看"


def commit_clean_frame(frame: pd.DataFrame, message: str) -> None:
    """保存清洗结果并刷新页面。"""
    st.session_state[CLEAN_KEY] = frame
    set_flash("success", message)
    st.rerun()


def _widget_suffix() -> str:
    """为当前数据源生成稳定的控件后缀，换文件时重置控件状态。"""
    metadata = st.session_state.get(META_KEY, {})
    raw = str(metadata.get("signature") or "default")
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]


def render_header() -> None:
    """渲染页面标题。"""
    st.markdown(
        """
        <div class="dc-page-head">
            <div class="dc-kicker">Workspace / Data Cleaning</div>
            <h1 class="dc-title">数据清洗</h1>
            <p class="dc-subtitle">
                所有清洗操作只作用于独立副本，原始数据始终保留。
                每一步都可以通过“恢复原始数据”撤销。
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state() -> None:
    """没有上传数据时的提示。"""
    st.markdown(
        """
        <section class="dc-empty">
            <div class="dc-empty-kicker">NO DATA YET</div>
            <h3>还没有可清洗的数据</h3>
            <p>
                数据清洗需要使用“数据查看”模块成功读取的 DataFrame。
                请先上传 CSV 或 Excel 文件，再返回本页面。
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.button(
        "前往数据查看",
        key="go_to_data_view",
        type="primary",
        on_click=go_to_data_view,
    )


def render_source_summary(original: pd.DataFrame, clean: pd.DataFrame, metadata: dict) -> None:
    """显示数据源、原始数据和清洗副本状态。"""
    file_name = html.escape(str(metadata.get("file_name", "未命名数据")))
    source_column, action_column = st.columns([4, 1], gap="medium")

    with source_column:
        st.markdown(
            f"""
            <div class="dc-source-card">
                <div class="dc-source-label">
                    SOURCE / READ-ONLY
                    <span class="dc-badge">原始数据基准</span>
                </div>
                <div class="dc-source-name">{file_name}</div>
                <div class="dc-source-meta">
                    原始：{len(original):,} 行 × {original.shape[1]:,} 列 ·
                    清洗副本：{len(clean):,} 行 × {clean.shape[1]:,} 列
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with action_column:
        with st.container(key="clean_restore_action"):
            st.button(
                "恢复原始数据",
                key="restore_original_data",
                width="stretch",
                on_click=restore_original_callback,
            )
    st.caption("恢复操作只会重置清洗副本，不会修改数据查看模块中的原始数据。")


def render_comparison(original: pd.DataFrame, clean: pd.DataFrame) -> None:
    """显示清洗前后的数据规模和质量指标。"""
    before = frame_metrics(original)
    after = frame_metrics(clean)
    items = (
        ("数据行数", before["rows"], after["rows"]),
        ("字段数量", before["columns"], after["columns"]),
        ("缺失值总数", before["missing_cells"], after["missing_cells"]),
        ("完全重复记录", before["duplicate_rows"], after["duplicate_rows"]),
    )

    columns = st.columns(4, gap="medium")
    for column, (label, before_value, after_value) in zip(columns, items):
        delta = after_value - before_value
        if delta == 0:
            trend = "与原始数据相同"
        elif delta > 0:
            trend = f"增加 {delta:,}"
        else:
            trend = f"减少 {abs(delta):,}"

        with column:
            st.markdown(
                f"""
                <div class="dc-compare">
                    <div class="dc-compare-label">{label}</div>
                    <div class="dc-compare-nums">
                        <span>{before_value:,} →</span>
                        <strong>{after_value:,}</strong>
                    </div>
                    <div class="dc-compare-note">原始 → 当前 · {trend}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_missing_tab(frame: pd.DataFrame, suffix: str) -> None:
    """缺失值检查与处理。"""
    st.markdown(
        """
        <div class="dc-section-kicker">MISSING VALUES</div>
        <h3 class="dc-section-title">缺失值检查与处理</h3>
        <p class="dc-tab-copy">
            查看各字段的缺失数量和比例，然后只对选中的字段执行处理。
        </p>
        """,
        unsafe_allow_html=True,
    )

    missing_table = build_missing_table(frame)
    st.dataframe(
        missing_table,
        width="stretch",
        hide_index=True,
        height=min(260, 42 + max(len(missing_table), 2) * 32),
    )

    method = st.selectbox(
        "缺失值处理方式",
        options=("删除含缺失值的行", "均值填充", "中位数填充", "指定值填充"),
        key=f"missing_method_{suffix}",
    )

    if method == "删除含缺失值的行":
        rows_with_missing = int(frame.isna().any(axis=1).sum())
        if rows_with_missing == 0:
            st.info("当前数据没有缺失值，无需删除行。")
            return

        st.warning(
            f"此操作会删除 {rows_with_missing} 行包含缺失值的记录，"
            "并且无法只恢复这些行；可以通过“恢复原始数据”整体撤销。"
        )
        confirmed = st.checkbox(
            f"我确认删除这 {rows_with_missing} 行",
            key=f"confirm_missing_delete_{suffix}",
        )
        if st.button(
            f"删除 {rows_with_missing} 行",
            key=f"apply_missing_delete_{suffix}",
            disabled=not confirmed,
        ):
            updated = delete_missing_rows(frame)
            commit_clean_frame(updated, f"已删除 {rows_with_missing} 行含缺失值的记录。")
        return

    if method in {"均值填充", "中位数填充"}:
        numeric_columns = [
            column
            for column in frame.columns
            if pd.api.types.is_numeric_dtype(frame[column])
        ]
        if not numeric_columns:
            st.info("当前数据没有数值字段，无法使用均值或中位数填充。")
            return

        fields = st.multiselect(
            "选择数值字段",
            options=numeric_columns,
            format_func=str,
            key=f"missing_numeric_fields_{suffix}",
        )
        missing_selected = int(frame[fields].isna().sum().sum()) if fields else 0
        if fields:
            st.caption(f"所选字段共有 {missing_selected:,} 个缺失值。")
        st.markdown(
            '<div class="dc-note">只处理所选数值字段；整数字段在填充后可能变为浮点类型。</div>',
            unsafe_allow_html=True,
        )

        if st.button(
            f"应用{method}",
            key=f"apply_missing_stat_{suffix}",
            disabled=not fields or missing_selected == 0,
        ):
            try:
                updated = fill_missing_with_stat(frame, fields, "mean" if method == "均值填充" else "median")
            except CleaningError as exc:
                st.error(str(exc))
            else:
                commit_clean_frame(updated, f"已使用{method}填充 {len(fields)} 个字段。")
        return

    fields = st.multiselect(
        "选择要填充的字段",
        options=list(frame.columns),
        format_func=str,
        key=f"missing_fill_fields_{suffix}",
    )
    fill_value = st.text_input(
        "填充值",
        value="",
        placeholder="例如：0、未知、2024-01-01",
        key=f"missing_fill_value_{suffix}",
    )
    missing_selected = int(frame[fields].isna().sum().sum()) if fields else 0
    if fields:
        st.caption(f"所选字段共有 {missing_selected:,} 个缺失值。")
    st.warning("只会修改所选字段中的缺失值，不会自动处理其他字段。")

    if st.button(
        "应用指定值填充",
        key=f"apply_missing_value_{suffix}",
        disabled=not fields or missing_selected == 0,
    ):
        try:
            updated = fill_missing_with_value(frame, fields, fill_value)
        except CleaningError as exc:
            st.error(str(exc))
        else:
            commit_clean_frame(updated, f"已使用指定值填充 {len(fields)} 个字段。")


def render_duplicate_tab(frame: pd.DataFrame, suffix: str) -> None:
    """完全重复记录处理。"""
    st.markdown(
        """
        <div class="dc-section-kicker">DUPLICATES</div>
        <h3 class="dc-section-title">重复记录处理</h3>
        <p class="dc-tab-copy">
            删除所有字段完全相同的记录，并保留第一次出现的那一行。
        </p>
        """,
        unsafe_allow_html=True,
    )

    duplicate_count = int(frame.duplicated().sum())
    if duplicate_count == 0:
        st.info("当前数据没有完全重复记录。")
        return

    st.warning(
        f"此操作会删除 {duplicate_count} 行完全重复记录，并保留第一次出现的记录。"
    )
    confirmed = st.checkbox(
        f"我确认删除这 {duplicate_count} 行",
        key=f"confirm_duplicates_{suffix}",
    )
    if st.button(
        f"删除 {duplicate_count} 行重复记录",
        key=f"apply_duplicates_{suffix}",
        disabled=not confirmed,
    ):
        updated = drop_duplicate_rows(frame)
        commit_clean_frame(updated, f"已删除 {duplicate_count} 行完全重复记录。")


def render_text_tab(frame: pd.DataFrame, suffix: str) -> None:
    """文本字段首尾空格清理。"""
    st.markdown(
        """
        <div class="dc-section-kicker">TEXT CLEANING</div>
        <h3 class="dc-section-title">文本清理</h3>
        <p class="dc-tab-copy">
            去除所选文本字段的首尾空格，不修改数字、日期或其他未选字段。
        </p>
        """,
        unsafe_allow_html=True,
    )

    text_columns = get_text_columns(frame)
    if not text_columns:
        st.info("当前数据没有可清理的文本字段。")
        return

    fields = st.multiselect(
        "选择文本字段",
        options=text_columns,
        format_func=str,
        key=f"text_fields_{suffix}",
    )
    change_count = count_text_changes(frame, fields) if fields else 0
    if fields:
        st.caption(f"所选字段共有 {change_count:,} 个单元格包含首尾空格。")
    st.markdown(
        '<div class="dc-note">只处理列表中选中的字段，其他字段保持不变。</div>',
        unsafe_allow_html=True,
    )

    if st.button(
        "去除所选字段首尾空格",
        key=f"apply_text_{suffix}",
        disabled=not fields or change_count == 0,
    ):
        try:
            updated = strip_text_columns(frame, fields)
        except CleaningError as exc:
            st.error(str(exc))
        else:
            commit_clean_frame(updated, f"已清理 {len(fields)} 个文本字段。")


def render_type_tab(frame: pd.DataFrame, suffix: str) -> None:
    """单字段类型转换。"""
    st.markdown(
        """
        <div class="dc-section-kicker">TYPE CONVERSION</div>
        <h3 class="dc-section-title">字段类型转换</h3>
        <p class="dc-tab-copy">
            每次只转换一个字段。转换失败时不会写入任何部分结果，当前数据保持不变。
        </p>
        """,
        unsafe_allow_html=True,
    )

    if frame.shape[1] == 0:
        st.info("当前数据没有可转换的字段。")
        return

    field = st.selectbox(
        "选择字段",
        options=list(frame.columns),
        format_func=str,
        key=f"type_field_{suffix}",
    )
    current_dtype = frame[field].dtype
    st.caption(f"当前类型：{current_dtype}")

    target_type = st.selectbox(
        "目标类型",
        options=TARGET_TYPES,
        key=f"type_target_{suffix}",
    )
    st.markdown(
        '<div class="dc-note">支持转换为文本、整数、小数、日期时间和布尔值。</div>',
        unsafe_allow_html=True,
    )

    if st.button("转换字段类型", key=f"apply_type_{suffix}"):
        try:
            updated = convert_column_type(frame, field, target_type)
        except CleaningError as exc:
            st.error(str(exc))
        else:
            commit_clean_frame(updated, f"已把字段“{field}”转换为{target_type}。")


def render_comparison_section(original: pd.DataFrame, clean: pd.DataFrame) -> None:
    """渲染清洗前后对比区域。"""
    st.markdown(
        """
        <div class="dc-section-head">
            <div class="dc-section-kicker">BEFORE / AFTER</div>
            <h2 class="dc-section-title">清洗前后对比</h2>
            <p class="dc-section-copy">左侧数字为原始数据，右侧数字为当前清洗副本。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_comparison(original, clean)


def render_actions(clean: pd.DataFrame, suffix: str) -> None:
    """渲染四类清洗操作的选项卡。"""
    st.markdown(
        """
        <div class="dc-section-head">
            <div class="dc-section-kicker">CLEANING TOOLS</div>
            <h2 class="dc-section-title">清洗操作</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    missing_tab, duplicate_tab, text_tab, type_tab = st.tabs(
        ["缺失值", "重复记录", "文本清理", "类型转换"]
    )
    with missing_tab:
        render_missing_tab(clean, suffix)
    with duplicate_tab:
        render_duplicate_tab(clean, suffix)
    with text_tab:
        render_text_tab(clean, suffix)
    with type_tab:
        render_type_tab(clean, suffix)


def render_preview_and_export(clean: pd.DataFrame, metadata: dict) -> None:
    """显示清洗后预览和导出按钮。"""
    st.markdown(
        """
        <div class="dc-section-head">
            <div class="dc-section-kicker">RESULT</div>
            <h2 class="dc-section-title">清洗后数据预览</h2>
            <p class="dc-section-copy">仅显示前 20 行；导出内容为当前清洗副本。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if clean.empty:
        st.info("当前清洗副本没有数据行。")
    else:
        st.dataframe(
            clean.head(20),
            width="stretch",
            height=min(460, 44 + max(min(len(clean), 20), 2) * 32),
        )
        st.caption(f"共 {len(clean):,} 行 × {clean.shape[1]:,} 列，显示前 {min(len(clean), 20)} 行。")

    st.markdown(
        """
        <div class="dc-export-box">
            <div class="dc-export-label">EXPORT</div>
            <div class="dc-export-copy">
                导出当前清洗结果，不会导出原始数据。CSV 使用 UTF-8-SIG，
                Excel 工作簿包含一个“清洗结果”工作表。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    base_name = metadata.get("file_name", "geodata.csv")
    export_columns = st.columns(2, gap="medium")

    try:
        csv_bytes = dataframe_to_csv_bytes(clean)
    except Exception as exc:
        csv_bytes = None
        with export_columns[0]:
            st.error(f"CSV 导出准备失败：{exc}")
    if csv_bytes is not None:
        with export_columns[0]:
            st.download_button(
                "下载清洗后 CSV",
                data=csv_bytes,
                file_name=make_export_filename(base_name, "csv"),
                mime="text/csv",
                key="download_clean_csv",
                width="stretch",
            )

    try:
        excel_bytes = dataframe_to_excel_bytes(clean)
    except Exception as exc:
        excel_bytes = None
        with export_columns[1]:
            st.error(f"Excel 导出准备失败：{exc}")
    if excel_bytes is not None:
        with export_columns[1]:
            st.download_button(
                "下载清洗后 Excel",
                data=excel_bytes,
                file_name=make_export_filename(base_name, "xlsx"),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_clean_excel",
                width="stretch",
            )

    st.markdown(
        '<p class="dc-footer">GeoData Studio · 数据清洗 · 原始数据保持不变</p>',
        unsafe_allow_html=True,
    )


def render_data_clean() -> None:
    """数据清洗页面入口。"""
    st.markdown(CLEAN_STYLE, unsafe_allow_html=True)
    render_header()

    original = ensure_clean_state()
    if original is None:
        render_empty_state()
        return

    show_flash()
    clean = st.session_state[CLEAN_KEY]
    metadata = st.session_state.get(META_KEY, {})
    suffix = _widget_suffix()

    render_source_summary(original, clean, metadata)
    st.markdown("<div style='height: 0.8rem;'></div>", unsafe_allow_html=True)
    render_comparison_section(original, clean)
    render_actions(clean, suffix)
    render_preview_and_export(clean, metadata)
