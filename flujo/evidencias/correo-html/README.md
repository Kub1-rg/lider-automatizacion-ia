# Prueba real de notificaciones HTML y previews

La ejecución [notificaciones-20261019T213619+0000.json](notificaciones-20261019T213619+0000.json) registra dos webhooks reales procesados por n8n y DeepSeek con `--html`:

| Caso | Solicitud | Recepción | Notificación | Resultado |
|---|---:|---:|---:|---|
| B3, queja por tóner y urgencia alta | 67 | 10 | 6 | SMTP aceptó el mensaje; estado `enviada`, un intento. |
| B4, seis escritorios en L y stock tres | 68 | 11 | 7 | SMTP aceptó el mensaje; estado `enviada`, un intento, `sin_stock=true`. |

El usuario confirmó la llegada a su bandeja de los dos mensajes anteriores (solicitudes 65 y 66). La llegada de estos dos mensajes HTML nuevos aún no está confirmada. Los avisos previos de outbox 1–3 siguen pendientes. La ejecución SMTP no guardó una captura del mensaje recibido ni del MIME transmitido. La API genera el correo como `multipart/alternative`, con partes `text/plain` y `text/html`; esto describe el formato esperado del renderer, no una inspección del tráfico SMTP.

Los PNG de [`renders/README.md`](renders/README.md) son vistas estáticas generadas desde las plantillas con WeasyPrint a 680, 640, 390 y 360 px. Sirven para revisar el diseño y el desbordamiento; no son capturas de la ejecución SMTP ni verifican Gmail u Outlook. El envío lo hace `python scripts/probar_notificaciones_reales.py --html`; no lo ejecutes para consultar la evidencia porque cada corrida crea dos solicitudes, consume dos llamadas reales a DeepSeek y envía dos correos nuevos.

Los archivos `.html`, `.txt` y `.eml` de preview se generan desde `api.email_templates.render_notification` con fixtures ficticios. Los `.eml` usan direcciones `example.test` y no representan los mensajes reales.

Para regenerar solo los previews desde la raíz del proyecto:

```powershell
python scripts/generar_previews_correo.py
```
