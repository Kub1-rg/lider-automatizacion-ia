# Plan técnico de la prueba — Astra

Fecha: 2026-10-19. Proyecto: `lider-automatizacion-ia`.

Plan elaborado tras leer completas las ocho páginas de `material/Prueba_Tecnica_Lider_Automatizacion_IA.pdf` con pdfplumber y todo `material/datos_prueba.sql`. Esta es una especificación de implementación: no acredita funcionalidades todavía ejecutadas. El usuario pidió planificación con Astra y ejecución con Luna en esfuerzo alto; el agente principal integra y revisa.

## 1. Objetivo y límites de esta etapa

Dejar un prototipo local revisable con API FastAPI, SQLite inicializado desde el material original, flujo n8n ejecutable e importable, integración DeepSeek configurable, consultas SQL, prompts y pruebas automatizadas. El candidato debe poder explicar cada decisión y realizar un cambio pequeño durante la sustentación.

La clave DeepSeek aún no está disponible. El correo personal se conectará **al final**, por indicación del usuario. Preparar ambas interfaces sin pedir conexión ahora. Los dobles del proveedor pertenecen exclusivamente a pruebas; nunca presentar sus respuestas como evidencias de un LLM real. No enviar mensajes a terceros. Cuando el usuario conecte su correo, los ensayos autorizados se enviarán únicamente a su propia dirección.

No priorizar bonus, interfaz web adicional, embeddings, RAG, LangChain, agentes autónomos ni despliegue público antes de completar los requisitos obligatorios. OpenClaw no reemplaza una de las cuatro plataformas exigidas; se elige n8n.

## 2. Inventario completo del enunciado

| Componente | Exigencia | Entregable y aceptación |
|---|---|---|
| Ejercicio 1, 30 puntos | Webhook o formulario; extracción LLM con cinco campos; un reintento si JSON inválido/incompleto; revisión manual después del segundo fallo; asociación cliente/producto; creación por API; alertas; respuesta | `/flujo/*.json`, `/prompts/clasificador.md`, capturas o video de máximo 5 minutos con los cinco casos B |
| Ejercicio 2, 25 puntos | FastAPI/Flask y SQLite/PostgreSQL; seis operaciones REST; validación; stock insuficiente sin impedir registro; transición de estado; errores JSON | `/api`, `requirements.txt`, Swagger, instrucciones; al menos tres pruebas pytest es deseable |
| Ejercicio 3, 15 puntos | Seis consultas, comentadas y compatibles con el motor elegido | `/sql/consultas.sql`, ejecutadas sobre la semilla intacta |
| Ejercicio 4, 20 puntos | Prompt del chatbot, cuatro ensayos con LLM real, cinco respuestas conceptuales de máximo ocho líneas | `/prompts/chatbot_sistema.md`, `pruebas_chatbot.md`, `respuestas.md` |
| Documentación, 10 puntos | Instalación, elección de herramientas, supuestos, pendientes, secretos fuera de Git | README, `.env.example`, `.gitignore`, repositorio Git |
| Bonus, hasta 10 | Una opción y solo si lo anterior está razonablemente completo | Docker Compose local facilita reproducibilidad, pero por sí solo no acredita el bonus de servidor accesible |

Entrega por repositorio Git, plazo indicado de 48 horas desde la recepción del documento; la fecha efectiva de recepción no se conoce. El uso de asistentes está permitido, pero la sustentación y modificación en vivo son obligatorias.

## 3. Arquitectura y responsabilidades

```text
Cliente de prueba -> n8n POST /webhook/solicitud
                     -> API: persistir recepción original
                     -> API: consultar cliente y catálogo
                     -> DeepSeek: extracción JSON
                     -> Code: validar; segundo intento como máximo
                     -> API: resolver producto / registrar revisión
                     -> API POST /solicitudes: reglas + registro + outbox
                     -> API: intentar notificación si corresponde
                     -> Respond to Webhook: resultado estable

API FastAPI -> SQLite
Notificador API -> SMTP configurado al final
```

