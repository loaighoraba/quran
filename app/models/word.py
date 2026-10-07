from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.aya import Aya
    from app.models.segment import Segment


class Word(Base):
    __tablename__ = "words"
    __table_args__ = (
        UniqueConstraint("aya_id", "number"),
        CheckConstraint("number >= 1", name="number_positive"),
    )

    # Global word index (1..77429), in Quran order
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    aya_id: Mapped[int] = mapped_column(ForeignKey("ayas.id"))
    # Word position within the aya
    number: Mapped[int] = mapped_column(SmallInteger)
    # Segment forms joined, so it always matches the morphology
    text_uthmani: Mapped[str] = mapped_column(Text)
    # Diacritics stripped, for loose search
    text_normalized: Mapped[str] = mapped_column(Text, index=True)

    aya: Mapped[Aya] = relationship(back_populates="words")
    segments: Mapped[list[Segment]] = relationship(back_populates="word", order_by="Segment.number")
