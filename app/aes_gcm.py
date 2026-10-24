"""
AES-256-GCM en Python puro (respaldo de la tablet si el cifrado de Android no responde).
Mismo resultado que cryptography.AESGCM: texto cifrado || etiqueta de 16 bytes.
Es mas lento (unos segundos para un proyecto), pero no depende de nada.
"""

def _crear_sbox():
    """S-box de AES calculada (inverso en GF(2^8) + transformacion afin)."""
    sbox = [0] * 256
    p = q = 1
    while True:
        p = p ^ ((p << 1) & 0xFF) ^ (0x1B if p & 0x80 else 0)
        q ^= q << 1
        q ^= q << 2
        q ^= q << 4
        q &= 0xFF
        if q & 0x80:
            q ^= 0x09
        x = q ^ (((q << 1) | (q >> 7)) & 0xFF) ^ (((q << 2) | (q >> 6)) & 0xFF) ^ \
            (((q << 3) | (q >> 5)) & 0xFF) ^ (((q << 4) | (q >> 4)) & 0xFF)
        sbox[p] = x ^ 0x63
        if p == 1:
            break
    sbox[0] = 0x63
    return bytes(sbox)


_SBOX = _crear_sbox()


def _xt(a):
    a <<= 1
    return (a ^ 0x11B) & 0xFF if a & 0x100 else a


def _tablas():
    t0 = []
    for x in range(256):
        s = _SBOX[x]
        s2 = _xt(s)
        s3 = s2 ^ s
        t0.append((s2 << 24) | (s << 16) | (s << 8) | s3)
    rot = lambda v, n: ((v >> n) | (v << (32 - n))) & 0xFFFFFFFF
    return t0, [rot(v, 8) for v in t0], [rot(v, 16) for v in t0], [rot(v, 24) for v in t0]


_T0, _T1, _T2, _T3 = _tablas()


def _expandir(llave):
    nk = len(llave) // 4
    nr = nk + 6
    w = [int.from_bytes(llave[4 * i:4 * i + 4], "big") for i in range(nk)]
    rcon = 1
    for i in range(nk, 4 * (nr + 1)):
        t = w[i - 1]
        if i % nk == 0:
            t = ((t << 8) | (t >> 24)) & 0xFFFFFFFF
            t = (_SBOX[t >> 24] << 24) | (_SBOX[(t >> 16) & 255] << 16) | (_SBOX[(t >> 8) & 255] << 8) | _SBOX[t & 255]
            t ^= rcon << 24
            rcon = _xt(rcon)
        elif nk > 6 and i % nk == 4:
            t = (_SBOX[t >> 24] << 24) | (_SBOX[(t >> 16) & 255] << 16) | (_SBOX[(t >> 8) & 255] << 8) | _SBOX[t & 255]
        w.append(w[i - nk] ^ t)
    return w, nr


def _bloque(w, nr, b):
    s0, s1, s2, s3 = (int.from_bytes(b[i:i + 4], "big") ^ w[k] for k, i in enumerate((0, 4, 8, 12)))
    T0, T1, T2, T3 = _T0, _T1, _T2, _T3
    k = 4
    for _ in range(nr - 1):
        t0 = T0[s0 >> 24] ^ T1[(s1 >> 16) & 255] ^ T2[(s2 >> 8) & 255] ^ T3[s3 & 255] ^ w[k]
        t1 = T0[s1 >> 24] ^ T1[(s2 >> 16) & 255] ^ T2[(s3 >> 8) & 255] ^ T3[s0 & 255] ^ w[k + 1]
        t2 = T0[s2 >> 24] ^ T1[(s3 >> 16) & 255] ^ T2[(s0 >> 8) & 255] ^ T3[s1 & 255] ^ w[k + 2]
        t3 = T0[s3 >> 24] ^ T1[(s0 >> 16) & 255] ^ T2[(s1 >> 8) & 255] ^ T3[s2 & 255] ^ w[k + 3]
        s0, s1, s2, s3 = t0, t1, t2, t3
        k += 4
    S = _SBOX
    out = b""
    for a, b_, c, d, wk in ((s0, s1, s2, s3, w[k]), (s1, s2, s3, s0, w[k + 1]), (s2, s3, s0, s1, w[k + 2]),
                            (s3, s0, s1, s2, w[k + 3])):
        v = (S[a >> 24] << 24) | (S[(b_ >> 16) & 255] << 16) | (S[(c >> 8) & 255] << 8) | S[d & 255]
        out += (v ^ wk).to_bytes(4, "big")
    return out


_R = 0xE1 << 120


def _ghash_tabla(h):
    """Multiplicacion por H en GF(2^128) con tablas de 4 bits (16 x 32)."""
    def mul(x, y):
        z, v = 0, y
        for i in range(127, -1, -1):
            if (x >> i) & 1:
                z ^= v
            v = (v >> 1) ^ _R if v & 1 else v >> 1
        return z
    tabla = []
    for pos in range(32):
        fila = []
        for n in range(16):
            fila.append(mul(n << (4 * (31 - pos)), h))
        tabla.append(fila)
    return tabla


def _ghash(tabla, aad, ct):
    y = 0

    def bloques(datos):
        for i in range(0, len(datos), 16):
            yield datos[i:i + 16].ljust(16, b"\x00")
    for blk in list(bloques(aad)) + list(bloques(ct)) + [(len(aad) * 8).to_bytes(8, "big") + (len(ct) * 8).to_bytes(8, "big")]:
        y ^= int.from_bytes(blk, "big")
        z = 0
        for pos in range(32):
            z ^= tabla[pos][(y >> (4 * (31 - pos))) & 15]
        y = z
    return y


def _ctr(w, nr, j0, datos):
    out = bytearray()
    cont = int.from_bytes(j0, "big")
    for i in range(0, len(datos), 16):
        cont = (cont & ~0xFFFFFFFF) | ((cont + 1) & 0xFFFFFFFF)
        ks = _bloque(w, nr, cont.to_bytes(16, "big"))
        trozo = datos[i:i + 16]
        out += (int.from_bytes(trozo, "big") ^ int.from_bytes(ks[:len(trozo)], "big")).to_bytes(len(trozo), "big")
    return bytes(out)


class EtiquetaInvalida(Exception):
    pass


def _prep(llave, nonce):
    w, nr = _expandir(llave)
    h = int.from_bytes(_bloque(w, nr, bytes(16)), "big")
    j0 = nonce + b"\x00\x00\x00\x01"
    return w, nr, _ghash_tabla(h), j0


def cifrar(llave, nonce, datos, aad=b""):
    w, nr, tabla, j0 = _prep(llave, nonce)
    ct = _ctr(w, nr, j0, datos)
    s = _ghash(tabla, aad, ct)
    tag = (s ^ int.from_bytes(_bloque(w, nr, j0), "big")).to_bytes(16, "big")
    return ct + tag


def descifrar(llave, nonce, datos, aad=b""):
    if len(datos) < 16:
        raise EtiquetaInvalida()
    ct, tag = datos[:-16], datos[-16:]
    w, nr, tabla, j0 = _prep(llave, nonce)
    s = _ghash(tabla, aad, ct)
    esperado = (s ^ int.from_bytes(_bloque(w, nr, j0), "big")).to_bytes(16, "big")
    import hmac
    if not hmac.compare_digest(esperado, tag):
        raise EtiquetaInvalida()
    return _ctr(w, nr, j0, ct)