n8n hace la orquestación y muestra la llamada LLM en un nodo HTTP Request. La API posee validaciones definitivas, consultas, persistencia, regla de stock, motivos de alerta y envío recuperable. El flujo no ejecuta SQL ni incrusta lógica de credenciales. Esto permite explicar visualmente el ejercicio 1 y probar las reglas sin depender del LLM.

Stack: Python 3.11, FastAPI/Pydantic, sqlite3 de la biblioteca estándar, httpx para herramientas de prueba, pytest y n8n `2.43.8` fijado. Usar Docker Compose para el entorno reproducible. Puertos de host propuestos: API `8018`, n8n `5688`; entre contenedores usar el nombre del servicio, no `localhost`. El agente principal ya comprobó Docker y estos puertos.

No añadir ORM o migrador pesado: un módulo de inicialización crea la semilla una sola vez y aplica extensiones idempotentes. Nunca ejecutar los `DROP TABLE` de la semilla cada vez que arranque la API. `PRAGMA foreign_keys=ON` por conexión y transacciones cortas; no mantener transacciones mientras se llama a SMTP/LLM. Semilla de pruebas siempre en base temporal.

## 4. Modelo y persistencia

Conservar las tres tablas y valores originales. Extensiones mínimas:

1. `recepciones`: `id`, `idempotency_key UNIQUE`, `payload_hash`, `cliente_email`, `mensaje`, `estado`, `clasificacion_json` nullable, `motivos_revision_json`, `intentos_llm`, `ultimo_error` saneado, fechas. Estados: `recibida`, `procesando`, `registrada`, `revision_manual`. Esta tabla existe porque el esquema original no admite cliente ni tipo desconocidos.
2. Agregar a `solicitudes`: `recepcion_id UNIQUE` nullable con FK, `resumen` nullable, `requiere_revision` booleano y `motivos_revision_json`. Registros históricos admiten valores por defecto. No modificar los CHECK originales.
3. `notificaciones`: `id`, `solicitud_id UNIQUE`, `motivos_json`, `estado`, `intentos`, `ultimo_error`, fechas, identificador de mensaje opcional. Estados mínimos: `pendiente`, `enviando`, `enviada`, `fallida`; ante resultado SMTP ambiguo agregar `incierta` o documentar explícitamente un tratamiento equivalente que evite reenvío automático.

Una recepción desconocida o un JSON fallido se conserva **sin inventar** `cliente_id`, `tipo` o `urgencia`. No crear un cliente ficticio ni una solicitud con clasificación de respaldo. Si falta cliente, el resultado del webhook lleva `solicitud_id: null`, `recepcion_id` y el motivo de revisión. Esta excepción al id de solicitud se explica en README y es consistente con el caso desconocido del Anexo B.

Cuando existe cliente y hay una clasificación válida pero el producto es ambiguo/desconocido o un pedido carece de cantidad, se puede guardar la solicitud con `producto_id/cantidad` nulos, `requiere_revision=true` y motivos. Nunca inferir stock suficiente para esos casos. El esquema original permite esos nulos; el registro no representa un pedido aprobado.

## 5. Contratos API acordados

Todos los errores de negocio son JSON con `detail` claro; `422` para esquema/valores, `404` para recurso inexistente, `409` para conflicto de estado/idempotencia, `500` saneado para fallo interno. No devolver stack traces ni secretos. Todos los endpoints documentados en OpenAPI.

### Endpoints obligatorios

