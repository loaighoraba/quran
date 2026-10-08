from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.word import Word


class Segment(Base):
    """A morpheme of a word, from the Quranic Arabic Corpus morphology."""

    __tablename__ = "segments"
    __table_args__ = (
        UniqueConstraint("word_id", "number"),
        CheckConstraint("number >= 1", name="number_positive"),
        CheckConstraint("pos IN ('N', 'V', 'P')", name="pos"),
        CheckConstraint("kind IN ('prefix', 'stem', 'suffix')", name="kind"),
        Index("ix_segments_features", "features", postgresql_using="gin"),
    )

    # Global segment index (1..130030), in Quran order
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id"))
    # Segment position within the word
    number: Mapped[int] = mapped_column(SmallInteger)
    # Empty for elided suffixes (e.g. the 1st-person ي)
    form: Mapped[str] = mapped_column(Text)
    # Diacritics stripped, so a stem matches regardless of case ending (مَرْيَمَ, مَرْيَمُ)
    form_normalized: Mapped[str] = mapped_column(Text, index=True)
    # Coarse part of speech: N(oun), V(erb), P(article)
    pos: Mapped[str] = mapped_column(String(1))
    kind: Mapped[str] = mapped_column(String(6))
    root: Mapped[str | None] = mapped_column(Text, index=True)
    lemma: Mapped[str | None] = mapped_column(Text, index=True)
    # Verb form (VF), 1..12
    verb_form: Mapped[int | None] = mapped_column(SmallInteger)
    mood: Mapped[str | None] = mapped_column(Text)
    # Particle family (FAM), e.g. إِنّ or كَان
    family: Mapped[str | None] = mapped_column(Text)
    # Remaining flags, e.g. {DET}, {M,GEN}, {PERF,3MS}; query with features @> '{GEN}'
    features: Mapped[list[str]] = mapped_column(ARRAY(Text))

    word: Mapped[Word] = relationship(back_populates="segments")
