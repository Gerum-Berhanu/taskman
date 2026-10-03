# Commit messages

Use short Conventional Commits:

- `feat:` new **user-facing** capability (API/behavior clients can use)
- `fix:` bug fix
- `refactor:` improve structure or clarity without changing behavior
- `style:` rename or cosmetic consistency only — no behavior or structure change
- `docs:` documentation only
- `test:` tests only
- `chore:` tooling, scaffold, deps
- `wip:` branch-only progress — green building blocks **or** unfinished work; not merge material as-is

**`feat:` vs `wip:`:** `feat` only when the capability ships (e.g. endpoint works). Schema/repo/helpers with no public behavior yet → `wip` on the feature branch; squash or rewrite into a real `feat` / `docs` / `test` before `main`.

**`style:` vs `refactor:`:** use `style:` for renames and surface consistency (e.g. handler names matching a domain prefix). Use `refactor:` when you move code, split modules, change layering, or reshape APIs internally — even if behavior stays the same.

Examples:

- `chore: initial project scaffold`
- `feat: add create task endpoint`
- `fix: return 404 when task is missing`
- `refactor: move task routes into APIRouter and DRY 404 handling`
- `style: rename workspace create handler to create_workspace`
- `docs: explain how to run the API`
- `wip: add task status aggregate and summary schema`

Prefer one focused change per commit.
