import re

def normalize_name(name: str) -> str:
    if not name:
        return None
    name = name.lower()
    name = re.sub(r"[^\w\s]", "", name)  # remove dots, commas
    name = re.sub(r"\s+", " ", name).strip()
    return name


def safe_int(val, default=0):
    try:
        return int(val)
    except:
        return default


def safe_float(val, default=0.0):
    try:
        return float(val)
    except:
        return default


def clean_name(name):
    return (
        name.replace("(c)", "")
            .replace("(wk)", "")
            .strip()
    )