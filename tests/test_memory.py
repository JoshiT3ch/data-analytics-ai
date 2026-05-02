import os
import unittest
from unittest.mock import patch
from uuid import uuid4

from src.core import executor, memory


class MemoryTests(unittest.TestCase):
    def setUp(self):
        os.makedirs("tmp", exist_ok=True)
        os.makedirs("data/raw", exist_ok=True)
        self.memory_file = f"tmp/test_memory_{uuid4().hex}.json"
        self.sample_file = "data/raw/test_memory_unit.xlsx"

        with open(self.sample_file, "wb") as file:
            file.write(b"placeholder")

    def tearDown(self):
        for file_path in (self.memory_file, self.sample_file):
            if os.path.exists(file_path):
                os.remove(file_path)

    def test_load_memory_returns_empty_when_file_missing(self):
        with patch("src.core.memory.MEMORY_FILE", self.memory_file):
            self.assertEqual(memory.load_memory(), {})

    def test_save_memory_round_trips_safe_fields(self):
        stored_memory = {
            "latest_input_file": "data/raw/test.xlsx",
            "latest_output_file": "outputs/test_cleaned.xlsx",
            "latest_command": "clean-duplicates",
            "latest_plan": [
                {
                    "command": "clean-duplicates",
                    "file_path": "data/raw/test.xlsx",
                }
            ],
            "updated_at": "2026-05-02T10:00:00",
            "OPENAI_API_KEY": "should-not-be-stored",
        }

        with patch("src.core.memory.MEMORY_FILE", self.memory_file):
            memory.save_memory(stored_memory)
            loaded = memory.load_memory()

        self.assertEqual(loaded["latest_output_file"], "outputs/test_cleaned.xlsx")
        self.assertNotIn("OPENAI_API_KEY", loaded)

    def test_summarize_it_resolves_to_latest_output_file(self):
        stored_memory = {
            "latest_input_file": "data/raw/test.xlsx",
            "latest_output_file": "outputs/test_cleaned.xlsx",
            "latest_command": "clean-duplicates",
            "latest_plan": [],
            "updated_at": "2026-05-02T10:00:00",
        }
        plan = [{"command": "summarize", "file_path": "data/raw/test.xlsx"}]

        with patch("src.core.memory.MEMORY_FILE", self.memory_file):
            memory.save_memory(stored_memory)
            resolved = memory.resolve_file_reference("summarize it", plan)

        self.assertEqual(resolved[0]["file_path"], "outputs/test_cleaned.xlsx")

    def test_missing_file_resolves_to_latest_output_file(self):
        stored_memory = {
            "latest_input_file": "data/raw/test.xlsx",
            "latest_output_file": "outputs/test_no_empty.xlsx",
            "latest_command": "remove-empty-rows",
            "latest_plan": [],
            "updated_at": "2026-05-02T10:00:00",
        }
        plan = [{"command": "detect-columns", "file_path": "data/raw/test.xlsx"}]

        with patch("src.core.memory.MEMORY_FILE", self.memory_file):
            memory.save_memory(stored_memory)
            resolved = memory.resolve_file_reference("show me the columns", plan)

        self.assertEqual(resolved[0]["file_path"], "outputs/test_no_empty.xlsx")

    def test_dry_run_does_not_update_memory(self):
        plan = [{"command": "clean-duplicates", "file_path": self.sample_file}]

        with patch("src.core.memory.MEMORY_FILE", self.memory_file):
            result = executor.execute_plan(plan, dry_run=True)
            loaded = memory.load_memory()

        self.assertEqual(result["status"], "success")
        self.assertEqual(loaded, {})

    def test_clear_memory_removes_memory_file(self):
        with patch("src.core.memory.MEMORY_FILE", self.memory_file):
            memory.save_memory({"latest_command": "summarize"})
            self.assertTrue(os.path.exists(self.memory_file))
            memory.clear_memory()

        self.assertFalse(os.path.exists(self.memory_file))


if __name__ == "__main__":
    unittest.main()
