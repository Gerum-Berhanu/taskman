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

# Clears orphaned reload workers left on the port by a previous dev session.
[private]
free-port port="8000":
    @powershell.exe -NoLogo -ExecutionPolicy Bypass -File scripts/free-port.ps1 -Port {{port}}

dev: free-port
    -uv run fastapi dev

staging $TASKMAN_ENV="staging":
    -uv run fastapi run

prod $TASKMAN_ENV="production":
    -uv run fastapi run

test $TASKMAN_ENV="test": (free-port "8765")
    -uv run fastapi dev --port 8765

migrate:
    uv run alembic upgrade head

migrate-staging $TASKMAN_ENV="staging":
    uv run alembic upgrade head

migrate-prod $TASKMAN_ENV="production":
    uv run alembic upgrade head

migrate-test $TASKMAN_ENV="test":
    uv run alembic upgrade head

# Pytest uses its own SQLite DB via conftest (not env/.env.test).
pytest:
    uv run pytest -q