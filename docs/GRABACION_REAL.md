# Guion para grabar la demostración real

**Estado:** el usuario ya grabó la [versión final de 4:09](../flujo/evidencias/video/sustentacion-anexo-b.mp4), mostrando la interfaz y resultados de ejecuciones guardadas. Este guion se conserva para una eventual nueva corrida durante la captura, que no fue lo mostrado en el video final. **Duración objetivo para repetir:** 3–4 minutos; máximo 5. Refuerza la evidencia del procesamiento que pide el PDF; el video existente explica trazas y no captura n8n. No mostrar `.env`, credenciales, destinatarios, encabezados de correo ni datos de cuentas.

## Preparación, solo cuando se vaya a grabar

La captura puede hacerla el usuario en su grabador de pantalla o tras conectar un navegador disponible. Antes de una nueva corrida B, coordinarla con el agente principal: `scripts/probar_flujo_real.py --allow-notifications` consume cinco llamadas reales a DeepSeek, crea cuatro solicitudes y puede disparar hasta tres correos. El runner exige la bandera, pero no puede comprobar si SMTP está activo.

Para evitar correos durante esa grabación, el agente principal debe recrear temporalmente **solo** el servicio API con `NOTIFICATIONS_ENABLED=false` mediante un override temporal fuera del repositorio, sin editar `.env`; comprobar `http://127.0.0.1:18018/health` y confirmar la configuración deshabilitada antes de iniciar. Al terminar, restaurar la configuración anterior recreando API con `compose.yaml` solamente, comprobar el health y retirar el override. No ejecutar esta preparación hasta que la grabación esté coordinada. El editor local está en `http://127.0.0.1:5688`; la API en `http://127.0.0.1:18018/docs`.

## Guion sugerido

1. **Arquitectura y workflow (30–40 s).** Mostrar el workflow de n8n y resumir: webhook → consulta API → clasificación DeepSeek → validación/revisión → persistencia y alertas. Mencionar que la API aplica reglas de negocio y que el entorno está ligado a localhost.
2. **Cinco casos (2 min).** Ejecutar, solo con la captura iniciada y tras la preparación anterior:

   ```powershell
   python scripts/probar_flujo_real.py --allow-notifications
   ```

   El runner genera una evidencia nueva en `flujo/evidencias/real/`. Explicar B1–B4 como solicitudes registradas, y B5 como recepción de cliente desconocido en revisión manual, sin solicitud. En B4, seis escritorios frente a stock tres producen `sin_stock=true`; no se descuenta inventario. Mostrar los IDs y resultados de la corrida que acaba de ejecutarse, sin leer cuerpos de correo ni datos ajenos al caso.
3. **Persistencia y cierre (30–40 s).** Abrir la evidencia recién generada y, si el tiempo alcanza, mostrar los registros API correspondientes. Aclarar que la ejecución real usa entradas de prueba y que el aviso de revisión manual requiere atención humana. Cerrar con límites: no hay autenticación de clientes ni despliegue público.

Para revisar una evidencia ya guardada sin repetir llamadas, imprimir únicamente campos seleccionados (no `raw_body`):

```powershell
$e = Get-Content -Raw 'flujo/evidencias/real/flujo-real-20261019T202729Z-afcf5fa1.json' | ConvertFrom-Json
$e.results | ForEach-Object {
    [pscustomobject]@{
        Caso = $_.case
        HTTP = $_.webhook.http_status
        Recepcion = $_.webhook.body.recepcion_id
        Solicitud = $_.webhook.body.solicitud_id
        Tipo = $_.webhook.body.clasificacion.tipo
        Producto = $_.webhook.body.clasificacion.producto
        Cantidad = $_.webhook.body.clasificacion.cantidad
        Revision = $_.webhook.body.requiere_revision
        Motivos = ($_.webhook.body.motivos_revision -join ', ')
    }
} | Format-Table -AutoSize
```

Ese archivo corresponde a la corrida histórica enlazada en [estado actual](ESTADO_ACTUAL.md); no atribuirla a una grabación nueva. La corrida nueva sí consume proveedor y crea registros. No repetir el runner para consultar resultados. Si la captura no puede completarse ahora, conservar esta guía como pendiente; no fabricar una grabación ni presentar el MP4 explicativo como captura de pantalla.
