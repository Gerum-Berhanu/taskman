# Taskman

REST API project scaffold.

## Requirements

- Python 3.x
- [uv](https://github.com/astral-sh/uv)

## Setup

```bash
uv sync
```

Copy `.env.example` to `.env` if you need local overrides.

## Run

```bash
uv run uvicorn app.main:app --reload
```

Open interactive docs at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

## Project structure

See [docs/project-structure.md](docs/project-structure.md).
