"""
Steps with dependencies (e.g. "verify identity" before "change address";
independent lookups run in parallel) are modeled as a DAG and executed in
topological order. Raises on cycles so a bad plan never runs. See docs/PRD.md §3.
"""

from __future__ import annotations

from collections import defaultdict, deque


class CycleError(ValueError):
    pass


def topological_batches(depends_on: dict[str, list[str]]) -> list[list[str]]:
    """
    Given {step_id: [dependency_step_ids]}, return batches of step_ids where
    each batch can run in parallel (all its dependencies are in earlier batches).
    """
    in_degree: dict[str, int] = {node: 0 for node in depends_on}
    dependents: dict[str, list[str]] = defaultdict(list)

    for node, deps in depends_on.items():
        for dep in deps:
            dependents[dep].append(node)
            in_degree[node] += 1

    ready = deque(sorted(node for node, deg in in_degree.items() if deg == 0))
    batches: list[list[str]] = []
    seen = 0

    while ready:
        batch = list(ready)
        ready.clear()
        batches.append(batch)
        seen += len(batch)

        for node in batch:
            for dependent in dependents[node]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    ready.append(dependent)

    if seen != len(depends_on):
        raise CycleError("task plan has a dependency cycle")

    return batches
