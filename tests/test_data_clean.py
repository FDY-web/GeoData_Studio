from __future__ import annotations

import io
import unittest

import pandas as pd

from data_clean import (
    CleaningError,
    build_missing_table,
    convert_column_type,
    count_text_changes,
    dataframe_to_csv_bytes,
    dataframe_to_excel_bytes,
    delete_missing_rows,
    drop_duplicate_rows,
    fill_missing_with_stat,
    fill_missing_with_value,
    frame_metrics,
    make_export_filename,
    restore_copy,
    strip_text_columns,
)


class MissingValueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = pd.DataFrame(
            {
                "数量": [1.0, None, 3.0],
                "名称": ["A", None, "C"],
                "编号": [10, 20, 30],
            }
        )
        self.original = self.frame.copy(deep=True)

    def assert_original_unchanged(self) -> None:
        pd.testing.assert_frame_equal(self.frame, self.original)

    def test_missing_table(self) -> None:
        table = build_missing_table(self.frame)
        quantity = table[table["字段名称"] == "数量"].iloc[0]
        self.assertEqual(quantity["缺失数量"], 1)
        self.assertEqual(quantity["缺失比例"], "33.33%")

    def test_delete_rows_with_missing_values(self) -> None:
        result = delete_missing_rows(self.frame)
        self.assertEqual(result.shape, (2, 3))
        self.assertEqual(list(result["名称"]), ["A", "C"])
        self.assert_original_unchanged()

    def test_mean_and_median_fill_selected_numeric_column(self) -> None:
        mean_result = fill_missing_with_stat(self.frame, ["数量"], "mean")
        median_result = fill_missing_with_stat(self.frame, ["数量"], "median")

        self.assertEqual(mean_result.loc[1, "数量"], 2.0)
        self.assertEqual(median_result.loc[1, "数量"], 2.0)
        self.assertTrue(pd.isna(mean_result.loc[1, "名称"]))
        self.assert_original_unchanged()

    def test_specified_value_fill_selected_columns(self) -> None:
        result = fill_missing_with_value(self.frame, ["数量", "名称"], "0")
        self.assertEqual(result.loc[1, "数量"], 0)
        self.assertEqual(result.loc[1, "名称"], "0")
        self.assert_original_unchanged()

    def test_invalid_fill_value_is_rejected(self) -> None:
        with self.assertRaises(CleaningError):
            fill_missing_with_value(self.frame, ["数量"], "不是数字")
        self.assert_original_unchanged()

    def test_metrics(self) -> None:
        metrics = frame_metrics(self.frame)
        self.assertEqual(metrics["rows"], 3)
        self.assertEqual(metrics["columns"], 3)
        self.assertEqual(metrics["missing_cells"], 2)
        self.assertEqual(metrics["duplicate_rows"], 0)


class DuplicateAndTextTests(unittest.TestCase):
    def test_drop_duplicate_rows_keeps_first(self) -> None:
        frame = pd.DataFrame(
            {"名称": ["A", "A", "B"], "值": [1, 1, 2]},
            index=[10, 11, 12],
        )
        original = frame.copy(deep=True)
        result = drop_duplicate_rows(frame)

        self.assertEqual(len(result), 2)
        self.assertEqual(result.iloc[0]["名称"], "A")
        self.assertEqual(result.iloc[1]["名称"], "B")
        pd.testing.assert_frame_equal(frame, original)

    def test_strip_only_selected_text_columns(self) -> None:
        frame = pd.DataFrame(
            {
                "名称": ["  A  ", "B ", None],
                "编码": [" 01 ", "02 ", None],
                "值": [1, 2, 3],
            }
        )
        original = frame.copy(deep=True)
        result = strip_text_columns(frame, ["名称"])

        self.assertEqual(result.loc[0, "名称"], "A")
        self.assertEqual(result.loc[1, "名称"], "B")
        self.assertEqual(result.loc[0, "编码"], " 01 ")
        self.assertEqual(count_text_changes(frame, ["名称", "编码"]), 4)
        pd.testing.assert_frame_equal(frame, original)


class TypeConversionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = pd.DataFrame(
            {
                "整数文本": ["1", "2", "3"],
                "错误数字": ["1", "x", "3"],
                "小数文本": ["1", "2.5", "3"],
                "日期文本": ["2024-01-01", "2024-02-01", None],
                "布尔文本": ["是", "否", None],
            }
        )
        self.original = self.frame.copy(deep=True)

    def assert_original_unchanged(self) -> None:
        pd.testing.assert_frame_equal(self.frame, self.original)

    def test_convert_to_integer(self) -> None:
        result = convert_column_type(self.frame, "整数文本", "整数")
        self.assertEqual(str(result["整数文本"].dtype), "Int64")
        self.assertEqual(result.loc[0, "整数文本"], 1)
        self.assert_original_unchanged()

    def test_invalid_integer_conversion_is_rejected(self) -> None:
        with self.assertRaises(CleaningError):
            convert_column_type(self.frame, "错误数字", "整数")
        self.assert_original_unchanged()

    def test_fractional_value_cannot_become_integer(self) -> None:
        with self.assertRaises(CleaningError):
            convert_column_type(self.frame, "小数文本", "整数")
        self.assert_original_unchanged()

    def test_convert_to_float(self) -> None:
        result = convert_column_type(self.frame, "小数文本", "小数")
        self.assertEqual(result.loc[1, "小数文本"], 2.5)
        self.assertEqual(str(result["小数文本"].dtype), "Float64")

    def test_convert_to_datetime(self) -> None:
        result = convert_column_type(self.frame, "日期文本", "日期时间")
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(result["日期文本"]))
        self.assertEqual(result.loc[0, "日期文本"], pd.Timestamp("2024-01-01"))
        self.assert_original_unchanged()

    def test_convert_to_boolean(self) -> None:
        result = convert_column_type(self.frame, "布尔文本", "布尔值")
        self.assertEqual(str(result["布尔文本"].dtype), "boolean")
        self.assertTrue(bool(result.loc[0, "布尔文本"]))
        self.assertFalse(bool(result.loc[1, "布尔文本"]))
        self.assertTrue(pd.isna(result.loc[2, "布尔文本"]))

    def test_convert_invalid_boolean_is_rejected(self) -> None:
        frame = pd.DataFrame({"标志": ["是", "也许"]})
        with self.assertRaises(CleaningError):
            convert_column_type(frame, "标志", "布尔值")

    def test_convert_numeric_to_datetime_is_rejected(self) -> None:
        frame = pd.DataFrame({"值": [1, 2, 3]})
        with self.assertRaises(CleaningError):
            convert_column_type(frame, "值", "日期时间")


class RestoreAndExportTests(unittest.TestCase):
    def test_restore_copy_is_independent(self) -> None:
        original = pd.DataFrame({"值": [1, 2, 3]})
        restored = restore_copy(original)
        restored.loc[0, "值"] = 99

        self.assertEqual(original.loc[0, "值"], 1)
        self.assertEqual(restored.loc[0, "值"], 99)

    def test_export_csv_bytes(self) -> None:
        frame = pd.DataFrame({"城市": ["北京", "上海"], "人口": [2189, 2487]})
        exported = dataframe_to_csv_bytes(frame)
        restored = pd.read_csv(io.BytesIO(exported))

        self.assertEqual(restored.shape, (2, 2))
        self.assertEqual(restored.loc[0, "城市"], "北京")

    def test_export_excel_bytes(self) -> None:
        frame = pd.DataFrame({"城市": ["北京"], "人口": [2189]})
        exported = dataframe_to_excel_bytes(frame)
        restored = pd.read_excel(io.BytesIO(exported), sheet_name="清洗结果")

        self.assertEqual(restored.shape, (1, 2))
        self.assertEqual(restored.loc[0, "城市"], "北京")

    def test_export_filename_is_safe(self) -> None:
        self.assertEqual(make_export_filename("cities.csv", "csv"), "cities_cleaned.csv")
        self.assertEqual(make_export_filename("a:b?.xlsx", "xlsx"), "a_b__cleaned.xlsx")


if __name__ == "__main__":
    unittest.main()
