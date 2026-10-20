# Retomar la entrega

Proyecto: `C:\Users\Usuario\Documents\proyectos personales\lider-automatizacion-ia`.
Repositorio: [Kub1-rg/lider-automatizacion-ia](https://github.com/Kub1-rg/lider-automatizacion-ia), rama `main`.

## Estado al cierre

- Ejercicios obligatorios implementados con evidencias históricas: 21 pruebas API, 16 grupos/107 aserciones de integración técnica y C1–C4 reales revisados 4/4. No se repitieron suites al cerrar la entrega.
- Dos corridas B1–B5 reales, ambas 5/5. La [segunda](../flujo/evidencias/real/flujo-real-20261019T230505Z-1df02d8d.json) usó ejecuciones n8n 15–19, recepciones 12–16 y solicitudes 69–72. B5 quedó en revisión manual sin crear solicitud. Un intento LLM por caso.
- Total documentado: **22 llamadas reales** al proveedor, incluidas cinco de la segunda corrida. No repetir llamadas para leer evidencia.
- Lectura del runtime del 2026-10-20 04:04 UTC (19 de octubre, Colombia): 12 clientes, 12 productos, 72 solicitudes, 16 recepciones y 10 notificaciones. Cuatro enviadas, un intento cada una; seis pendientes, cero intentos. No se reenviaron pendientes.
- SMTP está habilitado en la configuración normal restaurada de API. El usuario confirmó la llegada de mensajes de solicitudes 65/66 y aceptó conversacionalmente el diseño HTML. No existe verificación automatizada de entrega/render en Gmail.
- **Video final:** [sustentacion-anexo-b.mp4](../flujo/evidencias/video/sustentacion-anexo-b.mp4), 4:09.45, captura del usuario de n8n/API. Explica ejecuciones guardadas; no muestra una nueva corrida durante la grabación. Se recortaron barras del navegador/Windows y se conservó el audio. [Índice](../flujo/evidencias/video/README.md) y [manifiesto](../flujo/evidencias/video/manifiesto-sustentacion.json). La revisión visual fue por muestreo; no se transcribió ni certificó toda la narración.
- La única grabación de entrega es `sustentacion-anexo-b.mp4`. Se retiró el MP4 anterior generado con placas; se conservaron las evidencias JSON y su manifiesto histórico.
- **Acceso autorizado a Chrome/n8n verificado.** El bloqueo histórico de permisos fue superado en esta sesión; no es un pendiente actual. Los IDs de pestaña cambian: obtener inventario nuevo si se necesita UI.
- Workflow organizado y publicado: 69 nodos funcionales, nueve notas, ocho bloques y guía de lectura. Se comparó export antes/después: solo posiciones y notas, mismos parámetros funcionales y conexiones. Script: `scripts/organizar_workflow.py`. Respaldo local excluido de Git: `.runtime/visual-backup/`.
- SHA-256 actual del workflow: `5bd008ad567cc279f09fa7b6bb32b58227c333064a636b3331e32f48916d421d`. Los manifiestos antiguos conservan los hashes de las versiones históricas.
- Semilla original intacta: `65cd979a28b746b7ca8753b97399789c6f5d864f68424aa8a7a0698ed6ac648f`. Preservar bytes y finales de línea de los artefactos.
- Servicios: n8n `http://127.0.0.1:5688`, API `http://127.0.0.1:18018/docs`, vinculados a loopback. No exponer a Internet. Perfil técnico separado: 5689/18019/5690; no asumir que está activo.

## Pendiente

Compartir el enlace del repositorio con el evaluador mediante el canal que el usuario elija. No se ha enviado ningún mensaje externo desde esta sesión. Después de entregar: sustentación técnica y modificación pequeña en vivo; guía en [SUSTENTACION.md](SUSTENTACION.md). El bonus LangGraph es opcional y no está implementado.

## Seguridad y reproducción

- No abrir, copiar ni mostrar `.env`, claves, contraseñas, destinatarios, cabeceras de correo ni salida de `docker inspect`/`docker compose config`.
- No ejecutar nuevos runners de DeepSeek/SMTP para preparar documentación, revisar video o leer evidencia.
- Una corrida `python scripts/probar_flujo_real.py --allow-notifications` consume cinco llamadas, crea cuatro solicitudes y puede enviar hasta tres correos. La bandera no comprueba el estado SMTP.
- Para grabar otra corrida sin correos, seguir [GRABACION_REAL.md](GRABACION_REAL.md): override temporal fuera del repositorio, recrear solo API con notificaciones deshabilitadas, verificar antes y restaurar al terminar. No editar `.env`.
- El permiso autorizado de Chrome se verifica por las herramientas normales; nunca eludir una denegación con otro host, puerto, proxy o perfil.
- Lecturas seguras: `git status --short`, `git log -1 --oneline`, documentos y evidencias guardadas. No repetir pruebas por rutina.

## Referencias

- [Estado actual](ESTADO_ACTUAL.md), [criterios de entrega](CRITERIOS_ENTREGA.md) y [plan de cierre](PLAN_CIERRE.md).
- [Video final](../flujo/evidencias/video/sustentacion-anexo-b.mp4) y [evidencia B1–B5 reciente](../flujo/evidencias/real/flujo-real-20261019T230505Z-1df02d8d.json).
- [Respuestas reales C1–C4](../prompts/pruebas_chatbot.md), [SQL](../sql/consultas.sql) y [notificaciones HTML](../flujo/evidencias/correo-html/README.md).
- [Enunciado](../material/enunciado.txt) y PDF original en `material/`.
