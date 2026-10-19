#!/usr/bin/env python3
"""Build an offline, explanatory MP4 from existing real-run evidence JSON."""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
VIDEO_DIR = ROOT / "flujo" / "evidencias" / "video"
OUTPUT_VIDEO = VIDEO_DIR / "demostracion-anexo-b.mp4"
MANIFEST = VIDEO_DIR / "manifiesto.json"
WIDTH, HEIGHT = 1280, 720
FPS = 5
FOOTER = "Reproducción explicativa de trazas reales · No es captura de la interfaz n8n"

SOURCE_REAL = ROOT / "flujo" / "evidencias" / "real" / "flujo-real-20261019T202729Z-afcf5fa1.json"
SOURCE_CATALOGUE = VIDEO_DIR / "catalogo_escritorio_api_readonly.json"
SOURCE_CURRENT_API = VIDEO_DIR / "api_state_readonly_snapshot.json"
SOURCE_LATER_NOTIFS = ROOT / "flujo" / "evidencias" / "correo-html" / "notificaciones-20261019T213619+0000.json"

NAVY = "#10283E"
NAVY_LIGHT = "#183B56"
TEAL = "#11A6A3"
TEAL_DARK = "#087D7A"
INK = "#1B2C3B"
MUTED = "#536879"
PAPER = "#F3F6F8"
WHITE = "#FFFFFF"
LINE = "#D9E2E8"
GREEN = "#1F7958"
GREEN_BG = "#E4F3EC"
GOLD = "#8A5B00"
GOLD_BG = "#FFF1CF"
RED = "#9C3434"
RED_BG = "#FCE8E8"


@dataclass
class Slide:
    name: str
    image: Image.Image
    seconds: float


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as source:
        return json.load(source)


def utc_timestamp(value: str | None) -> str:
    if not value:
        return "hora no disponible"
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def find_font_file() -> Path | None:
    candidates = [
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/calibri.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    ]
    return next((path for path in candidates if path.is_file()), None)


def load_fonts() -> dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont]:
    font_file = find_font_file()
    if font_file is None:
        return {"small": ImageFont.load_default(), "body": ImageFont.load_default(), "large": ImageFont.load_default(), "title": ImageFont.load_default(), "bold": ImageFont.load_default()}
    return {
        "small": ImageFont.truetype(str(font_file), 17),
        "body": ImageFont.truetype(str(font_file), 22),
        "large": ImageFont.truetype(str(font_file), 27),
        "title": ImageFont.truetype(str(font_file), 38),
        "bold": ImageFont.truetype(str(font_file), 24, index=0),
    }


FONTS = load_fonts()


def bold_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_file = find_font_file()
    if font_file is None:
        return ImageFont.load_default()
    bold_candidates = [
        Path("C:/Windows/Fonts/segoeuib.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/calibrib.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
    ]
    bold_file = next((path for path in bold_candidates if path.is_file()), font_file)
    return ImageFont.truetype(str(bold_file), size)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, width: int) -> list[str]:
    words = str(text).split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if draw.textbbox((0, 0), candidate, font=font)[2] <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_wrapped(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font: ImageFont.ImageFont,
                 fill: str, width: int, line_gap: int = 7, max_lines: int | None = None) -> int:
    x, y = xy
    lines = wrap_text(draw, text, font, width)
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and draw.textbbox((0, 0), last + "…", font=font)[2] > width:
            last = last[:-1]
        lines[-1] = last.rstrip() + "…"
    line_height = draw.textbbox((0, 0), "Ágj", font=font)[3] + line_gap
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height
    return y


def rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str,
            outline: str | None = None, radius: int = 22, width: int = 2) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def base_slide(kicker: str, title: str, progress: int, total: int = 10) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, WIDTH, 12), fill=TEAL)
    draw.text((52, 32), kicker.upper(), font=FONTS["small"], fill=TEAL_DARK)
    draw.text((52, 60), title, font=FONTS["title"], fill=NAVY)
    # Progress indicator
    x0, x1, y = 1080, 1228, 48
    rounded(draw, (x0, y, x1, y + 10), LINE, radius=5, width=1)
    rounded(draw, (x0, y, x0 + int((x1 - x0) * progress / total), y + 10), TEAL, radius=5, width=1)
    draw.line((48, 672, WIDTH - 48, 672), fill=LINE, width=2)
    draw.text((50, 684), FOOTER, font=FONTS["small"], fill=MUTED)
    return image, draw


