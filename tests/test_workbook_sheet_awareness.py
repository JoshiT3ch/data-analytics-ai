import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pandas as pd

from src.commands.add_formula_column import add_formula_column
from src.commands.create_chart import create_chart
from src.commands.detect_columns import detect_columns
from src.commands.generate_insights import generate_insights
from src.commands.list_sheets import list_sheets
from src.commands.set_current_sheet import set_current_sheet
from src.commands.summarize import summarize
from src.core import executor, session_memory
from src.core.nlp_parser import parse_plan


class WorkbookSheetAwarenessTests(unittest.TestCase):
    def setUp(self):
        os.makedirs("data/raw", exist_ok=True)
        os.makedirs("outputs", exist_ok=True)
        os.makedirs("outputs/charts", exist_ok=True)
        os.makedirs("outputs/insights", exist_ok=True)
        os.makedirs("tmp", exist_ok=True)

        self.workbook = "data/raw/company_report.xlsx"
        self.formula_output = "outputs/company_report_with_profit.xlsx"
        self.summary_output = "outputs/company_report_summary.txt"
        self.insights_output = "outputs/insights/company_report_insights.txt"
        self.chart_output = "outputs/charts/revenue_by_month_bar_chart.png"
        unique = uuid4().hex
        self.session_file = Path(f"tmp/test_sheet_session_{unique}.json")
        self.legacy_memory_file = f"tmp/test_sheet_memory_{unique}.json"

        self._write_company_report()

    def tearDown(self):
        for file_path in (
            self.formula_output,
            self.summary_output,
            self.insights_output,
            self.chart_output,
            self.session_file,
            self.legacy_memory_file,
        ):
            if os.path.exists(file_path):
                os.remove(file_path)

    def _write_company_report(self):
        sales = pd.DataFrame(
            [
                {"Month": "January", "Revenue": 12000, "Cost": 8000, "Category": "Electronics", "Product": "Laptop", "Quantity": 10, "Price": 500, "Discount": 300},
                {"Month": "February", "Revenue": 15000, "Cost": 9000, "Category": "Clothing", "Product": "Shirt", "Quantity": 15, "Price": 200, "Discount": 150},
                {"Month": "March", "Revenue": 18000, "Cost": 11000, "Category": "Food", "Product": "Snacks", "Quantity": 20, "Price": 100, "Discount": 100},
            ]
        )
        expenses = pd.DataFrame(
            [
                {"Month": "January", "Department": "Marketing", "Expense": 3000, "Vendor": "Ads"},
                {"Month": "February", "Department": "Operations", "Expense": 4500, "Vendor": "Logistics"},
                {"Month": "March", "Department": "Marketing", "Expense": 3500, "Vendor": "Events"},
            ]
        )
        inventory = pd.DataFrame(
            [
                {"Item": "Laptop", "Category": "Electronics", "Stock": 12, "Value": 24000},
                {"Item": "Shirt", "Category": "Clothing", "Stock": 40, "Value": 8000},
                {"Item": "Snacks", "Category": "Food", "Stock": 100, "Value": 5000},
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

    def test_list_sheets_from_workbook(self):
        result = list_sheets(self.workbook)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["sheets"], ["Sales", "Expenses", "Inventory"])

        plan = self._parse_without_llm(f"list sheets in {self.workbook}")
        self.assertEqual(plan[0]["command"], "list-sheets")
        self.assertEqual(plan[0]["file_path"], self.workbook)

    def test_set_current_sheet_updates_session_memory(self):
        plan = [
            {
                "command": "set-current-sheet",
                "file_path": self.workbook,
                "sheet_name": "Sales",
            }
        ]

        with patch("src.core.session_memory.SESSION_FILE", self.session_file):
            with patch("src.core.session_memory.SESSION_DIR", Path("tmp")):
                with patch("src.core.memory.MEMORY_FILE", self.legacy_memory_file):
                    with patch("src.core.executor._write_log", return_value="logs/test.json"):
                        result = executor.execute_plan(plan)

        self.assertEqual(result["status"], "success")
        saved_session = json.loads(self.session_file.read_text(encoding="utf-8"))
        self.assertEqual(saved_session["current_file"], self.workbook)
        self.assertEqual(saved_session["current_sheet"], "Sales")
        self.assertEqual(saved_session["last_command"], "set-current-sheet")

        parsed = self._parse_without_llm(f"use the Sales sheet from {self.workbook}")
        self.assertEqual(parsed[0]["command"], "set-current-sheet")
        self.assertEqual(parsed[0]["sheet_name"], "Sales")

    def test_summarize_specific_sheet(self):
        result = summarize(self.workbook, sheet_name="Expenses")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["sheet_name"], "Expenses")
        self.assertIn("- Expense", result["summary"])
        self.assertNotIn("- Revenue", result["summary"])

        plan = self._parse_without_llm(f"summarize the Expenses sheet from {self.workbook}")
        self.assertEqual(plan[0]["command"], "summarize")
        self.assertEqual(plan[0]["sheet_name"], "Expenses")

    def test_detect_columns_specific_sheet(self):
        result = detect_columns(self.workbook, sheet_name="Inventory")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["sheet_name"], "Inventory")
        self.assertIn(("Stock", "int64"), result["columns"])
        self.assertNotIn(("Revenue", "int64"), result["columns"])

    def test_generate_insights_from_specific_sheet(self):
        result = generate_insights(self.workbook, sheet_name="Expenses")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["sheet_name"], "Expenses")
        report = Path(self.insights_output).read_text(encoding="utf-8")
        self.assertIn("Expense", report)
        self.assertNotIn("Revenue increased", report)

    def test_chart_from_specific_sheet(self):
        result = create_chart(
            self.workbook,
            chart_type="bar",
            x_column="Month",
            y_column="Revenue",
            title="Revenue by Month",
            sheet_name="Sales",
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["sheet_name"], "Sales")
        self.assertTrue(os.path.exists(self.chart_output))

        plan = self._parse_without_llm(
            f"create a chart of revenue by month from the Sales sheet in {self.workbook}"
        )
        self.assertEqual(plan[0]["command"], "create-chart")
        self.assertEqual(plan[0]["sheet_name"], "Sales")

    def test_formula_column_on_specific_sheet(self):
        result = add_formula_column(
            self.workbook,
            new_column="Profit",
            left_column="Revenue",
            operator="-",
            right_column="Cost",
            sheet_name="Sales",
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["sheet_name"], "Sales")

        sales = pd.read_excel(self.formula_output, sheet_name="Sales")
        expenses = pd.read_excel(self.formula_output, sheet_name="Expenses")
        self.assertIn("Profit", sales.columns)
        self.assertEqual(sales.loc[0, "Profit"], 4000)
        self.assertNotIn("Profit", expenses.columns)

    def test_invalid_sheet_name_returns_helpful_error(self):
        result = summarize(self.workbook, sheet_name="Missing")

        self.assertEqual(result["status"], "error")
        self.assertEqual(
            result["message"],
            "Sheet 'Missing' was not found. Available sheets: Sales, Expenses, Inventory",
        )

    def test_no_sheet_uses_session_current_sheet(self):
        with patch("src.core.session_memory.SESSION_FILE", self.session_file):
            with patch("src.core.session_memory.SESSION_DIR", Path("tmp")):
                session_memory.save_session_memory(
                    {
                        "current_file": self.workbook,
                        "current_sheet": "Expenses",
                        "last_command": "set-current-sheet",
                        "last_output_file": None,
                        "last_result_summary": "Current sheet set.",
                        "command_history": [],
                    }
                )

                result = summarize(self.workbook)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["sheet_name"], "Expenses")
        self.assertIn("- Expense", result["summary"])


if __name__ == "__main__":
    unittest.main()
