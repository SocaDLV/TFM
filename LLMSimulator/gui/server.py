# -*- coding: utf-8 -*-
"""
HTTP Server and REST API for LLM-NoC Co-Simulation Workbench.
Uses Python's standard library ThreadingHTTPServer.
"""

import json
import os
import sys
import mimetypes
from urllib.parse import urlparse, parse_qs
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

from gui.sim_runner import runner_instance


class WorkbenchAPIHandler(BaseHTTPRequestHandler):
    """Handles REST API requests and serves static frontend assets."""

    def __init__(self, *args, **kwargs):
        self.gui_dir = Path(__file__).resolve().parent
        self.static_dir = self.gui_dir / "static"
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        # Silence default access logging to avoid terminal clutter while polling
        return

    def _send_json(self, status_code, payload):
        """Sends a JSON response with standard CORS and no-cache headers."""
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(data)

    def _send_error(self, status_code, message):
        self._send_json(status_code, {"success": False, "error": message})

    def do_OPTIONS(self):
        """Handle CORS pre-flight requests."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_HEAD(self):
        """Handle HEAD requests for static assets."""
        self._handle_get(send_body=False)

    def do_GET(self):
        """Routes GET requests to API or static files."""
        self._handle_get(send_body=True)

    def _handle_get(self, send_body=True):
        parsed = urlparse(self.path)
        path = parsed.path

        # REST API Routes
        if path == "/api/status":
            query = parse_qs(parsed.query)
            offset = 0
            if "offset" in query:
                try:
                    offset = int(query["offset"][0])
                except ValueError:
                    offset = 0

            status_data = runner_instance.get_status(offset=offset)
            data = json.dumps(status_data, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            if send_body:
                self.wfile.write(data)
            return

        # Static Assets Serving
        if path in ["/", "/index.html"]:
            file_path = self.static_dir / "index.html"
        elif path.startswith("/static/"):
            rel_path = path[len("/static/"):]
            file_path = self.static_dir / rel_path
        else:
            file_path = self.static_dir / path.lstrip("/")

        try:
            file_path = file_path.resolve()
            if not str(file_path).startswith(str(self.static_dir.resolve())):
                self._send_error(403, "Acceso denegado fuera de static/")
                return

            if not file_path.exists() or not file_path.is_file():
                self._send_error(404, f"Fichero no encontrado: {path}")
                return

            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type is None:
                if file_path.suffix == ".css":
                    mime_type = "text/css"
                elif file_path.suffix == ".js":
                    mime_type = "application/javascript"
                else:
                    mime_type = "application/octet-stream"

            file_size = file_path.stat().st_size
            self.send_response(200)
            self.send_header("Content-Type", f"{mime_type}; charset=utf-8" if "text" in mime_type or "javascript" in mime_type else mime_type)
            self.send_header("Content-Length", str(file_size))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()

            if send_body:
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())

        except Exception as e:
            self._send_error(500, f"Error al servir archivo estático: {e}")

    def do_POST(self):
        """Routes POST requests to API endpoints."""
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/run":
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self._send_error(400, "Cuerpo JSON vacío en solicitud POST")
                return

            try:
                body = self.rfile.read(content_length).decode("utf-8")
                params = json.loads(body)
            except Exception as e:
                self._send_error(400, f"JSON no válido en solicitud: {e}")
                return

            try:
                res = runner_instance.run(params)
                self._send_json(200, {"success": True, **res})
            except ValueError as ve:
                self._send_error(400, str(ve))
            except RuntimeError as re:
                self._send_error(409, str(re))
            except Exception as e:
                self._send_error(500, f"Error interno al iniciar simulación: {e}")
            return

        elif path == "/api/abort":
            try:
                res = runner_instance.abort()
                self._send_json(200, {"success": True, **res})
            except Exception as e:
                self._send_error(500, f"Error al abortar simulación: {e}")
            return

        else:
            self._send_error(404, f"Endpoint API no encontrado: {path}")


def create_server(host="0.0.0.0", port=8080):
    """Instantiates and returns the ThreadingHTTPServer."""
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, WorkbenchAPIHandler)
    return httpd
