import pytest

from app.ranges import merge_ranges, parse_range, resolve_range

# Surahs 1..3 with their real aya counts
AYA_COUNTS = {1: 7, 2: 286, 3: 200}


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2", ((2, None), (2, None))),
        ("2-3", ((2, None), (3, None))),
        ("2:255", ((2, 255), (2, 255))),
        ("2:1-20", ((2, 1), (2, 20))),
        ("2:1-3:10", ((2, 1), (3, 10))),
        (" 2:5 ", ((2, 5), (2, 5))),
    ],
)
def test_parse_range(value, expected):
    assert parse_range(value) == expected


@pytest.mark.parametrize("value", ["", "a", "2:", "2:1-", "2::1", "-2", "2:1-3:"])
def test_parse_range_rejects_invalid(value):
    with pytest.raises(ValueError):
        parse_range(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1", (1, 7)),
        ("2", (8, 293)),
        ("2:1-20", (8, 27)),
        ("1-2", (1, 293)),
        ("1:7-2:1", (7, 8)),
        ("3:200", (493, 493)),
    ],
)
def test_resolve_range(value, expected):
    assert resolve_range(value, AYA_COUNTS) == expected


@pytest.mark.parametrize("value", ["4", "0", "2:0", "2:287", "3-2", "2:20-10"])
def test_resolve_range_rejects_out_of_bounds(value):
    with pytest.raises(ValueError):
        resolve_range(value, AYA_COUNTS)


def test_merge_ranges():
    assert merge_ranges([(10, 20), (1, 5), (15, 30), (6, 8), (40, 40)]) == [
        (1, 8),
        (10, 30),
        (40, 40),
    ]
