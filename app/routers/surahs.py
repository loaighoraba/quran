from fastapi import APIRouter
from sqlalchemy import select

from app.db import SessionDep
from app.models import Surah
from app.routers.schemas import SurahOut

router = APIRouter(prefix="/surahs", tags=["surahs"])


@router.get("")
def list_surahs(session: SessionDep) -> list[SurahOut]:
    """All 114 surahs in order, for picking ranges by name."""
    surahs = session.scalars(select(Surah).order_by(Surah.id))
    return [SurahOut.model_validate(surah, from_attributes=True) for surah in surahs]
