from __future__ import annotations

import hashlib
import html
import importlib.util
import io

import pandas as pd
import streamlit as st

DATA_KEY = "data_view_dataframe"
META_KEY = "data_view_metadata"
FAILED_SIGNATURE_KEY = "data_view_failed_signature"
FAILED_MESSAGE_KEY = "data_view_failed_message"
UPLOADER_VERSION_KEY = "data_view_uploader_version"

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
CSV_ENCODINGS = ("utf-8-sig", "utf-8", "gbk", "gb18030")
PREVIEW_ROWS = 20


class DataReadError(Exception):
    """用户上传的数据无法读取时抛出的业务异常。"""


DATA_VIEW_STYLE = """
<style>
.dv-page-head {
    margin: 0.2rem 0 1.35rem;
}

.dv-kicker {
    color: #0d9488;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.16em;
    text-transform: uppercase;
}

.dv-title {
    margin: 0.28rem 0 0.5rem;
    color: #0b1f2a;
    font-size: 2rem;
    line-height: 1.25;
    letter-spacing: -0.03em;
}

.dv-subtitle {
    max-width: 780px;
    margin: 0;
    color: #5d7471;
    font-size: 0.9rem;
    line-height: 1.8;
}

.st-key-data_upload_card {
    margin-bottom: 1.2rem;
    padding: 1.2rem 1.3rem 0.9rem;
    border: 1px solid #dbe7e3;
    border-radius: 16px;
    background: #ffffff;
    box-shadow: 0 9px 26px rgba(11, 31, 42, 0.04);
}

.dv-step {
    color: #0d9488;
    font-family: Consolas, "Courier New", monospace;
    font-size: 0.66rem;
    font-weight: 700;
    letter-spacing: 0.13em;
}

.dv-upload-title {
    margin: 0.3rem 0 0.35rem;
    color: #0b1f2a;
    font-size: 1.1rem;
}

.dv-upload-copy {
    margin: 0 0 0.8rem;
    color: #5d7471;
    font-size: 0.84rem;
    line-height: 1.7;
}

[data-testid="stFileUploaderDropzone"] {
    border: 1px dashed #c7e7df;
    border-radius: 12px;
    background: #f8fcfb;
}

.st-key-data_upload_card [data-testid="stFileUploader"] label p {
    color: #0b1f2a;
    font-weight: 600;
}

.dv-empty {
    margin-top: 0.2rem;
    padding: 1.5rem 1.6rem;
    border: 1px solid #dbe7e3;
    border-radius: 16px;
    background: linear-gradient(145deg, #f7fcfb, #ffffff);
}

.dv-empty-kicker {
    color: #0f766e;
    font-size: 0.66rem;
    font-weight: 700;
    letter-spacing: 0.14em;
}

.dv-empty h3 {
    margin: 0.4rem 0 0.35rem;
    color: #0b1f2a;
    font-size: 1.2rem;
}

.dv-empty-copy {
    max-width: 760px;
    margin: 0;
    color: #5d7471;
    font-size: 0.86rem;
    line-height: 1.8;
}

.dv-steps {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.75rem;
    margin-top: 1.1rem;
}

.dv-step-item {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.75rem 0.8rem;
    border: 1px solid #e2ece9;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.72);
}

.dv-step-number {
    color: #0d9488;
    font-family: Consolas, "Courier New", monospace;
    font-size: 0.72rem;
    font-weight: 700;
}

.dv-step-item strong {
    display: block;
    color: #0b1f2a;
    font-size: 0.82rem;
}

.dv-step-item small {
    display: block;
    margin-top: 0.1rem;
    color: #7d918d;
    font-size: 0.7rem;
}

.dv-file-card {
    padding: 1.1rem 1.2rem;
    border: 1px solid #cfe7e1;
    border-radius: 14px;
    background: linear-gradient(120deg, #f0fdfa, #ffffff);
}

.dv-file-label {
    color: #0d9488;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.13em;
    text-transform: uppercase;
}

.dv-file-name {
    margin-top: 0.25rem;
    color: #0b1f2a;
    font-size: 1.18rem;
    font-weight: 700;
    line-height: 1.4;
    overflow-wrap: anywhere;
}

.dv-file-meta {
    margin-top: 0.3rem;
    color: #5d7471;
    font-size: 0.78rem;
    line-height: 1.6;
    overflow-wrap: anywhere;
}

.st-key-data_clear_action .stButton > button {
    min-height: 2.35rem;
    border: 1px solid #d8e5e1;
    border-radius: 9px;
    background: #ffffff;
    color: #6b7f7b;
    font-size: 0.78rem;
    font-weight: 600;
}

.st-key-data_clear_action .stButton > button:hover {
    border-color: #d9a6a0;
    background: #fff7f6;
    color: #a33d32;
}

.dv-kpi {
    min-height: 104px;
    padding: 0.9rem 1rem;
    border: 1px solid #dbe7e3;
    border-top: 3px solid #0d9488;
    border-radius: 12px;
    background: #ffffff;
    box-shadow: 0 6px 18px rgba(11, 31, 42, 0.035);
}

.dv-kpi-label {
    color: #5d7471;
    font-size: 0.72rem;
    letter-spacing: 0.04em;
}

.dv-kpi-value {
    margin-top: 0.28rem;
    color: #0b1f2a;
    font-size: 1.45rem;
    font-weight: 700;
    line-height: 1.2;
}

.dv-kpi-hint {
    margin-top: 0.14rem;
    color: #829590;
    font-size: 0.7rem;
}

.dv-session-note {
    margin: 0.2rem 0 0.9rem;
    color: #738883;
    font-size: 0.76rem;
    line-height: 1.6;
}

.dv-table-caption {
    margin: 0.15rem 0 0.55rem;
    color: #738883;
    font-size: 0.76rem;
}

.dv-table-hint {
    margin-top: 0.55rem;
    color: #829590;
    font-size: 0.72rem;
    line-height: 1.65;
}

@media (max-width: 760px) {
    .dv-title {
        font-size: 1.7rem;
    }

    .dv-steps {
        grid-template-columns: 1fr;
    }

    .dv-empty {
        padding: 1.2rem 1.1rem;
    }
}
</style>
"""


