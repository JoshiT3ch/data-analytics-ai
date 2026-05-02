import os
import unittest
from unittest.mock import patch
from uuid import uuid4

from src.core import executor


class ExecutorTests(unittest.TestCase):
    def setUp(self):
        os.makedirs("data/raw", exist_ok=True)
        os.makedirs("outputs", exist_ok=True)
        os.makedirs("tmp", exist_ok=True)
        self.sample_file = "data/raw/test_executor_unit.xlsx"
        self.cleaned_file = "outputs/test_executor_unit_cleaned.xlsx"
        self.memory_file = f"tmp/test_executor_memory_{uuid4().hex}.json"

        with open(self.sample_file, "wb") as file:
            file.write(b"placeholder")

    def tearDown(self):
        for file_path in (self.sample_file, self.cleaned_file, self.memory_file):
            if os.path.exists(file_path):
                os.remove(file_path)

    def test_multi_step_chains_previous_output(self):
        def fake_route(command, file_path):
            if command == "clean-duplicates":
                output_file = self.cleaned_file
                with open(output_file, "wb") as file:
                    file.write(b"cleaned")
                return {
                    "status": "success",
                    "output_file": output_file,
                    "message": "cleaned",
                }

            return {
                "status": "success",
                "output_file": "outputs/test_cleaned_summary.txt",
                "message": f"summarized {file_path}",
            }

        plan = [
            {"command": "clean-duplicates", "file_path": self.sample_file},
            {"command": "summarize"},
        ]

        with patch("src.core.executor.route_command", side_effect=fake_route):
            with patch("src.core.executor._write_log", return_value="logs/test.json"):
                with patch("src.core.memory.MEMORY_FILE", self.memory_file):
                    result = executor.execute_plan(plan)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["results"][1]["input_file"], self.cleaned_file)
        self.assertEqual(result["log_file"], "logs/test.json")

    def test_missing_file_suggests_closest_match(self):
        result = executor.execute_plan(
            [{"command": "summarize", "file_path": "data/raw/test_executor_unt.xlsx"}],
            dry_run=True,
        )

        self.assertEqual(result["status"], "error")
        self.assertIn(
            "Did you mean: data/raw/test_executor_unit.xlsx?",
            result["message"],
        )

    def test_invalid_command_is_rejected_before_execution(self):
        result = executor.execute_plan(
            [{"command": "delete-everything", "file_path": self.sample_file}],
            dry_run=True,
        )

        self.assertEqual(result["status"], "error")
        self.assertIn("Unsupported command", result["message"])

    def test_mixed_valid_invalid_steps_stop_at_invalid_step(self):
        plan = [
            {"command": "summarize", "file_path": self.sample_file},
            {"command": "unknown", "file_path": self.sample_file},
        ]

        result = executor.execute_plan(plan, dry_run=True)

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["failed_step"], 2)
        self.assertEqual(len(result["results"]), 1)


if __name__ == "__main__":
    unittest.main()
