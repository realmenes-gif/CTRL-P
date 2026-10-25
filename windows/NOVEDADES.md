## Ctrl-P v1.17 (Windows)

- En línea: «Abrir» desde la lista siempre trae la última versión de Google. Si la copia de esta computadora es más vieja se baja la nueva; si además tiene cambios sin subir, pregunta cuál abrir y la otra queda guardada como copia (no se pierde nada).
- En línea (administrador): botón «Reemplazar la de Google…» para que el archivo abierto pase a ser la versión en línea (por ejemplo si lo editaste sin internet o abriste una copia local). La anterior queda guardada en Google.
- En línea (administrador): al sincronizar, si en Google hay una versión más nueva que la abierta, pregunta: «Abrir la de Google» o «Reemplazarla con la mía» (antes daba error).
- En línea (usuarios): al abrir el proyecto desde la lista se trae solo lo nuevo que aprobó el administrador; sus avances sin enviar se mantienen.
- La tarjeta del proyecto abierto muestra la versión abierta y la que está en Google (con aviso si hay una más nueva).

### Incluye lo de la v1.16

- Memorias con formato propio: cada semana dice solo «SEM 04 AL 10 SEP» (o «SEM 28 AGO AL 03 SEP»), así se lee completo en la columna; antes el título largo quedaba cortado y parecía decir «EJECUTADO ESTE PERÍODO».

### Incluye lo de la v1.15

- Datos fijos: si la partida ya tiene toda su cantidad repartida, solo se ven las ubicaciones con cantidad asignada; «Mostrar todas» las muestra todas y «Solo las asignadas» vuelve a ocultarlas.
- Memorias de cálculo y «Corte + memorias»: antes de sacarlas aparece la lista para marcar cuáles van (un clic en la fila). «Quitar las de pago por hitos» las saca de una vez; lo desmarcado se recuerda mientras Ctrl-P esté abierto.
- errores.log se manda solo: cuando aparece un error, Ctrl-P envía lo nuevo del registro al administrador (sin claves ni datos del proyecto), así no hace falta mandarlo a mano.
- Ubicaciones: ya no salen errores «invalid command name …entry» al crear o editar edificios.

### Incluye lo de la v1.14

- En línea: si Google tarda y responde sin los datos (por ejemplo al abrir un proyecto), Ctrl-P lo reintenta solo una vez y, si sigue igual, avisa con un mensaje claro en vez de dar error.

### Incluye lo de la v1.13

- Informes ya no se queda «No responde» al seleccionar una fila de la tabla (las tres partes de la tabla se pasaban la selección entre ellas sin parar).

### Incluye lo de la v1.12

- Registro de avance: si la partida ya tiene toda su cantidad repartida en Datos fijos, solo se ven las ubicaciones con cantidad asignada (y las que ya tienen avance); el botón «Mostrar todas» las muestra todas.

### Incluye lo de la v1.11

- Memorias: la vereda va por sector (celda combinada) con el número de cada tramo; las actividades por hitos del formato que todavía no tienen hitos cargados salen igual con los 4 hitos (40/20/25/15) y sus requisitos.
- Memorias: sin cantidad de diseño, las columnas de diseño y % quedan vacías en vez de 0.

### Incluye lo de la v1.10

- Memorias de cálculo con el formato propio de cada actividad (según «formatos de memorias»): por espacio o edificio, edificio con sus niveles, niveles en sub-columnas, secciones por nivel con tipos o equipos, sectores y tramos, fachadas con costo y pago por hitos con sus requisitos y nota. Las actividades sin formato propio siguen con el general.
- En todas: cantidad de diseño, anterior, este período (por semana, o «ESTE PERÍODO» en el corte de estimación), acumulado y pendiente, más las columnas especiales de cada formato (% de avance, costo unitario, ejecutado por hito…). El cálculo es el mismo; encabezado con logos y sin firmas.

### Incluye lo de la v1.9

- En línea: las ventanas de espera («Consultando…», «Bajando…») tienen «Cancelar» y la X funciona; después de 5 segundos muestran cuánto llevan. Lo que sube o envía cambios no se cancela, para no dejarlo a medias.
- En línea: si Google no responde, avisa en 1 minuto (antes podía quedarse esperando) y anota en errores.log cuánto tardó cada consulta.

