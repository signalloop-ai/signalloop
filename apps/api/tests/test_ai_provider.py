from signalloop_api.ai_provider import extract_response_text


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
