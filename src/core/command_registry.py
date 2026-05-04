import os

from src.commands.clean_excel import clean_duplicates
from src.commands.detect_columns import detect_columns
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
    "remove-empty-rows": {
        "function": remove_empty_rows,
        "type": "transform",
        "produces_output": True,
        "chainable_output": True,
        "output_path": no_empty_output_path,
        "creates_backup": True,
        "supports_preview": False,
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
}


COMMANDS = {
    command: metadata["function"]
    for command, metadata in COMMAND_REGISTRY.items()
}


def get_command_metadata(command):
    return COMMAND_REGISTRY.get(command)


def supported_commands():
    return set(COMMAND_REGISTRY)
