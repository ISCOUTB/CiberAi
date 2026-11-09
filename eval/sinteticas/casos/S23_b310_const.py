from urllib.request import urlopen


def estado():
    return urlopen("https://example.com/status").read()
