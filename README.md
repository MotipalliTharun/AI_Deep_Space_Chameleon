# AI Space Chameleon

A one-line embeddable support widget that auto-themes to any website, answers
customers with RAG, runs multi-step requests through a data-structure-based
task engine ("AI Stacks and Queues"), and hands the chat to a human agent
with full context when it cannot finish.

Full plan: [`AI Space Chameleon — Project Plan.pdf`](./AI%20Space%20Chameleon%20—%20Project%20Plan.pdf)
· extracted reference copy at [`docs/PRD.md`](./docs/PRD.md).

MVP target launch: **Feb 1, 2027** (kickoff Oct 5, 2026, 7-person team, 5 sprints after discovery).

## The bet

1. **Chameleon widget** — one `<script>` tag, auto-themes to the host site, works on Shopify, WordPress, React or plain HTML.
2. **AI Stacks and Queues** — every request becomes a structured task: a priority queue orders work, a stack decomposes it into ordered sub-steps with rollback (undo stack / saga pattern), and a DAG + topological sort runs independent steps in parallel.
3. **Honest handoff** — when confidence drops, a step fails, or the customer asks, the task moves to a human agent queue with a summary, the full step trail and a suggested reply. Customers are never trapped.

## Repo layout

```
apps/
  widget/       Preact + TypeScript + Vite, Shadow DOM. Customer-facing chat bubble.
  dashboard/    React + TypeScript + Tailwind. Admin dashboard + agent inbox.
services/
  api/          Python 3.12 + FastAPI. Intent router, RAG, WebSocket/SSE streaming.
  workers/      Python workers on Redis Streams. Task engine: heap, stack, undo stack, DAG, dead-letter queue.
infra/
  terraform/    IaC for AWS (ECS Fargate + CloudFront CDN for MVP), Secrets Manager.
eval/
  cases/        RAG + task-planning eval suite (target: 300 cases).
  redteam/      Prompt-injection / abuse red-team set (target: 100% refusal).
docs/
  PRD.md, ARCHITECTURE.md, DATA_MODEL.md, CODING_STANDARDS.md
.github/workflows/  CI/CD pipeline (lint → unit → SAST/secret scan → integration → eval(quick) → build → deploy).
```

## Core data structures (the differentiator)

| Structure | Used for |
|---|---|
| Priority queue (min-heap) | Incoming task queue, ordered by SLA deadline / tier / urgency |
| Stack (LIFO) | Plan execution: task decomposed into sub-steps |
| Undo stack | Compensating actions per side-effecting step (saga pattern) |
| DAG + topological sort | Steps with dependencies; independent steps run in parallel |
| FIFO queue per agent group | Human escalation, one queue per skill |
| Dead-letter queue | Steps that fail after retries |
| Sliding window / token bucket | Rate limits per site / visitor |
| LRU cache | Frequent answers and embeddings |
| Finite state machine | Task lifecycle: queued → planning → running → waiting-on-customer → done/failed/escalated |

See [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) for the full system diagram and data model.

## Getting started (local dev)

```bash
cp .env.example .env          # fill in LLM provider key, etc.
docker compose up -d          # Postgres (pgvector) + Redis
cd services/api && pip install -e ".[dev]" && uvicorn app.main:app --reload
cd services/workers && pip install -e ".[dev]" && python -m workers.main
cd apps/widget && npm install && npm run dev
cd apps/dashboard && npm install && npm run dev
```

## MVP must-haves (v1 cut line)

- Widget with auto-theme, Shopify + WordPress install
- RAG over help articles with sources
- Task engine: priority queue, step stack, undo stack, dead-letter queue
- Three actions: order status, return/exchange, address change
- Escalation queue + built-in agent inbox + Zendesk ticket fallback
- Admin dashboard: setup, knowledge, tasks, conversations, feedback inbox
- Thumbs, CSAT and agent handoff ratings
- Eval suite (300 cases) and red-team set in CI

Anything else waits for v1.1 unless it replaces a must-have.

## Status

Sprint 0 (Foundation) scaffold — repo structure, CI/CD skeleton, skeleton widget + API,
coding standards. See [`docs/PRD.md`](./docs/PRD.md) section 9 for the full sprint plan.
