"""Fusiona el adaptador LoRA, convierte a GGUF y cuantiza a Q4_K_M.

El conversor oficial vive en el repositorio de llama.cpp
(``convert_hf_to_gguf.py``) y solo genera tipos de 16/32 bits o q8_0; los
K-quants como Q4_K_M se producen despues con ``llama-quantize``.

Este script hace el flujo completo:

1. fusiona el adaptador LoRA con el modelo base;
2. convierte el modelo fusionado a GGUF f16 con el conversor oficial;
3. descarga (si hace falta) un binario de ``llama-quantize`` para Windows;
4. cuantiza el GGUF f16 a Q4_K_M.

Uso:
    python training/export_gguf.py `
        --adapter training/out/qwen-coder-1.5b-lora `
        --out training/out/qwen-coder-1.5b-merged `
        --gguf-out training/out/gguf/qwen-coder-1.5b-q4_k_m.gguf

Antes hay que tener el repositorio de llama.cpp. Si no existe en
``training/llama.cpp``, clonar la version fijada:

    git clone --depth 1 --branch v0.8.0 https://github.com/ggml-org/llama.cpp training/llama.cpp

Despues de exportar, registrar el modelo en Ollama desde la raiz del proyecto:

    # Modelfile
    FROM ./training/out/gguf/qwen-coder-1.5b-q4_k_m.gguf

    ollama create qwen2.5-coder-triage -f Modelfile
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
LLAMA_CPP_REPO = "https://github.com/ggml-org/llama.cpp"
USER_AGENT = "proyecto-ing-export"


def merge(base_model: str, adapter_path: str, out_dir: str) -> Path:
    print("cargando modelo base:", base_model)
    model = AutoModelForCausalLM.from_pretrained(
        base_model, torch_dtype="auto", trust_remote_code=True
    )
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    print("fusionando adaptador:", adapter_path)
    model = PeftModel.from_pretrained(model, adapter_path)
    model = model.merge_and_unload()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(out), safe_serialization=True)
    tokenizer.save_pretrained(str(out))
    print("modelo fusionado guardado en:", out)
    return out


def find_converter(llama_cpp: Path) -> Path:
    candidates = [
        llama_cpp / "convert_hf_to_gguf.py",
        llama_cpp / "convert-hf-to-gguf.py",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "No se encontro convert_hf_to_gguf.py en {}. Clona llama.cpp:\n"
        "  git clone --depth 1 --branch v0.8.0 {} {}".format(
            llama_cpp, LLAMA_CPP_REPO, llama_cpp
        )
    )


def _http_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_download(url: str, dest: Path) -> None:
    print("descargando:", url)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=300) as resp, dest.open("wb") as fh:
        shutil.copyfileobj(resp, fh)


def download_quantize_bin(dest_dir: Path) -> Path:
    """Descarga el binario de llama-quantize para Windows x64."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    latest = _http_json(
        "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest"
    )
    tag = None
    for asset in latest.get("assets", []):
        if asset.get("name") == "nightly-tag.txt":
            req = urllib.request.Request(
                asset["browser_download_url"], headers={"User-Agent": USER_AGENT}
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                tag = resp.read().decode("utf-8").strip()
            break
    if not tag:
        tag = latest.get("tag_name")
    if not tag:
        raise RuntimeError("No se pudo determinar la ultima version de llama.cpp")

    release = _http_json(
        "https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/{}".format(tag)
    )
    asset = None
    for candidate in release.get("assets", []):
        if candidate.get("name", "").endswith("-bin-win-cpu-x64.zip"):
            asset = candidate
            break
    if asset is None:
        raise RuntimeError(
            "No se encontro un binario win-cpu-x64 para llama.cpp {}. "
            "Descargalo desde https://github.com/ggml-org/llama.cpp/releases "
            "y pasa --quantize-bin.".format(tag)
        )

    zip_path = dest_dir / asset["name"]
    _http_download(asset["browser_download_url"], zip_path)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest_dir)
    zip_path.unlink()

    for candidate in dest_dir.rglob("llama-quantize.exe"):
        print("llama-quantize:", candidate)
        return candidate
    raise RuntimeError("El ZIP no contiene llama-quantize.exe")


