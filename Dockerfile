# syntax=docker/dockerfile:1

FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.15 /uv /uvx /bin/

WORKDIR /app

# Create a dedicated unprivileged runtime user.
RUN groupadd --system --gid 10001 appuser \
    && useradd --system \
        --uid 10001 \
        --gid 10001 \
        --create-home \
        --home-dir /home/appuser \
        appuser

# Switch to the non-root user
USER 10001:10001

# Copy dependency metadata first so Docker can cache dependency installation.
COPY pyproject.toml uv.lock ./

# Install production dependencies into /app/.venv.
#
# --no-install-project is intentional because this repository runs directly
# from source and does not currently define a separate build backend/package
# configuration for installing the application itself.
RUN uv sync --frozen --no-dev --no-install-project

# Copy application files and assign ownership to the non-root user.
COPY --chown=10001:10001 . .

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Migrations are executed separately during deployment.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]