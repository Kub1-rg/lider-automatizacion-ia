# Video explicativo del Anexo B

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