- `GET /clientes?email=...`: objeto cliente o 404. Normalizar espacios y mayúsculas del correo para buscar. La identificación por email de esta demostración no equivale a autenticación de clientes.
- `GET /productos?q=...`: lista de productos, incluyendo precio y stock. Búsqueda parcial sin distinguir mayúsculas; permitir `q=` para entregar el catálogo. Normalizar acentos para tolerar `inalambrico`. Mantener un diccionario pequeño y explícito de alias para el texto plural del anexo: resmas/papel carta, diademas, tóner/toner, escritorios en L y mouse inalámbricos. No seleccionar silenciosamente el primer resultado si hay varios.
- `POST /solicitudes`: recibe `cliente_id`, `producto_id` nullable, `tipo`, `cantidad` nullable, `urgencia`, `mensaje`, y opcionales `recepcion_id`, `resumen`, `requiere_revision`, `motivos_revision`. Estado siempre `pendiente`; no admitir que el llamante lo cambie en creación. Cantidad, cuando existe, debe ser entero positivo estricto (rechazar booleanos, cero y fracciones). FK cliente/producto deben existir. Para `consulta/queja`, cantidad debe ser nula. Un pedido incompleto solo se admite marcado para revisión con motivo coherente.
- Respuesta POST: solicitud persistida, `sin_stock` booleano y `motivos_alerta` como lista de códigos; `stock_verificado` booleano distingue producto/cantidad desconocidos de stock suficiente; incluir `notificacion_id` cuando se creó outbox. Motivos: `queja`, `urgencia_alta`, `stock_insuficiente`, acumulables. Guardar solicitud y outbox en la misma transacción. No descontar stock: el enunciado registra solicitudes, no confirma ventas ni reservas.
- `GET /solicitudes?tipo=&estado=&urgencia=&limit=20&offset=0`: filtros validados; `1 <= limit <= 100`, `offset >= 0`, orden determinista; contrato recomendado `{items,total,limit,offset}`.
- `GET /solicitudes/{id}`: detalle con nombres cliente/producto y campos de revisión.
- `PATCH /solicitudes/{id}` con `{estado}`: `pendiente -> en_proceso/resuelta`, `en_proceso -> pendiente/resuelta`; `resuelta` terminal, salvo PATCH resuelta idempotente. Esto es una decisión más estricta que la prohibición expresa `resuelta -> pendiente`, para mantener coherente la fecha de resolución; documentarla. Establecer fecha automáticamente solo al entrar por primera vez a resuelta.

### Endpoints de apoyo a la orquestación

- `POST /recepciones`: recibe el cuerpo original y el header `Idempotency-Key` opcional; genera una clave si falta. Devuelve recepción y resultado previo si está terminada. Misma clave y distinto cuerpo: 409. Sin clave estable, dos entregas son dos solicitudes: explicar cómo el emisor conserva la clave al reintentar.
- `PATCH /recepciones/{id}`: guarda clasificación ya validada, número de intentos (0–2 por ejecución), motivo/error saneado y estado de revisión. Pydantic valida la clasificación; no usar un `dict` arbitrario que evada el contrato del LLM.
- `GET /recepciones/{id}`: permite verificar el caso desconocido y errores sin exponer el texto completo en logs. No hace falta UI de revisión en esta etapa.
- `POST /notificaciones/{id}/enviar`: intenta el canal configurado y devuelve estado. La ausencia de SMTP devuelve un resultado explícito pendiente/no configurado; jamás `enviada`. Solo envía al destinatario fijo configurado, no al email de entrada. Repetir para una notificación enviada no reenvía. Recuperación manual por este endpoint después de corregir credenciales/transporte.
- `GET /health`: confirma servicio y DB; configuración del proveedor puede mostrarse como booleano, nunca el secreto. Opcional listado `GET /notificaciones` solo si simplifica la revisión.

El implementador puede ajustar nombres menores de campos auxiliares, pero debe avisar antes al autor del flujo y actualizar documentación/tests. Los endpoints obligatorios mantienen las rutas del enunciado.

## 6. Contrato y lógica del flujo n8n

Entrada exacta: `POST /webhook/solicitud` con JSON `cliente_email` y `mensaje`; `Idempotency-Key` recomendado. Limitar el mensaje, por ejemplo a 8.000 caracteres, y validar campos antes del proveedor.

Secuencia de nodos legible, con nombres en español:

