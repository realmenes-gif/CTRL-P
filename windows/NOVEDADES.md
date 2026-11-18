## Ctrl-P v1.27 (Windows)

- Informes › «Generar actas»: con el formato Excel de la actividad (por ejemplo, el formulario de liberación de Tabiquería) saca un acta por edificio, nivel y tipo, todas en un libro (una hoja por acta). Eliges el formato, el corte anterior, el período, la fecha del acta, el primer número de registro y la enmienda; cada hito muestra lo contractual, el anterior (cantidad y %), lo del período, la enmienda con tope en lo contractual, el equivalente a cobrar y lo pendiente. Ctrl-P recuerda el último corte y el último número.
- Proyecto › «Formatos de actas»: cargas el Excel de cada actividad y eliges sus partidas, el código del registro, la enmienda y la nota de observaciones. El formato queda guardado dentro del proyecto.

### Incluye lo de la v1.26

- Informes, Exportar y Memorias: con «Solo lo contractual» apagado, el excedente (lo ejecutado por encima de lo contractual) ahora sí suma en los montos del período y acumulados. Encendido, siguen siendo solo los montos cobrables. El excedente se sigue mostrando aparte.

### Incluye lo de la v1.25

- Registro de avance: la barra de desplazamiento horizontal queda abajo de la tabla, fija y siempre visible, fina y más oscura. Ya no tapa los títulos de las fechas.

### Incluye lo de la v1.24

- Datos fijos: cada edificio es una sola tarjeta dibujada (como la tabla de Registro); al hacer clic en una casilla aparece la casilla para escribir. Enter, Tab y las flechas pasan a la siguiente, también a la del edificio siguiente. La 06.03 abre en 0.4 s en vez de 1 s, con un tercio de los controles.
- Datos fijos › Tramos/Equipos: la lista de ubicaciones con «+ Tramo» se dibuja en un solo lienzo; la 17.02.02 abre en la mitad del tiempo.
- Ubicaciones: cada edificio es una sola tarjeta dibujada (nombre, Editar, Eliminar, + tramo y niveles). La página abre en 0.2 s en vez de 0.9 s, y Refrescar tarda 0.08 s en vez de 0.7 s.
- Apariencia: se quitó el interruptor «Usar la tabla clásica»; Registro de avance usa siempre la tabla nueva.

### Incluye lo de la v1.23

- Registro de avance con tabla nueva (virtual): solo se dibujan las filas que se ven. La 06.03 (374 filas) abre en 0.2 s en vez de 2.5–3 s, y deslizar y escribir son instantáneos aunque la partida tenga cientos de filas.
- La tabla ocupa el resto de la pantalla y se desliza por dentro; la tarjeta de la partida queda arriba y los títulos de columna quedan siempre a la vista.
- Se escribe igual: tocás la casilla y escribís; Enter o ↓ bajan a la siguiente, ↑ sube. Al bajar con Enter se selecciona el número (escribir lo reemplaza).
- Historial completo, niveles que se abren y cierran, Fechas con avance, Observaciones, «+ tramo», los colores y los cálculos funcionan igual.

### Incluye lo de la v1.22

- Registro de avance · «Historial completo»: a la izquierda queda fijo Ubicación, Contractual, Acum. ant., Acum. total, % avance y Saldo; a la derecha solo los días, en orden cronológico, y es lo único que se desliza en horizontal.
- Historial completo: un clic en un día lo vuelve editable en su misma columna (pasa a ser la fecha de registro y los totales se recalculan a esa fecha); las columnas no se mueven.
- Historial completo: la lista de partidas se oculta para dar lugar a los días; «☰ Partidas» la muestra u oculta. Al volver a «Día» vuelve sola.
- Observaciones: el interruptor empieza apagado cada vez que se abre Ctrl-P.
- Niveles cerrados: se abren los que tienen avance en la fecha que se ve (antes se iban sumando los de otras fechas); lo que abrís o cerrás a mano se recuerda.

### Incluye lo de la v1.21

- Memorias de cálculo unas 3 veces más rápidas (64 memorias: de 9 a 3 segundos). El Excel sale igual.
- Exportar informe a Excel e Informes «Detallado por ubicación» más rápidos (edificios y niveles se leen una sola vez por cálculo).
- Datos fijos: abrir una partida grande pasa de 2–2.5 a menos de 1 segundo. Las casillas de cantidad son más livianas (cuadradas, con el mismo «Sin asignar»).
- Ubicaciones: entrar y Refrescar más rápido (las etiquetas de niveles se dibujan de forma liviana).
- Barras de desplazamiento: se dibujan una sola vez cuando la ventana queda libre (antes obligaban a reacomodar todo varias veces al armar cada página).
- Registro de avance: en partidas con mucho detalle (más de 40 filas para escribir), los niveles sin avance en la fecha quedan cerrados en una línea con sus totales y se abren con un clic en el nombre; su detalle se arma recién al abrirlos. Los niveles con avance ese día quedan abiertos.

### Incluye lo de la v1.20

- Registro de avance: «Semana» y «Mes» se reemplazan por «Historial completo». Muestra lo de cada día con avance de la partida, fila por fila, a la derecha de los totales (del más reciente al más viejo) y se desliza en horizontal. Solo se escribe en «Del día», que es la fecha de registro; un clic en la fecha de una columna te lleva a ese día.
- Se quitó el interruptor «Ver otras fechas (4)»: lo reemplaza «Historial completo».
- Ceros: en Registro de avance y Datos fijos, un 0 escrito se borra solo al salir de la casilla y no cuenta como avance. Los 0 que ya estaban guardados se ven como casilla vacía y ya no aparecen en «Fechas con avance» ni marcan la partida con ✓.

### Incluye lo de la v1.19

- Registro de avance: «Ver otras fechas» (en la barra de abajo) agrega, al lado de «Del día», lo que ingresaste en las 4 fechas anteriores con avance de esa partida, fila por fila, para comparar mientras escribís. Un clic en la fecha de la columna te lleva a ese día. Se ingresa igual que siempre en «Del día».

### Incluye lo de la v1.18

- Pantallas extra (HDMI, televisor, proyector): al pasar la ventana de una pantalla a otra ya no se pone transparente ni se pega (Ctrl-P ya no reescala todo al cambiar de monitor; de ahí venía el error «invalid command name …dropdownmenu»).
- Apariencia › «Tamaño de letra y controles» (90 % a 200 %): agranda letras, tablas, botones y menú para verse bien en monitores grandes. Se aplica reiniciando Ctrl-P (lo hace solo, con el mismo proyecto).
- Registro de avance: «Ver» Día · Semana · Mes. En Semana y Mes se ve lo ejecutado en todo el período (columna «De la semana» / «Del mes») y solo se puede mirar; para escribir o corregir se vuelve a «Día». Las flechas ‹ › avanzan de a un día, una semana o un mes.
- Registro de avance: botón «Fechas con avance ▾» con la lista de los días en que la partida tiene avance (cantidad y ubicaciones); un clic lleva a esa fecha.
- Registro de avance más rápido: la tabla se arma mucho más rápido y por tandas (lo que se ve aparece enseguida), al escribir solo se recalcula esa fila y «Guardar» actualiza los totales sin volver a armar la tabla.
- Todo el programa más liviano: los avisos de tamaño de la ventana ya no se reparten a cada control (eran miles de llamadas al armar tablas grandes).

### Incluye lo de la v1.17

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
