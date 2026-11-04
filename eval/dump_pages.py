import re
import fitz

doc = fitz.open(r"C:\Games\u\proyecto ing\eval\Avance 4.pdf")
for i, page in enumerate(doc):
    lines = [l.strip() for l in page.get_text().splitlines() if l.strip()]
    print("--- pagina {}: {} lineas".format(i + 1, len(lines)))
    if lines:
        print("    inicia:", lines[0][:80])
    for line in lines:
        if re.match(r"^[1-9]\.(\s|\d)", line):
            print("    ", line[:80])
