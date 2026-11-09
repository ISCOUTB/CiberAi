import random
import string


def token():
    return "".join(random.choice(string.ascii_letters) for _ in range(16))
