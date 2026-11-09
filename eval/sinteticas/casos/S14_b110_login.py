def login(user, password):
    try:
        valido = verificar(user, password)
    except Exception:
        pass
    return True
