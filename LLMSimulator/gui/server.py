# -*- coding: utf-8 -*-
"""
HTTP Server and REST API for LLM-NoC Co-Simulation Workbench.
Uses Python's standard library ThreadingHTTPServer.
Handles simulation lifecycle, live status polling, and Phase 2 on-the-fly
analysis endpoints (summary KPIs, GPU chronogram, packet tracking, save/discard).
"""

import json
import os
import sys
import shutil
import mimetypes
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

from gui.sim_runner import runner_instance
from gui.trace_parser import (
    get_simulation_summary,
    get_chronogram_data,
    get_packet_tracking_data,
    get_packets_in_time_window
)
from gui.analysis_gui import list_all_simulations, compare_simulations


class WorkbenchAPIHandler(BaseHTTPRequestHandler):
    """Handles REST API requests and serves static frontend assets."""

    def __init__(self, *args, **kwargs):
        self.gui_dir = Path(__file__).resolve().parent
        self.base_dir = self.gui_dir.parent
        self.static_dir = self.gui_dir / "static"
        self.staging_root = self.base_dir / "build" / "tmp_staging"
        self.results_root = self.base_dir / "build" / "results"
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

    def _resolve_simulation_dir(self, source, folder_name):
        """Resolves the physical directory for a simulation in staging or results."""
        if source == "staging":
            if not self.staging_root.exists():
                return None
            if not folder_name:
                subdirs = [p for p in self.staging_root.iterdir() if p.is_dir()]
                return subdirs[0] if subdirs else None
            target = self.staging_root / folder_name
            return target if target.exists() else None
        elif source == "saved":
            if not self.results_root.exists() or not folder_name:
                return None
            target = self.results_root / folder_name
            return target if target.exists() else None
        else:
            # Auto-detect: check staging first, then results
            if self.staging_root.exists():
                if folder_name and (self.staging_root / folder_name).exists():
                    return self.staging_root / folder_name
                subdirs = [p for p in self.staging_root.iterdir() if p.is_dir()]
                if subdirs and not folder_name:
                    return subdirs[0]

            if self.results_root.exists() and folder_name:
                target = self.results_root / folder_name
                if target.exists():
                    return target
            return None

    def _handle_get(self, send_body=True):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # ---------------------------------------------------------------------
        # REST API Routes: Phase 1
        # ---------------------------------------------------------------------
        if path == "/api/status":
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

        # ---------------------------------------------------------------------
        # REST API Routes: Phase 2 (Results & Timelines)
        # ---------------------------------------------------------------------
        if path == "/api/results/active":
            has_active = False
            folder_name = None
            staging_path = None
            if self.staging_root.exists():
                subdirs = [p for p in self.staging_root.iterdir() if p.is_dir()]
                if subdirs:
                    has_active = True
                    folder_name = subdirs[0].name
                    staging_path = str(subdirs[0])

            self._send_json(200, {
                "active": has_active,
                "has_active": has_active,
                "source": "staging" if has_active else None,
                "status": "unsaved" if has_active else "none",
                "folder": folder_name,
                "folder_name": folder_name,
                "staging_path": staging_path
            })
            return

        if path == "/api/results/summary":
            source = query.get("source", ["staging"])[0]
            folder_name = query.get("folder", [None])[0]
            iteration = query.get("iteration", ["last"])[0]
            target_dir = self._resolve_simulation_dir(source, folder_name)

            if not target_dir:
                self._send_error(404, f"Simulación no encontrada en {source}: {folder_name or '(activa)'}")
                return

            try:
                summary = get_simulation_summary(target_dir, iteration=iteration)
                self._send_json(200, {"success": True, "source": source, **summary})
            except Exception as e:
                self._send_error(500, f"Error al generar resumen de simulación: {e}")
            return

        if path == "/api/results/chronogram":
            source = query.get("source", ["staging"])[0]
            folder_name = query.get("folder", [None])[0]
            iteration = query.get("iteration", ["last"])[0]
            target_dir = self._resolve_simulation_dir(source, folder_name)

            if not target_dir:
                self._send_error(404, f"Simulación no encontrada en {source}: {folder_name or '(activa)'}")
                return

            try:
                chrono_data = get_chronogram_data(target_dir, iteration=iteration)
                self._send_json(200, {"success": True, "source": source, "folder": target_dir.name, **chrono_data})
            except Exception as e:
                self._send_error(500, f"Error al generar cronograma de simulación: {e}")
            return

        if path == "/api/results/packets":
            source = query.get("source", ["staging"])[0]
            folder_name = query.get("folder", [None])[0]
            iteration = query.get("iteration", ["last"])[0]
            target_dir = self._resolve_simulation_dir(source, folder_name)

            if not target_dir:
                self._send_error(404, f"Simulación no encontrada en {source}: {folder_name or '(activa)'}")
                return

            try:
                offset = int(query.get("offset", [0])[0])
            except ValueError:
                offset = 0

            try:
                limit = int(query.get("limit", [150])[0])
            except ValueError:
                limit = 150

            regime = query.get("regime", ["custom"])[0]

            try:
                packet_data = get_packet_tracking_data(target_dir, offset=offset, limit=limit, regime=regime, iteration=iteration)
                self._send_json(200, {"success": True, "source": source, "folder": target_dir.name, **packet_data})
            except Exception as e:
                self._send_error(500, f"Error al parsear seguimiento de paquetes: {e}")
            return

        if path == "/api/results/packets_window":
            source = query.get("source", ["staging"])[0]
            folder_name = query.get("folder", [None])[0]
            target_dir = self._resolve_simulation_dir(source, folder_name)

            if not target_dir:
                self._send_error(404, f"Simulación no encontrada en {source}: {folder_name or '(activa)'}")
                return

            try:
                start_ns = float(query.get("start_ns", [0.0])[0])
            except ValueError:
                start_ns = 0.0

            try:
                end_ns = float(query.get("end_ns", [20000.0])[0])
            except ValueError:
                end_ns = 20000.0

            iteration = query.get("iteration", ["last"])[0]

            try:
                max_packets = int(query.get("max_packets", [450])[0])
            except ValueError:
                max_packets = 450

            try:
                window_data = get_packets_in_time_window(
                    target_dir,
                    start_ns=start_ns,
                    end_ns=end_ns,
                    iteration=iteration,
                    max_packets=max_packets
                )
                self._send_json(200, {"success": True, "source": source, "folder": target_dir.name, **window_data})
            except Exception as e:
                self._send_error(500, f"Error al consultar paquetes en ventana temporal: {e}")
            return

        # ---------------------------------------------------------------------
        # REST API Routes: Phase 3 (History & Comparative Analysis)
        # ---------------------------------------------------------------------
        if path == "/api/history/list":
            try:
                sims = list_all_simulations(self.results_root, self.staging_root)
                self._send_json(200, {"success": True, "simulations": sims, "total": len(sims)})
            except Exception as e:
                self._send_error(500, f"Error listando simulaciones: {e}")
            return

        # ---------------------------------------------------------------------
        # Static Assets Serving
        # ---------------------------------------------------------------------
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

        # ---------------------------------------------------------------------
        # POST: Phase 1 Lifecycle
        # ---------------------------------------------------------------------
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

        # ---------------------------------------------------------------------
        # POST: Phase 2 Save and Discard
        # ---------------------------------------------------------------------
        elif path == "/api/results/save":
            content_length = int(self.headers.get("Content-Length", 0))
            payload = {}
            if content_length > 0:
                try:
                    payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
                except Exception:
                    pass

            folder_name = payload.get("folder") or payload.get("folder_name")
            label = payload.get("label", "").strip()

            target_staging = self._resolve_simulation_dir("staging", folder_name)
            if not target_staging or not target_staging.exists():
                self._send_error(404, f"No se encontró carpeta en staging para guardar: {folder_name or '(activa)'}")
                return

            try:
                # Escribir gui_metadata.json dentro de la carpeta
                meta_file = target_staging / "gui_metadata.json"
                metadata = {
                    "folder_name": target_staging.name,
                    "label": label,
                    "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                with open(meta_file, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)

                # Mover carpeta de tmp_staging a results
                self.results_root.mkdir(parents=True, exist_ok=True)
                dest = self.results_root / target_staging.name
                if dest.exists():
                    shutil.rmtree(dest)

                shutil.move(str(target_staging), str(dest))

                self._send_json(200, {
                    "success": True,
                    "status": "saved",
                    "folder": dest.name,
                    "saved_folder_name": dest.name,
                    "folder_name": dest.name,
                    "saved_path": str(dest),
                    "label": label
                })
            except Exception as e:
                self._send_error(500, f"Error al guardar simulación en resultados: {e}")
            return

        elif path == "/api/results/discard":
            content_length = int(self.headers.get("Content-Length", 0))
            payload = {}
            if content_length > 0:
                try:
                    payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
                except Exception:
                    pass

            folder_name = payload.get("folder") or payload.get("folder_name")

            try:
                if self.staging_root.exists():
                    if folder_name:
                        target = self.staging_root / folder_name
                        if target.exists():
                            if target.is_dir():
                                shutil.rmtree(target)
                            else:
                                target.unlink()
                    else:
                        for item in self.staging_root.iterdir():
                            if item.is_dir():
                                shutil.rmtree(item)
                            else:
                                item.unlink()

                self._send_json(200, {
                    "success": True,
                    "status": "discarded",
                    "message": "Simulación descartada con éxito."
                })
            except Exception as e:
                self._send_error(500, f"Error al descartar simulación en staging: {e}")
            return

        # ---------------------------------------------------------------------
        # POST: Phase 3 (History & Comparative Analysis)
        # ---------------------------------------------------------------------
        elif path == "/api/history/label":
            content_length = int(self.headers.get("Content-Length", 0))
            payload = {}
            if content_length > 0:
                try:
                    payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
                except Exception:
                    pass

            folder_name = payload.get("folder") or payload.get("folder_name")
            label = payload.get("label", "").strip()

            if not folder_name:
                self._send_error(400, "Nombre de carpeta no especificado.")
                return

            try:
                target = (self.results_root / folder_name).resolve()
                if not str(target).startswith(str(self.results_root.resolve())):
                    self._send_error(403, "Acceso no autorizado fuera de build/results/")
                    return

                if not target.exists() or not target.is_dir():
                    self._send_error(404, f"Simulación no encontrada en historial: {folder_name}")
                    return

                meta_file = target / "gui_metadata.json"
                meta_data = {}
                if meta_file.exists():
                    try:
                        with open(meta_file, "r", encoding="utf-8") as f:
                            meta_data = json.load(f)
                    except Exception:
                        meta_data = {}

                meta_data["label"] = label
                meta_data["folder_name"] = folder_name
                meta_data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                with open(meta_file, "w", encoding="utf-8") as f:
                    json.dump(meta_data, f, indent=2, ensure_ascii=False)

                self._send_json(200, {
                    "success": True,
                    "folder": folder_name,
                    "label": label,
                    "message": "Etiqueta actualizada correctamente."
                })
            except Exception as e:
                self._send_error(500, f"Error al actualizar etiqueta: {e}")
            return

        elif path == "/api/history/delete":
            content_length = int(self.headers.get("Content-Length", 0))
            payload = {}
            if content_length > 0:
                try:
                    payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
                except Exception:
                    pass

            folder_name = payload.get("folder") or payload.get("folder_name")
            if not folder_name:
                self._send_error(400, "Nombre de carpeta no especificado.")
                return

            try:
                target = (self.results_root / folder_name).resolve()
                if not str(target).startswith(str(self.results_root.resolve())):
                    self._send_error(403, "Acceso no autorizado fuera de build/results/")
                    return

                if not target.exists() or not target.is_dir():
                    self._send_error(404, f"Simulación no encontrada: {folder_name}")
                    return

                shutil.rmtree(target)
                self._send_json(200, {
                    "success": True,
                    "folder": folder_name,
                    "message": f"Simulación '{folder_name}' eliminada correctamente del historial."
                })
            except Exception as e:
                self._send_error(500, f"Error al eliminar simulación: {e}")
            return

        elif path == "/api/analysis/compare":
            content_length = int(self.headers.get("Content-Length", 0))
            payload = {}
            if content_length > 0:
                try:
                    payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
                except Exception:
                    pass

            simulations = payload.get("simulations", [])
            semilog = bool(payload.get("semilog", False))

            if not simulations:
                self._send_error(400, "Debe seleccionar al menos una simulación para comparar.")
                return

            try:
                comp_data = compare_simulations(
                    simulations,
                    semilog=semilog,
                    base_results_dir=self.results_root,
                    base_staging_dir=self.staging_root
                )
                self._send_json(200, {"success": True, **comp_data})
            except Exception as e:
                self._send_error(500, f"Error generando comparativa: {e}")
            return

        else:
            self._send_error(404, f"Endpoint API no encontrado: {path}")


def create_server(host="0.0.0.0", port=8080):
    """Instantiates and returns the ThreadingHTTPServer."""
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, WorkbenchAPIHandler)
    return httpd
