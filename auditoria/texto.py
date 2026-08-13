"""Utilitarios de normalizacao de texto (remover acento, casefold, etc)."""

import re
import unicodedata


def sem_acento(s):
    s = str(s or "")
    nfkd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalizar_texto(s):
    s = sem_acento(s).lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return s.strip()


def normalizar_header(s):
    s = sem_acento(s).lower()
    return re.sub(r"[^a-z0-9]", "", s)


def apenas_digitos(s):
    return re.sub(r"\D", "", str(s or ""))


def para_numero(br_str):
    if br_str is None or br_str == "":
        return 0.0
    if isinstance(br_str, (int, float)):
        return float(br_str)
    limpo = str(br_str).strip()
    limpo = re.sub(r"[R$\s]", "", limpo)
    if limpo == "":
        return 0.0
    sem_milhar = limpo.replace(".", "").replace(",", ".")
    try:
        return float(sem_milhar)
    except ValueError:
        return 0.0
