"""Request intake: the mandatory request template, parsed strictly.

A request is a filled-in copy of templates/talep-sablonu.txt. Parsing is code, not
model: the model never has to find the fields, and a request that does not follow
the template goes back to the requester.
"""
HEADER = ("talep_no", "talep_eden", "islem")
FIELDS = {"klasor": "folder", "is_adi": "name", "tip": "type", "host": "host", "calistiran": "run_as",
          "komut": "command", "gunler": "calendar", "saat": "time", "bagimlilik": "deps",
          "bildirim": "notify", "aciklama": "description",
          "baglanti": "connection", "hedef": "target", "sure_siniri": "timeout"}
# Written only for the job types that use them; which type needs which is a check, not a template rule.
TYPE_KEYS = ("baglanti", "hedef", "sure_siniri")
OPS = ("yeni", "degisiklik", "kaldir")
IDENTITY = ("klasor", "is_adi")


def parse(text):
    """Return (values, errors). `values` keeps the template's own keys."""
    values, errors = {}, []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if not sep or key not in HEADER + tuple(FIELDS):
            errors.append(f"sablonda olmayan satir: {line[:40]}")
        elif key in values:
            errors.append(f"alan iki kez yazilmis: {key}")
        elif key == "bagimlilik":
            inner = val[1:-1] if val.startswith("[") and val.endswith("]") else val
            values[key] = [x.strip() for x in inner.split(",") if x.strip()]
        elif val:
            values[key] = val

    errors += [f"zorunlu alan bos: {k}" for k in HEADER if not values.get(k)]
    op = values.get("islem")
    if op and op not in OPS:
        errors.append("islem 'yeni', 'degisiklik' ya da 'kaldir' olmali")
    if op == "yeni":
        optional = set(TYPE_KEYS) | {"bagimlilik"} | ({"komut"} if values.get("tip") == "bos" else set())
        errors += [f"zorunlu alan bos: {k}" for k in FIELDS if k not in optional and not values.get(k)]
        if "bagimlilik" not in values:
            errors.append("zorunlu alan bos: bagimlilik (bagimlilik yoksa [] yazin)")
    elif op == "degisiklik":
        errors += [f"zorunlu alan bos: {k}" for k in IDENTITY if not values.get(k)]
        if not any(k in values for k in FIELDS if k not in IDENTITY):
            errors.append("degisecek alan yazilmamis")
    elif op == "kaldir":
        errors += [f"zorunlu alan bos: {k}" for k in IDENTITY if not values.get(k)]
        extra = sorted(k for k in values if k in FIELDS and k not in IDENTITY)
        if extra:
            errors.append("kaldirma talebinde yalnizca klasor ve is_adi yazilir; fazla alan: " + ", ".join(extra))
    return values, errors


def to_definition(values):
    """Template keys -> definition fields, only for the fields the requester wrote."""
    return {FIELDS[k]: v for k, v in values.items() if k in FIELDS}
