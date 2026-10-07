# Build stage: install locked dependencies into /app/.venv with uv
FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Dependencies first, so code changes don't invalidate this layer
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY . .
RUN uv sync --locked --no-dev


# Runtime stage: just Python, the virtualenv and the code
FROM python:3.14-slim

RUN useradd --create-home --uid 1000 app

WORKDIR /app
COPY --from=builder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER app

EXPOSE 8080

# App Platform terminates TLS at its load balancer and forwards X-Forwarded-* headers
CMD ["fastapi", "run", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
