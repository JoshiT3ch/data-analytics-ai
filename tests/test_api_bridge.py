import os
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pandas as pd
from fastapi.testclient import TestClient

from src.api.server import app
from src.core import session_memory


class LocalApiBridgeTests(unittest.TestCase):
    def setUp(self):
        os.makedirs("data/raw", exist_ok=True)
        os.makedirs("outputs", exist_ok=True)
        os.makedirs("tmp", exist_ok=True)

        unique = uuid4().hex
        self.workbook = "data/raw/company_report.xlsx"
        self.missing_workbook = f"data/raw/missing_{unique}.xlsx"
        self.summary_output = "outputs/company_report_summary.txt"
        self.session_file = Path(f"tmp/test_api_session_{unique}.json")
        self.legacy_memory_file = f"tmp/test_api_memory_{unique}.json"
        self.client = TestClient(app)
        self._write_workbook()

    def tearDown(self):
        for file_path in (
            self.summary_output,
            self.session_file,
            self.legacy_memory_file,
        ):
            if os.path.exists(file_path):
                os.remove(file_path)

    def _write_workbook(self):
        sales = pd.DataFrame(
            [
                {
                    "Month": "January",
                    "Revenue": 12000,
                    "Cost": 8000,
                    "Category": "Electronics",
                },
                {
                    "Month": "February",
                    "Revenue": 15000,
                    "Cost": 9000,
                    "Category": "Clothing",
                },
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

    @contextmanager
    def _isolated_api(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("src.ai.llm_interpreter.load_dotenv", return_value=False):
                with patch("src.core.session_memory.SESSION_FILE", self.session_file):
                    with patch("src.core.session_memory.SESSION_DIR", Path("tmp")):
                        with patch("src.core.memory.MEMORY_FILE", self.legacy_memory_file):
                            with patch("src.core.executor._write_log", return_value="logs/test.json"):
                                yield

    def _save_context(self, sheet_name="Sales"):
        session_memory.save_session_memory(
            {
                "current_file": self.workbook,
                "current_sheet": sheet_name,
                "last_command": "summarize",
                "last_output_file": self.summary_output,
                "last_result_summary": "Summary generated successfully.",
                "command_history": [
                    {"command": "set-current-sheet", "timestamp": "2026-05-05T10:00:00"},
                    {"command": "summarize", "timestamp": "2026-05-05T10:01:00"},
                ],
            }
        )

    def test_health_check(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "ok",
                "service": "excel-data-analyst-ai",
            },
        )

    def test_chat_with_summarize_command(self):
        with self._isolated_api():
            response = self.client.post(
                "/chat",
                json={
                    "message": "summarize the Sales sheet",
                    "file_path": self.workbook,
                    "sheet_name": "Sales",
                },
            )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(body["success"])
        self.assertEqual(body["command"], "summarize")
        self.assertEqual(body["file_path"], self.workbook)
        self.assertEqual(body["sheet_name"], "Sales")
        self.assertIn("Rows: 2", body["output_text"])
        self.assertIn(
            {"type": "file", "path": self.summary_output},
            body["artifacts"],
        )

    def test_chat_with_workbook_status(self):
        with self._isolated_api():
            self._save_context(sheet_name="Expenses")
            response = self.client.post("/chat", json={"message": "workbook status"})

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(body["success"])
        self.assertEqual(body["command"], "workbook-status")
        self.assertEqual(body["session"]["current_file"], self.workbook)
        self.assertEqual(body["session"]["current_sheet"], "Expenses")
        self.assertIn("Excel Context", body["output_text"])

    def test_structured_command_with_summarize(self):
        with self._isolated_api():
            response = self.client.post(
                "/command",
                json={
                    "command": "summarize",
                    "file_path": self.workbook,
                    "sheet_name": "Sales",
                },
            )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(body["success"])
        self.assertEqual(body["command"], "summarize")
        self.assertEqual(body["sheet_name"], "Sales")
        self.assertIn("Revenue", body["output_text"])

    def test_workbook_status_endpoint(self):
        with self._isolated_api():
            self._save_context(sheet_name="Sales")
            response = self.client.get("/workbook/status")

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(body["success"])
        self.assertEqual(body["current_file"], self.workbook)
        self.assertEqual(body["current_sheet"], "Sales")
        self.assertEqual(body["sheets"], ["Sales", "Expenses", "Inventory"])
        self.assertEqual(body["sheet_summary"]["Sales"], {"rows": 2, "columns": 4})
        self.assertEqual(body["recent_commands"], ["set-current-sheet", "summarize"])

    def test_workbook_sheets_endpoint_with_valid_workbook(self):
        with self._isolated_api():
            response = self.client.get(
                "/workbook/sheets",
                params={"file_path": self.workbook},
            )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(body["success"])
        self.assertEqual(body["file_path"], self.workbook)
        self.assertEqual(body["sheets"], ["Sales", "Expenses", "Inventory"])

    def test_workbook_sheets_endpoint_with_missing_workbook(self):
        with self._isolated_api():
            response = self.client.get(
                "/workbook/sheets",
                params={"file_path": self.missing_workbook},
            )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(body["success"])
        self.assertEqual(
            body["message"],
            f"Workbook not found: {self.missing_workbook}",
        )

    def test_workbook_context_endpoint_with_valid_sheet(self):
        with self._isolated_api():
            response = self.client.post(
                "/workbook/context",
                json={
                    "file_path": self.workbook,
                    "sheet_name": "Expenses",
                },
            )
            saved_session = session_memory.load_session_memory()

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(body["success"])
        self.assertEqual(body["current_file"], self.workbook)
        self.assertEqual(body["current_sheet"], "Expenses")
        self.assertEqual(saved_session["current_file"], self.workbook)
        self.assertEqual(saved_session["current_sheet"], "Expenses")
        self.assertEqual(saved_session["last_command"], "set-current-sheet")

    def test_workbook_context_endpoint_with_invalid_sheet(self):
        with self._isolated_api():
            response = self.client.post(
                "/workbook/context",
                json={
                    "file_path": self.workbook,
                    "sheet_name": "Missing",
                },
            )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(body["success"])
        self.assertEqual(
            body["message"],
            "Sheet 'Missing' was not found. Available sheets: Sales, Expenses, Inventory",
        )


if __name__ == "__main__":
    unittest.main()
