# Coding standards

## General
- Trunk-based via **GitHub Flow**: short-lived `feature/SC-xx` branches off a protected `main`, squash merges, [Conventional Commits](https://www.conventionalcommits.org/), release tags `vX.Y.Z`.
- Every PR: lint → unit tests → SAST/secret scan → integration tests → quick eval (100 cases, if AI-touching) → build → image scan → deploy to Dev.
- No PR merges with coverage below 80% or a red eval gate.

## TypeScript (widget, dashboard)
- Strict mode on (`"strict": true`). No `any` without a `// TODO(reason)` comment.
- Widget: no runtime dependency beyond Preact; keep the loader under 15 KB gzipped.
- Format/lint: Prettier + ESLint (airbnb-ish, adjusted for Preact/JSX).
- Components are function components; no class components.

## Python (api, workers)
- Python 3.12, type-hinted everywhere (`mypy --strict` on `app/` and `workers/`).
- Format/lint: `ruff` (lint + format), `black` off (ruff format instead).
- Structure: routers thin, business logic in `app/core`, no SQL in routers.
- Every side-effecting task step must define a compensation (undo) function — enforced by the property tests in `eval/` / `services/workers/tests`.

## Testing (see PRD §10 for the full matrix)
- Unit: pytest / Vitest, every PR.
- Data-structure property tests (Hypothesis): heap ordering, undo-stack LIFO reversal, DAG topological validity — every PR.
- Integration: pytest + Testcontainers (Redis + Postgres) — every PR.
- Failure injection: every PR touching the task engine.
- AI evals (Promptfoo/Ragas): PRs touching AI, full suite nightly.
- Red team: every AI PR + before release, 100% refusal required.
- E2E: Playwright, after deploy to staging.
- Load: k6, before release — 1,000 concurrent chats, p95 < 3s.

## Definition of done
- Merged via reviewed PR; CI green; coverage ≥ 80%
- Acceptance criteria verified by QA
- Eval scores equal or better for any AI change
- No new critical/high security findings
- Docs and runbook updated; demoed to the PM
