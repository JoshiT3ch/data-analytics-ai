import io
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from src.core.command_registry import supported_commands
from src.core.executor import execute_plan
from src.core.nlp_parser import parse_plan
from src.core import session_memory
from src.core.workbook_manager import (
    WorkbookError,
    list_sheets as workbook_sheets,
    read_sheet,
    resolve_sheet_name,
)


ARTIFACT_KEYS = {
    "output_file",
    "summary_file",
    "insights_file",
    "dashboard_file",
    "manifest_file",
}


def _model_dict(model):
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_none=True)
    return model.dict(exclude_none=True)


def _session_snapshot():
    memory = session_memory.load_session_memory()
    return {
        "current_file": memory.get("current_file"),
        "current_sheet": memory.get("current_sheet"),
        "last_command": memory.get("last_command"),
        "last_output_file": memory.get("last_output_file"),
        "last_result_summary": memory.get("last_result_summary"),
    }


def _recent_commands(history, limit=5):
    if not isinstance(history, list):
        return []

    commands = []
    for entry in history[-limit:]:
        if isinstance(entry, dict) and entry.get("command"):
            commands.append(str(entry["command"]))

    return commands


def _error_response(
    message,
    command=None,
    file_path=None,
    sheet_name=None,
    output_text="",
    error=None,
):
    return {
        "success": False,
        "message": message,
        "command": command,
        "file_path": file_path,
        "sheet_name": sheet_name,
        "output_text": output_text,
        "artifacts": [],
        "session": _session_snapshot(),
        "error": error or message,
    }


def _artifact_type(path):
    return "directory" if Path(path).is_dir() else "file"


def _add_artifact(artifacts, seen, path):
    if not isinstance(path, str) or not path:
        return

    if path in seen or not Path(path).exists():
        return

    seen.add(path)
    artifacts.append(
        {
            "type": _artifact_type(path),
            "path": path,
        }
    )


def _collect_artifacts_from_value(value, artifacts, seen):
    if isinstance(value, dict):
        for key, nested_value in value.items():
            if key in ARTIFACT_KEYS:
                _add_artifact(artifacts, seen, nested_value)
            elif key in {"charts", "artifacts"}:
                _collect_artifacts_from_value(nested_value, artifacts, seen)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                _add_artifact(artifacts, seen, item)
            else:
                _collect_artifacts_from_value(item, artifacts, seen)


def _collect_artifacts(results: Iterable[Dict[str, Any]]):
    artifacts = []
    seen = set()
    for result in results:
        _collect_artifacts_from_value(result, artifacts, seen)
    return artifacts


def _first_result(execution_result):
    results = execution_result.get("results")
    if isinstance(results, list) and results:
        return results[0]
    return {}


def _last_result(execution_result):
    results = execution_result.get("results")
    if isinstance(results, list) and results:
        return results[-1]
    return {}


def _apply_request_context(plan, file_path=None, sheet_name=None):
    if not isinstance(plan, list):
        return plan

    contextualized = []
    for step in plan:
        if not isinstance(step, dict):
            contextualized.append(step)
            continue

        updated = step.copy()
        if file_path:
            updated["file_path"] = file_path
        if sheet_name:
            updated["sheet_name"] = sheet_name
        contextualized.append(updated)

    return contextualized


def _command_options_from_payload(payload):
    ignored = {"command", "preview"}
    return {
        key: value
        for key, value in payload.items()
        if key not in ignored and value is not None
    }


def _success_message(execution_result):
    if execution_result.get("status") == "success":
        return "Command executed successfully."
    return execution_result.get("message") or "Command failed."


def _execution_response(plan, execution_result, output_text):
    first_step = plan[0] if plan else {}
    first_result = _first_result(execution_result)
    last_result = _last_result(execution_result)
    success = execution_result.get("status") == "success"
    command = first_result.get("command") or first_step.get("command")
    file_path = (
        first_result.get("input_file")
        or first_step.get("file_path")
        or session_memory.load_session_memory().get("current_file")
    )
    sheet_name = (
        last_result.get("sheet_name")
        or last_result.get("current_sheet")
        or first_result.get("sheet_name")
        or first_step.get("sheet_name")
        or session_memory.load_session_memory().get("current_sheet")
    )
    results = execution_result.get("results") or []

    return {
        "success": success,
        "message": _success_message(execution_result),
        "command": command,
        "file_path": file_path,
        "sheet_name": sheet_name,
        "output_text": output_text.strip(),
        "artifacts": _collect_artifacts(results),
        "session": _session_snapshot(),
        "error": None if success else execution_result.get("message"),
    }


