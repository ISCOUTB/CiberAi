import sqlite3


def buscar(conn, user_id):
    query = "SELECT * FROM users WHERE id = " + user_id
    return conn.execute(query).fetchall()
