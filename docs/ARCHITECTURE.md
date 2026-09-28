# Architecture

One multi-tenant backend serves every site. The intent router sends plain questions to
RAG, action requests to the task engine, and "human please" straight to the escalation
queue. The task engine is the differentiator: its queues live in Redis and its task
records in PostgreSQL so nothing is lost on restart.

```
                         ┌────────────────────┐
 Customer ──message──▶   │   Intent router     │
                         └─────────┬───────────┘
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
              ┌───────────┐  ┌───────────┐  ┌──────────────┐
              │    RAG    │  │   Task    │  │  Escalation  │
              │  (answer  │  │  engine   │  │    queue     │
              │ + source) │  │ (plan +   │  │ (FIFO/skill, │
              └───────────┘  │  execute) │  │  priority)   │
                              └─────┬─────┘  └──────┬───────┘
                                    │ on failure     │
                                    ▼                ▼
                              ┌───────────┐   ┌─────────────┐
                              │ Undo stack│   │ Agent inbox │
                              │(compensate)│──▶│ / Zendesk   │
                              └───────────┘   └─────────────┘
```

A failed step in the task engine first runs the undo stack (saga-style compensation),
then moves the task to the escalation queue with its full step trail attached.

## Core data model

- `tenants`, `sites` (theme tokens, settings), `users` (admins, agents)
- `conversations`, `messages`, `feedback`
- `tasks` (state, priority, deadline, owner), `task_steps` (order, depends_on, status, compensation), `dead_letters`
- `documents`, `document_chunks` (pgvector column), `eval_cases`

See [`DATA_MODEL.md`](./DATA_MODEL.md) for field-level detail (to be filled in during Sprint 0/1).

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Widget | Preact + TypeScript, Vite, Shadow DOM | Tiny bundle, isolated styles |
| Dashboard + agent inbox | React + TypeScript, Tailwind | Fast to build, one design system |
| API | Python 3.12 + FastAPI, WebSockets / SSE | Streaming answers; standard for AI work |
| Task workers | Python workers on Redis Streams (or Celery) | Priority queues, retries, consumer groups |
| LLM | Hosted LLM API — small model for routing, larger model for planning | Cost control; swap models behind one interface |
| Retrieval | Embedding model + PostgreSQL pgvector | One database for data and vectors |
| Cache and rate limits | Redis | LRU cache, token buckets, sessions |
| Hosting | Docker on AWS (ECS Fargate for MVP, EKS later), CloudFront CDN for the widget | Low ops for a small team; CDN keeps the widget fast |
| IaC and secrets | Terraform, AWS Secrets Manager | Repeatable environments; no keys in code |
| Observability | Datadog or Grafana + Sentry; Langfuse for LLM traces | Latency, errors, token cost, answer quality |
| Integrations | Shopify Admin API, WooCommerce REST, Zendesk API, webhooks | Covers the first customer segment |

## Non-functional targets

- First token < 1.5s, full answer < 3s for 95% of messages
- 99.9% monthly availability for the chat API
- 1,000 concurrent chats across tenants at launch
- Widget loader < 15 KB gzipped, no layout shift on host page
- Tenant isolation, signed customer tokens, encryption in transit/at rest, PII masking before the LLM
- GDPR/CCPA export and deletion; configurable retention
- WCAG 2.1 AA
