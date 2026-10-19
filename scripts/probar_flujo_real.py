"""Prueba una sola pasada de cinco casos del Anexo B en el webhook n8n real.

El workflow puede generar hasta tres correos y llamadas de proveedor con costo.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WEBHOOK = "http://127.0.0.1:5688"
DEFAULT_API = "http://127.0.0.1:18018"
CASES = [
    {"case": "B1_resmas_urgentes", "email": "compras@ferreteriaeltornillo.com",
     "message": "Buenos días, necesitamos 10 resmas de papel carta para el viernes, es urgente.",
     "status": 201, "client_id": 1, "product_id": 1, "kind": "pedido", "quantity": 10,
     "urgent": True, "sin_stock": False, "alert": "urgencia_alta"},
    {"case": "B2_consulta_diademas", "email": "compras@clinicalosandes.com",
     "message": "Hola, ¿tienen diademas con micrófono? ¿Cuánto valen y en cuánto tiempo llegan?",
     "status": 201, "client_id": 5, "product_id": 11, "kind": "consulta", "quantity": None},
    {"case": "B3_queja_toner", "email": "compras@oficinasmodernassas.com",
     "message": "Es la segunda vez que el tóner llega dañado. Estamos muy molestos, necesitamos que nos respondan hoy mismo.",
     "status": 201, "client_id": 3, "product_id": 2, "kind": "queja", "quantity": None,
     "urgent": True, "alert": "queja"},
    {"case": "B4_stock_escritorios", "email": "compras@constructorahorizonte.com",
     "message": "Por favor despachar 6 escritorios en L para la nueva oficina de Rionegro.",
     "status": 201, "client_id": 10, "product_id": 4, "kind": "pedido", "quantity": 6,
     "sin_stock": True, "alert": "stock_insuficiente"},
    {"case": "B5_cliente_desconocido", "email": "juanperez.compras@gmail.com",
     "message": "hola buenas q precio tienen los mouse inalambricos y si hacen envios",
     "status": 202, "unknown_client": True},
]


def decode_json(raw: bytes):
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def request_json(url: str, payload=None, headers=None, timeout=20):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request_headers = {"Accept": "application/json", **(headers or {})}
    if data is not None:
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=request_headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            return {"http_status": response.status, "body": decode_json(raw),
                    "raw_body": raw.decode("utf-8", errors="replace") if decode_json(raw) is None else None}
    except urllib.error.HTTPError as error:
        raw = error.read()
        body = decode_json(raw)
        return {"http_status": error.code, "body": body,
                "raw_body": raw.decode("utf-8", errors="replace") if body is None else None}
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        # Do not serialize exception text, request headers, or environment values.
        return {"http_status": None, "body": None, "transport_error": type(error).__name__}


def get_request_id(response_body):
    if not isinstance(response_body, dict):
        return None
    return response_body.get("solicitud_id") or response_body.get("id")


def run_case(case, webhook, api):
    key = f"flujo-real-{uuid.uuid4()}"
    started = time.monotonic()
    webhook_result = request_json(
        webhook.rstrip("/") + "/webhook/solicitud",
        {"cliente_email": case["email"], "mensaje": case["message"]},
        {"Idempotency-Key": key}, timeout=60,
    )
    elapsed = round(time.monotonic() - started, 3)
    body = webhook_result.get("body") if isinstance(webhook_result.get("body"), dict) else {}
    reception_id = body.get("recepcion_id")
    solicitation_id = get_request_id(body)
    reception_result = None
    solicitation_result = None
    if reception_id is not None:
        reception_result = request_json(f"{api.rstrip('/')}/recepciones/{reception_id}", timeout=15)
        reception_body = reception_result.get("body") if isinstance(reception_result.get("body"), dict) else {}
        solicitation_id = solicitation_id or reception_body.get("solicitud_id")
    else:
        reception_body = {}
    if solicitation_id is not None:
        solicitation_result = request_json(f"{api.rstrip('/')}/solicitudes/{solicitation_id}", timeout=15)
    solicitation_body = (solicitation_result or {}).get("body")
    if not isinstance(solicitation_body, dict):
        solicitation_body = {}
    classification = body.get("clasificacion") or reception_body.get("clasificacion")
    if not isinstance(classification, dict):
        classification = {}

    checks = {"webhook_http_status": webhook_result.get("http_status") == case["status"]}
    if case.get("unknown_client"):
        reasons = reception_body.get("motivos_revision") or body.get("motivos_revision") or []
        checks.update({
            "reception_persisted": reception_id is not None and reception_result is not None and reception_result.get("http_status") == 200,
            "manual_review": reception_body.get("estado") == "revision_manual" or body.get("requiere_revision") is True,
            "unknown_client_reason": "cliente_desconocido" in reasons,
            "no_solicitation_created": solicitation_id is None,
            "classification_present": bool(classification),
        })
    else:
        reasons = solicitation_body.get("motivos_alerta") or body.get("motivos_alerta") or []
        checks.update({
            "reception_persisted": reception_id is not None and reception_result is not None and reception_result.get("http_status") == 200,
            "solicitation_persisted": solicitation_id is not None and solicitation_result is not None and solicitation_result.get("http_status") == 200,
            "client_id": solicitation_body.get("cliente_id") == case["client_id"],
            "product_id": solicitation_body.get("producto_id") == case["product_id"],
            "type": solicitation_body.get("tipo") == case["kind"],
            "quantity": solicitation_body.get("cantidad") == case.get("quantity"),
        })
        if "urgent" in case:
            checks["urgency_high"] = solicitation_body.get("urgencia") == "alta"
        if "sin_stock" in case:
            checks["stock_result"] = solicitation_body.get("sin_stock") is case["sin_stock"]
            checks["stock_verified"] = solicitation_body.get("stock_verificado") is True
        if "alert" in case:
            checks[f"alert_{case['alert']}"] = case["alert"] in reasons
        if case["case"] == "B2_consulta_diademas":
            checks["no_stock_alert_for_consultation"] = "stock_insuficiente" not in reasons

    result = {
        "case": case["case"],
        "request": {"cliente_email": case["email"], "mensaje": case["message"], "idempotency_key": key},
        "elapsed_seconds": elapsed,
        "webhook": webhook_result,
        "recepcion_api": reception_result,
        "solicitud_api": solicitation_result,
        "checks": checks,
        "passed": all(checks.values()),
    }
    return result


def write_evidence(path, artifact):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def main():
    parser = argparse.ArgumentParser(
        description="Prueba real de cinco casos del Anexo B en el webhook n8n. "
                    "El workflow puede generar hasta tres correos y llamadas de proveedor con costo."
    )
    parser.add_argument("--webhook", default=DEFAULT_WEBHOOK)
    parser.add_argument("--api", default=DEFAULT_API)
    parser.add_argument("--output-dir", default=str(ROOT / "flujo" / "evidencias" / "real"))
    parser.add_argument(
        "--allow-notifications", action="store_true",
        help="autoriza continuar aunque el workflow podría generar hasta tres correos y costos de proveedor",
    )
    args = parser.parse_args()
    if not args.allow_notifications:
        parser.error("se requiere --allow-notifications; el runner no puede verificar la configuración SMTP del contenedor")

    health = request_json(args.api.rstrip("/") + "/health", timeout=10)
    if health.get("http_status") != 200 or not isinstance(health.get("body"), dict) or health["body"].get("status") != "ok":
        print(f"API no saludable en {args.api}; no se enviaron casos B.", file=sys.stderr)
        return 2

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    output = Path(args.output_dir) / f"flujo-real-{run_id}.json"
    artifact = {
        "kind": "prueba_real_webhook_deepseek",
        "provider": "DeepSeek configurado por el proceso n8n; no se capturaron credenciales ni headers",
        "model_configured": "deepseek-flash",
        "metadata": {"request_id": None, "usage": None,
                     "note": "El webhook no expone metadata del nodo LLM; el agente principal puede completar estos campos desde la ejecución n8n sin incluir headers."},
        "started_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "webhook": args.webhook.rstrip("/") + "/webhook/solicitud",
        "api": args.api,
        "email_sending": "gestionado_por_workflow; no_verificado_por_runner",
        "health": health,
        "results": [],
        "passed": 0,
        "total_planned": len(CASES),
        "stopped_after_failure": None,
    }
    write_evidence(output, artifact)
    print("Notificaciones gestionadas por configuración local del workflow; el runner no verifica su envío.")
    for case in CASES:
        result = run_case(case, args.webhook, args.api)
        artifact["results"].append(result)
        artifact["passed"] = sum(1 for item in artifact["results"] if item["passed"])
        if not result["passed"]:
            artifact["stopped_after_failure"] = case["case"]
        write_evidence(output, artifact)
        failed = [name for name, passed in result["checks"].items() if not passed]
        print(f"{'OK' if result['passed'] else 'FALLO'} {case['case']}: HTTP {result['webhook']['http_status']}; "
              f"checks={sum(result['checks'].values())}/{len(result['checks'])}; duración={result['elapsed_seconds']} s")
        if failed:
            print("Falló: " + ", ".join(failed) + f". Evidencia: {output}", file=sys.stderr)
            return 1
    artifact["finished_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    write_evidence(output, artifact)
    print(f"Evidencia guardada: {output}; {artifact['passed']}/{len(CASES)} casos B aprobados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