def pill(draw: ImageDraw.ImageDraw, x: int, y: int, label: str, fill: str, text_color: str, font: ImageFont.ImageFont | None = None) -> int:
    font = font or FONTS["small"]
    bbox = draw.textbbox((0, 0), label, font=font)
    w = bbox[2] + 28
    rounded(draw, (x, y, x + w, y + 38), fill, radius=18, width=1)
    draw.text((x + 14, y + 7), label, font=font, fill=text_color)
    return w


def card(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], title: str,
         fill: str = WHITE, accent: str = TEAL) -> None:
    rounded(draw, box, fill, outline=LINE, radius=20, width=2)
    draw.rectangle((box[0], box[1], box[0] + 8, box[3]), fill=accent)
    draw.text((box[0] + 28, box[1] + 20), title.upper(), font=FONTS["small"], fill=accent)


def kv(draw: ImageDraw.ImageDraw, x: int, y: int, label: str, value: str,
       width: int = 490, value_color: str = INK, font: ImageFont.ImageFont | None = None) -> int:
    font = font or FONTS["body"]
    draw.text((x, y), label, font=FONTS["small"], fill=MUTED)
    lines = wrap_text(draw, value, font, width - 170)
    line_height = draw.textbbox((0, 0), "Ágj", font=font)[3] + 4
    for i, line in enumerate(lines[:2]):
        draw.text((x + 170, y - 2 + i * line_height), line, font=font, fill=value_color)
    return max(42, len(lines[:2]) * line_height + 10)


def safe_message(value: str) -> str:
    # The source evidence includes client_email separately; only the message body is shown.
    return re.sub(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", "[correo omitido]", value, flags=re.I)


def validate_sources(real: dict[str, Any], catalogue: dict[str, Any], current_api: dict[str, Any], later: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    results = real.get("results", [])
    if len(results) != 5 or any(result.get("passed") is not True for result in results):
        raise ValueError("La fuente B1–B5 no contiene exactamente cinco casos aprobados.")
    for result in results:
        calls = result.get("n8n_execution", {}).get("provider_calls", [])
        if len(calls) != 1 or calls[0].get("http_status") != 200:
            raise ValueError(f"{result.get('case')} no muestra exactamente una llamada HTTP 200 al proveedor.")
    stock_result = catalogue.get("result", {})
    if stock_result.get("id") != 4 or stock_result.get("stock") != 3:
        raise ValueError("La instantánea de solo lectura del catálogo no coincide con el Escritorio en L, stock 3.")
    current_requests = current_api.get("requests", [])
    expected_request_ids = [61, 62, 63, 64]
    if [row.get("id") for row in current_requests] != expected_request_ids or any(row.get("http_status") != 200 for row in current_requests):
        raise ValueError("La instantánea GET actual no confirma solicitudes 61–64 con HTTP 200.")
    receipt = current_api.get("reception", {})
    if (receipt.get("http_status") != 200 or receipt.get("recepcion_id") != 7
            or receipt.get("estado") != "revision_manual" or receipt.get("solicitud_id") is not None
            or "cliente_desconocido" not in receipt.get("motivos_revision", [])):
        raise ValueError("La instantánea GET actual no confirma la recepción manual B5.")
    b4_current = current_requests[3]
    if b4_current.get("producto_id") != 4 or b4_current.get("cantidad") != 6 or not b4_current.get("sin_stock"):
        raise ValueError("La lectura GET actual no confirma B4 con cantidad 6 y sin_stock=true.")
    later_cases = later.get("cases", [])
    later_lookup = {case.get("case"): case for case in later_cases}
    for case_name, expected_request_id, expected_notification_id in (("B3", 67, 6), ("B4", 68, 7)):
        case = later_lookup.get(case_name)
        if not case or case.get("request", {}).get("id") != expected_request_id:
            raise ValueError(f"La evidencia posterior {case_name} no tiene el ID de solicitud esperado.")
        if case.get("webhook_result", {}).get("notificacion_id") != expected_notification_id:
            raise ValueError(f"La evidencia posterior {case_name} no tiene el ID de notificación esperado.")
        if case.get("smtp_acceptance") != "accepted_by_smtp":
            raise ValueError(f"La notificación posterior {case_name} no registra aceptación SMTP.")
    return results, int(stock_result["stock"])


def make_opening(real: dict[str, Any]) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), NAVY)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, WIDTH, 14), fill=TEAL)
    pill(draw, 68, 60, "ANEXO B · TRAZAS REALES · DATOS DE PRUEBA", TEAL, WHITE)
    draw.text((68, 140), "Automatización de solicitudes", font=FONTS["title"], fill=WHITE)
    draw.text((68, 192), "B1–B5 ejecutados con DeepSeek real · entradas de prueba", font=FONTS["large"], fill="#BBD1DF")
    rounded(draw, (68, 278, 1212, 455), NAVY_LIGHT, outline="#2A536E", radius=24, width=2)
    draw.text((108, 312), "5 / 5", font=bold_font(62), fill="#73E0D7")
    draw.text((340, 314), "casos procesados", font=FONTS["large"], fill=WHITE)
    draw.text((108, 397), "5 respuestas del proveedor · HTTP 200 · 1 intento por caso", font=FONTS["body"], fill="#E5EDF3")
    started = utc_timestamp(real.get("started_at_utc"))
    draw.text((68, 505), f"Corrida fuente UTC: {started} · workflow {real.get('workflow_id', 'solicitudes-ia-suministros-v1')}", font=FONTS["small"], fill="#BBD1DF")
    draw.text((68, 564), FOOTER, font=FONTS["small"], fill="#FFFFFF")
    draw.text((68, 616), "La narración visual se reconstruye desde el JSON de evidencia; no es una grabación.", font=FONTS["small"], fill="#BBD1DF")
    return image


