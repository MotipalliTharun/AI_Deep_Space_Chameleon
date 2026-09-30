# Dashboard authentication & authorization

Covers how admins and support agents sign in to the dashboard. (Widget
visitors use signed customer tokens: separate design, not covered here.)

## Model

| Table | Purpose |
|---|---|
| `tenants` | One customer workspace. Every other row is scoped to one. |
| `users` | Dashboard users. Email is globally unique and lower-cased. `password_hash` is nullable so SSO-only users can be added later. |
| `auth_sessions` | One signed-in device. Revoking it kills that device on its next request. |
| `refresh_tokens` | Single-use refresh tokens, SHA-256 hashed at rest. |
| `audit_events` | Append-only security log per tenant (logins, failures, user changes, token reuse). |

## Roles (RBAC)

| Role | Can |
|---|---|
| `owner` | Everything, including managing other owners. A workspace always keeps ≥ 1 active owner. |
| `admin` | Setup, knowledge, team (admins + agents), audit log. Cannot create, edit or remove owners. |
| `agent` | Agent inbox, conversations, tasks, feedback. |

Users cannot change their own role or deactivate themselves. Server-side checks
live in `app/api/deps.py` (`require_roles`) and `app/services/user_service.py`;
the dashboard hides what a role cannot use, but the API is the source of truth.

## Tokens and cookies

| Cookie | Contents | Flags | Lifetime |
|---|---|---|---|
| `sc_access` | HS256 JWT: `sub`, `tid`, `role`, `sid`, `iss`, `aud`, `exp` | httpOnly, SameSite=Lax, Path=/ | 15 min |
| `sc_refresh` | 256-bit opaque token | httpOnly, SameSite=Strict, Path=/v1/auth | 30 days |
| `sc_csrf` | Random token (double-submit) | SameSite=Strict, readable by JS | 30 days |

- Every request re-checks the session row, user, tenant and role, so logout,
  deactivation and role changes apply immediately rather than at token expiry.
- **Refresh rotation with reuse detection:** each refresh token works once. A used
  token presented again (after a 10 s grace for concurrent tabs) revokes the
  whole session and writes `auth.refresh_reuse_detected` to the audit log.
- **CSRF:** cookie-authenticated `POST/PATCH/DELETE` must send `X-CSRF-Token`
  equal to the `sc_csrf` cookie. `Authorization: Bearer` callers are exempt.
- In development the dashboard proxies `/v1` through Vite so cookies stay
  same-origin. In production serve the dashboard and API under one site
  (e.g. `app.example.com` + `app.example.com/v1` via CloudFront/ALB) and set
  `COOKIE_SECURE=true`.

## Sign-in hardening

- Argon2id password hashing, rehashed transparently when parameters change.
- NIST 800-63B password policy: ≥ 12 chars, deny-list, no email name. No forced rotation.
- Identical responses and timing for unknown email vs. wrong password.
- Sliding-window rate limit: 10/min per email, 50/min per IP (429 + `Retry-After`).
- Lockout: 10 consecutive failures lock the account for 15 min (HTTP 423).
- Password change signs out every other session.
- Production refuses to boot with the dev JWT secret or insecure cookies.

## API

| Method | Path | Who |
|---|---|---|
| POST | `/v1/auth/signup` | anyone (disable with `ALLOW_SELF_SIGNUP=false`) |
| POST | `/v1/auth/login` · `/refresh` · `/logout` | anyone |
| GET | `/v1/auth/me` · `/sessions` | signed in |
| POST | `/v1/auth/change-password` · `/logout-all` | signed in |
| DELETE | `/v1/auth/sessions/{id}` | signed in (own sessions) |
| GET/POST | `/v1/users` | owner, admin |
| PATCH | `/v1/users/{id}` | owner, admin (role rules above) |
| GET | `/v1/audit-events?action=&before=&limit=` | owner, admin |

## Operations

```bash
cd services/api
alembic upgrade head
python -m app.cli create-owner --company "Acme" --email ops@acme.com --name "Ops"  # prompts for password
```

## Roadmap (not in this phase)

- Redis-backed rate limiter (the in-memory one is per-replica).
- Email invites + password reset (needs the notification service).
- OIDC / SAML SSO for the Scale plan (users table is already SSO-ready).
- TOTP / WebAuthn MFA.
- Breached-password check (HIBP k-anonymity) in place of the static deny list.
