import os
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pandas as pd

from src.commands.workbook_status import workbook_status
from src.core import executor, session_memory
from src.core.nlp_parser import parse_plan


class WorkbookStatusTests(unittest.TestCase):
    def setUp(self):
        os.makedirs("data/raw", exist_ok=True)
        os.makedirs("tmp", exist_ok=True)
        self.workbook = "data/raw/company_report.xlsx"
        unique = uuid4().hex
        self.session_file = Path(f"tmp/test_workbook_status_session_{unique}.json")
        self.legacy_memory_file = f"tmp/test_workbook_status_memory_{unique}.json"
        self._write_workbook()

    def tearDown(self):
        for file_path in (self.session_file, self.legacy_memory_file):
            if os.path.exists(file_path):
                os.remove(file_path)

    def _write_workbook(self):
        sales = pd.DataFrame(
            [
                {"Month": "January", "Revenue": 12000, "Cost": 8000},
                {"Month": "February", "Revenue": 15000, "Cost": 9000},
            ]
        )
        expenses = pd.DataFrame(
            [
                {"Month": "January", "Expense": 3000, "Department": "Marketing"},
                {"Month": "February", "Expense": 4500, "Department": "Operations"},
                {"Month": "March", "Expense": 3500, "Department": "Marketing"},
            ]
        )
        inventory = pd.DataFrame(
            [
                {"Item": "Laptop", "Stock": 12, "Value": 24000},
                {"Item": "Shirt", "Stock": 40, "Value": 8000},
                {"Item": "Snacks", "Stock": 100, "Value": 5000},
            ]
        )

        with pd.ExcelWriter(self.workbook, engine="openpyxl") as writer:
            sales.to_excel(writer, sheet_name="Sales", index=False)
            expenses.to_excel(writer, sheet_name="Expenses", index=False)
            inventory.to_excel(writer, sheet_name="Inventory", index=False)

    def _parse_without_llm(self, text):
        with patch.dict(os.environ, {}, clear=True):
            with patch("src.ai.llm_interpreter.load_dotenv", return_value=False):
                with patch("src.core.session_memory.SESSION_FILE", self.session_file):
                    with patch("src.core.session_memory.SESSION_DIR", Path("tmp")):
                        with patch("src.core.memory.MEMORY_FILE", self.legacy_memory_file):
                            return parse_plan(text)

    def _save_context(self, current_file=None):
        with patch("src.core.session_memory.SESSION_FILE", self.session_file):
            with patch("src.core.session_memory.SESSION_DIR", Path("tmp")):
                session_memory.save_session_memory(
                    {
                        "current_file": current_file or self.workbook,
                        "current_sheet": "Expenses",
                        "last_command": "summarize",
                        "last_output_file": "outputs/company_report_summary.txt",
                        "last_result_summary": "Summary generated successfully.",
                        "command_history": [
                            {"command": "set-current-sheet", "timestamp": "2026-05-05T10:00:00"},
                            {"command": "summarize", "timestamp": "2026-05-05T10:01:00"},
                            {"command": "generate-insights", "timestamp": "2026-05-05T10:02:00"},
                        ],
                    }
                )

    def test_workbook_status_phrase_maps_to_command(self):
        plan = self._parse_without_llm("workbook status")

        self.assertEqual(plan[0]["command"], "workbook-status")
        self.assertIsNone(plan[0]["file_path"])

    def test_what_workbook_phrase_maps_to_command(self):
        plan = self._parse_without_llm("what workbook am I using")

        self.assertEqual(plan[0]["command"], "workbook-status")

    def test_show_current_excel_context_maps_to_command(self):
        plan = self._parse_without_llm("show current Excel context")

        self.assertEqual(plan[0]["command"], "workbook-status")

    def test_workbook_status_returns_session_context_and_sheets(self):
        self._save_context()

        with patch("src.core.session_memory.SESSION_FILE", self.session_file):
            with patch("src.core.session_memory.SESSION_DIR", Path("tmp")):
                result = workbook_status()

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["current_file"], self.workbook)
        self.assertEqual(result["current_sheet"], "Expenses")
        self.assertEqual(result["sheets"], ["Sales", "Expenses", "Inventory"])
        self.assertEqual(
            result["sheet_summaries"],
            [
                {"sheet": "Sales", "rows": 2, "columns": 3},
                {"sheet": "Expenses", "rows": 3, "columns": 3},
                {"sheet": "Inventory", "rows": 3, "columns": 3},
            ],
        )
        self.assertEqual(result["last_command"], "summarize")
        self.assertEqual(result["last_output_file"], "outputs/company_report_summary.txt")
        self.assertEqual(
            result["last_result_summary"],
            "Summary generated successfully.",
        )
        self.assertEqual(
            result["recent_commands"],
            ["set-current-sheet", "summarize", "generate-insights"],
        )

    def test_workbook_status_handles_missing_session_memory(self):
        plan = [{"command": "workbook-status", "file_path": None}]

        with patch("src.core.session_memory.SESSION_FILE", self.session_file):
            with patch("src.core.session_memory.SESSION_DIR", Path("tmp")):
                with patch("src.core.memory.MEMORY_FILE", self.legacy_memory_file):
                    with patch("src.core.executor._write_log", return_value="logs/test.json"):
                        result = executor.execute_plan(plan)

        self.assertEqual(result["status"], "error")
        self.assertIn("No workbook context found.", result["message"])

    def test_workbook_status_handles_missing_workbook_file(self):
        missing_file = "data/raw/missing_company_report.xlsx"
        self._save_context(current_file=missing_file)

        with patch("src.core.session_memory.SESSION_FILE", self.session_file):
            with patch("src.core.session_memory.SESSION_DIR", Path("tmp")):
                result = workbook_status()

        self.assertEqual(result["status"], "error")
        self.assertIn("file no longer exists", result["message"])
        self.assertIn(missing_file, result["message"])


if __name__ == "__main__":
    unittest.main()