def make_architecture() -> Image.Image:
    image, draw = base_slide("Recorrido", "Una solicitud atraviesa cuatro componentes", 2, total=11)
    boxes = [
        (70, 238, 305, 390, "Mensaje", "texto original", NAVY_LIGHT),
        (365, 238, 600, 390, "n8n", "webhook y ramas", TEAL_DARK),
        (660, 238, 895, 390, "DeepSeek", "extracción · 1 llamada", NAVY_LIGHT),
        (955, 238, 1190, 390, "API + SQLite", "validación y registro", TEAL_DARK),
    ]
    for x0, y0, x1, y1, title, subtitle, color in boxes:
        rounded(draw, (x0, y0, x1, y1), color, radius=22)
        draw.text((x0 + 22, y0 + 40), title, font=bold_font(27), fill=WHITE)
        draw_wrapped(draw, (x0 + 22, y0 + 84), subtitle, FONTS["small"], "#E3F1F2", x1 - x0 - 44, max_lines=3)
    for x in (318, 613, 908):
        draw.line((x, 314, x + 35, 314), fill=TEAL, width=6)
        draw.polygon([(x + 35, 304), (x + 50, 314), (x + 35, 324)], fill=TEAL)
    rounded(draw, (70, 434, 1190, 574), WHITE, outline=LINE, radius=18)
    draw.text((100, 457), "Regla visible", font=bold_font(23), fill=NAVY)
    draw_wrapped(draw, (100, 497), "Los casos B1–B4 generan una solicitud; B5 se conserva como recepción para revisión manual porque el cliente no está registrado.", FONTS["body"], INK, 1040, max_lines=2)
    return image


def classify_case(result: dict[str, Any], stock: int) -> dict[str, Any]:
    webhook = result.get("webhook", {})
    body = webhook.get("body", {})
    classified = body.get("clasificacion") or {}
    solicitation = (result.get("solicitud_api") or {}).get("body") or {}
    checks = result.get("checks", {})
    return {
        "label": result.get("case", "").split("_", 1)[0],
        "message": safe_message(result.get("request", {}).get("mensaje", "")),
        "http": webhook.get("http_status"),
        "receipt_id": body.get("recepcion_id"),
        "request_id": body.get("solicitud_id"),
        "classification": classified,
        "product_id": solicitation.get("producto_id"),
        "client_id": solicitation.get("cliente_id"),
        "review": body.get("requiere_revision", False),
        "review_reasons": body.get("motivos_revision", []),
        "no_stock": body.get("sin_stock", False),
        "stock_verified": body.get("stock_verificado", False),
        "alerts": body.get("motivos_alerta", []),
        "notification_id": body.get("notificacion_id"),
        "notification_status": body.get("notificacion_estado", "pendiente"),
        "check_count": sum(value is True for value in checks.values()),
        "check_total": len(checks),
        "passed": result.get("passed") is True,
        "stock": stock if body.get("sin_stock") is True else None,
    }


