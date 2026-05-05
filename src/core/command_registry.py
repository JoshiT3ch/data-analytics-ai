import os

from src.commands.add_formula_column import add_formula_column, output_path_for_formula
from src.commands.build_dashboard import build_dashboard
from src.commands.clean_excel import clean_duplicates
from src.commands.create_chart import create_chart
from src.commands.detect_columns import detect_columns
from src.commands.generate_insights import generate_insights
from src.commands.remove_empty_rows import remove_empty_rows
from src.commands.summarize import summarize


def _output_path(file_path, suffix, extension=None):
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    output_extension = extension or os.path.splitext(file_path)[1] or ".xlsx"
    return f"outputs/{file_name}_{suffix}{output_extension}"


def cleaned_output_path(file_path):
    return _output_path(file_path, "cleaned")


def no_empty_output_path(file_path):
    return _output_path(file_path, "no_empty", ".xlsx")


def summary_output_path(file_path):
    return _output_path(file_path, "summary", ".txt")


def insights_output_path(file_path):
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    return f"outputs/insights/{file_name}_insights.txt"


def dashboard_output_path(file_path):
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    return f"outputs/dashboards/{file_name}_dashboard"


def formula_output_path(file_path, new_column=None, **_options):
    return output_path_for_formula(file_path, new_column)


COMMAND_REGISTRY = {
    "clean-duplicates": {
        "function": clean_duplicates,
        "type": "transform",
        "produces_output": True,
        "chainable_output": True,
        "output_path": cleaned_output_path,
        "creates_backup": True,
        "supports_preview": True,
    },
    "summarize": {
        "function": summarize,
        "type": "analysis",
        "produces_output": True,
        "chainable_output": False,
        "output_path": summary_output_path,
        "creates_backup": False,
        "supports_preview": False,
    },
    "generate-insights": {
        "function": generate_insights,
        "type": "analysis",
        "produces_output": True,
        "chainable_output": False,
        "output_path": insights_output_path,
        "creates_backup": False,
        "supports_preview": False,
        "option_fields": ("target_column", "group_by"),
        "uses_session_file": True,
    },
    "build-dashboard": {
        "function": build_dashboard,
        "type": "analysis",
        "produces_output": True,
        "chainable_output": False,
        "output_path": dashboard_output_path,
        "creates_backup": False,
        "supports_preview": False,
        "option_fields": ("target_column", "group_by"),
        "uses_session_file": True,
    },
    "remove-empty-rows": {
        "function": remove_empty_rows,
        "type": "transform",
        "produces_output": True,
        "chainable_output": True,
        "output_path": no_empty_output_path,
        "creates_backup": True,
        "supports_preview": False,
    },
    "add-formula-column": {
        "function": add_formula_column,
        "type": "transform",
        "produces_output": True,
        "chainable_output": True,
        "output_path": formula_output_path,
        "creates_backup": True,
        "supports_preview": True,
        "option_fields": ("new_column", "left_column", "operator", "right_column"),
        "uses_session_file": True,
    },
    "detect-columns": {
        "function": detect_columns,
        "type": "analysis",
        "produces_output": False,
        "chainable_output": False,
        "output_path": None,
        "creates_backup": False,
        "supports_preview": False,
    },
    "create-chart": {
        "function": create_chart,
        "type": "visualization",
        "produces_output": True,
        "chainable_output": False,
        "output_path": None,
        "creates_backup": False,
        "supports_preview": False,
        "option_fields": ("chart_type", "x_column", "y_column", "title"),
    },
}


COMMANDS = {
    command: metadata["function"]
    for command, metadata in COMMAND_REGISTRY.items()
}


def get_command_metadata(command):
    return COMMAND_REGISTRY.get(command)


def supported_commands():
    return set(COMMAND_REGISTRY)
