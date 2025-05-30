import os
import pickle

import pytest

from apps.models import DataModel, DataModels, hex_to_abgr, original_data_to
from apps.config import (
    ADDITIONAL_EN_FIELD_NAMES,
    ADDITIONAL_JA_FIELD_NAMES,
    DRG_RENAME_ORG_TO_EN,
    DRG_DEFAULT_FIELD_NAMES,
    DRG_EN_FIELD_NAMES,
    DRG_JA_FIELD_NAMES,
)

file_path = os.path.join(os.path.dirname(__file__), "data", "readed_way_point_file.pkl")
with open(file_path, "rb") as f:
    ORIGINAL_DATA_LIST = pickle.load(f)


def test_original_data_to():
    """
    Test the original_data_to function to ensure it correctly converts
    data using the DRG_RENAME_ORG_TO_EN mapping.
    """
    for data in ORIGINAL_DATA_LIST:
        result = original_data_to(data, DRG_RENAME_ORG_TO_EN)
        assert isinstance(result, dict)
        assert all(key in DRG_EN_FIELD_NAMES for key in result.keys())


@pytest.mark.parametrize(
    "hex_color, expected",
    [
        ("#FF0000", "ff0000ff"),
        ("#00FF00", "ff00ff00"),
        ("#0000FF", "ffff0000"),
    ],
)
def test_hex_to_abgr(hex_color, expected):
    """
    Test the hex_to_abgr function to ensure it correctly converts
    hex color codes to ABGR format.
    """
    # Example hex color
    result = hex_to_abgr(hex_color)
    assert isinstance(result, str)
    assert result == expected
