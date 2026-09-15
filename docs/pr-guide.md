# Pull request description guide

Keep the body to **What** and **Why**. Skip Test plan for now (habit for later).

## Title

One line that a stranger could skim: verb + subject (+ scope if useful).

Examples: `Add workspace membership repository`, `Rename workspace services for clarity`

## What

What changed; the **outcome of the branch**, not a commit changelog.

- Prefer **bullets** (one outcome per bullet)
- Optional one-line lead only when it helps frame several bullets
- Name behavior, API shape, or design move (e.g. “split membership from workspace”)
- If a bullet could be copy-pasted from `git log`, drop it; commits already cover steps

## Why

Why this change exists; the problem or goal, not a restatement of What.

- One short paragraph is enough (bullets only if you have distinct reasons)
- Tie to a real need (clarity, correctness, scoping, habits) when you can

## Example

**Title:** `Normalize repositories and split workspace membership`

```markdown
## What
- One persistence idiom across repositories (`*Record` / `*CreateData`, shared flush/refresh + `to_record` via `BaseRepository`)
- Split workspace membership into its own repository and service
- Short CRUD names at the workspace API/service boundary
- Stable task list ordering / param order; `revoke_all` without N+1

## Why
The repository layer had grown several parallel styles, and membership lived inside workspace persistence. That made the next features harder to reason about. This branch locks one idiom and a clean membership boundary before more design/auth work.
```