### Incluye lo de la v1.8

- En línea: Ctrl-P ya trae puestos los datos del servidor de Google. Cada persona solo inicia sesión con su cuenta de Google y escribe la clave del proyecto (ya no aparece «Configurar…»).

### Incluye lo de la v1.7


- Informes ya no se queda «No responde»: los ajustes automáticos de tamaño (texto, tarjetas y tabla) tienen un freno y la tabla no empuja el tamaño de la ventana.
- Si el programa deja de responder, errores.log anota qué parte se estaba moviendo.

### Incluye lo de la v1.6

- **En línea con Google** (nueva sección «En línea»): cada usuario entra con su cuenta de Google, pide acceso y abre el proyecto con la clave del proyecto. Sus cambios se envían y quedan pendientes de aprobación (en naranja con ⏳ en Informes) hasta que el administrador los acepta uno por uno o con «Seleccionar todo». Lo rechazado queda archivado y cada usuario recibe el aviso de qué se aceptó y qué no. Los proyectos viajan cifrados a tu Google Drive.
- **Memorias por filas** en las actividades con sectores o tramos: el sector en una celda combinada, «No.» con cada tramo y las mismas columnas que las demás.
- Informes: sin el espacio vacío entre «% aporte» y «Período»; la barra horizontal solo aparece cuando hace falta.

### Incluye lo de la v1.5

- Cortes semanales a elección (por defecto de viernes a jueves): en Proyecto › Datos del proyecto o tocando «Semanas: …» en Informes. Se usan en «+ Por semana» y en las memorias de cálculo.
- Corte de estimación: «Corte + memorias» agrega las memorias de cálculo con una sola columna «ESTE PERÍODO» (la suma del período, sin semanas). Las de «Memorias de cálculo» siguen con el desglose por semana.
- Memorias: el cuadro de observaciones queda en blanco.
- Informes: opciones en orden (fechas, vista, detalle, qué mostrar); al tocar varias seguidas se calcula una sola vez.
- Si el programa deja de responder, queda anotado en errores.log dónde se quedó.

### Incluye lo de la v1.4

- **Instalador** (Ctrl-P_instalador.exe): se instala para tu usuario sin pedir administrador, con acceso en el menú Inicio y en el escritorio, doble clic en los proyectos .ctrlp y desinstalador. Instalado, los proyectos y exportaciones van a Documentos\CTRL-P DOC. Se sigue actualizando solo desde el programa.
- Informes: la barra horizontal solo aparece cuando hay columnas que desplazar (antes el programa se podía quedar «No responde» al tocarla).

### Incluye lo de la v1.3

- Memorias de cálculo: con un solo nivel ya no sale la columna TOTAL extra (la cantidad de diseño ya es el total), y las áreas exteriores van en la misma columna que el nivel I.

### Incluye lo de la v1.2

- Informes › **Memorias de cálculo**: una pestaña por cada actividad del filtro elegido («Mostrar»), con el formato de la memoria de cálculo de estimación: logos, datos del proyecto, período, datos de la partida, un bloque por tipo (ej. MURO / TABIQUERÍA / TRASDOSADO) con la cantidad de diseño por edificio y nivel, el período anterior, cada semana y lo pendiente, y el resumen para estimación.
- Las memorias llevan fórmulas de Excel (totales, subtotales, pendientes, resumen y datos de la partida); las cantidades salen de los datos fijos y del registro de avance.
- Semanas cortadas cada 7 días desde el primer día del período, incluidos el primero y el último (ej. 16–22 y 23–29 de octubre).
- «Solo memorias» saca un archivo liviano; «Informe + memorias» las agrega al informe de siempre. Respetan «Ver solo lo contractual».

Descarga: **Ctrl-P_instalador.exe** (recomendado) o **Ctrl-P_portable.zip** (descomprimir y abrir Ctrl-P.exe). Si ya tenés la v1.1 o posterior, el programa se actualiza solo.
