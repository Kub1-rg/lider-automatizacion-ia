"""OpenAI-compatible deterministic provider double for isolated Compose integration."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
import threading
import time


COUNTS = {}
LOCK = threading.Lock()


def message_from_request(body):
    messages = body.get("messages") or []
    text = "\n".join(str(item.get("content", "")) for item in messages if isinstance(item, dict))
    match = re.search(r"(?:Mensaje del cliente|Mensaje original):\s*([\s\S]*?)\s*$", text, re.IGNORECASE)
    return (match.group(1).strip() if match else text[-8000:]).strip()


def classification(message):
    lower = message.casefold()
    if "fixture_multiproduct" in lower:
        return {"tipo": "pedido", "producto": "resma papel carta", "cantidad": 2, "urgencia": "baja", "resumen": "Solicita resmas de papel carta y mouse inalámbricos."}
    if "fixture_unknown_product" in lower:
        return {"tipo": "consulta", "producto": "impresora láser industrial", "cantidad": None, "urgencia": "baja", "resumen": "Consulta por una impresora láser industrial."}
    if "10 resmas" in lower:
        return {"tipo": "pedido", "producto": "papel carta", "cantidad": 10, "urgencia": "alta", "resumen": "Solicita 10 resmas de papel carta con urgencia."}
    if "diademas" in lower:
        return {"tipo": "consulta", "producto": "diademas con micrófono", "cantidad": None, "urgencia": "baja", "resumen": "Consulta por diademas con micrófono, precio y entrega."}
    if "tóner" in lower or "toner" in lower:
        return {"tipo": "queja", "producto": "tóner", "cantidad": None, "urgencia": "alta", "resumen": "Reporta que el tóner llegó dañado y pide respuesta."}
    if "escritorios en l" in lower:
        return {"tipo": "pedido", "producto": "escritorios en L", "cantidad": 6, "urgencia": "media", "resumen": "Solicita seis escritorios en L para una nueva oficina."}
    if "mouse" in lower or "ratón" in lower or "raton" in lower:
        return {"tipo": "consulta", "producto": "mouse inalámbrico", "cantidad": None, "urgencia": "baja", "resumen": "Consulta por mouse inalámbricos y envíos."}
    if "fixture_retry_invalid_then_valid" in lower:
        return {"tipo": "consulta", "producto": None, "cantidad": None, "urgencia": "baja", "resumen": "Prueba de segundo intento del proveedor."}
    return {"tipo": "consulta", "producto": None, "cantidad": None, "urgencia": "baja", "resumen": "Consulta de prueba para la integración técnica."}


class Handler(BaseHTTPRequestHandler):
    server_version = "FixtureLLM/1.0"

    def log_message(self, _format, *_args):
        return

    def _send(self, status, value):
        data = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.rstrip("/") in {"/health", "/healthz"}:
            return self._send(200, {"status": "ok", "fixture": True})
        if self.path.rstrip("/") == "/stats":
            with LOCK:
                counts = dict(COUNTS)
            return self._send(200, {"fixture": True, "call_counts": counts})
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path.rstrip("/") == "/reset":
            if self.headers.get("Authorization") != "Bearer test-double-only-not-a-real-key":
                return self._send(401, {"error": {"message": "Fixture reset requires its explicit test-only token."}})
            with LOCK:
                COUNTS.clear()
            return self._send(200, {"status": "reset", "fixture": True})
        if not self.path.endswith("/chat/completions"):
            return self._send(404, {"error": "expected OpenAI-compatible chat completions path"})
        if self.headers.get("Authorization") != "Bearer test-double-only-not-a-real-key":
            return self._send(401, {"error": {"message": "Fixture requires its explicit test-only token."}})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        except Exception:
            return self._send(400, {"error": {"message": "invalid JSON"}})
        message = message_from_request(body)
        key = message.casefold()
        with LOCK:
            COUNTS[key] = COUNTS.get(key, 0) + 1
            call_count = COUNTS[key]
        if "fixture_http_401" in key:
            return self._send(401, {"error": {"message": "synthetic unauthorized error"}})
        if "fixture_http_503" in key:
            return self._send(503, {"error": {"message": "synthetic upstream unavailable"}})
        if "fixture_timeout" in key:
            time.sleep(1.5)
            self.close_connection = True
            return
        if "fixture_schema_invalid_then_valid" in key and call_count == 1:
            value = classification(message)
            value["tipo"] = "solicitud_desconocida"
            content = json.dumps(value, ensure_ascii=False)
        elif "fixture_always_invalid" in key or ("fixture_retry_invalid_then_valid" in key and call_count == 1):
            content = "{invalid-json"
        else:
            content = json.dumps(classification(message), ensure_ascii=False)
        return self._send(200, {
            "id": f"fixture-{call_count}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": body.get("model", "fixture-classifier"),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        })


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8099), Handler).serve_forever()

