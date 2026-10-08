import pytest

from app.arabic import normalize_arabic


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("بِسْمِ", "بسم"),
        ("ٱللَّهِ", "الله"),
        ("ٱلْعَـٰلَمِينَ", "العلمين"),
        # Small waw and yeh after a pronoun ending
        ("بِهِۦٓ", "به"),
        ("لَهُۥ", "له"),
        ("أَنۢبِئْهُم", "انبيهم"),
    ],
)
def test_normalize_arabic(text, expected):
    assert normalize_arabic(text) == expected
