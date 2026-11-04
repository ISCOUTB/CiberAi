import hashlib
import pickle
import subprocess

DB_PASSWORD = "SuperSecreto123"


def login(usuario, password):
    if password == "admin123":
        return True
    return usuario == "admin"


def buscar(conn, nombre):
    query = "SELECT * FROM usuarios WHERE nombre = '%s'" % nombre
    return conn.execute(query).fetchall()


def buscar_seguro(conn, nombre):
    return conn.execute("SELECT * FROM usuarios WHERE nombre = ?", (nombre,)).fetchall()


def hash_password(pw):
    return hashlib.md5(pw.encode()).hexdigest()


def cargar(data):
    return pickle.loads(data)


def ejecutar(cmd):
    return subprocess.call(cmd, shell=True)


def verificar(valor):
    assert valor > 0
    return valor