def execute_chat_request(request):
    payload = _model_dict(request)
    message = str(payload.get("message") or "").strip()
    if not message:
        return _error_response("message is required.", error="Missing message")

    stdout = io.StringIO()
    try:
        with redirect_stdout(stdout):
            plan = parse_plan(message)
            plan = _apply_request_context(
                plan,
                file_path=payload.get("file_path"),
                sheet_name=payload.get("sheet_name"),
            )
            if not plan:
                return _error_response(
                    "Could not understand input",
                    output_text=stdout.getvalue(),
                    error="Unsupported command",
                )
            execution_result = execute_plan(
                plan,
                preview=bool(payload.get("preview", False)),
            )
    except Exception as error:
        return _error_response(
            "Command execution failed.",
            output_text=stdout.getvalue(),
            error=str(error),
        )

    return _execution_response(plan, execution_result, stdout.getvalue())


def execute_structured_command(request):
    payload = _model_dict(request)
    command = str(payload.get("command") or "").strip()
    if not command:
        return _error_response("command is required.", error="Missing command")

    if command not in supported_commands():
        return _error_response(
            f"Unsupported command: {command}",
            command=command,
            file_path=payload.get("file_path"),
            sheet_name=payload.get("sheet_name"),
            error="Unsupported command",
        )

    step = {"command": command}
    step.update(_command_options_from_payload(payload))
    plan = [step]

    stdout = io.StringIO()
    try:
        with redirect_stdout(stdout):
            execution_result = execute_plan(
                plan,
                preview=bool(payload.get("preview", False)),
            )
    except Exception as error:
        return _error_response(
            "Command execution failed.",
            command=command,
            file_path=payload.get("file_path"),
            sheet_name=payload.get("sheet_name"),
            output_text=stdout.getvalue(),
            error=str(error),
        )

    return _execution_response(plan, execution_result, stdout.getvalue())


def get_workbook_status():
    memory = session_memory.load_session_memory()
    current_file = memory.get("current_file")
    current_sheet = memory.get("current_sheet")

    base_response = {
        "current_file": current_file,
        "current_sheet": current_sheet,
        "sheets": [],
        "sheet_summary": {},
        "last_command": memory.get("last_command"),
        "last_output_file": memory.get("last_output_file"),
        "last_result_summary": memory.get("last_result_summary"),
        "recent_commands": _recent_commands(memory.get("command_history")),
        "current_sheet_valid": None,
    }

    if not current_file:
        return {
            "success": False,
            "message": "No workbook context found. Try opening or setting a workbook first.",
            **base_response,
        }

    if not Path(current_file).exists():
        return {
            "success": False,
            "message": (
                "Current workbook was found in memory but the file no longer exists: "
                f"{current_file}"
            ),
            **base_response,
        }

    try:
        sheets = workbook_sheets(current_file)
    except WorkbookError as error:
        return {
            "success": False,
            "message": str(error),
            **base_response,
        }

    sheet_summary = {}
    for sheet in sheets:
        try:
            df = read_sheet(current_file, sheet)
            sheet_summary[sheet] = {
                "rows": int(len(df)),
                "columns": int(len(df.columns)),
            }
        except WorkbookError:
            sheet_summary[sheet] = {
                "rows": None,
                "columns": None,
            }

    current_sheet_valid = not current_sheet or current_sheet in sheets
    message = "Workbook context loaded."
    if not current_sheet_valid:
        message = "Workbook context loaded, but the current sheet was not found."

    return {
        "success": True,
        "message": message,
        **base_response,
        "sheets": sheets,
        "sheet_summary": sheet_summary,
        "current_sheet_valid": current_sheet_valid,
    }


def list_workbook_sheets(file_path: Optional[str]):
    if not file_path:
        return {
            "success": False,
            "file_path": file_path,
            "sheets": [],
            "message": "file_path is required.",
        }

    try:
        sheets = workbook_sheets(file_path)
    except WorkbookError as error:
        message = str(error)
        if message.startswith("File not found:"):
            message = f"Workbook not found: {file_path}"
        return {
            "success": False,
            "file_path": file_path,
            "sheets": [],
            "message": message,
        }

    return {
        "success": True,
        "file_path": file_path,
        "sheets": sheets,
        "message": f"Found {len(sheets)} sheets.",
    }


def update_workbook_context(request):
    payload = _model_dict(request)
    file_path = payload.get("file_path")
    requested_sheet = payload.get("sheet_name")

    if not file_path:
        return {
            "success": False,
            "current_file": None,
            "current_sheet": None,
            "message": "file_path is required.",
        }

    try:
        resolved_sheet = resolve_sheet_name(file_path, requested_sheet=requested_sheet)
    except WorkbookError as error:
        message = str(error)
        if message.startswith("File not found:"):
            message = f"Workbook not found: {file_path}"
        return {
            "success": False,
            "current_file": file_path,
            "current_sheet": requested_sheet,
            "message": message,
        }

    session_memory.record_command(
        command="set-current-sheet",
        input_file=file_path,
        output_file=None,
        summary=f"Current sheet set to {resolved_sheet}.",
        sheet_name=resolved_sheet,
    )

    return {
        "success": True,
        "current_file": file_path,
        "current_sheet": resolved_sheet,
        "message": "Workbook context updated.",
    }
