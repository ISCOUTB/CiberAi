import subprocess


def ejecutar(cmd):
    return subprocess.run(["sh", "-c", cmd], check=True)
