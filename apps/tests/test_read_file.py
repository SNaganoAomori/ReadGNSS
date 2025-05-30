import os

import pytest

from apps.read_file import read_drg_way_point, _DrgWayPoint
from apps.models import DataModel

FILE_2023 = os.path.join(
    os.path.dirname(__file__), "data", "2023_横浜_2119は1__way-point.gpx"
)
FILE_2024 = os.path.join(
    os.path.dirname(__file__), "data", "2024_六ヶ所_1166ほ__way-point.gpx"
)


@pytest.mark.parametrize("file_path", [FILE_2023, FILE_2024])
def test_drg_way_point(file_path):
    """Test reading DRG Way Point files."""
    # Test reading a file from 2023
    way_pnt = _DrgWayPoint(file_path)
    items = way_pnt.read_items()
    assert isinstance(items, list)
    assert all(isinstance(item, dict) for item in items)


@pytest.mark.parametrize("file_path", [FILE_2023, FILE_2024])
def test_read_drg_way_point(file_path):
    """Test the read_drg_way_point function."""
    items = read_drg_way_point(file_path)
    assert isinstance(items, list)
    assert all(isinstance(item, DataModel) for item in items)
