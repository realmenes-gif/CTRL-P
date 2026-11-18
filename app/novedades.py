"""Version de la app de la tablet y sus novedades (buildozer toma la version de aqui; GitHub arma version.json)."""

VERSION_INTERNA = "1.4.8"

CAMBIOS = [
    ("1.4.8", [
        "Informes: en las partidas con suministro ya cobrado (p. ej. Tabiquería al 21/10), lo registrado después cuenta × el complemento de lo cobrado en cada hito (61 % → × 39 %) contra lo contractual; lo que pasa es no cobrable. Da lo mismo que las actas de la computadora (el dato se pone allá, en Formatos de actas).",
    ]),
    ("1.4.7", [
        "Informes con «Solo lo contractual» topa por hito: si lo contractual son 50 M2, no se cobran más de 50 de estructura, 50 de lámina, etc. Igual que en la computadora.",
    ]),
    ("1.4.6", [
        "Tablas (Informes, Presupuesto y otras): ahora se deslizan de lado con el dedo para ver las columnas de la derecha. Antes el gesto horizontal no hacía nada.",
    ]),
    ("1.4.5", [
        "Informes: «Monto período» y «% aporte» van junto a «Período», a la vista sin deslizar la tabla (antes quedaban al final, fuera de la pantalla).",
    ]),
    ("1.4.4", [
        "Informes: con «Solo lo contractual» apagado, el excedente (lo ejecutado por encima de lo contractual) ahora sí suma en los montos del período y acumulados. Encendido, siguen siendo solo los montos cobrables.",
    ]),
    ("1.4.3", [
        "Datos fijos: cada edificio es una sola tarjeta dibujada; al tocar una casilla aparece la casilla para escribir, y Enter pasa a la siguiente. Abre unas 6 veces más rápido (de unos 970 controles a 185).",
        "Datos fijos › Tramos/Equipos: los renglones de ubicación con «+ Tramo» se dibujan sin un control por renglón.",
        "Ubicaciones: cada edificio es una sola tarjeta dibujada (nombre, Editar, Eliminar, + tramo y niveles). La página se arma al instante.",
    ]),
    ("1.4.2", [
        "Informes por ubicación más rápidos (edificios y niveles se leen una sola vez por cálculo).",
    ]),
    ("1.4.1", [
        "Ceros: en Registro de avance y Datos fijos, un 0 escrito se borra solo al salir de la casilla y no cuenta como avance; los 0 ya guardados se ven como casilla vacía.",
    ]),
    ("1.4.0", [
        "Informes: los botones de opciones van en una barra que se despliega con «Opciones ▼». Cerrada, muestra en una línea lo elegido (período, detalle, vista y qué se muestra) y la tabla tiene mucho más lugar.",
        "Informes: «Ocultar resumen» pasó a la barra de arriba y los indicadores debajo de la gráfica quedan del alto de su texto (la gráfica no cambia).",
        "Las casillas de texto (por ejemplo la fecha «Hasta») muestran el texto siempre centrado y entero (antes podía verse medio número).",
    ]),
    ("1.3.9", [
        "En línea: al abrir el proyecto desde la lista, si el administrador subió una versión nueva, se trae sola (tus avances sin enviar se mantienen).",
    ]),
    ("1.3.8", [
        "Datos fijos: si la partida ya tiene toda su cantidad repartida, solo se ven las ubicaciones con cantidad asignada; «Mostrar todas» las muestra todas.",
        "errores.log se manda solo al administrador cuando aparece un error (sin claves ni datos del proyecto).",
    ]),
    ("1.3.7", [
        "En línea: si Google tarda y responde sin los datos (por ejemplo al abrir un proyecto), Ctrl-P lo reintenta solo una vez y, si sigue igual, avisa con un mensaje claro en vez de dar error.",
    ]),
    ("1.3.6", [
        "Registro de avance: si la partida ya tiene toda su cantidad repartida en Datos fijos, solo se ven las ubicaciones con cantidad asignada (y las que ya tienen avance); el botón «Mostrar todas» las muestra todas.",
    ]),
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
