import sqlite3
import ssl
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.database import connect, initialize_database
from api.main import create_app


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("NOTIFICATIONS_ENABLED", "false")
    monkeypatch.setenv("SMTP_USERNAME", "fixture@example.test")
    monkeypatch.setenv("SMTP_PASSWORD", "fixture-password")
    app = create_app(db_path, ROOT / "material" / "datos_prueba.sql")
    with TestClient(app) as test_client:
        yield test_client, db_path


def test_seed_search_and_read_only_restart(client):
    api, db_path = client
    assert api.get("/health").json()["database"] == "ok"
    assert api.get("/clientes", params={"email": "  COMPRAS@FERRETERIAELTORNILLO.COM "}).json()["id"] == 1
    assert api.get("/clientes", params={"email": "nadie@example.com"}).status_code == 404
    assert [p["id"] for p in api.get("/productos", params={"q": "inalambrico"}).json()] == [5]
    assert api.get("/productos", params={"q": "toner"}).json()[0]["id"] == 2
    assert len(api.get("/productos").json()) == 12
    added = api.post("/solicitudes", json={
        "cliente_id": 11, "producto_id": None, "tipo": "consulta", "cantidad": None,
        "urgencia": "baja", "mensaje": "¿Cuál es el horario de atención?"
    })
    assert added.status_code == 201
    initialize_database(db_path, ROOT / "material" / "datos_prueba.sql")
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT COUNT(*) FROM solicitudes").fetchone()[0] == 61
    with connect(db_path) as db:
        assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO solicitudes(cliente_id, tipo, urgencia, estado, mensaje, fecha_creacion) VALUES (999, 'consulta', 'baja', 'pendiente', 'x', '2026-10-19')")


def test_create_order_with_insufficient_stock_alerts_without_reserving(client):
    api, db_path = client
    response = api.post("/solicitudes", json={
        "cliente_id": 10, "producto_id": 4, "tipo": "pedido", "cantidad": 6,
        "urgencia": "media", "mensaje": "Seis escritorios en L", "resumen": "Pedido de seis escritorios"
    })
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["sin_stock"] is True
    assert result["stock_verificado"] is True
    assert result["motivos_alerta"] == ["stock_insuficiente"]
    assert result["notificacion_id"] is not None
    assert api.get(f"/solicitudes/{result['id']}").json()["sin_stock"] is True
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT stock FROM productos WHERE id=4").fetchone()[0] == 3
        assert db.execute("SELECT COUNT(*) FROM notificaciones WHERE solicitud_id=?", (result["id"],)).fetchone()[0] == 1
    notification = api.post(f"/notificaciones/{result['notificacion_id']}/enviar").json()
    assert notification["estado"] == "pendiente" and notification["enviado"] is False


@pytest.mark.parametrize("body", [
    {"cliente_id": 1, "producto_id": 1, "tipo": "pedido", "cantidad": 0, "urgencia": "baja", "mensaje": "x"},
    {"cliente_id": 1, "producto_id": 1, "tipo": "pedido", "cantidad": True, "urgencia": "baja", "mensaje": "x"},
    {"cliente_id": 1, "producto_id": 1, "tipo": "pedido", "cantidad": 1.5, "urgencia": "baja", "mensaje": "x"},
    {"cliente_id": 1, "producto_id": 1, "tipo": "consulta", "cantidad": 1, "urgencia": "baja", "mensaje": "x"},
    {"cliente_id": 1, "producto_id": None, "tipo": "pedido", "cantidad": None, "urgencia": "baja", "mensaje": "x"},
])
def test_invalid_business_fields_are_rejected(client, body):
    response = client[0].post("/solicitudes", json=body)
    assert response.status_code == 422


def test_status_transitions_and_resolution_timestamp_is_stable(client):
    api, _ = client
    first = api.patch("/solicitudes/1", json={"estado": "resuelta"})
    assert first.status_code == 200
    resolved_at = first.json()["fecha_resolucion"]
    second = api.patch("/solicitudes/1", json={"estado": "resuelta"})
    assert second.json()["fecha_resolucion"] == resolved_at
    assert api.patch("/solicitudes/1", json={"estado": "pendiente"}).status_code == 409
    assert api.patch("/solicitudes/9999", json={"estado": "resuelta"}).status_code == 404


