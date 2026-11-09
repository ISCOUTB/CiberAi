import subprocess


def ping(host):
    return subprocess.call("ping " + host, shell=True)
