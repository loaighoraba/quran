import unicodedata
from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import ColumnElement, Select, exists, func, or_, select, true
from sqlalchemy.orm import InstrumentedAttribute, selectinload

from app.arabic import normalize_arabic
from app.db import SessionDep
from app.models import Aya, Segment, Surah, Word
from app.ranges import merge_ranges, resolve_range
from app.routers.schemas import (
    AyaMatch,
    AyaMatches,
    Count,
    CountBy,
    Frequency,
    MatchedWord,
    Summary,
)

router = APIRouter(prefix="/stats", tags=["stats"])


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


def alef_variants(value: str) -> list[str]:
    """value with any of its alefs dropped: ثلاث -> ثلاث, ثلث."""
    positions = [i for i, c in enumerate(value) if c == "ا"][:6]
    variants = []
    for mask in range(2 ** len(positions)):
        dropped = {p for bit, p in enumerate(positions) if mask >> bit & 1}
        variants.append("".join(c for i, c in enumerate(value) if i not in dropped))
    return variants


def matches_form(
    column: ColumnElement[str], value: str, *, exact_exists: bool
) -> ColumnElement[bool]:
    """column == value, or failing any exact match, equal to value with some alefs dropped.

    The Uthmani script writes many long ā as a dagger alif, which normalizing strips (ثلاث is
    stored as ثلث), while people type the alif. Exact matches win, so قال doesn't match قل.
    """
    if exact_exists:
        return column == value
    return column.in_(alef_variants(value))


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


@dataclass
class Occurrences:
    """Where a word, stem, lemma or root occurs: what /count tallies and /ayas lists."""

    by: CountBy
    query: str
    # Words (joined to segments where needed) holding an occurrence; no columns selected yet
    statement: Select
    # The matched form to group a breakdown by; None for segments without one
    label: ColumnElement[str | None]


def occurrences(
    session: SessionDep,
    by: CountBy,
    q: Annotated[
        str, Query(min_length=1, max_length=50, description="The word, stem, lemma or root")
    ],
) -> Occurrences:
    value = normalize_query(by, q)
    match by:
        case CountBy.word:
            statement, part = split_words()
            exact = session.scalar(select(exists().where(Word.split_normalized.contains([value]))))
            statement = statement.where(matches_form(part, value, exact_exists=bool(exact)))
            # The simple script's spelling, with the alef; Uthmani where the scripts don't pair up
            label = func.coalesce(Word.text_simple, Word.text_uthmani)
        case CountBy.stem:
            exact = session.scalar(
                select(exists().where(Segment.kind == "stem", Segment.form_normalized == value))
            )
            statement = stems().where(
                matches_form(Segment.form_normalized, value, exact_exists=bool(exact))
            )
            label = Segment.form
        case CountBy.lemma:
            # Every segment, so particles written as prefixes (و, ب) count too
            statement = (
                select()
                .select_from(Segment)
                .join(Word)
                .where(Segment.lemma.in_(matching_values(session, Segment.lemma, value)))
            )
            label = Segment.lemma
        case CountBy.root:
            statement = stems().where(
                Segment.root.in_(matching_values(session, Segment.root, value))
            )
            label = Segment.lemma
    return Occurrences(by=by, query=q, statement=statement, label=label)


type OccurrencesDep = Annotated[Occurrences, Depends(occurrences)]


@router.get("/count")
def count(session: SessionDep, in_range: AyaFilterDep, found: OccurrencesDep) -> Count:
    rows = session.execute(
        found.statement.add_columns(found.label, func.count()).where(in_range).group_by(found.label)
    ).all()
    # Every matched value is non-null (stems with a root always have a lemma); the check narrows
    # the lemma column's str | None type
    breakdown = sorted(
        (Frequency(value=v, count=c) for v, c in rows if v is not None),
        key=lambda f: (-f.count, f.value),
    )
    return Count(
        by=found.by, query=found.query, count=sum(f.count for f in breakdown), breakdown=breakdown
    )


@router.get("/ayas")
def ayas(
    session: SessionDep,
    in_range: AyaFilterDep,
    found: OccurrencesDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
) -> AyaMatches:
    """The ayas containing the query, in Quran order, with the matched words flagged."""
    matched = (
        found.statement.add_columns(Word.aya_id, Word.number).where(in_range).distinct().subquery()
    )
    total = session.scalar(select(func.count(func.distinct(matched.c.aya_id)))) or 0
    aya_ids = list(
        session.scalars(
            select(matched.c.aya_id)
            .distinct()
            .order_by(matched.c.aya_id)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    )
    matched_numbers: dict[int, set[int]] = {aya_id: set() for aya_id in aya_ids}
    for aya_id, number in session.execute(
        select(matched.c.aya_id, matched.c.number).where(matched.c.aya_id.in_(aya_ids))
    ):
        matched_numbers[aya_id].add(number)
    rows = session.scalars(
        select(Aya).where(Aya.id.in_(aya_ids)).order_by(Aya.id).options(selectinload(Aya.words))
    )
    return AyaMatches(
        by=found.by,
        query=found.query,
        total=total,
        page=page,
        page_size=page_size,
        ayas=[
            AyaMatch(
                id=aya.id,
                surah=aya.surah_id,
                number=aya.number,
                words=[
                    MatchedWord(
                        text=word.text_uthmani, matched=word.number in matched_numbers[aya.id]
                    )
                    for word in aya.words
                ],
            )
            for aya in rows
        ],
    )


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
