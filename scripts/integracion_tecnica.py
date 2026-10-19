"""Pruebas del webhook n8n real usando solo el proveedor fixture del perfil técnico."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request
import uuid


ROOT = Path(__file__).resolve().parents[1]


def parse_json(raw):
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def request_json(url, payload=None, headers=None, timeout=15):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request_headers = {"Accept": "application/json", **(headers or {})}
    if data is not None:
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=request_headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return response.status, parse_json(raw), raw
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        return error.code, parse_json(raw), raw
    except Exception as error:
        return None, None, f"{type(error).__name__}: {error}"


def fixture_count(stub_url, marker):
    status, stats, raw = request_json(stub_url.rstrip("/") + "/stats", timeout=5)
    if status != 200 or not isinstance(stats, dict) or stats.get("fixture") is not True:
        raise RuntimeError(f"El endpoint de conteo del fixture falló: HTTP {status} {raw}")
    marker = marker.casefold()
    return sum(count for message, count in stats.get("call_counts", {}).items() if marker in message.casefold())


def call_webhook(base_url, email, message, key, timeout=20):
    started = time.monotonic()
    status, body, raw = request_json(
        base_url.rstrip("/") + "/webhook/solicitud",
        {"cliente_email": email, "mensaje": message},
        {"Idempotency-Key": key},
        timeout=timeout,
    )
    return status, body, raw, round(time.monotonic() - started, 3)


def api_get(api_url, path):
    status, body, raw = request_json(api_url.rstrip("/") + path, timeout=6)
    return {"http_status": status, "body": body if body is not None else raw}


def request_id_from_webhook(body):
    if not isinstance(body, dict):
        return None
    return body.get("solicitud_id") or body.get("id")


def run_case(spec, base_url, api_url, stub_url, run_id):
    name, email, message = spec["name"], spec["email"], spec["message"]
    key = f"tecnica-{run_id}-{name}"
    marker = spec.get("fixture_marker")
    before = fixture_count(stub_url, marker) if marker else None
    status, body, raw, duration = call_webhook(base_url, email, message, key)
    after = fixture_count(stub_url, marker) if marker else None
    receipt_id = body.get("recepcion_id") if isinstance(body, dict) else None
    receipt = api_get(api_url, f"/recepciones/{receipt_id}") if receipt_id is not None else None
    request_id = request_id_from_webhook(body)
    request = api_get(api_url, f"/solicitudes/{request_id}") if request_id is not None else None

    checks = {"webhook_status": status == spec["expected_status"]}
    receipt_body = receipt.get("body") if receipt else None
    request_body = request.get("body") if request else None
    if spec.get("receipt_state") is not None:
        checks["receipt_persisted"] = receipt is not None and receipt["http_status"] == 200
        checks["receipt_state"] = isinstance(receipt_body, dict) and receipt_body.get("estado") == spec["receipt_state"]
        checks["receipt_attempts"] = isinstance(receipt_body, dict) and receipt_body.get("intentos_llm") == spec["attempts"]
    if spec.get("fixture_calls") is not None:
        checks["actual_fixture_calls"] = (after - before) == spec["fixture_calls"]
    if spec.get("classification") is not None:
        actual = body.get("clasificacion") if isinstance(body, dict) else None
        checks["classification"] = isinstance(actual, dict) and all(actual.get(k) == v for k, v in spec["classification"].items())
    for key_name, expected in spec.get("request", {}).items():
        checks[f"request_{key_name}"] = isinstance(request_body, dict) and request_body.get(key_name) == expected
    if "alert_reasons" in spec:
        actual_alerts = (body or {}).get("motivos_alerta") or []
        checks["alert_reasons"] = set(actual_alerts) == set(spec["alert_reasons"])
    if "notification_state" in spec:
        checks["notification_disabled"] = isinstance(body, dict) and body.get("notificacion_estado") == spec["notification_state"]
    if "sin_stock" in spec:
        checks["sin_stock"] = isinstance(body, dict) and body.get("sin_stock") is spec["sin_stock"]
    if "revision_reason" in spec:
        reasons = (body or {}).get("motivos_revision") or []
        checks["revision_reason"] = spec["revision_reason"] in reasons
    if spec.get("requires_no_request"):
        checks["no_request_created"] = request_id is None and isinstance(receipt_body, dict) and receipt_body.get("solicitud_id") is None

    return {
        "case": name,
        "request": {"cliente_email": email, "mensaje": message, "idempotency_key": key},
        "http_status": status,
        "expected_http_status": spec["expected_status"],
        "duration_seconds": duration,
        "response": body if body is not None else raw,
        "recepcion_api": receipt,
        "solicitud_api": request,
        "fixture_calls": None if marker is None else after - before,
        "checks": checks,
        "pass": all(checks.values()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--webhook", default="http://127.0.0.1:5689")
    parser.add_argument("--api", default="http://127.0.0.1:18019")
    parser.add_argument("--stub", default="http://127.0.0.1:5690")
    parser.add_argument("--output-dir", default=str(ROOT / "flujo" / "evidencias" / "tecnica"))
    args = parser.parse_args()

    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    run_id = uuid.uuid4().hex[:12]
    specs = [
        {"name": "B1_resmas_urgentes", "email": "compras@ferreteriaeltornillo.com", "message": "Buenos días, necesitamos 10 resmas de papel carta para el viernes, es urgente.", "expected_status": 201, "receipt_state": "registrada", "attempts": 1, "fixture_marker": "10 resmas", "fixture_calls": 1, "classification": {"tipo": "pedido", "cantidad": 10, "urgencia": "alta"}, "request": {"cliente_id": 1, "producto_id": 1, "cantidad": 10}, "alert_reasons": ["urgencia_alta"], "notification_state": "pendiente"},
        {"name": "B2_consulta_diademas", "email": "compras@clinicalosandes.com", "message": "Hola, ¿tienen diademas con micrófono? ¿Cuánto valen y en cuánto tiempo llegan?", "expected_status": 201, "receipt_state": "registrada", "attempts": 1, "fixture_marker": "diademas con micrófono", "fixture_calls": 1, "classification": {"tipo": "consulta", "cantidad": None}, "request": {"cliente_id": 5, "producto_id": 11, "cantidad": None}},
        {"name": "B3_queja_toner", "email": "compras@oficinasmodernassas.com", "message": "Es la segunda vez que el tóner llega dañado. Estamos muy molestos, necesitamos que nos respondan hoy mismo.", "expected_status": 201, "receipt_state": "registrada", "attempts": 1, "fixture_marker": "segunda vez que el tóner", "fixture_calls": 1, "classification": {"tipo": "queja", "cantidad": None, "urgencia": "alta"}, "request": {"cliente_id": 3, "producto_id": 2, "cantidad": None}, "alert_reasons": ["queja", "urgencia_alta"], "notification_state": "pendiente"},
        {"name": "B4_stock_escritorios", "email": "compras@constructorahorizonte.com", "message": "Por favor despachar 6 escritorios en L para la nueva oficina de Rionegro.", "expected_status": 201, "receipt_state": "registrada", "attempts": 1, "fixture_marker": "despachar 6 escritorios", "fixture_calls": 1, "classification": {"tipo": "pedido", "cantidad": 6}, "request": {"cliente_id": 10, "producto_id": 4, "cantidad": 6}, "sin_stock": True, "alert_reasons": ["stock_insuficiente"], "notification_state": "pendiente"},
        {"name": "B5_cliente_desconocido", "email": "juanperez.compras@gmail.com", "message": "hola buenas q precio tienen los mouse inalambricos y si hacen envios", "expected_status": 202, "receipt_state": "revision_manual", "attempts": 1, "fixture_marker": "mouse inalambricos", "fixture_calls": 1, "classification": {"tipo": "consulta", "cantidad": None}, "requires_no_request": True, "revision_reason": "cliente_desconocido"},
        {"name": "retry_invalido_luego_valido", "email": "compras@clinicalosandes.com", "message": "FIXTURE_RETRY_INVALID_THEN_VALID consulta de prueba de reintento.", "expected_status": 201, "receipt_state": "registrada", "attempts": 2, "fixture_marker": "FIXTURE_RETRY_INVALID_THEN_VALID", "fixture_calls": 2, "classification": {"tipo": "consulta", "cantidad": None}},
        {"name": "json_schema_invalido_luego_valido", "email": "compras@clinicalosandes.com", "message": "FIXTURE_SCHEMA_INVALID_THEN_VALID consulta de prueba con enum inválido en el primer resultado.", "expected_status": 201, "receipt_state": "registrada", "attempts": 2, "fixture_marker": "FIXTURE_SCHEMA_INVALID_THEN_VALID", "fixture_calls": 2, "classification": {"tipo": "consulta", "cantidad": None}},
        {"name": "dos_respuestas_invalidas_revision", "email": "compras@clinicalosandes.com", "message": "FIXTURE_ALWAYS_INVALID solicitud que requiere revisión manual.", "expected_status": 202, "receipt_state": "revision_manual", "attempts": 2, "fixture_marker": "FIXTURE_ALWAYS_INVALID", "fixture_calls": 2, "requires_no_request": True},
        {"name": "multiples_productos_revision", "email": "compras@clinicalosandes.com", "message": "FIXTURE_MULTIPRODUCT Necesitamos 2 resmas de papel carta y 3 mouse inalámbricos.", "expected_status": 202, "receipt_state": "revision_manual", "attempts": 1, "fixture_marker": "FIXTURE_MULTIPRODUCT", "fixture_calls": 1, "classification": {"tipo": "pedido", "producto": "resma papel carta", "cantidad": 2}, "requires_no_request": True, "revision_reason": "multiples_productos"},
        {"name": "producto_ajeno_catalogo_revision", "email": "compras@clinicalosandes.com", "message": "FIXTURE_UNKNOWN_PRODUCT ¿Tienen impresora láser industrial?", "expected_status": 202, "receipt_state": "revision_manual", "attempts": 1, "fixture_marker": "FIXTURE_UNKNOWN_PRODUCT", "fixture_calls": 1, "classification": {"tipo": "consulta", "producto": "impresora láser industrial", "cantidad": None}, "requires_no_request": True, "revision_reason": "producto_no_encontrado"},
        {"name": "proveedor_401", "email": "compras@clinicalosandes.com", "message": "FIXTURE_HTTP_401 error sintético de autenticación del proveedor.", "expected_status": 202, "receipt_state": "revision_manual", "attempts": 1, "fixture_marker": "FIXTURE_HTTP_401", "fixture_calls": 1, "requires_no_request": True},
        {"name": "proveedor_503", "email": "compras@clinicalosandes.com", "message": "FIXTURE_HTTP_503 error sintético de disponibilidad del proveedor.", "expected_status": 202, "receipt_state": "revision_manual", "attempts": 2, "fixture_marker": "FIXTURE_HTTP_503", "fixture_calls": 2, "requires_no_request": True},
        {"name": "proveedor_timeout_conexion", "email": "compras@clinicalosandes.com", "message": "FIXTURE_TIMEOUT corte sintético de conexión del proveedor.", "expected_status": 202, "receipt_state": "revision_manual", "attempts": 2, "fixture_marker": "FIXTURE_TIMEOUT", "fixture_calls": 2, "requires_no_request": True},
    ]

    health = request_json(args.api.rstrip("/") + "/health", timeout=5)
    if health[0] != 200:
        print(f"API técnica no disponible en {args.api}: HTTP {health[0]} {health[2]}", file=sys.stderr)
        return 2
    stub = request_json(args.stub.rstrip("/") + "/healthz", timeout=5)
    if stub[0] != 200 or not (isinstance(stub[1], dict) and stub[1].get("fixture") is True):
        print(f"El proveedor fixture no responde en {args.stub}.", file=sys.stderr)
        return 2
    reset_status, reset_body, reset_raw = request_json(
        args.stub.rstrip("/") + "/reset",
        payload={},
        headers={"Authorization": "Bearer test-double-only-not-a-real-key"},
        timeout=5,
    )
    if reset_status != 200 or not (isinstance(reset_body, dict) and reset_body.get("status") == "reset"):
        print(f"No se pudo reiniciar el contador aislado del fixture: HTTP {reset_status} {reset_raw}", file=sys.stderr)
        return 2

    results = []
    for spec in specs:
        result = run_case(spec, args.webhook, args.api, args.stub, run_id)
        results.append(result)
        print(f"{'OK' if result['pass'] else 'REVISAR'} {spec['name']}: HTTP {result['http_status']}, {sum(result['checks'].values())}/{len(result['checks'])} aserciones, {result['duration_seconds']} s")

    # Reentrega exacta: mismo resultado y ninguna llamada extra al fixture.
    b1 = specs[0]
    key = f"tecnica-{run_id}-{b1['name']}"
    before_replay = fixture_count(args.stub, b1["fixture_marker"])
    replay_status, replay_body, replay_raw, replay_duration = call_webhook(args.webhook, b1["email"], b1["message"], key)
    after_replay = fixture_count(args.stub, b1["fixture_marker"])
    original = results[0].get("response") or {}
    replay = {
        "case": "replay_misma_clave_y_cuerpo",
        "http_status": replay_status,
        "duration_seconds": replay_duration,
        "response": replay_body if replay_body is not None else replay_raw,
        "fixture_calls_before": before_replay,
        "fixture_calls_after": after_replay,
        "checks": {
            "http_200": replay_status == 200,
            "same_reception": isinstance(replay_body, dict) and replay_body.get("recepcion_id") == original.get("recepcion_id"),
            "same_request": isinstance(replay_body, dict) and request_id_from_webhook(replay_body) == request_id_from_webhook(original),
            "no_extra_llm_call": after_replay == before_replay,
        },
    }
    replay["pass"] = all(replay["checks"].values())
    results.append(replay)
    print(f"{'OK' if replay['pass'] else 'REVISAR'} replay mismo cuerpo/clave: {replay_status}, fixture {before_replay}->{after_replay}")

    # Mismo Idempotency-Key con otro cuerpo debe ser rechazado por la API.
    conflict_status, conflict_body, conflict_raw, conflict_duration = call_webhook(
        args.webhook, b1["email"], "Cuerpo distinto para probar el conflicto de idempotencia.", key, timeout=20
    )
    conflict = {"case": "misma_clave_cuerpo_distinto_via_webhook", "http_status": conflict_status,
                "duration_seconds": conflict_duration,
                "response": conflict_body if conflict_body is not None else conflict_raw,
                "pass": conflict_status == 409}
    results.append(conflict)
    print(f"{'OK' if conflict['pass'] else 'REVISAR'} clave repetida con cuerpo distinto: HTTP {conflict_status}")

    # Validación antes de persistir o llamar al proveedor.
    invalid_before = fixture_count(args.stub, "fixture_invalid_input")
    invalid_status, invalid_body, invalid_raw, invalid_duration = call_webhook(
        args.webhook, "", "mensaje sin correo válido", f"tecnica-{run_id}-entrada-invalida"
    )
    invalid_after = fixture_count(args.stub, "fixture_invalid_input")
    invalid = {"case": "entrada_invalida", "http_status": invalid_status,
               "duration_seconds": invalid_duration,
               "response": invalid_body if invalid_body is not None else invalid_raw,
               "fixture_calls_before": invalid_before, "fixture_calls_after": invalid_after,
               "pass": invalid_status == 422 and invalid_after == invalid_before}
    results.append(invalid)
    print(f"{'OK' if invalid['pass'] else 'REVISAR'} entrada inválida: HTTP {invalid_status}, sin llamada LLM")

    artifact = {
        "kind": "simulacion_tecnica_integrada",
        "provider": "doble HTTP local y determinista; no es DeepSeek",
        "email": "NOTIFICATIONS_ENABLED=false y SMTP vacío en el Compose técnico; no se envió correo",
        "started_at_utc": started_at,
        "run_id": run_id,
        "webhook": args.webhook.rstrip("/") + "/webhook/solicitud",
        "api": args.api,
        "fixture": args.stub,
        "results": results,
        "passed": sum(1 for result in results if result["pass"]),
        "total": len(results),
    }
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"integracion-{timestamp}-{run_id}.json"
    output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Evidencia técnica simulada: {output_path}")
    print(f"Resultado: {artifact['passed']}/{artifact['total']} grupos de aserciones")
    return 0 if artifact["passed"] == artifact["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
