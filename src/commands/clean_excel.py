import pandas as pd
import os

def clean_duplicates(file_path):
    try:
        if not os.path.exists(file_path):
            print("❌ File not found")
            return

        df = pd.read_excel(file_path)

        print(f"📊 Original rows: {len(df)}")

        df_cleaned = df.drop_duplicates()

        print(f"✅ Cleaned rows: {len(df_cleaned)}")

        # 👇 Dynamic output name
        filename = os.path.basename(file_path)
        name, ext = os.path.splitext(filename)

        output_path = f"outputs/{name}_cleaned{ext}"
        df_cleaned.to_excel(output_path, index=False)

        print(f"💾 Saved to: {output_path}")

    except Exception as e:
        print(f"❌ Error: {e}")