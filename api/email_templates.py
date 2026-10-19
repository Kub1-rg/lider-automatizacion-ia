"""Plantillas puras para avisos de solicitud por correo."""
from __future__ import annotations

import html
from datetime import datetime
from zoneinfo import ZoneInfo


BOGOTA = ZoneInfo("America/Bogota")
MONTHS_ES = ("enero", "febrero", "marzo", "abril", "mayo", "junio",
             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")
REASON_LABELS = {
    "queja": "Queja de cliente",
    "urgencia_alta": "Urgencia alta",
    "stock_insuficiente": "Stock insuficiente",
}
URGENCY_LABELS = {"alta": "Alta", "media": "Media", "baja": "Baja"}
STATUS_LABELS = {"pendiente": "Pendiente", "en_proceso": "En proceso", "resuelta": "Resuelta"}


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def _date_label(value: str | None) -> str | None:
    """Format a timezone-aware stored timestamp; omit unknown/naive timestamps."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    local = parsed.astimezone(BOGOTA)
    return (f"{local.day:02d} de {MONTHS_ES[local.month - 1]} de {local.year}, "
            f"{local.hour:02d}:{local.minute:02d} (hora Colombia)")


def _reason_labels(reasons: list[str] | tuple[str, ...]) -> list[str]:
    # Unknown codes receive a generic user-facing label; internal codes stay out of mail.
    return [REASON_LABELS.get(_text(code), "Alerta de atención") for code in reasons]


def _context(data: dict) -> dict:
    request_id = _text(data.get("request_id"))
    request_type = _text(data.get("tipo"))
    title = ("Queja prioritaria: revisar respuesta al cliente" if request_type == "queja"
             else "Pedido con stock insuficiente" if data.get("sin_stock")
             else "Solicitud prioritaria" if _text(data.get("urgencia")) == "alta"
             else "Nueva solicitud de cliente")
    quantity = data.get("cantidad")
    stock = data.get("stock_available")
    missing = None
    if data.get("sin_stock") and isinstance(quantity, int) and isinstance(stock, int):
        missing = max(0, quantity - stock)
    return {
        "request_id": request_id,
        "title": title,
        "customer_name": _text(data.get("customer_name")) or "Cliente",
        "product_name": _text(data.get("product_name")) or "No especificado",
        "quantity": quantity if isinstance(quantity, int) and not isinstance(quantity, bool) else None,
        "status": STATUS_LABELS.get(_text(data.get("estado")), "Pendiente"),
        "urgency": URGENCY_LABELS.get(_text(data.get("urgencia")), "No indicada"),
        "date_label": _date_label(data.get("fecha_creacion")),
        "summary": _text(data.get("resumen")),
        "original_message": _text(data.get("mensaje")),
        "reason_labels": _reason_labels(data.get("motivos_alerta") or []),
        "sin_stock": bool(data.get("sin_stock")),
        "stock_available": stock if isinstance(stock, int) and not isinstance(stock, bool) else None,
        "missing": missing,
        "notification_id": _text(data.get("notification_id")),
    }


def render_notification(data: dict) -> tuple[str, str]:
    """Return `(plain_text, html)` for a transmittable request notification."""
    c = _context(data)
    product_line = f"Producto: {c['product_name']}"
    if c["quantity"] is not None:
        product_line += f"\nCantidad solicitada: {c['quantity']} unidades"
    reason_text = "\n".join(f"• {label}" for label in c["reason_labels"])
    lines = [
        f"Solicitud #{c['request_id']} — Suministros Andinos SAS",
        c["title"],
        f"Cliente: {c['customer_name']}",
        product_line,
        f"Estado: {c['status']}",
        f"Urgencia: {c['urgency']}",
    ]
    if c["date_label"]:
        lines.append(f"Recibida: {c['date_label']}")
    if reason_text:
        lines.extend(["Motivos de alerta:", reason_text])
    if c["summary"]:
        lines.extend([f"Resumen: {c['summary']}"])
    if c["sin_stock"]:
        lines.extend(["", "DISPONIBILIDAD ACTUAL", product_line])
        if c["stock_available"] is not None:
            lines.append(f"Disponible ahora en catálogo: {c['stock_available']} unidades")
        if c["missing"] is not None:
            lines.append(f"Faltante según esta lectura: {c['missing']} unidades")
        lines.append("El aviso no representa una reserva de unidades; confirmar disponibilidad antes de comprometer el pedido.")
    lines.extend(["", "Acción sugerida:", _action(c), ""])
    if c["original_message"]:
        lines.extend(["Mensaje del cliente:", c["original_message"], ""])
    lines.extend(["Notificación automática de Suministros Andinos SAS.",
                  f"Referencia de aviso: {c['notification_id']}" if c["notification_id"] else ""])
    plain = "\n".join(line for line in lines if line is not None)

    esc = lambda value: html.escape(_text(value), quote=True)
    reasons_html = "".join(
        f'<td style="padding:0 8px 8px 0;"><span style="display:inline-block;padding:7px 11px;'
        f'border-radius:999px;background:{_reason_color(label)};color:{_reason_text_color(label)};'
        f'font:600 12px Arial,Helvetica,sans-serif;">{esc(label)}</span></td>'
        for label in c["reason_labels"]
    )
    details = [f'<tr><td style="padding:9px 8px 9px 0;border-bottom:1px solid #e8edf2;color:#607080;font:13px Arial,Helvetica,sans-serif;width:34%;">Cliente</td>'
               f'<td style="padding:9px 0;border-bottom:1px solid #e8edf2;color:#10263b;font:600 14px Arial,Helvetica,sans-serif;">{esc(c["customer_name"])}</td></tr>',
               f'<tr><td style="padding:9px 0;border-bottom:1px solid #e8edf2;color:#607080;font:13px Arial,Helvetica,sans-serif;">Producto</td>'
               f'<td style="padding:9px 0;border-bottom:1px solid #e8edf2;color:#10263b;font:600 14px Arial,Helvetica,sans-serif;">{esc(c["product_name"])}</td></tr>']
    if c["quantity"] is not None:
        details.append(f'<tr><td style="padding:9px 0;border-bottom:1px solid #e8edf2;color:#607080;font:13px Arial,Helvetica,sans-serif;">Cantidad solicitada</td>'
                       f'<td style="padding:9px 0;border-bottom:1px solid #e8edf2;color:#10263b;font:600 14px Arial,Helvetica,sans-serif;">{c["quantity"]} unidades</td></tr>')
    details.extend([
        f'<tr><td style="padding:9px 0;border-bottom:1px solid #e8edf2;color:#607080;font:13px Arial,Helvetica,sans-serif;">Estado</td>'
        f'<td style="padding:9px 0;border-bottom:1px solid #e8edf2;color:#10263b;font:600 14px Arial,Helvetica,sans-serif;">{esc(c["status"])}</td></tr>',
        f'<tr><td style="padding:9px 0;border-bottom:1px solid #e8edf2;color:#607080;font:13px Arial,Helvetica,sans-serif;">Urgencia</td>'
        f'<td style="padding:9px 0;border-bottom:1px solid #e8edf2;color:#10263b;font:600 14px Arial,Helvetica,sans-serif;">{esc(c["urgency"])}</td></tr>',
    ])
    if c["date_label"]:
        details.append(f'<tr><td style="padding:9px 0;border-bottom:1px solid #e8edf2;color:#607080;font:13px Arial,Helvetica,sans-serif;">Recibida</td>'
                       f'<td style="padding:9px 0;border-bottom:1px solid #e8edf2;color:#10263b;font:14px Arial,Helvetica,sans-serif;">{esc(c["date_label"])}</td></tr>')

    stock_html = ""
    if c["sin_stock"]:
        stock_rows = ""
        stock_values = [
            ("Solicitado", f"{c['quantity']} unidades" if c["quantity"] is not None else "Cantidad no indicada"),
            ("Disponible ahora", f"{c['stock_available']} unidades" if c["stock_available"] is not None else "No verificado"),
            ("Faltante", f"{c['missing']} unidades" if c["missing"] is not None else "Por confirmar"),
        ]
        for label, value in stock_values:
            stock_rows += (f'<tr><td style="width:50%;padding:7px 0;color:#604500;font:13px Arial,Helvetica,sans-serif;">{label}</td>'
                           f'<td style="width:50%;padding:7px 0 7px 12px;text-align:right;color:#604500;font:700 14px Arial,Helvetica,sans-serif;">{esc(value)}</td></tr>')
        stock_html = (
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            'style="width:100%;margin-top:20px;background:#fff7df;border:1px solid #f3d98b;border-radius:10px;">'
            '<tr><td style="padding:16px 18px 4px;color:#604500;font:700 13px Arial,Helvetica,sans-serif;letter-spacing:.3px;">'
            'DISPONIBILIDAD ACTUAL</td></tr><tr><td style="padding:2px 18px 6px;">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100%;">{stock_rows}</table>'
            '</td></tr><tr><td style="padding:0 18px 16px;color:#705c25;font:12px/1.5 Arial,Helvetica,sans-serif;">'
            'La cifra refleja esta lectura del catálogo y no representa una reserva. Confirmar disponibilidad antes de comprometer el pedido.'
            '</td></tr></table>'
        )

    summary_html = (f'<div style="margin-top:18px;padding:14px 16px;border-left:3px solid #16a6a1;background:#f3f8f8;">'
                    f'<div style="margin-bottom:5px;color:#49606e;font:700 12px Arial,Helvetica,sans-serif;text-transform:uppercase;letter-spacing:.4px;">Resumen</div>'
                    f'<div style="color:#223748;font:14px/1.55 Arial,Helvetica,sans-serif;">{esc(c["summary"])}</div></div>') if c["summary"] else ""
    original_html = (f'<div style="margin-top:18px;"><div style="margin-bottom:7px;color:#607080;font:700 12px Arial,Helvetica,sans-serif;text-transform:uppercase;letter-spacing:.4px;">'
                     f'Mensaje del cliente</div><div style="padding:13px 15px;border:1px solid #e6ebef;border-radius:9px;background:#fafbfd;'
                     f'color:#334653;font:14px/1.55 Arial,Helvetica,sans-serif;white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word;">'
                     f'{esc(c["original_message"])}</div></div>') if c["original_message"] else ""

    html_body = f'''<!doctype html>
<html lang="es">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Solicitud #{esc(c['request_id'])}</title></head>
<body style="margin:0;padding:24px 12px;background:#f2f5f8;color:#10263b;font-family:Arial,Helvetica,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100%;border-collapse:collapse;background:#f2f5f8;">
    <tr><td align="center" style="padding:0;">
      <table role="presentation" width="640" cellpadding="0" cellspacing="0" style="width:100%;max-width:640px;border-collapse:separate;border-spacing:0;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 8px 28px rgba(16,38,59,.09);">
        <tr><td style="padding:22px 26px;background:#10263b;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100%;">
          <tr>
            <td width="48" valign="middle"><div style="width:42px;height:42px;line-height:42px;text-align:center;border-radius:11px;background:#16a6a1;color:#ffffff;font:bold 15px/42px Arial,Helvetica,sans-serif;">SA</div></td>
            <td valign="middle" style="padding-left:12px;color:#ffffff;"><div style="font:700 16px Arial,Helvetica,sans-serif;">Suministros Andinos</div><div style="padding-top:4px;color:#bed0dc;font:12px Arial,Helvetica,sans-serif;">Alerta de atención</div></td>
            <td valign="middle" style="padding-left:12px;text-align:right;color:#bed0dc;font:12px Arial,Helvetica,sans-serif;">Solicitud #{esc(c['request_id'])}</td>
          </tr></table>
        </td></tr>
        <tr><td style="padding:28px 30px 30px;">
          <div style="color:#10263b;font:700 23px/1.25 Arial,Helvetica,sans-serif;">{esc(c['title'])}</div>
          <div style="margin-top:8px;color:#687a88;font:14px Arial,Helvetica,sans-serif;">Requiere revisión del equipo de atención.</div>
          <table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:18px;"><tr>{reasons_html}</tr></table>
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100%;margin-top:12px;border-collapse:collapse;">{''.join(details)}</table>
          {stock_html}
          {summary_html}
          <div style="margin-top:20px;padding:16px 18px;border-radius:10px;background:#eef8f7;">
            <div style="color:#116f6c;font:700 12px Arial,Helvetica,sans-serif;text-transform:uppercase;letter-spacing:.4px;">Acción sugerida</div>
            <div style="padding-top:6px;color:#244c50;font:14px/1.5 Arial,Helvetica,sans-serif;">{esc(_action(c))}</div>
          </div>
          {original_html}
        </td></tr>
        <tr><td style="padding:16px 26px;background:#f8fafb;border-top:1px solid #e8edf2;color:#71808a;font:12px/1.5 Arial,Helvetica,sans-serif;">
          Notificación automática de Suministros Andinos SAS{f' · Aviso {esc(c["notification_id"])}' if c['notification_id'] else ''}
        </td></tr>
      </table>
      <div style="padding:14px 8px 0;color:#84919a;font:11px Arial,Helvetica,sans-serif;">Mensaje generado para revisión interna.</div>
    </td></tr>
  </table>
</body>
</html>'''
    return plain, html_body


def _action(context: dict) -> str:
    if context["sin_stock"]:
        return "Confirmar alternativas o disponibilidad con el cliente antes de comprometer el pedido."
    if context.get("urgency") == "Alta" or "Queja de cliente" in context.get("reason_labels", []):
        return "Revisar el caso y responder al cliente con prioridad."
    return "Revisar la solicitud y contactar al cliente si hace falta aclarar algún dato."


def _reason_color(label: str) -> str:
    if label == "Queja de cliente":
        return "#fde8e7"
    if label == "Urgencia alta":
        return "#fff0cc"
    return "#e5f2f2"


def _reason_text_color(label: str) -> str:
    if label == "Queja de cliente":
        return "#9b2c2c"
    if label == "Urgencia alta":
        return "#835600"
    return "#176d6b"
