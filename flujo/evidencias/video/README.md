# Videos de la entrega

## Grabación final · interfaz n8n y API

[Ver o descargar sustentacion-anexo-b.mp4](sustentacion-anexo-b.mp4) · **4:09.45** · H.264/AAC · 1280×608 · dentro del máximo de cinco minutos.

Captura aportada por el usuario: `2026-10-19 22-58-52.mkv`. Se convirtió a MP4 para facilitar la reproducción, se recortaron las barras superior del navegador e inferior de Windows y se conservó la pista AAC sin recodificar. No se alteró el orden de la explicación ni se añadieron ejecuciones o resultados. El original permanece en el equipo del usuario y no se incluye en Git.

| Tiempo aproximado | Contenido visible |
|---|---|
| 00:00–01:25 | Workflow organizado: recepción/idempotencia, contexto API, clasificación IA y registro/alertas. |
| 01:25–02:55 | Interfaz n8n: recorrido por las ejecuciones guardadas 15–19 de B1–B5. |
| 02:55–03:25 | API: solicitud 72, B4 con cantidad seis y stock insuficiente. |
| 03:25–04:09 | API: recepción 16, B5 en revisión manual por cliente desconocido y sin solicitud asociada. |

Los tiempos orientan la revisión y proceden de fotogramas muestreados; no son una transcripción. La pista de audio se conserva, pero la narración no fue auditada palabra por palabra. Los datos mostrados de cliente/mensaje pertenecen a los casos de prueba suministrados.

**Proveniencia:** [segunda corrida real B1–B5](../real/flujo-real-20261019T230505Z-1df02d8d.json), cinco casos aprobados, solicitudes 69–72 y recepciones 12–16. La captura muestra resultados existentes, no una corrida nueva durante la grabación. Los correos estuvieron deshabilitados durante esa corrida; al cierre se restauró la configuración normal con SMTP habilitado.

El [manifiesto final](manifiesto-sustentacion.json) conserva hashes, duración, transformación y límites de revisión. El cierre no repitió runners, llamadas al proveedor ni envíos de correo.

## Evidencia histórica conservada

Se retiró el MP4 anterior generado con placas para dejar una sola grabación de entrega. Se conservan las evidencias JSON, las instantáneas de API, las imágenes y el [manifiesto histórico](manifiesto.json). Este manifiesto describe el artefacto anterior, retirado de la versión actual; no corresponde al video final. El generador histórico `scripts/generar_video_evidencia.py` tampoco produce la captura final.