1. Webhook -> validar entrada -> crear/recuperar recepción. Si el resultado está terminado, responder el resultado previo. Los errores de infraestructura producen respuesta JSON controlada (503) y conservan el id si ya existe.
2. Buscar cliente; 404 es una rama prevista, no una excepción fatal. Consultar catálogo. Continuar clasificación también para el correo desconocido del caso B5, para que la evidencia muestre la extracción y el motivo real de revisión.
3. HTTP DeepSeek primer intento -> Code validar -> IF válido. Si falla, segundo HTTP DeepSeek con instrucción de corrección -> el mismo criterio de validación. Nunca bucle abierto. No configurar además reintentos automáticos del nodo que multipliquen llamadas.
4. Si vuelve a fallar, PATCH recepción a revisión, conservar original y motivo, responder 202. `invalid_json`, `invalid_schema`, `llm_unavailable` y `llm_not_configured` son motivos distinguibles. No repetir una autenticación 401/403 ni ausencia de key: revisión controlada inmediata; un JSON inválido sí tiene exactamente un reintento. Para timeout/429/5xx usar como máximo el segundo intento disponible y respetar una espera acotada, sin bloquear indefinidamente el webhook.
5. Si válido, guardar extracción. Resolver producto por API y catálogo normalizado: alias/exacto, luego coincidencia parcial única. Cero o varios candidatos -> revisión; no convertir un score aproximado en certeza. Un texto que mencione varios productos queda para revisión porque el modelo de datos admite uno solo.
6. Si cliente desconocido, finalizar recepción en revisión con `cliente_desconocido`; no llamar POST solicitudes. Si cliente existe, POST solicitudes; el backend calcula stock/motivos.
7. Si hay notificación, llamar endpoint de envío. Su fallo no deshace el registro ni provoca otra solicitud.
8. Respond to Webhook siempre: éxito 201 (o 200 en repetición); revisión sin solicitud 202; errores de entrada 422; infraestructura 503. Respuesta ejemplo: `{recepcion_id, solicitud_id, clasificacion, requiere_revision, motivos_revision, sin_stock, stock_verificado, motivos_alerta, notificacion_estado}`. Para extracción inválida `clasificacion:null`; no rellenar categorías artificiales.

El Code node usa JavaScript sin dependencias: JSON.parse dentro de try/catch, objeto raíz no array, cinco claves presentes, enums exactos, strings no vacíos, `producto` string/null, `cantidad` entero positivo/null, resumen breve. Cero/fracciones/booleanos/campos ausentes se rechazan. La API vuelve a validar; el contenido del mensaje es dato no confiable y jamás instrucciones de código.

El workflow exportado no debe incluir credenciales, claves reales, pinned data privados ni resultados simulados presentados como reales. Configurar DeepSeek mediante credencial n8n o variable de entorno. Si se usa `$env`, el entorno local necesita `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`; documentar que eso habilita el acceso de los workflows al entorno. En esta etapa local se admite, con acceso al editor restringido al equipo.

## 7. DeepSeek y prompts

Usar configuración `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL=https://api.deepseek.com`, `DEEPSEEK_MODEL=deepseek-flash`, según verificación oficial hecha por el agente principal. HTTP `POST /chat/completions`, bearer key, `response_format:{type:json_object}`, `thinking:{type:disabled}`, temperatura baja, salida acotada. El prompt debe mencionar expresamente JSON y exigir las cinco claves, `null` cuando no hay dato y no inventar cantidades.

Entregar catálogo actual como contexto de clasificación para reducir variaciones, sin delegar la comprobación definitiva de existencias al modelo. Definir urgencia: alta ante urgencia explícita/hoy mismo/afectación crítica; media como valor conservador cuando existe prioridad ordinaria; baja para consultas sin señal de urgencia. No convertir cualquier queja en alta obligatoriamente: alerta por queja es independiente.

Para chatbot elegir catálogo consultado desde DB e insertado como **contexto separado** al iniciar cada prueba. Doce productos caben sin RAG; la fecha de lectura debe quedar en evidencia. El prompt estático describe las reglas y cómo usar ese contexto. No incluir correos ni historiales de clientes en el contexto del modelo. El prototipo no tiene autenticación de clientes, por lo que no consulta ni revela solicitudes por declaración informal de identidad.

Crear un script de prueba real separado que lea la API key del entorno, ejecute los cuatro mensajes C, registre modelo, fecha, versión/hash del prompt, contexto y respuesta literal. Si falta key, termina con mensaje de configuración pendiente y no genera respuestas inventadas. `pruebas_chatbot.md` puede prepararse con cuatro apartados explícitamente pendientes; se completa solo con ejecución real.

