import unicodedata
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.usefixtures("quran_db")

client = TestClient(app)


def get(url: str, **params: Any) -> Any:
    response = client.get(url, params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_summary_whole_quran():
    assert get("/stats/summary") == {
        "ayas": 6236,
        "words": 77790,
        "words_uthmani": 77429,
        "roots": 1651,
        "lemmas": 4776,
    }


def test_summary_fatiha():
    summary = get("/stats/summary", range="1")
    assert (summary["ayas"], summary["words"]) == (7, 29)


def test_summary_counts_overlapping_ranges_once():
    assert get("/stats/summary", range=["2:1-20", "2:10-25"])["ayas"] == 25


def test_summary_splits_vocative():
    # 19:28 يَٰٓأُخْتَ هَٰرُونَ ...: the simple script writes يا أخت
    summary = get("/stats/summary", range="19:28")
    assert summary["words"] == summary["words_uthmani"] + 1


@pytest.mark.parametrize(
    ("by", "q", "count"),
    [
        # word excludes ومريم; stem includes it
        ("word", "مريم", 33),
        # بِهِۦ: the small yeh isn't part of the normalized word
        ("word", "به", 327),
        ("stem", "مريم", 34),
        ("stem", "مَرْيَمَ", 34),
        ("lemma", "قال", 1618),
        ("root", "ر ح م", 339),
        # Roots are stored with hamza; typing it is optional
        ("root", "أله", 2851),
        ("root", "اله", 2851),
    ],
)
def test_count(by, q, count):
    assert get("/stats/count", by=by, q=q)["count"] == count


def test_count_word_breakdown_shows_written_forms():
    breakdown = get("/stats/count", by="word", q="مريم")["breakdown"]
    assert breakdown == [
        {"value": "مَرْيَمَ", "count": 28},
        {"value": "يَٰمَرْيَمُ", "count": 5},
    ]


def test_count_lemma_matches_all_lemmas_with_the_same_letters():
    breakdown = get("/stats/count", by="lemma", q="علم")["breakdown"]
    lemmas = {unicodedata.normalize("NFD", f["value"]) for f in breakdown}
    expected = {unicodedata.normalize("NFD", lemma) for lemma in ("عَلِمَ", "عِلْم", "عَلَّمَ")}
    assert expected <= lemmas
    # Diacritics typed in another order still match exactly (the data has shadda before fatha)
    assert get("/stats/count", by="lemma", q="عَلَّمَ")["count"] == 41
    # A diacritized lemma matches only itself
    assert get("/stats/count", by="lemma", q="عِلْم")["breakdown"] == [{"value": "عِلْم", "count": 105}]


def test_count_in_range():
    assert get("/stats/count", by="root", q="رحم", range="1")["count"] == 4


def test_top():
    assert get("/stats/top", by="root", limit=2) == [
        {"value": "أله", "count": 2851},
        {"value": "قول", "count": 1722},
    ]


@pytest.mark.parametrize(
    "params",
    [
        {"range": "115"},
        {"range": "2:300"},
        {"range": "3-2"},
        {"range": "x"},
    ],
)
def test_invalid_range(params):
    assert client.get("/stats/summary", params=params).status_code == 422


def test_count_rejects_multiple_words():
    assert client.get("/stats/count", params={"by": "word", "q": "يا مريم"}).status_code == 422