def find_quantize_bin(explicit: str, dest_dir: Path) -> Path:
    if explicit:
        path = Path(explicit)
        if not path.exists():
            raise FileNotFoundError("No existe --quantize-bin: {}".format(path))
        return path

    env_path = os.environ.get("LLAMA_QUANTIZE")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    on_path = shutil.which("llama-quantize")
    if on_path:
        return Path(on_path)

    for candidate in dest_dir.rglob("llama-quantize.exe"):
        return candidate

    if os.name != "nt":
        raise FileNotFoundError(
            "No se encontro llama-quantize. Compila llama.cpp o pasa "
            "--quantize-bin /ruta/a/llama-quantize."
        )
    return download_quantize_bin(dest_dir)


def convert(merged: Path, gguf_out: Path, converter: Path) -> None:
    gguf_out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(converter),
        str(merged),
        "--outfile",
        str(gguf_out),
        "--outtype",
        "f16",
    ]
    print("convirtiendo a GGUF f16:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    if not gguf_out.exists():
        raise RuntimeError("El conversor no genero el archivo: {}".format(gguf_out))


def quantize(f16_gguf: Path, gguf_out: Path, quant_type: str, quantize_bin: Path) -> None:
    quantize_bin = quantize_bin.resolve()
    f16_gguf = f16_gguf.resolve()
    gguf_out = gguf_out.resolve()
    cmd = [str(quantize_bin), str(f16_gguf), str(gguf_out), quant_type]
    print("cuantizando a {}:".format(quant_type), " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=str(quantize_bin.parent))
    if not gguf_out.exists():
        raise RuntimeError("llama-quantize no genero el archivo: {}".format(gguf_out))
    size_mb = gguf_out.stat().st_size / (1024 * 1024)
    print("GGUF guardado en: {} ({:.1f} MB)".format(gguf_out, size_mb))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="Qwen/Qwen2.5-Coder-1.5B-Instruct")
    ap.add_argument("--adapter", default="training/out/qwen-coder-1.5b-lora")
    ap.add_argument("--out", default="training/out/qwen-coder-1.5b-merged")
    ap.add_argument(
        "--gguf-out",
        default="training/out/gguf/qwen-coder-1.5b-q4_k_m.gguf",
        help="Ruta completa del archivo .gguf final.",
    )
    ap.add_argument(
        "--f16-out",
        default="training/out/gguf/qwen-coder-1.5b-f16.gguf",
        help="GGUF intermedio sin cuantizar.",
    )
    ap.add_argument("--quant", default="Q4_K_M", help="Tipo de cuantizacion final.")
    ap.add_argument(
        "--llama-cpp",
        default="training/llama.cpp",
        help="Directorio del repositorio de llama.cpp con convert_hf_to_gguf.py.",
    )
    ap.add_argument(
        "--quantize-bin",
        default="",
        help="Ruta a llama-quantize.exe. Si se omite, se busca o se descarga.",
    )
    ap.add_argument(
        "--tools-dir",
        default="training/llama-bin",
        help="Directorio donde descargar el binario de llama-quantize.",
    )
    args = ap.parse_args()

    adapter = Path(args.adapter)
    if not adapter.exists():
        raise FileNotFoundError(
            "No existe el adaptador {}. Entrena primero con training/train_qlora.py".format(
                adapter
            )
        )

    converter = find_converter(Path(args.llama_cpp))
    f16_gguf = Path(args.f16_out)
    gguf_out = Path(args.gguf_out)

    merged = merge(args.base, str(adapter), args.out)
    convert(merged, f16_gguf, converter)

    quantize_bin = find_quantize_bin(args.quantize_bin, Path(args.tools_dir))
    quantize(f16_gguf, gguf_out, args.quant, quantize_bin)

    print("")
    print("Listo. GGUF final:", gguf_out)
    print("Para registrarlo en Ollama, desde la raiz del proyecto:")
    print("  ollama create qwen2.5-coder-triage -f Modelfile")


if __name__ == "__main__":
    main()
