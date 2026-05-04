import json
import sys

from src.core.executor import execute_plan
from src.core.memory import clear_memory, load_memory
from src.core.nlp_parser import parse_plan
from src.core.router import route_command
from src.core.session_memory import clear_session_memory, load_session_memory
from src.utils.plan_formatter import format_execution_plan, format_execution_summary


def _safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(str(text).encode("ascii", errors="replace").decode("ascii"))


def _parse_flags(args):
    dry_run = "--dry-run" in args
    preview = "--preview" in args
    debug = "--debug" in args
    confirm = "--confirm" in args
    cleaned_args = [
        arg
        for arg in args
        if arg not in {"--dry-run", "--preview", "--debug", "--confirm"}
    ]

    return cleaned_args, dry_run, preview, debug, confirm


def _confirm_execution():
    answer = input("Proceed with execution? (y/n): ").strip().lower()
    return answer in {"y", "yes"}


def _preview_and_execute(plan, dry_run=False, preview=False, debug=False, confirm=False):
    _safe_print(format_execution_plan(plan))

    if dry_run or preview:
        result = execute_plan(plan, dry_run=dry_run, preview=preview, debug=debug)
        _safe_print(format_execution_summary(result, plan))
        return result

    if confirm and not _confirm_execution():
        print("Execution cancelled.")
        return {
            "status": "cancelled",
            "message": "Execution cancelled by user.",
            "results": [],
        }

    result = execute_plan(plan, dry_run=False, preview=False, debug=debug)
    _safe_print(format_execution_summary(result, plan))
    return result


def _is_undo_request(text):
    normalized = " ".join(str(text or "").lower().split())
    return normalized in {"undo", "undo last action", "undo last", "undo previous action"}


def _show_memory():
    session_memory = load_session_memory()
    legacy_memory = load_memory()

    if session_memory.get("command_history"):
        _safe_print(json.dumps(session_memory, indent=2))
    else:
        _safe_print(json.dumps(legacy_memory, indent=2))


def main():
    args, dry_run, preview, debug, confirm = _parse_flags(sys.argv[1:])

    if len(args) < 1:
        print("Usage:")
        print("1. python -m src.main <command> <file>")
        print('2. python -m src.main "natural language input"')
        print("3. python -m src.main memory")
        print("4. python -m src.main memory-clear")
        print("5. python -m src.main undo")
        print('6. python -m src.main "create a bar chart of sales by category from data/raw/sales.xlsx"')
        print("Optional flags: --preview --dry-run --debug --confirm")
        return

    if _is_undo_request(" ".join(args)):
        result = route_command("undo")
        if result.get("status") != "success":
            return
        return

    if len(args) == 1:
        user_input = args[0]

        if user_input == "memory":
            _show_memory()
            return

        if user_input == "memory-clear":
            clear_memory()
            clear_session_memory()
            print("Memory cleared.")
            return

        plan = parse_plan(user_input)

        if not plan:
            print("Could not understand input")
            return

        _preview_and_execute(
            plan,
            dry_run=dry_run,
            preview=preview,
            debug=debug,
            confirm=confirm,
        )
        return

    command = args[0]
    file_path = args[1]

    if dry_run or preview or debug:
        _preview_and_execute(
            [{"command": command, "file_path": file_path}],
            dry_run=dry_run,
            preview=preview,
            debug=debug,
            confirm=confirm,
        )
        return

    if confirm:
        _preview_and_execute(
            [{"command": command, "file_path": file_path}],
            dry_run=False,
            preview=False,
            debug=False,
            confirm=True,
        )
        return

    execute_plan(
        [{"command": command, "file_path": file_path}],
        dry_run=False,
        preview=False,
        debug=False,
    )


if __name__ == "__main__":
    main()
