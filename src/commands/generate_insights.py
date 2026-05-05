from pathlib import Path
import re

import pandas as pd

from src.core.session_memory import load_session_memory
from src.core.workbook_manager import WorkbookError, read_sheet, resolve_sheet_name


INSIGHTS_OUTPUT_DIR = Path("outputs") / "insights"

MONTH_ORDER = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

METRIC_CANDIDATES = (
    "Revenue",
    "Sales",
    "Amount",
    "Total",
    "Profit",
    "Income",
    "Value",
)


def _output_path(file_path):
    source = Path(file_path)
    INSIGHTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return (INSIGHTS_OUTPUT_DIR / f"{source.stem}_insights.txt").as_posix()


def _current_session_file():
    current_file = load_session_memory().get("current_file")
    if isinstance(current_file, str) and current_file.lower().endswith(".xlsx"):
        return current_file
    return None


def _current_session_sheet():
    current_sheet = load_session_memory().get("current_sheet")
    if isinstance(current_sheet, str) and current_sheet:
        return current_sheet
    return None


def _normalize_name(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _match_column(df, requested_column):
    if not requested_column:
        return None

    requested = _normalize_name(requested_column)
    for column in df.columns:
        if _normalize_name(column) == requested:
            return column

    return None


def _find_column(df, candidates):
    for candidate in candidates:
        column = _match_column(df, candidate)
        if column is not None:
            return column
    return None


def _numeric_columns(df):
    return list(df.select_dtypes(include="number").columns)


def _categorical_columns(df):
    numeric = set(_numeric_columns(df))
    return [
        column
        for column in df.columns
        if column not in numeric and not pd.api.types.is_datetime64_any_dtype(df[column])
    ]


def _format_value(value):
    if pd.isna(value):
        return "n/a"

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return str(value)

    if numeric_value.is_integer():
        return str(int(numeric_value))

    return f"{numeric_value:.2f}"


def _join_columns(columns):
    columns = list(columns)
    if not columns:
        return "None"
    return ", ".join(str(column) for column in columns)


def _safe_column_label(column):
    return str(column)


def _build_overview(df, file_path, numeric_columns, categorical_columns, missing_counts, duplicate_rows):
    lines = [
        "Dataset Overview",
        "----------------",
        f"File name: {Path(file_path).name}",
        f"Row count: {len(df)}",
        f"Column count: {len(df.columns)}",
        f"Column names: {_join_columns(df.columns)}",
        f"Numeric columns: {_join_columns(numeric_columns)}",
        f"Categorical columns: {_join_columns(categorical_columns)}",
        "Missing values by column:",
    ]

    for column, count in missing_counts.items():
        lines.append(f"- {_safe_column_label(column)}: {int(count)}")

    lines.append(f"Duplicate rows: {duplicate_rows}")
    return lines


def _build_statistics(df, numeric_columns, categorical_columns):
    lines = [
        "",
        "Basic Statistics",
        "----------------",
    ]

    if numeric_columns:
        lines.append("Numeric columns:")
        for column in numeric_columns:
            series = pd.to_numeric(df[column], errors="coerce").dropna()
            if series.empty:
                lines.append(f"- {column}: no numeric values")
                continue

            lines.append(
                "- {column}: mean {mean}, min {min}, max {max}, total {total}".format(
                    column=column,
                    mean=_format_value(series.mean()),
                    min=_format_value(series.min()),
                    max=_format_value(series.max()),
                    total=_format_value(series.sum()),
                )
            )
    else:
        lines.append("No numeric columns found.")

    lines.append("")
    if categorical_columns:
        lines.append("Top categorical values:")
        for column in categorical_columns:
            counts = df[column].dropna().value_counts().head(3)
            if counts.empty:
                lines.append(f"- {column}: no values")
                continue

            top_values = ", ".join(
                f"{value} ({int(count)})" for value, count in counts.items()
            )
            lines.append(f"- {column}: {top_values}")
    else:
        lines.append("No categorical columns found.")

    return lines


def _metric_column(df, target_column=None, preferred=None):
    numeric = set(_numeric_columns(df))

    requested = _match_column(df, target_column)
    if requested in numeric:
        return requested

    for candidate in preferred or ():
        matched = _match_column(df, candidate)
        if matched in numeric:
            return matched

    for candidate in METRIC_CANDIDATES:
        matched = _match_column(df, candidate)
        if matched in numeric:
            return matched

    return next(iter(numeric), None)


def _top_group_finding(df, group_column, metric_column, label):
    if group_column is None or metric_column is None:
        return None

    grouped = (
        df[[group_column, metric_column]]
        .dropna(subset=[group_column])
        .assign(**{metric_column: pd.to_numeric(df[metric_column], errors="coerce")})
        .dropna(subset=[metric_column])
        .groupby(group_column, dropna=False)[metric_column]
        .sum()
    )

    if grouped.empty:
        return None

    top_name = grouped.idxmax()
    metric_name = str(metric_column).lower()
    return f"{top_name} recorded the highest total {metric_name} by {label}."


def _month_sort_key(value):
    text = str(value).strip().lower()
    if text in MONTH_ORDER:
        return (0, MONTH_ORDER[text])

    parsed = pd.to_datetime(value, errors="coerce")
    if not pd.isna(parsed):
        return (1, parsed)

    return (2, text)


def _month_label(value):
    parsed = pd.to_datetime(value, errors="coerce")
    if not pd.isna(parsed) and not isinstance(value, str):
        return parsed.strftime("%Y-%m-%d")
    return str(value)


def _monthly_series(df, month_column, metric_column):
    if month_column is None or metric_column is None:
        return None

    trend_df = df[[month_column, metric_column]].copy()
    trend_df[metric_column] = pd.to_numeric(trend_df[metric_column], errors="coerce")
    trend_df = trend_df.dropna(subset=[month_column, metric_column])
    if trend_df.empty:
        return None

    grouped = trend_df.groupby(month_column, sort=False, dropna=False)[metric_column].sum()
    sorted_items = sorted(grouped.items(), key=lambda item: _month_sort_key(item[0]))
    return pd.Series(
        [value for _, value in sorted_items],
        index=[label for label, _ in sorted_items],
    )


def _trend_finding(series, metric_column):
    if series is None or len(series) < 2:
        return None

    first_label = _month_label(series.index[0])
    last_label = _month_label(series.index[-1])
    first_value = series.iloc[0]
    last_value = series.iloc[-1]
    metric_name = str(metric_column)

    differences = series.diff().dropna()
    if (differences >= 0).all() and last_value > first_value:
        return (
            f"{metric_name} increased from {first_label} to {last_label}, "
            f"rising from {_format_value(first_value)} to {_format_value(last_value)}."
        )

    if (differences <= 0).all() and last_value < first_value:
        return (
            f"{metric_name} decreased from {first_label} to {last_label}, "
            f"falling from {_format_value(first_value)} to {_format_value(last_value)}."
        )

    return f"{metric_name} showed a mixed trend from {first_label} to {last_label}."


def _month_extreme_findings(series, metric_column):
    if series is None or series.empty:
        return []

    metric_name = str(metric_column).lower()
    highest_month = series.idxmax()
    lowest_month = series.idxmin()

    return [
        (
            f"{_month_label(highest_month)} had the highest total {metric_name} "
            f"({_format_value(series.max())})."
        ),
        (
            f"{_month_label(lowest_month)} had the lowest total {metric_name} "
            f"({_format_value(series.min())})."
        ),
    ]


def _build_findings(df, file_path, target_column=None, group_by=None):
    missing_counts = df.isna().sum()
    duplicate_rows = int(df.duplicated().sum())
    findings = [
        f"Dataset contains {len(df)} rows and {len(df.columns)} columns.",
    ]

    category_column = _match_column(df, group_by) or _find_column(df, ("Category",))
    sales_metric = _metric_column(df, target_column=target_column, preferred=("Sales",))
    revenue_metric = _metric_column(df, target_column=target_column, preferred=("Revenue",))

    category_metric = sales_metric or revenue_metric
    category_finding = _top_group_finding(
        df,
        category_column,
        category_metric,
        str(category_column).lower() if category_column is not None else "category",
    )
    if category_finding:
        findings.append(category_finding)

    product_column = _find_column(df, ("Product", "Item", "SKU"))
    product_metric = sales_metric or revenue_metric
    product_finding = _top_group_finding(df, product_column, product_metric, "product")
    if product_finding:
        findings.append(product_finding)

    month_column = _find_column(df, ("Month", "Date", "Order Date", "Transaction Date"))
    trend_metric = revenue_metric or sales_metric or _metric_column(df, target_column)
    month_series = _monthly_series(df, month_column, trend_metric)
    findings.extend(_month_extreme_findings(month_series, trend_metric))

    trend_finding = _trend_finding(month_series, trend_metric)
    if trend_finding:
        findings.append(trend_finding)

    missing_total = int(missing_counts.sum())
    if missing_total:
        affected_columns = [
            str(column)
            for column, count in missing_counts.items()
            if int(count) > 0
        ]
        findings.append(
            "Missing values were found in: " + ", ".join(affected_columns) + "."
        )
    else:
        findings.append("No major missing value issue was detected.")

    if duplicate_rows:
        findings.append(f"{duplicate_rows} duplicate rows were detected.")
    else:
        findings.append("No duplicate rows were detected.")

    return findings


def _build_recommendations(findings, row_count, has_missing_values, duplicate_rows):
    recommendations = []
    findings_text = " ".join(findings).lower()

    if "highest total sales" in findings_text or "highest total revenue" in findings_text:
        recommendations.append("Prioritize high-performing categories and products.")

    if "increased from" in findings_text:
        recommendations.append("Continue tracking monthly revenue trends.")
    elif "decreased from" in findings_text:
        recommendations.append("Investigate what changed during the declining period.")
    elif "mixed trend" in findings_text:
        recommendations.append("Review month-to-month drivers behind the mixed trend.")

    if has_missing_values:
        recommendations.append("Clean or impute missing values before deeper analysis.")
    else:
        recommendations.append("No major missing value issue was detected.")

    if duplicate_rows:
        recommendations.append("Remove duplicate rows before using this dataset for reporting.")

    if row_count < 30:
        recommendations.append("Use a larger dataset for stronger conclusions.")

    if not recommendations:
        recommendations.append("Keep collecting consistent data and monitor changes over time.")

    return recommendations


def _build_report(df, file_path, target_column=None, group_by=None):
    numeric_columns = _numeric_columns(df)
    categorical_columns = _categorical_columns(df)
    missing_counts = df.isna().sum()
    duplicate_rows = int(df.duplicated().sum())
    findings = _build_findings(
        df,
        file_path,
        target_column=target_column,
        group_by=group_by,
    )
    recommendations = _build_recommendations(
        findings,
        len(df),
        bool(missing_counts.sum()),
        duplicate_rows,
    )

    lines = [
        "Smart Data Insight Report",
        "=========================",
        "",
    ]
    lines.extend(
        _build_overview(
            df,
            file_path,
            numeric_columns,
            categorical_columns,
            missing_counts,
            duplicate_rows,
        )
    )
    lines.extend(_build_statistics(df, numeric_columns, categorical_columns))
    lines.extend(["", "Key Findings", "------------"])
    lines.extend(f"- {finding}" for finding in findings)
    lines.extend(["", "Recommendations", "---------------"])
    lines.extend(f"- {recommendation}" for recommendation in recommendations)

    return "\n".join(lines), findings, recommendations


def generate_insights(file_path, target_column=None, group_by=None, sheet_name=None):
    """Generate a rule-based data insight report from an Excel file."""
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
        resolved_sheet = resolve_sheet_name(
            file_path,
            requested_sheet=sheet_name,
            session_sheet=_current_session_sheet(),
        )
        df = read_sheet(source, resolved_sheet)
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
        message = f"Error reading file: {error}"
        print(message)
        return {
            "status": "error",
            "output_file": None,
            "message": message,
        }

    report, findings, recommendations = _build_report(
        df,
        file_path,
        target_column=target_column,
        group_by=group_by,
    )
    output_path = _output_path(file_path)

    with open(output_path, "w", encoding="utf-8") as output_file:
        output_file.write(report)

    message = f"Insights generated successfully: {output_path}"
    print(message)
    print(f"Sheet used: {resolved_sheet}")
    print("")
    print("Key Findings:")
    for finding in findings[:5]:
        print(f"- {finding}")
    print("")
    print("Recommendations:")
    for recommendation in recommendations[:5]:
        print(f"- {recommendation}")

    return {
        "status": "success",
        "output_file": output_path,
        "message": message,
        "result_summary": "Insights generated successfully.",
        "key_findings": findings,
        "recommendations": recommendations,
        "sheet_name": resolved_sheet,
    }
