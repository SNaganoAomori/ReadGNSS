import datetime

import pytest

from apps.web import fetch_elevation_from_web, fetch_corrected_semidynamic_from_web


def test_fetch_elevation_from_web():
    """Test the fetch_elevation_from_web function with sample coordinates."""
    lons = [141.272242456, 140.740228]
    lats = [40.924881316, 40.824348]
    result = fetch_elevation_from_web(lons, lats)
    assert isinstance(result, list)
    with pytest.raises(Exception):
        fetch_elevation_from_web(141.272242456, 40.924881316)  # Invalid input type


"""
    argument:
    lon 40.832592069
    lat 140.728905776

    2025 -> 140.728900297, 40.832596992
    2024 -> 140.728900519, 40.832596769
    2023 -> 140.728900789, 40.832596547
    2022 -> 140.728900981, 40.832596306
    2021 -> 140.728901300, 40.832596014

    """


@pytest.mark.parametrize(
    "survey_datetime, expected_lon, expected_lat",
    [
        (datetime.datetime(2025, 5, 1, 0, 0, 0), 140.728900297, 40.832596992),
        (datetime.datetime(2024, 11, 1, 0, 0, 0), 140.728900519, 40.832596769),
        (datetime.datetime(2023, 11, 1, 0, 0, 0), 140.728900789, 40.832596547),
        (datetime.datetime(2022, 11, 1, 0, 0, 0), 140.728900981, 40.832596306),
        (datetime.datetime(2021, 11, 1, 0, 0, 0), 140.728901300, 40.832596014),
    ],
)
def test_fetch_corrected_semidynamic_from_web(
    survey_datetime, expected_lon, expected_lat
):
    """Test the fetch_corrected_semidynamic_from_web function with sample coordinates and dates."""
    result = fetch_corrected_semidynamic_from_web(
        correction_datetime=survey_datetime,
        lons=[140.728905776],
        lats=[40.832592069],
    )
    assert isinstance(result, list)
    coords = result[0]
    assert coords.longitude == expected_lon
    assert coords.latitude == expected_lat
