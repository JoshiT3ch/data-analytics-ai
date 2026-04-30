import os

import pandas as pd


def _get_output_path(file_path):
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    os.makedirs("outputs", exist_ok=True)
    return os.path.join("outputs", f"{file_name}_summary.txt")


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


def summarize(file_path):
    try:
        if not os.path.exists(file_path):
            print("File not found")
            return

        df = pd.read_excel(file_path)
        summary = _build_summary(df)
        output_path = _get_output_path(file_path)

        with open(output_path, "w", encoding="utf-8") as output_file:
            output_file.write(summary)

        print(summary)
        print(f"Saved to: {output_path}")

    except ValueError as error:
        print(f"Invalid file: {error}")
    except Exception as error:
        print(f"Error: {error}")
