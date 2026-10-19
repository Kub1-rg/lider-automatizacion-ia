# Estado actual de la entrega

**Corte verificado:** 2026-10-19 21:49:44 UTC (16:49:44, America/Bogota). Resultados comunicados y revisados por el agente principal. La [ejecución del plan técnico Astra](PLAN_ASTRA.md) se implementó con Luna en esfuerzo alto e integración a cargo del agente principal.

Repositorio público publicado: [Kub1-rg/lider-automatizacion-ia](https://github.com/Kub1-rg/lider-automatizacion-ia), rama `main`, con código, pruebas y evidencias.

## Resultados por ejercicio

### 1. Flujo n8n

- [x] Workflow de 69 nodos importado y publicado en n8n 2.43.8. Su SHA-256 final es `8ec5735fdcbb6653ab879b416053b82e78d0fb9d454bdb7da17ba1b037d62d2c`.
- [x] Suite técnica: 16 grupos y 107 aserciones contra el webhook real de n8n y un doble HTTP local. Verificó B1–B5, alertas, revisión, reintentos, fallos del proveedor e idempotencia. Esto verifica ramas y contratos con fixtures; no mide la comprensión de un LLM.
- [x] Ejecución con DeepSeek real B1–B5: 5/5 respuestas HTTP 200 del proveedor, una llamada por caso. Se crearon cuatro solicitudes (IDs 61–64) y una recepción manual (ID 7, cliente desconocido); se registraron ejecuciones n8n con IDs 6 a 10. El pedido B4 quedó con cantidad 6 frente a stock 3 y `sin_stock=true`.
- [x] Pruebas reales de notificaciones: dos webhooks iniciales generaron las solicitudes 65 y 66; una corrida posterior con `--html` generó 67 y 68. DeepSeek respondió HTTP 200 una vez por caso. Los cuatro mensajes fueron aceptados por SMTP y las notificaciones 4–7 quedaron `enviada`, con un intento cada una. Las solicitudes B3 (queja/urgencia alta) y B4 (seis escritorios frente a stock tres) mantuvieron sus alertas.
- [x] El usuario confirmó que recibió los mensajes de las solicitudes 65 y 66. La llegada de los mensajes HTML de las solicitudes 67 y 68 aún no está confirmada.
- [x] Chatbot real: C1–C4 revisadas en la versión final del prompt, 4/4 acordes con el comportamiento esperado. La revisión confirmó rechazo a revelar el prompt (C1), precio unitario COP 780.000/stock 3 sin prometer entrega (C2), respuesta de privacidad sin metadatos internos (C3), y solicitud de referencia y cantidad con presupuesto opcional (C4).

En total hubo **17 llamadas reales al proveedor**: cinco para B1–B5, cuatro en una primera ronda C1–C4, cuatro en la ronda final C1–C4, dos en la primera prueba de notificaciones y dos en la prueba HTML. No son diecisiete clasificaciones B. La primera ronda C tuvo fallos menores de cantidad ambigua, escalamiento prematuro, claridad de precio COP, detalles internos y longitud; se conserva como historial y la ronda final es la referencia.

### 2. API REST y consultas SQL

- [x] 21 pruebas pytest aprobadas. Incluyen la ejecución de las seis consultas SQL sobre una base temporal sembrada y sus resultados esperados, y guardas para que el runner B requiera autorización explícita de notificaciones.
- [x] Smoke normal: API health HTTP 200, OpenAPI HTTP 200 y editor n8n HTTP 200.
- [x] La API tiene 68 solicitudes en la base normal tras las pruebas B y de notificación; el seed original de 60 solicitudes se conservó, sin reiniciar la base. Las pruebas SQL usan una base temporal y mantienen los resultados esperados: 11 solicitudes pendientes, distribución 18 consultas (30 %), 30 pedidos (50 %) y 12 quejas (20 %), además de las agregaciones y pedidos sobre stock.
- [x] La prueba previa sin clave produjo una recepción `revision_manual` con motivo `llm_not_configured` y cero intentos, sin crear una solicitud ficticia. Fue una comprobación de fallback anterior a la ejecución real; actualmente la clave ya está configurada localmente.

### 3. Prompts y chatbot

- [x] La respuesta final para C1–C4 y sus metadatos están en [pruebas_chatbot.md](../prompts/pruebas_chatbot.md). SHA-256 del prompt final: `58daf9802be9e0be0729d9ff79bc0e3bfe618bc63799f559bf7603e43e9da67e`.
- [x] Se conserva la ronda C inicial en [chatbot-v1](../prompts/evidencias/chatbot-v1-20261019T202737Z.md), junto con la razón de las mejoras.

## Evidencias

- [B1–B5 con proveedor real](../flujo/evidencias/real/flujo-real-20261019T202729Z-afcf5fa1.json). Todas las respuestas observadas del proveedor fueron HTTP 200 con un intento. Los avisos de outbox 1 (urgencia B1), 2 (queja y urgencia B3) y 3 (stock B4) quedaron pendientes; esto no es evidencia de envío SMTP.
- [Notificaciones SMTP reales](../flujo/evidencias/correo/notificaciones-20261019T212803+0000.json) y [guía de evidencia](../flujo/evidencias/correo/README.md). SMTP aceptó los mensajes asociados a notificaciones 4 y 5; ambos registros quedaron `enviada`, con un intento y Message-ID distintos. Repetir el POST para la notificación 4 no envió un duplicado y conservó un intento. La aceptación SMTP no confirma que el mensaje haya llegado a la bandeja.
- [Notificaciones HTML reales](../flujo/evidencias/correo-html/notificaciones-20261019T213619+0000.json) y [índice de evidencia HTML](../flujo/evidencias/correo-html/README.md). SMTP aceptó las notificaciones 6 y 7 asociadas a solicitudes 67 y 68, ambas con un intento. La llegada a la bandeja no está confirmada.
- [Video explicativo de los cinco casos B](../flujo/evidencias/video/demostracion-anexo-b.mp4) (2:36, 1280×720). Reproduce trazas reales de webhook/API y su resultado; no es una grabación de la interfaz n8n ni sustituye una captura de UI si el evaluador la exige.
- [Previews de las plantillas HTML](../flujo/evidencias/correo-html/README.md), con [renders estáticos en escritorio y móvil](../flujo/evidencias/correo-html/renders/README.md). QA visual de B3, B4 y urgencia a 680, 640, 390 y 360 px: contenido legible y sin clipping horizontal. Los PNG son renders estáticos con WeasyPrint; no validan la presentación en Gmail/Outlook ni son capturas de mensajes SMTP. El renderer de la API prepara `multipart/alternative` con partes `text/plain` y `text/html`; no se capturó el MIME recibido por el servidor.
- [Suite técnica aprobada: 16/16 grupos, 107 aserciones](../flujo/evidencias/tecnica/integracion-20261019T202015Z-c08a759f65a5.json). Usa un fixture local y está separada de las llamadas reales.
- [Primer intento técnico: 7/13 grupos](../flujo/evidencias/tecnica/integracion-20261019T201713Z-409ab9a65599.json), conservado como historial; la ejecución aprobada posterior es la referencia técnica.
- [Respuestas finales C1–C4](../prompts/pruebas_chatbot.md) y [respuestas iniciales C1–C4](../prompts/evidencias/chatbot-v1-20261019T202737Z.md).

La semilla `material/datos_prueba.sql` conserva SHA-256 `65cd979a28b746b7ca8753b97399789c6f5d864f68424aa8a7a0698ed6ac648f`. El workflow final conservó su hash durante la validación real. Se verificó que `.env`, `.runtime/`, bases locales y cachés Python estén excluidos de Git y que el escaneo UTF-8 no encuentre texto dañado. El envío SMTP usa validación explícita de certificados TLS; el Message-ID se persiste antes del intento y se reutiliza al reintentar.

## Entorno y reproducción

El plan proponía API en `8018`, pero Windows reserva el rango TCP `7969–8068`; se usó `127.0.0.1:18018` para API normal, `127.0.0.1:5688` para n8n y `127.0.0.1:8000` dentro de Docker. No se modificó la reserva. El perfil técnico aislado usó API `18019`, n8n `5689` y fixture `5690`; permanece detenido con sus volúmenes conservados. El stack normal permanece activo y ligado a loopback. No tiene autenticación de clientes y no debe exponerse a Internet.

La configuración local ya permite las llamadas reales a DeepSeek. Para volver a iniciar/recrear el entorno normal se puede ejecutar `./scripts/bootstrap.ps1`. Para repetir B1–B5 el runner ahora exige `python scripts/probar_flujo_real.py --allow-notifications`: una corrida completa crea cuatro solicitudes nuevas, consume cinco llamadas reales al modelo y puede enviar hasta tres correos (B1, B3 y B4). Sin esa bandera termina antes de cualquier solicitud HTTP; la bandera es un reconocimiento del operador y el runner no puede verificar SMTP dentro del contenedor. Para repetir C1–C4: `python scripts/probar_chatbot.py`; consume cuatro llamadas y actualiza el archivo de resultados. `python scripts/probar_notificaciones_reales.py --html` crea dos solicitudes, consume dos llamadas y envía dos mensajes nuevos. No ejecutes estos comandos solo para consultar las evidencias.

## Pendiente para completar la entrega

La revisión documental ya cerró la explicación de las ampliaciones al esquema, las elecciones técnicas y el contexto de catálogo en el README. El [plan de cierre](PLAN_CIERRE.md) organiza las siguientes etapas. La próxima es capturar una corrida real de B1–B5 con el [guion preparado](GRABACION_REAL.md); todavía no se ha realizado esa grabación.

- **Verificación de correo HTML:** el usuario confirmó que recibió los mensajes de las solicitudes 65 y 66. SMTP aceptó los mensajes HTML asociados a las solicitudes 67 y 68, pero su llegada a la bandeja no está confirmada. Los avisos anteriores de outbox 1–3 continúan pendientes y no se borraron ni reenviaron. La vista PNG es estática; falta verificar el diseño en Gmail/Outlook.
- **Evidencia visual:** el video explica las trazas reales de los cinco casos B; no muestra la interfaz n8n. Grabar una captura de UI si el evaluador exige esa forma de evidencia es el riesgo residual.
- **Revisión y sustentación:** falta la revisión final del candidato y la sustentación. El repositorio público ya contiene la entrega. El bonus es opcional y no está implementado.

