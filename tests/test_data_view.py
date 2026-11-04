from __future__ import annotations

import io
import unittest

import pandas as pd

try:
    import xlwt
except ImportError:  # 测试环境可选依赖
    xlwt = None

from data_view import (
    DataReadError,
    build_schema,
    format_file_size,
    get_extension,
    is_new_upload,
    make_file_signature,
    read_csv_bytes,
    read_excel_bytes,
    summarize_dataframe,
)


class DataReadingTests(unittest.TestCase):
    def test_read_utf8_csv(self) -> None:
        data = "城市,人口\n北京,2189\n上海,2487\n".encode("utf-8")
        frame, encoding = read_csv_bytes(data)

        self.assertEqual(frame.shape, (2, 2))
        self.assertEqual(list(frame.columns), ["城市", "人口"])
        self.assertEqual(frame.iloc[0, 0], "北京")
        self.assertIn(encoding, {"utf-8-sig", "utf-8"})

    def test_read_gbk_csv(self) -> None:
        data = "城市,人口\n北京,2189\n广州,1882\n".encode("gbk")
        frame, encoding = read_csv_bytes(data)

        self.assertEqual(frame.iloc[0, 0], "北京")
        self.assertEqual(encoding, "gbk")

    def test_empty_csv_is_rejected(self) -> None:
        with self.assertRaises(DataReadError):
            read_csv_bytes(b"")

        with self.assertRaises(DataReadError):
            read_csv_bytes(b"   \n")

    def test_xlsx_multiple_sheets(self) -> None:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            pd.DataFrame({"站点": ["A", "B"], "值": [1, 2]}).to_excel(
                writer, sheet_name="站点表", index=False
            )
            pd.DataFrame({"指标": ["总计"], "值": [3]}).to_excel(
                writer, sheet_name="汇总", index=False
            )

        data = buffer.getvalue()
        frame, sheet_names, selected = read_excel_bytes(data, "multi.xlsx")
        self.assertEqual(sheet_names, ["站点表", "汇总"])
        self.assertEqual(selected, "站点表")
        self.assertEqual(frame.shape, (2, 2))

        second_frame, _, second_selected = read_excel_bytes(data, "multi.xlsx", "汇总")
        self.assertEqual(second_selected, "汇总")
        self.assertEqual(second_frame.iloc[0, 0], "总计")

    @unittest.skipIf(xlwt is None, "xlwt 未安装，跳过 .xls 测试")
    def test_legacy_xls_read(self) -> None:
        workbook = xlwt.Workbook()
        sheet = workbook.add_sheet("旧格式")
        sheet.write(0, 0, "城市")
        sheet.write(0, 1, "人口")
        sheet.write(1, 0, "北京")
        sheet.write(1, 1, 2189)
        buffer = io.BytesIO()
        workbook.save(buffer)

        frame, sheet_names, selected = read_excel_bytes(buffer.getvalue(), "legacy.xls")
        self.assertEqual(sheet_names, ["旧格式"])
        self.assertEqual(selected, "旧格式")
        self.assertEqual(frame.iloc[0, 0], "北京")

    def test_corrupt_excel_is_rejected(self) -> None:
        with self.assertRaises(DataReadError):
            read_excel_bytes(b"this is not an excel file", "broken.xlsx")

    def test_unsupported_extension_is_rejected(self) -> None:
        with self.assertRaises(DataReadError):
            get_extension("data.txt")


class DataSummaryTests(unittest.TestCase):
    def test_schema_and_quality_summary(self) -> None:
        frame = pd.DataFrame(
            {
                "名称": ["A", "B", None, "A"],
                "值": [1, None, 3, 1],
            }
        )

        summary = summarize_dataframe(frame)
        self.assertEqual(summary["rows"], 4)
        self.assertEqual(summary["columns"], 2)
        self.assertEqual(summary["missing_cells"], 2)
        self.assertEqual(summary["duplicate_rows"], 1)

        schema = build_schema(frame)
        name_row = schema[schema["字段名称"] == "名称"].iloc[0]
        self.assertEqual(name_row["数据类型"], "object")
        self.assertEqual(name_row["非空数量"], 3)
        self.assertEqual(name_row["缺失数量"], 1)
        self.assertEqual(name_row["缺失比例"], "25.00%")

    def test_format_file_size(self) -> None:
        self.assertEqual(format_file_size(512), "512 B")
        self.assertEqual(format_file_size(2048), "2.0 KB")
        self.assertEqual(format_file_size(2 * 1024 * 1024), "2.00 MB")


class UploadStateTests(unittest.TestCase):
    def test_reupload_detection(self) -> None:
        first_signature = make_file_signature("data.csv", b"id,value\n1,10\n")
        second_signature = make_file_signature("data.csv", b"id,value\n1,20\n")

        self.assertNotEqual(first_signature, second_signature)
        self.assertTrue(is_new_upload(first_signature, None))
        self.assertFalse(is_new_upload(first_signature, {"signature": first_signature}))
        self.assertTrue(is_new_upload(second_signature, {"signature": first_signature}))


if __name__ == "__main__":
    unittest.main()
