"""Descarga el dataset de HuggingFace en formato parquet.

Requisito:
    pip install datasets

Uso:
    python dataset/scripts/download_dataset.py
"""

from pathlib import Path

from datasets import load_dataset

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "dataset" / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    ds = load_dataset("ayshajavd/code-security-vulnerability-dataset")
    for split in ["train", "validation", "test"]:
        if split in ds:
            out = OUT_DIR / f"{split}-00000-of-00001.parquet"
            ds[split].to_parquet(str(out))
            print(f"guardado: {out} ({len(ds[split])} filas)")
    print("Listo. Ahora puedes ejecutar dataset/scripts/build_splits.py")


if __name__ == "__main__":
    main()