def test_reception_idempotency_and_unknown_customer_review(client):
    api, db_path = client
    headers = {"Idempotency-Key": "webhook-test-1"}
    payload = {"cliente_email": "unknown@example.com", "mensaje": "¿Tienen mouse inalámbricos?"}
    created = api.post("/recepciones", json=payload, headers=headers)
    assert created.status_code == 201
    replay = api.post("/recepciones", json=payload, headers=headers)
    assert replay.status_code == 200
    assert replay.json()["recepcion_id"] == created.json()["recepcion_id"]
    assert api.post("/recepciones", json={**payload, "mensaje": "otro"}, headers=headers).status_code == 409

    reception_id = created.json()["recepcion_id"]
    classified = api.patch(f"/recepciones/{reception_id}", json={
        "estado": "revision_manual", "clasificacion": {
            "tipo": "consulta", "producto": "mouse inalámbrico", "cantidad": None,
            "urgencia": "baja", "resumen": "Consulta por mouse inalámbricos"
        }, "intentos_llm": 1, "motivos_revision": ["cliente_desconocido"]
    })
    assert classified.status_code == 200, classified.text
    assert classified.json()["clasificacion"]["tipo"] == "consulta"
    assert api.get(f"/recepciones/{reception_id}").json()["estado"] == "revision_manual"
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT COUNT(*) FROM solicitudes").fetchone()[0] == 60


def test_valid_reception_is_idempotent_through_request_and_outbox(client):
    api, db_path = client
    headers = {"Idempotency-Key": "webhook-test-2"}
    reception = api.post("/recepciones", json={
        "cliente_email": "compras@oficinasmodernassas.com", "mensaje": "El tóner llegó dañado, respondan hoy"
    }, headers=headers).json()
    rid = reception["recepcion_id"]
    api.patch(f"/recepciones/{rid}", json={
        "estado": "procesando", "clasificacion": {
            "tipo": "queja", "producto": "Tóner HP 85A", "cantidad": None,
            "urgencia": "alta", "resumen": "Queja por tóner dañado"
        }, "intentos_llm": 1, "motivos_revision": []
    })
    body = {"recepcion_id": rid, "cliente_id": 3, "producto_id": 2, "tipo": "queja", "cantidad": None,
            "urgencia": "alta", "mensaje": "El tóner llegó dañado, respondan hoy", "resumen": "Queja por tóner dañado"}
    first = api.post("/solicitudes", json=body)
    assert first.status_code == 201, first.text
    replay = api.post("/solicitudes", json=body)
    assert replay.status_code == 200
    assert replay.json()["id"] == first.json()["id"]
    assert first.json()["motivos_alerta"] == ["queja", "urgencia_alta"]
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT COUNT(*) FROM solicitudes WHERE recepcion_id=?", (rid,)).fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM notificaciones WHERE solicitud_id=?", (first.json()["id"],)).fetchone()[0] == 1
    assert api.patch(f"/recepciones/{rid}", json={
        "estado": "revision_manual", "clasificacion": None, "intentos_llm": 2,
        "motivos_revision": ["llm_unavailable"]
    }).status_code == 409


def test_reception_cannot_be_attached_to_another_customer_or_message(client):
    api, _ = client
    reception = api.post("/recepciones", json={
        "cliente_email": "compras@oficinasmodernassas.com", "mensaje": "Necesitamos una resma"
    }, headers={"Idempotency-Key": "ownership-check"}).json()
    assert api.patch(f"/recepciones/{reception['recepcion_id']}", json={
        "estado": "registrada", "clasificacion": None, "intentos_llm": 0, "motivos_revision": []
    }).status_code == 409
    base = {"recepcion_id": reception["recepcion_id"], "cliente_id": 1, "producto_id": 1,
            "tipo": "pedido", "cantidad": 1, "urgencia": "baja", "mensaje": "Necesitamos una resma"}
    assert api.post("/solicitudes", json=base).status_code == 409
    mismatched_message = {**base, "cliente_id": 3, "mensaje": "Otro mensaje"}
    assert api.post("/solicitudes", json=mismatched_message).status_code == 409
    assert api.post("/solicitudes", json={**base, "recepcion_id": 999999, "cliente_id": 3}).status_code == 404


