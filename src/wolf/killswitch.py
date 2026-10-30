import os


def is_engaged(path):
    return os.path.exists(path)


def engage(path, reason="manual"):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(reason + "\n")


def release(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
