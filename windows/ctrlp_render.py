"""Ctrl-P - render de planos PDF en paralelo (un proceso por nucleo, cada uno dibuja una franja de la pagina).

Modulo liviano a proposito: los procesos hijos solo importan esto y pymupdf (no la interfaz)."""
import os
from concurrent.futures import ProcessPoolExecutor

NUCLEOS = max(1, os.cpu_count() or 1)
MIN_PIXELES_PARALELO = 6_000_000      # por debajo de esto no vale la pena repartir

_pool = None


def _pool_procesos():
    global _pool
    if _pool is None:
        _pool = ProcessPoolExecutor(max_workers=NUCLEOS)
    return _pool


def cerrar(forzar=False):
    """Cierra los procesos que dibujan los planos. Con forzar, los termina de una vez (al actualizar)."""
    global _pool
    if _pool is not None:
        procs = list((getattr(_pool, "_processes", None) or {}).values())
        _pool.shutdown(wait=False, cancel_futures=True)
        _pool = None
        if forzar:
            for pr in procs:
                try:
                    pr.terminate()
                except Exception:
                    pass


def _franja(fuente, es_ruta, pagina, zoom, r0, r1, memoria, ancho):
    """En el proceso hijo: dibuja las filas [r0, r1) de la pagina directo en la memoria compartida."""
    import pymupdf
    from multiprocessing import shared_memory
    d = pymupdf.open(fuente) if es_ruta else pymupdf.open(stream=fuente, filetype="pdf")
    shm = shared_memory.SharedMemory(name=memoria)
    try:
        page = d[pagina]
        rect = page.rect
        clip = pymupdf.Rect(rect.x0, rect.y0 + r0 / zoom, rect.x1, rect.y0 + r1 / zoom)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=clip, alpha=False)
        filas = min(pix.height, r1 - r0)
        w = min(pix.width, ancho)
        fuente_b = pix.samples_mv if hasattr(pix, "samples_mv") else pix.samples
        st = pix.stride
        base = r0 * ancho * 3
        if w == ancho and st == ancho * 3:
            shm.buf[base:base + filas * st] = fuente_b[:filas * st]
        else:
            for y in range(filas):
                shm.buf[base + y * ancho * 3: base + y * ancho * 3 + w * 3] = fuente_b[y * st: y * st + w * 3]
        return filas
    finally:
        shm.close()
        d.close()


def renderizar(fuente, pagina, zoom, es_ruta=False):
    """Pagina PDF -> PIL.Image RGB, repartiendo el trabajo entre todos los nucleos si la pagina es grande.
    fuente: ruta del archivo (es_ruta=True) o los bytes del PDF."""
    import pymupdf
    from PIL import Image
    d = pymupdf.open(fuente) if es_ruta else pymupdf.open(stream=fuente, filetype="pdf")
    try:
        page = d[pagina]
        w = int(round(page.rect.width * zoom))
        h = int(round(page.rect.height * zoom))
        if NUCLEOS < 2 or w * h < MIN_PIXELES_PARALELO:
            pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
            return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    finally:
        d.close()
    from multiprocessing import shared_memory
    shm = None
    try:
        n = min(NUCLEOS, 16)
        cortes = [round(h * k / n) for k in range(n + 1)]
        shm = shared_memory.SharedMemory(create=True, size=w * h * 3)
        shm.buf[:w * h * 3] = b"\xff" * (w * h * 3)
        pool = _pool_procesos()
        trabajos = [pool.submit(_franja, fuente, es_ruta, pagina, zoom, cortes[k], cortes[k + 1], shm.name, w)
                    for k in range(n)]
        for tr in trabajos:
            tr.result()
        img = Image.frombytes("RGB", (w, h), bytes(shm.buf[:w * h * 3]))
        shm.close()
        shm.unlink()
        return img
    except Exception:
        if shm is not None:
            try:
                shm.close()
                shm.unlink()
            except Exception:
                pass
        cerrar()
        d = pymupdf.open(fuente) if es_ruta else pymupdf.open(stream=fuente, filetype="pdf")
        try:
            pix = d[pagina].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
            return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        finally:
            d.close()
