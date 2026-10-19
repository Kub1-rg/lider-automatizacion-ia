# Plan de cierre

El orden acordado es **documentación → grabación real → sustentación → bonus opcional**. Los criterios describen trabajo pendiente; no declaran cerradas las etapas futuras.

| Etapa | Alcance | Criterio de cierre |
|---|---|---|
| 1. Documentación | Completar README con esquema ampliado, elección de herramientas y contexto del catálogo; preparar el plan y el guion. | README contrastado con el código; enlaces y documentos revisados; evidencias auditadas conservadas. **Cerrada.** El [estado actual](ESTADO_ACTUAL.md) conserva los resultados verificados. |
| 2. Grabación real | Captura de 3–4 minutos, máximo 5, de la interfaz n8n y una nueva corrida B1–B5 coordinada; detalles en [GRABACION_REAL.md](GRABACION_REAL.md). | Video/capturas muestran la ejecución real y sus resultados, distinguen B5 como revisión sin solicitud, omiten secretos y no presentan una explicación estática como captura. Aún no grabado. |
| 3. Simulacro y sustentación | Recorrido hablado del diseño, casos, reglas de stock, idempotencia, límites y una modificación pequeña que solicite el usuario. | El usuario puede explicar y defender las decisiones; los cambios en vivo se prueban sin exponer credenciales ni alterar datos fuera del alcance. Pendiente de coordinación. |
| 4. Bonus opcional | Evaluar LangGraph para un GET de lectura únicamente, después de completar los ejercicios obligatorios y la sustentación. | Decisión explícita de continuar, alcance acotado, integración separada y pruebas propias. No bloquea la entrega obligatoria y no está implementado. |

Chrome ya aparece conectado, pero el último intento de leer n8n fue rechazado por una política de permisos guardada para `http://127.0.0.1:5688`. La captura compartida por el usuario muestra navegación predeterminada en «Permitir siempre», sin excepciones visibles; la causa de la discrepancia no está confirmada. El [punto de continuación](RETOMAR_SESION.md) documenta cómo retomar la comprobación en una nueva conversación con `@Chrome`, sin eludir el bloqueo.

No se reinician servicios ni se llama a DeepSeek/SMTP hasta que la grabación esté preparada y coordinada. El runner B consume cinco llamadas reales, crea cuatro solicitudes nuevas y puede generar hasta tres correos: la API debe estar temporalmente configurada con notificaciones deshabilitadas, con verificación previa y restauración al terminar, sin editar `.env`. La guía de grabación documenta ese control. No mostrar el archivo `.env`, `docker compose config`, secretos ni salida de inspección de contenedores.
