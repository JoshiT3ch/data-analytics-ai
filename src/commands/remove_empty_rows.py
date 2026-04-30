import os

import pandas as pd


def _get_output_path(file_path):
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    os.makedirs("outputs", exist_ok=True)
    return os.path.join("outputs", f"{file_name}_no_empty.xlsx")


def _remove_empty_rows(df):
    return df.dropna(how="all")


def remove_empty_rows(file_path):
    try:
        if not os.path.exists(file_path):
            print("File not found")
            return

        df = pd.read_excel(file_path)
        cleaned_df = _remove_empty_rows(df)
        output_path = _get_output_path(file_path)

        cleaned_df.to_excel(output_path, index=False)

        print(f"Original rows: {len(df)}")
        print(f"Rows after removing empty rows: {len(cleaned_df)}")
        print(f"Saved to: {output_path}")

    except ValueError as error:
        print(f"Invalid file: {error}")
    except Exception as error:
        print(f"Error: {error}")
