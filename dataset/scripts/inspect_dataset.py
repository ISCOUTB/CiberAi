import pandas as pd
import os

for split in ['train', 'validation', 'test']:
    path = f'dataset/data/{split}-00000-of-00001.parquet'
    if os.path.exists(path):
        df = pd.read_parquet(path)
        print(f"=== SPLIT: {split} ===")
        print(f"Total rows: {len(df)}")
        print("Columns:", df.columns.tolist())
        if 'language' in df.columns:
            print("Languages:\n", df['language'].value_counts())
        if 'is_vulnerable' in df.columns:
            print("Vulnerable distribution:\n", df['is_vulnerable'].value_counts())
        print("-" * 40)
