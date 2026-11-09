import hashlib


def etag(contenido):
    return hashlib.md5(contenido).hexdigest()
