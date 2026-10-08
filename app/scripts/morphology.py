"""Parse the Quranic Arabic Corpus morphology (datasources/quran-morphology.txt).

Each line is `surah:aya:word:segment<TAB>form<TAB>pos<TAB>features`, e.g.
`1:1:3:2	رَّحْمَٰنِ	N	ROOT:رحم|LEM:رَحْمٰن|MS|GEN|ADJ`.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from app.arabic import normalize_arabic

type AyaKey = tuple[int, int]
type WordKey = tuple[int, int, int]

POS_VALUES = {"N", "V", "P"}
# key:value features promoted to their own segment columns
KEYED_FEATURES = {
    "ROOT": "root",
    "LEM": "lemma",
    "VF": "verb_form",
    "MOOD": "mood",
    "FAM": "family",
}


@dataclass(frozen=True)
class MorphSegment:
    surah: int
    aya: int
    word: int
    number: int
    form: str
    pos: str
    features: str

    @property
    def word_key(self) -> WordKey:
        return self.surah, self.aya, self.word


def parse_morphology(lines: Iterable[str]) -> list[MorphSegment]:
    segments = []
    for line in lines:
        line = line.rstrip("\n")
        if not line:
            continue
        location, form, pos, features = line.split("\t")
        if pos not in POS_VALUES:
            raise ValueError(f"Unknown part of speech {pos!r} at {location}")
        surah, aya, word, number = map(int, location.split(":"))
        segments.append(MorphSegment(surah, aya, word, number, form, pos, features))
    check_numbering(segments)
    return segments


def check_numbering(segments: list[MorphSegment]) -> None:
    """Words within an aya and segments within a word must be numbered 1, 2, 3, ..."""
    previous: MorphSegment | None = None
    for segment in segments:
        if previous is not None and segment.word_key == previous.word_key:
            expected = (segment.word, previous.number + 1)
        elif previous is not None and (segment.surah, segment.aya) == (
            previous.surah,
            previous.aya,
        ):
            expected = (previous.word + 1, 1)
        else:
            expected = (1, 1)
        if (segment.word, segment.number) != expected:
            location = f"{segment.surah}:{segment.aya}:{segment.word}:{segment.number}"
            raise ValueError(f"Non-contiguous numbering at {location}")
        previous = segment


def parse_features(raw: str) -> dict[str, Any]:
    """Split a feature string into the promoted columns, the segment kind and remaining flags."""
    columns: dict[str, Any] = dict.fromkeys(KEYED_FEATURES.values())
    flags = []
    for item in raw.split("|"):
        if not item:
            continue
        key, separator, value = item.partition(":")
        if not separator:
            flags.append(item)
            continue
        if key not in KEYED_FEATURES:
            raise ValueError(f"Unknown feature key {key!r} in {raw!r}")
        column = KEYED_FEATURES[key]
        columns[column] = int(value) if column == "verb_form" else value

    is_prefix, is_suffix = "PREF" in flags, "SUFF" in flags
    if is_prefix and is_suffix:
        raise ValueError(f"Segment is both prefix and suffix: {raw!r}")
    columns["kind"] = "prefix" if is_prefix else "suffix" if is_suffix else "stem"
    columns["features"] = [flag for flag in flags if flag not in ("PREF", "SUFF")]
    return columns


def build_rows(
    segments: list[MorphSegment], aya_ids: dict[AyaKey, int]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build `words` and `segments` rows, with global ids assigned in Quran order."""
    words: dict[WordKey, list[MorphSegment]] = {}
    for segment in segments:
        words.setdefault(segment.word_key, []).append(segment)

    aya_keys = {(surah, aya) for surah, aya, _ in words}
    if aya_keys != aya_ids.keys():
        missing = aya_keys ^ aya_ids.keys()
        raise ValueError(f"Morphology and Quran text have different ayas: {sorted(missing)[:10]}")

    word_rows, segment_rows = [], []
    for word_id, ((surah, aya, number), word_segments) in enumerate(words.items(), start=1):
        text = "".join(segment.form for segment in word_segments)
        word_rows.append(
            {
                "id": word_id,
                "aya_id": aya_ids[surah, aya],
                "number": number,
                "text_uthmani": text,
                "text_normalized": normalize_arabic(text),
            }
        )
        for segment in word_segments:
            segment_rows.append(
                {
                    "id": len(segment_rows) + 1,
                    "word_id": word_id,
                    "number": segment.number,
                    "form": segment.form,
                    "form_normalized": normalize_arabic(segment.form),
                    "pos": segment.pos,
                    **parse_features(segment.features),
                }
            )
    return word_rows, segment_rows