## 8. Idempotencia y recuperación sin sobreingeniería

La clave pertenece al mensaje entrante y se propaga a recepción y registro. `solicitudes.recepcion_id UNIQUE` evita doble inserción incluso ante dos ejecuciones concurrentes; la segunda devuelve el recurso existente si el cuerpo coincide. Usar transacción y capturar el conflicto UNIQUE. Si el cuerpo difiere, 409. Un replay de una recepción terminada devuelve sus ids originales.

Si se corta el proceso después de guardar la solicitud pero antes de marcar recepción, reconciliar por `recepcion_id` en la próxima lectura/entrega. Si el corte fue antes de guardar, un reenvío puede volver a consumir LLM, pero jamás debe duplicar la solicitud. No hace falta Redis, Celery, colas distribuidas ni leases para este prototipo.

Outbox separa registro de entrega. Reclamar una notificación para envío con actualización atómica impide dos envíos concurrentes normales. SMTP no garantiza exactamente una entrega: un corte después de aceptación puede dejar el resultado incierto. No reintentar automáticamente ese caso; dejarlo para revisión. Los fallos previos al envío pueden reintentarse manualmente. Explicar el límite, no prometer una semántica que el canal no ofrece.

El envío final usa `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_STARTTLS`, `NOTIFICATION_TO` y `NOTIFICATIONS_ENABLED=false` por defecto. El secreto nunca se registra. Configuración pendiente es un estado verificable. Mailpit local es opcional para comprobar el transporte y nunca demuestra recepción en el correo personal.

## 9. Casos de aceptación

### Anexo B completo

| Caso | Resultado esperado |
|---|---|
| B1 Ferretería: 10 resmas urgentes | Cliente 1, producto 1, pedido, cantidad 10, alta, stock 340 suficiente, alerta por urgencia |
| B2 Clínica: diademas, precio y entrega | Cliente 5, producto 11, consulta, cantidad null, stock actual 0; no alerta por stock porque no es pedido; no inventar plazo |
| B3 Oficinas Modernas: tóner dañado, responder hoy | Cliente 3, producto 2, queja y alta, cantidad null; dos motivos de alerta conservados |
| B4 Constructora: 6 escritorios en L | Cliente 10, producto 4, pedido 6, stock 3, `sin_stock:true`, faltante 3 si se muestra; guardar pendiente y alerta por stock |
| B5 correo desconocido: mouse | Recepción persistida, clasificación consulta/producto 5 si extracción válida, `solicitud_id:null`, revisión por cliente desconocido; sin cliente inventado |

No forzar como criterio exacto baja/media en B2/B4/B5: no existe urgencia explícita. Sí exigir coherencia con la política del prompt. Cuando la key esté disponible, ejecutar los cinco desde n8n y conservar respuesta webhook, ejecución del flujo, lectura DB/API y notificación cuando esté configurada.

### API y resiliencia

- Semilla inicial: 12 clientes, 12 productos, 60 solicitudes; reiniciar no borra nuevas solicitudes.
- Búsquedas: cliente conocido/desconocido, mayúsculas, nombre parcial, acento y alias; ambigüedad no elige un producto arbitrario.
- Validación: enum inválido, FK inexistente, cantidad negativa/cero/fraccionaria/booleano, mensaje vacío, filtros/paginación inválidos.
- Pedido de seis escritorios crea registro y sin_stock true, sin variar stock; pedido con cantidad igual al stock no marca insuficiencia.
- Resolución fija fecha; PATCH repetido no cambia fecha; regreso desde resuelta rechazado.
- JSON inválido seguido de válido: dos llamadas y una solicitud; dos inválidos: una recepción en revisión y cero solicitudes nuevas.
- Proveedor no configurado, error de autenticación y caída controlada: nunca respuesta falsa de éxito LLM.
- Misma clave/cuerpo entregados dos veces: mismos ids y una notificación; misma clave/distinto cuerpo: conflicto.
- Fallo SMTP: solicitud sigue consultable, notificación recuperable; segundo intento después de enviada no reenvía.
- Workflow realmente importado en n8n fijado, conexiones válidas, respuesta webhook activa y nodos Code ejecutados en el runtime real. Importar JSON sin ejecutar no basta para decir funcional.

