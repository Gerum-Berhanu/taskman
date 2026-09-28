# Writing the README

The root README should answer:

1. What Taskman is (one short paragraph)
2. Requirements (Python / uv / Postgres / Redis / optional Just & Docker)
3. Setup (`uv sync`, copy `env.example` → `env`, start Redis, migrate)
4. How to run on the host (`just dev` / profile recipes) and via Compose
5. How to run commands in containers (`docker compose exec` / `docker exec`)
6. Where to try it (`/docs`)
7. Link to deeper docs under `docs/`

Keep it accurate to the current stack. Details and process notes belong in `docs/`, not in a novel-length README — but operational gotchas (Redis before startup, Compose `--env-file` vs `exec`) belong in the README when they save hours.
