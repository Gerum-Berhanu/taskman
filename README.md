# Taskman

REST API for task management, built with FastAPI. The app uses JWT authentication, a layered architecture (routes → services → repositories), and in-memory persistence for now. PostgreSQL, workspaces, and RBAC are planned — see [project requirements](docs/project-requirements.md).

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
uv sync
cp .env.example .env   # then set SECRET_KEY (and DATABASE_URL when using a real DB)
```

## Run

```bash
uv run uvicorn app.main:app --reload
```

Or with the FastAPI CLI:

```bash
uv run fastapi dev
```

Health check: `GET /health`

## API docs

Interactive docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

**Implemented today**

| Method | Path | Notes |
|--------|------|--------|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | OAuth2 password form → JWT |
| GET | `/auth/me` | Current user (Bearer token) |
| POST | `/tasks` | Create task (auth required) |
| GET | `/tasks` | List tasks |
| GET/PATCH/DELETE | `/tasks/{task_id}` | Read, update, delete |

Authorize in `/docs` with a token from `/auth/login` (use email as username).

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/project-structure.md](docs/project-structure.md) | Folders, layers, and where to add code |
| [docs/project-requirements.md](docs/project-requirements.md) | Full capstone spec (target features) |
| [docs/commit-messages.md](docs/commit-messages.md) | Commit message conventions |
| [docs/README.md](docs/README.md) | Index of all docs |
