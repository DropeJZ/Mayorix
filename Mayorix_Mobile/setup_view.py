"""Configuración inicial de la conexión directa a MongoDB Atlas."""

from __future__ import annotations

import flet as ft

import config
import ui_mobile as ui


def setup_view(app) -> ft.Control:
    uri = ft.TextField(
        hint_text="mongodb+srv://usuario:clave@cluster.mongodb.net/mayorix",
        multiline=True,
        min_lines=3,
        max_lines=5,
        border=ft.InputBorder.NONE,
        text_size=11.5,
        color=ui.INK,
        hint_style=ft.TextStyle(size=10.5, color=ui.MUTED_2),
        cursor_color=ui.TEAL,
        content_padding=ft.Padding.symmetric(horizontal=9, vertical=9),
        password=False,
    )
    mensaje = ui.txt("", 10, ui.MUTED, max_lines=4,
                     align=ft.TextAlign.CENTER)
    boton = ui.action_button(
        "Guardar y conectar",
        ft.Icons.CLOUD_DONE_OUTLINED,
    )

    async def guardar(e=None):
        boton.disabled = True
        boton.opacity = 0.6
        mensaje.value = "Validando conexión con Atlas…"
        mensaje.color = ui.MUTED
        app.page.update()
        try:
            await app.configurar_atlas(str(uri.value or ""))
        except Exception as exc:
            mensaje.value = str(exc) or "No se pudo guardar la configuración."
            mensaje.color = ui.RED
            boton.disabled = False
            boton.opacity = 1.0
            app.page.update()

    boton.on_click = lambda e: app.page.run_task(guardar)

    contenido = ft.Container(
        content=ft.Column(
            [
                ui.brand_mark(62, 29),
                ui.txt("Mayorix", 31, ui.INK, ui.W_700,
                       align=ft.TextAlign.CENTER),
                ui.txt("MAYOR DISLUDA · RED COMERCIAL", 8.8, ui.TEAL, ui.W_700,
                       align=ft.TextAlign.CENTER),
                ft.Container(height=5),
                ui.txt("Configuración del dispositivo", 19, ui.INK,
                       ui.W_700, align=ft.TextAlign.CENTER),
                ui.txt(
                    "Paso único para el administrador. Pega la URI remota de "
                    "MongoDB Atlas. Quedará guardada en el espacio privado "
                    "de esta instalación.",
                    10.5, ui.MUTED, align=ft.TextAlign.CENTER, max_lines=4,
                ),
                ui.field_shell(
                    "URI DE MONGODB ATLAS",
                    uri,
                    "Debe incluir la base mayorix y permitir la conexión "
                    "desde la red móvil del vendedor.",
                ),
                ui.info_box(
                    "Usa preferentemente un usuario de Atlas con permisos "
                    "mínimos sobre la base mayorix, no una cuenta atlasAdmin.",
                    ui.ORANGE, ui.ORANGE_SOFT, ui.ORANGE_BORDER,
                    ft.Icons.SECURITY,
                ),
                mensaje,
                boton,
                ui.txt(
                    f"Mayorix Vendedor v{config.APP_VERSION} · DropeTech",
                    9, ui.MUTED_2, align=ft.TextAlign.CENTER,
                ),
            ],
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
        ),
        width=max(280, min(int(app.page.width or 380) - 40, 390)),
        bgcolor=ui.WHITE,
        border=ft.Border.all(1, ui.BORDER),
        border_radius=18,
        padding=ft.Padding.symmetric(horizontal=17, vertical=18),
    )

    return ft.Container(
        content=ft.SafeArea(
            ft.Container(
                content=ft.Column(
                    [contenido],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                ),
                padding=ft.Padding.symmetric(horizontal=16, vertical=18),
                expand=True,
            ),
            expand=True,
        ),
        bgcolor=ui.BG,
        expand=True,
    )
