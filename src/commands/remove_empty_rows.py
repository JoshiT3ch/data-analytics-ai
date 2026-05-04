import os

import pandas as pd


def _get_output_path(file_path):
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    os.makedirs("outputs", exist_ok=True)
    return f"outputs/{file_name}_no_empty.xlsx"


def _remove_empty_rows(df):
    return df.dropna(how="all")


def remove_empty_rows(file_path):
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
        cleaned_df = _remove_empty_rows(df)
        removed_rows = len(df) - len(cleaned_df)
        output_path = _get_output_path(file_path)

        cleaned_df.to_excel(output_path, index=False)

        print(f"Original rows: {len(df)}")
        print(f"Rows after removing empty rows: {len(cleaned_df)}")
        message = f"Done. Removed {removed_rows} empty rows. Output saved to {output_path}"
        print(message)
        return {
            "status": "success",
            "output_file": output_path,
            "message": message,
            "result_summary": f"Removed {removed_rows} empty rows.",
            "original_rows": len(df),
            "cleaned_rows": len(cleaned_df),
            "removed_rows": removed_rows,
            "affected_rows": removed_rows,
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
