"""Perfil del vendedor y estado de la conexión."""

from __future__ import annotations

import flet as ft

import config
import ui_mobile as ui


def profile_view(app) -> ft.Control:
    vendedor = app.vendor or {}
    resumen = app.orders_summary or {}
    por_estado = resumen.get("por_estado", {})
    pendientes = int(por_estado.get("Pendiente", 0)) + int(
        por_estado.get("En revisión", 0)
    )

    datos = [
        _dato(ft.Icons.BADGE_OUTLINED, "Código", vendedor.get("codigo", "—")),
        _dato(ft.Icons.LOCATION_ON_OUTLINED, "Ciudad",
              vendedor.get("ciudad", "—")),
        _dato(ft.Icons.PHONE_OUTLINED, "Teléfono",
              vendedor.get("telefono", "—")),
        _dato(ft.Icons.EMAIL_OUTLINED, "Correo",
              vendedor.get("email", "—")),
    ]

    perfil = ui.card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            content=ui.txt(
                                _iniciales(vendedor.get("nombre", "V")),
                                20, ui.WHITE, ui.W_700,
                                align=ft.TextAlign.CENTER,
                            ),
                            width=54, height=54,
                            bgcolor=ui.TEAL,
                            border_radius=27,
                            alignment=ft.Alignment.CENTER,
                        ),
                        ft.Column(
                            [
                                ui.txt(vendedor.get("nombre", "Vendedor"),
                                       17, ui.INK, ui.W_700, max_lines=2),
                                ui.pill("Rol · Vendedor", ui.TEAL,
                                        ui.TEAL_SOFT, dot=True, size=9),
                            ],
                            spacing=5,
                            expand=True,
                        ),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Divider(height=1, color=ui.BORDER),
                ft.Column(datos, spacing=8),
            ],
            spacing=12,
        ),
        padding=15,
    )

    metricas = ft.Row(
        [
            ui.metric("Pedidos", str(resumen.get("total_pedidos", 0)),
                      ft.Icons.RECEIPT_LONG_OUTLINED, ui.TEAL, ui.TEAL_SOFT),
            ui.metric("Por revisar", str(pendientes),
                      ft.Icons.PENDING_ACTIONS_OUTLINED,
                      ui.ORANGE, ui.ORANGE_SOFT),
            ui.metric("Total", ui.money(resumen.get("total_usd", 0)),
                      ft.Icons.ATTACH_MONEY, ui.BLUE, ui.BLUE_SOFT),
        ],
        spacing=7,
    )

    conexion = ui.card(
        ft.Column(
            [
                ui.txt("Conexión", 13.5, ui.INK, ui.W_600),
                _dato(ft.Icons.STORAGE_OUTLINED, "Base de datos",
                      f"MongoDB Atlas · {app.db_name}"),
                _dato(
                    ft.Icons.CURRENCY_EXCHANGE,
                    "Tasa BCV",
                    f"{ui.bolivares(app.rate)} / $" if app.rate
                    else "No disponible",
                ),
                _dato(
                    ft.Icons.LOCK_OUTLINE,
                    "Seguridad",
                    "Conexión TLS directa a Atlas",
                ),
                ui.secondary_button(
                    "Actualizar tasa BCV",
                    ft.Icons.REFRESH,
                    lambda e: app.page.run_task(app.refresh_rate_async),
                ),
            ],
            spacing=9,
        ),
        padding=14,
    )

    acciones = ft.Column(
        [
            ui.primary_button(
                "Ver mis pedidos",
                ft.Icons.RECEIPT_LONG_OUTLINED,
                lambda e: app.set_tab("pedidos"),
            ),
            ui.secondary_button(
                "Cerrar sesión",
                ft.Icons.LOGOUT,
                lambda e: app.logout(),
                color=ui.RED,
            ),
            ui.txt(
                f"Mayorix Vendedor v{config.APP_VERSION} · DropeTech",
                9.5, ui.MUTED_2, align=ft.TextAlign.CENTER,
            ),
        ],
        spacing=8,
    )

    return ft.Column(
        [
            ft.Container(
                content=ui.section_title(
                    "Mi perfil",
                    "Red comercial Mayor Disluda",
                ),
                padding=ft.Padding.only(left=14, right=14, top=12, bottom=8),
            ),
            ft.Container(
                content=ft.Column(
                    [perfil, metricas, conexion, acciones,
                     ft.Container(height=12)],
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                ),
                padding=ft.Padding.symmetric(horizontal=14),
                expand=True,
            ),
        ],
        spacing=0,
        expand=True,
    )


def _dato(icono, label, valor):
    return ft.Row(
        [
            ft.Icon(icono, size=15, color=ui.MUTED),
            ui.txt(label, 10.5, ui.MUTED),
            ft.Container(expand=True),
            ui.txt(valor or "—", 10.5, ui.INK, ui.W_500, max_lines=1),
        ],
        spacing=7,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _iniciales(nombre: str) -> str:
    partes = [p for p in str(nombre or "").split() if p]
    if not partes:
        return "V"
    if len(partes) == 1:
        return partes[0][:2].upper()
    return (partes[0][0] + partes[-1][0]).upper()
