"""
Mayorix · Shell de la Empresa
=============================
Layout principal de la Administración Central de Mayor Disluda:
navegación animada, módulos conectados y cierre de sesión.
"""

from __future__ import annotations

import asyncio
import time

import flet as ft

import data
import database
from . import (
    dashboard_view,
    finanzas_view,
    inventario_view,
    pedidos_view,
    tasa_bcv,
    ui,
    vendedores_view,
)


NAV_ITEMS = [
    {
        "key": "dashboard", "label": "Dashboard", "group": "PRINCIPAL",
        "icon": ft.Icons.SPACE_DASHBOARD_OUTLINED,
        "description": "Resumen de Mayor Disluda y red comercial.",
        "view": dashboard_view.dashboard_view,
    },
    {
        "key": "inventario", "label": "Repuestos", "group": "OPERACIONES",
        "icon": ft.Icons.CAR_REPAIR,
        "description": "Inventario MongoDB, importación y OCR.",
        "view": inventario_view.inventario_view,
    },
    {
        "key": "pedidos", "label": "Pedidos recibidos", "group": "OPERACIONES",
        "icon": ft.Icons.SHOPPING_BAG_OUTLINED,
        "description": "Auditoría, aprobación y despacho.",
        "view": pedidos_view.pedidos_view,
    },
    {
        "key": "vendedores", "label": "Vendedores", "group": "RED COMERCIAL",
        "icon": ft.Icons.BADGE_OUTLINED,
        "description": "Registro y gestión de la red comercial.",
        "view": vendedores_view.vendedores_view,
    },
    {
        "key": "finanzas", "label": "Finanzas", "group": "ANÁLISIS",
        "icon": ft.Icons.BAR_CHART_OUTLINED,
        "description": "Ingresos, cuentas por cobrar y transacciones.",
        "view": finanzas_view.finanzas_view,
    },
]

NAV_POR_GRUPO = ["PRINCIPAL", "OPERACIONES", "RED COMERCIAL", "ANÁLISIS"]
NAV_MAP = {item["key"]: item for item in NAV_ITEMS}


