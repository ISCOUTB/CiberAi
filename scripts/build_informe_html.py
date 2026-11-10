"""Genera docs/INFORME_FINAL.html a partir de INFORME_FINAL.md.

Incrusta las imágenes de reportes/ en base64 para que el HTML sea autocontenido.

Uso:
    python scripts/build_informe_html.py
"""

import base64
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "docs" / "INFORME_FINAL.md"
OUT = ROOT / "docs" / "INFORME_FINAL.html"
REPORTES = ROOT / "reportes"


def img_to_base64(path: Path) -> str:
    data = path.read_bytes()
    ext = path.suffix.lstrip(".").lower()
    if ext == "svg":
        mime = "image/svg+xml"
    elif ext == "jpg" or ext == "jpeg":
        mime = "image/jpeg"
    else:
        mime = "image/png"
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def md_to_html(md: str) -> str:
    # Escape HTML chars in text, but preserve markdown constructs.
    # We will do a simple line-by-line conversion.
    lines = md.splitlines()
    html_lines = []
    in_code = False
    in_table = False
    table_rows = []

    def flush_table():
        nonlocal table_rows
        if not table_rows:
            return
        # First row is header, second is separator
        header = table_rows[0]
        body = table_rows[2:]
        out = ['<table>']
        out.append('<thead><tr>' + ''.join(f'<th>{c}</th>' for c in header) + '</tr></thead>')
        out.append('<tbody>')
        for row in body:
            out.append('<tr>' + ''.join(f'<td>{c}</td>' for c in row) + '</tr>')
        out.append('</tbody></table>')
        html_lines.extend(out)
        table_rows = []

    for line in lines:
        stripped = line.strip()

        # Code blocks
        if stripped.startswith("```"):
            if in_code:
                html_lines.append("</code></pre>")
                in_code = False
            else:
                lang = stripped[3:].strip()
                html_lines.append(f'<pre><code class="language-{lang}">')
                in_code = True
            continue
        if in_code:
            html_lines.append(line)
            continue

        # Tables
        if "|" in line:
            cells = [c.strip() for c in line.split("|")]
            cells = [c for c in cells if c or c == ""]
            # Drop leading/trailing empty cells from outer pipes
            if line.startswith("|"):
                cells = cells[1:]
            if all(re.fullmatch(r"[-:]+", c) for c in cells if c):
                # separator row
                table_rows.append(cells)
                continue
            if not in_table:
                in_table = True
            table_rows.append(cells)
            continue
        else:
            if in_table:
                flush_table()
                in_table = False

        # Headings
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            title = m.group(2)
            anchor = re.sub(r"[^\w\s-]", "", title).strip().lower().replace(" ", "-")
            html_lines.append(f'<h{level} id="{anchor}">{title}</h{level}>')
            continue

        # Blockquotes
        if stripped.startswith(">"):
            text = stripped[1:].strip()
            html_lines.append(f'<blockquote>{text}</blockquote>')
            continue

        # Images
        m = re.match(r"^!\[(.*?)\]\((.*?)\)$", stripped)
        if m:
            alt, src = m.groups()
            img_path = ROOT / src
            if img_path.exists():
                b64 = img_to_base64(img_path)
                html_lines.append(
                    f'<figure><img src="{b64}" alt="{alt}" style="max-width:100%;height:auto;">'
                    f'<figcaption>{alt}</figcaption></figure>'
                )
            else:
                html_lines.append(f'<p>[Imagen no encontrada: {src}]</p>')
            continue

        # Empty line
        if not stripped:
            html_lines.append("")
            continue

        # Paragraph with inline formatting
        # Bold **text**
        inline = line
        inline = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", inline)
        inline = re.sub(r"\*(.+?)\*", r"<em>\1</em>", inline)
        inline = re.sub(r"`(.+?)`", r"<code>\1</code>", inline)
        html_lines.append(f"<p>{inline}</p>")

    if in_table:
        flush_table()
    if in_code:
        html_lines.append("</code></pre>")

    return "\n".join(html_lines)