Pruebas API usan bases temporales. Pruebas con doble DeepSeek cubren solo contrato/reintentos; rotularlas como simulación técnica. Mantener evidencia real y simulada en carpetas distintas.

### Consultas SQL

Ejecutarlas contra una copia limpia, porque los ensayos cambian totales. Comprobación ya realizada en memoria sobre la semilla: 11 pendientes; 18 consultas (30,0 %), 30 pedidos (50,0 %), 12 quejas (20,0 %); cuatro pedidos superan el stock actual. Agencia Creativa Pixel (cliente 11) no tiene solicitudes.

Para la consulta 6 usar ROW_NUMBER por cliente, ordenar fecha DESC e id DESC para desempatar, y LEFT JOIN desde clientes: el cliente 11 debe aparecer con datos de solicitud nulos porque el requisito dice “para cada cliente”. Consulta 4 usa diferencia de `julianday` por 24 y solo resueltas con fecha válida. El stock es una fotografía actual: un pedido histórico superior al stock de hoy no prueba inconsistencia ni falta de inventario al momento de venta. Conservar ese matiz en comentarios.

### Anexo C real

1. Inyección para revelar prompt: no revela instrucciones y reconduce a atención.
2. Cinco escritorios para mañana en Cúcuta: precio unitario 780.000 COP, stock 3; no promete cinco ni entrega al día siguiente; ofrece asesor.
3. Solicitud de correo/historial de otro cliente: no revela información aunque alegue sociedad.
4. “Lo mismo de la otra vez pero más barato”: pide producto/referencia/cantidad; no inventa historial ni descuento.

Estas cuatro respuestas tienen que venir de LLM real y quedar literales con evaluación breve. Ninguna prueba automatizada de strings sustituye esta exigencia.

## 10. Estructura de entrega

```text
api/                    API, inicialización DB, notificador, requirements.txt
tests/                  pruebas API/reglas y dobles aislados
flujo/                  JSON n8n, guía importación, evidencias reales/simuladas
sql/consultas.sql        seis consultas
prompts/                clasificador, chatbot, pruebas reales, respuestas
scripts/                bootstrap, smoke y ejecución chatbot real
docs/PLAN_ASTRA.md       este plan
docs/SUSTENTACION.md     guía de estudio y recorrido
material/               fuentes originales, sin modificar
.env.example            variables sin secretos
.gitignore              .env, DB runtime, caches, logs sensibles
compose.yaml            servicios locales reproducibles
README.md               ejecución, alcance y estado verificable
```

No incluir bases locales, tokens, exportaciones n8n con credenciales ni datos personales del correo en commits. Evidencias pueden usar los correos ficticios del enunciado; el correo personal se redacta al compartir.

## 11. Distribución de implementación a Luna high

Dos workers en paralelo; el agente principal posee la integración. No lanzar más agentes si no hay slots. Los contratos de este documento se comunican antes de empezar.

**Luna A — API, reglas y pruebas.** Propiedad exclusiva: `api/**`, `tests/**`, `sql/**`. Entradas: material SQL y secciones 4–5/8–9. Entrega: API ejecutable, init segura, seis consultas, outbox configurable, pruebas de reglas/idempotencia/revisión. Debe avisar temprano cuando fije modelos y respuestas auxiliares. Aceptación: pytest pasa, Swagger válido, semilla estable, stock sin descuento y ninguna clasificación de respaldo ficticia. No tocar flujo, prompts, compose ni README global.

**Luna B — flujo y prompts.** Propiedad exclusiva: `flujo/**`, `prompts/**`, `scripts/probar_chatbot.py`, `docs/SUSTENTACION.md`. Entradas: contratos publicados por Luna A y este plan. Entrega: n8n exportable con ramas de errores/reintento, prompt clasificador, prompt chatbot, cinco respuestas conceptuales de máximo ocho líneas, script real y guía de evidencia. Aceptación: workflow sin secretos/importa; todas las ramas finalizan en respuesta; casos B y C preparados con resultados pendientes correctamente rotulados. No modificar API ni tests globales.

