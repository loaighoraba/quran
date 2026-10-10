"""Interactive IPython shell with the database session and models loaded, like `rails console`.

Run with: uv run python -m app.scripts.console

Connects to the database in .env, which may be production; `s` is a plain session, so
nothing is written unless you call s.commit().
"""

from collections.abc import Callable
from typing import Any

from IPython import start_ipython
from sqlalchemy import delete, func, insert, select, text, update
from traitlets.config import Config

from app.config import Settings, get_settings
from app.db import build_engine, build_session_factory
from app.models import Aya, Segment, Surah, Word


def main(
    settings: Settings | None = None,
    start_shell: Callable[..., Any] = start_ipython,
) -> None:
    engine = build_engine(settings or get_settings())
    session_factory = build_session_factory(engine)
    namespace = {
        "engine": engine,
        "s": session_factory(),
        "select": select,
        "insert": insert,
        "update": update,
        "delete": delete,
        "func": func,
        "text": text,
        "Aya": Aya,
        "Segment": Segment,
        "Surah": Surah,
        "Word": Word,
    }
    config = Config()
    config.TerminalInteractiveShell.banner2 = (
        f"Connected to {engine.url.render_as_string(hide_password=True)}\n"
        f"Loaded: {', '.join(namespace)}\n"
    )
    start_shell(argv=[], user_ns=namespace, config=config)


if __name__ == "__main__":
    main()
