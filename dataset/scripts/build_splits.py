import pandas as pd
import json
import hashlib
import os
import random
import sys

sys.stdout.reconfigure(encoding='utf-8')

HIGH = ["CWE-89", "CWE-78", "CWE-79", "CWE-502", "CWE-798", "CWE-94"]

def norm(code):
    return "".join(str(code).split()) if isinstance(code, str) else ""

def h(code):
    return hashlib.sha256(norm(code).encode("utf-8")).hexdigest()

def severity(cwe):
    return "Alta" if any(c in str(cwe) for c in HIGH) else "Media"

def transform(row):
    vuln = bool(row["is_vulnerable"])
    cwe = row["cwe_id"] if vuln and row["cwe_id"] else "Ninguno"
    fixed = row.get("code_fixed")
    fixed = fixed if isinstance(fixed, str) and fixed.strip() else None
    target = {
        "finding_id": row["h"][:16],
        "veredicto": "VULNERABLE" if vuln else "SAFE",
        "cwe": cwe,
        "severidad": severity(cwe) if vuln else "Info",
        "explicacion": (
            f"Se detecta un patrón asociado a {cwe} en código {row['language']}."
            if vuln else
            f"El fragmento de código {row['language']} no presenta el patrón vulnerable indicado."
        ),
        "vector_ataque": f"Explotación mediante vectores propios de {cwe}." if vuln else "N/A",
        "correccion": fixed or ("Aplicar validación de entradas y sanitización." if vuln else "N/A"),
    }
    prompt = (
        f"Analiza el siguiente fragmento de código en {row['language']}.\n\n"
        f"<code_snippet>\n{row['code']}\n</code_snippet>\n"
    )
    return {
        "prompt": prompt,
        "target": json.dumps(target, ensure_ascii=False),
        "meta": {"language": row["language"], "source": row["source"],
                 "cwe": cwe, "is_vulnerable": vuln, "hash": row["h"]},
    }

def main():
    stats = {}
    frames = {}
    for sp in ["train", "validation", "test"]:
        df = pd.read_parquet(f"dataset/data/{sp}-00000-of-00001.parquet")
        df["h"] = df["code"].map(h)
        frames[sp] = df
        stats[f"{sp}_rows"] = int(len(df))

    tr, va, te = frames["train"], frames["validation"], frames["test"]
    h_tr, h_va, h_te = set(tr["h"]), set(va["h"]), set(te["h"])

    stats["hashes_train_vs_test"] = len(h_tr & h_te)
    stats["hashes_train_vs_val"] = len(h_tr & h_va)
    stats["hashes_val_vs_test"] = len(h_va & h_te)

    tr = tr[~tr["h"].isin(h_te | h_va)].copy()
    va = va[~va["h"].isin(h_te)].copy()

    corpus = pd.concat([tr[["h", "is_vulnerable"]], va[["h", "is_vulnerable"]], te[["h", "is_vulnerable"]]])
    conflicts = corpus.groupby("h")["is_vulnerable"].nunique()
    bad = set(conflicts[conflicts > 1].index)
    stats["hashes_etiqueta_contradictoria"] = len(bad)
    tr = tr[~tr["h"].isin(bad)].copy()
    va = va[~va["h"].isin(bad)].copy()

    tr = tr.drop_duplicates(subset=["h"])
    va = va.drop_duplicates(subset=["h"])

    random.seed(42)
    idx = list(tr.index)
    random.shuffle(idx)
    cut = int(len(idx) * 0.80)
    tr_80 = tr.loc[idx[:cut]]
    tr_20 = tr.loc[idx[cut:]]
    va_final = pd.concat([tr_20, va])

    stats.update({
        "train_despues_filtro": int(len(tr)),
        "train_80": int(len(tr_80)),
        "val_20": int(len(tr_20)),
        "validacion_original_limpia": int(len(va)),
        "validacion_total": int(len(va_final)),
        "test_intacto": int(len(te)),
        "vuln_train_80": int(tr_80["is_vulnerable"].sum()),
        "vuln_val_total": int(va_final["is_vulnerable"].sum()),
        "lenguajes_train_80": {k: int(v) for k, v in tr_80["language"].value_counts().items()},
    })

    os.makedirs("dataset/splits", exist_ok=True)
    for name, frame in [("train_80", tr_80), ("val_20", tr_20), ("val_total", va_final)]:
        path = f"dataset/splits/{name}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for _, row in frame.iterrows():
                f.write(json.dumps(transform(row), ensure_ascii=False) + "\n")
        print(f"{name}: {len(frame)} registros -> {path}")

    with open("dataset/splits/stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(json.dumps(stats, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
