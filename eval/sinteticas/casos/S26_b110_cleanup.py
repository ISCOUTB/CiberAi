import os


def limpiar(path):
    try:
        os.remove(path)
    except Exception:
        pass
