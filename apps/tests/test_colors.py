import string

import pytest

from apps.colors import Colors

colors = Colors()


@pytest.mark.parametrize(
    "color_name, type_, expected",
    [
        ("red", "rgb", (1.0, 0.0, 0.0, 0.5)),
        ("red", "hex", "#ff000080"),
        ("red", "kml", "7f0000ff"),
    ],
)
def test_get_from_colors_cls(color_name, type_, expected):
    """Test the get method of Colors class."""
    assert colors.get(color_name, type_, 0.5) == expected
    with pytest.raises(ValueError):
        colors.get("invalid_color", type_)


def test_get_colors():
    hex_string = string.hexdigits + "#"
    assert all(c in hex_string for c in colors.red("hex"))
