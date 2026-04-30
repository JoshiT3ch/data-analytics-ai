import os

import pandas as pd


def _infer_column_types(df):
    return [(column, str(dtype)) for column, dtype in df.dtypes.items()]


def detect_columns(file_path):
    try:
        if not os.path.exists(file_path):
            print("File not found")
            return

        df = pd.read_excel(file_path)

        print("Columns and inferred data types:")
        for column, dtype in _infer_column_types(df):
            print(f"{column}: {dtype}")

    except ValueError as error:
        print(f"Invalid file: {error}")
    except Exception as error:
        print(f"Error: {error}")
