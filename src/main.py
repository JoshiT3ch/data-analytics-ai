import json
import sys

from src.core.executor import execute_plan
from src.core.memory import clear_memory, load_memory
from src.core.nlp_parser import parse_plan
from src.utils.plan_formatter import format_execution_plan, format_execution_summary


def _safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(str(text).encode("ascii", errors="replace").decode("ascii"))


def _parse_flags(args):
    dry_run = "--dry-run" in args
    debug = "--debug" in args
    confirm = "--confirm" in args
    cleaned_args = [
        arg
        for arg in args
        if arg not in {"--dry-run", "--debug", "--confirm"}
    ]

    return cleaned_args, dry_run, debug, confirm


def _confirm_execution():
    answer = input("Proceed with execution? (y/n): ").strip().lower()
    return answer in {"y", "yes"}


def _preview_and_execute(plan, dry_run=False, debug=False, confirm=False):
    _safe_print(format_execution_plan(plan))

    if dry_run:
        result = execute_plan(plan, dry_run=True, debug=debug)
        _safe_print(format_execution_summary(result, plan))
        return result

    if confirm and not _confirm_execution():
        print("Execution cancelled.")
        return {
            "status": "cancelled",
            "message": "Execution cancelled by user.",
            "results": [],
        }

    result = execute_plan(plan, dry_run=False, debug=debug)
    _safe_print(format_execution_summary(result, plan))
    return result


def main():
    args, dry_run, debug, confirm = _parse_flags(sys.argv[1:])

    if len(args) < 1:
        print("Usage:")
        print("1. python -m src.main <command> <file>")
        print('2. python -m src.main "natural language input"')
        print("3. python -m src.main memory")
        print("4. python -m src.main memory-clear")
        print("Optional flags: --dry-run --debug --confirm")
        return

    if len(args) == 1:
        user_input = args[0]

        if user_input == "memory":
            _safe_print(json.dumps(load_memory(), indent=2))
            return

        if user_input == "memory-clear":
            clear_memory()
            print("Memory cleared.")
            return

        plan = parse_plan(user_input)

        if not plan:
            print("Could not understand input")
            return

        _preview_and_execute(plan, dry_run=dry_run, debug=debug, confirm=confirm)
        return

    command = args[0]
    file_path = args[1]

    if dry_run or debug:
        _preview_and_execute(
            [{"command": command, "file_path": file_path}],
            dry_run=dry_run,
            debug=debug,
            confirm=confirm,
        )
        return

    if confirm:
        _preview_and_execute(
            [{"command": command, "file_path": file_path}],
            dry_run=False,
            debug=False,
            confirm=True,
        )
        return

    execute_plan([{"command": command, "file_path": file_path}], dry_run=False, debug=False)


if __name__ == "__main__":
    main()
