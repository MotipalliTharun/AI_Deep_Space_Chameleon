# Eval suite

Target for launch gate (PRD §9, §10): 300 RAG + task-planning cases, 100%
refusal on the red-team set, correctness ≥ 90%, groundedness ≥ 98%, plan
validity ≥ 95%.

- `cases/` — RAG and multi-step task-planning eval cases (target: 300).
- `redteam/` — prompt-injection, other-customer-data-request and abuse cases (target: 100% refusal).

Cases are plain JSON so `services/api`'s eval runner (Promptfoo/Ragas +
custom, per PRD §10) and CI can both consume them without extra tooling.
