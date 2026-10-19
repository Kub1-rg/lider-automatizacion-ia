import hashlib
import json
import os
import ssl
import smtplib
import unicodedata
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictStr

from .database import PROJECT_ROOT, connect, initialize_database
from .email_templates import render_notification
from .models import Classification, ClassificationPatch, ReceptionCreate, SolicitudCreate, SolicitudEstadoUpdate


load_dotenv()


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _loads(value, fallback):
    if value is None:
        return fallback
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return fallback


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char)).strip()


def _reception_view(row):
    return {
        "id": row["id"], "recepcion_id": row["id"], "idempotency_key": row["idempotency_key"],
        "estado": row["estado"], "cliente_email": row["cliente_email"], "mensaje": row["mensaje"],
        "clasificacion": _loads(row["clasificacion_json"], None),
        "intentos_llm": row["intentos_llm"], "motivos_revision": _loads(row["motivos_revision_json"], []),
        "ultimo_error": row["ultimo_error"], "solicitud_id": row["solicitud_id"],
        "resultado": _loads(row["resultado_json"], None),
    }


class SolicitudOutput(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: int
    cliente_id: int
    producto_id: int | None
    tipo: str
    cantidad: int | None
    urgencia: str
    estado: str
    mensaje: str
    fecha_creacion: str
    fecha_resolucion: str | None
    resumen: str | None = None
    requiere_revision: bool = False
    motivos_revision: list[str] = Field(default_factory=list)
    sin_stock: bool = False
    stock_verificado: bool = False
    motivos_alerta: list[str] = Field(default_factory=list)
    notificacion_id: int | None = None


def create_app(database_path: str | Path | None = None, seed_path: str | Path | None = None) -> FastAPI:
    db_path = Path(database_path or os.getenv("DATABASE_PATH", PROJECT_ROOT / "api" / "data" / "solicitudes.db"))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        initialize_database(db_path, seed_path)
        yield

    app = FastAPI(title="Suministros Andinos API", version="1.0.0", lifespan=lifespan)
    app.state.database_path = db_path

    def db_connect():
        return connect(app.state.database_path)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        errors = [{"loc": e.get("loc"), "msg": e.get("msg"), "type": e.get("type")} for e in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": "Datos de entrada inválidos", "errors": errors})

    @app.exception_handler(Exception)
    async def internal_error_handler(request: Request, exc: Exception):
        return JSONResponse(status_code=500, content={"detail": "Error interno al procesar la solicitud"})

    @app.get("/health")
    def health():
        with db_connect() as db:
            db.execute("SELECT 1").fetchone()
        return {"status": "ok", "database": "ok", "llm_provider": "n8n"}

    @app.get("/clientes/{client_id}")
    def get_client_by_id(client_id: int):
        with db_connect() as db:
            row = db.execute("SELECT * FROM clientes WHERE id=?", (client_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Cliente no encontrado")
        return dict(row)

    @app.get("/clientes")
    def get_client(email: str = Query(min_length=3, max_length=120)):
        normalized = email.strip().casefold()
        with db_connect() as db:
            rows = db.execute("SELECT * FROM clientes").fetchall()
        row = next((r for r in rows if r["email"].strip().casefold() == normalized), None)
        if row is None:
            raise HTTPException(404, "Cliente no encontrado")
        return dict(row)

    @app.get("/productos")
    def get_products(q: str = Query(default="", max_length=120)):
        with db_connect() as db:
            rows = db.execute("SELECT id,nombre,categoria,precio,stock FROM productos ORDER BY id").fetchall()
        needle = _normalize(q)
        return [dict(row) for row in rows if not needle or needle in _normalize(row["nombre"])]

    def _solicitud_view(row, sin_stock=False, stock_verificado=False, motivos_alerta=None, notificacion_id=None):
        result = dict(row)
        result["requiere_revision"] = bool(result.get("requiere_revision", 0))
        result["motivos_revision"] = _loads(result.pop("motivos_revision_json", None), [])
        result.update({"sin_stock": sin_stock, "stock_verificado": stock_verificado,
                       "motivos_alerta": motivos_alerta or [], "notificacion_id": notificacion_id})
        return result

    def _current_request_view(db, row):
        result = dict(row)
        reasons = []
        if result["tipo"] == "queja":
            reasons.append("queja")
        if result["urgencia"] == "alta":
            reasons.append("urgencia_alta")
        stock_verified = False
        insufficient = False
        if result["tipo"] == "pedido" and result["producto_id"] is not None and result["cantidad"] is not None:
            product = db.execute("SELECT stock FROM productos WHERE id=?", (result["producto_id"],)).fetchone()
            if product:
                stock_verified = True
                insufficient = result["cantidad"] > product["stock"]
                if insufficient:
                    reasons.append("stock_insuficiente")
        notification = db.execute("SELECT id FROM notificaciones WHERE solicitud_id=?", (result["id"],)).fetchone()
        return _solicitud_view(row, insufficient, stock_verified, reasons,
                               notification["id"] if notification else None)

    @app.post("/solicitudes", response_model=SolicitudOutput, status_code=201)
    def create_solicitud(payload: SolicitudCreate, response: Response):
        data = payload.model_dump()
        with db_connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if data["recepcion_id"] is not None:
                source_reception = db.execute("SELECT * FROM recepciones WHERE id=?", (data["recepcion_id"],)).fetchone()
                if source_reception is None:
                    raise HTTPException(404, "Recepción no encontrada")
                owner = db.execute("SELECT email FROM clientes WHERE id=?", (data["cliente_id"],)).fetchone()
                if source_reception["mensaje"] != data["mensaje"]:
                    raise HTTPException(409, "El mensaje no coincide con la recepción original")
                if owner is None or owner["email"].strip().casefold() != source_reception["cliente_email"].strip().casefold():
                    raise HTTPException(409, "El cliente no corresponde al correo de la recepción")
            if data["recepcion_id"] is not None:
                prior = db.execute("""SELECT s.*, n.id AS notification_id, r.resultado_json,
                    c.email AS source_email FROM solicitudes s
                    JOIN clientes c ON c.id=s.cliente_id
                    LEFT JOIN notificaciones n ON n.solicitud_id=s.id
                    LEFT JOIN recepciones r ON r.id=s.recepcion_id WHERE s.recepcion_id=?""",
                                   (data["recepcion_id"],)).fetchone()
                if prior:
                    same = (prior["cliente_id"] == data["cliente_id"] and prior["producto_id"] == data["producto_id"]
                            and prior["tipo"] == data["tipo"] and prior["cantidad"] == data["cantidad"]
                            and prior["urgencia"] == data["urgencia"] and prior["mensaje"] == data["mensaje"]
                            and prior["resumen"] == data["resumen"]
                            and bool(prior["requiere_revision"]) == data["requiere_revision"]
                            and _loads(prior["motivos_revision_json"], []) == data["motivos_revision"])
                    if not same:
                        raise HTTPException(409, "La recepción ya tiene una solicitud con datos distintos")
                    saved = _loads(prior["resultado_json"], None)
                    if saved:
                        response.status_code = 200
                        return saved

            if not db.execute("SELECT 1 FROM clientes WHERE id=?", (data["cliente_id"],)).fetchone():
                raise HTTPException(404, "Cliente no encontrado")
            if data["producto_id"] is not None and not db.execute("SELECT 1 FROM productos WHERE id=?", (data["producto_id"],)).fetchone():
                raise HTTPException(404, "Producto no encontrado")

            stock_verified = False
            insufficient = False
            alert_reasons = []
            if data["tipo"] == "queja":
                alert_reasons.append("queja")
            if data["urgencia"] == "alta":
                alert_reasons.append("urgencia_alta")
            if data["tipo"] == "pedido" and data["producto_id"] is not None and data["cantidad"] is not None:
                product = db.execute("SELECT stock FROM productos WHERE id=?", (data["producto_id"],)).fetchone()
                stock_verified = True
                insufficient = data["cantidad"] > product["stock"]
                if insufficient:
                    alert_reasons.append("stock_insuficiente")

            cursor = db.execute("""INSERT INTO solicitudes
                (cliente_id,producto_id,tipo,cantidad,urgencia,estado,mensaje,fecha_creacion,
                 fecha_resolucion,recepcion_id,resumen,requiere_revision,motivos_revision_json)
                VALUES (?,?,?,?,?,'pendiente',?,?,NULL,?,?,?,?)""",
                (data["cliente_id"], data["producto_id"], data["tipo"], data["cantidad"], data["urgencia"],
                 data["mensaje"], _now(), data["recepcion_id"], data["resumen"], int(data["requiere_revision"]),
                 _json(data["motivos_revision"])))
            request_id = cursor.lastrowid
            notification_id = None
            if alert_reasons:
                notification_id = db.execute("INSERT INTO notificaciones(solicitud_id,motivos_json,estado) VALUES(?,?, 'pendiente')",
                                              (request_id, _json(alert_reasons))).lastrowid
            row = db.execute("SELECT * FROM solicitudes WHERE id=?", (request_id,)).fetchone()
            result = _solicitud_view(row, insufficient, stock_verified, alert_reasons, notification_id)
            if data["recepcion_id"] is not None:
                db.execute("UPDATE recepciones SET estado='registrada', solicitud_id=?, resultado_json=?, fecha_actualizacion=? WHERE id=?",
                           (request_id, _json(result), _now(), data["recepcion_id"]))
            db.commit()
            return result
    @app.get("/solicitudes")
    def list_solicitudes(tipo: str | None = None, estado: str | None = None, urgencia: str | None = None,
                         limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0)):
        allowed = {"tipo": {"pedido", "consulta", "queja"}, "estado": {"pendiente", "en_proceso", "resuelta"},
                   "urgencia": {"baja", "media", "alta"}}
        filters = {"tipo": tipo, "estado": estado, "urgencia": urgencia}
        clauses, values = [], []
        for key, value in filters.items():
            if value is not None:
                if value not in allowed[key]:
                    raise HTTPException(422, f"Filtro {key} inválido")
                clauses.append(f"{key}=?")
                values.append(value)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with db_connect() as db:
            total = db.execute("SELECT COUNT(*) FROM solicitudes" + where, values).fetchone()[0]
            rows = db.execute("SELECT * FROM solicitudes" + where + " ORDER BY fecha_creacion ASC,id ASC LIMIT ? OFFSET ?",
                              [*values, limit, offset]).fetchall()
            items = [_current_request_view(db, row) for row in rows]
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    @app.get("/solicitudes/{request_id}")
    def get_solicitud(request_id: int):
        with db_connect() as db:
            row = db.execute("""SELECT s.*, c.nombre AS cliente_nombre, c.email AS cliente_email,
                p.nombre AS producto_nombre FROM solicitudes s JOIN clientes c ON c.id=s.cliente_id
                LEFT JOIN productos p ON p.id=s.producto_id WHERE s.id=?""", (request_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Solicitud no encontrada")
        with db_connect() as db:
            return _current_request_view(db, row)

    @app.patch("/solicitudes/{request_id}")
    def update_solicitud(request_id: int, payload: SolicitudEstadoUpdate):
        with db_connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT estado,fecha_resolucion FROM solicitudes WHERE id=?", (request_id,)).fetchone()
            if row is None:
                raise HTTPException(404, "Solicitud no encontrada")
            current, target = row["estado"], payload.estado
            if current == "resuelta" and target == "resuelta":
                return {"id": request_id, "estado": current, "fecha_resolucion": row["fecha_resolucion"]}
            transitions = {"pendiente": {"pendiente", "en_proceso", "resuelta"},
                           "en_proceso": {"pendiente", "en_proceso", "resuelta"}, "resuelta": set()}
            if target not in transitions[current]:
                raise HTTPException(409, "No se permite cambiar una solicitud resuelta")
            resolved_at = _now() if target == "resuelta" else None
            db.execute("UPDATE solicitudes SET estado=?,fecha_resolucion=? WHERE id=?", (target, resolved_at, request_id))
            return {"id": request_id, "estado": target, "fecha_resolucion": resolved_at}

    @app.post("/recepciones", status_code=201)
    def create_reception(payload: ReceptionCreate, response: Response,
                         idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=200)):
        email = payload.cliente_email.strip()
        body_hash = hashlib.sha256(_json({"cliente_email": email.casefold(), "mensaje": payload.mensaje}).encode()).hexdigest()
        key = idempotency_key.strip() if idempotency_key and idempotency_key.strip() else hashlib.sha256(os.urandom(32)).hexdigest()
        with db_connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT * FROM recepciones WHERE idempotency_key=?", (key,)).fetchone()
            if existing:
                if existing["payload_hash"] != body_hash:
                    raise HTTPException(409, "Idempotency-Key ya existe con un cuerpo distinto")
                response.status_code = 200
                view = _reception_view(existing)
                if existing["estado"] in {"registrada", "revision_manual"}:
                    view["resultado_previo"] = view["resultado"]
                return view
            cursor = db.execute("""INSERT INTO recepciones(idempotency_key,payload_hash,cliente_email,mensaje,estado)
                VALUES(?,?,?,?,'recibida')""", (key, body_hash, email, payload.mensaje))
            row = db.execute("SELECT * FROM recepciones WHERE id=?", (cursor.lastrowid,)).fetchone()
            return _reception_view(row)

    @app.get("/recepciones/{reception_id}")
    def get_reception(reception_id: int):
        with db_connect() as db:
            row = db.execute("SELECT * FROM recepciones WHERE id=?", (reception_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Recepción no encontrada")
        return _reception_view(row)

    @app.patch("/recepciones/{reception_id}")
    def update_reception(reception_id: int, payload: ClassificationPatch):
        with db_connect() as db:
            row = db.execute("SELECT * FROM recepciones WHERE id=?", (reception_id,)).fetchone()
            if row is None:
                raise HTTPException(404, "Recepción no encontrada")
            if row["estado"] == "registrada" and payload.estado != "registrada":
                raise HTTPException(409, "Una recepción registrada es terminal")
            if payload.estado == "registrada" and row["solicitud_id"] is None:
                raise HTTPException(409, "Una recepción solo queda registrada al crear su solicitud")
            if payload.estado == "revision_manual" and not payload.motivos_revision:
                raise HTTPException(422, "La revisión manual requiere al menos un motivo")
            if row["estado"] == "registrada":
                raise HTTPException(409, "Una recepción registrada es terminal")
            if row["estado"] == "revision_manual" and payload.estado not in {"revision_manual", "procesando", "registrada"}:
                raise HTTPException(409, "Transición de recepción inválida")
            classification = payload.clasificacion.model_dump() if payload.clasificacion else None
            db.execute("""UPDATE recepciones SET estado=?,clasificacion_json=?,intentos_llm=?,motivos_revision_json=?,
                ultimo_error=?,fecha_actualizacion=? WHERE id=?""",
                       (payload.estado, _json(classification) if classification else None, payload.intentos_llm,
                        _json(payload.motivos_revision), payload.ultimo_error, _now(), reception_id))
            result = db.execute("SELECT * FROM recepciones WHERE id=?", (reception_id,)).fetchone()
        return _reception_view(result)

    def send_smtp(notification_id: int, notification_data: dict):
        with db_connect() as db:
            saved = db.execute("SELECT estado,message_id,fecha_actualizacion FROM notificaciones WHERE id=?",
                               (notification_id,)).fetchone()
        if saved is None:
            raise HTTPException(404, "Notificación no encontrada")
        if saved["estado"] == "enviada":
            return {"notificacion_id": notification_id, "estado": "enviada", "configurado": True,
                    "enviado": True, "message_id": saved["message_id"],
                    "fecha_actualizacion": saved["fecha_actualizacion"],
                    "detalle": "Aceptada por el servidor SMTP; esto no confirma llegada a la bandeja"}
        if os.getenv("NOTIFICATIONS_ENABLED", "false").casefold() != "true":
            return {"notificacion_id": notification_id, "estado": saved["estado"], "configurado": False,
                    "enviado": False, "message_id": saved["message_id"],
                    "fecha_actualizacion": saved["fecha_actualizacion"], "detalle": "Notificaciones desactivadas"}
        required = ["SMTP_HOST", "SMTP_PORT", "SMTP_FROM", "NOTIFICATION_TO"]
        if not all(os.getenv(name) for name in required):
            return {"notificacion_id": notification_id, "estado": saved["estado"], "configurado": False,
                    "enviado": False, "message_id": saved["message_id"],
                    "fecha_actualizacion": saved["fecha_actualizacion"], "detalle": "Configuración SMTP incompleta"}
        with db_connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM notificaciones WHERE id=?", (notification_id,)).fetchone()
            if row is None:
                raise HTTPException(404, "Notificación no encontrada")
            if row["estado"] == "enviada":
                return {"notificacion_id": notification_id, "estado": "enviada", "configurado": True,
                        "enviado": True, "message_id": row["message_id"],
                        "fecha_actualizacion": row["fecha_actualizacion"],
                        "detalle": "Aceptada por el servidor SMTP; esto no confirma llegada a la bandeja"}
            if row["estado"] in {"enviando", "incierta"}:
                return {"notificacion_id": notification_id, "estado": row["estado"], "configurado": True,
                        "enviado": False, "message_id": row["message_id"],
                        "fecha_actualizacion": row["fecha_actualizacion"],
                        "detalle": "Requiere revisión manual antes de reintentar"}
            message_id = row["message_id"] or make_msgid()
            reserved_at = _now()
            db.execute("""UPDATE notificaciones SET estado='enviando',intentos=intentos+1,message_id=?,
                fecha_actualizacion=? WHERE id=?""", (message_id, reserved_at, notification_id))

        client = None
        sent_call_started = False
        try:
            email = EmailMessage()
            request_id = notification_data["request_id"]
            email["Subject"] = f"Solicitud #{request_id} requiere atención"
            email["From"] = os.environ["SMTP_FROM"]
            email["To"] = os.environ["NOTIFICATION_TO"]
            email["Message-ID"] = message_id
            plain, html_body = render_notification(notification_data)
            email.set_content(plain)
            email.add_alternative(html_body, subtype="html")
            port = int(os.environ["SMTP_PORT"])
            timeout = float(os.getenv("SMTP_TIMEOUT", "10"))
            client = smtplib.SMTP(os.environ["SMTP_HOST"], port, timeout=timeout)
            if os.getenv("SMTP_STARTTLS", "true").casefold() == "true":
                client.starttls(context=ssl.create_default_context())
            username = os.getenv("SMTP_USERNAME")
            password = os.getenv("SMTP_PASSWORD")
            if username:
                client.login(username, password or "")
            sent_call_started = True
            client.send_message(email)
            state, detail = "enviada", "Aceptada por el servidor SMTP; esto no confirma llegada a la bandeja"
        except (smtplib.SMTPAuthenticationError, smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused) as exc:
            state, detail = "fallida", "El servidor rechazó autenticación o destinatario"
        except Exception:
            state = "incierta" if sent_call_started else "fallida"
            detail = "Resultado SMTP incierto; requiere revisión manual" if sent_call_started else "No se pudo conectar o preparar SMTP"
        finally:
            if client is not None:
                try:
                    client.quit()
                except Exception:
                    pass
        with db_connect() as db:
            updated_at = _now()
            db.execute("UPDATE notificaciones SET estado=?,ultimo_error=?,fecha_actualizacion=? WHERE id=?",
                       (state, None if state == "enviada" else detail, updated_at, notification_id))
        return {"notificacion_id": notification_id, "estado": state, "configurado": True,
                "enviado": state == "enviada", "message_id": message_id,
                "fecha_actualizacion": updated_at, "detalle": detail}

    @app.post("/notificaciones/{notification_id}/enviar")
    def send_notification(notification_id: int):
        with db_connect() as db:
            row = db.execute("""SELECT n.*,s.id AS request_id,s.tipo,s.producto_id,s.cantidad,s.urgencia,
                s.estado AS request_status,s.fecha_creacion,s.resumen,s.mensaje,
                c.nombre AS customer_name,p.nombre AS product_name,p.stock AS stock_available
                FROM notificaciones n
                JOIN solicitudes s ON s.id=n.solicitud_id
                JOIN clientes c ON c.id=s.cliente_id
                LEFT JOIN productos p ON p.id=s.producto_id
                WHERE n.id=?""", (notification_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Notificación no encontrada")
        current_stock_check = (row["tipo"] == "pedido" and row["cantidad"] is not None
                               and row["stock_available"] is not None)
        notification_data = {
            "notification_id": notification_id,
            "request_id": row["request_id"],
            "cliente_nombre": row["customer_name"],
            "customer_name": row["customer_name"],
            "product_name": row["product_name"],
            "tipo": row["tipo"],
            "cantidad": row["cantidad"],
            "urgencia": row["urgencia"],
            "estado": row["request_status"],
            "fecha_creacion": row["fecha_creacion"],
            "resumen": row["resumen"],
            "mensaje": row["mensaje"],
            "motivos_alerta": _loads(row["motivos_json"], []),
            "stock_available": row["stock_available"],
            "sin_stock": bool(current_stock_check and row["cantidad"] > row["stock_available"]),
        }
        return send_smtp(notification_id, notification_data)

    return app


app = create_app()
