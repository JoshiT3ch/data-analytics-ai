import json
import os
from datetime import datetime
from difflib import get_close_matches
from uuid import uuid4

from src.core.backup_manager import create_backup
from src.core.command_registry import COMMANDS, get_command_metadata
from src.core.memory import update_memory_after_step
from src.core.router import route_command
from src.core.session_memory import record_result


RAW_DATA_DIR = os.path.join("data", "raw")


def _timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def _write_log(log_data):
    os.makedirs("logs", exist_ok=True)
    log_file = os.path.join("logs", f"run_{_timestamp()}_{uuid4().hex[:8]}.json")

    with open(log_file, "w", encoding="utf-8") as file:
        json.dump(log_data, file, indent=2)

    return log_file


def _error_result(message, results=None, step_index=None, log_data=None, write_log=True):
    print(message)
    response = {
        "status": "error",
        "message": message,
        "failed_step": step_index,
        "results": results or [],
    }

    if log_data is not None:
        log_data["status"] = "error"
        log_data["message"] = message
        log_data["failed_step"] = step_index
        log_data["results"] = results or []
        if write_log:
            response["log_file"] = _write_log(log_data)

    return response


def _as_result(command, file_path, result):
    if isinstance(result, dict):
        normalized = result.copy()
    else:
        normalized = {
            "status": "success",
            "output_file": None,
            "message": "Command completed.",
        }

    normalized.setdefault("status", "success")
    normalized.setdefault("output_file", None)
    normalized.setdefault("message", "Command completed.")
    normalized["command"] = command
    normalized["input_file"] = file_path

    return normalized


def _available_raw_files():
    try:
        if not os.path.isdir(RAW_DATA_DIR):
            return []

        return sorted(
            f"data/raw/{file_name}"
            for file_name in os.listdir(RAW_DATA_DIR)
            if file_name.lower().endswith(".xlsx")
        )
    except OSError:
        return []


def _closest_raw_file(file_path):
    raw_files = _available_raw_files()
    if not raw_files:
        return None

    requested_name = os.path.basename(str(file_path or ""))
    raw_names = {os.path.basename(path): path for path in raw_files}
    matches = get_close_matches(requested_name, raw_names.keys(), n=1, cutoff=0.5)

    if matches:
        return raw_names[matches[0]]

    return raw_files[0] if len(raw_files) == 1 else None


def _missing_file_message(file_path):
    suggestion = _closest_raw_file(file_path)
    if suggestion:
        return f"File not found: {file_path}. Did you mean: {suggestion}?"

    return f"File not found: {file_path}"


def _expected_output_file(command, file_path):
    metadata = get_command_metadata(command) or {}
    output_path_builder = metadata.get("output_path")

    if callable(output_path_builder) and file_path:
        return output_path_builder(file_path)

    return None


def _chainable_output_file(command, input_file, result, dry_run=False):
    metadata = get_command_metadata(command) or {}
    if not metadata.get("chainable_output"):
        return None

    output_file = result.get("output_file") if isinstance(result, dict) else None
    if not output_file and dry_run:
        output_file = _expected_output_file(command, input_file)

    if not isinstance(output_file, str) or not output_file.lower().endswith(".xlsx"):
        return None

    if not dry_run and not os.path.exists(output_file):
        return None

    return output_file


def _validate_step_shape(step, index, has_current_file):
    if not isinstance(step, dict):
        return f"Step {index} is malformed."

    command = step.get("command")
    if not isinstance(command, str) or not command.strip():
        return f"Step {index} is missing a command."

    if command not in COMMANDS:
        return f"Unsupported command at step {index}: {command}"

    file_path = step.get("file_path")
    if not file_path and not has_current_file:
        return f"Step {index} is missing a file_path and there is no previous output to use."

    if file_path is not None and not isinstance(file_path, str):
        return f"Step {index} has an invalid file_path."

    return None


def _resolve_step_file(step, current_file_path, warnings):
    requested_file_path = step.get("file_path")

    if current_file_path and not requested_file_path:
        warnings.append(f"Using previous output file: {current_file_path}")
        return current_file_path

    if current_file_path and requested_file_path and requested_file_path != current_file_path:
        warnings.append(
            f"Using chained file {current_file_path} instead of requested {requested_file_path}."
        )
        return current_file_path

    return requested_file_path or current_file_path


def _validate_file(file_path, dry_run=False, allow_virtual=False):
    if not file_path:
        return "Missing file path."

    if dry_run and allow_virtual:
        return None

    if os.path.exists(file_path):
        return None

    return _missing_file_message(file_path)