def render_case(case: dict[str, Any], case_index: int, stock: int) -> Image.Image:
    titles = {
        "B1": "Pedido urgente · resmas de papel carta",
        "B2": "Consulta · diademas con micrófono",
        "B3": "Queja · tóner dañado",
        "B4": "Pedido · escritorio en L y stock",
        "B5": "Cliente desconocido · revisión manual",
    }
    image, draw = base_slide(f"Caso {case_index} de 5 · {case['label']}", titles.get(case["label"], case["label"]), 2 + case_index, total=11)

    # Original message panel
    card(draw, (52, 124, 1228, 262), "Mensaje recibido", fill=WHITE, accent=TEAL)
    draw_wrapped(draw, (82, 169), f"“{case['message']}”", FONTS["body"], INK, 1094, line_gap=8, max_lines=3)

    # Classification panel
    card(draw, (52, 286, 602, 532), "Clasificación registrada", fill=WHITE, accent=TEAL_DARK)
    cl = case["classification"]
    items = [
        ("Tipo", cl.get("tipo") or "—"),
        ("Producto", cl.get("producto") or "—"),
        ("Cantidad", "No especificada" if cl.get("cantidad") is None else str(cl.get("cantidad"))),
        ("Urgencia", cl.get("urgencia") or "—"),
    ]
    y = 337
    for label, value in items:
        y += kv(draw, 82, y, label, str(value), width=470, font=FONTS["body"])

    # Persisted IDs + route outcome
    card(draw, (628, 286, 1228, 532), "Ruta y persistencia", fill=WHITE, accent=TEAL_DARK)
    route_lines = [
        ("Webhook", f"HTTP {case['http']}"),
        ("Recepción", f"ID {case['receipt_id']} · persistida"),
        ("Solicitud", "No creada" if case["request_id"] is None else f"ID {case['request_id']} · persistida"),
        ("Revisión", "Sí · " + ", ".join(case["review_reasons"]) if case["review"] else "No requerida"),
    ]
    y = 337
    for label, value in route_lines:
        y += kv(draw, 658, y, label, value, width=520, font=FONTS["body"])

    # Bottom result strip
    rounded(draw, (52, 552, 1228, 641), NAVY, radius=18)
    if case["alerts"]:
        alert_text = " · ".join(case["alerts"])
        tag = f"Alerta: {alert_text}"
    elif case["review"]:
        tag = "Sin solicitud ficticia"
    else:
        tag = "Sin alerta"
    draw.text((78, 574), f"Validaciones: {case['check_count']}/{case['check_total']}  ·  {tag}", font=bold_font(21), fill=WHITE)
    if case["label"] == "B4":
        detail = f"Cantidad solicitada 6  ·  stock actual {stock}  ·  sin_stock=true  ·  notificación {case['notification_id']} inicialmente pendiente"
    elif case["notification_id"] is not None:
        detail = f"Outbox {case['notification_id']} inicialmente pendiente en esta corrida"
    elif case["review"]:
        detail = "HTTP 202 · motivo cliente_desconocido · no se creó solicitud"
    else:
        detail = "Una respuesta DeepSeek HTTP 200 · una llamada · clasificación persistida"
    draw.text((78, 610), detail, font=FONTS["small"], fill="#C7D9E4")
    return image


