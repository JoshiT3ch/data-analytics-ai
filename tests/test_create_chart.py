import os
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pandas as pd

from src.ai.llm_interpreter import normalize_plan
from src.commands.create_chart import create_chart
from src.commands.summarize import summarize
from src.core.nlp_parser import parse_plan


class CreateChartTests(unittest.TestCase):
    def setUp(self):
        os.makedirs("data/raw", exist_ok=True)
        os.makedirs("outputs/charts", exist_ok=True)

        unique = uuid4().hex
        self.sales_file = f"data/raw/test_sales_{unique}.xlsx"
        self.missing_column_file = f"data/raw/test_missing_chart_{unique}.xlsx"
        self.summary_file = f"outputs/test_missing_chart_{unique}_summary.txt"
        self.created_files = [self.sales_file, self.missing_column_file]

        pd.DataFrame(
            [
                {"Category": "Electronics", "Sales": 5000, "Month": "January", "Revenue": 12000, "Product": "Laptop"},
                {"Category": "Clothing", "Sales": 3000, "Month": "February", "Revenue": 15000, "Product": "Shirt"},
                {"Category": "Food", "Sales": 2000, "Month": "March", "Revenue": 18000, "Product": "Snacks"},
                {"Category": "Electronics", "Sales": 7000, "Month": "April", "Revenue": 22000, "Product": "Phone"},
                {"Category": "Clothing", "Sales": 4000, "Month": "May", "Revenue": 25000, "Product": "Shoes"},
            ]
        ).to_excel(self.sales_file, index=False)

        pd.DataFrame(
            [
                {"Name": "Ada", "Age": 30, "City": "Manila"},
                {"Name": "Lin", "Age": 22, "City": "Cebu"},
            ]
        ).to_excel(self.missing_column_file, index=False)

    def tearDown(self):
        for file_path in self.created_files:
            if os.path.exists(file_path):
                os.remove(file_path)

        for output_file in (
            "outputs/charts/sales_by_category_bar_chart.png",
            "outputs/charts/age_distribution_histogram_chart.png",
            self.summary_file,
        ):
            if os.path.exists(output_file):
                os.remove(output_file)

    def test_bar_chart_creation(self):
        result = create_chart(
            self.sales_file,
            chart_type="bar",
            x_column="category",
            y_column="sales",
            title="Sales by Category",
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["output_file"], "outputs/charts/sales_by_category_bar_chart.png")
        self.assertTrue(os.path.exists(result["output_file"]))

    def test_histogram_creation_using_test_age_column(self):
        test_file_created = False
        test_file = "data/raw/test.xlsx"
        if not os.path.exists(test_file):
            pd.DataFrame({"Age": [22, 30, 25, 30]}).to_excel(test_file, index=False)
            test_file_created = True

        try:
            result = create_chart(
                test_file,
                chart_type="histogram",
                x_column="age",
                title="Age Distribution",
            )
        finally:
            if test_file_created and os.path.exists(test_file):
                os.remove(test_file)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["output_file"], "outputs/charts/age_distribution_histogram_chart.png")
        self.assertTrue(os.path.exists(result["output_file"]))

    def test_missing_column_error_lists_available_columns(self):
        result = create_chart(
            self.missing_column_file,
            chart_type="bar",
            x_column="City",
            y_column="Sales",
            title="Sales by City",
        )

        self.assertEqual(result["status"], "error")
        self.assertEqual(
            result["message"],
            "Column 'Sales' was not found. Available columns: Name, Age, City",
        )

    def test_missing_file_and_no_session_error_is_clear(self):
        result = create_chart(
            None,
            chart_type="bar",
            x_column="Category",
            y_column="Sales",
            title="Sales by Category",
        )

        self.assertEqual(result["status"], "error")
        self.assertEqual(
            result["message"],
            "No input file provided and no current session file found.",
        )

    def test_parser_detects_chart_command(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("src.ai.llm_interpreter.load_dotenv", return_value=False):
                plan = parse_plan(
                    "create a bar chart of sales by category from data/raw/sales.xlsx"
                )

        self.assertEqual(plan[0]["command"], "create-chart")
        self.assertEqual(plan[0]["file_path"], "data/raw/sales.xlsx")
        self.assertEqual(plan[0]["chart_type"], "bar")
        self.assertEqual(plan[0]["x_column"], "Category")
        self.assertEqual(plan[0]["y_column"], "Sales")
        self.assertEqual(plan[0]["title"], "Sales by Category")

    def test_existing_summarize_command_still_works(self):
        result = summarize(self.missing_column_file)

        self.assertEqual(result["status"], "success")
        self.assertIn("Rows: 2", result["summary"])

    def test_normalize_plan_preserves_chart_options(self):
        plan = normalize_plan(
            {
                "steps": [
                    {
                        "command": "create-chart",
                        "file_path": "sales.xlsx",
                        "chart_type": "line",
                        "x_column": "Month",
                        "y_column": "Revenue",
                        "title": "Revenue Trend by Month",
                        "confidence": 0.9,
                        "reason": "chart requested",
                    }
                ]
            },
            "visualize revenue trend by month from sales.xlsx",
        )

        self.assertEqual(plan[0]["command"], "create-chart")
        self.assertEqual(plan[0]["file_path"], "data/raw/sales.xlsx")
        self.assertEqual(plan[0]["chart_type"], "line")
        self.assertEqual(plan[0]["x_column"], "Month")
        self.assertEqual(plan[0]["y_column"], "Revenue")


if __name__ == "__main__":
    unittest.main()
