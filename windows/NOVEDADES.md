## Ctrl-P v1.9 (Windows)

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
