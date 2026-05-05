from pathlib import Path

import pandas as pd

from src.core.session_memory import load_session_memory
from src.core.workbook_manager import (
    WorkbookError,
    read_sheet,
    resolve_sheet_name,
    write_sheet_to_workbook,
)


def _get_output_path(file_path):
    source = Path(file_path)
    Path("outputs").mkdir(parents=True, exist_ok=True)
    return (Path("outputs") / f"{source.stem}_cleaned{source.suffix}").as_posix()


def _session_sheet():
    sheet_name = load_session_memory().get("current_sheet")
    return sheet_name if isinstance(sheet_name, str) and sheet_name else None


def clean_duplicates(file_path, preview=False, sheet_name=None):
    try:
        source = Path(file_path)
        if not source.exists():
            message = f"File not found: {file_path}"
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
        original_rows = len(df)
        duplicate_rows = int(df.duplicated().sum())
        df_cleaned = df.drop_duplicates()
        cleaned_rows = len(df_cleaned)

        if preview:
            message = f"Preview only. Found {duplicate_rows} duplicate rows. No changes were applied."
            print("Preview only:")
            print("- Command: clean-duplicates")
            print(f"- File: {file_path}")
            print(f"- Sheet: {resolved_sheet}")
            print(f"- Duplicate rows found: {duplicate_rows}")
            print("- No changes were applied.")
            return {
                "status": "success",
                "output_file": None,
                "message": message,
                "result_summary": message,
                "preview": True,
                "original_rows": original_rows,
                "cleaned_rows": cleaned_rows,
                "duplicate_rows": duplicate_rows,
                "affected_rows": duplicate_rows,
                "sheet_name": resolved_sheet,
            }

        output_path = _get_output_path(file_path)
        write_sheet_to_workbook(file_path, output_path, resolved_sheet, df_cleaned)

        message = (
            f"Done. Removed {duplicate_rows} duplicate rows from sheet {resolved_sheet}. "
            f"Output saved to {output_path}"
        )
        print(message)
        return {
            "status": "success",
            "output_file": output_path,
            "message": message,
            "result_summary": f"Removed {duplicate_rows} duplicate rows.",
            "original_rows": original_rows,
            "cleaned_rows": cleaned_rows,
            "duplicate_rows": duplicate_rows,
            "affected_rows": duplicate_rows,
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
