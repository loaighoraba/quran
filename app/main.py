from pathlib import Path

from fastapi import FastAPI
from sqlalchemy import text

from app.config import Settings, get_settings
from app.db import SessionDep, build_engine, build_session_factory
from app.routers import stats, surahs


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    engine = build_engine(settings)
    session_factory = build_session_factory(engine)

    app = FastAPI(title="Quran API")

    app.state.engine = engine
    app.state.session_factory = session_factory

    app.include_router(stats.router)
    app.include_router(surahs.router)
    app.frontend(
        "/",
        directory=Path(__file__).resolve().parents[1] / "frontend" / "dist",
        check_dir=False,
    )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/health/db")
    def health_db(session: SessionDep):
        session.execute(text("SELECT 1"))
        return {"status": "ok"}

    return app
