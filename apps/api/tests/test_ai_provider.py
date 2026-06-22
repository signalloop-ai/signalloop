from signalloop_api.ai_policy import SOCRATIC_REDIRECT_MESSAGE
from signalloop_api.ai_provider import extract_response_text, parse_ai_decision


def test_extract_response_text_from_message_output() -> None:
    payload = {
        "output": [
            {"type": "reasoning", "content": []},
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "Focus on the observed status code mismatch first.",
                    }
                ],
            },
        ]
    }

    assert extract_response_text(payload) == "Focus on the observed status code mismatch first."


def test_parse_ai_decision_uses_socratic_message_for_no_issue_identified_without_message() -> None:
    decision = parse_ai_decision(
        '{"allowed": false, "policy_tags": ["no_issue_identified"], "message": ""}',
        "Is my code correct?",
        [],
    )

    assert decision.allowed is False
    assert decision.policy_tags == ["no_issue_identified"]
    assert decision.message == SOCRATIC_REDIRECT_MESSAGE
