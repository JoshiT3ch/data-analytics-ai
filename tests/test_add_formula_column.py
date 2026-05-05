import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pandas as pd

from src.commands.add_formula_column import add_formula_column
from src.core import executor
from src.core.nlp_parser import parse_plan


class AddFormulaColumnTests(unittest.TestCase):
    def setUp(self):
        os.makedirs("outputs", exist_ok=True)
        os.makedirs("tmp", exist_ok=True)
        self.sales_file = "data/raw/sales.xlsx"
        self.profit_output = "outputs/sales_with_profit.xlsx"
        self.total_output = "outputs/sales_with_total.xlsx"
        self.preview_output = "outputs/sales_with_preview_profit.xlsx"
        unique = uuid4().hex
        self.session_file = Path(f"tmp/test_formula_session_{unique}.json")
        self.legacy_memory_file = f"tmp/test_formula_memory_{unique}.json"

    def tearDown(self):
        for file_path in (
            self.profit_output,
            self.total_output,
            self.preview_output,
            self.session_file,
            self.legacy_memory_file,
        ):
            if os.path.exists(file_path):
                os.remove(file_path)

    def _parse_without_llm(self, text):
        with patch.dict(os.environ, {}, clear=True):
            with patch("src.ai.llm_interpreter.load_dotenv", return_value=False):
                with patch("src.core.session_memory.SESSION_FILE", self.session_file):
                    with patch("src.core.session_memory.SESSION_DIR", Path("tmp")):
                        with patch("src.core.memory.MEMORY_FILE", self.legacy_memory_file):
                            return parse_plan(text)

    def test_parser_detects_profit_formula(self):
        plan = self._parse_without_llm(
            "add a formula column for profit using revenue minus cost from data/raw/sales.xlsx"
        )

        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["command"], "add-formula-column")
        self.assertEqual(plan[0]["file_path"], self.sales_file)
        self.assertEqual(plan[0]["new_column"], "Profit")
        self.assertEqual(plan[0]["left_column"], "Revenue")
        self.assertEqual(plan[0]["operator"], "-")
        self.assertEqual(plan[0]["right_column"], "Cost")

    def test_parser_detects_total_formula(self):
        plan = self._parse_without_llm(
            "create a new column called total with quantity times price from data/raw/sales.xlsx"
        )

        self.assertEqual(plan[0]["command"], "add-formula-column")
        self.assertEqual(plan[0]["new_column"], "Total")
        self.assertEqual(plan[0]["left_column"], "Quantity")
        self.assertEqual(plan[0]["operator"], "*")
        self.assertEqual(plan[0]["right_column"], "Price")

    def test_parser_detects_profit_margin_formula(self):
        plan = self._parse_without_llm(
            "calculate profit margin from revenue and cost from data/raw/sales.xlsx"
        )

        self.assertEqual(plan[0]["command"], "add-formula-column")
        self.assertEqual(plan[0]["new_column"], "Profit Margin")
        self.assertEqual(plan[0]["left_column"], "Profit")
        self.assertEqual(plan[0]["operator"], "/")
        self.assertEqual(plan[0]["right_column"], "Revenue")

    def test_formula_column_creation_with_revenue_minus_cost(self):
        result = add_formula_column(
            self.sales_file,
            new_column="Profit",
            left_column="revenue",
            operator="minus",
            right_column="cost",
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["output_file"], self.profit_output)
        self.assertTrue(os.path.exists(self.profit_output))

        df = pd.read_excel(self.profit_output)
        self.assertIn("Profit", df.columns)
        self.assertEqual(df.loc[0, "Profit"], 4000)
        self.assertEqual(df.loc[4, "Profit"], 10000)

    def test_formula_column_creation_with_quantity_times_price(self):
        result = add_formula_column(
            self.sales_file,
            new_column="Total",
            left_column="Quantity",
            operator="*",
            right_column="Price",
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["output_file"], self.total_output)

        df = pd.read_excel(self.total_output)
        self.assertIn("Total", df.columns)
        self.assertEqual(df.loc[0, "Total"], 5000)
        self.assertEqual(df.loc[2, "Total"], 2000)

    def test_preview_mode_does_not_create_output_or_backup(self):
        plan = [
            {
                "command": "add-formula-column",
                "file_path": self.sales_file,
                "new_column": "Preview Profit",
                "left_column": "Revenue",
                "operator": "-",
                "right_column": "Cost",
            }
        ]

        with patch("src.core.executor.create_backup") as create_backup:
            result = executor.execute_plan(plan, preview=True)

        self.assertEqual(result["status"], "success")
        self.assertTrue(result["results"][0]["preview"])
        self.assertFalse(os.path.exists(self.preview_output))
        create_backup.assert_not_called()

    def test_missing_column_returns_helpful_error(self):
        result = add_formula_column(
            self.sales_file,
            new_column="Profit",
            left_column="Revenue",
            operator="-",
            right_column="MissingCost",
        )

        self.assertEqual(result["status"], "error")
        self.assertEqual(
            result["message"],
            "Column 'MissingCost' was not found. Available columns: Category, Sales, Cost, Month, Revenue, Product, Quantity, Price, Discount",
        )

    def test_profit_margin_without_profit_returns_guidance(self):
        result = add_formula_column(
            self.sales_file,
            new_column="Profit Margin",
            left_column="Profit",
            operator="/",
            right_column="Revenue",
        )

        self.assertEqual(result["status"], "error")
        self.assertEqual(
            result["message"],
            "Profit margin requires Profit and Revenue columns. Try: add a formula column for profit using revenue minus cost.",
        )

    def test_session_memory_updates_after_successful_formula_command(self):
        plan = [
            {
                "command": "add-formula-column",
                "file_path": self.sales_file,
                "new_column": "Profit",
                "left_column": "Revenue",
                "operator": "-",
                "right_column": "Cost",
            }
        ]

        with patch("src.core.session_memory.SESSION_FILE", self.session_file):
            with patch("src.core.session_memory.SESSION_DIR", Path("tmp")):
                with patch("src.core.memory.MEMORY_FILE", self.legacy_memory_file):
                    with patch(
                        "src.core.executor.create_backup",
                        return_value="backups/test_formula_backup.xlsx",
                    ):
                        with patch("src.core.executor._write_log", return_value="logs/test.json"):
                            result = executor.execute_plan(plan)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["results"][0]["backup_file"], "backups/test_formula_backup.xlsx")

        saved_session = json.loads(self.session_file.read_text(encoding="utf-8"))
        self.assertEqual(saved_session["current_file"], self.profit_output)
        self.assertEqual(saved_session["last_command"], "add-formula-column")
        self.assertEqual(saved_session["last_output_file"], self.profit_output)
        self.assertEqual(saved_session["last_result_summary"], "Added formula column Profit.")
        self.assertEqual(
            saved_session["command_history"][0]["backup_file"],
            "backups/test_formula_backup.xlsx",
        )


if __name__ == "__main__":
    unittest.main()
