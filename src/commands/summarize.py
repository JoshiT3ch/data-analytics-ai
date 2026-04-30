import os

import pandas as pd


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


def summarize(file_path):
    try:
        if not os.path.exists(file_path):
            message = "File not found"
            print(message)
            return {
                "status": "error",
                "output_file": None,
                "message": message,
            }

        df = pd.read_excel(file_path)
        summary = _build_summary(df)
        output_path = _get_output_path(file_path)

        with open(output_path, "w", encoding="utf-8") as output_file:
            output_file.write(summary)

        print(summary)
        message = f"Saved to: {output_path}"
        print(message)
        return {
            "status": "success",
            "output_file": output_path,
            "message": message,
            "summary": summary,
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
