from signalloop_api.ai_policy import REDIRECT_MESSAGE, fallback_classify


def test_disallowed_full_solution_request_is_redirected() -> None:
    decision = fallback_classify("Find all bugs and give me the code for each issue.")

    assert decision.allowed is False
    assert "enumerate_defects" in decision.tags
    assert decision.redirect_message == REDIRECT_MESSAGE


def test_disallowed_final_explanation_request_is_redirected() -> None:
    decision = fallback_classify("Write my final explanation and decision log.")

    assert decision.allowed is False
    assert "final_explanation" in decision.tags


def test_allowed_public_test_question_passes() -> None:
    decision = fallback_classify("This public test assertion failed. How should I debug it?")

    assert decision.allowed is True
    assert decision.tags == ["general_allowed"]
