# Taskman development commands

# Cross-platform task runner: https://github.com/casey/just
# Install: winget install Casey.Just  |  brew install just  |  cargo install just
#
# Config merge (in app/core/config.py): process env > env/.env.{TASKMAN_ENV} > env/.env
# TASKMAN_ENV selects the profile (default: development).
# `$NAME=...` on a recipe is Just-native env export (any shell).
# `windows-shell` applies on Windows only (Just defaults to `sh` there otherwise).

set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

default:
    @just --list
    
dev port="8000":
    -uv run fastapi dev --port {{port}}

# Run dev environment without automatic reload.
run port="8000":
    -uv run fastapi run --port {{port}}

staging $TASKMAN_ENV="staging":
    -uv run fastapi run

prod $TASKMAN_ENV="production":
    -uv run fastapi run

test port="8765" $TASKMAN_ENV="test":
    -uv run fastapi dev --port {{port}}

migrate:
    uv run alembic upgrade head

migrate-staging $TASKMAN_ENV="staging":
    uv run alembic upgrade head

migrate-prod $TASKMAN_ENV="production":
    uv run alembic upgrade head

migrate-test $TASKMAN_ENV="test":
    uv run alembic upgrade head

pytest:
    uv run pytest -q