def test_smtp_sent_state_is_idempotent_and_uses_fixed_recipient(client, monkeypatch):
    api, _ = client
    monkeypatch.setenv("NOTIFICATIONS_ENABLED", "true")
    monkeypatch.setenv("SMTP_HOST", "mail.example.test")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_FROM", "alerts@example.test")
    monkeypatch.setenv("NOTIFICATION_TO", "owner@example.test")
    calls = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            assert host == "mail.example.test" and port == 587
        def starttls(self, context=None):
            assert context is not None
            assert context.verify_mode == ssl.CERT_REQUIRED
            assert context.check_hostname is True
        def login(self, username, password):
            pass
        def send_message(self, message):
            calls.append(message)
        def quit(self):
            pass

    monkeypatch.setattr("api.main.smtplib.SMTP", FakeSMTP)
    created = api.post("/solicitudes", json={
        "cliente_id": 3, "producto_id": 2, "tipo": "queja", "cantidad": None,
        "urgencia": "alta", "mensaje": "Tóner dañado"
    }).json()
    first = api.post(f"/notificaciones/{created['notificacion_id']}/enviar").json()
    assert first["estado"] == "enviada" and first["enviado"] is True
    assert calls[0]["To"] == "owner@example.test"
    assert first["message_id"] == calls[0]["Message-ID"]
    assert first["message_id"] and first["fecha_actualizacion"]
    assert calls[0].get_content_type() == "multipart/alternative"
    plain = calls[0].get_body(preferencelist=("plain",)).get_content()
    html = calls[0].get_body(preferencelist=("html",)).get_content()
    assert "Queja de cliente" in plain and "Urgencia alta" in plain
    assert "Queja de cliente" in html and "Urgencia alta" in html
    assert "urgencia_alta" not in html and "queja" not in html
    assert "Solicitud #" in calls[0]["Subject"]
    monkeypatch.setenv("NOTIFICATIONS_ENABLED", "false")
    second = api.post(f"/notificaciones/{created['notificacion_id']}/enviar").json()
    assert second["estado"] == "enviada" and len(calls) == 1
    assert second["message_id"] == first["message_id"]
    assert second["fecha_actualizacion"] == first["fecha_actualizacion"]


def test_smtp_failure_before_send_is_recoverable_and_request_remains(client, monkeypatch):
    api, db_path = client
    monkeypatch.setenv("NOTIFICATIONS_ENABLED", "true")
    monkeypatch.setenv("SMTP_HOST", "mail.example.test")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_FROM", "alerts@example.test")
    monkeypatch.setenv("NOTIFICATION_TO", "owner@example.test")
    created = api.post("/solicitudes", json={
        "cliente_id": 3, "producto_id": 2, "tipo": "queja", "cantidad": None,
        "urgencia": "alta", "mensaje": "Tóner dañado"
    }).json()

    def fail_to_connect(*args, **kwargs):
        raise OSError("offline")

    monkeypatch.setattr("api.main.smtplib.SMTP", fail_to_connect)
    failed = api.post(f"/notificaciones/{created['notificacion_id']}/enviar").json()
    assert failed["estado"] == "fallida" and failed["enviado"] is False
    failed_message_id = failed["message_id"]
    assert failed_message_id and failed["fecha_actualizacion"]
    assert api.get(f"/solicitudes/{created['id']}").status_code == 200
    received_message_ids = []

    class FakeSMTP:
        def __init__(self, *args, **kwargs): pass
        def starttls(self, context=None):
            assert context is not None
            assert context.verify_mode == ssl.CERT_REQUIRED
            assert context.check_hostname is True
        def login(self, username, password): pass
        def send_message(self, message):
            received_message_ids.append(message["Message-ID"])
        def quit(self): pass

    monkeypatch.setattr("api.main.smtplib.SMTP", FakeSMTP)
    retried = api.post(f"/notificaciones/{created['notificacion_id']}/enviar").json()
    assert retried["estado"] == "enviada"
    assert retried["message_id"] == failed_message_id == received_message_ids[0]
    assert retried["fecha_actualizacion"]
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT COUNT(*) FROM solicitudes WHERE id=?", (created["id"],)).fetchone()[0] == 1


