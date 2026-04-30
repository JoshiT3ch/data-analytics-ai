import os

import pandas as pd


def _infer_column_types(df):
    return [(column, str(dtype)) for column, dtype in df.dtypes.items()]


def detect_columns(file_path):
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
        columns = _infer_column_types(df)

        print("Columns and inferred data types:")
        for column, dtype in columns:
            print(f"{column}: {dtype}")

        return {
            "status": "success",
            "output_file": None,
            "message": "Detected columns.",
            "columns": columns,
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
