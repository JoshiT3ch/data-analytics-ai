import json
import os
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pandas as pd

from src.commands.build_dashboard import build_dashboard
from src.core import executor, session_memory
from src.core.nlp_parser import parse_plan


class BuildDashboardTests(unittest.TestCase):
    def setUp(self):
        os.makedirs("outputs/dashboards", exist_ok=True)
        os.makedirs("tmp", exist_ok=True)
        self.sales_file = "data/raw/sales.xlsx"
        self.dashboard_dir = Path("outputs/dashboards/sales_dashboard")
        self.dashboard_file = self.dashboard_dir / "dashboard.xlsx"
        self.summary_file = self.dashboard_dir / "summary.txt"
        self.insights_file = self.dashboard_dir / "insights.txt"
        self.manifest_file = self.dashboard_dir / "manifest.json"
        unique = uuid4().hex
        self.session_file = Path(f"tmp/test_dashboard_session_{unique}.json")
        self.legacy_memory_file = f"tmp/test_dashboard_memory_{unique}.json"

    def tearDown(self):
        if self.dashboard_dir.exists():
            shutil.rmtree(self.dashboard_dir)

        for file_path in (self.session_file, self.legacy_memory_file):
            if os.path.exists(file_path):
                os.remove(file_path)

    def _parse_without_llm(self, text):
        with patch.dict(os.environ, {}, clear=True):
            with patch("src.ai.llm_interpreter.load_dotenv", return_value=False):
                with patch("src.core.session_memory.SESSION_FILE", self.session_file):
                    with patch("src.core.session_memory.SESSION_DIR", Path("tmp")):
                        with patch("src.core.memory.MEMORY_FILE", self.legacy_memory_file):
                            return parse_plan(text)

    def test_dashboard_creation_from_sales_file(self):
        result = build_dashboard(self.sales_file)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["output_file"], self.dashboard_dir.as_posix())
        self.assertTrue(self.dashboard_file.exists())
        self.assertTrue(self.summary_file.exists())
        self.assertTrue(self.insights_file.exists())
        self.assertTrue(self.manifest_file.exists())
        self.assertGreaterEqual(len(result["charts"]), 3)

        manifest = json.loads(self.manifest_file.read_text(encoding="utf-8"))
        self.assertEqual(manifest["source_file"], self.sales_file)
        self.assertEqual(manifest["dashboard_file"], self.dashboard_file.as_posix())
        for chart in manifest["charts"]:
            self.assertTrue(Path(chart["file"]).exists())

        with pd.ExcelFile(self.dashboard_file) as excel_file:
            self.assertIn("Dashboard", excel_file.sheet_names)
            self.assertIn("Summary", excel_file.sheet_names)
            self.assertIn("Insights", excel_file.sheet_names)
            self.assertIn("Charts", excel_file.sheet_names)
            self.assertIn("Data Preview", excel_file.sheet_names)

    def test_parser_detects_dashboard_request(self):
        plan = self._parse_without_llm(
            "build a dashboard from data/raw/sales.xlsx"
        )

        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["command"], "build-dashboard")
        self.assertEqual(plan[0]["file_path"], self.sales_file)

    def test_parser_prefers_dashboard_over_separate_summary_chart_insight_steps(self):
        plan = self._parse_without_llm(
            "create a dashboard report with summary charts and insights from data/raw/sales.xlsx"
        )

        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["command"], "build-dashboard")

    def test_missing_file_error(self):
        result = build_dashboard("data/raw/does_not_exist.xlsx")

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "File not found: data/raw/does_not_exist.xlsx")

    def test_no_file_and_no_session_error(self):
        plan = self._parse_without_llm("build a dashboard")

        self.assertEqual(plan[0]["command"], "build-dashboard")
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

        plan = self._parse_without_llm("create a dashboard report")

        self.assertEqual(plan[0]["command"], "build-dashboard")
        self.assertEqual(plan[0]["file_path"], self.sales_file)

    def test_executor_updates_session_memory_after_success(self):
        plan = [{"command": "build-dashboard", "file_path": self.sales_file}]

        with patch("src.core.session_memory.SESSION_FILE", self.session_file):
            with patch("src.core.session_memory.SESSION_DIR", Path("tmp")):
                with patch("src.core.memory.MEMORY_FILE", self.legacy_memory_file):
                    with patch("src.core.executor._write_log", return_value="logs/test.json"):
                        result = executor.execute_plan(plan)

        self.assertEqual(result["status"], "success")

        saved_session = json.loads(self.session_file.read_text(encoding="utf-8"))
        self.assertEqual(saved_session["current_file"], self.sales_file)
        self.assertEqual(saved_session["last_command"], "build-dashboard")
        self.assertEqual(saved_session["last_output_file"], self.dashboard_dir.as_posix())
        self.assertEqual(
            saved_session["last_result_summary"],
            "Dashboard built successfully.",
        )


if __name__ == "__main__":
    unittest.main()
