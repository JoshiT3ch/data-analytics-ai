import os

import pandas as pd

from src.core.session_memory import load_session_memory
from src.core.workbook_manager import (
    WorkbookError,
    read_sheet,
    resolve_sheet_name,
    write_sheet_to_workbook,
)


def _get_output_path(file_path):
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    os.makedirs("outputs", exist_ok=True)
    return f"outputs/{file_name}_no_empty.xlsx"


def _remove_empty_rows(df):
    return df.dropna(how="all")


def _session_sheet():
    sheet_name = load_session_memory().get("current_sheet")
    return sheet_name if isinstance(sheet_name, str) and sheet_name else None


def remove_empty_rows(file_path, sheet_name=None):
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
        cleaned_df = _remove_empty_rows(df)
        removed_rows = len(df) - len(cleaned_df)
        output_path = _get_output_path(file_path)

        write_sheet_to_workbook(file_path, output_path, resolved_sheet, cleaned_df)

        print(f"Sheet used: {resolved_sheet}")
        print(f"Original rows: {len(df)}")
        print(f"Rows after removing empty rows: {len(cleaned_df)}")
        message = (
            f"Done. Removed {removed_rows} empty rows from sheet {resolved_sheet}. "
            f"Output saved to {output_path}"
        )
        print(message)
        return {
            "status": "success",
            "output_file": output_path,
            "message": message,
            "result_summary": f"Removed {removed_rows} empty rows.",
            "original_rows": len(df),
            "cleaned_rows": len(cleaned_df),
            "removed_rows": removed_rows,
            "affected_rows": removed_rows,
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
