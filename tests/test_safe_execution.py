import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pandas as pd

from src.commands.clean_excel import clean_duplicates
from src.commands.undo import undo_last_action
from src.core import backup_manager, executor, session_memory


class SafeExecutionTests(unittest.TestCase):
    def setUp(self):
        os.makedirs("tmp", exist_ok=True)
        os.makedirs("data/raw", exist_ok=True)
        os.makedirs("outputs", exist_ok=True)

        unique = uuid4().hex
        self.input_file = f"data/raw/test_safe_{unique}.xlsx"
        self.output_file = f"outputs/test_safe_{unique}_cleaned.xlsx"
        self.session_file = Path(f"tmp/test_safe_session_{unique}.json")
        self.legacy_memory_file = f"tmp/test_safe_legacy_{unique}.json"
        self.backup_dir = Path(f"tmp/backups_{unique}")
        self.restore_dir = Path(f"tmp/outputs_{unique}")

        pd.DataFrame(
            [
                {"name": "Ada", "sales": 10},
                {"name": "Ada", "sales": 10},
                {"name": "Lin", "sales": 20},
            ]
        ).to_excel(self.input_file, index=False)

    def tearDown(self):
        for file_path in (
            self.input_file,
            self.output_file,
            self.session_file,
            self.legacy_memory_file,
        ):
            if os.path.exists(file_path):
                os.remove(file_path)

        for folder in (self.backup_dir, self.restore_dir):
            if folder.exists():
                for child in folder.iterdir():
                    child.unlink()
                folder.rmdir()

    def test_clean_duplicates_preview_does_not_write_output(self):
        result = clean_duplicates(self.input_file, preview=True)

        self.assertEqual(result["status"], "success")
        self.assertTrue(result["preview"])
        self.assertEqual(result["duplicate_rows"], 1)
        self.assertFalse(os.path.exists(self.output_file))

    def test_executor_creates_backup_and_session_memory_for_transform(self):
        plan = [{"command": "clean-duplicates", "file_path": self.input_file}]

        with patch("src.core.session_memory.SESSION_FILE", self.session_file):
            with patch("src.core.session_memory.SESSION_DIR", Path("tmp")):
                with patch("src.core.memory.MEMORY_FILE", self.legacy_memory_file):
                    with patch("src.core.backup_manager.BACKUP_DIR", self.backup_dir):
                        with patch("src.core.executor.create_backup", backup_manager.create_backup):
                            result = executor.execute_plan(plan)

        self.assertEqual(result["status"], "success")
        self.assertTrue(os.path.exists(self.output_file))

        backup_file = result["results"][0]["backup_file"]
        self.assertTrue(os.path.exists(backup_file))

        saved_session = json.loads(self.session_file.read_text(encoding="utf-8"))
        self.assertEqual(saved_session["current_file"], self.output_file)
        self.assertEqual(saved_session["last_command"], "clean-duplicates")
        self.assertEqual(saved_session["command_history"][0]["backup_file"], backup_file)
        self.assertEqual(
            saved_session["command_history"][0]["metadata"]["affected_rows"],
            1,
        )

    def test_undo_restores_latest_backup_to_new_output_file(self):
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        backup_file = self.backup_dir / "test_safe_before_clean_duplicates.xlsx"
        backup_file.write_bytes(Path(self.input_file).read_bytes())

        with patch("src.core.session_memory.SESSION_FILE", self.session_file):
            with patch("src.core.session_memory.SESSION_DIR", Path("tmp")):
                session_memory.save_session_memory(
                    {
                        "current_file": self.output_file,
                        "current_sheet": "Sheet1",
                        "last_command": "clean-duplicates",
                        "last_output_file": self.output_file,
                        "last_result_summary": "Removed 1 duplicate row.",
                        "command_history": [
                            {
                                "command": "clean-duplicates",
                                "input_file": self.input_file,
                                "output_file": self.output_file,
                                "summary": "Removed 1 duplicate row.",
                                "backup_file": backup_file.as_posix(),
                                "timestamp": "2026-05-04T10:30:00",
                            }
                        ],
                    }
                )

                with patch("src.core.memory.MEMORY_FILE", self.legacy_memory_file):
                    with patch("src.core.backup_manager.OUTPUT_DIR", self.restore_dir):
                        result = undo_last_action()

        self.assertEqual(result["status"], "success")
        self.assertTrue(result["output_file"].endswith("_restored.xlsx"))
        self.assertTrue(os.path.exists(result["output_file"]))

    def test_undo_handles_missing_session_memory(self):
        with patch("src.core.session_memory.SESSION_FILE", self.session_file):
            with patch("src.core.session_memory.SESSION_DIR", Path("tmp")):
                result = undo_last_action()

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "No session memory found.")


if __name__ == "__main__":
    unittest.main()
