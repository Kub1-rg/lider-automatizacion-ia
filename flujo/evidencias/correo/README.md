# Evidencia de notificaciones

El archivo [notificaciones-20261019T212803+0000.json](notificaciones-20261019T212803+0000.json) registra dos webhooks reales procesados por n8n y DeepSeek:

- **B3:** solicitud 65, recepción 8 y notificación 4; queja con urgencia alta.
- **B4:** solicitud 66, recepción 9 y notificación 5; seis escritorios solicitados frente a stock tres, con `sin_stock=true`.

El servidor SMTP aceptó ambos mensajes. Los dos registros quedaron `enviada`, con un intento cada uno y Message-ID diferentes. Repetir el POST de la notificación 4 no produjo un envío duplicado. La aceptación por SMTP no verifica que el correo haya llegado a la bandeja; el artefacto omite direcciones y credenciales.

Los avisos anteriores de outbox 1–3 siguen pendientes y no fueron borrados ni enviados por esta prueba. No vuelvas a ejecutar `python scripts/probar_notificaciones_reales.py` solo para consultar esta evidencia: el runner crea dos solicitudes nuevas, consume llamadas reales a DeepSeek y envía dos correos adicionales.
