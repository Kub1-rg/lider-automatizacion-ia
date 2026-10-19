"""Genera previews .html/.txt/.eml con fixtures ficticios y el renderer de producción."""
from __future__ import annotations

from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api.email_templates import render_notification


OUT = ROOT / "flujo" / "evidencias" / "correo-html"
FIXTURES = [
    {
        "slug": "preview-b3-queja",
        "data": {
            "notification_id": "PREVIEW-B3", "request_id": "PREVIEW-B3",
            "customer_name": "Oficinas Modernas SAS", "product_name": "Tóner HP 85A",
            "tipo": "queja", "cantidad": None, "urgencia": "alta", "estado": "pendiente",
            "fecha_creacion": "2026-10-19T20:00:00+00:00",
            "resumen": "El cliente reporta que el tóner llegó dañado y solicita respuesta hoy.",
            "mensaje": "Es la segunda vez que el tóner llega dañado. Estamos muy molestos, necesitamos que nos respondan hoy mismo.",
            "motivos_alerta": ["queja", "urgencia_alta"], "sin_stock": False, "stock_available": 12,
        },
        "subject": "Queja prioritaria — Solicitud de muestra B3",
    },
    {
        "slug": "preview-b4-stock-insuficiente",
        "data": {
            "notification_id": "PREVIEW-B4", "request_id": "PREVIEW-B4",
            "customer_name": "Constructora Horizonte", "product_name": "Escritorio en L",
            "tipo": "pedido", "cantidad": 6, "urgencia": "baja", "estado": "pendiente",
            "fecha_creacion": "2026-10-19T20:05:00+00:00",
            "resumen": "Solicitud de seis escritorios en L para una nueva oficina.",
            "mensaje": "Por favor despachar 6 escritorios en L para la nueva oficina de Rionegro.",
            "motivos_alerta": ["stock_insuficiente"], "sin_stock": True, "stock_available": 3,
        },
        "subject": "Pedido con stock insuficiente — Solicitud de muestra B4",
    },
    {
        "slug": "preview-urgencia-alta",
        "data": {
            "notification_id": "PREVIEW-URGENTE", "request_id": "PREVIEW-URGENTE",
            "customer_name": "Ferretería El Tornillo", "product_name": "Resma papel carta",
            "tipo": "pedido", "cantidad": 10, "urgencia": "alta", "estado": "pendiente",
            "fecha_creacion": "2026-10-19T20:10:00+00:00",
            "resumen": "Pedido urgente de diez resmas de papel carta.",
            "mensaje": "Buenos días, necesitamos 10 resmas de papel carta para el viernes, es urgente.",
            "motivos_alerta": ["urgencia_alta"], "sin_stock": False, "stock_available": 340,
        },
        "subject": "Urgencia alta — Solicitud de muestra",
    },
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for fixture in FIXTURES:
        plain, html = render_notification(fixture["data"])
        (OUT / f"{fixture['slug']}.html").write_text(html, encoding="utf-8")
        (OUT / f"{fixture['slug']}.txt").write_text(plain, encoding="utf-8")
        message = EmailMessage()
        message["From"] = "Suministros Andinos <avisos@example.test>"
        message["To"] = "Equipo de atención <equipo@example.test>"
        message["Subject"] = fixture["subject"]
        message["Message-ID"] = make_msgid(domain="example.test")
        message.set_content(plain)
        message.add_alternative(html, subtype="html")
        (OUT / f"{fixture['slug']}.eml").write_bytes(message.as_bytes())
    print(f"Generadas {len(FIXTURES)} previews HTML, texto y MIME en {OUT}.")


if __name__ == "__main__":
    main()