def render_later_notifications(later: dict[str, Any]) -> Image.Image:
    image, draw = base_slide("Ejecución posterior · separada de B1–B5", "Prueba de notificaciones con plantillas HTML", 9, total=11)
    cases = later.get("cases", [])
    data = []
    for case in cases:
        data.append({
            "label": case.get("case"),
            "request": (case.get("request") or {}).get("id"),
            "notification": (case.get("webhook_result") or {}).get("notificacion_id"),
            "accepted": case.get("smtp_acceptance") == "accepted_by_smtp",
        })
    cards = [
        ("B3 · Queja", data[0] if data else {}, 70),
        ("B4 · Stock insuficiente", data[1] if len(data) > 1 else {}, 650),
    ]
    for title, item, x in cards:
        rounded(draw, (x, 180, x + 560, 400), WHITE, outline=LINE, radius=22, width=2)
        draw.text((x + 32, 210), title, font=bold_font(27), fill=NAVY)
        draw.text((x + 32, 268), f"Solicitud #{item.get('request', '—')}", font=FONTS["large"], fill=INK)
        draw.text((x + 32, 315), f"Notificación #{item.get('notification', '—')}", font=FONTS["body"], fill=INK)
        pill(draw, x + 32, 350, "SMTP aceptó" if item.get("accepted") else "Sin aceptación", GREEN_BG if item.get("accepted") else GOLD_BG, GREEN if item.get("accepted") else GOLD)
    rounded(draw, (92, 434, 1188, 580), GOLD_BG, outline="#E8D39D", radius=20)
    draw_wrapped(draw, (120, 465), "Ejecución posterior a la corrida B1–B5: solicitudes 67 y 68, notificaciones 6 y 7. El artefacto registra aceptación SMTP; esta placa no afirma entrega a bandeja. No se muestran destinatarios, Message-ID ni credenciales.", FONTS["body"], INK, 1030, max_lines=4)
    return image


def render_current_api_snapshot(snapshot: dict[str, Any], stock: int) -> Image.Image:
    image, draw = base_slide("Lecturas GET · solo lectura", "La API conserva los resultados observados", 8, total=11)
    draw.text((68, 132), f"Consulta actual registrada: {snapshot.get('captured_at_utc', '—')} · cinco respuestas HTTP 200", font=FONTS["body"], fill=MUTED)

    x_left, x_right = 68, 1212
    rounded(draw, (x_left, 186, x_right, 525), WHITE, outline=LINE, radius=20, width=2)
    # Header row
    draw.rectangle((x_left + 1, 187, x_right - 1, 237), fill=NAVY_LIGHT)
    draw.text((92, 200), "CASO / GET", font=FONTS["small"], fill=WHITE)
    draw.text((470, 200), "REGISTRO ACTUAL", font=FONTS["small"], fill=WHITE)
    rows = snapshot.get("requests", [])
    row_specs = [
        ("B1", "GET /solicitudes/61 · HTTP 200", "pedido · 10 resmas · urgencia alta"),
        ("B2", "GET /solicitudes/62 · HTTP 200", "consulta · diadema con micrófono"),
        ("B3", "GET /solicitudes/63 · HTTP 200", "queja · tóner · urgencia alta"),
        ("B4", "GET /solicitudes/64 · HTTP 200", f"pedido · cantidad 6 · stock {stock} · sin_stock=true"),
    ]
    y = 246
    for row, (label, endpoint, detail) in zip(rows, row_specs):
        if y > 246:
            draw.line((x_left + 24, y, x_right - 24, y), fill=LINE, width=1)
        draw.text((92, y + 12), label, font=bold_font(21), fill=TEAL_DARK)
        draw.text((165, y + 12), endpoint, font=FONTS["small"], fill=INK)
        draw.text((470, y + 10), detail, font=FONTS["body"], fill=INK)
        y += 62

    receipt = snapshot.get("reception", {})
    rounded(draw, (68, 548, 1212, 642), GOLD_BG, outline="#E8D39D", radius=18)
    draw.text((94, 566), "B5", font=bold_font(21), fill=GOLD)
    draw.text((165, 566), f"GET /recepciones/7 · HTTP {receipt.get('http_status')}", font=FONTS["small"], fill=INK)
    draw.text((480, 566), "revision_manual · cliente_desconocido · sin solicitud", font=FONTS["small"], fill=INK)
    # Clarify the provenance of this independent current-state check.
    draw.text((94, 608), "solicitud_id=null · GET confirma persistencia actual, no repite la llamada al modelo.", font=FONTS["small"], fill=MUTED)
    return image


