"""Version de la app de la tablet y sus novedades (buildozer toma la version de aqui; GitHub arma version.json)."""

VERSION_INTERNA = "1.3.1"

CAMBIOS = [
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
