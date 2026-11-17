"""Carrito y toma de pedidos del vendedor."""

from __future__ import annotations

import flet as ft

import ui_mobile as ui


def cart_view(app) -> ft.Control:
    filas = []
    for codigo, entrada in app.cart.items():
        item = entrada["doc"]
        cantidad = int(entrada["cantidad"])
        precio = float(item.get("precio", 0) or 0)
        importe = precio * cantidad
        filas.append(_fila_carrito(app, item, cantidad, importe))

    subtotal, iva, total = app.cart_totals()
    total_bs = total * float(app.rate or 0)

    if not app.cart:
        cuerpo = ui.empty_state(
            "Tu carrito está vacío.",
            ft.Icons.SHOPPING_CART_OUTLINED,
            "Abre el catálogo y agrega repuestos para armar el pedido.",
        )
    else:
        cuerpo = ft.Column(filas, spacing=8)

    resumen = ui.card(
        ft.Column(
            [
                _linea("Subtotal", ui.money(subtotal)),
                _linea(
                    "IVA (16%)" if app.checkout["tipo_doc"] == "Factura fiscal"
                    else "IVA",
                    ui.money(iva),
                ),
                ft.Divider(height=1, color=ui.BORDER),
                _linea("Total USD", ui.money(total), fuerte=True),
                _linea("Total Bs.", ui.bolivares(total_bs), color=ui.TEAL_DARK),
                ui.txt(
                    f"Tasa BCV aplicada: {ui.bolivares(app.rate)} / $"
                    if app.rate else "Tasa BCV no disponible",
                    9.5, ui.MUTED if app.rate else ui.ORANGE,
                ),
            ],
            spacing=6,
        ),
        padding=14,
    )

    cliente = ui.text_field(
        "Nombre del cliente o negocio",
        value=app.checkout["cliente"],
        on_change=lambda e: app.checkout.update(
            {"cliente": e.control.value}
        ),
    )
    ciudad = ui.text_field(
        "Ciudad (opcional)",
        value=app.checkout["ciudad"],
        on_change=lambda e: app.checkout.update(
            {"ciudad": e.control.value}
        ),
    )
    condicion = ft.Dropdown(
        value=app.checkout["condicion"],
        options=[ft.DropdownOption(key="Contado", text="Contado"),
                 ft.DropdownOption(key="Crédito 30 días",
                                   text="Crédito 30 días")],
        on_select=lambda e: app.checkout.update(
            {"condicion": e.control.value}
        ),
        border=ft.InputBorder.NONE,
        text_size=13,
        dense=True,
        expand=True,
        content_padding=ft.Padding.symmetric(horizontal=8, vertical=4),
    )
    tipo_doc = ft.Dropdown(
        value=app.checkout["tipo_doc"],
        options=[ft.DropdownOption(key="Nota de entrega",
                                   text="Nota de entrega"),
                 ft.DropdownOption(key="Factura fiscal",
                                   text="Factura fiscal (+16% IVA)")],
        on_select=lambda e: app.checkout.update(
            {"tipo_doc": e.control.value}
        ),
        border=ft.InputBorder.NONE,
        text_size=13,
        dense=True,
        expand=True,
        content_padding=ft.Padding.symmetric(horizontal=8, vertical=4),
    )
    notas = ui.text_field(
        "Nota para el administrador (opcional)",
        value=app.checkout["notas"],
        on_change=lambda e: app.checkout.update(
            {"notas": e.control.value}
        ),
    )
    app.cart_fields = {
        "cliente": cliente,
        "ciudad": ciudad,
        "condicion": condicion,
        "tipo_doc": tipo_doc,
        "notas": notas,
    }

    formulario = ui.card(
        ft.Column(
            [
                ui.txt("Datos del pedido", 14, ui.INK, ui.W_600),
                ui.field_shell("CLIENTE", cliente),
                ui.field_shell("CIUDAD", ciudad),
                ui.field_shell("CONDICIÓN DE PAGO", condicion),
                ui.field_shell("DOCUMENTO", tipo_doc),
                ui.field_shell("NOTA", notas),
                ui.action_button(
                    "Enviando pedido…" if app.order_sending else "Enviar pedido",
                    ft.Icons.SEND,
                    lambda e: app.page.run_task(app.submit_order_async),
                    disabled=app.order_sending or not app.cart,
                ),
                ui.txt(
                    "El pedido quedará Pendiente hasta que la administración "
                    "lo revise.",
                    9.5, ui.MUTED, max_lines=2,
                ),
            ],
            spacing=10,
        ),
        padding=14,
    )

    encabezado = ui.section_title(
        "Carrito",
        (f"{len(app.cart)} "
         f"{'línea' if len(app.cart) == 1 else 'líneas'} · "
         f"{sum(x['cantidad'] for x in app.cart.values())} "
         f"{'unidad' if sum(x['cantidad'] for x in app.cart.values()) == 1 else 'unidades'}")
        if app.cart else "Arma el pedido del cliente",
        trailing=ui.pill(ui.money(total), ui.TEAL, ui.TEAL_SOFT),
    )

    return ft.Column(
        [
            ft.Container(
                content=ft.Column(
                    [
                        encabezado,
                        ui.txt(
                            "Precios en USD · conversión automática a bolívares",
                            9.5, ui.MUTED,
                        ),
                    ],
                    spacing=6,
                ),
                padding=ft.Padding.only(left=14, right=14, top=12, bottom=8),
            ),
            ft.Container(
                content=ft.Column(
                    [
                        cuerpo,
                        resumen if app.cart else ft.Container(),
                        formulario if app.cart else ft.Container(),
                        ft.Container(height=10),
                    ],
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


def _linea(label, valor, fuerte=False, color=ui.INK):
    return ft.Row(
        [
            ui.txt(label, 11, ui.MUTED if not fuerte else ui.INK,
                   ui.W_600 if fuerte else ui.W_500),
            ft.Container(expand=True),
            ui.txt(valor, 12, color, ui.W_700 if fuerte else ui.W_500),
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _fila_carrito(app, item, cantidad, importe):
    codigo = item.get("codigo", "")
    controles = ft.Row(
        [
            _boton_cantidad(ft.Icons.REMOVE, lambda e: app.change_qty(codigo, -1)),
            ui.txt(str(cantidad), 12, ui.INK, ui.W_700,
                   align=ft.TextAlign.CENTER),
            _boton_cantidad(ft.Icons.ADD, lambda e: app.change_qty(codigo, 1)),
            ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE,
                icon_size=17,
                icon_color=ui.MUTED,
                tooltip="Quitar",
                on_click=lambda e: app.remove_item(codigo),
            ),
        ],
        spacing=3,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    return ui.card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ui.pill(codigo, ui.MUTED, ui.SOFT, size=8.5),
                                ui.txt(item.get("descripcion", "—"), 12.5,
                                       ui.INK, ui.W_600, max_lines=2),
                                ui.txt(item.get("marca", "") or "Sin marca",
                                       9, ui.MUTED_2, max_lines=1),
                            ],
                            spacing=3,
                            expand=True,
                        ),
                        ft.Column(
                            [
                                ui.txt(ui.money(importe), 13, ui.INK, ui.W_700,
                                       align=ft.TextAlign.RIGHT),
                                ui.txt(ui.bolivares(importe * app.rate), 9,
                                       ui.MUTED, align=ft.TextAlign.RIGHT),
                            ],
                            spacing=1,
                            horizontal_alignment=ft.CrossAxisAlignment.END,
                        ),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                ft.Row(
                    [
                        ui.txt("Cantidad", 9.5, ui.MUTED),
                        ft.Container(expand=True),
                        controles,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=8,
        ),
        padding=11,
    )


def _boton_cantidad(icono, on_click):
    return ft.Container(
        content=ft.Icon(icono, size=16, color=ui.TEAL),
        width=32, height=32,
        bgcolor=ui.TEAL_SOFT,
        border_radius=8,
        alignment=ft.Alignment.CENTER,
        on_click=on_click,
        ink=True,
    )
