# Ctrl-P v1 para Android (tablet)

App de control de avance de obra para tablets Android 11 o más reciente. Usa los mismos archivos `.ctrlp`
que la versión de escritorio (los módulos `ctrlp_core.py` y `ctrlp_excel.py` son los mismos).

## Obtener el APK
Cada cambio que se sube a la rama `main` compila el APK automáticamente en GitHub:
**Actions → Compilar APK → la última ejecución → Artifacts → Ctrl-P-APK** (un .zip con el .apk adentro).

## Instalar en la tablet
1. Copiar el `.apk` a la tablet y abrirlo (Android pide permitir «instalar apps de origen desconocido»).
2. Al abrir Ctrl-P por primera vez, dar el permiso «Administrar todos los archivos»: así abre y guarda los
   proyectos en `Documentos/CTRL-P DOC`, igual que en la computadora.

## Estructura
- `app/` código de la app (Kivy). `main.py` arranca; `ctrlp_core.py` y `ctrlp_excel.py` son los del escritorio.
- `recursos/` ícono y pantalla de inicio.
- `buildozer.spec` configuración del APK.
