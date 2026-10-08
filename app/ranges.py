"""Parse aya ranges like `2:1-2:20` and resolve them to global aya ids.

Accepted forms:
    2           the whole surah
    2-4         surahs 2 to 4
    2:255       one aya
    2:1-20      ayas 1 to 20 of surah 2
    2:1-3:10    from 2:1 to 3:10, across surahs
"""

import re

RANGE = re.compile(r"^(\d+)(?::(\d+))?(?:-(\d+)(?::(\d+))?)?$")

type AyaRef = tuple[int, int | None]  # (surah, aya); aya None means the surah's start or end


def parse_range(value: str) -> tuple[AyaRef, AyaRef]:
    match = RANGE.match(value.strip())
    if not match:
        raise ValueError(
            f"Invalid range {value!r}; expected e.g. 2, 2-4, 2:255, 2:1-20 or 2:1-3:10"
        )
    start_surah, start_aya, end_first, end_aya = (int(g) if g else None for g in match.groups())
    assert start_surah is not None
    start = (start_surah, start_aya)
    if end_first is None:
        end = start
    elif end_aya is not None:
        end = (end_first, end_aya)
    elif start_aya is not None:
        # 2:1-20: the number after the dash is an aya in the same surah
        end = (start_surah, end_first)
    else:
        end = (end_first, None)
    return start, end


def resolve_range(value: str, aya_counts: dict[int, int]) -> tuple[int, int]:
    """Global aya ids (first, last) of a range; aya_counts maps surah -> number of ayas."""
    start, end = parse_range(value)
    first, last = _aya_id(start, aya_counts, at_end=False), _aya_id(end, aya_counts, at_end=True)
    if first > last:
        raise ValueError(f"Range {value!r} ends before it starts")
    return first, last


def merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlapping or adjacent ranges, so no aya is counted twice."""
    merged: list[tuple[int, int]] = []
    for first, last in sorted(ranges):
        if merged and first <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], last))
        else:
            merged.append((first, last))
    return merged


def _aya_id(ref: AyaRef, aya_counts: dict[int, int], *, at_end: bool) -> int:
    surah, aya = ref
    if surah not in aya_counts:
        raise ValueError(f"Surah {surah} doesn't exist")
    if aya is None:
        aya = aya_counts[surah] if at_end else 1
    if not 1 <= aya <= aya_counts[surah]:
        raise ValueError(f"Surah {surah} has no aya {aya}")
    return sum(count for s, count in aya_counts.items() if s < surah) + aya
