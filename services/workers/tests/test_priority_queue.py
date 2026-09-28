from workers.priority_queue import TaskPriorityQueue


def test_pops_lowest_priority_number_first() -> None:
    q = TaskPriorityQueue()
    q.push("low-priority", priority=5, deadline_epoch=100.0)
    q.push("urgent", priority=1, deadline_epoch=200.0)
    q.push("mid", priority=3, deadline_epoch=50.0)

    assert q.pop() == "urgent"
    assert q.pop() == "mid"
    assert q.pop() == "low-priority"


def test_ties_broken_by_earlier_deadline() -> None:
    q = TaskPriorityQueue()
    q.push("later", priority=1, deadline_epoch=200.0)
    q.push("sooner", priority=1, deadline_epoch=100.0)

    assert q.pop() == "sooner"
