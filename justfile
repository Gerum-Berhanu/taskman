# Cross-platform task runner: https://github.com/casey/just
# Install: winget install Casey.Just  |  brew install just  |  cargo install just
#
# Config merge (in app/core/config.py): process env > env/.env.{TASKMAN_ENV} > env/.env
# TASKMAN_ENV selects the profile (default: development).
#
# `$NAME=...` on a recipe is Just-native env export (works with any shell).
# `set windows-shell` is required because Just still defaults to Unix `sh`.

set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

default:
    @just --list

dev:
    -uv run uvicorn app.main:app --reload

prod $TASKMAN_ENV="production":
    -uv run uvicorn app.main:app

migrate:
    uv run alembic upgrade head

migrate-prod $TASKMAN_ENV="production":
    uv run alembic upgrade head

test:
    uv run pytest -q