def make_file_signature(file_name: str, data: bytes) -> str:
    """用文件名、大小和内容哈希标识一次上传，避免重复解析同一文件。"""
    digest = hashlib.sha256(data).hexdigest()
    return f"{file_name.lower()}:{len(data)}:{digest}"


def is_new_upload(signature: str, metadata: dict | None) -> bool:
    """判断当前上传是否与上一次成功读取的文件不同。"""
    return not metadata or metadata.get("signature") != signature


def format_file_size(size_bytes: int) -> str:
    """把字节数格式化为易读大小。"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.2f} MB"


def get_extension(file_name: str) -> str:
    """返回小写扩展名，并拒绝不支持的文件类型。"""
    extension = "." + file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if extension not in SUPPORTED_EXTENSIONS:
        raise DataReadError("不支持该文件格式。请上传 .csv、.xlsx 或 .xls 文件。")
    return extension


def read_csv_bytes(data: bytes) -> tuple[pd.DataFrame, str]:
    """按常见中文编码依次尝试读取 CSV，返回 DataFrame 和实际编码。"""
    if not data or not data.strip():
        raise DataReadError("CSV 文件为空，请上传包含数据的文件。")

    for encoding in CSV_ENCODINGS:
        try:
            frame = pd.read_csv(io.BytesIO(data), encoding=encoding)
            return frame, encoding
        except UnicodeDecodeError:
            continue
        except pd.errors.EmptyDataError as exc:
            raise DataReadError("CSV 文件没有可读取的表格内容。") from exc
        except pd.errors.ParserError as exc:
            raise DataReadError("CSV 格式无法解析，请检查分隔符和列结构。") from exc
        except Exception as exc:
            raise DataReadError(f"CSV 读取失败：{exc}") from exc

    raise DataReadError(
        "无法识别 CSV 文件编码。已尝试 UTF-8、GBK 和 GB18030，请将文件另存为 UTF-8 后重试。"
    )


def read_excel_bytes(
    data: bytes,
    file_name: str,
    sheet_name: str | None = None,
) -> tuple[pd.DataFrame, list[str], str]:
    """读取 Excel 指定工作表，返回数据、工作表列表和实际读取的工作表。"""
    if not data:
        raise DataReadError("Excel 文件为空，请上传包含数据的文件。")

    extension = get_extension(file_name)
    engine = "xlrd" if extension == ".xls" else "openpyxl"

    if extension == ".xls" and importlib.util.find_spec("xlrd") is None:
        raise DataReadError("当前环境缺少 xlrd，无法读取 .xls 文件。")

    try:
        workbook = pd.ExcelFile(io.BytesIO(data), engine=engine)
        sheet_names = list(workbook.sheet_names)
        if not sheet_names:
            raise DataReadError("Excel 文件中没有可读取的工作表。")

        selected_sheet = sheet_name or sheet_names[0]
        if selected_sheet not in sheet_names:
            raise DataReadError(f"找不到工作表：{selected_sheet}")

        frame = workbook.parse(sheet_name=selected_sheet)
        return frame, sheet_names, selected_sheet
    except DataReadError:
        raise
    except Exception as exc:
        raise DataReadError(f"Excel 文件读取失败，请检查文件是否损坏：{exc}") from exc


def summarize_dataframe(frame: pd.DataFrame) -> dict[str, int]:
    """计算数据规模、缺失单元格数和完全重复记录数。"""
    return {
        "rows": int(frame.shape[0]),
        "columns": int(frame.shape[1]),
        "missing_cells": int(frame.isna().sum().sum()),
        "duplicate_rows": int(frame.duplicated().sum()),
    }


def build_schema(frame: pd.DataFrame) -> pd.DataFrame:
    """生成字段类型、非空数量、缺失数量和缺失比例表。"""
    rows = []
    total_rows = len(frame)

    for position, column_name in enumerate(frame.columns):
        series = frame.iloc[:, position]
        missing_count = int(series.isna().sum())
        missing_ratio = missing_count / total_rows if total_rows else 0.0
        rows.append(
            {
                "字段名称": str(column_name),
                "数据类型": str(series.dtype),
                "非空数量": int(series.notna().sum()),
                "缺失数量": missing_count,
                "缺失比例": f"{missing_ratio:.2%}",
            }
        )

    return pd.DataFrame(rows, columns=["字段名称", "数据类型", "非空数量", "缺失数量", "缺失比例"])


def ensure_data_view_state() -> None:
    """初始化数据查看模块自己的会话状态。"""
    if UPLOADER_VERSION_KEY not in st.session_state:
        st.session_state[UPLOADER_VERSION_KEY] = 0


def has_dataset() -> bool:
    """当前会话是否已成功读取过数据。"""
    return DATA_KEY in st.session_state and META_KEY in st.session_state


def clear_dataset() -> None:
    """清除当前会话中的数据集和上传错误。"""
    st.session_state.pop(DATA_KEY, None)
    st.session_state.pop(META_KEY, None)
    st.session_state.pop(FAILED_SIGNATURE_KEY, None)
    st.session_state.pop(FAILED_MESSAGE_KEY, None)


def clear_data_callback() -> None:
    """清除数据，并让下一次渲染使用全新的上传组件。"""
    clear_dataset()
    st.session_state[UPLOADER_VERSION_KEY] = st.session_state.get(UPLOADER_VERSION_KEY, 0) + 1


def store_dataset(frame: pd.DataFrame, metadata: dict) -> None:
    """把成功读取的数据和元信息放入 session_state。"""
    st.session_state[DATA_KEY] = frame
    st.session_state[META_KEY] = metadata


def record_upload_error(signature: str, message: str) -> None:
    """记录失败的上传，避免同一个损坏文件在每次重跑时被反复解析。"""
    st.session_state[FAILED_SIGNATURE_KEY] = signature
    st.session_state[FAILED_MESSAGE_KEY] = message


def render_page_header() -> None:
    """渲染数据查看页标题。"""
    st.markdown(
        """
        <div class="dv-page-head">
            <div class="dv-kicker">Workspace / Data View</div>
            <h1 class="dv-title">数据查看</h1>
            <p class="dv-subtitle">
                上传 CSV 或 Excel 文件，查看文件信息、字段类型、前 20 行数据和质量概况。
                文件只在当前浏览器会话中读取，不会写入服务器磁盘。
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_upload_card() -> st.runtime.uploaded_file_manager.UploadedFile | None:
    """渲染上传卡片，返回用户选择的文件。"""
    uploader_key = f"data_uploader_{st.session_state[UPLOADER_VERSION_KEY]}"

    with st.container(key="data_upload_card"):
        st.markdown(
            """
            <div class="dv-step">01 / UPLOAD</div>
            <h3 class="dv-upload-title">选择一份数据文件</h3>
            <p class="dv-upload-copy">
                支持 CSV、XLSX 和 XLS。CSV 会依次尝试 UTF-8、GBK、GB18030 编码；
                Excel 文件如果有多个工作表，可在上传后选择。
            </p>
            """,
            unsafe_allow_html=True,
        )

        uploaded_file = st.file_uploader(
            "上传 CSV / Excel 文件",
            type=["csv", "xlsx", "xls"],
            key=uploader_key,
            help="单个文件最大 200 MB。上传新文件会替换当前会话中的数据。",
        )

        st.caption("文件仅在当前会话内保存；刷新页面或重启服务后需要重新上传。")

    return uploaded_file


