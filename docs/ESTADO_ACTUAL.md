# Estado actual de la entrega

**Corte de cierre:** 2026-10-20 04:04 UTC (19 de octubre, 23:04, Colombia). Esta revisión fue de solo lectura y edición documental; no repitió pruebas ni envió correos. Las suites aprobadas que se citan son resultados históricos, no corridas nuevas.

Repositorio público: [Kub1-rg/lider-automatizacion-ia](https://github.com/Kub1-rg/lider-automatizacion-ia), rama `main`.

**Video final:** [sustentacion-anexo-b.mp4](../flujo/evidencias/video/sustentacion-anexo-b.mp4), 4:09.45, H.264/AAC, 1280×608. Es una captura del usuario de la interfaz real: workflow organizado, ejecuciones guardadas B1–B5 (IDs 15–19), solicitud 72 y recepción 16. No muestra una nueva corrida durante la grabación. Se recortaron las barras del navegador y de Windows; se conservó el audio sin recodificar. La revisión visual se hizo por muestreo, sin transcribir ni certificar palabra por palabra la narración. [Índice y manifiesto](../flujo/evidencias/video/README.md).

**Runtime leído al cierre:** 12 clientes, 12 productos, 72 solicitudes, 16 recepciones y 10 notificaciones. Cuatro notificaciones están `enviada`, con cuatro intentos en total; seis están `pendiente`, con cero intentos. SMTP está habilitado tras restaurar/reconstruir solo la API con `compose.yaml`. No se enviaron los avisos pendientes durante esta revisión.

**Chrome/n8n:** acceso autorizado verificado en esta sesión; el bloqueo anterior quedó superado. Workflow organizado en ocho bloques y una guía de lectura: 69 nodos funcionales más nueve notas. Comparación estática del export antes/después confirmó los mismos parámetros funcionales y conexiones. Copia local de respaldo en `.runtime/visual-backup/`, excluida de Git.

## Resultados por ejercicio

### 1. Flujo n8n

- [x] Workflow importado y publicado en n8n 2.43.8: 69 nodos funcionales y nueve notas visuales. SHA-256 actual de `flujo/solicitudes.json`: `5bd008ad567cc279f09fa7b6bb32b58227c333064a636b3331e32f48916d421d`. El hash histórico `8ec5735fdcbb6653ab879b416053b82e78d0fb9d454bdb7da17ba1b037d62d2c` corresponde a la versión validada antes de reorganizar posiciones y notas.
- [x] Suite técnica: 16 grupos y 107 aserciones contra el webhook real de n8n y un doble HTTP local. Verificó B1–B5, alertas, revisión, reintentos, fallos del proveedor e idempotencia. Esto verifica ramas y contratos con fixtures; no mide la comprensión de un LLM.
- [x] Ejecución con DeepSeek real B1–B5: 5/5 respuestas HTTP 200 del proveedor, una llamada por caso. Se crearon cuatro solicitudes (IDs 61–64) y una recepción manual (ID 7, cliente desconocido); se registraron ejecuciones n8n con IDs 6 a 10. El pedido B4 quedó con cantidad 6 frente a stock 3 y `sin_stock=true`.
- [x] Pruebas reales de notificaciones: dos webhooks iniciales generaron las solicitudes 65 y 66; una corrida posterior con `--html` generó 67 y 68. DeepSeek respondió HTTP 200 una vez por caso. Los cuatro mensajes fueron aceptados por SMTP y las notificaciones 4–7 quedaron `enviada`, con un intento cada una. Las solicitudes B3 (queja/urgencia alta) y B4 (seis escritorios frente a stock tres) mantuvieron sus alertas.
- [x] El usuario confirmó que recibió los mensajes de las solicitudes 65 y 66. La llegada de los mensajes HTML de las solicitudes 67 y 68 aún no está confirmada.
- [x] Chatbot real: C1–C4 revisadas en la versión final del prompt, 4/4 acordes con el comportamiento esperado. La revisión confirmó rechazo a revelar el prompt (C1), precio unitario COP 780.000/stock 3 sin prometer entrega (C2), respuesta de privacidad sin metadatos internos (C3), y solicitud de referencia y cantidad con presupuesto opcional (C4).

Hasta el primer corte hubo **17 llamadas reales al proveedor**: cinco para B1–B5, cuatro en una primera ronda C1–C4, cuatro en la ronda final C1–C4, dos en la primera prueba de notificaciones y dos en la prueba HTML. No son diecisiete clasificaciones B. La primera ronda C tuvo fallos menores de cantidad ambigua, escalamiento prematuro, claridad de precio COP, detalles internos y longitud; se conserva como historial y la ronda final es la referencia.

- [x] Segunda corrida real B1–B5: [evidencia de las 23:05 UTC](../flujo/evidencias/real/flujo-real-20261019T230505Z-1df02d8d.json), 5/5 aprobados, un intento LLM por caso. Ejecuciones n8n 15–19, solicitudes 69–72 y recepciones 12–16; B5 no creó solicitud. Se confirmó `NOTIFICATIONS_ENABLED=false` antes de ejecutarla. Los avisos 8–10 quedaron pendientes sin intentos. Después se restauró la configuración normal de API con notificaciones activas.

El total **documentado** es ahora **22 llamadas reales**: las 17 anteriores más cinco de la segunda corrida B. No se hicieron llamadas nuevas al convertir el video, reorganizar visualmente el flujo o preparar esta entrega.

### 2. API REST y consultas SQL

- [x] 21 pruebas pytest aprobadas. Incluyen la ejecución de las seis consultas SQL sobre una base temporal sembrada y sus resultados esperados, y guardas para que el runner B requiera autorización explícita de notificaciones.
- [x] Smoke normal: API health HTTP 200, OpenAPI HTTP 200 y editor n8n HTTP 200.
- [x] La API tiene 72 solicitudes en la base normal tras las dos corridas B y las pruebas de notificación; el seed original de 60 solicitudes se conservó, sin reiniciar la base. Las pruebas SQL usan una base temporal y mantienen los resultados esperados: 11 solicitudes pendientes, distribución 18 consultas (30 %), 30 pedidos (50 %) y 12 quejas (20 %), además de las agregaciones y pedidos sobre stock.
- [x] La prueba previa sin clave produjo una recepción `revision_manual` con motivo `llm_not_configured` y cero intentos, sin crear una solicitud ficticia. Fue una comprobación de fallback anterior a la ejecución real; actualmente la clave ya está configurada localmente.

### 3. Prompts y chatbot

- [x] La respuesta final para C1–C4 y sus metadatos están en [pruebas_chatbot.md](../prompts/pruebas_chatbot.md). SHA-256 del prompt final: `58daf9802be9e0be0729d9ff79bc0e3bfe618bc63799f559bf7603e43e9da67e`.
- [x] Se conserva la ronda C inicial en [chatbot-v1](../prompts/evidencias/chatbot-v1-20261019T202737Z.md), junto con la razón de las mejoras.

## Evidencias

- [Grabación final de interfaz n8n/API](../flujo/evidencias/video/sustentacion-anexo-b.mp4), 4:09, y [manifiesto verificable](../flujo/evidencias/video/manifiesto-sustentacion.json).
- [Segunda corrida B1–B5](../flujo/evidencias/real/flujo-real-20261019T230505Z-1df02d8d.json), ejecuciones 15–19, 5/5.

- [B1–B5 con proveedor real](../flujo/evidencias/real/flujo-real-20261019T202729Z-afcf5fa1.json). Todas las respuestas observadas del proveedor fueron HTTP 200 con un intento. Los avisos de outbox 1 (urgencia B1), 2 (queja y urgencia B3) y 3 (stock B4) quedaron pendientes; esto no es evidencia de envío SMTP.
- [Notificaciones SMTP reales](../flujo/evidencias/correo/notificaciones-20261019T212803+0000.json) y [guía de evidencia](../flujo/evidencias/correo/README.md). SMTP aceptó los mensajes asociados a notificaciones 4 y 5; ambos registros quedaron `enviada`, con un intento y Message-ID distintos. Repetir el POST para la notificación 4 no envió un duplicado y conservó un intento. La aceptación SMTP no confirma que el mensaje haya llegado a la bandeja.
- [Notificaciones HTML reales](../flujo/evidencias/correo-html/notificaciones-20261019T213619+0000.json) y [índice de evidencia HTML](../flujo/evidencias/correo-html/README.md). SMTP aceptó las notificaciones 6 y 7 asociadas a solicitudes 67 y 68, ambas con un intento. La llegada a la bandeja no está confirmada.
- [Previews de las plantillas HTML](../flujo/evidencias/correo-html/README.md), con [renders estáticos en escritorio y móvil](../flujo/evidencias/correo-html/renders/README.md). QA visual de B3, B4 y urgencia a 680, 640, 390 y 360 px: contenido legible y sin clipping horizontal. Los PNG son renders estáticos con WeasyPrint; no validan la presentación en Gmail/Outlook ni son capturas de mensajes SMTP. El renderer de la API prepara `multipart/alternative` con partes `text/plain` y `text/html`; no se capturó el MIME recibido por el servidor.
- [Suite técnica aprobada: 16/16 grupos, 107 aserciones](../flujo/evidencias/tecnica/integracion-20261019T202015Z-c08a759f65a5.json). Usa un fixture local y está separada de las llamadas reales.
- [Primer intento técnico: 7/13 grupos](../flujo/evidencias/tecnica/integracion-20261019T201713Z-409ab9a65599.json), conservado como historial; la ejecución aprobada posterior es la referencia técnica.
- [Respuestas finales C1–C4](../prompts/pruebas_chatbot.md) y [respuestas iniciales C1–C4](../prompts/evidencias/chatbot-v1-20261019T202737Z.md).

La semilla `material/datos_prueba.sql` conserva SHA-256 `65cd979a28b746b7ca8753b97399789c6f5d864f68424aa8a7a0698ed6ac648f`. El workflow final conservó su hash durante la validación real. Se verificó que `.env`, `.runtime/`, bases locales y cachés Python estén excluidos de Git y que el escaneo UTF-8 no encuentre texto dañado. El envío SMTP usa validación explícita de certificados TLS; el Message-ID se persiste antes del intento y se reutiliza al reintentar.

## Entorno y reproducción

El plan proponía API en `8018`, pero Windows reserva el rango TCP `7969–8068`; se usó `127.0.0.1:18018` para API normal, `127.0.0.1:5688` para n8n y `127.0.0.1:8000` dentro de Docker. No se modificó la reserva. El perfil técnico aislado usó API `18019`, n8n `5689` y fixture `5690`; permanece detenido con sus volúmenes conservados. El stack normal permanece activo y ligado a loopback. No tiene autenticación de clientes y no debe exponerse a Internet.

La configuración local ya permite las llamadas reales a DeepSeek. Para volver a iniciar/recrear el entorno normal se puede ejecutar `./scripts/bootstrap.ps1`. Para repetir B1–B5 el runner ahora exige `python scripts/probar_flujo_real.py --allow-notifications`: una corrida completa crea cuatro solicitudes nuevas, consume cinco llamadas reales al modelo y puede enviar hasta tres correos (B1, B3 y B4). Sin esa bandera termina antes de cualquier solicitud HTTP; la bandera es un reconocimiento del operador y el runner no puede verificar SMTP dentro del contenedor. Para repetir C1–C4: `python scripts/probar_chatbot.py`; consume cuatro llamadas y actualiza el archivo de resultados. `python scripts/probar_notificaciones_reales.py --html` crea dos solicitudes, consume dos llamadas y envía dos mensajes nuevos. No ejecutes estos comandos solo para consultar las evidencias.

## Pendiente para completar la entrega

Los ejercicios obligatorios tienen código y evidencias documentadas; el video final ya está incorporado. La evaluación final corresponde al evaluador. El [plan de cierre](PLAN_CIERRE.md) conserva como siguiente etapa la sustentación y una modificación pequeña en vivo, posteriores a la entrega.

- **Verificación de correo HTML:** el usuario confirmó que recibió los mensajes de las solicitudes 65 y 66. SMTP aceptó los mensajes HTML asociados a las solicitudes 67 y 68, pero su llegada a la bandeja no está confirmada. Los avisos de outbox 1–3 y 8–10 continúan pendientes y no se borraron ni reenviaron. La vista PNG es estática; falta verificar el diseño en Gmail/Outlook.
- **Evidencia visual:** el video final captura n8n/API y muestra resultados de ejecuciones guardadas de los cinco casos. No afirmar que se lanzó otra corrida mientras se grababa. La narración no fue auditada palabra por palabra.
- **Revisión y sustentación:** falta la revisión final del candidato y la sustentación. El repositorio público ya contiene la entrega. El bonus es opcional y no está implementado.

