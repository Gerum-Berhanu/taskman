# Commit messages

Use short Conventional Commits:

- `feat:` new user-facing capability
- `fix:` bug fix
- `refactor:` improve structure or clarity without changing behavior
- `docs:` documentation only
- `test:` tests only
- `chore:` tooling, scaffold, deps
- `wip:` incomplete work not ready to merge (feature branches only)

Examples:

- `chore: initial project scaffold`
- `feat: add create task endpoint`
- `fix: return 404 when task is missing`
- `refactor: move task routes into APIRouter and DRY 404 handling`
- `docs: explain how to run the API`
- `wip: add ClientSession and RefreshToken models`

Prefer one focused change per commit.

Use `wip:` on feature branches when you land new pieces that are not fully integrated or green yet. Before merging to `main`, prefer coherent `feat:` / `refactor:` / etc. commits (squash or rewrite `wip:` commits as needed).
