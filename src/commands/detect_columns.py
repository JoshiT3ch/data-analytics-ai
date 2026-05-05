import os

import pandas as pd

from src.core.session_memory import load_session_memory
from src.core.workbook_manager import WorkbookError, read_sheet, resolve_sheet_name


def _infer_column_types(df):
    return [(column, str(dtype)) for column, dtype in df.dtypes.items()]


def _session_sheet():
    sheet_name = load_session_memory().get("current_sheet")
    return sheet_name if isinstance(sheet_name, str) and sheet_name else None


def detect_columns(file_path, sheet_name=None):
    try:
        if not os.path.exists(file_path):
            message = "File not found"
            print(message)
            return {
                "status": "error",
                "output_file": None,
                "message": message,
            }

        resolved_sheet = resolve_sheet_name(
            file_path,
            requested_sheet=sheet_name,
            session_sheet=_session_sheet(),
        )
        df = read_sheet(file_path, resolved_sheet)
        columns = _infer_column_types(df)

        print(f"Sheet used: {resolved_sheet}")
        print("Columns and inferred data types:")
        for column, dtype in columns:
            print(f"{column}: {dtype}")

        return {
            "status": "success",
            "output_file": None,
            "message": "Detected columns.",
            "columns": columns,
            "sheet_name": resolved_sheet,
        }

    except WorkbookError as error:
        message = str(error)
        print(message)
        return {
            "status": "error",
            "output_file": None,
            "message": message,
        }
    except ValueError as error:
        message = f"Invalid file: {error}"
        print(message)
        return {
            "status": "error",
            "output_file": None,
            "message": message,
        }
    except Exception as error:
        message = f"Error: {error}"
        print(message)
        return {
            "status": "error",
            "output_file": None,
            "message": message,
        }
