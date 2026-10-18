# Service method conventions

Application services in `app/services/` are the use-case layer: routes and dependencies call them; they talk to repositories via the UoW.

## Public vs private

| Kind | Naming | Who calls it | Returns |
|------|--------|--------------|---------|
| **Public** | no leading `_` | Routes **or** DI (`app/dependencies/`) — anything outside this service class | Prefer `dto.api`. `None` for empty success (e.g. logout). Small domain values OK when the caller is not an HTTP body (e.g. `WorkspaceMemberRole` for RBAC). **Never** `dto.repository` `*Record` (especially anything carrying secrets like `hashed_password`). |
| **Private** | leading `_` | Only sibling methods on the same service | Anything useful internally (`*Record`, raw JWT `str`, helpers). |

If a method is only used to support other methods on the same class, prefix it with `_` and keep it private. If something outside the service needs it, it is public — and it must not leak persistence DTOs across that boundary.

## Examples

- `AuthService.login` → public, returns `Token`
- `AuthService._authenticate` → private, returns `UserRecord` for `login` only
- `AuthService._create_access_token` → private JWT helper
- `AuthService.get_user_from_token` → public (used by `CurrentUserDep`), returns `UserRead`
- `TaskService._validate_assignee` / `_invalidate_summary` → private helpers

## Do not

- Expose `*Record` from a public service method “because DI needs it” — map to an API DTO (or a narrow domain type) instead.
- Treat “not called from `api/`” as the only test for privacy; dependencies are still external callers.
