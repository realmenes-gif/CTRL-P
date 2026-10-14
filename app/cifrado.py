"""
Ctrl-P Android - cifrado RSA-OAEP (SHA-256) en Python puro.
Si en la tablet no esta la libreria «cryptography», esto reemplaza la funcion del nucleo que guarda la contrasena
de cada usuario cifrada para el administrador. El resultado es el mismo formato que en la computadora
(el administrador la puede ver desde la computadora).
"""

import base64
import hashlib
import os


def _der_largo(b, i):
    n = b[i]
    i += 1
    if n < 0x80:
        return n, i
    k = n & 0x7F
    return int.from_bytes(b[i:i + k], "big"), i + k


def _der_elem(b, i):
    tag = b[i]
    largo, j = _der_largo(b, i + 1)
    return tag, b[j:j + largo], j + largo


def clave_publica(pem):
    """PEM «PUBLIC KEY» (SubjectPublicKeyInfo) -> (n, e)."""
    txt = pem.decode() if isinstance(pem, bytes) else pem
    der = base64.b64decode("".join(l for l in txt.strip().splitlines() if not l.startswith("-----")))
    _, spki, _ = _der_elem(der, 0)                 # SEQUENCE
    _, _, i = _der_elem(spki, 0)                   # AlgorithmIdentifier
    _, bits, _ = _der_elem(spki, i)                # BIT STRING
    _, rsa, _ = _der_elem(bits[1:], 0)             # SEQUENCE { n, e }
    _, n, i = _der_elem(rsa, 0)
    _, e, _ = _der_elem(rsa, i)
    return int.from_bytes(n, "big"), int.from_bytes(e, "big")


def _mgf1(semilla, largo):
    out = b""
    c = 0
    while len(out) < largo:
        out += hashlib.sha256(semilla + c.to_bytes(4, "big")).digest()
        c += 1
    return out[:largo]


def cifrar_oaep(pem, mensaje):
    n, e = clave_publica(pem)
    k = (n.bit_length() + 7) // 8
    h = 32
    if len(mensaje) > k - 2 * h - 2:
        raise ValueError("Mensaje demasiado largo")
    lhash = hashlib.sha256(b"").digest()
    db = lhash + b"\x00" * (k - len(mensaje) - 2 * h - 2) + b"\x01" + mensaje
    semilla = os.urandom(h)
    mdb = bytes(a ^ b for a, b in zip(db, _mgf1(semilla, k - h - 1)))
    msem = bytes(a ^ b for a, b in zip(semilla, _mgf1(mdb, h)))
    em = b"\x00" + msem + mdb
    return pow(int.from_bytes(em, "big"), e, n).to_bytes(k, "big")


def instalar(core):
    """Si falta «cryptography», el nucleo usa este cifrado (mismo resultado)."""
    try:
        import cryptography  # noqa: F401
        return False
    except Exception:
        pass

    def _cifrar_para_admin(clave):
        try:
            return base64.b64encode(cifrar_oaep(core.ADMIN_PUBLICA, clave.encode("utf-8"))).decode()
        except Exception:
            return ""
    core._cifrar_para_admin = _cifrar_para_admin
    return True
