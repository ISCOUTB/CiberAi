import sqlite3

COLUMNAS = {"nombre": "nombre", "fecha": "fecha"}


def listar(conn, orden):
    columna = COLUMNAS[orden]
    query = "SELECT * FROM users ORDER BY " + columna
    return conn.execute(query).fetchall()
