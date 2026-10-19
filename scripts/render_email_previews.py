#!/usr/bin/env python3
"""Render email-template HTML to static PNGs for offline visual review."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import fitz
from PIL import Image
from weasyprint import CSS, HTML


PAGE_HEIGHT_CSS_PX = 4096
BOTTOM_PADDING_CSS_PX = 28


def safe_stem(path: Path) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "-", path.stem).strip("-").lower()


def content_bottom_css_px(page: object) -> float:
    """Find the last laid-out HTML element, excluding the full-page root boxes."""
    root = getattr(page, "_page_box", None)
    if root is None:
        return 0.0

    bottoms: list[float] = []
    for box in root.descendants():
        tag = getattr(box, "element_tag", None)
        if not tag or tag in {"html", "body"}:
            continue
        y = getattr(box, "position_y", None)
        height = getattr(box, "height", None)
        if y is not None and height is not None and height > 0:
            bottoms.append(float(y + height))
    return max(bottoms, default=0.0)


def render_one(source: Path, output_dir: Path, width: int) -> dict[str, object]:
    css = f"""
        @page {{ size: {width}px {PAGE_HEIGHT_CSS_PX}px; margin: 0; }}
        html {{ width: {width}px !important; min-width: {width}px !important; }}
        body {{ margin: 0 !important; min-width: 0 !important; max-width: none !important; }}
    """
    html = HTML(filename=str(source), base_url=str(source.parent), media_type="screen")
    document = html.render(stylesheets=[CSS(string=css)])
    if len(document.pages) != 1:
        raise RuntimeError(
            f"{source.name} desbordó la página de {PAGE_HEIGHT_CSS_PX}px a {width}px "
            f"(páginas generadas: {len(document.pages)})."
        )

    bottom = content_bottom_css_px(document.pages[0])
    if bottom <= 0 or bottom > PAGE_HEIGHT_CSS_PX:
        raise RuntimeError(f"No se pudo determinar el alto del contenido de {source.name}.")
    height = min(PAGE_HEIGHT_CSS_PX, math.ceil(bottom + BOTTOM_PADDING_CSS_PX))

    # PDF is an intermediate rasterization stage only; the retained evidence is PNG.
    pdf_bytes = document.write_pdf()
    pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = pdf[0]
    clip = fitz.Rect(0, 0, width * 0.75, height * 0.75)
    pixmap = page.get_pixmap(matrix=fitz.Matrix(4 / 3, 4 / 3), clip=clip, alpha=False)
    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)

    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{safe_stem(source)}-{width}px.png"
    image.save(target, format="PNG", optimize=True)
    return {"source": source.name, "viewport_width": width, "png": target.name, "size": list(image.size)}


def parse_widths(value: str) -> list[int]:
    try:
        widths = [int(part.strip()) for part in value.split(",") if part.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use widths in pixels separated by commas.") from exc
    if not widths or any(width < 240 or width > 1600 for width in widths):
        raise argparse.ArgumentTypeError("Viewport widths must be between 240 and 1600 pixels.")
    return widths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path, help="Directory containing HTML previews")
    parser.add_argument("output_dir", type=Path, help="Directory where PNGs will be written")
    parser.add_argument("--widths", type=parse_widths, default=parse_widths("680,640,390,360"))
    args = parser.parse_args()

    if not args.input_dir.is_dir():
        parser.error(f"Input directory not found: {args.input_dir}")
    sources = sorted(args.input_dir.glob("*.html"))
    if not sources:
        parser.error(f"No HTML previews found in {args.input_dir}")

    try:
        results = [render_one(source, args.output_dir, width) for source in sources for width in args.widths]
    except Exception as exc:  # Report one actionable error without dumping HTML or user data.
        print(f"Preview render failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"renderer": "WeasyPrint->PDF->PyMuPDF/PNG", "images": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
