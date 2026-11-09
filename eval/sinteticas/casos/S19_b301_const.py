import pickle

DEFAULT = b"\x80\x04K\x01."


def cargar():
    return pickle.loads(DEFAULT)
