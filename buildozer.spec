[app]
title = Ctrl-P
package.name = ctrlp
package.domain = com.consorciohospitaltocoa
source.dir = app
source.include_exts = py,png,jpg,ttf,txt,json
source.exclude_dirs = __pycache__
version = 1.2.1
requirements = python3,kivy==2.3.1,pillow,openpyxl,et_xmlfile,sqlite3,openssl,pyjnius,android,certifi
orientation = landscape, landscape-reverse
fullscreen = 0
icon.filename = recursos/icono.png
presplash.filename = recursos/presplash.png
android.presplash_color = #EEF2F7
android.permissions = INTERNET, MANAGE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE
android.api = 34
android.minapi = 30
android.ndk = 28c
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = True
android.release_artifact = apk
android.debug_artifact = apk
p4a.branch = v2026.05.09

[buildozer]
log_level = 2
warn_on_root = 0
