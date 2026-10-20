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

## Video anterior de trazas · evidencia complementaria

`demostracion-anexo-b.mp4` es una **reproducción explicativa de una ejecución real con entradas de prueba**. Presenta los cinco casos B1–B5 de `../real/flujo-real-20261019T202729Z-afcf5fa1.json`, con mensajes, clasificación, IDs, estados HTTP, alertas y el resultado de las verificaciones. No es un screencast ni una captura de la interfaz n8n.

El video dura menos de tres minutos, está en 1280×720 y usa H.264. Sus placas se dibujan con Pillow; imageio-ffmpeg codifica el video. Las imágenes PNG de cada placa y sus hashes de fuente, tiempos, resolución y duración están en [manifiesto.json](manifiesto.json). El producto Escritorio en L / stock 3 se documentó mediante un GET de solo lectura en [catalogo_escritorio_api_readonly.json](catalogo_escritorio_api_readonly.json).

La placa “lecturas GET” utiliza la instantánea [api_state_readonly_snapshot.json](api_state_readonly_snapshot.json): cuatro solicitudes (61–64) y recepción 7, todas consultadas con HTTP 200. La instantánea omite correos y mensajes originales, conserva IDs, tipo, producto, cantidad, estado y alertas, y no atribuye esos GETs al modelo. El generador reutiliza este archivo fechado y su hash; no emite nuevas solicitudes HTTP al regenerar.

La placa de notificaciones HTML corresponde a una ejecución posterior y separada: solicitudes 67/68, notificaciones 6/7, aceptación SMTP registrada en `../correo-html/notificaciones-20261019T213619+0000.json`. La placa no afirma que esos mensajes hayan llegado a bandeja. No incluye correo electrónico, headers, Message-ID, credenciales ni variables del entorno.

Para regenerar desde la raíz del repositorio, instala únicamente las dependencias del video si faltan; no se agregan a `api/requirements.txt`:

```powershell
python -m pip install Pillow==11.0.0 imageio-ffmpeg==0.6.0
python scripts/generar_video_evidencia.py
```

El script solo lee los JSON mencionados y escribe el MP4, el manifiesto y PNGs. No llama al webhook, a la API, a DeepSeek ni a SMTP y no requiere iniciar el stack.