def test_smtp_ambiguous_result_is_not_retried(client, monkeypatch):
    api, _ = client
    monkeypatch.setenv("NOTIFICATIONS_ENABLED", "true")
    monkeypatch.setenv("SMTP_HOST", "mail.example.test")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_FROM", "alerts@example.test")
    monkeypatch.setenv("NOTIFICATION_TO", "owner@example.test")
    send_attempts = []

    class AmbiguousSMTP:
        def __init__(self, *args, **kwargs): pass
        def starttls(self, context=None):
            assert context is not None
            assert context.verify_mode == ssl.CERT_REQUIRED
            assert context.check_hostname is True
        def login(self, username, password): pass
        def send_message(self, message):
            send_attempts.append(message["Message-ID"])
            raise OSError("connection lost after send began")
        def quit(self): pass

    monkeypatch.setattr("api.main.smtplib.SMTP", AmbiguousSMTP)
    created = api.post("/solicitudes", json={
        "cliente_id": 3, "producto_id": 2, "tipo": "queja", "cantidad": None,
        "urgencia": "alta", "mensaje": "Tóner dañado"
    }).json()
    first = api.post(f"/notificaciones/{created['notificacion_id']}/enviar").json()
    second = api.post(f"/notificaciones/{created['notificacion_id']}/enviar").json()
    assert first["estado"] == "incierta"
    assert second["estado"] == "incierta"
    assert first["message_id"] and second["message_id"] == first["message_id"]
    assert len(send_attempts) == 1
    assert send_attempts[0] == first["message_id"]


def test_list_filters_details_and_pagination(client):
    api, _ = client
    result = api.get("/solicitudes", params={"tipo": "queja", "estado": "pendiente", "limit": 1, "offset": 0})
    assert result.status_code == 200
    assert result.json()["total"] > 0
    assert len(result.json()["items"]) == 1
    detail = api.get("/solicitudes/1").json()
    assert detail["cliente_nombre"] == "Ferretería El Tornillo"
    assert detail["producto_nombre"] == "Monitor 24 pulgadas"
    assert api.get("/solicitudes", params={"limit": 0}).status_code == 422
    assert api.get("/solicitudes", params={"estado": "otra"}).status_code == 422


def test_sql_queries_return_expected_seed_results(client):
    _, db_path = client
    sql_text = (ROOT / "sql" / "consultas.sql").read_text(encoding="utf-8")
    queries = [part.strip() for part in sql_text.split(";") if part.strip() and not part.strip().startswith("--")]
    # Semicolons separate complete queries; comments are intentionally retained in the file.
    queries = []
    current = []
    for line in sql_text.splitlines():
        if line.lstrip().startswith("--"):
            continue
        current.append(line)
        if ";" in line:
            queries.append("\n".join(current).split(";")[0])
            current = []
    assert len(queries) == 6
    with sqlite3.connect(db_path) as db:
        results = [db.execute(query).fetchall() for query in queries]
    assert len(results[0]) == 11
    assert [(row[0], row[1], row[2]) for row in results[1]] == [
        ("consulta", 18, 30.0), ("pedido", 30, 50.0), ("queja", 12, 20.0)
    ]
    assert [(row[0], row[1], row[2]) for row in results[2]] == [
        ("Ferretería El Tornillo", "Bogotá", 4), ("Clínica Los Andes", "Bogotá", 2),
        ("Colegio San Martín", "Bucaramanga", 2), ("Oficinas Modernas SAS", "Cali", 2)
    ]
    assert [(row[0], row[1]) for row in results[3]] == [
        ("consulta", 51.0), ("pedido", 66.61), ("queja", 72.8)
    ]
    assert any(row[1] == "Agencia Creativa Pixel" and row[2] is None for row in results[5])
    assert len(results[4]) == 4
