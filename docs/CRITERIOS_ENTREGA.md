# Checklist trazable de entrega

Este checklist contrasta el [enunciado PDF](../material/Prueba_Tecnica_Lider_Automatizacion_IA.pdf) y su [transcripción de texto](../material/enunciado.txt) con los archivos y evidencias actuales. Distingue implementación probada de entregables pendientes; no equivale a una calificación externa.

## Ejercicio 1 — Flujo de automatización con IA (PDF, pp. 2–3)

| Criterio | Implementación/evidencia | Estado |
|---|---|---|
| Webhook recibe email y mensaje, clasifica con LLM, valida JSON y reintenta una vez | [Workflow n8n 2.43.8](../flujo/solicitudes.json); [evidencia B1–B5](../flujo/evidencias/real/flujo-real-20261019T202729Z-afcf5fa1.json) | Verificado. Cinco llamadas reales al clasificador, una por caso; respuestas HTTP 200. |
| Asociar cliente/producto, crear solicitud y manejar alertas de queja, urgencia y stock | API valida relaciones y stock; evidencia B1–B5 y [pruebas SMTP](../flujo/evidencias/correo/README.md), [prueba HTML](../flujo/evidencias/correo-html/README.md) | Verificado en los casos reales y en 16 grupos/107 aserciones técnicas. Los fixtures técnicos son simulados y se reportan aparte. |
| Exportar workflow y documentar prompt clasificador | [solicitudes.json](../flujo/solicitudes.json), [clasificador.md](../prompts/clasificador.md) | Completo. |
| Video de hasta cinco minutos o capturas procesando los cinco casos B | [Video explicativo de trazas reales](../flujo/evidencias/video/demostracion-anexo-b.mp4) (2:36, 1280×720) y [JSON detallado](../flujo/evidencias/real/flujo-real-20261019T202729Z-afcf5fa1.json) | Parcial: explica las cinco trazas reales, pero no graba la interfaz n8n. Si el evaluador requiere captura UI, queda ese riesgo residual. |

## Ejercicio 2 — API REST (PDF, pp. 3–4)

| Criterio | Implementación/evidencia | Estado |
|---|---|---|
| Endpoints de clientes, productos y solicitudes; filtros, detalle y cambio de estado | [API](../api/main.py); Swagger local `http://127.0.0.1:18018/docs` | Implementado; smoke normal respondió HTTP 200. |
| Validaciones de tipo/urgencia/estado, regla de stock y errores HTTP | [API](../api/main.py), [pruebas automatizadas](../tests) | Implementado; 21 pruebas pytest aprobadas. |
| Probar con datos SQL suministrados sin alterarlos | [Semilla](../material/datos_prueba.sql), [estado de pruebas](ESTADO_ACTUAL.md) | Verificado con base temporal; la base normal conserva 68 solicitudes y el seed de 60. |

## Ejercicio 3 — Consultas SQL (PDF, p. 4)

| Criterio | Implementación/evidencia | Estado |
|---|---|---|
| Seis consultas legibles con JOIN, agregaciones y ventana/subconsulta | [consultas.sql](../sql/consultas.sql) | Completo. |
| Resultados sobre una copia de la base de ejemplo | Las pruebas de API ejecutan las consultas sobre base temporal | Verificado; los datos originales no se modificaron. |

## Ejercicio 4 — Prompt engineering y conceptos (PDF, pp. 4–5)

| Criterio | Implementación/evidencia | Estado |
|---|---|---|
| Prompt de sistema: dominio acotado, no inventar, empatía, privacidad y tono | [chatbot_sistema.md](../prompts/chatbot_sistema.md) | Completo. |
| Probar Anexo C y conservar las respuestas reales | [pruebas_chatbot.md](../prompts/pruebas_chatbot.md), [respuestas iniciales](../prompts/evidencias/chatbot-v1-20261019T202737Z.md) | Ronda final C1–C4 revisada, 4/4 acordes con el comportamiento esperado; la ronda inicial se conserva como historial. |
| Explicar RAG, function calling, agente/chatbot y costo | [respuestas.md](../prompts/respuestas.md) | Completo; cada respuesta se limita a ocho líneas. |

## Documentación, seguridad y operación (PDF, p. 6)

- [x] README explica instalación, ejecución, elecciones y decisiones; `.env.example` no contiene credenciales.
- [x] [Sustentación](SUSTENTACION.md) contiene recorrido del grafo y una práctica técnica aislada, sin llamadas reales al LLM ni envío de correo.
- [x] Se registran 17 llamadas reales al proveedor, 68 solicitudes, 21 pruebas pytest y los límites de la evidencia. La integración técnica usa un doble HTTP, no DeepSeek.
- [x] SMTP aceptó los avisos reales; el usuario confirmó la llegada de los dos primeros. Los dos mensajes HTML más recientes siguen pendientes de confirmación en bandeja. Los avisos outbox 1–3 continúan pendientes.
- [x] Los PNG de correo son renders estáticos. El usuario indicó “Listo” tras revisar la etapa HTML; esto se registra como aceptación conversacional, no como verificación automatizada en Gmail u Outlook.
- [ ] Falta la evidencia visual exigida para los cinco casos del Anexo B.
- [ ] Falta la sustentación final y la modificación pequeña en vivo con el evaluador.
- [x] Repositorio Git público publicado: [Kub1-rg/lider-automatizacion-ia](https://github.com/Kub1-rg/lider-automatizacion-ia), rama `main` con el contenido de la entrega.

## Bonus y decisiones fuera de alcance

El PDF otorga hasta 10 puntos opcionales por Power BI, LangChain/LangGraph, una segunda API Node.js o despliegue en servidor. No se implementó bonus. No es requisito para cerrar los ejercicios 1–4. La entrega está publicada; consultar este checklist no activa pruebas adicionales de correo/LLM.
