@echo off
if not "%~1"=="_abierto" (
    cmd /k ""%~f0" _abierto"
    exit /b
)
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title Creando Ctrl-P portable

echo.
echo  ==========================================================
echo    Creando la version PORTABLE de Ctrl-P
echo    Control de avance detallado de obra
echo    (solo se hace una vez; tarda unos minutos)
echo  ==========================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo  No se encontro Python. Instalalo desde https://www.python.org/downloads/
    echo  y marca la casilla "Add python.exe to PATH" durante la instalacion.
    echo.
    goto :fin
)

python -c "import sys; sys.exit(0 if sys.maxsize > 2**32 else 1)"
if errorlevel 1 (
    echo  Tu Python es de 32 bits. Instala Python de 64 bits desde python.org.
    goto :fin
)

python -c "import tkinter" 2>nul
if errorlevel 1 (
    echo  A tu Python le falta "tcl/tk". Reinstala Python desde python.org
    echo  dejando marcada la opcion "tcl/tk and IDLE".
    goto :fin
)

if not exist "CtrlP.py" goto :faltan
if not exist "ctrlp_core.py" goto :faltan
if not exist "ctrlp_excel.py" goto :faltan
if not exist "ctrlp_ui.py" goto :faltan
if not exist "ctrlp_planos.py" goto :faltan
if not exist "ctrlp_render.py" goto :faltan
if not exist "ctrlp_actualizar.py" goto :faltan
if not exist "ctrlp.ico" goto :faltan
if not exist "fuentes\Inter-Regular.ttf" goto :faltan

echo [1/3] Instalando herramientas (CustomTkinter, openpyxl, lxml, Pillow, PyMuPDF, cryptography, PyInstaller)...
rem Las mismas que usa GitHub al publicar (.github/workflows/publicar_windows.yml)
python -m pip install --upgrade --quiet --disable-pip-version-check "customtkinter>=5.2,<6" openpyxl lxml pillow "pymupdf>=1.24,<2" cryptography pyinstaller
if errorlevel 1 (
    echo  Error instalando las librerias. Revisa tu conexion a internet.
    goto :fin
)

echo [2/3] Armando el programa (puede tardar 2 a 5 minutos)...
python -m PyInstaller --noconfirm --clean --windowed --onedir ^
    --name Ctrl-P ^
    --icon "%~dp0ctrlp.ico" ^
    --collect-all customtkinter ^
    --collect-all pymupdf ^
    --collect-submodules cryptography ^
    --hidden-import lxml.etree ^
    --hidden-import PIL._tkinter_finder ^
    --hidden-import PIL.ImageTk ^
    --add-data "%~dp0fuentes;fuentes" ^
    --add-data "%~dp0ctrlp.ico;." ^
    --distpath "%~dp0_dist" --workpath "%~dp0_build" --specpath "%~dp0_build" ^
    CtrlP.py
if errorlevel 1 (
    echo.
    echo  Hubo un error armando el programa. Copia el texto de arriba y envialo.
    goto :fin
)

echo [3/3] Ordenando la carpeta portable...
rem Desde la v1.1 la carpeta se llama Ctrl-P_portable (sin numero): el programa se actualiza solo.
set "DESTINO=%~dp0Ctrl-P_portable"
rem Si ya existia, se reemplaza solo el programa: la carpeta CTRL-P DOC (proyectos) se conserva
if exist "%DESTINO%\_internal" rmdir /s /q "%DESTINO%\_internal"
if not exist "%DESTINO%" mkdir "%DESTINO%"
robocopy "%~dp0_dist\Ctrl-P" "%DESTINO%" /E /XD "CTRL-P DOC" /NFL /NDL /NJH /NJS /NP >nul
rmdir /s /q "%~dp0_dist" 2>nul
rmdir /s /q "%~dp0_build" 2>nul

echo.
echo  ==========================================================
echo    LISTO
echo.
echo    Carpeta portable:  Ctrl-P_portable
echo    Programa:          Ctrl-P.exe  (doble clic)
echo.
echo    Podes copiar esa carpeta COMPLETA a una USB o a otra PC
echo    con Windows 10/11. No necesita Python ni instalacion.
echo    Tus proyectos .ctrlp se guardan donde vos elijas.
echo  ==========================================================
echo.
explorer "%DESTINO%"
echo  Ya podes cerrar esta ventana.
goto :eof

:faltan
echo  Faltan archivos junto a este .bat.
echo  Descomprimi el .zip COMPLETO (con la carpeta fuentes) y ejecuta
echo  este .bat desde esa carpeta.
goto :fin

:fin
echo.
echo  El proceso se detuvo. Revisa el mensaje de arriba.
