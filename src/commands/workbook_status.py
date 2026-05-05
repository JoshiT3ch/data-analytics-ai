from pathlib import Path

from src.core.session_memory import load_session_memory
from src.core.workbook_manager import WorkbookError, list_sheets, read_sheet


NO_CONTEXT_MESSAGE = (
    "No workbook context found. Try opening or setting a workbook first.\n\n"
    'Example:\n'
    'python -m src.main "list sheets in data/raw/company_report.xlsx"\n'
    'python -m src.main "use the Sales sheet from data/raw/company_report.xlsx"'
)


def _recent_commands(history, limit=5):
    if not isinstance(history, list):
        return []

    commands = []
    for entry in history[-limit:]:
        if isinstance(entry, dict) and entry.get("command"):
            commands.append(str(entry["command"]))

    return commands


def _sheet_summaries(file_path, sheets):
    summaries = []
    for sheet in sheets:
        try:
            df = read_sheet(file_path, sheet)
            summaries.append(
                {
                    "sheet": sheet,
                    "rows": int(len(df)),
                    "columns": int(len(df.columns)),
                }
            )
        except WorkbookError:
            summaries.append(
                {
                    "sheet": sheet,
                    "rows": None,
                    "columns": None,
                }
            )

    return summaries


def _print_status(memory, sheets, summaries, current_sheet_valid):
    print("Excel Context")
    print("")
    print(f"Current workbook: {memory.get('current_file')}")
    print(f"Current sheet: {memory.get('current_sheet') or 'not set'}")
    if memory.get("current_sheet") and not current_sheet_valid:
        print("Current sheet warning: stored sheet was not found in the workbook.")

    print("")
    print("Available sheets:")
    for sheet in sheets:
        print(f"- {sheet}")

    print("")
    print("Sheet Summary:")
    for summary in summaries:
        if summary["rows"] is None:
            print(f"- {summary['sheet']}: unavailable")
        else:
            print(
                f"- {summary['sheet']}: {summary['rows']} rows, "
                f"{summary['columns']} columns"
            )

    print("")
    print(f"Last command: {memory.get('last_command') or 'none'}")
    print(f"Last output file: {memory.get('last_output_file') or 'none'}")
    print(f"Last result: {memory.get('last_result_summary') or 'none'}")

    recent = _recent_commands(memory.get("command_history"))
    print("")
    print("Recent commands:")
    if recent:
        for command in recent:
            print(f"- {command}")
    else:
        print("- none")


def workbook_status(file_path=None):
    """Print current workbook/session context."""
    memory = load_session_memory()
    current_file = memory.get("current_file")

    if not current_file:
        print(NO_CONTEXT_MESSAGE)
        return {
            "status": "error",
            "output_file": None,
            "message": NO_CONTEXT_MESSAGE,
        }

    if not Path(current_file).exists():
        message = (
            "Current workbook was found in memory but the file no longer exists:\n"
            f"{current_file}"
        )
        print(message)
        return {
            "status": "error",
            "output_file": None,
            "message": message,
            "current_file": current_file,
            "current_sheet": memory.get("current_sheet"),
        }

    try:
        sheets = list_sheets(current_file)
        summaries = _sheet_summaries(current_file, sheets)
    except WorkbookError as error:
        message = str(error)
        print(message)
        return {
            "status": "error",
            "output_file": None,
            "message": message,
            "current_file": current_file,
            "current_sheet": memory.get("current_sheet"),
        }

    current_sheet = memory.get("current_sheet")
    current_sheet_valid = not current_sheet or current_sheet in sheets
    _print_status(memory, sheets, summaries, current_sheet_valid)

    return {
        "status": "success",
        "output_file": None,
        "message": "Workbook status displayed.",
        "result_summary": "Workbook status displayed.",
        "current_file": current_file,
        "current_sheet": current_sheet,
        "current_sheet_valid": current_sheet_valid,
        "sheets": sheets,
        "sheet_summaries": summaries,
        "last_command": memory.get("last_command"),
        "last_output_file": memory.get("last_output_file"),
        "last_result_summary": memory.get("last_result_summary"),
        "recent_commands": _recent_commands(memory.get("command_history")),
    }
