"""
Mayorix · Punto de entrada para Render / Web Service
====================================================
Ejecuta la aplicación administrativa existente en modo web, escuchando en
0.0.0.0 y usando el puerto dinámico de Render.

Local:
    python main.py
    PORT=8000 MONGO_URI="mongodb+srv://..." python main.py
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DESKTOP_DIR = BASE_DIR.parent / "src" / "Mayorix_Desktop"

try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

if str(DESKTOP_DIR) not in sys.path:
    sys.path.insert(0, str(DESKTOP_DIR))

import flet as ft  # noqa: E402


def _cargar_desktop():
    ruta = DESKTOP_DIR / "main.py"
    if not ruta.is_file():
        raise RuntimeError(f"No se encontró el punto de entrada: {ruta}")
    spec = importlib.util.spec_from_file_location(
        "mayorix_desktop_main", str(ruta)
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar Mayorix Desktop.")
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo
    spec.loader.exec_module(modulo)
    return modulo


desktop = _cargar_desktop()


def main(page: ft.Page):
    desktop.main(page)


if __name__ == "__main__":
    os.environ.setdefault("FLET_FORCE_WEB_SERVER", "1")
    puerto = int(os.getenv("PORT", "8000"))
    print(f"Mayorix web escuchando en http://0.0.0.0:{puerto}", flush=True)
    ft.run(
        main,
        host="0.0.0.0",
        port=puerto,
        view=ft.AppView.WEB_BROWSER,
        assets_dir=str(DESKTOP_DIR / "assets"),
    )
