import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from src.commands.generate_insights import generate_insights
from src.core import executor, session_memory
from src.core.nlp_parser import parse_plan


class GenerateInsightsTests(unittest.TestCase):
    def setUp(self):
        os.makedirs("outputs/insights", exist_ok=True)
        os.makedirs("tmp", exist_ok=True)
        self.sales_file = "data/raw/sales.xlsx"
        self.output_file = "outputs/insights/sales_insights.txt"
        unique = uuid4().hex
        self.session_file = Path(f"tmp/test_insights_session_{unique}.json")
        self.legacy_memory_file = f"tmp/test_insights_memory_{unique}.json"

    def tearDown(self):
        for file_path in (
            self.output_file,
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

    def test_insight_report_creation_from_sales_file(self):
        result = generate_insights(self.sales_file)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["output_file"], self.output_file)
        self.assertTrue(os.path.exists(self.output_file))

        report = Path(self.output_file).read_text(encoding="utf-8")
        self.assertIn("Dataset Overview", report)
        self.assertIn("File name: sales.xlsx", report)
        self.assertIn("Row count: 5", report)
        self.assertIn("Recommendations", report)
        self.assertIn("Electronics recorded the highest total sales by category.", report)
        self.assertIn("Revenue increased from January to May", report)

    def test_parser_detects_give_me_insights(self):
        plan = self._parse_without_llm(
            "give me insights from data/raw/sales.xlsx"
        )

        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["command"], "generate-insights")
        self.assertEqual(plan[0]["file_path"], self.sales_file)

    def test_parser_detects_analyze_trends(self):
        plan = self._parse_without_llm(
            "analyze trends in data/raw/sales.xlsx"
        )

        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["command"], "generate-insights")
        self.assertEqual(plan[0]["file_path"], self.sales_file)

    def test_missing_file_error(self):
        result = generate_insights("data/raw/does_not_exist.xlsx")

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "File not found: data/raw/does_not_exist.xlsx")

    def test_no_file_and_no_session_error(self):
        plan = self._parse_without_llm(
            "find patterns and recommendations from this Excel file"
        )

        self.assertEqual(plan[0]["command"], "generate-insights")
        self.assertIsNone(plan[0]["file_path"])

        with patch("src.core.session_memory.SESSION_FILE", self.session_file):
            with patch("src.core.session_memory.SESSION_DIR", Path("tmp")):
                with patch("src.core.memory.MEMORY_FILE", self.legacy_memory_file):
                    with patch("src.core.executor._write_log", return_value="logs/test.json"):
                        result = executor.execute_plan(plan)

        self.assertEqual(result["status"], "error")
        self.assertEqual(
            result["message"],
            "No input file provided and no current session file found.",
        )

    def test_no_file_uses_current_session_file(self):
        with patch("src.core.session_memory.SESSION_FILE", self.session_file):
            with patch("src.core.session_memory.SESSION_DIR", Path("tmp")):
                session_memory.save_session_memory(
                    {
                        "current_file": self.sales_file,
                        "current_sheet": "Sheet1",
                        "last_command": "summarize",
                        "last_output_file": "outputs/sales_summary.txt",
                        "last_result_summary": "Saved summary.",
                        "command_history": [],
                    }
                )

        plan = self._parse_without_llm("explain this dataset")

        self.assertEqual(plan[0]["command"], "generate-insights")
        self.assertEqual(plan[0]["file_path"], self.sales_file)

    def test_executor_updates_session_memory_after_success(self):
        plan = [{"command": "generate-insights", "file_path": self.sales_file}]

        with patch("src.core.session_memory.SESSION_FILE", self.session_file):
            with patch("src.core.session_memory.SESSION_DIR", Path("tmp")):
                with patch("src.core.memory.MEMORY_FILE", self.legacy_memory_file):
                    with patch("src.core.executor._write_log", return_value="logs/test.json"):
                        result = executor.execute_plan(plan)

        self.assertEqual(result["status"], "success")

        saved_session = json.loads(self.session_file.read_text(encoding="utf-8"))
        self.assertEqual(saved_session["current_file"], self.sales_file)
        self.assertEqual(saved_session["last_command"], "generate-insights")
        self.assertEqual(saved_session["last_output_file"], self.output_file)
        self.assertEqual(
            saved_session["last_result_summary"],
            "Insights generated successfully.",
        )


if __name__ == "__main__":
    unittest.main()
