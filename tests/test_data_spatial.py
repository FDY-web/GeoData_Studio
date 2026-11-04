from __future__ import annotations

import unittest

import pandas as pd

from data_spatial import (
    PLOT_LAT,
    PLOT_LON,
    SpatialError,
    build_map_figure,
    build_offline_figure,
    detect_coordinate_columns,
    validate_coordinates,
)


class CoordinateDetectionTests(unittest.TestCase):
    def test_english_names(self) -> None:
        frame = pd.DataFrame({"longitude": [1.0], "latitude": [2.0], "name": ["A"]})
        lon, lat = detect_coordinate_columns(frame)
        self.assertEqual(lon, "longitude")
        self.assertEqual(lat, "latitude")

    def test_chinese_names(self) -> None:
        frame = pd.DataFrame({"经度": [1.0], "纬度": [2.0], "名称": ["A"]})
        lon, lat = detect_coordinate_columns(frame)
        self.assertEqual(lon, "经度")
        self.assertEqual(lat, "纬度")

    def test_short_english_names(self) -> None:
        frame = pd.DataFrame({"lng": [1.0], "lat": [2.0], "name": ["A"]})
        lon, lat = detect_coordinate_columns(frame)
        self.assertEqual(lon, "lng")
        self.assertEqual(lat, "lat")

    def test_no_coordinate_names(self) -> None:
        frame = pd.DataFrame({"a": [1], "b": [2]})
        self.assertEqual(detect_coordinate_columns(frame), (None, None))

    def test_numeric_candidate_is_preferred(self) -> None:
        frame = pd.DataFrame(
            {
                "lon_text": ["104.0"],
                "lon": [104.1],
                "lat": [30.6],
            }
        )
        lon, lat = detect_coordinate_columns(frame)
        self.assertEqual(lon, "lon")
        self.assertEqual(lat, "lat")

    def test_long_name_is_not_treated_as_longitude(self) -> None:
        frame = pd.DataFrame({"long_name": ["A"], "latitude": [30.6]})
        lon, _ = detect_coordinate_columns(frame)
        self.assertIsNone(lon)


class CoordinateValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = pd.DataFrame(
            {
                "lon": [104.06, None, "abc", 181, 104.07, 104.08, -200],
                "lat": [30.67, 30.68, 30.7, 30.8, "xyz", 30.75, 30.7],
                "name": ["A", "B", "C", "D", "E", "F", "G"],
            }
        )
        self.original = self.frame.copy(deep=True)

    def assert_original_unchanged(self) -> None:
        pd.testing.assert_frame_equal(self.frame, self.original)

    def test_quality_counts(self) -> None:
        check = validate_coordinates(self.frame, "lon", "lat")

        self.assertEqual(check.total_rows, 7)
        self.assertEqual(check.missing_lon, 1)
        self.assertEqual(check.missing_lat, 0)
        self.assertEqual(check.missing_rows, 1)
        self.assertEqual(check.non_numeric_lon, 1)
        self.assertEqual(check.non_numeric_lat, 1)
        self.assertEqual(check.out_of_range_lon, 2)
        self.assertEqual(check.out_of_range_lat, 0)
        self.assertEqual(check.valid_count, 2)
        self.assertEqual(check.invalid_count, 5)
        self.assert_original_unchanged()

    def test_valid_ranges_and_points(self) -> None:
        check = validate_coordinates(self.frame, "lon", "lat")

        self.assertAlmostEqual(check.lon_min, 104.06)
        self.assertAlmostEqual(check.lon_max, 104.08)
        self.assertAlmostEqual(check.lat_min, 30.67)
        self.assertAlmostEqual(check.lat_max, 30.75)
        self.assertEqual(len(check.valid_points), 2)
        self.assertEqual(list(check.valid_points["name"]), ["A", "F"])
        self.assertEqual(
            list(check.valid_points[PLOT_LON]), [104.06, 104.08]
        )
        self.assertEqual(
            list(check.valid_points[PLOT_LAT]), [30.67, 30.75]
        )

    def test_invalid_reasons(self) -> None:
        check = validate_coordinates(self.frame, "lon", "lat")
        reasons = " ".join(check.invalid_rows["无效原因"].tolist())

        self.assertIn("经度缺失", reasons)
        self.assertIn("经度非数值", reasons)
        self.assertIn("经度超出 -180~180", reasons)
        self.assertIn("纬度非数值", reasons)

    def test_boundary_coordinates_are_valid(self) -> None:
        frame = pd.DataFrame(
            {
                "lon": [-180.0, 180.0],
                "lat": [-90.0, 90.0],
            }
        )
        check = validate_coordinates(frame, "lon", "lat")
        self.assertEqual(check.valid_count, 2)
        self.assertEqual(check.invalid_count, 0)

    def test_same_field_is_rejected(self) -> None:
        with self.assertRaises(SpatialError):
            validate_coordinates(self.frame, "lon", "lon")
        self.assert_original_unchanged()

    def test_missing_field_is_rejected(self) -> None:
        with self.assertRaises(SpatialError):
            validate_coordinates(self.frame, "missing", "lat")
        self.assert_original_unchanged()


class MapFigureTests(unittest.TestCase):
    def setUp(self) -> None:
        frame = pd.DataFrame(
            {
                "lon": [104.06, 104.08, None],
                "lat": [30.67, 30.75, 30.7],
                "name": ["A", "B", "C"],
            }
        )
        self.check = validate_coordinates(frame, "lon", "lat")

    def test_map_contains_only_valid_points(self) -> None:
        figure = build_map_figure(self.check.valid_points, ["name"])
        self.assertEqual(len(figure.data), 1)
        self.assertEqual(len(figure.data[0].lat), 2)
        self.assertEqual(len(figure.data[0].lon), 2)
        self.assertEqual(figure.layout.map.style, "open-street-map")

    def test_offline_figure(self) -> None:
        figure = build_offline_figure(self.check.valid_points, ["name"])
        self.assertEqual(len(figure.data), 1)
        self.assertEqual(len(figure.data[0].x), 2)
        self.assertEqual(len(figure.data[0].y), 2)

    def test_empty_points_are_rejected(self) -> None:
        empty = self.check.valid_points.iloc[0:0].copy()
        with self.assertRaises(SpatialError):
            build_map_figure(empty, [])
        with self.assertRaises(SpatialError):
            build_offline_figure(empty, [])


if __name__ == "__main__":
    unittest.main()