def _initial_log(plan, dry_run, debug, preview=False):
    return {
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "status": "running",
        "dry_run": dry_run,
        "preview": preview,
        "debug": debug,
        "plan": plan,
        "steps": [],
        "results": [],
        "warnings": [],
    }


def _should_create_backup(metadata, file_path):
    return (
        bool(metadata.get("creates_backup"))
        and isinstance(file_path, str)
        and file_path.lower().endswith(".xlsx")
    )


def execute_plan(plan, dry_run=False, debug=False, preview=False):
    if not isinstance(plan, list) or not plan:
        return _error_result("Could not understand input")

    write_logs = not dry_run and not preview
    log_data = _initial_log(plan, dry_run, debug, preview)
    results = []
    effective_plan = []
    current_file_path = None
    current_file_is_virtual = False

    if debug:
        print("Execution plan:")
        print(json.dumps({"steps": plan}, indent=2))

    for index, step in enumerate(plan, start=1):
        shape_error = _validate_step_shape(step, index, current_file_path is not None)
        if shape_error:
            return _error_result(shape_error, results, index, log_data, write_logs)

        command = step["command"]
        metadata = get_command_metadata(command) or {}
        warnings = []
        file_path = _resolve_step_file(step, current_file_path, warnings)

        file_error = _validate_file(
            file_path,
            dry_run=dry_run or preview,
            allow_virtual=current_file_is_virtual,
        )
        if file_error:
            return _error_result(file_error, results, index, log_data, write_logs)

        for warning in warnings:
            print(f"Warning: {warning}")
            log_data["warnings"].append(
                {
                    "step": index,
                    "message": warning,
                }
            )

        transition = {
            "step": index,
            "command": command,
            "command_type": metadata.get("type"),
            "input_file": file_path,
            "output_file": None,
            "backup_file": None,
            "status": "pending",
            "message": "",
            "warnings": warnings,
        }
        log_data["steps"].append(transition)

        print(f"Step {index}/{len(plan)}: {command} -> {file_path}")

        if dry_run:
            output_file = _expected_output_file(command, file_path)
            result = {
                "status": "success",
                "output_file": output_file,
                "message": "Dry run: command was validated but not executed.",
                "command": command,
                "input_file": file_path,
            }
        elif preview:
            result = _as_result(
                command,
                file_path,
                route_command(command, file_path, preview=True),
            )
            result["preview"] = True
        else:
            backup_file = None
            if _should_create_backup(metadata, file_path):
                try:
                    backup_file = create_backup(file_path, command)
                except (OSError, FileNotFoundError) as error:
                    return _error_result(
                        f"Could not create backup before {command}: {error}",
                        results,
                        index,
                        log_data,
                        write_logs,
                    )

            result = _as_result(command, file_path, route_command(command, file_path))
            if backup_file:
                result["backup_file"] = backup_file

        results.append(result)
        transition["status"] = result.get("status")
        transition["output_file"] = result.get("output_file")
        transition["backup_file"] = result.get("backup_file")
        transition["message"] = result.get("message", "")

        if result.get("status") != "success":
            message = f"Step {index} failed: {result.get('message', 'Command failed.')}"
            return _error_result(message, results, index, log_data, write_logs)

        effective_step = {
            "command": command,
            "file_path": file_path,
        }
        if "confidence" in step:
            effective_step["confidence"] = step.get("confidence")
        if "reason" in step:
            effective_step["reason"] = step.get("reason")
        effective_plan.append(effective_step)

        if not dry_run and not preview:
            memory_step = effective_step.copy()
            memory_step["_latest_plan"] = effective_plan
            update_memory_after_step(memory_step, result)
            record_result(command, file_path, result)

        next_file_path = _chainable_output_file(
            command,
            file_path,
            result,
            dry_run=dry_run or preview,
        )

        if metadata.get("chainable_output") and not next_file_path:
            message = f"Step {index} did not produce a chainable Excel output."
            return _error_result(message, results, index, log_data, write_logs)

        if next_file_path and next_file_path != file_path:
            if not preview:
                print(f"Working file updated: {file_path} -> {next_file_path}")
            transition["next_working_file"] = next_file_path
            current_file_path = next_file_path
            current_file_is_virtual = dry_run or preview
        else:
            current_file_path = file_path
            current_file_is_virtual = False

    log_data["status"] = "success"
    if dry_run:
        log_data["message"] = "Dry run completed successfully."
    elif preview:
        log_data["message"] = "Preview completed successfully."
    else:
        log_data["message"] = "Plan executed successfully."
    log_data["results"] = results
    log_file = _write_log(log_data) if write_logs else None

    response = {
        "status": "success",
        "message": log_data["message"],
        "results": results,
    }

    if log_file:
        response["log_file"] = log_file

    return response
