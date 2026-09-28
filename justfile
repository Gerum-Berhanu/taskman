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

pytest $TASKMAN_ENV="test":
    uv run pytest -q

# Staging stack (Compose). --env-file supplies POSTGRES_* / REDIS_* for URL interpolation.
compose-staging:
    docker compose --env-file env/env-compose/.env.staging up -d --build

# Production stack = staging base + compose.prod.yaml overrides.
compose-prod:
    docker compose --env-file env/env-compose/.env.production -f compose.yaml -f compose.prod.yaml up -d --build

compose-staging-down:
    docker compose --env-file env/env-compose/.env.staging down

compose-prod-down:
    docker compose --env-file env/env-compose/.env.production -f compose.yaml -f compose.prod.yaml down