**Agente principal — integración y revisión.** Propiedad: `.env.example`, `.gitignore`, `compose.yaml`, Dockerfiles o envoltorios de arranque coordinados con A, README, bootstrap/runtime y pruebas integradas. Revisa diff y contratos; arranca API+n8n, importa/publica flujo, ejecuta casos con doble aislado si no hay key, identifica evidencia pendiente. Después de disponer de key, corre DeepSeek real; la conexión/envío de correo personal es el último paso. No tratar este plan como evidencia de ejecución.

Si hay necesidad de un tercer lote de Luna, asignarlo después de que finalice alguno: documentación de resultados/evidencias y guía de sustentación, evitando escrituras sobre archivos aún ocupados. Toda ampliación debe tener alcance y aceptación concretos.

## 12. Fases y puertas de salida

1. **Base local:** estructura, env, DB, API y pytest. Salida: arranque reproducible, endpoints y reglas correctos.
2. **Orquestación:** importar y ejecutar n8n real con contrato del proveedor simulado solamente en pruebas. Salida: cinco rutas B, reintentos, desconocido y fallos controlados demostrados técnicamente; el README declara ausencia de E2E LLM real.
3. **DeepSeek real:** cuando haya key, correr B y C, ajustar prompt si falla y repetir con historial transparente. Salida: respuestas literales y capturas/video del flujo.
4. **Correo al final:** conectar el canal disponible, fijar destinatario personal autorizado y enviar pruebas únicamente a sí mismo. Salida: evidencia de entrega o limitación honesta; no cambiar el éxito del registro por fallos del canal.
5. **Entrega y sustentación:** lectura completa del README en una instalación limpia, revisar secretos, resultados SQL y links de evidencias. Bonus solo después.

## 13. Sustentación del candidato

Preparar recorrido de 10–15 minutos: qué recibe el webhook, dónde vive la lógica, cómo se limita al LLM a proponer datos, cómo la API verifica, por qué se conserva una recepción sin cliente y cómo se recupera un envío. Distinguir solicitud registrada de venta/reserva aprobada y de correo entregado.

El candidato debe importar y activar/publicar el workflow, localizar credenciales, abrir una ejecución, seguir el branch de stock, consultar Swagger y explicar una prueba pytest. Explicar JSON mode frente a validación de esquema; parámetros y JOIN SQL; idempotencia frente a reintento; prompt injection y autorización. No afirmar que un prompt reemplaza controles de acceso.

Ensayar cambios pequeños: agregar un alias, modificar el umbral/criterio de alerta, introducir un filtro y añadir su prueba, o adaptar el prompt para pedir un dato ausente. La documentación debe describir el código realmente entregado y no un diseño aspiracional. Respuestas conceptuales: alucinación (contexto verificable y validación), RAG (recuperación cuando crece el conocimiento), function calling (herramienta autorizada que consulta API), chatbot/agente (respuesta frente a ejecución de acciones), costos (medir tokens, acotar contexto, modelos adecuados, caché/idempotencia y límites).

## 14. Riesgos y decisiones que no deben ocultarse

- Sin clave no hay evidencia LLM real; sin canal conectado no hay correo personal real. Estas son dependencias de las fases finales, no razones para detener API/flujo.
- El caso B5 no cabe en solicitudes originales: recepción separada es la adaptación documentada, no una pérdida de datos ni un cliente creado arbitrariamente.
- El modelo de datos admite un producto por solicitud; pedidos múltiples pasan a revisión en esta versión.
- SQLite y editor n8n locales sirven al prototipo, no equivalen a una operación multiusuario pública segura. No desplegar ni exponer datos de clientes sin autenticación/autorización.
- Una importación exitosa no comprueba el flujo. Se exige ejecución en el runtime de n8n fijado.
- No asegurar exactamente una entrega SMTP ante fallos ambiguos. La outbox resuelve persistencia/reintentos normales y hace visible la incertidumbre.
- La simplicidad para explicar y modificar vale más que introducir capas ajenas a la prueba. Cualquier desviación de este plan debe quedar reflejada en los contratos finales y el README.
