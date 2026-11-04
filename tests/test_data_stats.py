from __future__ import annotations

import unittest

import pandas as pd

from data_stats import (
    StatisticsError,
    category_frequencies,
    format_number,
    get_category_columns,
    get_numeric_columns,
    group_statistics,
    numeric_statistics_table,
    numeric_summary,
)


class FieldDetectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = pd.DataFrame(
            {
                "数值": [1.0, 2.0, None, 4.0],
                "整数": [10, 20, 30, 40],
                "类别": ["A", "B", "A", None],
                "布尔": [True, False, True, False],
                "日期": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", None]),
                "文本数字": ["1", "2", "3", "4"],
            }
        )

    def test_numeric_columns_exclude_text_and_boolean(self) -> None:
        numeric = get_numeric_columns(self.frame)
        self.assertEqual(numeric, ["数值", "整数"])

    def test_category_columns_include_text_and_boolean(self) -> None:
        categories = get_category_columns(self.frame)
        self.assertEqual(categories, ["类别", "布尔", "文本数字"])

    def test_numeric_summary(self) -> None:
        summary = numeric_summary(self.frame, "数值")
        self.assertEqual(summary["count"], 3)
        self.assertEqual(summary["missing"], 1)
        self.assertAlmostEqual(summary["mean"], 7 / 3)
        self.assertEqual(summary["median"], 2.0)
        self.assertEqual(summary["min"], 1.0)
        self.assertEqual(summary["max"], 4.0)

        table = numeric_statistics_table(summary)
        self.assertIn("均值", table["指标"].tolist())
        self.assertEqual(table.loc[table["指标"] == "缺失值", "值"].iloc[0], "1")

    def test_numeric_summary_rejects_text_column(self) -> None:
        with self.assertRaises(StatisticsError):
            numeric_summary(self.frame, "类别")


class CategoryFrequencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = pd.DataFrame(
            {
                "类别": ["A", "A", "B", None],
                "值": [1, 2, 3, 4],
            }
        )

    def test_frequency_counts_and_missing_category(self) -> None:
        result = category_frequencies(self.frame, "类别")
        counts = dict(zip(result["类别"], result["频数"]))
        ratios = dict(zip(result["类别"], result["占比"]))

        self.assertEqual(counts["A"], 2)
        self.assertEqual(counts["B"], 1)
        self.assertEqual(counts["(缺失)"], 1)
        self.assertEqual(ratios["A"], "50.00%")

    def test_top_n_limit(self) -> None:
        result = category_frequencies(self.frame, "类别", top_n=2)
        self.assertEqual(len(result), 2)
        self.assertEqual(result.iloc[0]["类别"], "A")

    def test_input_is_not_modified(self) -> None:
        original = self.frame.copy(deep=True)
        category_frequencies(self.frame, "类别")
        pd.testing.assert_frame_equal(self.frame, original)


class GroupStatisticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = pd.DataFrame(
            {
                "类别": ["A", "A", "B", None, "B"],
                "值": [1.0, 4.0, 2.0, None, None],
            }
        )
        self.original = self.frame.copy(deep=True)

    def assert_original_unchanged(self) -> None:
        pd.testing.assert_frame_equal(self.frame, self.original)

    def test_group_mean(self) -> None:
        result = group_statistics(self.frame, "类别", "值", "mean")
        values = dict(zip(result["分组"], result["统计值"]))
        self.assertEqual(values["A"], 2.5)
        self.assertEqual(values["B"], 2.0)
        self.assertNotIn("(缺失)", values)
        self.assert_original_unchanged()

    def test_group_sum_and_count(self) -> None:
        sum_result = group_statistics(self.frame, "类别", "值", "sum")
        count_result = group_statistics(self.frame, "类别", "值", "count")

        sum_values = dict(zip(sum_result["分组"], sum_result["统计值"]))
        count_values = dict(zip(count_result["分组"], count_result["统计值"]))
        self.assertEqual(sum_values["A"], 5.0)
        self.assertEqual(count_values["B"], 1)
        self.assertEqual(count_values["(缺失)"], 0)

    def test_group_median(self) -> None:
        result = group_statistics(self.frame, "类别", "值", "median")
        values = dict(zip(result["分组"], result["统计值"]))
        self.assertEqual(values["A"], 2.5)

    def test_invalid_grouping_is_rejected(self) -> None:
        with self.assertRaises(StatisticsError):
            group_statistics(self.frame, "不存在", "值", "mean")
        with self.assertRaises(StatisticsError):
            group_statistics(self.frame, "类别", "类别", "mean")
        with self.assertRaises(StatisticsError):
            group_statistics(self.frame, "类别", "值", "unknown")
        self.assert_original_unchanged()


class FormattingTests(unittest.TestCase):
    def test_format_number(self) -> None:
        self.assertEqual(format_number(1000), "1,000")
        self.assertEqual(format_number(2.5), "2.50")
        self.assertEqual(format_number(float("nan")), "—")
        self.assertEqual(format_number(None), "—")


if __name__ == "__main__":
    unittest.main()
