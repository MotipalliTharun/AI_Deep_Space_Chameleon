from workers.undo_stack import UndoStack


def test_rollback_runs_in_reverse_order() -> None:
    order: list[str] = []
    stack = UndoStack()
    stack.push("create_return_label", lambda: order.append("cancel_return_label"))
    stack.push("create_exchange_order", lambda: order.append("cancel_exchange_order"))

    undone = stack.rollback_all()

    assert undone == ["create_exchange_order", "create_return_label"]
    assert order == ["cancel_exchange_order", "cancel_return_label"]
    assert len(stack) == 0
