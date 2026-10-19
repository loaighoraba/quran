import pytest

from app.arabic import normalize_arabic, spell_part_in_simple_script


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


def test_spell_part_writes_a_dagger_alif_the_simple_script_spells_with_an_alef():
    assert spell_part_in_simple_script("ثَلَٰثَ", "ثَلَٰثَ", "ثَلَاثَ") == "ثَلَاثَ"
    # Only the stem's own dagger alif, after a prefix that has none
    assert spell_part_in_simple_script("ثَلَٰثَ", "وَثَلَٰثَ", "وَثَلَاثَ") == "ثَلَاثَ"


def test_spell_part_drops_a_dagger_alif_the_simple_script_leaves_out():
    assert spell_part_in_simple_script("ذَٰلِ", "ذَٰلِكَ", "ذَلِكَ") == "ذَلِ"


def test_spell_part_without_a_dagger_alif_or_simple_spelling_is_unchanged():
    assert spell_part_in_simple_script("مَرْيَمَ", "مَرْيَمَ", "مَرْيَمَ") == "مَرْيَمَ"
    assert spell_part_in_simple_script("ثَلَٰثَ", "ثَلَٰثَ", None) == "ثَلَٰثَ"
