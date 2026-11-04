import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
FILES = ["train_80.jsonl", "val_20.jsonl", "val_total.jsonl"]
MARK = "<code_snippet>"


def clean_prompt(prompt, language):
    idx = prompt.find(MARK)
    if idx == -1:
        return prompt
    return "Analiza el siguiente fragmento de código en {}.\n\n{}".format(language, prompt[idx:])


for name in FILES:
    path = ROOT / "splits" / name
    tmp = path.with_suffix(".tmp")
    changed = 0
    total = 0
    with path.open(encoding="utf-8") as src, tmp.open("w", encoding="utf-8", newline="\n") as dst:
        for line in src:
            if not line.strip():
                continue
            row = json.loads(line)
            total += 1
            new = clean_prompt(row["prompt"], row["meta"]["language"])
            if new != row["prompt"]:
                changed += 1
                row["prompt"] = new
            dst.write(json.dumps(row, ensure_ascii=False) + "\n")
    os.replace(tmp, path)
    print("{}: {} registros, {} prompts corregidos".format(name, total, changed))
