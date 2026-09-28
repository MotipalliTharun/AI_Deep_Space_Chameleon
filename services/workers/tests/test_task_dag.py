import pytest

from workers.task_dag import CycleError, topological_batches


def test_independent_steps_batch_together() -> None:
    # verify_identity -> address_change ; stock_check has no deps, runs alongside verify_identity
    plan = {
        "verify_identity": [],
        "stock_check": [],
        "address_change": ["verify_identity"],
    }
    batches = topological_batches(plan)
    assert batches[0] == sorted(["verify_identity", "stock_check"])
    assert batches[1] == ["address_change"]


def test_cycle_is_rejected() -> None:
    with pytest.raises(CycleError):
        topological_batches({"a": ["b"], "b": ["a"]})
