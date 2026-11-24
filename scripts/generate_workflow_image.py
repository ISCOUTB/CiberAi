"""Genera assets/workflow.png para el README."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)

WIDTH, HEIGHT = 1400, 600
BG = "#ffffff"
TEXT = "#1f2937"
BOX_BG = "#e0f2fe"
BOX_BORDER = "#0284c7"
ACCENT_BG = "#f0f9ff"
ACCENT_BORDER = "#0ea5e9"
ARROW = "#334155"


def draw_box(draw, x, y, w, h, text, fill=BOX_BG, border=BOX_BORDER, font=None):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=8, fill=fill, outline=border, width=2)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text((x + (w - tw) // 2, y + (h - th) // 2 - 2), text, fill=TEXT, font=font)


def draw_arrow(draw, x1, y1, x2, y2, font=None):
    draw.line([(x1, y1), (x2, y2)], fill=ARROW, width=2)
    # small arrowhead
    if x2 > x1:
        draw.polygon([(x2, y2), (x2 - 8, y2 - 4), (x2 - 8, y2 + 4)], fill=ARROW)
    elif x2 < x1:
        draw.polygon([(x2, y2), (x2 + 8, y2 - 4), (x2 + 8, y2 + 4)], fill=ARROW)
    elif y2 > y1:
        draw.polygon([(x2, y2), (x2 - 4, y2 - 8), (x2 + 4, y2 - 8)], fill=ARROW)
    else:
        draw.polygon([(x2, y2), (x2 - 4, y2 + 8), (x2 + 4, y2 + 8)], fill=ARROW)


def main():
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("segoeui.ttf", 16)
        title_font = ImageFont.truetype("segoeui.ttf", 24)
        small_font = ImageFont.truetype("segoeui.ttf", 13)
    except Exception:
        font = ImageFont.load_default()
        title_font = font
        small_font = font

    # Title
    title = "Flujo de trabajo de CiberAi"
    bbox = draw.textbbox((0, 0), title, font=title_font)
    tw = bbox[2] - bbox[0]
    draw.text(((WIDTH - tw) // 2, 20), title, fill=TEXT, font=title_font)

    # Boxes dimensions
    bw, bh = 170, 60

    # Row 1: repo -> detectors
    repo_x, repo_y = 60, 140
    draw_box(draw, repo_x, repo_y, bw, bh, "Repositorio\nPython", fill="#dcfce7", border="#16a34a", font=font)

    detectors = [
        ("Bandit\nSAST", 330, 80, "#fee2e2", "#dc2626"),
        ("Escáner OWASP\npropio", 330, 160, "#fef3c7", "#d97706"),
        ("LLM local\n(Ollama)", 330, 240, "#ede9fe", "#7c3aed"),
    ]
    for text, dx, dy, fill, border in detectors:
        draw_box(draw, dx, dy, bw, bh, text, fill=fill, border=border, font=font)
        draw_arrow(draw, repo_x + bw, repo_y + bh // 2, dx, dy + bh // 2, font=font)

    # Normalization box
    norm_x, norm_y = 600, 150
    draw_box(draw, norm_x, norm_y, 220, 80, "Normalizar +\ndeduplicar hallazgos", fill=ACCENT_BG, border=ACCENT_BORDER, font=font)
    for _, dx, dy, _, _ in detectors:
        draw_arrow(draw, dx + bw, dy + bh // 2, norm_x, norm_y + 40, font=font)

    # Triage box
    triage_x, triage_y = 900, 150
    draw_box(draw, triage_x, triage_y, 190, 80, "Triage con\nmodelo local", fill=ACCENT_BG, border=ACCENT_BORDER, font=font)
    draw_arrow(draw, norm_x + 220, norm_y + 40, triage_x, triage_y + 40, font=font)

    # Outputs
    outputs = [
        ("reporte.json", 1180, 110),
        ("hallazgos.sarif", 1180, 210),
    ]
    for text, ox, oy in outputs:
        draw_box(draw, ox, oy, 150, 60, text, fill="#f3f4f6", border="#4b5563", font=font)
        draw_arrow(draw, triage_x + 190, triage_y + 40, ox, oy + 30, font=font)

    # Interfaces row
    iface_y = 420
    interfaces = [
        ("Terminal CLI", 260, "#e0f2fe", "#0284c7"),
        ("Dashboard web", 560, "#fce7f3", "#db2777"),
        ("TUI pantalla completa", 860, "#ecfccb", "#65a30d"),
    ]
    draw.text((60, iface_y + 20), "Interfaces:", fill=TEXT, font=font)
    for text, ix, fill, border in interfaces:
        draw_box(draw, ix, iface_y, 190, 50, text, fill=fill, border=border, font=font)
        # connect outputs to interfaces visually
        draw.line([(ix + 95, iface_y), (ix + 95, iface_y - 30), (1180, iface_y - 30)], fill="#cbd5e1", width=1)

    # Advisor note
    note = "Modo asesor: SAFE solo recomienda descartar; la alerta permanece en el reporte."
    bbox = draw.textbbox((0, 0), note, font=small_font)
    tw = bbox[2] - bbox[0]
    draw.text(((WIDTH - tw) // 2, 520), note, fill="#4b5563", font=small_font)

    out_path = ASSETS / "workflow.png"
    img.save(out_path, "PNG")
    print("Imagen guardada en:", out_path)


if __name__ == "__main__":
    main()
