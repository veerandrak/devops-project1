"""Small, dependency-free health/metrics service for an SRE portfolio lab."""
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STARTED = time.monotonic()
LOCK = threading.Lock()
REQUESTS = 0


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global REQUESTS
        path = self.path.split("?", 1)[0]
        with LOCK:
            REQUESTS += 1
            count = REQUESTS
        code, content_type = 200, "application/json"
        if path in ("/healthz", "/readyz"):
            body = json.dumps({"status": "ok"}).encode()
        elif path == "/":
            body = json.dumps({"service": "platform-demo", "version": os.getenv("APP_VERSION", "local")}).encode()
        elif path == "/metrics":
            content_type = "text/plain; version=0.0.4"
            body = (
                "# HELP demo_http_requests_total Total GET requests including probes.\n"
                "# TYPE demo_http_requests_total counter\n"
                f"demo_http_requests_total {count}\n"
                "# HELP demo_uptime_seconds Process uptime in seconds.\n"
                "# TYPE demo_uptime_seconds gauge\n"
                f"demo_uptime_seconds {time.monotonic() - STARTED:.3f}\n"
            ).encode()
        else:
            code, body = 404, b'{"error":"not found"}'
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(json.dumps({"event": "http", "message": fmt % args}), flush=True)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", int(os.getenv("PORT", "8080"))), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
