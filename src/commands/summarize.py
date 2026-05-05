import os

import pandas as pd

from src.core.session_memory import load_session_memory
from src.core.workbook_manager import WorkbookError, read_sheet, resolve_sheet_name


def _get_output_path(file_path):
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    os.makedirs("outputs", exist_ok=True)
    return f"outputs/{file_name}_summary.txt"


def _build_summary(df):
    lines = [
        f"Rows: {len(df)}",
        f"Columns: {len(df.columns)}",
        "",
        "Column names:",
    ]

    lines.extend(f"- {column}" for column in df.columns)
    lines.extend(["", "Basic statistics:"])

    numeric_df = df.select_dtypes(include="number")
    if numeric_df.empty:
        lines.append("No numeric columns found.")
    else:
        for column in numeric_df.columns:
            lines.extend(
                [
                    f"{column}:",
                    f"  Mean: {numeric_df[column].mean()}",
                    f"  Min: {numeric_df[column].min()}",
                    f"  Max: {numeric_df[column].max()}",
                ]
            )

    return "\n".join(lines)


def _session_sheet():
    sheet_name = load_session_memory().get("current_sheet")
    return sheet_name if isinstance(sheet_name, str) and sheet_name else None


def summarize(file_path, sheet_name=None):
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
        summary = _build_summary(df)
        output_path = _get_output_path(file_path)

        with open(output_path, "w", encoding="utf-8") as output_file:
            output_file.write(summary)

        print(f"Sheet used: {resolved_sheet}")
        print(summary)
        message = f"Saved to: {output_path}"
        print(message)
        return {
            "status": "success",
            "output_file": output_path,
            "message": message,
            "summary": summary,
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
