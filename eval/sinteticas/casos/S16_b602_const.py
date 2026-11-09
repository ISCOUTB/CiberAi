import subprocess


def estado():
    return subprocess.call("uptime", shell=True)