def make_limits() -> Image.Image:
    image, draw = base_slide("Alcance", "Qué muestra y qué no afirma este video", 10, total=11)
    sections = [
        ("SÍ", "Cinco trazas observadas en la ejecución real con n8n, DeepSeek y la API; estados, identificadores y resultados extraídos de los JSON de evidencia.", GREEN_BG, GREEN),
        ("NO", "No es una captura ni un screencast de n8n. No recrea clics, no hace nuevas solicitudes y no demuestra que la interfaz se vea así.", RED_BG, RED),
        ("TAMPOCO", "No es una evaluación general de precisión del modelo. Es una corrida concreta de cinco casos; el B5 quedó para revisión manual.", GOLD_BG, GOLD),
    ]
    y = 155
    for tag, text, fill, color in sections:
        rounded(draw, (76, y, 1204, y + 130), fill, radius=22)
        pill(draw, 104, y + 24, tag, color, WHITE)
        draw_wrapped(draw, (300, y + 29), text, FONTS["body"], INK, 840, max_lines=3)
        y += 150
    return image


def make_closing() -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), NAVY)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, WIDTH, 14), fill=TEAL)
    draw.text((68, 98), "Resultados observados", font=FONTS["title"], fill=WHITE)
    metrics = [("4", "solicitudes registradas"), ("1", "recepción para revisión manual"), ("5/5", "casos aprobados")]
    x = 68
    for number, label in metrics:
        rounded(draw, (x, 200, x + 340, 400), NAVY_LIGHT, outline="#2A536E", radius=24, width=2)
        draw.text((x + 28, 230), number, font=bold_font(56), fill="#73E0D7")
        draw_wrapped(draw, (x + 28, 313), label, FONTS["body"], WHITE, 280, max_lines=2)
        x += 365
    draw.text((68, 474), "B4: pedido 6 · stock 3 · alerta de stock insuficiente", font=FONTS["large"], fill="#D5E4EC")
    draw.text((68, 574), FOOTER, font=FONTS["small"], fill=WHITE)
    draw.text((68, 624), "Fuente: flujo/evidencias/real/flujo-real-20261019T202729Z-afcf5fa1.json", font=FONTS["small"], fill="#BBD1DF")
    return image


def build_slides(real: dict[str, Any], catalogue: dict[str, Any], current_api: dict[str, Any], later: dict[str, Any]) -> list[Slide]:
    results, stock = validate_sources(real, catalogue, current_api, later)
    slides = [
        Slide("slide-01-apertura", make_opening(real), 8),
        Slide("slide-02-arquitectura", make_architecture(), 13),
    ]
    for index, result in enumerate(results, start=1):
        case = classify_case(result, stock)
        slides.append(Slide(f"slide-{index + 2:02d}-{case['label'].lower()}", render_case(case, index, stock), 17 if case["label"] != "B4" else 20))
    slides.extend([
        Slide("slide-08-verificacion-api-actual", render_current_api_snapshot(current_api, stock), 12),
        Slide("slide-09-notificaciones-html-posteriores", render_later_notifications(later), 14),
        Slide("slide-10-alcance-y-limitaciones", make_limits(), 14),
        Slide("slide-11-cierre", make_closing(), 7),
    ])
    return slides


def write_video(slides: list[Slide]) -> tuple[int, float]:
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    writer = imageio_ffmpeg.write_frames(
        str(OUTPUT_VIDEO),
        (WIDTH, HEIGHT),
        fps=FPS,
        codec="libx264",
        pix_fmt_in="rgb24",
        pix_fmt_out="yuv420p",
        quality=None,
        macro_block_size=1,
        ffmpeg_log_level="warning",
        output_params=["-crf", "25", "-preset", "medium", "-movflags", "+faststart"],
    )
    writer.send(None)
    try:
        for slide in slides:
            frame = slide.image.convert("RGB").tobytes()
            for _ in range(round(slide.seconds * FPS)):
                writer.send(frame)
    finally:
        writer.close()
    frame_count, duration = imageio_ffmpeg.count_frames_and_secs(str(OUTPUT_VIDEO))
    return frame_count, duration


