"""
Ctrl-P - actualizaciones (igual que PdFOL)
==========================================
- Revisa la ultima version publicada en GitHub (repositorio realmenes-gif/CTRL-P, etiquetas vX.Y).
- Baja Ctrl-P_portable.zip, comprueba su SHA256 y lo descomprime en una carpeta temporal.
- Un pequeno actualizador (.cmd sin ventana) espera que Ctrl-P se cierre, reemplaza los archivos del
  programa y lo vuelve a abrir. Nunca toca la carpeta «CTRL-P DOC» (proyectos, master, exportaciones)
  ni la configuracion del usuario (esta en %APPDATA%\\Ctrl-P).
"""

import hashlib
import os
import re
import shutil
import subprocess
import sys

REPO_GITHUB = "realmenes-gif/CTRL-P"
ZIP_PORTABLE = "Ctrl-P_portable.zip"
EXE_PORTABLE = "Ctrl-P.exe"
CARPETA_DOCS = "CTRL-P DOC"


class Cancelado(Exception):
    pass


def version_tupla(texto):
    nums = re.findall(r"\d+", str(texto or ""))
    return tuple(int(x) for x in nums[:4]) or (0,)


def ultima_version(version_actual, timeout=6):
    """Datos de la ultima version publicada para Windows (la «latest» del repositorio) o error."""
    import json
    import urllib.error
    import urllib.request
    url = f"https://api.github.com/repos/{REPO_GITHUB}/releases/latest"
    req = urllib.request.Request(url, headers={"User-Agent": f"Ctrl-P/{version_actual}",
                                               "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:          # todavia no hay ninguna version publicada
            return None
        raise
    zip_, sha = None, None
    for a in d.get("assets") or []:
        if a.get("name") == ZIP_PORTABLE:
            zip_ = a
        elif a.get("name") == ZIP_PORTABLE + ".sha256":
            sha = a
    return {"tag": d.get("tag_name", ""), "notas": d.get("body") or "", "web": d.get("html_url", ""),
            "zip": zip_, "sha": sha}


def hay_version_nueva(info, version_actual):
    return (bool(info and info.get("zip")) and str(info.get("tag", "")).startswith("v")
            and version_tupla(info["tag"]) > version_tupla(version_actual))


def notas_en_puntos(notas):
    """Los puntos de las notas del release (lineas que empiezan con «- »), sin el formato de Markdown."""
    puntos = []
    for ln in (notas or "").splitlines():
        ln = ln.strip().replace("**", "").replace("`", "")
        if ln.startswith(("- ", "* ")):
            puntos.append(ln[2:].strip())
        elif puntos and ln and not ln.startswith("#") and not ln.lower().startswith("descarga"):
            puntos[-1] += " " + ln
    return puntos


def descargar_actualizacion(info, carpeta, progreso=None, cancelar=None):
    """Baja el zip, comprueba el SHA256 y lo descomprime. Devuelve la carpeta que trae Ctrl-P.exe."""
    import urllib.request
    import zipfile
    os.makedirs(carpeta, exist_ok=True)
    destino = os.path.join(carpeta, ZIP_PORTABLE)
    req = urllib.request.Request(info["zip"]["browser_download_url"], headers={"User-Agent": "Ctrl-P"})
    h = hashlib.sha256()
    with urllib.request.urlopen(req, timeout=30) as r, open(destino, "wb") as f:
        total = int(r.headers.get("Content-Length") or info["zip"].get("size") or 0)
        hecho = 0
        while True:
            if cancelar is not None and cancelar.is_set():
                raise Cancelado()
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b)
            h.update(b)
            hecho += len(b)
            if progreso:
                progreso(hecho, total)
    esperado = None
    dig = info["zip"].get("digest") or ""
    if dig.startswith("sha256:"):
        esperado = dig.split(":", 1)[1].strip().lower()
    elif info.get("sha"):
        req = urllib.request.Request(info["sha"]["browser_download_url"], headers={"User-Agent": "Ctrl-P"})
        with urllib.request.urlopen(req, timeout=20) as r:
            esperado = r.read().decode("ascii", "ignore").split()[0].strip().lower()
    if not esperado:
        raise ValueError("La versión publicada no trae su suma SHA256: no se instala por seguridad.")
    if h.hexdigest().lower() != esperado:
        raise ValueError("La descarga no coincide con su SHA256 (archivo dañado o alterado). No se instaló nada.")
    nuevo = os.path.join(carpeta, "nuevo")
    shutil.rmtree(nuevo, ignore_errors=True)
    with zipfile.ZipFile(destino) as z:
        z.extractall(nuevo)
    for raiz, _dirs, archivos in os.walk(nuevo):
        if EXE_PORTABLE in archivos:
            return raiz
    raise ValueError(f"El zip no trae {EXE_PORTABLE}.")


def carpeta_escribible(carpeta):
    try:
        p = os.path.join(carpeta, ".ctrlp_prueba_escritura")
        with open(p, "w") as f:
            f.write("ok")
        os.remove(p)
        return True
    except Exception:
        return False


def lanzar_actualizador(nuevo, carpeta_tmp):
    """Escribe y arranca el actualizador: espera que Ctrl-P se cierre, reemplaza los archivos del programa
    (sin tocar CTRL-P DOC) y vuelve a abrir Ctrl-P."""
    app_dir = os.path.dirname(sys.executable)
    pid = os.getpid()
    bat = os.path.join(carpeta_tmp, "actualizar_CtrlP.cmd")
    lineas = [
        "@echo off",
        "chcp 65001 >nul",
        "title Actualizando Ctrl-P",
        "set /a VUELTAS=0",
        ":esperar",
        f'tasklist /FI "PID eq {pid}" 2>nul | find "{pid}" >nul',
        "if errorlevel 1 goto listo_para_copiar",
        "set /a VUELTAS+=1",
        "if %VUELTAS% GEQ 30 goto forzar",
        "ping -n 2 127.0.0.1 >nul",
        "goto esperar",
        ":forzar",
        f"taskkill /F /T /PID {pid} >nul 2>nul",
        "ping -n 2 127.0.0.1 >nul",
        ":listo_para_copiar",
        f'taskkill /F /IM {EXE_PORTABLE} >nul 2>nul',
        "ping -n 2 127.0.0.1 >nul",
        f'if exist "{app_dir}\\_internal" rmdir /s /q "{app_dir}\\_internal"',
        f'robocopy "{nuevo}" "{app_dir}" /E /XD "{CARPETA_DOCS}" /R:3 /W:1 /NFL /NDL /NJH /NJS /NP >nul',
        f'start "" "{os.path.join(app_dir, EXE_PORTABLE)}"',
        f'rmdir /s /q "{os.path.join(carpeta_tmp, "nuevo")}"',
        f'del /q "{os.path.join(carpeta_tmp, ZIP_PORTABLE)}"',
        '(goto) 2>nul & del "%~f0"',
    ]
    with open(bat, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\n".join(lineas) + "\n")
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0  # SW_HIDE
    subprocess.Popen(["cmd", "/c", bat], creationflags=0x08000000 | 0x00000200, startupinfo=si,
                     close_fds=True)  # CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP: no se ve ninguna ventana
