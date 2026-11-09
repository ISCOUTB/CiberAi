import subprocess


def listar():
    return subprocess.run(["ls", "-l"], check=True)
