"""
Mayorix Desktop · Punto de entrada
==================================
Mayorix — Sistema de Gestión Mayorista para Mayor Disluda (Powered by DropeTech).

Aplicación de escritorio exclusiva para la administración de la empresa:
login corporativo validado contra MongoDB y panel central con dashboard,
inventario, pedidos y vendedores.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# En un .exe empaquetado con PyInstaller en modo ventana no existen stdout/stderr.
# Flet/uvicorn configuran logging al arrancar y necesitan flujos válidos.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")
if sys.stdin is None:
    sys.stdin = open(os.devnull, "r", encoding="utf-8")

for _flujo in (sys.stdout, sys.stderr):
    try:
        _flujo.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

import flet as ft

import bcv_service
import database
from views import empresa_view, login_view, tasa_bcv, ui


class MayorixApp:
    """Controla el ciclo Login de empresa → Panel administrativo → Logout."""

    def __init__(self, page: ft.Page):
        self.page = page
        self.db = database.get_database()
        self.shell: empresa_view.EmpresaShell | None = None
        self._configurar_pagina()
        tasa_bcv.inicializar()
        bcv_service.iniciar_servicio()
        self.show_login()

    # ------------------------------------------------------------------
    # Configuración
    # ------------------------------------------------------------------

    def _configurar_pagina(self):
        page = self.page
        page.title = "Mayorix · Acceso empresa"
        page.bgcolor = ui.BG
        page.padding = 0
        page.theme_mode = ft.ThemeMode.LIGHT
        page.theme = ft.Theme(
            font_family="Segoe UI",
            use_material3=True,
            color_scheme=ft.ColorScheme(
                primary=ui.TEAL,
                secondary=ui.ORANGE,
                surface=ui.WHITE,
                on_surface=ui.INK,
                outline=ui.BORDER,
            ),
        )
        page.window.width = 1280
        page.window.height = 800
        page.window.resizable = True
        page.window.movable = True
        page.window.minimizable = True
        page.window.maximizable = True
        page.window.frameless = False
        page.window.title_bar_hidden = False
        page.window.title_bar_buttons_hidden = False
        page.window.skip_task_bar = False
        page.window.prevent_close = False
        page.window.update()

    # ------------------------------------------------------------------
    # Sesión
    # ------------------------------------------------------------------

    def show_login(self):
        if self.shell is not None:
            self.shell.close_all_dialogs()
            self.shell = None
        self.page.controls.clear()
        self.page.bgcolor = ui.BG
        self.page.title = "Mayorix · Acceso empresa"
        self.page.add(login_view.login_view(self.page, self.db, self.login_empresa))
        self.page.update()

    def login_empresa(self, usuario: dict):
        self.page.controls.clear()
        self.page.title = "Mayorix · Panel de empresa"
        self.page.bgcolor = ui.BG
        self.shell = empresa_view.EmpresaShell(
            self.page, usuario, self.db, self.logout
        )
        self.page.update()

    def logout(self):
        if self.shell is not None:
            self.shell.close_all_dialogs()
            self.shell = None
        self.show_login()

    def toast(self, mensaje: str, tono: str = "success"):
        config = {
            "success": (ui.TEAL, ft.Icons.CHECK_CIRCLE_OUTLINED),
            "warning": (ui.ORANGE, ft.Icons.WARNING_AMBER_ROUNDED),
            "info": (ui.BLUE, ft.Icons.INFO_OUTLINE),
            "error": (ui.RED, ft.Icons.ERROR_OUTLINE),
        }
        color, icono = config.get(tono, (ui.TEAL, ft.Icons.INFO_OUTLINE))
        self.page.show_dialog(
            ft.SnackBar(
                content=ft.Row(
                    [
                        ft.Icon(icono, size=17, color=color),
                        ui.txt(mensaje, 11.5, ui.WHITE, ui.W_500, expand=True),
                    ],
                    spacing=9,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=ui.INK,
                behavior=ft.SnackBarBehavior.FLOATING,
                width=430,
                duration=3200,
                elevation=6,
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.Padding.symmetric(horizontal=14, vertical=12),
            )
        )


def main(page: ft.Page):
    MayorixApp(page)


if __name__ == "__main__":
    ft.run(main, assets_dir=str(Path(__file__).parent / "assets"))
