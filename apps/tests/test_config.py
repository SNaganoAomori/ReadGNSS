import datetime

import pytest

from apps.config import Formatter, SemiDynamicCorrection, Web, no_constructor, NoLoader

formatter = Formatter()


@pytest.mark.parametrize(
    "test_input, expected",
    [
        ("2025-01-01T00:00:00", datetime.datetime(2025, 1, 1, 0, 0)),
        ("2025/01/01 00:00:00", datetime.datetime(2025, 1, 1, 0, 0)),
        ("2025/01/01 00:00", datetime.datetime(2025, 1, 1, 0, 0)),
        (datetime.datetime(2025, 1, 1, 0, 0), datetime.datetime(2025, 1, 1, 0, 0)),
        (None, None),
    ],
)
def test_check_datetime_format_from_formatter_cls(test_input, expected):
    """Test the convert_to_datetime function."""
    result = formatter.check_datetime_format(test_input)
    if result is None:
        assert result is None
        with pytest.raises(ValueError):
            formatter.check_datetime_format("invalid date")
    else:
        assert formatter.check_datetime_format(test_input) == expected


def test_check_decimal_places_of_mercator_from_formatter_cls():
    """Test the check_decimal_places_of_mercator function."""
    assert formatter.check_decimal_places_of_mercator(1234567.123456789) == 1234567.1235
    assert formatter.check_decimal_places_of_mercator(1234567.1) == 1234567.1
    assert formatter.check_decimal_places_of_mercator(1234567) == 1234567
    assert formatter.check_decimal_places_of_mercator(None) is None


def test_check_decimal_places_of_geodetic_from_formatter_cls():
    """Test the check_decimal_places_of_latitude function."""
    assert (
        formatter.check_decimal_places_of_geodetic(35.12345678912345) == 35.12345678912
    )
    assert formatter.check_decimal_places_of_geodetic(None) is None


@pytest.mark.parametrize(
    "crs_generation, crs_type, expected",
    [("The current", "JPN10", None), ("JGD2011_R", "JPN10", 6678), (None, None, None)],
)
def test_drg_generation_converter_from_formatter_cls(
    crs_generation, crs_type, expected
):
    """Test the drg_generation_converter function."""
    assert formatter.drg_generation_converter(crs_generation, crs_type) == expected


@pytest.mark.parametrize(
    "test_input, expected", [("ＡＢＣＤＥ", "ABCDE"), ("１２３４５", "12345")]
)
def test_parse_zen2han_from_formatter_cls(test_input, expected):
    """Test the parse_zen2han function."""
    assert formatter.parse_zen2han(test_input) == expected


@pytest.mark.parametrize(
    "test_input, expected",
    [
        ("１２３４．５", 1234.5),
        ("１２３４.５", 1234.5),
        ("A1.1", 1.1),
        ("dfgafg", 0.0),
    ],
)
def test_parse_sentence_in_numeric_from_formatter_cls(test_input, expected):
    """Test the parse_sentence_in_numeric function."""
    assert formatter.parse_sentence_in_numeric(test_input) == expected


def test_elevation_url_from_web_cls():
    """Test the elevation_url function."""
    url = Web().elevation_url(lon=135.12345678912345, lat=35.12345678912345)
    assert isinstance(url, str)


@pytest.mark.parametrize(
    "datetime_, expected",
    [
        (datetime.datetime(2025, 1, 1, 0, 0), 2024),
        (datetime.datetime(2025, 5, 1, 0, 0), 2025),
        (datetime.datetime(2023, 12, 31, 0, 0), 2023),
        (2024, 2024),
    ],
)
def test_check_correction_year(datetime_, expected):
    """Test the check_correction_year function."""
    assert SemiDynamicCorrection.check_correction_year(datetime_) == expected


def test_semidaynamic_correction():
    data = {
        "correction_year": 2023,
        "longitude": 141.304236043,
        "latitude": 41.142934835,
    }
    semi_dynamic_correction = SemiDynamicCorrection(**data)
    url = semi_dynamic_correction.get_correction_url()
    assert isinstance(url, str)


def test_order():
    NoLoader.add_constructor("tag:yaml.org,2002:bool", no_constructor)
    Web().dummy_user_agent()
