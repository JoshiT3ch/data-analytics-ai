from pathlib import Path

import pandas as pd


def _get_output_path(file_path):
    source = Path(file_path)
    Path("outputs").mkdir(parents=True, exist_ok=True)
    return (Path("outputs") / f"{source.stem}_cleaned{source.suffix}").as_posix()


def clean_duplicates(file_path, preview=False):
    try:
        source = Path(file_path)
        if not source.exists():
            message = f"File not found: {file_path}"
            print(message)
            return {
                "status": "error",
                "output_file": None,
                "message": message,
            }

        df = pd.read_excel(file_path)
        original_rows = len(df)
        duplicate_rows = int(df.duplicated().sum())
        df_cleaned = df.drop_duplicates()
        cleaned_rows = len(df_cleaned)

        if preview:
            message = f"Preview only. Found {duplicate_rows} duplicate rows. No changes were applied."
            print("Preview only:")
            print("- Command: clean-duplicates")
            print(f"- File: {file_path}")
            print(f"- Duplicate rows found: {duplicate_rows}")
            print("- No changes were applied.")
            return {
                "status": "success",
                "output_file": None,
                "message": message,
                "result_summary": message,
                "preview": True,
                "original_rows": original_rows,
                "cleaned_rows": cleaned_rows,
                "duplicate_rows": duplicate_rows,
                "affected_rows": duplicate_rows,
            }

        output_path = _get_output_path(file_path)
        df_cleaned.to_excel(output_path, index=False)

        message = f"Done. Removed {duplicate_rows} duplicate rows. Output saved to {output_path}"
        print(message)
        return {
            "status": "success",
            "output_file": output_path,
            "message": message,
            "result_summary": f"Removed {duplicate_rows} duplicate rows.",
            "original_rows": original_rows,
            "cleaned_rows": cleaned_rows,
            "duplicate_rows": duplicate_rows,
            "affected_rows": duplicate_rows,
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
