# Retomar la entrega

Este archivo conserva el contexto para continuar la entrega en una nueva conversación. El proyecto está en `C:\Users\Usuario\Documents\proyectos personales\lider-automatizacion-ia`.

## Estado confirmado

- El repositorio público es [Kub1-rg/lider-automatizacion-ia](https://github.com/Kub1-rg/lider-automatizacion-ia), rama `main`. El último commit antes de agregar este handoff es `f0ad49a`; el agente principal se encarga de Git.
- La documentación de esquema, decisiones técnicas y plan de cierre está en [README.md](../README.md), [estado actual](ESTADO_ACTUAL.md), [criterios de entrega](CRITERIOS_ENTREGA.md) y [plan de cierre](PLAN_CIERRE.md).
- El proyecto aprobó 21 pruebas pytest (API, plantillas y protección del runner). La integración del workflow aprobó 16 grupos y 107 aserciones con fixture local; esa suite no cuenta como clasificación real del proveedor.
- B1–B5 se ejecutaron con DeepSeek real: 5/5 respuestas correctas para los casos revisados, una llamada por caso, ejecuciones n8n 6–10, recepciones 3–7 y solicitudes 61–64. B5 quedó en revisión para cliente desconocido, sin crear solicitud.
- Las evidencias conservadas contabilizan 17 llamadas reales al modelo y la lectura actual confirma 68 solicitudes. Actualizar estas cifras solo si hay nuevas ejecuciones documentadas; consultar evidencias o hacer lecturas de estado no requiere repetir llamadas al modelo.
- SMTP aceptó cuatro notificaciones en total. El usuario confirmó conversacionalmente que recibió las asociadas a las solicitudes 65 y 66. Para HTML, SMTP aceptó notificaciones 6 y 7 (solicitudes 67 y 68), un intento cada una; el usuario dio aceptación conversacional del diseño. No hay una verificación automatizada de entrega o renderizado en Gmail. Las notificaciones outbox 1–3 siguen pendientes y no se reenviaron.
- Corte de solo lectura del runtime (2026-10-19 22:31:26 UTC): 12 clientes, 12 productos, 68 solicitudes, 11 recepciones y 7 notificaciones. Notificaciones 1–3 permanecen pendientes con cero intentos; 4–7 están enviadas con un intento cada una. SMTP está habilitado en el runtime y configurado para autoentrega; no se registraron ni reproducen aquí valores de destinatario. No se recreó ningún servicio en esa verificación.
- El video [demostración-anexo-b.mp4](../flujo/evidencias/video/demostracion-anexo-b.mp4) dura 156 segundos y reproduce trazas JSON reales. No es captura de la interfaz n8n ni reemplaza una grabación en vivo si la evaluación la exige. Hashes y manifiestos de evidencia se conservaron.
- Servicios locales: n8n en `http://127.0.0.1:5688`, API/Swagger en `http://127.0.0.1:18018/docs`. El perfil técnico aislado usa puertos 5689/18019/5690 y en el último estado estaba detenido. No exponer estos servicios a Internet; el repositorio público contiene código, no un despliegue público.
- La semilla original conserva SHA-256 `65cd979a28b746b7ca8753b97399789c6f5d864f68424aa8a7a0698ed6ac648f`. `.gitattributes` preserva los bytes de la semilla, workflow, prompts y evidencias para mantener sus hashes; no normalizar esos artefactos al retomar.

## Siguiente trabajo

La documentación está lista. El siguiente paso es comprobar si la sesión puede usar Chrome y, si el acceso está autorizado, preparar una captura real de los cinco casos en un máximo de cinco minutos. Luego se puede practicar la sustentación y hacer una modificación pequeña en vivo. LangGraph para un GET de solo lectura es un bonus opcional, posterior a los requisitos principales.

La sesión de CUA encontró dos perfiles de Chrome, pero el acceso al n8n local `http://127.0.0.1:5688` fue denegado por la política guardada. La pantalla mostraba la extensión instalada y el ajuste de navegación «Permitir siempre», sin excepciones visibles. La causa de la discrepancia no está confirmada. El último control de UI rechazó el acceso: **no se debe dar por resuelto**.

Para retomarlo, inicia una conversación nueva y selecciona `@Chrome` según la guía oficial de [la extensión de ChatGPT para Chrome](https://learn.chatgpt.com/docs/chrome-extension). Si persiste la denegación, reinicia la aplicación/navegador y vuelve a comprobar permisos de forma normal. No intentes eludir la política con localhost alternativo, otra puerta o proxy, CDP sin autorización, ni otro perfil. Los identificadores de pestañas pueden cambiar tras reinstalar; toma un inventario nuevo y no reutilices IDs previos.

## Seguridad y reproducción

- No abrir, copiar ni mostrar `.env`, claves, contraseñas, destinatarios, cabeceras de correo ni salida de `docker inspect`/`docker compose config`. Evitar capturas que incluyan el escritorio o información personal.
- No ejecutar nuevos runners de DeepSeek o SMTP durante la fase de documentación o preparación de UI.
- Como SMTP está habilitado en el runtime del corte indicado, cualquier nueva corrida podría enviar correo. Mantener esta precaución hasta verificar explícitamente una configuración segura para la grabación.
- `python scripts/probar_flujo_real.py --allow-notifications` crea cuatro solicitudes nuevas, consume cinco llamadas reales a DeepSeek y puede enviar hasta tres correos. No iniciarlo antes de que la captura esté lista y coordinada. Nunca ejecutarlo solo para leer evidencia.
- El guion [GRABACION_REAL.md](GRABACION_REAL.md) contempla deshabilitar temporalmente las notificaciones en **solo la API**, mediante un override temporal fuera del repositorio, comprobar el estado antes de la corrida y restaurar la configuración después. No editar `.env`; coordinar ese procedimiento con el agente principal justo antes de grabar. El usuario no necesita hacer ese cambio durante este handoff.
- Para inspeccionar el repositorio sin efectos secundarios: `git status --short`, `git log -1 --oneline` y lectura de los documentos/evidencias ya guardados. No ejecutar runners al revisar resultados.

## Evidencias y documentos de referencia

- [Enunciado PDF original](../material/Prueba_Tecnica_Lider_Automatizacion_IA.pdf) y [datos SQL originales](../material/datos_prueba.sql)
- [Plan técnico inicial de Astra](PLAN_ASTRA.md), implementado con Luna en esfuerzo alto; es un plan histórico, no el estado vigente
- [Estado y resultados](ESTADO_ACTUAL.md)
- [Guía para la sustentación](SUSTENTACION.md)
- [Guion de grabación real](GRABACION_REAL.md)
- [Plan de cierre](PLAN_CIERRE.md)
- [Criterios de entrega](CRITERIOS_ENTREGA.md)
- [Ejecución real B1–B5](../flujo/evidencias/real/flujo-real-20261019T202729Z-afcf5fa1.json)
- [Resultados reales del chatbot C1–C4](../prompts/pruebas_chatbot.md)
- [Evidencia de notificaciones SMTP](../flujo/evidencias/correo/README.md)
- [Evidencia de notificaciones HTML](../flujo/evidencias/correo-html/README.md)
- [Video explicativo de trazas](../flujo/evidencias/video/demostracion-anexo-b.mp4)

## Mensaje inicial sugerido para la nueva conversación

> Continúa el proyecto `C:\Users\Usuario\Documents\proyectos personales\lider-automatizacion-ia`. Lee primero `docs/RETOMAR_SESION.md`, `docs/ESTADO_ACTUAL.md` y `docs/GRABACION_REAL.md`. La documentación, el repositorio público y las pruebas existentes ya están cerrados; no repitas las 17 llamadas reales ni los envíos. El pendiente es revisar el acceso autorizado a Chrome para una posible captura en vivo de B1–B5, máximo cinco minutos. El último acceso a `http://127.0.0.1:5688` fue rechazado por política guardada y sigue sin resolver. No intentes eludirla. Antes de ejecutar cualquier runner, explica el costo y posibles efectos con base en el guion y coordina la preparación temporal de la API con notificaciones deshabilitadas. No muestres secretos ni datos personales. El bonus LangGraph es opcional.
