from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy import text

from app.db import SessionDep, engine
from app.routers import stats, surahs


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    engine.dispose()


app = FastAPI(title="Quran API", lifespan=lifespan)
app.include_router(stats.router)
app.include_router(surahs.router)
# The React single-page app, built by `npm run build` in frontend/. API routes take priority;
# other paths fall back to index.html for client-side routing.
app.frontend("/", directory=Path(__file__).resolve().parents[1] / "frontend" / "dist")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
def health_db(session: SessionDep) -> dict[str, str]:
    session.execute(text("SELECT 1"))
    return {"status": "ok"}