def render_empty_state() -> None:
    """上传前展示操作说明。"""
    st.markdown(
        """
        <section class="dv-empty">
            <div class="dv-empty-kicker">NO DATA YET</div>
            <h3>上传后，这里会显示真实的数据内容</h3>
            <p class="dv-empty-copy">
                数据查看不会生成示例数据。读取成功后，页面会显示文件名、数据规模、
                字段类型、缺失值、重复记录和前 20 行预览。
            </p>
            <div class="dv-steps">
                <div class="dv-step-item">
                    <span class="dv-step-number">01</span>
                    <div><strong>上传文件</strong><small>CSV / XLSX / XLS</small></div>
                </div>
                <div class="dv-step-item">
                    <span class="dv-step-number">02</span>
                    <div><strong>读取数据</strong><small>自动尝试常见编码</small></div>
                </div>
                <div class="dv-step-item">
                    <span class="dv-step-number">03</span>
                    <div><strong>检查结构</strong><small>字段、缺失值与重复行</small></div>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_file_summary(metadata: dict) -> None:
    """显示当前文件信息和清除按钮。"""
    file_name = html.escape(str(metadata.get("file_name", "")))
    file_type = html.escape(str(metadata.get("file_type", "")))
    file_size = format_file_size(int(metadata.get("file_size", 0)))

    meta_parts = [file_type, file_size]
    if metadata.get("sheet_name"):
        meta_parts.append(f"工作表：{metadata['sheet_name']}")
    if metadata.get("encoding"):
        meta_parts.append(f"编码：{str(metadata['encoding']).upper()}")
    meta_text = " · ".join(html.escape(part) for part in meta_parts)

    summary_column, action_column = st.columns([4, 1], gap="medium")
    with summary_column:
        st.markdown(
            f"""
            <div class="dv-file-card">
                <div class="dv-file-label">Current Dataset</div>
                <div class="dv-file-name">{file_name}</div>
                <div class="dv-file-meta">{meta_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with action_column:
        with st.container(key="data_clear_action"):
            st.button(
                "清除数据",
                key="clear_dataset_button",
                width="stretch",
                on_click=clear_data_callback,
            )


def render_kpis(frame: pd.DataFrame) -> None:
    """显示数据规模和质量指标。"""
    summary = summarize_dataframe(frame)
    columns = st.columns(4, gap="medium")
    items = (
        ("数据行数", f"{summary['rows']:,}", "条记录"),
        ("字段数量", f"{summary['columns']:,}", "列"),
        ("缺失单元格", f"{summary['missing_cells']:,}", "按 NaN / None / NaT 统计"),
        ("完全重复记录", f"{summary['duplicate_rows']:,}", "整行完全相同的记录"),
    )

    for column, (label, value, hint) in zip(columns, items):
        with column:
            st.markdown(
                f"""
                <div class="dv-kpi">
                    <div class="dv-kpi-label">{label}</div>
                    <div class="dv-kpi-value">{value}</div>
                    <div class="dv-kpi-hint">{hint}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_preview(frame: pd.DataFrame) -> None:
    """显示前 20 行数据。"""
    preview = frame.head(PREVIEW_ROWS)
    st.markdown(
        f'<div class="dv-table-caption">仅显示前 {len(preview):,} 行，共 {len(frame):,} 行。</div>',
        unsafe_allow_html=True,
    )

    if preview.empty:
        st.info("当前工作表没有数据行。")
        return

    table_height = min(520, 44 + max(len(preview), 2) * 32)
    st.dataframe(preview, width="stretch", height=table_height)
    st.markdown(
        '<div class="dv-table-hint">表格可横向滚动；列较多时建议全屏查看。</div>',
        unsafe_allow_html=True,
    )


def render_schema(frame: pd.DataFrame) -> None:
    """显示字段类型和缺失值统计。"""
    if frame.shape[1] == 0:
        st.info("当前工作表没有字段。")
        return

    schema = build_schema(frame)
    st.dataframe(schema, width="stretch", hide_index=True)
    st.markdown(
        '<div class="dv-table-hint">'
        "缺失值按 pandas 的 NaN / None / NaT 统计；CSV 中的空字段默认按缺失值处理。"
        "</div>",
        unsafe_allow_html=True,
    )


def render_dataset(metadata: dict) -> None:
    """渲染已成功读取的数据。"""
    frame = st.session_state[DATA_KEY]
    render_file_summary(metadata)
    st.markdown(
        '<div class="dv-session-note">'
        "当前数据保存在本次浏览器会话中；切换到其他页面再返回时仍会保留。"
        "</div>",
        unsafe_allow_html=True,
    )
    render_kpis(frame)

    preview_tab, schema_tab = st.tabs(
        [
            f"数据预览（前 {min(len(frame), PREVIEW_ROWS)} 行）",
            f"字段信息（{frame.shape[1]} 列）",
        ]
    )
    with preview_tab:
        render_preview(frame)
    with schema_tab:
        render_schema(frame)


def update_sheet_if_needed(data: bytes, file_name: str, metadata: dict) -> None:
    """Excel 多工作表时显示选择器，并在切换后重新读取。"""
    sheet_names = metadata.get("sheet_names") or []
    if len(sheet_names) <= 1:
        return

    current_sheet = metadata.get("sheet_name")
    current_index = sheet_names.index(current_sheet) if current_sheet in sheet_names else 0
    selected_sheet = st.selectbox(
        "选择工作表",
        options=sheet_names,
        index=current_index,
        key=f"sheet_selector_{metadata['signature'][:16]}",
    )

    if selected_sheet == current_sheet:
        return

    try:
        frame, _, _ = read_excel_bytes(data, file_name, selected_sheet)
        updated_metadata = {
            **metadata,
            "sheet_name": selected_sheet,
            "row_count": int(frame.shape[0]),
            "column_count": int(frame.shape[1]),
        }
        store_dataset(frame, updated_metadata)
        st.success("已切换到所选工作表。")
    except DataReadError as exc:
        st.error(f"工作表读取失败：{exc}")


def process_uploaded_file(uploaded_file: st.runtime.uploaded_file_manager.UploadedFile) -> None:
    """校验并读取上传文件，成功后更新会话中的数据。"""
    data = uploaded_file.getvalue()
    file_name = uploaded_file.name
    signature = make_file_signature(file_name, data)

    if st.session_state.get(FAILED_SIGNATURE_KEY) == signature:
        st.error(st.session_state.get(FAILED_MESSAGE_KEY, "该文件读取失败，请重新上传。"))
        if has_dataset():
            st.info("当前仍显示上一次成功读取的数据。")
        return

    metadata = st.session_state.get(META_KEY)
    if not is_new_upload(signature, metadata):
        if metadata is not None and metadata.get("file_type") == "Excel":
            update_sheet_if_needed(data, file_name, metadata)
        return

    try:
        extension = get_extension(file_name)

        if extension == ".csv":
            frame, encoding = read_csv_bytes(data)
            new_metadata = {
                "signature": signature,
                "file_name": file_name,
                "file_size": len(data),
                "file_type": "CSV",
                "sheet_name": None,
                "sheet_names": [],
                "encoding": encoding,
                "row_count": int(frame.shape[0]),
                "column_count": int(frame.shape[1]),
            }
            store_dataset(frame, new_metadata)
            st.success(f"CSV 读取成功，使用编码：{encoding.upper()}。")
        else:
            frame, sheet_names, selected_sheet = read_excel_bytes(data, file_name)
            new_metadata = {
                "signature": signature,
                "file_name": file_name,
                "file_size": len(data),
                "file_type": "Excel",
                "sheet_name": selected_sheet,
                "sheet_names": sheet_names,
                "encoding": None,
                "row_count": int(frame.shape[0]),
                "column_count": int(frame.shape[1]),
            }
            store_dataset(frame, new_metadata)
            st.success(f"Excel 读取成功，共 {len(sheet_names)} 个工作表。")
            update_sheet_if_needed(data, file_name, st.session_state[META_KEY])

        st.session_state.pop(FAILED_SIGNATURE_KEY, None)
        st.session_state.pop(FAILED_MESSAGE_KEY, None)
    except DataReadError as exc:
        record_upload_error(signature, str(exc))
        st.error(str(exc))
        if has_dataset():
            st.info("当前仍显示上一次成功读取的数据。")
    except Exception as exc:
        message = f"文件读取失败：{exc}"
        record_upload_error(signature, message)
        st.error(message)
        if has_dataset():
            st.info("当前仍显示上一次成功读取的数据。")


def render_data_view() -> None:
    """数据查看页面入口。"""
    ensure_data_view_state()
    st.markdown(DATA_VIEW_STYLE, unsafe_allow_html=True)
    render_page_header()

    uploaded_file = render_upload_card()

    if uploaded_file is not None:
        process_uploaded_file(uploaded_file)

    if has_dataset():
        render_dataset(st.session_state[META_KEY])
    elif uploaded_file is None:
        render_empty_state()
