import json
import os
import re
from datetime import datetime

from src.core.command_registry import get_command_metadata


MEMORY_FILE = ".data_analytics_memory.json"
MEMORY_KEYS = {
    "latest_input_file",
    "latest_output_file",
    "latest_command",
    "latest_plan",
    "updated_at",
}
EXCEL_FILE_PATTERN = re.compile(r"\b[^\s,;:)]+\.xlsx\b", re.IGNORECASE)
REFERENCE_PATTERNS = [
    r"\bit\b",
    r"\bthis file\b",
    r"\bthat file\b",
    r"\bprevious file\b",
    r"\blatest file\b",
    r"\blast output\b",
]


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _is_excel_file(file_path):
    return isinstance(file_path, str) and file_path.lower().endswith(".xlsx")


def _sanitize_plan(plan):
    if not isinstance(plan, list):
        return []

    sanitized = []
    for step in plan:
        if not isinstance(step, dict):
            continue

        sanitized_step = {}
        for key in (
            "command",
            "file_path",
            "chart_type",
            "x_column",
            "y_column",
            "title",
            "confidence",
            "reason",
        ):
            if key in step:
                sanitized_step[key] = step[key]

        if sanitized_step:
            sanitized.append(sanitized_step)

    return sanitized


def _sanitize_memory(memory):
    if not isinstance(memory, dict):
        return {}

    return {
        key: value
        for key, value in memory.items()
        if key in MEMORY_KEYS
    }


def _has_explicit_excel_file(user_input):
    return isinstance(user_input, str) and EXCEL_FILE_PATTERN.search(user_input) is not None


def _has_file_reference(user_input):
    if not isinstance(user_input, str):
        return False

    text = user_input.lower()
    return any(re.search(pattern, text) for pattern in REFERENCE_PATTERNS)


def _memory_file_for_resolution(memory):
    latest_output_file = memory.get("latest_output_file")
    latest_input_file = memory.get("latest_input_file")

    if _is_excel_file(latest_output_file):
        return latest_output_file

    if _is_excel_file(latest_input_file):
        return latest_input_file

    try:
        from src.core.session_memory import load_session_memory

        current_file = load_session_memory().get("current_file")
        if _is_excel_file(current_file):
            return current_file
    except Exception:
        pass

    return None


def _predict_chain_output(command, file_path):
    metadata = get_command_metadata(command) or {}
    output_path_builder = metadata.get("output_path")

    if metadata.get("chainable_output") and callable(output_path_builder) and file_path:
        return output_path_builder(file_path)

    return None


def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as file:
            return _sanitize_memory(json.load(file))
    except (OSError, json.JSONDecodeError):
        return {}


def save_memory(memory):
    safe_memory = _sanitize_memory(memory)

    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(safe_memory, file, indent=2)


def clear_memory():
    if os.path.exists(MEMORY_FILE):
        os.remove(MEMORY_FILE)


def update_memory_after_step(step, result):
    if not isinstance(step, dict) or not isinstance(result, dict):
        return

    if result.get("status") != "success":
        return

    memory = load_memory()
    input_file = result.get("input_file") or step.get("file_path")
    output_file = result.get("output_file")
    command = result.get("command") or step.get("command")
    latest_plan = step.get("_latest_plan")

    if input_file:
        memory["latest_input_file"] = input_file

    if output_file:
        memory["latest_output_file"] = output_file

    if command:
        memory["latest_command"] = command

    if latest_plan is not None:
        memory["latest_plan"] = _sanitize_plan(latest_plan)
    elif command:
        memory["latest_plan"] = _sanitize_plan(
            [
                {
                    "command": command,
                    "file_path": input_file,
                }
            ]
        )

    memory["updated_at"] = _now()
    save_memory(memory)


def resolve_file_reference(user_input, parsed_plan):
    if not isinstance(parsed_plan, list) or not parsed_plan:
        return parsed_plan

    if _has_explicit_excel_file(user_input):
        return parsed_plan

    memory_file = _memory_file_for_resolution(load_memory())
    if not memory_file:
        return parsed_plan

    resolved_plan = []
    current_file = memory_file

    for step in parsed_plan:
        if not isinstance(step, dict):
            resolved_plan.append(step)
            continue

        resolved_step = step.copy()
        resolved_step["file_path"] = current_file
        resolved_plan.append(resolved_step)

        predicted_output = _predict_chain_output(resolved_step.get("command"), current_file)
        current_file = predicted_output or current_file

    return resolved_plan
