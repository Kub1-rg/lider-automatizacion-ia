from html.parser import HTMLParser

from api.email_templates import render_notification


class TagCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
    def handle_starttag(self, tag, attrs):
        self.tags.append(tag.lower())


def sample(**overrides):
    data = {
        "notification_id": 18,
        "request_id": 66,
        "customer_name": "Constructora Horizonte",
        "product_name": "Escritorio en L",
        "tipo": "pedido",
        "cantidad": 6,
        "urgencia": "baja",
        "estado": "pendiente",
        "fecha_creacion": "2026-10-19T21:28:08+00:00",
        "resumen": "Pedido de seis escritorios en L.",
        "mensaje": "Por favor despachar seis escritorios en L.",
        "motivos_alerta": ["stock_insuficiente"],
        "sin_stock": True,
        "stock_available": 3,
    }
    data.update(overrides)
    return data


def test_stock_shortfall_is_explicit_and_does_not_claim_reservation():
    plain, html = render_notification(sample())
    assert "Cantidad solicitada: 6 unidades" in plain
    assert "Disponible ahora en catálogo: 3 unidades" in plain
    assert "Faltante según esta lectura: 3 unidades" in plain
    assert "no representa una reserva" in plain
    assert "6 unidades" in html and "3 unidades" in html
    assert "Stock insuficiente" in html
    assert "stock_insuficiente" not in html


def test_hostile_customer_product_summary_and_message_are_html_escaped():
    hostile = sample(
        customer_name='<script>alert("x")</script> & Co',
        product_name='Escritorio </td><img src=x onerror="alert(1)">',
        resumen='<svg/onload=alert(1)> "resumen" & más',
        mensaje='</div><script>alert("mensaje")</script> & "comillas"\nsegunda línea',
        motivos_alerta=["unknown<code>", "urgencia_alta"],
    )
    plain, rendered = render_notification(hostile)
    parser = TagCollector()
    parser.feed(rendered)
    assert "script" not in parser.tags and "img" not in parser.tags and "svg" not in parser.tags
    assert "&lt;script&gt;" in rendered
    assert "&lt;img" in rendered and "onerror=&quot;alert(1)&quot;" in rendered
    assert "&lt;svg/onload=alert(1)&gt;" in rendered
    assert "unknown&lt;code&gt;" not in rendered and "unknown<code>" not in rendered
    assert "urgencia_alta" not in rendered and "Urgencia alta" in rendered
    assert "<script>" in plain and "<img" in plain  # Plain text stays readable as source text.


def test_date_uses_bogota_only_when_timestamp_has_timezone():
    plain, _ = render_notification(sample(fecha_creacion="2026-10-19T21:28:08+00:00"))
    assert "19 de octubre de 2026, 16:28 (hora Colombia)" in plain
    naive_plain, _ = render_notification(sample(fecha_creacion="2026-10-19 21:28:08"))
    assert "Recibida:" not in naive_plain
