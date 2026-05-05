from src.core.session_memory import load_session_memory
from src.core.workbook_manager import WorkbookError, resolve_sheet_name


def _current_session_file():
    current_file = load_session_memory().get("current_file")
    if isinstance(current_file, str) and current_file.lower().endswith(".xlsx"):
        return current_file
    return None


def set_current_sheet(file_path=None, sheet_name=None):
    file_path = file_path or _current_session_file()
    if not file_path:
        message = "No input file provided and no current session file found."
        print(message)
        return {
            "status": "error",
            "output_file": None,
            "message": message,
        }

    if not sheet_name:
        message = "No sheet name provided."
        print(message)
        return {
            "status": "error",
            "output_file": None,
            "message": message,
        }

    try:
        resolved_sheet = resolve_sheet_name(file_path, requested_sheet=sheet_name)
    except WorkbookError as error:
        message = str(error)
        print(message)
        return {
            "status": "error",
            "output_file": None,
            "message": message,
        }

    print(f"Current workbook set to: {file_path}")
    print(f"Current sheet set to: {resolved_sheet}")
    return {
        "status": "success",
        "output_file": None,
        "message": f"Current sheet set to: {resolved_sheet}",
        "result_summary": f"Current sheet set to {resolved_sheet}.",
        "sheet_name": resolved_sheet,
    }
