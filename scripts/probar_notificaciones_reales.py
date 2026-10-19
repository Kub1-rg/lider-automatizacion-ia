"""Envía como máximo dos avisos de prueba al propietario por el webhook n8n.

No hace reintentos HTTP. Ante cualquier respuesta SMTP distinta de `enviada`,
timeouts o errores, conserva evidencia parcial y se detiene para evitar duplicados.
El artefacto omite correos, mensajes originales, cabeceras y credenciales.
"""
from __future__ import annotations

import json
import argparse
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "flujo" / "evidencias" / "correo"
HTML_EVIDENCE_DIR = ROOT / "flujo" / "evidencias" / "correo-html"
N8N_BASE = "http://127.0.0.1:5688"
API_BASE = "http://127.0.0.1:18018"
CASES = [
    {
        "case": "B3",
        "description": "Queja por tóner dañado con solicitud de respuesta hoy",
        "payload": {
            "cliente_email": "compras@oficinasmodernassas.com",
            "mensaje": "Es la segunda vez que el tóner llega dañado. Estamos muy molestos, necesitamos que nos respondan hoy mismo.",
        },
        "expected": {"tipo": "queja", "urgencia": "alta", "producto_id": 2,
                     "alert_reasons": {"queja", "urgencia_alta"}},
    },
    {
        "case": "B4",
        "description": "Pedido de seis escritorios en L con stock actual de tres",
        "payload": {
            "cliente_email": "compras@constructorahorizonte.com",
            "mensaje": "Por favor despachar 6 escritorios en L para la nueva oficina de Rionegro.",
        },
        "expected": {"tipo": "pedido", "producto_id": 4, "cantidad": 6,
                     "sin_stock": True, "stock_verificado": True,
                     "alert_reasons": {"stock_insuficiente"}},
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def request_json(url: str, *, method: str = "GET", payload: dict | None = None,
                 idempotency_key: str | None = None, timeout: int = 90) -> tuple[int | None, dict | None, str | None]:
    headers = {"Accept": "application/json"}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            try:
                decoded = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return response.status, None, "invalid_json_response"
            return response.status, decoded if isinstance(decoded, dict) else None, None
    except urllib.error.HTTPError as exc:
        # Do not retain exception text, response body, or headers; they may contain sensitive data.
        return exc.code, None, "http_error"
    except (urllib.error.URLError, TimeoutError, OSError):
        return None, None, "transport_error_outcome_unknown"


def pick(source: dict | None, fields: tuple[str, ...]) -> dict:
    if not isinstance(source, dict):
        return {}
    return {key: source[key] for key in fields if key in source}


def write_evidence(path: Path, artifact: dict) -> None:
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fail(artifact: dict, path: Path, case: dict, stage: str,
         http_status: int | None = None, category: str = "unexpected_response") -> int:
    case["failure"] = {"stage": stage, "category": category, "http_status": http_status}
    artifact["status"] = "partial_stopped"
    artifact["updated_at"] = utc_now()
    write_evidence(path, artifact)
    print(f"Detenido en {case['case']} ({stage}, {category}, HTTP {http_status or 'sin respuesta'}); evidencia parcial guardada.")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Envía dos avisos reales controlados y conserva evidencia sin datos personales.")
    parser.add_argument(
        "--html", action="store_true",
        help="guarda esta ejecución en flujo/evidencias/correo-html y anota el formato MIME que genera el renderer",
    )
    args = parser.parse_args()

    evidence_dir = HTML_EVIDENCE_DIR if args.html else EVIDENCE_DIR
    evidence_dir.mkdir(parents=True, exist_ok=True)
    started = utc_now()
    slug = started.replace(":", "").replace("-", "").replace("+00:00", "Z")
    artifact_path = evidence_dir / f"notificaciones-{slug}.json"
    if artifact_path.exists():
        artifact_path = evidence_dir / f"notificaciones-{slug}-{uuid.uuid4().hex[:8]}.json"
    artifact = {
        "title": "Ensayo controlado de notificaciones por correo",
        "started_at": started,
        "updated_at": started,
        "status": "in_progress",
        "n8n_webhook": f"{N8N_BASE}/webhook/solicitud",
        "api_base": API_BASE,
        "recipient": "misma cuenta SMTP configurada; omitida por privacidad",
        "smtp_acceptance_is_not_mailbox_delivery": True,
        "cases": [],
    }
    if args.html:
        artifact["email_format_expectation"] = {
            "mime_type": "multipart/alternative",
            "parts": ["text/plain", "text/html"],
            "source": "API renderer, generated server-side from the saved request and catalog data",
            "smtp_message_captured": False,
        }
    write_evidence(artifact_path, artifact)

    for index, spec in enumerate(CASES):
        record = {
            "case": spec["case"],
            "description": spec["description"],
            "idempotency_key": f"correo-{uuid.uuid4()}",
            "started_at": utc_now(),
        }
        artifact["cases"].append(record)
        write_evidence(artifact_path, artifact)

        status, webhook, error = request_json(
            f"{N8N_BASE}/webhook/solicitud", method="POST", payload=spec["payload"],
            idempotency_key=record["idempotency_key"], timeout=120,
        )
        record["webhook_http_status"] = status
        if error or not isinstance(webhook, dict):
            return fail(artifact, artifact_path, record, "webhook", status, error or "invalid_webhook_response")
        record["webhook_result"] = pick(webhook, (
            "recepcion_id", "solicitud_id", "clasificacion", "requiere_revision", "motivos_revision",
            "sin_stock", "stock_verificado", "motivos_alerta", "notificacion_id", "notificacion_estado",
        ))
        record["webhook_completed_at"] = utc_now()
        write_evidence(artifact_path, artifact)

        result = record["webhook_result"]
        request_id = result.get("solicitud_id")
        notification_id = result.get("notificacion_id")
        if not isinstance(request_id, int) or not isinstance(notification_id, int):
            return fail(artifact, artifact_path, record, "webhook_result", status, "missing_request_or_notification_id")
        if result.get("notificacion_estado") != "enviada":
            return fail(artifact, artifact_path, record, "smtp_acceptance", status, "smtp_not_accepted")
        record["smtp_acceptance"] = "accepted_by_smtp"
        record["message_id"] = None

        status, request_detail, error = request_json(f"{API_BASE}/solicitudes/{request_id}", timeout=15)
        record["request_http_status"] = status
        if error or not isinstance(request_detail, dict):
            return fail(artifact, artifact_path, record, "get_request", status, error or "invalid_request_response")
        record["request"] = pick(request_detail, (
            "id", "cliente_id", "producto_id", "producto_nombre", "tipo", "cantidad", "urgencia", "estado",
            "sin_stock", "stock_verificado", "motivos_alerta", "notificacion_id",
        ))
        if record["request"].get("notificacion_id") != notification_id:
            return fail(artifact, artifact_path, record, "request_notification_match", status, "notification_id_mismatch")

        reception_id = result.get("recepcion_id")
        if isinstance(reception_id, int):
            status, reception, error = request_json(f"{API_BASE}/recepciones/{reception_id}", timeout=15)
            record["reception_http_status"] = status
            if error or not isinstance(reception, dict):
                return fail(artifact, artifact_path, record, "get_reception", status, error or "invalid_reception_response")
            record["reception"] = pick(reception, ("recepcion_id", "estado", "intentos_llm", "clasificacion", "motivos_revision", "solicitud_id"))
            if record["reception"].get("solicitud_id") != request_id:
                return fail(artifact, artifact_path, record, "reception_request_match", status, "request_id_mismatch")

        # Verify the first new outbox record is already sent. This endpoint is idempotent
        # for state `enviada`; it must never be called for an older or unsent notification.
        if index == 0:
            if result.get("notificacion_estado") != "enviada":
                return fail(artifact, artifact_path, record, "idempotency_guard", status, "notification_not_confirmed_sent")
            status, notification, error = request_json(
                f"{API_BASE}/notificaciones/{notification_id}/enviar", method="POST", payload={}, timeout=15,
            )
            record["idempotency_check_http_status"] = status
            if error or not isinstance(notification, dict):
                return fail(artifact, artifact_path, record, "idempotency_check", status, error or "invalid_notification_response")
            record["idempotency_check"] = pick(notification, ("notificacion_id", "estado", "enviado", "message_id", "fecha_actualizacion", "detalle"))
            if notification.get("estado") != "enviada" or notification.get("notificacion_id") != notification_id:
                return fail(artifact, artifact_path, record, "idempotency_check", status, "already_sent_state_not_preserved")
            record["message_id"] = notification.get("message_id")

        expected = spec["expected"]
        classification = webhook.get("clasificacion")
        if not isinstance(classification, dict) or classification.get("tipo") != expected["tipo"]:
            return fail(artifact, artifact_path, record, "acceptance_check", status, "classification_mismatch")
        if "urgencia" in expected and classification.get("urgencia") != expected["urgencia"]:
            return fail(artifact, artifact_path, record, "acceptance_check", status, "urgency_mismatch")
        if record["request"].get("producto_id") != expected["producto_id"]:
            return fail(artifact, artifact_path, record, "acceptance_check", status, "product_mismatch")
        if "cantidad" in expected and record["request"].get("cantidad") != expected["cantidad"]:
            return fail(artifact, artifact_path, record, "acceptance_check", status, "quantity_mismatch")
        if expected.get("sin_stock") is True and (webhook.get("sin_stock") is not True or webhook.get("stock_verificado") is not True):
            return fail(artifact, artifact_path, record, "acceptance_check", status, "stock_check_mismatch")
        actual_reasons = set(webhook.get("motivos_alerta") or [])
        if not expected["alert_reasons"].issubset(actual_reasons):
            return fail(artifact, artifact_path, record, "acceptance_check", status, "alert_reason_mismatch")

        record["status"] = "smtp_accepted"
        record["completed_at"] = utc_now()
        artifact["updated_at"] = record["completed_at"]
        write_evidence(artifact_path, artifact)
        print(f"{record['case']}: SMTP aceptó el aviso (solicitud {request_id}, notificación {notification_id}).")

    artifact["status"] = "smtp_accepted_by_provider"
    artifact["completed_at"] = utc_now()
    artifact["updated_at"] = artifact["completed_at"]
    write_evidence(artifact_path, artifact)
    print(f"Dos avisos aceptados por SMTP; evidencia guardada en {artifact_path}.")
    print("La aceptación SMTP no verifica entrega ni llegada a la bandeja de entrada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
