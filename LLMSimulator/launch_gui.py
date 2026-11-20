#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM-NoC Co-Simulation Workbench (GUI Launcher).
Starts the local web server and opens the interactive dashboard in the default browser.
"""

import argparse
import sys
import os
import webbrowser
from pathlib import Path

# Ensure LLMSimulator directory is on Python path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from gui.server import create_server


def parse_args():
    parser = argparse.ArgumentParser(
        description="LLM-NoC Co-Simulation Workbench (GUI)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Puerto HTTP local para la interfaz gráfica (por defecto: 8080)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Dirección de escucha del servidor (por defecto: 0.0.0.0)"
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="No abrir automáticamente la pestaña en el navegador web"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    port = args.port
    host = args.host

    server = create_server(host=host, port=port)
    url = f"http://localhost:{port}"

    print("=" * 70)
    print("   🧠 LLM-NoC Co-Simulation Workbench (GUI)")
    print("   🔬 LLMSimulator + BookSim2 Cycle-Accurate Framework")
    print("=" * 70)
    print(f"🚀 Servidor web activo y a la escucha en: {url}")
    print("📡 Endpoints API REST operativos: /api/status, /api/run, /api/abort")
    print("💡 Presiona Ctrl+C en cualquier momento para detener el servidor.")
    print("=" * 70)

    if not args.no_browser:
        try:
            print("🌐 Abriendo navegador web predeterminado...")
            webbrowser.open(url)
        except Exception as e:
            print(f"⚠️ No se pudo abrir automáticamente el navegador: {e}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo servidor web...")
    finally:
        server.server_close()
        print("✅ Servidor detenido de forma limpia.")


if __name__ == "__main__":
    main()

