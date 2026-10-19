# Workflow de solicitudes

El workflow importable de n8n 2.43.8 está en [solicitudes.json](solicitudes.json), con ID estable `solicitudes-ia-suministros-v1`. El webhook local es `POST http://127.0.0.1:5688/webhook/solicitud`; recibe JSON con `cliente_email` y `mensaje`. Conviene enviar un `Idempotency-Key` estable al reintentar.

Para iniciar el perfil normal y cargar/publicar el workflow:

```powershell
Copy-Item .env.example .env # solo si .env todavía no existe
./scripts/bootstrap.ps1
```

## Pruebas y evidencias

La ejecución real del Anexo B está documentada en [el artefacto B1–B5](evidencias/real/flujo-real-20261019T202729Z-afcf5fa1.json) y el [índice de evidencia real](evidencias/real/README.md). Los cinco casos pasaron. Se observaron cuatro solicitudes registradas y una recepción enviada a revisión manual por cliente desconocido. No se enviaron correos: SMTP permanece deshabilitado y los avisos de outbox están pendientes. La evidencia visual de la ejecución también está pendiente.

Los cuatro casos C de chatbot se ejecutaron aparte; la ronda final obtuvo 4/4 respuestas acordes con el comportamiento esperado y está documentada en [pruebas_chatbot.md](../prompts/pruebas_chatbot.md). En el proyecto se registraron 13 llamadas reales en total: cinco B, cuatro de una primera ronda C y cuatro de la ronda final C. La primera ronda C se conserva como historial en [chatbot-v1](../prompts/evidencias/chatbot-v1-20261019T202737Z.md). Estas salidas del proveedor son evidencia real de respuestas; los criterios y su evaluación siguen siendo revisión humana.

La suite técnica se inicia con `./scripts/bootstrap.ps1 -Technical` y se ejecuta con `python scripts/integracion_tecnica.py`. Usa un doble HTTP determinista, no DeepSeek. Sus fixtures verifican contratos y ramas, y no deben presentarse como respuestas reales de un modelo.

Para repetir B1–B5, el runner ahora exige `python scripts/probar_flujo_real.py --allow-notifications`. Una corrida completa hace cinco llamadas reales al proveedor, crea cuatro solicitudes nuevas y puede enviar hasta tres correos (B1, B3 y B4); la bandera autoriza explícitamente ese efecto y el runner no puede verificar la configuración SMTP desde fuera del contenedor. Sin la bandera termina antes de hacer solicitudes HTTP. Para repetir C1–C4, `python scripts/probar_chatbot.py` consume cuatro llamadas reales y actualiza el archivo de resultados. No ejecutes estos comandos solo para consultar las evidencias existentes.

Consulta el [estado actual del proyecto](../docs/ESTADO_ACTUAL.md) y la [guía de sustentación](../docs/SUSTENTACION.md) para ver límites, reproducción y explicación de la solución. La configuración local está en `.env`; no se incluye en el export ni en Git.
