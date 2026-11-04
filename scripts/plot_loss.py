"""Genera la curva de perdida de entrenamiento a partir de trainer_state.json.

Lee el ultimo checkpoint de training/out/qwen-coder-1.5b-lora y dibuja la
perdida de entrenamiento con una media movil. La perdida de validacion no se
grafica porque las evaluaciones intermedias dieron NaN: la truncacion a 2048
tokens dejaba ejemplos sin tokens de respuesta. El generador de datos ya se
corrigio (training/train_qlora.py, encode_rows), asi que una futura corrida
producira ambas curvas.

Uso:
    python scripts/plot_loss.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
LORA_DIR = ROOT / "training" / "out" / "qwen-coder-1.5b-lora"
OUT = ROOT / "reportes" / "curva_perdida.png"

NAVY = "#0F1633"
BLUE = "#2864E8"
MUTED = "#64708B"


def last_trainer_state():
    checkpoints = []
    for path in LORA_DIR.glob("checkpoint-*"):
        if path.is_dir():
            try:
                checkpoints.append((int(path.name.split("-")[1]), path))
            except ValueError:
                continue
    candidates = [p / "trainer_state.json" for _, p in sorted(checkpoints)]
    candidates.append(LORA_DIR / "trainer_state.json")
    for candidate in reversed(candidates):
        if candidate.exists():
            return candidate
    raise FileNotFoundError("No se encontro trainer_state.json en {}".format(LORA_DIR))


def moving_average(values, window=5):
    out = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        chunk = values[start:i + 1]
        out.append(sum(chunk) / len(chunk))
    return out


def main():
    state = json.loads(last_trainer_state().read_text(encoding="utf-8"))
    history = [e for e in state.get("log_history", []) if "loss" in e and "step" in e]
    if not history:
        raise SystemExit("trainer_state.json no contiene perdidas de entrenamiento")

    steps = [e["step"] for e in history]
    losses = [e["loss"] for e in history]
    smooth = moving_average(losses, 5)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    plt.rcParams["font.family"] = "DejaVu Sans"
    fig, ax = plt.subplots(figsize=(7.2, 3.4), dpi=200)
    ax.plot(steps, losses, color=MUTED, linewidth=0.8, alpha=0.45, label="Pérdida por paso")
    ax.plot(steps, smooth, color=BLUE, linewidth=2.2, label="Media móvil (5 puntos)")
    ax.set_xlabel("Paso de optimización", color=NAVY, fontsize=9)
    ax.set_ylabel("Pérdida", color=NAVY, fontsize=9)
    ax.set_title("Pérdida de entrenamiento — QLoRA, 1 época, 11.510 ejemplos",
                 color=NAVY, fontsize=10, loc="left")
    ax.grid(True, color="#E3E8F4", linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#C9D2E3")
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    ax.annotate("final {:.3f}".format(smooth[-1]),
                xy=(steps[-1], smooth[-1]),
                xytext=(-70, 18), textcoords="offset points",
                fontsize=8, color=BLUE,
                arrowprops={"arrowstyle": "-", "color": BLUE, "linewidth": 0.8})
    fig.tight_layout()
    fig.savefig(OUT, bbox_inches="tight")
    print("guardado:", OUT)
    print("puntos:", len(losses), "| perdida final:", round(smooth[-1], 4))


if __name__ == "__main__":
    main()
