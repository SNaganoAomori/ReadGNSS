import os

import geopandas as gpd
import pyproj
import pytest
import shapely

from apps.geometries import estimate_utm_crs, reproject_xy, Labeling, XY, Label

waypoint_file = os.path.join(os.path.dirname(__file__), "way_point.geojson")
gdf = gpd.read_file(waypoint_file)

global POINTS_DEG
POINTS_DEG = gdf.geometry.to_list()

global POINTS_UTM
POINTS_UTM = gdf.to_crs(6691).geometry.to_list()


@pytest.mark.parametrize(
    "lon, expected_epsg",
    [
        (130, 6689),
        (135, 6690),
        (140, 6691),
        (146, 6692),
    ],
)
def test_estimate_utm_crs(lon, expected_epsg):
    """
    Test the estimate_utm_crs function.
    """
    point = shapely.Point(lon, 35)
    utm_crs = estimate_utm_crs(point.x, point.y)
    utm_epsg = pyproj.CRS.from_wkt(utm_crs).to_epsg()
    assert utm_epsg == expected_epsg
    with pytest.raises(Exception):
        estimate_utm_crs(100, 100)


@pytest.mark.parametrize(
    "xs, ys",
    [
        (139.000, 35.000),
        ([139.000, 140.000], [35.000, 36.000]),
    ],
)
def test_reproject_xy(xs, ys):
    """Test the reproject_xy function."""
    in_crs = pyproj.CRS.from_epsg(4326).to_wkt()
    out_crs = pyproj.CRS.from_epsg(6691).to_wkt()
    xy = reproject_xy(xs, ys, in_crs, out_crs)
    assert isinstance(xy, XY)
    if isinstance(xs, list):
        for arg_x, arg_y, expected_x, expected_y in zip(xs, ys, xy.x, xy.y):
            assert arg_x != expected_x
            assert arg_y != expected_y
    else:
        assert xs != xy.x
        assert ys != xy.y


@pytest.mark.parametrize(
    "in_epsg, points",
    [
        (4326, POINTS_DEG),
        (6691, POINTS_UTM),
    ],
)
def test__check_mercator_from_labeling_cls(in_epsg, points):
    """Test the _check_mercator method of the Labeling class."""
    labeling = Labeling(
        labels=[i for i in range(len(points))],
        points=points,
        in_epsg=in_epsg,
    )
    for arg_point, label_point in zip(points, labeling._points):
        if in_epsg == 4326:
            assert arg_point.x != label_point.x
            assert arg_point.y != label_point.y
        else:
            assert arg_point.x == label_point.x
            assert arg_point.y == label_point.y


def test__check_labels_from_labeling_cls():
    """Test the _check_labels method of the Labeling class."""
    labels = [str(i) for i in range(len(POINTS_UTM))]
    labels[1] = None
    labeling = Labeling(
        labels=labels,
        points=POINTS_UTM,
        in_epsg=6691,
    )
    for arg_label, expected_label in zip(labels, labeling._labels):
        if arg_label is None:
            assert expected_label == ""
        else:
            assert str(arg_label) == expected_label
        assert isinstance(expected_label, str)

    with pytest.raises(Exception):
        Labeling(
            labels=["1", "2", "3"],
            points=POINTS_UTM,
            in_epsg=4326,
        )


def test_calculate_label_positions_from_labeling_cls():
    """Test the calculate_label_positions method of the Labeling class."""
    labels = [str(i) for i in range(len(POINTS_UTM))]
    labeling = Labeling(
        labels=labels,
        points=POINTS_UTM,
        in_epsg=6691,
    )
    label_positions = labeling.calculate_label_positions()
    assert isinstance(label_positions, list)
    assert all(isinstance(label, Label) for label in label_positions)
    assert all(isinstance(label.label, str) for label in label_positions)
    assert all(isinstance(label.coordinate, shapely.Point) for label in label_positions)
    # 少なくとも半分以上のラベル位置が区域外に出ていることを確認
    unit = len(label_positions) / 100
    total = 0
    for position in label_positions:
        if labeling._polygon.intersects(position.coordinate):
            total += unit
    assert total <= 0.5
