# Guía breve de sustentación y práctica

El objetivo es explicar el flujo como una integración controlada entre n8n, una API y SQLite, y demostrar una modificación pequeña sin consumir DeepSeek ni enviar correo. El [video final de 4:09](../flujo/evidencias/video/sustentacion-anexo-b.mp4) ya está incorporado; recorre los bloques 01–04 y las ejecuciones guardadas 15–19. Las vistas históricas de ejecuciones conservan su distribución anterior, mientras el editor muestra el layout organizado. El [estado actual](ESTADO_ACTUAL.md) y los [criterios de entrega](CRITERIOS_ENTREGA.md) enlazan las evidencias y los faltantes.

## Recorrido de la solución

1. Abre el editor n8n en `http://127.0.0.1:5688` y muestra **Solicitudes con IA - Suministros Andinos**. El webhook recibe `cliente_email` y `mensaje`; `Idempotency-Key` permite repetir la recepción sin crear otra.
2. Explica por qué la API persiste primero una recepción. Después **Consultar cliente** y **Consultar catálogo** aportan datos vigentes. Un cliente desconocido sigue a la extracción y al final va a revisión manual.
3. En **DeepSeek extracción intento 1**, muestra `/chat/completions`, JSON mode, `thinking` desactivado, temperatura cero y límite de salida. El LLM propone campos; Code hace el parseo y valida los cinco campos, tipos y enums. Si JSON o esquema falla, el flujo hace como máximo un segundo intento.
4. En **Resolver cliente y producto**, explica normalización y alias explícitos. El flujo exige una coincidencia única. Producto desconocido o ambiguo y datos insuficientes van a revisión; no se inventan asociaciones.
5. **Crear solicitud** llama a la API, que es autoridad sobre relaciones, stock y persistencia. El pedido se guarda aunque supere existencias, con `sin_stock` y los motivos correspondientes. No se descuenta ni reserva inventario.
6. El flujo conserva la respuesta de webhook: 201 para solicitud registrada, 202 para revisión, 422 para entrada inválida y 503 para indisponibilidad. La API crea alertas en outbox; SMTP puede aceptar un mensaje sin demostrar su llegada a bandeja.
7. En `http://127.0.0.1:18018/docs`, muestra `GET /clientes`, `GET /productos`, creación y consulta de solicitudes. Explica que los 21 tests de API usan bases temporales.

La ejecución documentada incluye B1–B5 reales con DeepSeek (5/5), C1–C4 en la ronda final (4/4 revisadas), 21 tests de API y 16 grupos/107 aserciones en la integración técnica aislada. El total documentado es de 22 llamadas reales al proveedor y la base normal tiene 72 solicitudes después de la segunda corrida B1–B5 (ejecuciones 15–19). El fixture técnico verifica ramas HTTP, no calidad del modelo. SMTP aceptó cuatro mensajes; el usuario confirmó la llegada de los dos primeros. La llegada de los dos HTML más recientes sigue sin confirmarse, y las notificaciones 1–3 permanecen pendientes.

## Cómo explicarlo si vienes de OpenClaw

OpenClaw permite plantear un agente que elige herramientas según la conversación. Aquí se pidió una automatización visual: n8n hace visible el orden y las bifurcaciones; el modelo solo propone la clasificación; la API valida reglas, identidad, stock y persistencia. El grafo es deliberadamente limitado y se puede auditar ejecución por ejecución.

En n8n, cada nodo recibe elementos JSON. Las conexiones expresan secuencia, IF abre ramas, Code transforma/valida y HTTP Request consume API. En esta versión los nodos HTTP reemplazan el elemento de entrada; los nodos Code posteriores reponen el contexto. Al depurar, compara entrada y salida del nodo que primero perdió o cambió un campo.

## Práctica segura en vivo

Comprueba primero los servicios y las pruebas unitarias; estos comandos no llaman al LLM ni envían correo:

```powershell
docker compose ps
Invoke-RestMethod http://127.0.0.1:18018/health
python -m pytest -q
```

Para modificar un nodo, usa el perfil técnico aislado: abre `http://127.0.0.1:5689`, explica un caso B y cambia un alias explícito en **Resolver cliente y producto**. Luego ejecuta la integración técnica, que usa un doble HTTP local, tiene SMTP deshabilitado y no hace llamadas reales a DeepSeek:

```powershell
./scripts/bootstrap.ps1 -Technical
python scripts/integracion_tecnica.py
```

No uses `scripts/probar_flujo_real.py --allow-notifications`, `scripts/probar_chatbot.py` ni `scripts/probar_notificaciones_reales.py` durante la práctica: llaman a DeepSeek; el runner B puede enviar hasta tres correos y cada runner de notificaciones envía dos. Sin `--allow-notifications`, el runner B falla antes de cualquier solicitud HTTP. No copies `.env` ni exportes credenciales. Para apagar el perfil técnico y conservar sus volúmenes:

```powershell
docker compose -f compose.yaml -f compose.tecnico.yaml -p lider-ia-tecnico down
```

## Preguntas conceptuales para la entrevista

- **Alucinaciones:** leer el catálogo vigente, limitar el contexto, pedir aclaración si falta información y validar antes de persistir. Un prompt reduce riesgo, pero no garantiza exactitud.
- **RAG:** recuperar fragmentos pertinentes de una base de conocimiento cuando el contenido crece o cambia; para doce productos basta una consulta directa.
- **Function calling:** el modelo puede proponer `consultar_solicitud(id)`, pero la aplicación autentica y autoriza al usuario antes de llamar `GET /solicitudes/{id}`.
- **Chatbot y agente:** un agente puede proponer o ejecutar herramientas acotadas; la API sigue aplicando permisos y reglas.
- **Costo:** medir tokens por caso, limitar contexto, salida y reintentos, deduplicar y elegir modelo según calidad medida. No proyectar factura sin precios vigentes y consumo observado.

Para revisar una respuesta del chatbot, consulta [respuestas conceptuales](../prompts/respuestas.md) y [pruebas reales C1–C4](../prompts/pruebas_chatbot.md). El usuario dio por lista la etapa de rediseño HTML en la conversación; los PNG son renders estáticos, no una verificación visual automatizada de Gmail u Outlook.
