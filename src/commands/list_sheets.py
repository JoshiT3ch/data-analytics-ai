from src.core.session_memory import load_session_memory
from src.core.workbook_manager import WorkbookError, list_sheets as workbook_sheets, resolve_sheet_name


def _current_session_file():
    current_file = load_session_memory().get("current_file")
    if isinstance(current_file, str) and current_file.lower().endswith(".xlsx"):
        return current_file
    return None


def list_sheets(file_path=None):
    file_path = file_path or _current_session_file()
    if not file_path:
        message = "No input file provided and no current session file found."
        print(message)
        return {
            "status": "error",
            "output_file": None,
            "message": message,
        }

    try:
        sheets = workbook_sheets(file_path)
        current_sheet = resolve_sheet_name(file_path)
    except WorkbookError as error:
        message = str(error)
        print(message)
        return {
            "status": "error",
            "output_file": None,
            "message": message,
        }

    print(f"Workbook: {file_path}")
    print("")
    print("Sheets found:")
    for sheet in sheets:
        print(f"- {sheet}")

    return {
        "status": "success",
        "output_file": None,
        "message": f"Found {len(sheets)} sheets.",
        "result_summary": f"Found {len(sheets)} sheets.",
        "sheets": sheets,
        "sheet_name": current_sheet,
    }
