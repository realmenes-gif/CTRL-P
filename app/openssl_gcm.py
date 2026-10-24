"""
AES-256-GCM con la libreria OpenSSL (libcrypto) que ya viene dentro del APK (la usa Python para https).
Igual de rapido que en la computadora. Mismo formato: texto cifrado || etiqueta de 16 bytes.
"""

import ctypes
import ctypes.util
import glob
import os
import sys

_LIB = []


class EtiquetaInvalida(Exception):
    pass


def _candidatos():
    vistos = []
    try:
        from jnius import autoclass
        act = autoclass("org.kivy.android.PythonActivity").mActivity
        vistos.append(act.getApplicationInfo().nativeLibraryDir)
    except Exception:
        pass
    for mod in ("_ssl", "_hashlib"):
        try:
            m = __import__(mod)
            if getattr(m, "__file__", None):
                vistos.append(os.path.dirname(m.__file__))
        except Exception:
            pass
    vistos += [p for p in sys.path if p and os.path.isdir(p)]
    for d in vistos:
        for patron in ("libcrypto*.so*",):
            for f in sorted(glob.glob(os.path.join(d, patron))):
                yield f
            for f in sorted(glob.glob(os.path.join(d, "..", "lib", patron))):
                yield f
    n = ctypes.util.find_library("crypto")
    if n:
        yield n
    for n in ("libcrypto.so.3", "libcrypto.so.1.1", "libcrypto1.1.so", "libcrypto.so"):
        yield n


def _lib():
    if _LIB:
        return _LIB[0]
    ultimo = None
    for ruta in _candidatos():
        try:
            L = ctypes.CDLL(ruta)
            L.EVP_aes_256_gcm.restype = ctypes.c_void_p
            L.EVP_CIPHER_CTX_new.restype = ctypes.c_void_p
            L.EVP_CIPHER_CTX_free.argtypes = [ctypes.c_void_p]
            for f in ("EVP_EncryptInit_ex", "EVP_DecryptInit_ex"):
                getattr(L, f).argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_char_p,
                                          ctypes.c_char_p]
            for f in ("EVP_EncryptUpdate", "EVP_DecryptUpdate"):
                getattr(L, f).argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int),
                                          ctypes.c_char_p, ctypes.c_int]
            for f in ("EVP_EncryptFinal_ex", "EVP_DecryptFinal_ex"):
                getattr(L, f).argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
            L.EVP_CIPHER_CTX_ctrl.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
            _LIB.append((L, ruta))
            return _LIB[0]
        except (OSError, AttributeError) as e:
            ultimo = e
    raise OSError(f"No se encontró libcrypto ({ultimo})")


_SET_IVLEN, _GET_TAG, _SET_TAG = 0x9, 0x10, 0x11


def _correr(cifrar, llave, nonce, datos, aad):
    L, _ = _lib()
    ctx = L.EVP_CIPHER_CTX_new()
    if not ctx:
        raise OSError("EVP_CIPHER_CTX_new")
    try:
        init = L.EVP_EncryptInit_ex if cifrar else L.EVP_DecryptInit_ex
        upd = L.EVP_EncryptUpdate if cifrar else L.EVP_DecryptUpdate
        fin = L.EVP_EncryptFinal_ex if cifrar else L.EVP_DecryptFinal_ex
        if init(ctx, L.EVP_aes_256_gcm(), None, None, None) != 1:
            raise OSError("init")
        if L.EVP_CIPHER_CTX_ctrl(ctx, _SET_IVLEN, len(nonce), None) != 1:
            raise OSError("ivlen")
        if init(ctx, None, None, bytes(llave), bytes(nonce)) != 1:
            raise OSError("init clave")
        n = ctypes.c_int(0)
        if aad and upd(ctx, None, ctypes.byref(n), bytes(aad), len(aad)) != 1:
            raise OSError("aad")
        if cifrar:
            cuerpo, tag = bytes(datos), None
        else:
            if len(datos) < 16:
                raise EtiquetaInvalida()
            cuerpo, tag = bytes(datos[:-16]), bytes(datos[-16:])
        sal = ctypes.create_string_buffer(len(cuerpo) + 32)
        if upd(ctx, sal, ctypes.byref(n), cuerpo, len(cuerpo)) != 1:
            raise OSError("update")
        total = n.value
        if not cifrar:
            tb = ctypes.create_string_buffer(tag, 16)
            if L.EVP_CIPHER_CTX_ctrl(ctx, _SET_TAG, 16, tb) != 1:
                raise OSError("set tag")
        n2 = ctypes.c_int(0)
        ok = fin(ctx, ctypes.byref(sal, total), ctypes.byref(n2))
        if ok != 1:
            if not cifrar:
                raise EtiquetaInvalida()
            raise OSError("final")
        total += n2.value
        r = sal.raw[:total]
        if cifrar:
            tb = ctypes.create_string_buffer(16)
            if L.EVP_CIPHER_CTX_ctrl(ctx, _GET_TAG, 16, tb) != 1:
                raise OSError("get tag")
            r += tb.raw
        return r
    finally:
        L.EVP_CIPHER_CTX_free(ctx)


def cifrar(llave, nonce, datos, aad=b""):
    return _correr(True, llave, nonce, datos, aad)


def descifrar(llave, nonce, datos, aad=b""):
    return _correr(False, llave, nonce, datos, aad)


def disponible():
    try:
        _lib()
        return True
    except OSError:
        return False
