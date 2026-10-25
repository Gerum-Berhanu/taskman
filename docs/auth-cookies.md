# Auth cookies

Access stays in the JSON body as `Bearer`. Refresh and device identity are HttpOnly cookies.

## Client contract

| Credential | Where it lives | How the client sends it |
|------------|----------------|-------------------------|
| Access | JSON body (`access_token`, `token_type: bearer`) | `Authorization: Bearer <access_token>` |
| Refresh | HttpOnly cookie (`refresh_token`) | Sent automatically with cookie-aware requests; **not** in JSON |
| Device id | HttpOnly cookie (`device_id`) | Sent on **login** only; server mints when absent |

Login and refresh responses include only the access token in the body. Cookies are `HttpOnly`, `SameSite=Lax`, `Path=/` (`Secure` outside local development).

| Cookie | Lifetime | Cleared on logout? |
|--------|----------|--------------------|
| `refresh_token` | `refresh_token_expire_minutes` | **Yes** |
| `device_id` | ~400 days (`device_id_cookie_max_age_seconds`) | **No** (install identity survives logout) |

## Endpoints

- `POST /auth/login` — access JSON + sets refresh cookie + sets/echoes `device_id` cookie. If `device_id` is present, any existing session for that device is deleted and replaced. Stores `user_agent` and client IP on the new session (not updated on refresh).
- `POST /auth/refresh` — reads **refresh cookie only** (device cookie is ignored); rotates refresh; returns new access JSON
- `POST /auth/logout` / `POST /auth/logout-all` — read refresh cookie; on success clear refresh only (204); keep `device_id`
- `GET /auth/sessions` — Bearer access; list live sessions (`id`, `device_id`, `user_agent`, `ip_address`, timestamps, `is_current`). `is_current` is true when the `device_id` cookie matches that row.

Missing or invalid refresh cookie on cookie-auth routes → `401` (`Could not validate credentials`).

## Role of `device_id`

- **Login replace:** same browser/install (same `device_id` cookie) logging in again replaces that install’s session so an old refresh stops working.
- **Not used on refresh/logout:** those paths validate the refresh cookie alone. A missing or wrong `device_id` cookie does not fail refresh in this design.
- Two installs (no shared device cookie) can hold two live sessions for the same user.

## Session lifecycle

- A `client_sessions` row exists only while the session is live (`UNIQUE(device_id)` — one row per install).
- Logout, logout-all, refresh-token reuse, expiry, and inactive-user checks **delete** the session (CASCADE refresh tokens). There is no soft-revoke / `revoked_at`.
- Re-login with the same `device_id` deletes any existing row for that device, then creates a new session.
- Idle sessions that never logout are removed by the expired-session purge (`expires_at`).
- UA/IP are kept only while the session row exists (privacy: gone after logout/replace/purge).

## Browser / SPA notes

- Keep the access token in memory (or equivalent); do not put refresh or `device_id` in `localStorage`.
- Same-origin requests send cookies by default.
- Cross-origin callers need credentialed fetches (`credentials: "include"` / `withCredentials`) and a CORS setup that allows credentials — not configured in this note.

Do not expect `refresh_token` or `device_id` fields in OpenAPI response bodies for login/refresh.
