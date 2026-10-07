# quran

FastAPI service.

## Development

```sh
uv sync
uv run fastapi dev        # http://127.0.0.1:8000, docs at /docs
uv run pytest
```

## Claude Code skills

`.claude/skills/` holds agent skills for Claude Code. `fastapi` is a symlink into
the FastAPI package inside `.venv`, so run `uv sync` first or it will be a broken link.
