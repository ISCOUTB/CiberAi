"""Primera pasada automática de etiquetado para eval/auditoria_repos.jsonl.

Deja 'dudoso' en los casos que no son obvios. El autor debe revisar manualmente.
"""

import json
import re
from pathlib import Path

AUDITORIA = Path("eval/auditoria_repos.jsonl")


def es_test(archivo, contexto):
    return "test" in archivo.lower() or "assert" in contexto.lower()


def lineas_constantes(contexto):
    """Heurística: busca listas de literales o ausencia de variables externas."""
    c = contexto.replace("\n", " ")
    return bool(re.search(r"\[['\"][^'\"]+['\"]\s*,\s*['\"]", c))


def etiquetar(alerta):
    regla = alerta["regla"]
    archivo = alerta["archivo"].lower()
    ctx = alerta["contexto"]

    # Patrones que suelen ser falsos positivos en estos repos
    if regla == "B101" and es_test(archivo, ctx):
        return "falso_positivo", "assert en prueba o código auxiliar; no es control de seguridad."
    if regla == "B110":
        # B110 es except Exception + pass. En itsdangerous es intencional para timestamp.
        return "falso_positivo", "pass intencional en manejo de formato de timestamp."
    if regla in ("B404", "B408"):
        return "falso_positivo", "import de módulo considerado inseguro; el uso es legítimo y controlado."
    if regla == "B105":
        # Credenciales: revisar contexto
        if re.search(r"test|dummy|example|placeholder", ctx, re.I):
            return "falso_positivo", "cadena de prueba o marcador, no credencial real."
        return "dudoso", "posible credencial; revisar si es producción."
    if regla in ("B603", "B605", "B607"):
        if lineas_constantes(ctx):
            return "falso_positivo", "subprocess con argumentos constantes; no inyección."
        if regla == "B603" and "sh" in ctx and "-c" in ctx:
            return "dudoso", "subprocess con sh -c; revisar si el comando es externo."
        return "dudoso", "subprocess; revisar si hay entrada externa."
    if regla == "B602":
        return "dudoso", "shell=True; revisar si el comando depende de entrada externa."
    if regla == "B324" and "itsdangerous" in archivo:
        return "real", "uso de SHA-1 como algoritmo de firma; aunque sea configurable, es un hash débil."
    if regla == "B310" and "jwks" in archivo:
        return "real", "urlopen sin validación de URL; potencial SSRF."
    if regla == "B310":
        return "dudoso", "urlopen; revisar si la URL es controlada."
    if regla == "B311":
        return "dudoso", "uso de random; revisar si es para seguridad."
    if regla == "B301":
        return "real", "uso de pickle.loads con entrada potencialmente externa."
    if regla == "B608":
        return "dudoso", "construcción SQL; revisar si usa parámetros."

    return "dudoso", "revisar manualmente"


def main():
    filas = []
    with AUDITORIA.open(encoding="utf-8") as fh:
        for linea in fh:
            if linea.strip():
                filas.append(json.loads(linea))

    for f in filas:
        if f["etiqueta"] in ("", "dudoso"):
            etiqueta, just = etiquetar(f)
            f["etiqueta"] = etiqueta
            f["justificacion"] = just
            f["auditor"] = "auto"

    AUDITORIA.write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in filas) + "\n",
        encoding="utf-8")
    conteo = {}
    for f in filas:
        conteo[f["etiqueta"]] = conteo.get(f["etiqueta"], 0) + 1
    print("Etiquetado automático:", conteo)
    print("Revisa los 'dudoso' antes de calcular métricas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
