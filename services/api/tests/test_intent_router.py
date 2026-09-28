from app.core.intent_router import classify_intent


def test_human_request_routes_to_human() -> None:
    assert classify_intent("can I talk to a human?").kind == "human"


def test_return_request_routes_to_action() -> None:
    assert classify_intent("I want to return item 2").kind == "action"


def test_generic_question_routes_to_question() -> None:
    assert classify_intent("what is your shipping policy?").kind == "question"
