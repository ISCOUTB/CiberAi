import sqlite3


def buscar(conn, nombre):
    query = "SELECT * FROM users WHERE nombre = '%s'" % nombre
    return conn.execute(query).fetchall()