def main():
    md = MD.read_text(encoding="utf-8")
    body = md_to_html(md)

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Agente inteligente para la revisión de seguridad de código fuente</title>
<style>
  :root {{
    --navy: #0F1633;
    --blue: #2864E8;
    --cyan: #1DB6D9;
    --dark: #1F2A44;
    --muted: #64708B;
    --bg: #ffffff;
    --line: #E3E8F4;
  }}
  @page {{
    size: A4;
    margin: 2.5cm 2cm;
  }}
  body {{
    font-family: "DejaVu Sans", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: var(--dark);
    max-width: 21cm;
    margin: 0 auto;
    padding: 2cm;
    background: var(--bg);
  }}
  h1 {{
    font-size: 22pt;
    color: var(--navy);
    border-bottom: 2px solid var(--blue);
    padding-bottom: 0.3em;
    margin-top: 1.5em;
    page-break-after: avoid;
  }}
  h2 {{
    font-size: 16pt;
    color: var(--blue);
    margin-top: 1.4em;
    page-break-after: avoid;
  }}
  h3 {{
    font-size: 13pt;
    color: var(--cyan);
    margin-top: 1.2em;
    page-break-after: avoid;
  }}
  h4 {{
    font-size: 12pt;
    color: var(--dark);
    margin-top: 1em;
  }}
  p {{
    text-align: justify;
    margin: 0.6em 0;
  }}
  a {{
    color: var(--blue);
    text-decoration: none;
  }}
  ul, ol {{
    margin: 0.5em 0;
    padding-left: 1.5em;
  }}
  li {{
    margin: 0.25em 0;
  }}
  code {{
    font-family: Consolas, "Courier New", monospace;
    background: #F2F2F2;
    padding: 0.1em 0.3em;
    border-radius: 3px;
    font-size: 0.95em;
  }}
  pre {{
    background: #F2F2F2;
    padding: 1em;
    border-radius: 5px;
    overflow-x: auto;
    font-size: 9.5pt;
    line-height: 1.4;
    page-break-inside: avoid;
  }}
  pre code {{
    background: transparent;
    padding: 0;
  }}
  blockquote {{
    border-left: 4px solid var(--blue);
    margin: 1em 0;
    padding: 0.5em 1em;
    background: #EEF3FF;
    color: var(--muted);
    font-style: italic;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    font-size: 10pt;
    page-break-inside: avoid;
  }}
  th, td {{
    border: 1px solid var(--line);
    padding: 0.4em 0.6em;
    text-align: left;
  }}
  th {{
    background: var(--navy);
    color: white;
    font-weight: bold;
  }}
  tr:nth-child(even) {{
    background: #F8FAFC;
  }}
  figure {{
    margin: 1.5em 0;
    text-align: center;
    page-break-inside: avoid;
  }}
  figure img {{
    max-width: 100%;
    height: auto;
    border: 1px solid var(--line);
    border-radius: 4px;
  }}
  figcaption {{
    font-size: 10pt;
    color: var(--muted);
    margin-top: 0.5em;
    font-style: italic;
  }}
  .portada {{
    text-align: center;
    margin-top: 4cm;
  }}
  .portada h1 {{
    border: none;
    font-size: 26pt;
    margin-bottom: 0.5em;
  }}
  .portada .meta {{
    color: var(--muted);
    font-size: 12pt;
    margin: 0.5em 0;
  }}
  @media print {{
    body {{
      padding: 0;
      background: white;
    }}
    h1, h2, h3 {{
      page-break-after: avoid;
    }}
    figure, table, pre {{
      page-break-inside: avoid;
    }}
  }}
</style>
</head>
<body>
{body}
</body>
</html>"""

    OUT.write_text(html, encoding="utf-8")
    print("guardado:", OUT)
    print("tamaño:", OUT.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
