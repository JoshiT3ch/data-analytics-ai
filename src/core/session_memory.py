import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path


SESSION_DIR = Path(".memory")
SESSION_FILE = SESSION_DIR / "session.json"

DEFAULT_SESSION_MEMORY = {
    "current_file": None,
    "current_sheet": None,
    "last_command": None,
    "last_output_file": None,
    "last_result_summary": None,
    "command_history": [],
}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _default_memory():
    return deepcopy(DEFAULT_SESSION_MEMORY)


def _as_string(value):
    if value is None:
        return None
    return str(value)


def _is_excel_file(file_path):
    return isinstance(file_path, str) and file_path.lower().endswith(".xlsx")


def _normalize_memory(memory):
    normalized = _default_memory()

    if not isinstance(memory, dict):
        return normalized

    for key in DEFAULT_SESSION_MEMORY:
        if key == "command_history":
            history = memory.get(key)
            normalized[key] = history if isinstance(history, list) else []
        else:
            normalized[key] = memory.get(key)

    return normalized


def _safe_metadata(result):
    if not isinstance(result, dict):
        return {}

    skipped_keys = {
        "status",
        "command",
        "input_file",
        "output_file",
        "message",
        "summary",
        "result_summary",
        "backup_file",
        "preview",
    }

    metadata = {}
    for key, value in result.items():
        if key in skipped_keys:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            metadata[key] = value
        elif isinstance(value, (list, dict)):
            metadata[key] = value

    return metadata


def _infer_sheet_name(file_path):
    if not _is_excel_file(file_path):
        return None

    try:
        import pandas as pd

        with pd.ExcelFile(file_path) as excel_file:
            if excel_file.sheet_names:
                return excel_file.sheet_names[0]
    except Exception:
        return None

    return None


def session_memory_exists():
    return SESSION_FILE.exists()


def load_session_memory():
    """Load the persisted session memory, returning an empty safe shape on errors."""
    if not SESSION_FILE.exists():
        return _default_memory()

    try:
        with SESSION_FILE.open("r", encoding="utf-8") as file:
            return _normalize_memory(json.load(file))
    except (OSError, json.JSONDecodeError):
        return _default_memory()


def load_session_memory_with_error():
    """Load session memory and return a user-facing error string when it is unusable."""
    if not SESSION_FILE.exists():
        return _default_memory(), "No session memory found."

    try:
        with SESSION_FILE.open("r", encoding="utf-8") as file:
            return _normalize_memory(json.load(file)), None
    except json.JSONDecodeError:
        return _default_memory(), "Session memory file is invalid JSON."
    except OSError as error:
        return _default_memory(), f"Could not read session memory: {error}"


def save_session_memory(memory):
    SESSION_DIR.mkdir(parents=True, exist_ok=True)

    with SESSION_FILE.open("w", encoding="utf-8") as file:
        json.dump(_normalize_memory(memory), file, indent=2)


def clear_session_memory():
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()


def result_summary(result):
    if not isinstance(result, dict):
        return "Command completed."

    for key in ("result_summary", "message"):
        value = result.get(key)
        if value:
            return str(value)

    return "Command completed."


def record_command(
    command,
    input_file=None,
    output_file=None,
    summary=None,
    backup_file=None,
    metadata=None,
    sheet_name=None,
):
    """Append a command entry and update the top-level current/last fields."""
    memory = load_session_memory()
    input_file = _as_string(input_file)
    output_file = _as_string(output_file)
    backup_file = _as_string(backup_file)
    summary = summary or "Command completed."

    entry = {
        "command": command,
        "input_file": input_file,
        "output_file": output_file,
        "summary": summary,
        "timestamp": _now(),
    }

    if backup_file:
        entry["backup_file"] = backup_file

    if metadata:
        entry["metadata"] = metadata

    if output_file:
        memory["last_output_file"] = output_file

    working_file = output_file if _is_excel_file(output_file) else input_file
    if _is_excel_file(working_file):
        memory["current_file"] = working_file
        memory["current_sheet"] = sheet_name or _infer_sheet_name(working_file)

    memory["last_command"] = command
    memory["last_result_summary"] = summary
    memory["command_history"].append(entry)

    save_session_memory(memory)
    return memory


def record_result(command, input_file, result):
    """Persist a successful command result into session memory."""
    if not isinstance(result, dict) or result.get("status") != "success":
        return load_session_memory()

    return record_command(
        command=command,
        input_file=result.get("input_file") or input_file,
        output_file=result.get("output_file"),
        summary=result_summary(result),
        backup_file=result.get("backup_file"),
        metadata=_safe_metadata(result),
        sheet_name=result.get("sheet_name") or result.get("current_sheet"),
    )


def latest_backup_entry(memory=None):
    memory = _normalize_memory(memory or load_session_memory())

    for entry in reversed(memory.get("command_history", [])):
        if isinstance(entry, dict) and entry.get("backup_file"):
            return entry

    return None
