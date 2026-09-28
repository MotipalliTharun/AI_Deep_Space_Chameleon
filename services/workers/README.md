# Task workers

The AI Stacks and Queues engine: priority queue (heap), plan stack, undo
stack (saga compensation), DAG + topological sort, dead-letter queue. See
`docs/PRD.md` §3 for the design and §7 for how this fits the architecture.

```bash
pip install -e ".[dev]"
pytest
python -m workers.main
```