class EmpresaShell:
    """Panel central de la empresa, con navegación y sesión."""

    def __init__(self, page: ft.Page, usuario: dict, db: database.Database, on_logout):
        self.page = page
        self.usuario = usuario
        self.db = db
        self.on_logout = on_logout
        self.route = "inventario"
        self._open_dialogs: list[ft.AlertDialog] = []
        self._nav_visuals: dict[str, dict] = {}
        self._pending_badge = None
        self._pending_badge_text = None
        self._registros_activo = True
        self._registros_vistos: set[str] = set()
        self._solicitudes_registro: list[dict] = []
        self._registros_count = -1
        self._registros_badge_text = None

        self.page.title = "Mayorix · Panel de empresa"
        self.page.bgcolor = ui.BG
        self.page.padding = 0

        try:
            vendedores_view.sincronizar_vendedores(self.db)
            pedidos_view.sincronizar_pedidos(self.db)
        except Exception:
            pass

        picker = next(
            (s for s in self.page.services if isinstance(s, ft.FilePicker)), None
        )
        if picker is None:
            picker = ft.FilePicker()
            self.page.services.append(picker)
        self.file_picker = picker

        self.sidebar_host = ft.Container(
            width=238,
            bgcolor=ui.WHITE,
            border=ft.Border(right=ft.BorderSide(1, ui.BORDER)),
            padding=0,
        )
        self.topbar_host = ft.Container(
            height=68,
            bgcolor=ui.WHITE,
            border=ft.Border(bottom=ft.BorderSide(1, ui.BORDER)),
            padding=0,
        )
        self.view_host = ft.AnimatedSwitcher(
            content=ft.Container(),
            duration=220,
            reverse_duration=150,
            switch_in_curve=ft.AnimationCurve.EASE_OUT,
            switch_out_curve=ft.AnimationCurve.EASE_IN,
            transition=ft.AnimatedSwitcherTransition.FADE,
        )
        self.content_area = ft.Column(
            [self.view_host],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=0,
        )
        body = ft.Column(
            [self.topbar_host, self.content_area],
            expand=True,
            spacing=0,
        )
        root = ft.Row(
            [self.sidebar_host, body],
            expand=True,
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        )
        self.sidebar_host.content = self._build_sidebar()
        self.page.add(root)
        self.render()
        self.page.run_task(self._actualizar_tasa_bcv, False)
        self.page.run_task(self._vigilar_registros_moviles)

    # ------------------------------------------------------------------
    # Navegación y render
    # ------------------------------------------------------------------

    def navigate(self, route: str):
        if route not in NAV_MAP:
            return
        self.route = route
        self.render()

    def refresh(self):
        self.render()

    def render(self):
        item = NAV_MAP.get(self.route, NAV_ITEMS[0])
        self._update_sidebar_active()
        self.topbar_host.content = self._build_topbar(item)
        try:
            vista = item["view"](self)
        except Exception as exc:
            vista = ui.info_box(
                f"No se pudo cargar el módulo {item['label']}: {exc}",
                ui.RED, ui.RED_SOFT, ui.RED, ft.Icons.ERROR_OUTLINE,
            )
        self.view_host.content = ft.Container(
            content=vista,
            padding=ft.Padding.only(left=26, right=26, top=22, bottom=30),
            opacity=0.0,
            animate_opacity=ft.Animation(210, ft.AnimationCurve.EASE_OUT),
        )
        self._refrescar_badge_pedidos()
        self.page.update()
        self.page.run_task(self._fade_in)
        self.page.run_task(self._scroll_to_top)

    def _refrescar_badge_pedidos(self):
        if self._pending_badge_text is None:
            return
        try:
            pendientes = dashboard_view.resumen_operativo(self.db)["pendientes"]
            self._pending_badge_text.value = str(pendientes)
            if self._pending_badge is not None:
                self._pending_badge.visible = pendientes > 0
        except Exception:
            pass

    async def _fade_in(self):
        try:
            await asyncio.sleep(0.02)
            actual = self.view_host.content
            if isinstance(actual, ft.Container):
                actual.opacity = 1.0
                self.page.update()
        except Exception:
            pass

    async def _actualizar_tasa_bcv(self, manual: bool = False):
        resultado = await asyncio.to_thread(tasa_bcv.actualizar, manual)
        if resultado.get("ok"):
            self.render()
            if manual:
                self.toast(
                    f"Tasa BCV: Bs. {data.TASA_VES:,.2f} / $",
                    "success" if not resultado.get("stale") else "warning",
                )
        elif manual:
            self.toast(
                resultado.get("error", "No se pudo actualizar la tasa BCV."),
                "warning",
            )

    async def _scroll_to_top(self):
        try:
            await self.content_area.scroll_to(
                offset=0, duration=180, curve=ft.AnimationCurve.EASE_OUT
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------------------

    def _build_sidebar(self):
        resumen = dashboard_view.resumen_operativo(self.db)
        logo = ft.Row(
            [
                ft.Container(
                    content=ft.Icon(ft.Icons.LOCAL_MALL_OUTLINED, size=22,
                                    color=ui.WHITE),
                    width=38,
                    height=38,
                    bgcolor=ui.TEAL,
                    border_radius=10,
                    alignment=ui.ALIGN_CENTER,
                ),
                ft.Column(
                    [
                        ui.txt("Mayorix", 21, ui.INK, ui.W_700),
                        ft.Text(
                            "POWERED BY DROPTECH",
                            size=8,
                            color=ui.MUTED_2,
                            weight=ui.W_700,
                            style=ft.TextStyle(letter_spacing=1.1),
                        ),
                    ],
                    spacing=0,
                    expand=True,
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        organizacion = ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ui.txt("MD", 9.5, ui.WHITE, ui.W_700),
                        width=27,
                        height=27,
                        bgcolor=ui.TEAL,
                        border_radius=7,
                        alignment=ui.ALIGN_CENTER,
                    ),
                    ft.Column(
                        [
                            ui.txt("Mayor Disluda", 10.5, ui.INK, ui.W_600,
                                   max_lines=1),
                            ui.txt("Repuestos · Venezuela", 8.5, ui.MUTED),
                        ],
                        spacing=0,
                        expand=True,
                    ),
                    ft.Icon(ft.Icons.UNFOLD_MORE, size=15, color=ui.MUTED_2),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=ui.SOFT,
            border=ft.Border.all(1, ui.BORDER),
            border_radius=8,
            padding=ft.Padding.symmetric(horizontal=8, vertical=7),
            on_click=lambda e: ui.open_company_dialog(self),
            ink=True,
            tooltip="Perfil de la empresa",
        )

        bloques = []
        for grupo in NAV_POR_GRUPO:
            items = [item for item in NAV_ITEMS if item["group"] == grupo]
            if not items:
                continue
            bloques.append(
                ft.Container(
                    content=ft.Text(
                        grupo,
                        size=8.5,
                        color=ui.MUTED_2,
                        weight=ui.W_700,
                        style=ft.TextStyle(letter_spacing=0.9),
                    ),
                    padding=ft.Padding.only(left=10, top=15, bottom=5),
                )
            )
            for item in items:
                bloque = self._nav_item(item)
                if item["key"] == "pedidos":
                    self._pending_badge_text = ui.txt(
                        str(resumen["pendientes"]), 8.5, ui.ORANGE, ui.W_700
                    )
                    self._pending_badge = ft.Container(
                        content=self._pending_badge_text,
                        bgcolor=ui.ORANGE_SOFT,
                        border_radius=9,
                        padding=ft.Padding.symmetric(horizontal=5, vertical=1),
                        visible=resumen["pendientes"] > 0,
                    )
                    bloque.content.controls.append(self._pending_badge)
                bloques.append(bloque)

        conectado = self.db.conectado
        estado_db = ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        width=6, height=6,
                        bgcolor=ui.TEAL if conectado else ui.ORANGE,
                        border_radius=3,
                    ),
                    ui.txt(self.db.estado_texto, 8.5,
                           ui.TEAL_DARK if conectado else "#9A3412",
                           ui.W_600, expand=True, max_lines=1),
                    ft.Icon(ft.Icons.CIRCLE, size=5, color=ui.MUTED_2),
                ],
                spacing=5,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            on_click=lambda e: self._conexion_dialog(),
            tooltip=self.db.detalle_estado,
            bgcolor=ui.SOFT,
            border=ft.Border.all(1, ui.BORDER),
            border_radius=8,
            padding=ft.Padding.symmetric(horizontal=9, vertical=7),
            ink=True,
        )

        utilidades = ft.Column(
            [
                self._utility_item("Ayuda y soporte", ft.Icons.HELP_OUTLINE,
                                   self._ayuda_dialog),
                self._utility_item("Configuración", ft.Icons.SETTINGS_OUTLINED,
                                   self._conexion_dialog),
            ],
            spacing=1,
        )

        pie = ft.Column(
            [
                ft.Divider(height=1, color=ui.BORDER),
                estado_db,
                ft.Row(
                    [
                        ui.txt("Mayorix v2.1.5", 8.3, ui.MUTED_2),
                        ft.Container(expand=True),
                        ui.txt("DropeTech", 8.3, ui.MUTED_2),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=9,
        )

        return ft.Column(
            [
                ft.Container(content=logo, padding=ft.Padding.only(
                    left=2, right=2, top=2, bottom=2)),
                organizacion,
                ft.Column(bloques, spacing=1),
                ft.Container(expand=True, height=8),
                utilidades,
                pie,
            ],
            spacing=9,
            expand=True,
        )

    def _nav_item(self, item):
        activo = item["key"] == self.route
        barra_activa = ft.Container(
            width=3, height=17,
            bgcolor=ui.TEAL if activo else "transparent",
            border_radius=2,
        )
        icono = ft.Icon(
            item["icon"], size=17,
            color=ui.TEAL if activo else ui.MUTED,
        )
        etiqueta = ui.txt(
            item["label"], 12.5,
            ui.TEAL_DARK if activo else "#334155",
            ui.W_600 if activo else ui.W_500,
            expand=True, max_lines=1,
        )
        contenido = ft.Row(
            [barra_activa, icono, etiqueta],
            spacing=9,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        contenedor = ft.Container(
            content=contenido,
            bgcolor=ui.SOFT_2 if activo else "transparent",
            border_radius=8,
            padding=ft.Padding.symmetric(horizontal=7, vertical=8),
            on_click=lambda e, key=item["key"]: self.navigate(key),
            ink=True,
            tooltip=item["description"] if not activo else None,
        )
        self._nav_visuals[item["key"]] = {
            "container": contenedor,
            "bar": barra_activa,
            "icon": icono,
            "label": etiqueta,
        }
        return contenedor

    def _utility_item(self, label, icono, on_click):
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(icono, size=16, color=ui.MUTED),
                    ui.txt(label, 11, "#334155", ui.W_500),
                ],
                spacing=9,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=10, vertical=6),
            border_radius=8,
            on_click=lambda e: on_click(),
            ink=True,
            tooltip=label,
        )

    def _update_sidebar_active(self):
        for key, visual in self._nav_visuals.items():
            activo = key == self.route
            visual["container"].bgcolor = ui.SOFT_2 if activo else "transparent"
            visual["bar"].bgcolor = ui.TEAL if activo else "transparent"
            visual["icon"].color = ui.TEAL if activo else ui.MUTED
            visual["label"].color = ui.TEAL_DARK if activo else "#334155"
            visual["label"].weight = ui.W_600 if activo else ui.W_500

    # ------------------------------------------------------------------
    # Topbar
    # ------------------------------------------------------------------

    def _build_topbar(self, item):
        migas = ft.Row(
            [
                ft.Container(
                    content=ui.txt("MD", 8.5, ui.WHITE, ui.W_700),
                    width=25, height=25, bgcolor=ui.TEAL, border_radius=6,
                    alignment=ui.ALIGN_CENTER,
                ),
                ft.Column(
                    [
                        ui.txt("Mayor Disluda", 10.5, ui.INK, ui.W_600),
                        ui.txt("Mayorix · Powered by DropeTech", 8.3, ui.MUTED),
                    ],
                    spacing=0,
                ),
                ft.Icon(ft.Icons.CHEVRON_RIGHT, size=14, color=ui.MUTED_2),
                ui.txt(item["label"], 10.5, ui.INK, ui.W_600),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        nombre_usuario = (self.usuario or {}).get("nombre") or "Administrador"
        email_usuario = (self.usuario or {}).get("email") or "Mayor Disluda"
        perfil = ft.PopupMenuButton(
            content=ft.Container(
                content=ft.Row(
                    [
                        ui.avatar(nombre_usuario, ui.TEAL, 30, 10.5),
                        ft.Column(
                            [
                                ui.txt(nombre_usuario, 10.5, ui.INK, ui.W_600,
                                       max_lines=1),
                                ui.txt(email_usuario, 8.5, ui.MUTED,
                                       max_lines=1),
                            ],
                            spacing=0,
                        ),
                        ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN, size=15,
                                color=ui.MUTED_2),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.Padding.symmetric(horizontal=5, vertical=3),
                border_radius=8,
            ),
            items=[
                ft.PopupMenuItem(
                    content=ui.txt("Perfil de empresa", 12),
                    icon=ft.Icons.BUSINESS_CENTER_OUTLINED,
                    on_click=lambda e: ui.open_company_dialog(self),
                ),
                ft.PopupMenuItem(
                    content=ui.txt("Conexión MongoDB", 12),
                    icon=ft.Icons.STORAGE_OUTLINED,
                    on_click=lambda e: self._conexion_dialog(),
                ),
                ft.PopupMenuItem(
                    content=ui.txt("Cerrar sesión", 12, ui.RED),
                    icon=ft.Icons.LOGOUT,
                    on_click=lambda e: self.logout(),
                ),
            ],
            tooltip="Menú de cuenta",
        )

        registros_count = len(self._solicitudes_registro)
        self._registros_badge_text = ui.txt(
            str(registros_count), 8.5,
            ui.WHITE if registros_count else ui.MUTED,
            ui.W_700,
        )
        registros_btn = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.PHONE_ANDROID, size=15,
                        color=ui.ORANGE if registros_count else ui.MUTED,
                    ),
                    ui.txt("Móvil", 9.5,
                           ui.ORANGE if registros_count else ui.MUTED,
                           ui.W_600),
                    ft.Container(
                        content=self._registros_badge_text,
                        bgcolor=ui.ORANGE if registros_count else ui.SOFT_2,
                        border_radius=9,
                        padding=ft.Padding.symmetric(horizontal=5, vertical=1),
                    ),
                ],
                spacing=5,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=8, vertical=5),
            bgcolor=ui.ORANGE_SOFT if registros_count else ui.WHITE,
            border=ft.Border.all(
                1, ui.ORANGE_BORDER if registros_count else ui.BORDER
            ),
            border_radius=20,
            on_click=lambda e: self._registros_dialog(),
            ink=True,
            tooltip="Registros móviles pendientes",
        )

        return ft.Container(
            content=ft.Row(
                [
                    migas,
                    ft.Container(expand=True),
                    registros_btn,
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.CURRENCY_EXCHANGE, size=12,
                                        color=ui.MUTED),
                                ui.txt(f"Bs. {data.TASA_VES:,.2f} / $", 9.5,
                                       ui.MUTED, ui.W_600),
                                ft.Icon(ft.Icons.REFRESH, size=11,
                                        color=ui.MUTED_2),
                            ],
                            spacing=5,
                            tight=True,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        bgcolor=ui.SOFT_2,
                        border_radius=20,
                        padding=ft.Padding.symmetric(horizontal=9, vertical=5),
                        on_click=lambda e: self.page.run_task(
                            self._actualizar_tasa_bcv, True),
                        ink=True,
                        tooltip=tasa_bcv.detalle(),
                    ),
                    ui.fecha_chip(
                        f"{data.HOY.day} {ui.MESES_CORTOS[data.HOY.month - 1]} "
                        f"{data.HOY.year}"
                    ),
                    perfil,
                ],
                spacing=11,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=22),
        )

    # ------------------------------------------------------------------
    # Diálogos y sesión
    # ------------------------------------------------------------------

    def show_dialog(self, dialog):
        self._open_dialogs.append(dialog)
        self.page.show_dialog(dialog)

    def close_dialog(self):
        self.close_dialogs(1)

    def close_dialogs(self, cantidad=1):
        cerrados = 0
        while self._open_dialogs and cerrados < cantidad:
            dialog = self._open_dialogs.pop()
            if getattr(dialog, "open", False):
                dialog.open = False
                dialog.update()
                cerrados += 1

    def close_all_dialogs(self):
        while self._open_dialogs:
            dialog = self._open_dialogs.pop()
            if getattr(dialog, "open", False):
                dialog.open = False
                dialog.update()

    def toast(self, mensaje, tono="success", duracion=3200):
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
                duration=duracion,
                elevation=6,
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.Padding.symmetric(horizontal=14, vertical=12),
            )
        )

    def logout(self):
        self._registros_activo = False
        self.close_all_dialogs()
        self.on_logout()

    async def _vigilar_registros_moviles(self):
        while self._registros_activo:
            try:
                solicitudes = await asyncio.to_thread(
                    self.db.listar_solicitudes_registro
                )
                nuevas = [
                    s for s in solicitudes
                    if str(s.get("solicitud_id", "")) not in self._registros_vistos
                ]
                self._solicitudes_registro = solicitudes
                for solicitud in nuevas:
                    sid = str(solicitud.get("solicitud_id", ""))
                    if sid:
                        self._registros_vistos.add(sid)
                    self.toast(
                        "Nuevo registro móvil · "
                        f"{solicitud.get('nombre', 'Vendedor')} · "
                        f"código {solicitud.get('codigo', '')}",
                        "info",
                        9000,
                    )
                self._actualizar_boton_registros()
            except Exception:
                pass
            await asyncio.sleep(3)

    def _actualizar_boton_registros(self, force: bool = False):
        cantidad = len(self._solicitudes_registro)
        if not force and cantidad == self._registros_count:
            return
        self._registros_count = cantidad
        if self._registros_badge_text is not None:
            self._registros_badge_text.value = str(cantidad)
            self._registros_badge_text.color = (
                ui.WHITE if cantidad else ui.MUTED
            )
        try:
            if self.topbar_host is not None:
                self.topbar_host.content = self._build_topbar(
                    NAV_MAP.get(self.route, NAV_ITEMS[0])
                )
                self.page.update()
        except Exception:
            pass

    def _registros_dialog(self):
        solicitudes = self.db.listar_solicitudes_registro()
        self._solicitudes_registro = solicitudes
        self._actualizar_boton_registros(force=True)
        if not solicitudes:
            cuerpo = ui.info_box(
                "No hay solicitudes de registro móvil pendientes. Los "
                "códigos aparecen aquí en cuanto un vendedor valida su "
                "cédula en la app Android.",
                ui.TEAL, ui.TEAL_SOFT, ui.TEAL_BORDER,
                ft.Icons.PHONE_ANDROID,
            )
        else:
            tarjetas = []
            for solicitud in solicitudes:
                restante = max(
                    0, int(solicitud.get("expira_epoch", 0)) - int(time.time())
                )
                minutos = max(1, (restante + 59) // 60)
                tarjetas.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Column(
                                    [
                                        ui.txt(
                                            solicitud.get("nombre", "Vendedor"),
                                            13, ui.INK, ui.W_700,
                                        ),
                                        ui.txt(
                                            f"Cédula "
                                            f"{solicitud.get('cedula', '')} · "
                                            f"{solicitud.get('vendedor_codigo', '')}",
                                            9.5, ui.MUTED,
                                        ),
                                        ui.txt(
                                            f"Vence en {minutos} min",
                                            9.5, ui.ORANGE, ui.W_600,
                                        ),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                                ft.Column(
                                    [
                                        ui.txt("CÓDIGO", 8.5, ui.MUTED_2,
                                               ui.W_700),
                                        ui.txt(
                                            str(solicitud.get("codigo", "")),
                                            24, ui.TEAL_DARK, ui.W_700,
                                        ),
                                    ],
                                    spacing=0,
                                    horizontal_alignment=(
                                        ft.CrossAxisAlignment.CENTER
                                    ),
                                ),
                                ui.text_button(
                                    "Descartar", ft.Icons.DELETE_OUTLINE,
                                    lambda e, sid=solicitud.get(
                                        "solicitud_id", ""
                                    ): self._descartar_solicitud(sid),
                                    color=ui.MUTED, size=9.5,
                                ),
                            ],
                            spacing=12,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        bgcolor=ui.SOFT,
                        border=ft.Border.all(1, ui.BORDER),
                        border_radius=12,
                        padding=12,
                    )
                )
            cuerpo = ft.Column(
                tarjetas,
                spacing=8,
                scroll=ft.ScrollMode.AUTO,
                height=min(420, max(120, len(tarjetas) * 96)),
            )
        self.show_dialog(ui._dialog_base(
            "Registros móviles",
            "Códigos de verificación para vendedores",
            cuerpo,
            [
                ui.text_button(
                    "Actualizar", ft.Icons.REFRESH,
                    lambda e: (self.close_dialog(), self._registros_dialog()),
                    color=ui.TEAL, size=11.5,
                ),
                ui.text_button("Cerrar", None, lambda e: self.close_dialog(),
                               color=ui.MUTED, size=11.5),
            ],
            width=620,
            icono=ft.Icons.PHONE_ANDROID,
            color=ui.ORANGE,
            bg=ui.ORANGE_SOFT,
        ))

    def _descartar_solicitud(self, solicitud_id: str):
        self.db.descartar_solicitud_registro(solicitud_id)
        self._solicitudes_registro = self.db.listar_solicitudes_registro()
        self._registros_count = -1
        self._actualizar_boton_registros(force=True)
        self.close_dialog()
        self._registros_dialog()

    def _ayuda_dialog(self):
        cuerpo = ft.Column(
            [
                ui.info_box(
                    "Mayorix está operativo. Usa el menú lateral para abrir "
                    "Dashboard, Repuestos, Pedidos recibidos, Vendedores y "
                    "Finanzas.",
                    ui.TEAL, ui.TEAL_SOFT, ui.TEAL_BORDER,
                    ft.Icons.CHECK_CIRCLE_OUTLINE,
                ),
                ui.txt(
                    "Si algún módulo muestra un aviso de conexión, abre "
                    "Configuración o el indicador de MongoDB y pulsa "
                    "Reconectar. La app conserva el modo de respaldo local "
                    "mientras Atlas no esté disponible.",
                    10, ui.MUTED, max_lines=5,
                ),
                ui.txt(
                    "Soporte técnico · DropeTech · Mayorix Desktop v2.1.5",
                    9.5, ui.MUTED_2,
                ),
            ],
            spacing=12,
        )
        self.show_dialog(ui._dialog_base(
            "Ayuda y soporte",
            "Guía rápida de operación",
            cuerpo,
            [
                ui.text_button("Estado de MongoDB", ft.Icons.STORAGE_OUTLINED,
                               lambda e: (self.close_dialog(),
                                          self._conexion_dialog()),
                               color=ui.TEAL, size=11.5),
                ui.text_button("Cerrar", None, lambda e: self.close_dialog(),
                               color=ui.MUTED, size=11.5),
            ],
            width=520,
            icono=ft.Icons.HELP_OUTLINE,
            color=ui.TEAL,
            bg=ui.TEAL_SOFT,
        ))

    def _conexion_dialog(self):
        conectado = self.db.conectado
        cuerpo = ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ui.txt("Estado", 9.5, ui.MUTED),
                                ui.pill(self.db.estado_texto,
                                        ui.TEAL if conectado else ui.ORANGE,
                                        ui.TEAL_SOFT if conectado else ui.ORANGE_SOFT),
                            ],
                            spacing=3,
                            expand=1,
                        ),
                        ft.Column(
                            [
                                ui.txt("Base de datos", 9.5, ui.MUTED),
                                ui.txt(self.db.db_name if conectado else "mayorix",
                                       10.5, ui.INK, ui.W_600),
                            ],
                            spacing=3,
                            expand=1,
                        ),
                    ],
                    spacing=14,
                ),
                ui.info_box(
                    self.db.detalle_estado if not conectado else
                    "MongoDB está conectado. Inventario y vendedores se guardan en línea.",
                    ui.ORANGE if not conectado else ui.TEAL,
                    ui.ORANGE_SOFT if not conectado else ui.TEAL_SOFT,
                    ui.ORANGE_BORDER if not conectado else ui.TEAL_BORDER,
                    ft.Icons.STORAGE_OUTLINED,
                ),
                ft.Row(
                    [
                        ft.Icon(ft.Icons.SETTINGS_ETHERNET, size=14, color=ui.MUTED),
                        ui.txt(f"URI: {self.db.uri_visible}", 9, ui.MUTED,
                               expand=True, max_lines=2),
                    ],
                    spacing=6,
                ),
                ui.txt(
                    "Configura la variable MONGO_URI para Atlas o una instancia "
                    "local autenticada. Si no está disponible, Mayorix mantiene "
                    "el modo de respaldo local.",
                    9.5, ui.MUTED, max_lines=4,
                ),
            ],
            spacing=12,
        )
        self.show_dialog(ui._dialog_base(
            "Conexión MongoDB",
            "Estado de la capa de datos de Mayorix",
            cuerpo,
            [
                ui.text_button("Reconectar", ft.Icons.REFRESH, self._reconectar,
                               color=ui.TEAL, size=11.5),
                ui.text_button("Cerrar", None, lambda e: self.close_dialog(),
                               color=ui.MUTED, size=11.5),
            ],
            width=500,
            icono=ft.Icons.STORAGE_OUTLINED,
            color=ui.TEAL,
            bg=ui.TEAL_SOFT,
        ))

    def _reconectar(self):
        ok, mensaje = self.db.reconectar()
        self.close_dialog()
        if ok:
            self.refresh()
            self.toast("MongoDB conectado correctamente.", "success")
        else:
            self.toast(mensaje, "warning")
