---
license: apache-2.0
task_categories:
- text-classification
language:
- en
- code
tags:
- security
- vulnerability-detection
- cwe
- owasp
- code-analysis
- multi-label-classification
size_categories:
- 100K<n<1M
pretty_name: Code Security Vulnerability Dataset
---

# Code Security Vulnerability Dataset

A curated multi-language dataset of **175,419 code samples** labeled with **31 vulnerability classes** (30 CWEs + safe) for training multi-label code vulnerability detection models. Labels are mapped to OWASP Top 10 2021 categories.

## Dataset Details

| Property | Value |
|----------|-------|
| **Total Samples** | 175,419 |
| **Train / Val / Test** | 140,335 / 17,542 / 17,542 |
| **Languages** | C, C++, Python, JavaScript, Java, PHP, Go |
| **Labels** | 31 (multi-label) |
| **Format** | Parquet with binary label vectors |

## Columns

| Column | Type | Description |
|--------|------|-------------|
| `code` | string | Source code snippet |
| `code_fixed` | string | Secure version (when available) |
| `cwe_id` | string | Primary CWE identifier |
| `owasp` | string | OWASP Top 10 2021 category |
| `language` | string | Programming language |
| `source` | string | Source dataset |
| `is_vulnerable` | bool | Whether the code contains a vulnerability |
| `labels` | list[int] | 31-dim binary vector (multi-label) |

## Label Index

| Index | Label | OWASP |
|-------|-------|-------|
| 0 | safe | — |
| 1 | CWE-20 (Input Validation) | A03 |
| 2 | CWE-22 (Path Traversal) | A01 |
| 3 | CWE-78 (Command Injection) | A03 |
| 4 | CWE-79 (XSS) | A03 |
| 5 | CWE-89 (SQL Injection) | A03 |
| 6 | CWE-94 (Code Injection) | A03 |
| 7 | CWE-119 (Buffer Overflow) | A03 |
| 8 | CWE-125 (Out-of-bounds Read) | A03 |
| 9 | CWE-190 (Integer Overflow) | A03 |
| 10 | CWE-200 (Info Exposure) | A01 |
| 11 | CWE-264 (Permissions) | A01 |
| 12 | CWE-269 (Privilege Mgmt) | A01 |
| 13 | CWE-276 (Default Perms) | A01 |
| 14 | CWE-284 (Access Control) | A01 |
| 15 | CWE-287 (Authentication) | A07 |
| 16 | CWE-310 (Crypto Issues) | A02 |
| 17 | CWE-327 (Broken Crypto) | A02 |
| 18 | CWE-330 (Weak Random) | A02 |
| 19 | CWE-352 (CSRF) | A01 |
| 20 | CWE-362 (Race Condition) | A04 |
| 21 | CWE-399 (Resource Mgmt) | A04 |
| 22 | CWE-401 (Memory Leak) | A03 |
| 23 | CWE-416 (Use After Free) | A03 |
| 24 | CWE-434 (File Upload) | A04 |
| 25 | CWE-476 (NULL Deref) | A03 |
| 26 | CWE-502 (Deserialization) | A08 |
| 27 | CWE-601 (Open Redirect) | A01 |
| 28 | CWE-787 (OOB Write) | A03 |
| 29 | CWE-798 (Hardcoded Creds) | A07 |
| 30 | CWE-918 (SSRF) | A10 |

## Source Datasets

1. **[BigVul](https://huggingface.co/datasets/bstee615/bigvul)** — 265K C/C++ functions from real CVE commits
2. **[CWE-enriched BigVul/PrimeVul](https://huggingface.co/datasets/mahdin70/cwe_enriched_balanced_bigvul_primevul)** — Balanced CWE-labeled subset
3. **[Code Vulnerability Labeled](https://huggingface.co/datasets/lemon42-ai/Code_Vulnerability_Labeled_Dataset)** — Multi-language (Python, JS, Java, PHP, Go)
4. **[CyberNative DPO](https://huggingface.co/datasets/CyberNative/Code_Vulnerability_Security_DPO)** — Vulnerable/secure code pairs

## Usage

```python
from datasets import load_dataset

ds = load_dataset("ayshajavd/code-security-vulnerability-dataset")
print(ds)
# DatasetDict({
#     train: Dataset({features: [...], num_rows: 140335}),
#     validation: Dataset({features: [...], num_rows: 17542}),
#     test: Dataset({features: [...], num_rows: 17542})
# })

# Example: get vulnerable samples
vuln = ds["train"].filter(lambda x: x["is_vulnerable"])
```

## Models Trained on This Dataset

- [graphcodebert-vuln-classifier](https://huggingface.co/ayshajavd/graphcodebert-vuln-classifier) — Multi-label vulnerability detection
- [codet5p-vuln-fixer](https://huggingface.co/ayshajavd/codet5p-vuln-fixer) — Secure code fix generation

## Demo

Try the [Code Security Analyzer](https://huggingface.co/spaces/ayshajavd/code-security-analyzer) Space for an interactive demo.
