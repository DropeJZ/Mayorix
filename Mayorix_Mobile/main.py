"""
Mayorix · Aplicación Android para vendedores
==========================================
Catálogo en vivo, carrito, tasa BCV, historial y registro por cédula.
Conexión directa a MongoDB Atlas desde el teléfono.
"""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

import flet as ft

import config
import rate
import session_store
import ui_mobile as ui
from catalog_view import catalog_view
from cart_view import cart_view
from data_mobile import MobileStore
from login_view import login_view
from orders_view import orders_view, show_order_detail
from profile_view import profile_view
from setup_view import setup_view

TABS = [
    ("catalogo", "Catálogo", ft.Icons.INVENTORY_2_OUTLINED),
    ("carrito", "Carrito", ft.Icons.SHOPPING_CART_OUTLINED),
    ("pedidos", "Pedidos", ft.Icons.RECEIPT_LONG_OUTLINED),
    ("perfil", "Perfil", ft.Icons.PERSON_OUTLINE),
]


class VendedorApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.store = MobileStore()
        self.db_name = self.store.db_name
        self.vendor: dict = {}
        self.rate = 0.0
        self.session_token = ""
        self.session_expira = 0
        self.tab = "catalogo"
        self.cart: dict[str, dict] = {}
        self.checkout = {
            "cliente": "",
            "ciudad": "",
            "condicion": "Contado",
            "tipo_doc": "Nota de entrega",
            "notas": "",
        }
        self.cart_fields: dict[str, object] = {}
        self.order_sending = False

        self.login_modo = "login"
        self.registro_cedula = ""
        self.registro_vendor: dict = {}
        self.registro_expira = 0

        self.catalog_q = ""
        self.catalog_items: list[dict] = []
        self.catalog_total = 0
        self.catalog_loading = False
        self.catalog_error = ""
        self._search_version = 0

        self.orders_items: list[dict] = []
        self.orders_summary: dict = {}
        self.orders_loading = False
        self.orders_error = ""
        self.orders_loaded = False

        self.content_host: ft.Container | None = None
        self.nav_host: ft.Container | None = None

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    async def run_blocking(self, fn, *args, **kwargs):
        return await asyncio.to_thread(fn, *args, **kwargs)

    def toast(self, mensaje, tono="success"):
        color = {
            "success": ui.TEAL,
            "error": ui.RED,
            "warning": ui.ORANGE,
            "info": ui.BLUE,
        }.get(tono, ui.INK)
        self.page.show_dialog(
            ft.SnackBar(
                content=ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.CHECK_CIRCLE_OUTLINED
                            if tono == "success" else ft.Icons.INFO_OUTLINE,
                            size=17, color=color,
                        ),
                        ui.txt(mensaje, 11, ui.WHITE, ui.W_500, expand=True),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=ui.INK,
                behavior=ft.SnackBarBehavior.FLOATING,
                duration=2000,
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.Padding.symmetric(horizontal=13, vertical=10),
            )
        )

    # ------------------------------------------------------------------
    # Sesión y registro
    # ------------------------------------------------------------------

    def refresh_login(self):
        self.page.controls.clear()
        self.page.add(login_view(self))
        self.page.update()

    def show_login(self):
        self.vendor = {}
        self.session_token = ""
        self.session_expira = 0
        self.cart = {}
        self.catalog_items = []
        self.orders_items = []
        self.orders_summary = {}
        self.orders_loaded = False
        self.login_modo = "login"
        self.registro_cedula = ""
        self.registro_vendor = {}
        self.registro_expira = 0
        self.page.title = "Mayorix · Vendedor"
        self.refresh_login()

    def iniciar_sesion_o_login(self):
        try:
            sesion = session_store.leer_sesion()
        except Exception:
            sesion = None
        if sesion:
            self.vendor = sesion.get("vendor", {}) or {}
            self.session_token = sesion.get("token", "")
            self.session_expira = int(sesion.get("expira_epoch", 0) or 0)
            self.rate = float(sesion.get("tasa", 0) or 0)
            self.show_shell()
            self.page.run_task(self._restaurar_sesion_remota, self.session_token)
            return
        self.show_login()

    async def _restaurar_sesion_remota(self, token: str):
        await self._cargar_tasa()
        if self.session_token != token:
            return
        session_store.guardar_sesion(
            token, self.vendor, self.session_expira, self.rate
        )
        try:
            vendedor = await self.run_blocking(
                self.store.validar_sesion, token
            )
        except Exception:
            self.toast(
                "Sin conexión con Atlas. Se conserva la sesión guardada.",
                "warning",
            )
            if self.content_host is not None:
                self.refresh_view()
            return
        if not vendedor or self.session_token != token:
            self._cerrar_sesion(
                aviso="La sesión expiró o fue revocada. Inicia sesión de nuevo."
            )
            return
        self.vendor = vendedor
        session_store.guardar_sesion(
            token, self.vendor, self.session_expira, self.rate
        )
        if self.content_host is not None:
            self.refresh_view()

    def _cerrar_sesion(self, aviso: str = ""):
        token = self.session_token
        self.session_token = ""
        self.session_expira = 0
        session_store.borrar_sesion()
        if token:
            self.page.run_task(self._revocar_sesion_remota, token)
        self.show_login()
        if aviso:
            self.toast(aviso, "warning")

    async def _revocar_sesion_remota(self, token: str):
        try:
            await self.run_blocking(self.store.revocar_sesion, token)
        except Exception:
            pass

    def show_setup(self):
        self.page.title = "Mayorix · Configuración"
        self.page.controls.clear()
        self.page.add(setup_view(self))
        self.page.update()

    async def configurar_atlas(self, uri: str):
        await self.run_blocking(self.store.configurar, uri)
        self.db_name = self.store.db_name
        await self._cargar_tasa()
        self.iniciar_sesion_o_login()
        self.toast("Conexión con MongoDB Atlas configurada.", "success")

    async def _cargar_tasa(self):
        try:
            datos = await self.run_blocking(rate.consultar_tasa)
            self.rate = float(datos.get("tasa", 0) or 0)
        except Exception:
            self.rate = 0.0

    async def login(self, cedula: str, password: str):
        vendedor = await self.run_blocking(
            self.store.autenticar_vendedor, cedula, password
        )
        self.vendor = vendedor
        await self._cargar_tasa()
        try:
            sesion = await self.run_blocking(
                self.store.crear_sesion, vendedor
            )
            self.session_token = sesion.get("token", "")
            self.session_expira = int(sesion.get("expira_epoch", 0) or 0)
            session_store.guardar_sesion(
                self.session_token, self.vendor, self.session_expira,
                self.rate,
            )
        except Exception:
            self.session_token = ""
            self.session_expira = 0
            self.toast(
                "Sesión iniciada, pero no se pudo guardar para el próximo "
                "arranque.",
                "warning",
            )
        self.show_shell()

    async def solicitar_registro(self, cedula: str):
        datos = await self.run_blocking(
            self.store.crear_solicitud_registro, cedula
        )
        self.registro_cedula = cedula
        self.registro_vendor = datos.get("vendedor", {}) or {}
        self.registro_expira = int(datos.get("expira_epoch", 0) or 0)
        self.login_modo = "codigo"
        self.refresh_login()

    async def confirmar_registro(self, codigo: str, password: str):
        vendedor = await self.run_blocking(
            self.store.confirmar_registro,
            self.registro_cedula,
            codigo,
            password,
        )
        self.vendor = vendedor
        self.login_modo = "login"
        await self._cargar_tasa()
        try:
            sesion = await self.run_blocking(
                self.store.crear_sesion, vendedor
            )
            self.session_token = sesion.get("token", "")
            self.session_expira = int(sesion.get("expira_epoch", 0) or 0)
            session_store.guardar_sesion(
                self.session_token, self.vendor, self.session_expira,
                self.rate,
            )
        except Exception:
            self.session_token = ""
            self.session_expira = 0
        self.show_shell()
        self.toast("Registro completado. Bienvenido a Mayorix.", "success")

    def logout(self):
        self._cerrar_sesion(aviso="Sesión cerrada.")

    def show_shell(self):
        self.page.title = "Mayorix · Vendedor"
        self.page.controls.clear()
        self.content_host = ft.Container(expand=True, bgcolor=ui.BG)
        self.nav_host = ft.Container(content=self._nav())
        root = ft.SafeArea(
            ft.Column(
                [
                    ui.top_bar(
                        self,
                        "Mayorix",
                        f"{self.vendor.get('nombre', 'Vendedor')} · "
                        f"{self.vendor.get('ciudad', 'Red comercial')}",
                    ),
                    self.content_host,
                    self.nav_host,
                ],
                spacing=0,
                expand=True,
            ),
            expand=True,
        )
        self.page.add(ft.Container(content=root, bgcolor=ui.BG, expand=True))
        self.set_tab("catalogo")

    def _nav(self):
        return ui.bottom_nav(self, TABS, self.tab)

    def refresh_nav(self):
        if self.nav_host is not None:
            self.nav_host.content = self._nav()
            self.page.update()

    def set_tab(self, key: str):
        if key not in {t[0] for t in TABS}:
            return
        self.tab = key
        if self.nav_host is not None:
            self.nav_host.content = self._nav()
        if key == "catalogo" and not self.catalog_items and not self.catalog_loading:
            self.page.run_task(self.load_catalog, True)
            return
        if key == "pedidos" and not self.orders_loaded and not self.orders_loading:
            self.page.run_task(self.load_orders_async, False)
            return
        self.refresh_view()

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def refresh_view(self):
        if self.content_host is None:
            return
        vistas = {
            "catalogo": catalog_view,
            "carrito": cart_view,
            "pedidos": orders_view,
            "perfil": profile_view,
        }
        constructor = vistas.get(self.tab, catalog_view)
        try:
            self.content_host.content = constructor(self)
        except Exception as exc:
            self.content_host.content = ft.Container(
                content=ui.error_state(f"No se pudo cargar la vista: {exc}"),
                padding=14,
            )
        self.page.update()

    # ------------------------------------------------------------------
    # Catálogo
    # ------------------------------------------------------------------

    def on_catalog_search(self, texto: str):
        self.catalog_q = str(texto or "")
        self._search_version += 1
        self.page.run_task(
            self._buscar_debounced, self._search_version, self.catalog_q
        )

    async def _buscar_debounced(self, version: int, texto: str):
        await asyncio.sleep(0.30)
        if version != self._search_version:
            return
        await self.load_catalog(True)

    async def load_catalog(self, reset: bool = True):
        if self.catalog_loading:
            return
        self.catalog_loading = True
        self.catalog_error = ""
        if reset:
            self.catalog_items = []
            self.catalog_total = 0
        self.refresh_view()
        try:
            skip = 0 if reset else len(self.catalog_items)
            datos = await self.run_blocking(
                self.store.catalogo, self.catalog_q, skip, 20
            )
            items = datos.get("items", []) or []
            if reset:
                self.catalog_items = items
            else:
                existentes = {i.get("codigo") for i in self.catalog_items}
                self.catalog_items.extend(
                    item for item in items
                    if item.get("codigo") not in existentes
                )
            self.catalog_total = int(datos.get("total", 0) or 0)
        except Exception as exc:
            self.catalog_error = (
                "No se pudo consultar Atlas. Revisa tu conexión a internet."
                if not str(exc) else str(exc)
            )
        finally:
            self.catalog_loading = False
        self.refresh_view()

    # ------------------------------------------------------------------
    # Carrito
    # ------------------------------------------------------------------

    def add_to_cart(self, item):
        codigo = str(item.get("codigo", "")).upper()
        if not codigo:
            return
        if codigo in self.cart:
            self.cart[codigo]["cantidad"] += 1
        else:
            self.cart[codigo] = {"doc": dict(item), "cantidad": 1}
        self.refresh_nav()
        self.toast(f"{codigo} agregado al carrito.", "success")
        if self.tab == "carrito":
            self.refresh_view()

    def change_qty(self, codigo: str, delta: int):
        entrada = self.cart.get(codigo)
        if not entrada:
            return
        entrada["cantidad"] += int(delta)
        if entrada["cantidad"] <= 0:
            self.cart.pop(codigo, None)
        self.refresh_nav()
        self.refresh_view()

    def remove_item(self, codigo: str):
        self.cart.pop(codigo, None)
        self.refresh_nav()
        self.refresh_view()

    def cart_totals(self):
        subtotal = sum(
            float(entrada["doc"].get("precio", 0) or 0) * entrada["cantidad"]
            for entrada in self.cart.values()
        )
        subtotal = round(subtotal, 2)
        iva = round(subtotal * 0.16, 2) \
            if self.checkout.get("tipo_doc") == "Factura fiscal" else 0.0
        total = round(subtotal + iva, 2)
        return subtotal, iva, total

    async def submit_order_async(self):
        if self.order_sending or not self.cart:
            return
        for clave, control in self.cart_fields.items():
            try:
                self.checkout[clave] = str(control.value or "")
            except AttributeError:
                pass
        if len(str(self.checkout.get("cliente", "")).strip()) < 2:
            self.toast("Indica el nombre del cliente.", "warning")
            return
        self.order_sending = True
        self.refresh_view()
        payload = {
            "cliente_nombre": self.checkout["cliente"].strip(),
            "cliente_ciudad": self.checkout["ciudad"].strip(),
            "condicion": self.checkout["condicion"],
            "tipo_doc": self.checkout["tipo_doc"],
            "notas": self.checkout["notas"].strip(),
            "items": [
                {"codigo": codigo, "cantidad": entrada["cantidad"]}
                for codigo, entrada in self.cart.items()
            ],
        }
        try:
            pedido = await self.run_blocking(
                self.store.crear_pedido, self.vendor, payload
            )
            self.cart = {}
            self.checkout.update({
                "cliente": "", "ciudad": "", "notas": "",
                "condicion": "Contado", "tipo_doc": "Nota de entrega",
            })
            self.orders_loaded = False
            self.toast(
                f"Pedido {pedido.get('pedido_id', '')} enviado.", "success"
            )
            self.tab = "pedidos"
            if self.nav_host is not None:
                self.nav_host.content = self._nav()
            await self.load_orders_async(True)
        except Exception as exc:
            self.toast(str(exc), "error")
        finally:
            self.order_sending = False
            if self.tab == "carrito":
                self.refresh_view()

    # ------------------------------------------------------------------
    # Pedidos y tasa
    # ------------------------------------------------------------------

    async def load_orders_async(self, force: bool = False):
        if self.orders_loading:
            return
        if self.orders_loaded and not force:
            self.refresh_view()
            return
        self.orders_loading = True
        self.orders_error = ""
        self.refresh_view()
        try:
            items = await self.run_blocking(
                self.store.listar_pedidos, self.vendor.get("codigo", "")
            )
            resumen = await self.run_blocking(
                self.store.resumen_vendedor, self.vendor.get("codigo", "")
            )
            self.orders_items = items or []
            self.orders_summary = resumen or {}
            self.orders_loaded = True
        except Exception as exc:
            self.orders_error = (
                "No se pudo cargar el historial desde Atlas."
                if not str(exc) else str(exc)
            )
        finally:
            self.orders_loading = False
        self.refresh_view()

    async def refresh_rate_async(self):
        try:
            datos = await self.run_blocking(rate.consultar_tasa, True)
            self.rate = float(datos.get("tasa", 0) or 0)
            self.toast(
                f"Tasa BCV: {ui.bolivares(self.rate)} / $", "success"
            )
            self.refresh_view()
        except Exception:
            self.toast("No se pudo actualizar la tasa BCV.", "error")

    def show_order_detail(self, pedido):
        show_order_detail(self, pedido)


def main(page: ft.Page):
    page.title = "Mayorix · Vendedor"
    page.bgcolor = ui.BG
    page.padding = 0
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(
        use_material3=True,
        color_scheme=ft.ColorScheme(
            primary=ui.TEAL,
            secondary=ui.ORANGE,
            surface=ui.WHITE,
            on_surface=ui.INK,
            outline=ui.BORDER,
        ),
    )
    app = VendedorApp(page)
    if app.store.configurado:
        app.iniciar_sesion_o_login()
    else:
        app.show_setup()


if __name__ == "__main__":
    puerto = int(os.getenv("MAYORIX_WEB_PORT", "0") or 0)
    ft.run(
        main,
        assets_dir=str(Path(__file__).parent / "assets"),
        port=puerto,
    )
