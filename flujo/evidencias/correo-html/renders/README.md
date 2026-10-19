# Previews estáticas de correo

Estas imágenes se generaron desde los tres archivos `.html` de la carpeta padre, con Docker, WeasyPrint 65.1, un PDF intermedio y PyMuPDF 1.26.3. El render usa anchos de 680, 640, 390 y 360 px y recorta el alto al contenido. No inicia servicios del proyecto, no accede al `.env` y no envía correo.

| Caso | Escritorio (680 px) | Móvil (360 px) |
| --- | --- | --- |
| Queja prioritaria B3 | [PNG](preview-b3-queja-680px.png) | [PNG](preview-b3-queja-360px.png) |
| Stock insuficiente B4 | [PNG](preview-b4-stock-insuficiente-680px.png) | [PNG](preview-b4-stock-insuficiente-360px.png) |
| Solicitud urgente | [PNG](preview-urgencia-alta-680px.png) | [PNG](preview-urgencia-alta-360px.png) |

La revisión estática encontró las tablas y etiquetas legibles en los cuatro anchos, sin desbordamiento horizontal en B3 ni B4. Esto permite revisar el HTML generado; no es una captura de Gmail u Outlook ni certifica fidelidad píxel a píxel en un cliente de correo.

Para regenerar las doce imágenes desde PowerShell en la raíz del repositorio:

```powershell
New-Item -ItemType Directory -Force flujo/evidencias/correo-html/renders | Out-Null
docker build -f Dockerfile.preview -t lider-ia-email-preview:local .
docker run --rm `
  -v "${PWD}/flujo/evidencias/correo-html:/input:ro" `
  -v "${PWD}/flujo/evidencias/correo-html/renders:/output" `
  lider-ia-email-preview:local /input /output --widths 680,640,390,360
```
