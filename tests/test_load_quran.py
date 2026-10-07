import pytest

from app.scripts.load_quran import (
    build_aya_rows,
    check_aya_counts,
    parse_metadata,
    parse_text,
    strip_basmala,
)

SIMPLE = [
    "1|1|بِسْمِ اللَّهِ الرَّحْمَـٰنِ الرَّحِيمِ\n",
    "2|1|بِسْمِ اللَّهِ الرَّحْمَـٰنِ الرَّحِيمِ الم\n",
    "9|1|بَرَاءَةٌ مِّنَ اللَّهِ\n",
    "97|1|بِّسْمِ اللَّهِ الرَّحْمَـٰنِ الرَّحِيمِ إِنَّا أَنزَلْنَاهُ\n",
    "\n",
    "# PLEASE DO NOT REMOVE OR CHANGE THIS COPYRIGHT BLOCK\n",
    "#  Tanzil Quran Text (Simple, Version 1.1)\n",
]
UTHMANI = [
    "1|1|بِسْمِ ٱللَّهِ ٱلرَّحْمَـٰنِ ٱلرَّحِيمِ\n",
    "2|1|بِسْمِ ٱللَّهِ ٱلرَّحْمَـٰنِ ٱلرَّحِيمِ الٓمٓ\n",
    "9|1|بَرَآءَةٌ مِّنَ ٱللَّهِ\n",
    "97|1|بِّسْمِ ٱللَّهِ ٱلرَّحْمَـٰنِ ٱلرَّحِيمِ إِنَّآ أَنزَلْنَـٰهُ\n",
]


def rows_by_key():
    rows = build_aya_rows(parse_text(SIMPLE), parse_text(UTHMANI))
    return {(row["surah_id"], row["number"]): row for row in rows}


def test_parse_text_skips_footer():
    assert list(parse_text(SIMPLE)) == [(1, 1), (2, 1), (9, 1), (97, 1)]


def test_basmala_stripped_from_first_aya():
    rows = rows_by_key()
    assert rows[2, 1]["text_simple"] == "الم"
    assert rows[2, 1]["text_uthmani"] == "الٓمٓ"


def test_basmala_with_shadda_stripped():
    rows = rows_by_key()
    assert rows[97, 1]["text_simple"] == "إِنَّا أَنزَلْنَاهُ"
    assert rows[97, 1]["text_uthmani"] == "إِنَّآ أَنزَلْنَـٰهُ"


def test_fatiha_and_tawba_unchanged():
    rows = rows_by_key()
    assert rows[1, 1]["text_simple"] == "بِسْمِ اللَّهِ الرَّحْمَـٰنِ الرَّحِيمِ"
    assert rows[9, 1]["text_simple"] == "بَرَاءَةٌ مِّنَ اللَّهِ"


def test_ids_are_sequential_global_index():
    assert [row["id"] for row in rows_by_key().values()] == [1, 2, 3, 4]


def test_strip_basmala_rejects_text_without_it():
    with pytest.raises(ValueError):
        strip_basmala("الم ذَٰلِكَ الْكِتَابُ لَا رَيْبَ")


def test_mismatched_keys_raise():
    with pytest.raises(ValueError):
        build_aya_rows(parse_text(SIMPLE), parse_text(UTHMANI[:2]))


def test_parse_metadata():
    xml = """<quran><suras>
        <sura index="1" ayas="7" start="0" name="الفاتحة" tname="Al-Faatiha"
              ename="The Opening" type="Meccan" order="5" rukus="1" />
        <sura index="9" ayas="129" start="1235" name="التوبة" tname="At-Tawba"
              ename="The Repentance" type="Medinan" order="113" rukus="16" />
    </suras></quran>"""
    fatiha, tawba = parse_metadata(xml)
    assert fatiha["revelation_type"] == "meccan"
    assert fatiha["has_basmala"] is False
    assert tawba == {
        "id": 9,
        "name_arabic": "التوبة",
        "name_transliterated": "At-Tawba",
        "name_english": "The Repentance",
        "revelation_type": "medinan",
        "revelation_order": 113,
        "aya_count": 129,
        "has_basmala": False,
    }


def test_check_aya_counts_rejects_mismatch():
    surahs = [{"id": 1, "aya_count": 7}]
    ayas = [{"surah_id": 1}] * 6236
    with pytest.raises(ValueError):
        check_aya_counts(surahs, ayas)
