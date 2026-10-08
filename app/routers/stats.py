import unicodedata
from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import ColumnElement, Select, func, or_, select, true
from sqlalchemy.orm import InstrumentedAttribute

from app.arabic import normalize_arabic
from app.db import SessionDep
from app.models import Segment, Surah, Word
from app.ranges import merge_ranges, resolve_range

router = APIRouter(prefix="/stats", tags=["stats"])


class CountBy(StrEnum):
    # Written word, with the vocative يا split off: مريم matches يمريم but not ومريم
    word = "word"
    # Word without prefixes and suffixes: مريم matches يمريم and ومريم
    stem = "stem"
    # Dictionary form: قال matches قالوا, يقول, قل
    lemma = "lemma"
    # Root letters: رحم matches رحمن, رحيم, رحمة
    root = "root"


class Summary(BaseModel):
    ayas: int
    # The vocative يا counted as its own word, as in the simple script
    words: int
    # One word per Uthmani-script word (يمريم is one word)
    words_uthmani: int
    roots: int
    lemmas: int


class Frequency(BaseModel):
    value: str
    count: int


class Count(BaseModel):
    by: CountBy
    query: str
    count: int
    # word and stem: the diacritized forms matched; lemma: the lemmas matched; root: its lemmas
    breakdown: list[Frequency]


def aya_filter(
    session: SessionDep,
    range_: Annotated[
        list[str] | None,
        Query(
            alias="range",
            description="Aya ranges, repeatable: 2, 2-4, 2:255, 2:1-20 or 2:1-3:10. "
            "Omit for the whole Quran.",
        ),
    ] = None,
) -> ColumnElement[bool]:
    """Turn ?range=... into a filter on words.aya_id."""
    if not range_:
        return true()
    aya_counts = dict(session.execute(select(Surah.id, Surah.aya_count)).all())
    try:
        ranges = merge_ranges([resolve_range(value, aya_counts) for value in range_])
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return or_(*(Word.aya_id.between(first, last) for first, last in ranges))


type AyaFilterDep = Annotated[ColumnElement[bool], Depends(aya_filter)]


def normalize_query(by: CountBy, q: str) -> str:
    # Roots are stored without spaces (رحم); accept ر ح م too
    value = "".join(q.split()) if by is CountBy.root else q.strip()
    if not value or any(c.isspace() for c in value):
        raise HTTPException(status_code=422, detail=f"q must be a single {by}")
    return value if by in (CountBy.lemma, CountBy.root) else normalize_arabic(value)


def canonical(text: str) -> str:
    # NFD puts stacked diacritics in one order, so shadda + fatha matches fatha + shadda
    return unicodedata.normalize("NFD", text)


def matching_values(
    session: SessionDep, column: InstrumentedAttribute[str | None], value: str
) -> list[str]:
    """Lemmas or roots equal to value; failing that, those equal once diacritics are stripped.

    So عِلْم matches only عِلْم, while علم matches عِلْم, عَلِمَ and عَلَّمَ, and اله matches أله.
    """
    values = [v for v in session.scalars(select(column).distinct()) if v is not None]
    exact = [v for v in values if canonical(v) == canonical(value)]
    return exact or [v for v in values if normalize_arabic(v) == normalize_arabic(value)]


def stems() -> Select:
    return select().select_from(Segment).join(Word).where(Segment.kind == "stem")


def split_words() -> tuple[Select, ColumnElement[str]]:
    """Words joined to their split parts (يمريم -> rows يا, مريم), and the part column."""
    parts = func.unnest(Word.split_normalized).table_valued("part").render_derived()
    return select().select_from(Word).join(parts, true()), parts.c.part


@router.get("/summary")
def summary(session: SessionDep, in_range: AyaFilterDep) -> Summary:
    words = session.execute(
        select(
            func.count(func.distinct(Word.aya_id)),
            func.coalesce(func.sum(func.cardinality(Word.split_normalized)), 0),
            func.count(),
        ).where(in_range)
    ).one()
    roots, lemmas = session.execute(
        select(func.count(func.distinct(Segment.root)), func.count(func.distinct(Segment.lemma)))
        .join(Word)
        .where(in_range)
    ).one()
    return Summary(
        ayas=words[0], words=words[1], words_uthmani=words[2], roots=roots, lemmas=lemmas
    )


@router.get("/count")
def count(
    session: SessionDep,
    in_range: AyaFilterDep,
    by: CountBy,
    q: Annotated[
        str, Query(min_length=1, max_length=50, description="The word, stem, lemma or root")
    ],
) -> Count:
    value = normalize_query(by, q)
    match by:
        case CountBy.word:
            statement, part = split_words()
            statement = (
                statement.add_columns(Word.text_uthmani, func.count())
                .where(part == value)
                .group_by(Word.text_uthmani)
            )
        case CountBy.stem:
            statement = (
                stems()
                .add_columns(Segment.form, func.count())
                .where(Segment.form_normalized == value)
                .group_by(Segment.form)
            )
        case CountBy.lemma:
            # Every segment, so particles written as prefixes (و, ب) count too
            statement = (
                select(Segment.lemma, func.count())
                .join(Word)
                .where(Segment.lemma.in_(matching_values(session, Segment.lemma, value)))
                .group_by(Segment.lemma)
            )
        case CountBy.root:
            statement = (
                stems()
                .add_columns(Segment.lemma, func.count())
                .where(Segment.root.in_(matching_values(session, Segment.root, value)))
                .group_by(Segment.lemma)
            )
    rows = session.execute(statement.where(in_range)).all()
    # Every matched value is non-null (stems with a root always have a lemma); the check narrows
    # the lemma column's str | None type
    breakdown = sorted(
        (Frequency(value=v, count=c) for v, c in rows if v is not None),
        key=lambda f: (-f.count, f.value),
    )
    return Count(by=by, query=q, count=sum(f.count for f in breakdown), breakdown=breakdown)


@router.get("/top")
def top(
    session: SessionDep,
    in_range: AyaFilterDep,
    by: CountBy,
    limit: Annotated[int, Query(ge=1, le=500)] = 20,
) -> list[Frequency]:
    match by:
        case CountBy.word:
            statement, column = split_words()
            statement = statement.add_columns(column)
        case CountBy.stem:
            column = Segment.form_normalized
            statement = stems().add_columns(column)
        case CountBy.lemma:
            # Every segment, so particles written as prefixes (و, ب) count too
            column = Segment.lemma
            statement = select(column).join(Word).where(column.is_not(None))
        case CountBy.root:
            column = Segment.root
            statement = stems().add_columns(column).where(column.is_not(None))
    rows = session.execute(
        statement.add_columns(func.count())
        .where(in_range)
        .group_by(column)
        .order_by(func.count().desc(), column)
        .limit(limit)
    )
    return [Frequency(value=v, count=c) for v, c in rows]
