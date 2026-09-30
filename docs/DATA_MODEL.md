# Data model (v1 draft)

Placeholder for Sprint 0/1: turn this into real migrations under `services/api/app/models`
once the ORM (SQLAlchemy + Alembic, proposed) is wired up.

Implemented tables live in `services/api/app/models` with Alembic migrations in
`services/api/migrations`. Auth tables are documented in [`AUTH.md`](./AUTH.md).

## tenants  ✅ implemented
- id, name, slug (unique), plan, is_active, created_at, updated_at
## sites
- id, tenant_id, domain, theme_tokens (json), settings (json)
## users  ✅ implemented
- id, tenant_id, role (owner | admin | agent), email (unique), full_name, password_hash (nullable for SSO),
  is_active, failed_login_count, locked_until, last_login_at, password_changed_at
- TODO: skill_groups (json) when the escalation queue lands
## auth_sessions, refresh_tokens, audit_events  ✅ implemented
- see [`AUTH.md`](./AUTH.md)

## conversations
- id, tenant_id, site_id, customer_ref, channel, state, created_at
## messages
- id, conversation_id, role (customer | ai | agent), text, sources (json), created_at
## feedback
- id, message_id, type (thumbs | csat | agent_rating), value, reason, created_at

## tasks
- id, conversation_id, intent, state (queued|planning|running|waiting-on-customer|done|failed|escalated), priority, deadline, owner
## task_steps
- id, task_id, order, depends_on (json list), status, compensation (json), result (json)
## dead_letters
- id, task_step_id, reason, payload (json), created_at

## documents
- id, tenant_id, title, source_url, type (article|pdf|url)
## document_chunks
- id, document_id, text, embedding (vector), token_count
## eval_cases
- id, category (rag|plan|redteam), input, expected, last_score
