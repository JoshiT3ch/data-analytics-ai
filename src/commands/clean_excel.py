import os

import pandas as pd


def clean_duplicates(file_path):
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

        print(f"Original rows: {len(df)}")

        df_cleaned = df.drop_duplicates()

        print(f"Cleaned rows: {len(df_cleaned)}")

        filename = os.path.basename(file_path)
        name, ext = os.path.splitext(filename)

        os.makedirs("outputs", exist_ok=True)
        output_path = f"outputs/{name}_cleaned{ext}"
        df_cleaned.to_excel(output_path, index=False)

        message = f"Saved to: {output_path}"
        print(message)
        return {
            "status": "success",
            "output_file": output_path,
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
