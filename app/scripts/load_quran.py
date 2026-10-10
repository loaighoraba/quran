"""Load the Quran texts, surah metadata and word morphology into the database.

Run with: uv run python -m app.scripts.load_quran

Idempotent: existing surahs, ayas, words and segments are replaced in a single transaction.
"""

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from psycopg import sql
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.arabic import normalize_arabic
from app.config import Settings, get_settings
from app.db import Base, build_engine, build_session_factory
from app.models import Aya, Segment, Surah, Word
from app.scripts.morphology import build_rows, parse_morphology

DATASOURCES = Path(__file__).resolve().parents[2] / "datasources"
SIMPLE_PATH = DATASOURCES / "quran-simple.txt"
UTHMANI_PATH = DATASOURCES / "quran-uthmani.txt"
METADATA_PATH = DATASOURCES / "quran-data.xml"
MORPHOLOGY_PATH = DATASOURCES / "quran-morphology.txt"

AYA_LINE = re.compile(r"^(\d+)\|(\d+)\|(.*)$")
TOTAL_AYAS = 6236
BASMALA_WORDS = 4
NORMALIZED_BASMALA = "بسم الله الرحمن الرحيم"
# Surah 1: the basmala is aya 1 itself; surah 9: no basmala
SURAHS_WITHOUT_PREFIXED_BASMALA = {1, 9}

type AyaKey = tuple[int, int]


def parse_text(lines: Iterable[str]) -> dict[AyaKey, str]:
    """Parse `surah|aya|text` lines, skipping blank lines and the copyright footer."""
    ayas: dict[AyaKey, str] = {}
    for line in lines:
        match = AYA_LINE.match(line.rstrip("\n"))
        if match:
            surah, aya, text = match.groups()
            ayas[int(surah), int(aya)] = text
    return ayas


def has_prefixed_basmala(surah: int, aya: int) -> bool:
    return aya == 1 and surah not in SURAHS_WITHOUT_PREFIXED_BASMALA


def strip_basmala(text: str) -> str:
    words = text.split(" ")
    prefix = " ".join(words[:BASMALA_WORDS])
    if normalize_arabic(prefix) != NORMALIZED_BASMALA:
        raise ValueError(f"Expected text to start with the basmala: {text!r}")
    return " ".join(words[BASMALA_WORDS:])


def build_aya_rows(simple: dict[AyaKey, str], uthmani: dict[AyaKey, str]) -> list[dict[str, Any]]:
    if simple.keys() != uthmani.keys():
        missing = simple.keys() ^ uthmani.keys()
        raise ValueError(f"Simple and Uthmani texts have different ayas: {sorted(missing)[:10]}")

    rows = []
    for index, (surah, aya) in enumerate(sorted(simple), start=1):
        text_simple, text_uthmani = simple[surah, aya], uthmani[surah, aya]
        if has_prefixed_basmala(surah, aya):
            text_simple, text_uthmani = strip_basmala(text_simple), strip_basmala(text_uthmani)
        rows.append(
            {
                "id": index,
                "surah_id": surah,
                "number": aya,
                "text_simple": text_simple,
                "text_uthmani": text_uthmani,
            }
        )
    return rows


def parse_metadata(xml: str) -> list[dict[str, Any]]:
    root = ET.fromstring(xml)
    return [
        {
            "id": int(sura.attrib["index"]),
            "name_arabic": sura.attrib["name"],
            "name_transliterated": sura.attrib["tname"],
            "name_english": sura.attrib["ename"],
            "revelation_type": sura.attrib["type"].lower(),
            "revelation_order": int(sura.attrib["order"]),
            "aya_count": int(sura.attrib["ayas"]),
            "has_basmala": int(sura.attrib["index"]) not in SURAHS_WITHOUT_PREFIXED_BASMALA,
        }
        for sura in root.iter("sura")
    ]


def check_aya_counts(surah_rows: list[dict[str, Any]], aya_rows: list[dict[str, Any]]) -> None:
    if len(aya_rows) != TOTAL_AYAS:
        raise ValueError(f"Expected {TOTAL_AYAS} ayas, got {len(aya_rows)}")
    counts: dict[int, int] = {}
    for row in aya_rows:
        counts[row["surah_id"]] = counts.get(row["surah_id"], 0) + 1
    expected = {row["id"]: row["aya_count"] for row in surah_rows}
    if counts != expected:
        raise ValueError("Aya counts in the texts don't match quran-data.xml")


def copy_rows(session: Session, model: type[Base], rows: list[dict[str, Any]]) -> None:
    """Bulk-load rows with COPY: one stream instead of a network round trip per batch."""
    columns = list(rows[0])
    statement = sql.SQL("COPY {} ({}) FROM STDIN").format(
        sql.Identifier(model.__tablename__),
        sql.SQL(", ").join(map(sql.Identifier, columns)),
    )
    cursor = session.connection().connection.cursor()
    with cursor.copy(statement) as copy:
        for row in rows:
            copy.write_row([row[column] for column in columns])


def main(settings: Settings | None = None) -> None:
    with SIMPLE_PATH.open(encoding="utf-8") as f:
        simple = parse_text(f)
    with UTHMANI_PATH.open(encoding="utf-8") as f:
        uthmani = parse_text(f)
    aya_rows = build_aya_rows(simple, uthmani)
    surah_rows = parse_metadata(METADATA_PATH.read_text(encoding="utf-8"))
    check_aya_counts(surah_rows, aya_rows)
    with MORPHOLOGY_PATH.open(encoding="utf-8") as f:
        morphology = parse_morphology(f)
    aya_ids = {(row["surah_id"], row["number"]): row["id"] for row in aya_rows}
    word_rows, segment_rows = build_rows(morphology, aya_ids)

    session_factory = build_session_factory(build_engine(settings or get_settings()))
    with session_factory.begin() as session:
        for model in (Segment, Word, Aya, Surah):
            session.execute(delete(model))
        copy_rows(session, Surah, surah_rows)
        copy_rows(session, Aya, aya_rows)
        copy_rows(session, Word, word_rows)
        copy_rows(session, Segment, segment_rows)

    print(
        f"Loaded {len(surah_rows)} surahs, {len(aya_rows)} ayas, "
        f"{len(word_rows)} words and {len(segment_rows)} segments."
    )


if __name__ == "__main__":
    main()
