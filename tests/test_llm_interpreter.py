import os
import unittest
from unittest.mock import patch

from src.ai import llm_interpreter


class _Message:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Message(content)


class _Response:
    def __init__(self, content):
        self.choices = [_Choice(content)]


class _Completions:
    def __init__(self, responses):
        self.responses = list(responses)

    def create(self, **kwargs):
        return _Response(self.responses.pop(0))


class _Chat:
    def __init__(self, responses):
        self.completions = _Completions(responses)


class _Client:
    responses = []

    def __init__(self, api_key):
        self.chat = _Chat(self.responses)


class LlmInterpreterTests(unittest.TestCase):
    def test_normalize_single_object_to_plan(self):
        plan = llm_interpreter.normalize_plan(
            {
                "command": "summarize",
                "file_path": "test.xlsx",
                "confidence": 0.9,
                "reason": "summary requested",
            },
            "summarize test.xlsx",
        )

        self.assertEqual(
            plan,
            [
                {
                    "command": "summarize",
                    "file_path": "data/raw/test.xlsx",
                    "confidence": 0.9,
                    "reason": "summary requested",
                }
            ],
        )

    def test_normalize_multi_step_plan_chains_transform_output(self):
        plan = llm_interpreter.normalize_plan(
            {
                "steps": [
                    {
                        "command": "clean-duplicates",
                        "file_path": "test.xlsx",
                        "confidence": 0.95,
                        "reason": "remove duplicates first",
                    },
                    {
                        "command": "summarize",
                        "file_path": "test.xlsx",
                        "confidence": 0.9,
                        "reason": "summarize the cleaned file",
                    },
                ]
            },
            "clean duplicate rows and then summarize test.xlsx",
        )

        self.assertEqual(plan[0]["file_path"], "data/raw/test.xlsx")
        self.assertEqual(plan[1]["file_path"], "outputs/test_cleaned.xlsx")

    def test_fallback_plan_handles_multi_step_request(self):
        plan = llm_interpreter._fallback_plan(
            "clean duplicate rows and then summarize test.xlsx",
            "test fallback",
        )

        self.assertEqual(
            [step["command"] for step in plan],
            ["clean-duplicates", "summarize"],
        )
        self.assertEqual(plan[0]["file_path"], "data/raw/test.xlsx")
        self.assertEqual(plan[1]["file_path"], "outputs/test_cleaned.xlsx")

    def test_malformed_llm_json_retries_then_uses_valid_response(self):
        fake_client_type = type("FakeOpenAI", (_Client,), {})
        fake_client_type.responses = [
            "not json",
            '{"steps":[{"command":"summarize","file_path":"test.xlsx","confidence":0.9,"reason":"ok"}]}',
        ]

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("src.ai.llm_interpreter.OpenAI", fake_client_type):
                result = llm_interpreter.interpret_user_request("summarize test.xlsx")

        self.assertEqual(result["steps"][0]["command"], "summarize")
        self.assertEqual(result["steps"][0]["file_path"], "data/raw/test.xlsx")

    def test_low_confidence_llm_falls_back_to_rules(self):
        fake_client_type = type("FakeOpenAI", (_Client,), {})
        fake_client_type.responses = [
            '{"steps":[{"command":"detect-columns","file_path":"test.xlsx","confidence":0.1,"reason":"unsure"}]}',
        ]

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("src.ai.llm_interpreter.OpenAI", fake_client_type):
                result = llm_interpreter.interpret_user_request("summarize test.xlsx")

        self.assertEqual(result["steps"][0]["command"], "summarize")
        self.assertIn("confidence", result["steps"][0]["reason"])


if __name__ == "__main__":
    unittest.main()
