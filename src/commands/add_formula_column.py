from pathlib import Path
import re

import pandas as pd

from src.core.session_memory import load_session_memory


SUPPORTED_OPERATORS = {
    "+": "+",
    "plus": "+",
    "add": "+",
    "added to": "+",
    "-": "-",
    "minus": "-",
    "subtract": "-",
    "*": "*",
    "times": "*",
    "multiply": "*",
    "multiplied by": "*",
    "/": "/",
    "divide": "/",
    "divided by": "/",
}

OPERATOR_LABELS = {
    "+": "+",
    "-": "-",
    "*": "*",
    "/": "/",
}


def _current_session_file():
    current_file = load_session_memory().get("current_file")
    if isinstance(current_file, str) and current_file.lower().endswith(".xlsx"):
        return current_file
    return None


def _slugify(value):
    text = str(value or "formula").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "formula"


def output_path_for_formula(file_path, new_column=None):
    source = Path(file_path)
    Path("outputs").mkdir(parents=True, exist_ok=True)
    suffix = _slugify(new_column) if new_column else "formula"
    return (Path("outputs") / f"{source.stem}_with_{suffix}{source.suffix}").as_posix()


def _available_columns(df):
    return ", ".join(str(column) for column in df.columns)


def _normalize_column_name(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _match_column(df, requested_column):
    if not requested_column:
        return None

    requested = _normalize_column_name(requested_column)
    for column in df.columns:
        if _normalize_column_name(column) == requested:
            return column

    return None


def _normalize_operator(operator):
    normalized = str(operator or "").strip().lower()
    return SUPPORTED_OPERATORS.get(normalized)


def _formula_label(left_column, operator, right_column):
    return f"{left_column} {OPERATOR_LABELS[operator]} {right_column}"


def _missing_details_message():
    return (
        "Missing formula details. Provide new_column, left_column, operator, and right_column."
    )


def _missing_column_message(column, df):
    return f"Column '{column}' was not found. Available columns: {_available_columns(df)}"


def _profit_margin_guidance(new_column, missing_column):
    if (
        _normalize_column_name(new_column) == "profitmargin"
        and _normalize_column_name(missing_column) == "profit"
    ):
        return (
            "Profit margin requires Profit and Revenue columns. "
            "Try: add a formula column for profit using revenue minus cost."
        )

    return None


def _numeric_series(df, column):
    series = pd.to_numeric(df[column], errors="coerce")
    if series.dropna().empty:
        return None
    return series


def _calculate(left_series, operator, right_series):
    if operator == "+":
        return left_series + right_series
    if operator == "-":
        return left_series - right_series
    if operator == "*":
        return left_series * right_series
    if operator == "/":
        return left_series / right_series
    return None


def _validate_formula(df, new_column, left_column, operator, right_column):
    if not all([new_column, left_column, operator, right_column]):
        return None, None, None, None, _missing_details_message()

    normalized_operator = _normalize_operator(operator)
    if not normalized_operator:
        return None, None, None, None, (
            "Unsupported operator. Supported operators: +, -, *, /"
        )

    matched_left = _match_column(df, left_column)
    if matched_left is None:
        guidance = _profit_margin_guidance(new_column, left_column)
        return None, None, None, None, guidance or _missing_column_message(left_column, df)

    matched_right = _match_column(df, right_column)
    if matched_right is None:
        return None, None, None, None, _missing_column_message(right_column, df)

    if _match_column(df, new_column) is not None:
        return None, None, None, None, f"Column '{new_column}' already exists."

    left_series = _numeric_series(df, matched_left)
    if left_series is None:
        return None, None, None, None, f"Column '{matched_left}' does not contain numeric values."

    right_series = _numeric_series(df, matched_right)
    if right_series is None:
        return None, None, None, None, f"Column '{matched_right}' does not contain numeric values."

    return matched_left, normalized_operator, matched_right, (left_series, right_series), None


def add_formula_column(
    file_path,
    new_column=None,
    left_column=None,
    operator=None,
    right_column=None,
    preview=False,
):
    """Add a calculated column to an Excel file."""
    file_path = file_path or _current_session_file()
    if not file_path:
        message = "No input file provided and no current session file found."
        print(message)
        return {
            "status": "error",
            "output_file": None,
            "message": message,
        }

    source = Path(file_path)
    if not source.exists():
        message = f"File not found: {file_path}"
        print(message)
        return {
            "status": "error",
            "output_file": None,
            "message": message,
        }

    try:
        df = pd.read_excel(source)
    except ValueError as error:
        message = f"Invalid file: {error}"
        print(message)
        return {
            "status": "error",
            "output_file": None,
            "message": message,
        }
    except Exception as error:
        message = f"Error reading file: {error}"
        print(message)
        return {
            "status": "error",
            "output_file": None,
            "message": message,
        }

    matched_left, normalized_operator, matched_right, operands, validation_error = _validate_formula(
        df,
        new_column,
        left_column,
        operator,
        right_column,
    )
    if validation_error:
        print(validation_error)
        return {
            "status": "error",
            "output_file": None,
            "message": validation_error,
        }

    formula = _formula_label(matched_left, normalized_operator, matched_right)
    if preview:
        message = "Preview only. No changes were applied."
        print("Preview only:")
        print("- Command: add-formula-column")
        print(f"- File: {file_path}")
        print(f"- New column: {new_column}")
        print(f"- Formula: {formula}")
        print("- No changes were applied.")
        return {
            "status": "success",
            "output_file": None,
            "message": message,
            "result_summary": message,
            "preview": True,
            "new_column": str(new_column),
            "formula": formula,
        }

    left_series, right_series = operands
    df[str(new_column)] = _calculate(left_series, normalized_operator, right_series)
    output_file = output_path_for_formula(file_path, new_column)
    df.to_excel(output_file, index=False)

    message = "Formula column added successfully."
    print(message)
    print(f"- New column: {new_column}")
    print(f"- Formula: {formula}")
    print(f"- Output saved to: {output_file}")
    return {
        "status": "success",
        "output_file": output_file,
        "message": message,
        "result_summary": f"Added formula column {new_column}.",
        "new_column": str(new_column),
        "left_column": str(matched_left),
        "operator": normalized_operator,
        "right_column": str(matched_right),
        "formula": formula,
        "affected_rows": int(len(df)),
    }
