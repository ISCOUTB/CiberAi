from urllib.request import urlopen


def descargar(url):
    return urlopen(url).read()
