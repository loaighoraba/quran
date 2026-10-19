import pytest

from app.scripts.morphology import (
    build_rows,
    pair_simple_words,
    parse_features,
    parse_morphology,
    split_vocative,
)

LINES = [
    "1:1:1:1\tبِ\tP\tP|PREF|LEM:ب\n",
    "1:1:1:2\tسْمِ\tN\tROOT:سمو|LEM:اسْم|M|GEN\n",
    "1:1:2:1\tٱللَّهِ\tN\tPN|ROOT:أله|LEM:اللَّه|GEN\n",
    "2:1:1:1\tالٓمٓ\tP\tINL|\n",
]


def test_parse_features_stem():
    assert parse_features("ROOT:رحم|LEM:رَحِيم|MS|GEN|ADJ") == {
        "root": "رحم",
        "lemma": "رَحِيم",
        "verb_form": None,
        "mood": None,
        "family": None,
        "kind": "stem",
        "features": ["MS", "GEN", "ADJ"],
    }


def test_parse_features_prefix():
    features = parse_features("CONJ|PREF|LEM:و")
    assert features["kind"] == "prefix"
    assert features["lemma"] == "و"
    assert features["features"] == ["CONJ"]


def test_parse_features_verb():
    features = parse_features("IMPF|VF:1|ROOT:عبد|LEM:عَبَدَ|1P|MOOD:IND")
    assert features["verb_form"] == 1
    assert features["mood"] == "IND"
    assert features["features"] == ["IMPF", "1P"]


def test_parse_features_ignores_trailing_separator():
    assert parse_features("INL|")["features"] == ["INL"]


def test_parse_features_rejects_unknown_key():
    with pytest.raises(ValueError):
        parse_features("XYZ:1")


def test_parse_morphology_keeps_empty_suffix_form():
    segments = parse_morphology([*LINES[:3], "1:1:2:2\t\tN\tPRON|SUFF|1S\n"])
    assert segments[-1].form == ""
    assert parse_features(segments[-1].features)["kind"] == "suffix"


def test_parse_morphology_rejects_gaps():
    with pytest.raises(ValueError):
        parse_morphology([LINES[0], "1:1:1:3\tسْمِ\tN\tM|GEN\n"])
    with pytest.raises(ValueError):
        parse_morphology([LINES[0], "1:1:3:1\tسْمِ\tN\tM|GEN\n"])


def test_parse_morphology_rejects_unknown_pos():
    with pytest.raises(ValueError):
        parse_morphology(["1:1:1:1\tبِ\tX\tP|PREF\n"])


def test_build_rows():
    segments = parse_morphology(LINES[:4])
    words, rows = build_rows(segments, {(1, 1): 1, (2, 1): 8})
    assert [(w["id"], w["aya_id"], w["number"]) for w in words] == [(1, 1, 1), (2, 1, 2), (3, 8, 1)]
    assert words[0]["text_uthmani"] == "بِسْمِ"
    assert words[1]["text_normalized"] == "الله"
    assert rows[0]["form_normalized"] == "ب"
    assert [(r["id"], r["word_id"], r["number"]) for r in rows] == [
        (1, 1, 1),
        (2, 1, 2),
        (3, 2, 1),
        (4, 3, 1),
    ]


def test_build_rows_rejects_missing_ayas():
    with pytest.raises(ValueError):
        build_rows(parse_morphology(LINES[:3]), {(1, 1): 1, (1, 2): 2})


def segment(form_normalized, kind="stem", features=()):
    return {"form_normalized": form_normalized, "kind": kind, "features": list(features)}


def test_split_vocative():
    assert split_vocative([segment("مريم")]) == ["مريم"]
    # يَٰمَرْيَمُ
    assert split_vocative([segment("ي", "prefix", ["VOC"]), segment("مريم")]) == ["يا", "مريم"]
    # وَيَٰٓـَٔادَمُ
    assert split_vocative(
        [segment("و", "prefix", ["CONJ"]), segment("ي", "prefix", ["VOC"]), segment("ادم")]
    ) == ["ويا", "ادم"]
    # The vocative م suffix of ٱللَّهُمَّ isn't written as a separate word
    assert split_vocative([segment("الله"), segment("م", "suffix", ["VOC"])]) == ["اللهم"]


def test_pair_simple_words_gives_a_vocative_two_words():
    assert pair_simple_words("يَا مَرْيَمُ اقْنُتِي", [2, 1]) == ["يَا مَرْيَمُ", "اقْنُتِي"]


def test_pair_simple_words_skips_stop_signs():
    assert pair_simple_words("ثَلَاثَ ۖ مِائَةٍ ۚ", [1, 1]) == ["ثَلَاثَ", "مِائَةٍ"]


def test_pair_simple_words_gives_up_when_the_scripts_split_differently():
    assert pair_simple_words("بَعْدَ مَا سَمِعَهُ", [2]) == [None]
