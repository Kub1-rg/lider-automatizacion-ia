# Automatización de solicitudes con IA

Prototipo local para recibir solicitudes de clientes, clasificarlas con un modelo configurable y registrarlas mediante una API FastAPI en SQLite. n8n coordina el flujo; la API valida y persiste los datos. El proyecto se prepara para ejecución local en Windows con Docker Desktop.

**Entrega actualizada el 19 de octubre de 2026 (Colombia):** API aprobada con 21 pruebas, suite técnica n8n de 16 grupos/107 aserciones, dos corridas B1–B5 con DeepSeek real (5/5 cada una) y chatbot C1–C4 revisado (4/4). La [grabación final de la interfaz n8n y API](flujo/evidencias/video/sustentacion-anexo-b.mp4) dura **4:09**, dentro del máximo de cinco minutos. Muestra el workflow organizado y resultados de ejecuciones guardadas. Consulta el [estado detallado y las evidencias](docs/ESTADO_ACTUAL.md).

Repositorio público de entrega: [Kub1-rg/lider-automatizacion-ia](https://github.com/Kub1-rg/lider-automatizacion-ia). El código, las pruebas y las evidencias están publicados en la rama `main`.

Para continuar en otra conversación, empieza por [RETOMAR_SESION.md](docs/RETOMAR_SESION.md): resume resultados, video final, configuración operativa y preparación para la sustentación. El acceso autorizado a Chrome/n8n fue comprobado.

La documentación y la grabación están preparadas para entregar mediante este repositorio. El [plan de cierre](docs/PLAN_CIERRE.md) deja pendiente la sustentación con el evaluador y una modificación pequeña en vivo; el bonus es opcional. El [guion de grabación](docs/GRABACION_REAL.md) se conserva como referencia para reproducir la demostración.

## Inicio local

Requisitos: Windows 10/11, PowerShell, Git y Docker Desktop iniciado. Python 3.11 o 3.12 en el host se necesita solo para ejecutar el script de evidencia integrada. El primer arranque descarga las imágenes y puede tardar varios minutos.

1. Abre PowerShell en la carpeta del repositorio.
2. Ejecuta `Copy-Item .env.example .env` si el archivo `.env` aún no existe. El `.env` es local e ignorado por Git; no copies su contenido a chats, capturas ni commits. La plantilla deja SMTP deshabilitado por defecto.
3. Ejecuta `./scripts/bootstrap.ps1`. El script construye e inicia la API y n8n, importa el workflow y lo publica con la CLI de n8n. Si es una instalación nueva y n8n solicita crear el propietario, hazlo en `http://127.0.0.1:5688` y vuelve a ejecutar el script. La cuenta es local y la crea el usuario; el repositorio no genera ni guarda contraseñas.
4. Abre la documentación de API en `http://127.0.0.1:18018/docs` y el editor n8n en `http://127.0.0.1:5688`.
5. Ejecuta `./scripts/smoke.ps1` para comprobar la respuesta HTTP de la API, OpenAPI y n8n.

La configuración local ya está preparada para DeepSeek. Si necesitas recrear los servicios normales, ejecuta `./scripts/bootstrap.ps1`. Para repetir C1–C4 ejecuta `python scripts/probar_chatbot.py`; son cuatro llamadas reales al proveedor y se actualiza `prompts/pruebas_chatbot.md`. Para repetir B1–B5 el comando ahora exige `python scripts/probar_flujo_real.py --allow-notifications`: una corrida completa genera cuatro solicitudes nuevas, consume cinco llamadas reales al proveedor y puede enviar hasta tres correos (B1, B3 y B4). Sin la bandera el runner termina antes de hacer solicitudes HTTP. No ejecutes estos comandos solo para consultar los resultados guardados. No compartas la configuración local en el chat ni en capturas.

El webhook del workflow se publica en `POST http://127.0.0.1:5688/webhook/solicitud`. El cuerpo esperado contiene `cliente_email` y `mensaje`; el flujo puede usar el encabezado `Idempotency-Key` para que una repetición conserve su identidad. Entre contenedores, el flujo accede a la API por `http://api:8000`.

### Lectura visual del workflow

El editor organiza los 69 nodos funcionales en bloques con notas de color. Para sustentar, sigue la columna principal: **01 Recepción e idempotencia → 02 Contexto desde la API → 03 Clasificación con IA → 04 Registro y alertas**. Acerca el zoom al bloque que estés explicando. A la derecha están **05 Corrección**, **06 Registro después de corregir** y **07 Revisión humana**; el bloque **08** reúne los fallos de configuración y API. Los nodos auxiliares de contexto conservan los datos entre llamadas HTTP.

La reorganización visual conserva los parámetros de los 69 nodos y todas las conexiones, y añade nueve notas. Se verificó mediante comparación estática del export anterior y posterior del runtime, sin ejecutar webhooks, LLM ni SMTP. Los hashes históricos de evidencia corresponden a la versión anterior al cambio de posiciones y notas. `python scripts/organizar_workflow.py` reproduce esta distribución sobre el JSON del repositorio; para llevarla a n8n hay que importar y publicar el workflow.

La API ofrece `GET /clientes?email=...`, `GET /productos?q=...`, `POST /solicitudes`, `GET /solicitudes` con filtros y paginación, `GET /solicitudes/{id}` y `PATCH /solicitudes/{id}` para el estado. Swagger en `/docs` describe campos y respuestas. Para idempotencia, repetir `POST /recepciones` o el webhook con la misma `Idempotency-Key` y el mismo cuerpo devuelve la recepción existente; reutilizar esa clave con otro cuerpo responde `409`. Las recepciones se pueden consultar y actualizar con `GET/PATCH /recepciones/{id}`.

## Integración técnica aislada

Para ensayar el workflow contra un proveedor determinista sin cambiar `.env` ni las variables del entorno productivo, ejecuta `./scripts/bootstrap.ps1 -Technical`. Esta instancia usa un proyecto y volúmenes Compose independientes, API en `127.0.0.1:18019`, n8n en `127.0.0.1:5689` y un doble HTTP en `127.0.0.1:5690`. La clave configurada en esa instancia es un literal de prueba que solo acepta el stub local. Su configuración fija `NOTIFICATIONS_ENABLED=false` y deja vacías las variables SMTP, incluso si `.env` contiene credenciales.

Ejecuta `python scripts/integracion_tecnica.py` para enviar los cinco mensajes B, probar JSON malformado y esquema inválido antes de respuestas válidas, dos fallos, múltiples productos, producto desconocido, errores 401/503, corte de conexión, repetición idempotente y conflicto de clave/cuerpo vía webhook. El script reinicia el contador del doble local antes de cada corrida, llama al webhook real de n8n y guarda un JSON con respuestas y resultados en `flujo/evidencias/tecnica/`. Esa evidencia es una simulación técnica del contrato y las ramas del flujo; no demuestra clasificación con DeepSeek ni entrega de email. Para revisar el estado HTTP del perfil técnico, define `$env:AUTOMATIZACION_TECNICA='1'` antes de ejecutar `./scripts/smoke.ps1`.

Para detener el perfil técnico y borrar solo sus bases/configuración separadas: `docker compose -f compose.yaml -f compose.tecnico.yaml -p lider-ia-tecnico down -v`. Elimina volúmenes de ese proyecto técnico.

Comandos útiles: `docker compose ps`, `docker compose logs -f api`, `docker compose logs -f n8n` y `docker compose down`. Los datos persisten en volúmenes de Docker. `docker compose down -v` elimina también la base y los datos de n8n; úsalo solo si quieres reiniciar el prototipo desde cero.

Para ejecutar las pruebas automatizadas de API desde un entorno Python 3.11/3.12, instala `python -m pip install -r api/requirements.txt` y ejecuta `python -m pytest -q`. Las pruebas usan bases temporales.

## Servicios y configuración

- **API:** Python 3.12 slim y FastAPI, publicada solo en `127.0.0.1:18018`. SQLite vive en el volumen `solicitudes_data` y la semilla original se copia a la imagen desde `material/datos_prueba.sql`.
- **Flujo:** n8n `2.43.8`, publicado solo en `127.0.0.1:5688`; su configuración y workflows residen en `n8n_data`. El workflow exportado está en `flujo/solicitudes.json`.
- **LLM:** el `.env` local de este equipo está configurado para DeepSeek con el modelo indicado por `DEEPSEEK_MODEL`; el archivo no se incluye en Git. Para otra instalación, define `DEEPSEEK_API_KEY` en su propio `.env`. Los dobles locales se identifican como tales y no cuentan como evidencia real del proveedor.
- **Notificaciones:** `.env.example` deja `NOTIFICATIONS_ENABLED=false`. El usuario confirmó que llegaron los dos mensajes asociados a solicitudes 65 y 66; el [ensayo SMTP HTML](flujo/evidencias/correo-html/README.md) registra aceptación SMTP para solicitudes 67 y 68, sin confirmar llegada a la bandeja. Los avisos previos 1–3 siguen pendientes. Los PNG son renders estáticos del HTML y no validan Gmail. No ejecutes `python scripts/probar_flujo_real.py --allow-notifications`, `python scripts/probar_notificaciones_reales.py` ni `python scripts/probar_notificaciones_reales.py --html` solo para consultar artefactos: el runner B puede enviar tres correos; cada runner de notificaciones envía dos correos y consume llamadas reales a DeepSeek. SMTP y el destinatario se configuran solo en el `.env` local con `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_STARTTLS` y `NOTIFICATION_TO`; nunca compartas esos valores.

El acceso de workflows a variables del entorno de n8n está habilitado para que el workflow lea la configuración local (`N8N_BLOCK_ENV_ACCESS_IN_NODE=false`). Por ello el editor queda vinculado a loopback y este Compose es para desarrollo en el equipo, no para publicar en Internet.

En n8n `2.43.8`, Compose fija `N8N_USE_WORKFLOW_PUBLICATION_SERVICE=false` para que importar/publicar con la CLI registre también el webhook HTTP en el arranque local. `/healthz` puede responder antes de que el webhook esté registrado; `bootstrap.ps1` reintenta la entrada inválida hasta 45 segundos y espera HTTP 422 antes de dar el inicio por terminado.

## Elecciones técnicas

- **FastAPI y Pydantic:** FastAPI expone la API HTTP y Pydantic define los contratos tipados de entrada y validación. Swagger/OpenAPI se genera en `/docs`, lo que permite inspeccionar rutas, esquemas y respuestas durante la revisión.
- **SQLite:** la base usa la semilla local `material/datos_prueba.sql` dentro de un archivo persistido en un volumen Docker. Evita depender de un servidor de base de datos separado y facilita repetir el prototipo con los mismos datos. La semilla se conserva sin modificar.
- **n8n:** se eligió como plataforma visual requerida por el alcance acordado, entre las opciones del enunciado, para mostrar el grafo de webhook, llamadas HTTP, validaciones y bifurcaciones. Como analogía con OpenClaw, la diferencia clave es que aquí las decisiones y el orden están representados en nodos inspeccionables, no delegados a un agente que seleccione herramientas libremente.
- **DeepSeek:** es el proveedor usado en las pruebas reales, según la elección del usuario. Endpoint compatible y modelo son configurables; las pruebas estructuradas solicitan JSON. La elección mantiene el proveedor intercambiable y la salida estructurada verificable; el consumo se registra en las evidencias.

## Ampliaciones al esquema

El archivo de semilla original no se alteró. `api/database.py` inicializa tablas y agrega campos propios del flujo cuando arranca la aplicación:

- **`recepciones`** guarda el correo y mensaje originales antes de llamar al LLM, una clave de idempotencia única y el hash del payload, clasificación, motivos, contador de intentos (0–2), estado, último error, resultado y relación a la solicitud creada. Cuando la salida no tiene un JSON válido, la clasificación puede quedar nula; para un correo de cliente desconocido se conserva `cliente_desconocido`. En ambos casos se puede revisar la recepción sin inventar datos para crear una solicitud.
- **`solicitudes`** agrega `recepcion_id`, `resumen`, `requiere_revision` y `motivos_revision_json`. Un índice único parcial sobre `recepcion_id` impide asociar dos solicitudes con la misma recepción.
- **`notificaciones`** es una outbox con una fila por solicitud, motivos, estado, intentos y `message_id`. La solicitud y su outbox se guardan dentro de la misma transacción. Antes del intento SMTP, la API confirma el estado `enviando`, el contador y el Message-ID; la conexión de red sucede después del commit, fuera de la transacción. Los resultados ambiguos quedan `incierta` para requerir revisión y evitar reenvío automático.

La regla de stock se evalúa al crear la solicitud. El B4 real guardó seis escritorios frente a tres disponibles y devolvió `sin_stock=true`; no descuenta ni reserva existencias.

## Contexto de catálogo para las pruebas del chatbot

`scripts/probar_chatbot.py` consulta `GET /productos?q=` antes de enviar los casos C, serializa la lista vigente con nombre, precio y stock, añade la hora de lectura y sustituye `{{catalogo_json}}` y `{{catalogo_leido_en}}` en el prompt de sistema. Así las respuestas de prueba usan una instantánea fechada del catálogo y pueden revisarse junto con su evidencia.

Este diseño aporta contexto al prompt; no es RAG ni una herramienta que el modelo llame por su cuenta. El modelo no consulta productos durante la respuesta: el script obtiene el catálogo antes de cada ronda de pruebas, así una ronda posterior incorpora los cambios del catálogo. Los doce productos caben en el contexto acotado del ensayo y no requieren recuperación vectorial.

## Decisiones y límites

- n8n se eligió para representar visualmente la orquestación exigida. OpenClaw puede ser familiar para el usuario, pero no sustituye a una de las plataformas solicitadas en la prueba.
- La API valida los campos, reglas de stock y estados, y almacena las solicitudes. SQLite y n8n se mantienen locales para facilitar la revisión y la sustentación.
- La base se inicializa desde la semilla y guarda los cambios en un volumen persistente. La cantidad solicitada puede superar el stock: la solicitud queda registrada y se alerta, sin descontar existencias ni confirmar una venta o reserva.
- Si un mensaje no permite clasificación suficiente o el correo no corresponde a un cliente, se conserva como recepción para revisión; no se inventa un cliente o una solicitud válida.
- El servicio está ligado a `127.0.0.1`, pero aún no incluye autenticación de clientes ni autorización multiusuario. No lo expongas a Internet ni lo uses con datos sensibles reales.
- Las ejecuciones reales B1–B5, C1–C4 y cuatro notificaciones SMTP están documentadas en [Estado actual](docs/ESTADO_ACTUAL.md). El usuario confirmó la llegada de los dos primeros correos y aceptó conversacionalmente el diseño HTML; la llegada de los mensajes HTML no tiene verificación automatizada. La [grabación final](flujo/evidencias/video/sustentacion-anexo-b.mp4) muestra la interfaz n8n y API durante 4:09; explica ejecuciones guardadas, no una nueva corrida durante la captura. La sustentación con el evaluador queda pendiente.

## Estructura del repositorio

```text
api/                    API FastAPI y dependencias
flujo/                  Workflow n8n exportado
material/               Enunciado y semilla original
prompts/                Prompts y resultados de pruebas
scripts/                Inicio, smoke e integración técnica
sql/                    Consultas del ejercicio
tests/                  Pruebas de API
Dockerfile.api          Imagen reproducible de API
compose.yaml            Servicios locales
.env.example            Nombres de configuración sin credenciales
```

La semilla `material/datos_prueba.sql` se conserva byte por byte. Los archivos `.env`, bases locales, cachés y logs están excluidos de Git. Consulta `docs/PLAN_ASTRA.md` para contratos, casos de aceptación y evidencia pendiente; el plan por sí solo no certifica que se hayan ejecutado pruebas.

