from pathlib import Path
import re

import pandas as pd


class WorkbookError(Exception):
    """User-facing workbook error."""


def _normalize_name(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _available_sheets_message(sheets):
    return ", ".join(str(sheet) for sheet in sheets)


def list_sheets(file_path):
    source = Path(file_path)
    if not source.exists():
        raise WorkbookError(f"File not found: {file_path}")

    try:
        with pd.ExcelFile(source) as excel_file:
            return list(excel_file.sheet_names)
    except ValueError as error:
        raise WorkbookError(f"Invalid file: {error}") from error
    except Exception as error:
        raise WorkbookError(f"Error reading workbook: {error}") from error


def match_sheet_name(file_path, sheet_name):
    sheets = list_sheets(file_path)
    requested = _normalize_name(sheet_name)

    for sheet in sheets:
        if _normalize_name(sheet) == requested:
            return sheet

    return None


def sheet_exists(file_path, sheet_name):
    return match_sheet_name(file_path, sheet_name) is not None


def get_default_sheet(file_path):
    sheets = list_sheets(file_path)
    if not sheets:
        raise WorkbookError("Workbook has no sheets.")
    return sheets[0]


def resolve_sheet_name(file_path, requested_sheet=None, session_sheet=None):
    sheets = list_sheets(file_path)
    if not sheets:
        raise WorkbookError("Workbook has no sheets.")

    if requested_sheet:
        matched_sheet = match_sheet_name(file_path, requested_sheet)
        if matched_sheet:
            return matched_sheet

        raise WorkbookError(
            f"Sheet '{requested_sheet}' was not found. "
            f"Available sheets: {_available_sheets_message(sheets)}"
        )

    if session_sheet:
        matched_sheet = match_sheet_name(file_path, session_sheet)
        if matched_sheet:
            return matched_sheet

    return sheets[0]


def read_sheet(file_path, sheet_name):
    try:
        return pd.read_excel(file_path, sheet_name=sheet_name)
    except ValueError as error:
        raise WorkbookError(f"Invalid file or sheet: {error}") from error
    except Exception as error:
        raise WorkbookError(f"Error reading sheet: {error}") from error


def write_sheet_to_workbook(source_file, output_file, sheet_name, df):
    sheets = list_sheets(source_file)
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        for sheet in sheets:
            if sheet == sheet_name:
                df.to_excel(writer, sheet_name=sheet, index=False)
            else:
                sheet_df = pd.read_excel(source_file, sheet_name=sheet)
                sheet_df.to_excel(writer, sheet_name=sheet, index=False)
