"""Disposable loopback backend. No remote dependencies or credentials."""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_error(404)
            return
        ready = os.environ.get("DEMO_UPSTREAM") == "mock://ready"
        body = json.dumps(
            {
                "status": "ok" if ready else "unhealthy",
                "reason": "ready" if ready else "missing_demo_upstream",
            }
        ).encode()
        self.send_response(200 if ready else 503)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(json.dumps({"port": server.server_address[1]}), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
