import re
import os
from pathlib import Path

Path("tmp/matplotlib").mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(Path("tmp/matplotlib")))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


CHART_OUTPUT_DIR = Path("outputs") / "charts"
SUPPORTED_CHART_TYPES = {"bar", "line", "pie", "histogram"}


def _slugify(value):
    text = str(value or "chart").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "chart"


def _output_path(title, chart_type):
    CHART_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return (CHART_OUTPUT_DIR / f"{_slugify(title)}_{chart_type}_chart.png").as_posix()


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

    for column in df.columns:
        normalized_column = _normalize_column_name(column)
        if normalized_column and normalized_column in requested:
            return column

    return None


def _column_error(requested_column, df):
    return f"Column '{requested_column}' was not found. Available columns: {_available_columns(df)}"


def _numeric_series(df, column):
    numeric_series = pd.to_numeric(df[column], errors="coerce").dropna()
    if numeric_series.empty:
        return None
    return numeric_series


def _plot_bar_or_line(df, chart_type, x_column, y_column, title, output_path):
    numeric_y = pd.to_numeric(df[y_column], errors="coerce")
    chart_df = df[[x_column]].copy()
    chart_df[y_column] = numeric_y
    chart_df = chart_df.dropna(subset=[x_column, y_column])

    if chart_df.empty:
        return f"Column '{y_column}' does not contain numeric values to plot."

    series = chart_df.groupby(x_column, sort=False, dropna=False)[y_column].sum()

    fig, ax = plt.subplots(figsize=(9, 5))
    kind = "bar" if chart_type == "bar" else "line"
    plot_kwargs = {"marker": "o"} if chart_type == "line" else {}
    series.plot(kind=kind, ax=ax, **plot_kwargs)
    ax.set_title(title)
    ax.set_xlabel(str(x_column))
    ax.set_ylabel(str(y_column))
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return None


def _plot_pie(df, x_column, y_column, title, output_path):
    chart_df = df.dropna(subset=[x_column])

    if chart_df.empty:
        return f"Column '{x_column}' does not contain values to plot."

    if y_column:
        numeric_y = pd.to_numeric(chart_df[y_column], errors="coerce")
        chart_df = chart_df.copy()
        chart_df[y_column] = numeric_y
        chart_df = chart_df.dropna(subset=[y_column])
        if chart_df.empty:
            return f"Column '{y_column}' does not contain numeric values to plot."
        series = chart_df.groupby(x_column, sort=False, dropna=False)[y_column].sum()
    else:
        series = chart_df[x_column].value_counts(sort=False)

    fig, ax = plt.subplots(figsize=(7, 7))
    series.plot(kind="pie", ax=ax, autopct="%1.1f%%")
    ax.set_title(title)
    ax.set_ylabel("")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return None


def _plot_histogram(df, x_column, title, output_path):
    series = _numeric_series(df, x_column)
    if series is None:
        return f"Column '{x_column}' does not contain numeric values to plot."

    fig, ax = plt.subplots(figsize=(8, 5))
    series.plot(kind="hist", ax=ax, bins=min(10, max(3, len(series))))
    ax.set_title(title)
    ax.set_xlabel(str(x_column))
    ax.set_ylabel("Frequency")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return None


def create_chart(file_path, chart_type=None, x_column=None, y_column=None, title=None):
    """Create a chart image from an Excel file."""
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

    chart_type = str(chart_type or "").strip().lower()
    if chart_type not in SUPPORTED_CHART_TYPES:
        message = "Unsupported chart type. Supported chart types: bar, line, pie, histogram"
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

    if not x_column:
        message = "Missing x_column for chart."
        print(message)
        return {
            "status": "error",
            "output_file": None,
            "message": message,
        }

    if chart_type in {"bar", "line"} and not y_column:
        message = f"Missing y_column for {chart_type} chart."
        print(message)
        return {
            "status": "error",
            "output_file": None,
            "message": message,
        }

    matched_x_column = _match_column(df, x_column)
    if not matched_x_column:
        message = _column_error(x_column, df)
        print(message)
        return {
            "status": "error",
            "output_file": None,
            "message": message,
        }

    matched_y_column = None
    if chart_type in {"bar", "line"} or y_column:
        matched_y_column = _match_column(df, y_column)
        if not matched_y_column:
            message = _column_error(y_column, df)
            print(message)
            return {
                "status": "error",
                "output_file": None,
                "message": message,
            }

    title = title or _default_title(chart_type, matched_x_column, matched_y_column)
    output_path = _output_path(title, chart_type)

    if chart_type in {"bar", "line"}:
        plot_error = _plot_bar_or_line(
            df,
            chart_type,
            matched_x_column,
            matched_y_column,
            title,
            output_path,
        )
    elif chart_type == "pie":
        plot_error = _plot_pie(df, matched_x_column, matched_y_column, title, output_path)
    else:
        plot_error = _plot_histogram(df, matched_x_column, title, output_path)

    if plot_error:
        print(plot_error)
        return {
            "status": "error",
            "output_file": None,
            "message": plot_error,
        }

    message = f"Chart created successfully: {output_path}"
    print(message)
    return {
        "status": "success",
        "output_file": output_path,
        "message": message,
        "result_summary": "Chart created successfully.",
        "chart_type": chart_type,
        "x_column": str(matched_x_column),
        "y_column": str(matched_y_column) if matched_y_column else None,
        "title": title,
    }


def _default_title(chart_type, x_column, y_column=None):
    if chart_type == "histogram":
        return f"{x_column} Distribution"
    if chart_type == "pie":
        return f"{x_column} Distribution"
    return f"{y_column} by {x_column}"
