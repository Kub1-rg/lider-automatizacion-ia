# Evidencia de ejecución real B1–B5

Ejecución del 19 de octubre de 2026 contra el webhook normal de n8n, con proveedor configurado DeepSeek `deepseek-flash`. La respuesta del proveedor fue HTTP 200 en los cinco casos; hubo un intento por caso. El artefacto conserva las solicitudes y respuestas del webhook/API, los identificadores de ejecución y la metadata selectiva de cada llamada: [flujo-real-20261019T202729Z-afcf5fa1.json](flujo-real-20261019T202729Z-afcf5fa1.json).

| Caso | Ejecución n8n | Recepción | Solicitud | Resultado observado |
|---|---:|---:|---:|---|
| B1, pedido urgente de resmas | 6 | 3 | 61 | Pedido de 10 resmas, urgencia alta; outbox 1 pendiente. |
| B2, consulta de diademas | 7 | 4 | 62 | Consulta de producto y precio. |
| B3, queja por tóner | 8 | 5 | 63 | Queja, urgencia alta; outbox 2 pendiente. |
| B4, seis escritorios en L | 9 | 6 | 64 | Stock insuficiente (6 solicitados, 3 disponibles); outbox 3 pendiente. [Solicitud 64 en API](http://127.0.0.1:18018/solicitudes/64). |
| B5, cliente desconocido | 10 | 7 | — | HTTP 202, revisión manual por `cliente_desconocido`; no se creó solicitud. |

Los cinco casos pasaron las comprobaciones del runner. Cada caso hizo una llamada al proveedor: **5 llamadas**, 3.857 tokens de entrada y 278 de salida (**4.135 tokens en total**, incluidos 2.048 tokens de entrada en caché). No se enviaron correos: SMTP está deshabilitado, y los avisos de outbox 1, 2 y 3 siguen pendientes. No hay capturas de pantalla de esta ejecución; la evidencia disponible es el JSON y los registros de webhook, API y n8n allí correlacionados.

El hash SHA-256 del workflow usado fue `8ec5735fdcbb6653ab879b416053b82e78d0fb9d454bdb7da17ba1b037d62d2c`; el del prompt de sistema embebido, `999edba611a5cb0627ba695fb002470209f42e8420889a009b79c048af31c21f`. La metadata de proveedor está asociada a cada caso en `results[].n8n_execution.provider_calls`, no a un único request global.

La suite técnica con doble HTTP es una evidencia separada y simulada; no se usa aquí para afirmar resultados del proveedor. Para el estado del proyecto y las otras pruebas, consulta [ESTADO_ACTUAL.md](../../../docs/ESTADO_ACTUAL.md).
