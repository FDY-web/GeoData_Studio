from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from data_clean import CLEAN_KEY, CLEAN_SOURCE_KEY
from data_view import META_KEY, DATA_KEY

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"


class AppStatePersistenceTests(unittest.TestCase):
    def test_dataset_survives_page_switch(self) -> None:
        frame = pd.DataFrame({"城市": ["北京", "上海"], "人口": [2189, 2487]})
        metadata = {
            "signature": "test-signature",
            "file_name": "cities.csv",
            "file_size": 32,
            "file_type": "CSV",
            "sheet_name": None,
            "sheet_names": [],
            "encoding": "utf-8",
            "row_count": 2,
            "column_count": 2,
        }

        app = AppTest.from_file(str(APP_PATH), default_timeout=30)
        app.run()
        app.session_state[DATA_KEY] = frame
        app.session_state[META_KEY] = metadata

        app.radio[0].set_value("数据查看").run()
        self.assertEqual(len(app.exception), 0)
        self.assertIn(DATA_KEY, app.session_state)
        self.assertTrue(any("cities.csv" in block.value for block in app.markdown))
        self.assertEqual(len(app.dataframe), 2)

        app.radio[0].set_value("首页").run()
        app.radio[0].set_value("数据查看").run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state[DATA_KEY].shape, (2, 2))
        self.assertEqual(app.session_state[META_KEY]["file_name"], "cities.csv")
        self.assertTrue(any("cities.csv" in block.value for block in app.markdown))

        replacement = pd.DataFrame({"城市": ["广州"], "人口": [1882]})
        app.session_state[DATA_KEY] = replacement
        app.session_state[META_KEY] = {
            **metadata,
            "signature": "replacement-signature",
            "file_name": "cities-new.csv",
            "row_count": 1,
        }
        app.run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state[DATA_KEY].shape, (1, 2))
        self.assertTrue(any("cities-new.csv" in block.value for block in app.markdown))

    def test_clean_copy_persists_and_restore_keeps_original(self) -> None:
        original = pd.DataFrame(
            {"城市": ["北京", "上海", "广州"], "人口": [2189, 2487, 1882]}
        )
        metadata = {
            "signature": "clean-test-signature",
            "file_name": "cities.csv",
            "file_size": 64,
            "file_type": "CSV",
            "sheet_name": None,
            "sheet_names": [],
            "encoding": "utf-8",
            "row_count": 3,
            "column_count": 2,
        }

        app = AppTest.from_file(str(APP_PATH), default_timeout=30)
        app.run()
        app.session_state[DATA_KEY] = original.copy(deep=True)
        app.session_state[META_KEY] = metadata

        app.radio[0].set_value("数据清洗").run()
        self.assertEqual(len(app.exception), 0)
        self.assertIn(CLEAN_KEY, app.session_state)
        pd.testing.assert_frame_equal(app.session_state[CLEAN_KEY], original)

        modified = original.iloc[1:].reset_index(drop=True)
        app.session_state[CLEAN_KEY] = modified
        app.radio[0].set_value("首页").run()
        app.radio[0].set_value("数据清洗").run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.session_state[CLEAN_KEY]), 2)
        pd.testing.assert_frame_equal(app.session_state[DATA_KEY], original)

        restore_buttons = [
            button for button in app.button if button.label == "恢复原始数据"
        ]
        self.assertTrue(restore_buttons)
        restore_buttons[0].click().run()
        self.assertEqual(len(app.exception), 0)
        pd.testing.assert_frame_equal(app.session_state[CLEAN_KEY], original)

        replacement = pd.DataFrame({"城市": ["深圳"], "人口": [1766]})
        app.session_state[DATA_KEY] = replacement
        app.session_state[META_KEY] = {
            **metadata,
            "signature": "new-clean-source-signature",
            "file_name": "new-cities.csv",
            "row_count": 1,
        }
        app.run()
        self.assertEqual(len(app.exception), 0)
        pd.testing.assert_frame_equal(app.session_state[CLEAN_KEY], replacement)
        self.assertEqual(
            app.session_state[CLEAN_SOURCE_KEY], "new-clean-source-signature"
        )

    def test_duplicate_action_updates_only_clean_copy(self) -> None:
        original = pd.DataFrame(
            {
                "城市": ["北京", "上海", "北京"],
                "人口": [2189, 2487, 2189],
                "备注": [" 首都", None, " 首都"],
            }
        )
        metadata = {
            "signature": "duplicate-action-signature",
            "file_name": "duplicates.csv",
            "file_size": 80,
            "file_type": "CSV",
            "sheet_name": None,
            "sheet_names": [],
            "encoding": "utf-8",
        }

        app = AppTest.from_file(str(APP_PATH), default_timeout=30)
        app.run()
        app.session_state[DATA_KEY] = original.copy(deep=True)
        app.session_state[META_KEY] = metadata
        app.radio[0].set_value("数据清洗").run()

        duplicate_checkboxes = [
            checkbox
            for checkbox in app.checkbox
            if "确认删除这 1 行" in checkbox.label
        ]
        self.assertEqual(len(duplicate_checkboxes), 2)
        duplicate_checkboxes[1].set_value(True).run()

        delete_buttons = [
            button for button in app.button if "行重复记录" in button.label
        ]
        self.assertTrue(delete_buttons)
        delete_buttons[0].click().run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.session_state[CLEAN_KEY]), 2)
        pd.testing.assert_frame_equal(app.session_state[DATA_KEY], original)

    def test_statistics_prefers_clean_copy_and_handles_stale_source(self) -> None:
        original = pd.DataFrame(
            {
                "城市": ["北京", "上海", "广州"],
                "人口": [2189, 2487, 1882],
                "类型": ["首都", "直辖市", "省会"],
            }
        )
        clean = original.copy(deep=True)
        clean.loc[0, "人口"] = 9999
        metadata = {
            "signature": "stats-source-signature",
            "file_name": "cities.csv",
            "file_size": 64,
            "file_type": "CSV",
            "sheet_name": None,
            "sheet_names": [],
            "encoding": "utf-8",
        }

        app = AppTest.from_file(str(APP_PATH), default_timeout=30)
        app.run()
        app.session_state[DATA_KEY] = original.copy(deep=True)
        app.session_state[META_KEY] = metadata
        app.session_state[CLEAN_KEY] = clean.copy(deep=True)
        app.session_state[CLEAN_SOURCE_KEY] = "stats-source-signature"

        app.radio[0].set_value("统计分析").run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("清洗后数据" in block.value for block in app.markdown))
        self.assertGreaterEqual(len(app.get("plotly_chart")), 1)
        pd.testing.assert_frame_equal(app.session_state[DATA_KEY], original)
        pd.testing.assert_frame_equal(app.session_state[CLEAN_KEY], clean)

        app.radio[0].set_value("首页").run()
        app.radio[0].set_value("统计分析").run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state[CLEAN_KEY].loc[0, "人口"], 9999)

        app.session_state[CLEAN_SOURCE_KEY] = "stale-signature"
        app.run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(
            any("清洗副本与当前上传文件不一致" in item.value for item in app.warning)
        )
        self.assertTrue(any("原始数据" in block.value for block in app.markdown))

    def test_statistics_without_data_shows_prompt(self) -> None:
        app = AppTest.from_file(str(APP_PATH), default_timeout=30)
        app.run()
        app.radio[0].set_value("统计分析").run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(
            any("还没有可分析的数据" in block.value for block in app.markdown)
        )

    def test_spatial_prefers_clean_copy_and_does_not_mutate_data(self) -> None:
        original = pd.DataFrame(
            {
                "name": ["A", "B", "C"],
                "longitude": [104.06, 104.08, None],
                "latitude": [30.67, 30.75, 30.70],
                "value": [1, 2, 3],
            }
        )
        clean = original.iloc[:2].reset_index(drop=True).copy()
        metadata = {
            "signature": "spatial-source-signature",
            "file_name": "points.csv",
            "file_size": 80,
            "file_type": "CSV",
            "sheet_name": None,
            "sheet_names": [],
            "encoding": "utf-8",
        }

        app = AppTest.from_file(str(APP_PATH), default_timeout=40)
        app.run()
        app.session_state[DATA_KEY] = original.copy(deep=True)
        app.session_state[META_KEY] = metadata
        app.session_state[CLEAN_KEY] = clean.copy(deep=True)
        app.session_state[CLEAN_SOURCE_KEY] = "spatial-source-signature"

        app.radio[0].set_value("空间分析").run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("清洗后数据" in block.value for block in app.markdown))
        self.assertTrue(any("坐标质量检查" in block.value for block in app.markdown))
        self.assertGreaterEqual(len(app.get("plotly_chart")), 2)
        pd.testing.assert_frame_equal(app.session_state[DATA_KEY], original)
        pd.testing.assert_frame_equal(app.session_state[CLEAN_KEY], clean)

        app.session_state[CLEAN_SOURCE_KEY] = "stale-spatial-source"
        app.run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(
            any("清洗副本与当前上传文件不一致" in item.value for item in app.warning)
        )

    def test_spatial_rejects_same_coordinate_fields(self) -> None:
        frame = pd.DataFrame(
            {
                "longitude": [104.06, 104.08],
                "latitude": [30.67, 30.75],
            }
        )
        metadata = {
            "signature": "spatial-manual-signature",
            "file_name": "points.csv",
            "file_size": 40,
            "file_type": "CSV",
            "sheet_name": None,
            "sheet_names": [],
            "encoding": "utf-8",
        }

        app = AppTest.from_file(str(APP_PATH), default_timeout=40)
        app.run()
        app.session_state[DATA_KEY] = frame
        app.session_state[META_KEY] = metadata
        app.radio[0].set_value("空间分析").run()

        selectboxes = [
            widget
            for widget in app.selectbox
            if widget.label in {"经度字段", "纬度字段"}
        ]
        self.assertEqual(len(selectboxes), 2)
        selectboxes[0].set_value("longitude")
        selectboxes[1].set_value("longitude").run()

        self.assertEqual(len(app.exception), 0)
        self.assertTrue(
            any("不能是同一个字段" in item.value for item in app.error)
        )

    def test_spatial_without_data_shows_prompt(self) -> None:
        app = AppTest.from_file(str(APP_PATH), default_timeout=30)
        app.run()
        app.radio[0].set_value("空间分析").run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(
            any("还没有可进行空间分析的数据" in block.value for block in app.markdown)
        )


if __name__ == "__main__":
    unittest.main()
