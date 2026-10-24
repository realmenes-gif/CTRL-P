"""Version de la app de la tablet y sus novedades (buildozer toma la version de aqui; GitHub arma version.json)."""

VERSION_INTERNA = "1.3.5"

CAMBIOS = [
    ("1.3.5", [
        "Actualizaciones: al haber una versión nueva, «Descargar» abre el navegador con el APK; se instala encima tocando el archivo descargado (los proyectos y la sesión se mantienen).",
    ]),
    ("1.3.4", [
        "En línea: las ventanas de espera («Consultando…», «Bajando…») tienen «Cancelar» y la X funciona; después de 5 segundos muestran cuánto llevan. Lo que sube o envía cambios no se cancela, para no dejarlo a medias.",
        "En línea: si Google no responde, avisa en 1 minuto (antes podía quedarse esperando) y anota en errores.log cuánto tardó cada consulta.",
    ]),
    ("1.3.3", [
        "En línea: la ventana de la clave se cierra al tocar «Aceptar» o «Cancelar» (antes se quedaba en pantalla aunque el proyecto ya se había abierto).",
        "En línea: un doble toque en «Abrir» o «Aceptar» ya no abre la ventana dos veces.",
    ]),
    ("1.3.2", [
        "En línea: al escribir la clave y tocar «Aceptar» el proyecto ya se abre (antes se tomaba como si se hubiera cancelado).",
        "Abrir un proyecto con usuario protegido por contraseña: ya no se cierra el proyecto al aceptar.",
    ]),
    ("1.3.1", [
        "En línea: abrir un proyecto con la clave ya no se queda pegado (el descifrado usa OpenSSL, igual de rápido que en la computadora).",
        "En línea: cada paso queda anotado en errores.log para encontrar fallas.",
    ]),
    ("1.3.0", [
        "Actualizaciones: en Apariencia › «Buscar actualizaciones» (y sola al abrir). Descarga la versión nueva, "
        "la comprueba y abre el instalador de Android; los proyectos y la sesión de Google se mantienen.",
    ]),
    ("1.2.1", [
        "En línea: ya trae puestos los datos del servidor de Google (solo se inicia sesión y se pone la clave "
        "del proyecto).",
    ]),
    ("1.2.0", [
        "Página «En línea»: iniciar sesión con Google, pedir acceso, abrir el proyecto con su clave y sincronizar. "
        "Los avances sin aprobar salen en naranja con ⏳ en Informes.",
    ]),
    ("1.1.0", [
        "Novedades de la computadora: tramos en áreas, filtro «Mostrar», verde al 100 %, semanas de viernes a "
        "jueves. Sin exportar a Excel (la app queda más liviana).",
    ]),
]
