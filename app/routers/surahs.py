from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.db import SessionDep
from app.models import Surah

router = APIRouter(prefix="/surahs", tags=["surahs"])


class SurahOut(BaseModel):
    id: int
    name_arabic: str
    name_transliterated: str
    name_english: str
    revelation_type: Literal["meccan", "medinan"]
    aya_count: int


@router.get("")
def list_surahs(session: SessionDep) -> list[SurahOut]:
    """All 114 surahs in order, for picking ranges by name."""
    surahs = session.scalars(select(Surah).order_by(Surah.id))
    return [SurahOut.model_validate(surah, from_attributes=True) for surah in surahs]
