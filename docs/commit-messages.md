# Commit messages

Use short Conventional Commits:

- `feat:` new user-facing capability
- `fix:` bug fix
- `refactor:` improve structure or clarity without changing behavior
- `style:` rename or cosmetic consistency only — no behavior or structure change
- `docs:` documentation only
- `test:` tests only
- `chore:` tooling, scaffold, deps
- `wip:` incomplete work not ready to merge (feature branches only)

**`style:` vs `refactor:`:** use `style:` for renames and surface consistency (e.g. handler names matching a domain prefix). Use `refactor:` when you move code, split modules, change layering, or reshape APIs internally — even if behavior stays the same.

Examples:

- `chore: initial project scaffold`
- `feat: add create task endpoint`
- `fix: return 404 when task is missing`
- `refactor: move task routes into APIRouter and DRY 404 handling`
- `style: rename workspace create handler to create_workspace`
- `docs: explain how to run the API`
- `wip: add ClientSession and RefreshToken models`

Prefer one focused change per commit.

Use `wip:` on feature branches when you land new pieces that are not fully integrated or green yet. Before merging to `main`, prefer coherent `feat:` / `refactor:` / `style:` / etc. commits (squash or rewrite `wip:` commits as needed).