def main() -> int:
    required = (SOURCE_REAL, SOURCE_CATALOGUE, SOURCE_CURRENT_API, SOURCE_LATER_NOTIFS)
    for path in required:
        if not path.is_file():
            print(f"Fuente requerida no encontrada: {path.relative_to(ROOT)}", file=sys.stderr)
            return 2

    try:
        real = load_json(SOURCE_REAL)
        catalogue = load_json(SOURCE_CATALOGUE)
        current_api = load_json(SOURCE_CURRENT_API)
        later = load_json(SOURCE_LATER_NOTIFS)
        slides = build_slides(real, catalogue, current_api, later)
        expected_pngs = {f"{slide.name}.png" for slide in slides}
        for stale_png in VIDEO_DIR.glob("slide-*.png"):
            if stale_png.name not in expected_pngs:
                stale_png.unlink()
        for slide in slides:
            slide.image.save(VIDEO_DIR / f"{slide.name}.png", format="PNG", optimize=True)
        frame_count, duration = write_video(slides)
        if duration >= 300 or len(slides) != 11:
            raise RuntimeError(f"Validación final fuera de rango: duración={duration:.2f}s, slides={len(slides)}")

        manifest = {
            "title": "Anexo B — explicación visual de trazas reales",
            "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "method": "PIL dibuja placas estáticas; imageio_ffmpeg/libx264 codifica MP4 H.264. Sin navegador y sin captura de interfaz.",
            "notice": FOOTER,
            "video": {
                "path": OUTPUT_VIDEO.relative_to(ROOT).as_posix(),
                "sha256": sha256(OUTPUT_VIDEO),
                "duration_seconds": round(duration, 3),
                "frame_count": frame_count,
                "fps": FPS,
                "resolution": [WIDTH, HEIGHT],
                "codec": "H.264/libx264",
                "crf": 25,
                "size_bytes": OUTPUT_VIDEO.stat().st_size,
            },
            "inputs": {
                path.relative_to(ROOT).as_posix(): {"sha256": sha256(path)} for path in required
            },
            "run_source": {
                "started_at_source": real.get("started_at_utc"),
                "started_at_utc": utc_timestamp(real.get("started_at_utc")),
                "finished_at_source": real.get("finished_at_utc"),
                "finished_at_utc": utc_timestamp(real.get("finished_at_utc")),
                "passed": real.get("passed"),
                "total_planned": real.get("total_planned"),
                "workflow_sha256": real.get("workflow_sha256"),
                "cases": [
                    {
                        "case": result.get("case"),
                        "http_status": result.get("webhook", {}).get("http_status"),
                        "receipt_id": result.get("webhook", {}).get("body", {}).get("recepcion_id"),
                        "request_id": result.get("webhook", {}).get("body", {}).get("solicitud_id"),
                        "passed": result.get("passed"),
                    }
                    for result in real.get("results", [])
                ],
            },
            "readonly_stock_snapshot": catalogue,
            "current_api_readonly_snapshot": current_api,
            "later_email_run": {
                "source": SOURCE_LATER_NOTIFS.relative_to(ROOT).as_posix(),
                "cases": [
                    {
                        "case": item.get("case"),
                        "request_id": (item.get("request") or {}).get("id"),
                        "notification_id": (item.get("webhook_result") or {}).get("notificacion_id"),
                        "smtp_acceptance": item.get("smtp_acceptance"),
                    }
                    for item in later.get("cases", [])
                ],
                "note": "Ejecución posterior y separada de B1–B5; aceptación SMTP no se presenta como confirmación de llegada.",
            },
            "slides": [
                {"path": f"flujo/evidencias/video/{slide.name}.png", "seconds": slide.seconds}
                for slide in slides
            ],
            "privacy": "No se incluyen direcciones de correo, headers, claves, tokens, Message-ID ni variables del entorno.",
            "limitations": [
                "Reproducción explicativa basada en registros existentes; no es un screencast ni una captura de n8n.",
                "Las trazas B1–B5 son una corrida concreta con entradas de prueba, no una evaluación general del modelo.",
                "La ejecución HTML posterior se identifica separadamente de la corrida B1–B5.",
            ],
        }
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception as exc:
        print(f"No se pudo crear la evidencia de video: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({
        "video": OUTPUT_VIDEO.relative_to(ROOT).as_posix(),
        "manifest": MANIFEST.relative_to(ROOT).as_posix(),
        "duration_seconds": round(duration, 3),
        "resolution": f"{WIDTH}x{HEIGHT}",
        "fps": FPS,
        "frames": frame_count,
        "size_bytes": OUTPUT_VIDEO.stat().st_size,
        "slides": len(slides),
        "cases": [result.get("case") for result in real.get("results", [])],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
