"""Historial de pedidos del vendedor."""

from __future__ import annotations

import flet as ft

import ui_mobile as ui


def orders_view(app) -> ft.Control:
    cuerpo = []
    if app.orders_loading:
        cuerpo.append(ui.loader("Cargando pedidos…"))
    elif app.orders_error:
        cuerpo.append(
            ui.error_state(
                app.orders_error,
                lambda e: app.page.run_task(app.load_orders_async, True),
            )
        )
    elif not app.orders_items:
        cuerpo.append(
            ui.empty_state(
                "Aún no tienes pedidos enviados.",
                ft.Icons.RECEIPT_LONG_OUTLINED,
                "Los pedidos que envíes desde el carrito aparecerán aquí.",
            )
        )
    else:
        for pedido in app.orders_items:
            cuerpo.append(_tarjeta_pedido(app, pedido))

    resumen = app.orders_summary or {}
    por_estado = resumen.get("por_estado", {})
    pendientes = int(por_estado.get("Pendiente", 0)) + int(
        por_estado.get("En revisión", 0)
    )

    encabezado = ui.section_title(
        "Pedidos",
        "Historial de la red comercial",
        trailing=ft.IconButton(
            icon=ft.Icons.REFRESH,
            icon_size=19,
            icon_color=ui.MUTED,
            tooltip="Actualizar historial",
            on_click=lambda e: app.page.run_task(app.load_orders_async, True),
        ),
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

    return ft.Column(
        [
            ft.Container(
                content=ft.Column(
                    [
                        encabezado,
                        metricas,
                        ui.txt(
                            "Desliza para ver todos los pedidos. Toca uno para "
                            "consultar el detalle.",
                            9.5, ui.MUTED, max_lines=2,
                        ),
                    ],
                    spacing=9,
                ),
                padding=ft.Padding.only(left=14, right=14, top=12, bottom=8),
            ),
            ft.Container(
                content=ft.Column(
                    cuerpo,
                    spacing=8,
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                ),
                padding=ft.Padding.only(left=14, right=14, bottom=14),
                expand=True,
            ),
        ],
        spacing=0,
        expand=True,
    )


def _tarjeta_pedido(app, pedido):
    total = float(pedido.get("total", 0) or 0)
    total_bs = float(pedido.get("total_ves", 0) or 0) or total * float(
        app.rate or 0
    )
    estado = pedido.get("estado", "Pendiente")
    items = pedido.get("items", []) or []
    unidades = sum(int(i.get("cantidad", 0) or 0) for i in items)
    lineas = len(items)
    resumen_items = (
        f"{lineas} {'línea' if lineas == 1 else 'líneas'} · "
        f"{unidades} {'unidad' if unidades == 1 else 'unidades'}"
    )
    tarjeta = ui.card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ui.txt(pedido.get("pedido_id", "—"), 11.5,
                                       ui.INK, ui.W_700),
                                ui.txt(ui.fecha_corta(pedido.get("fecha")),
                                       9.5, ui.MUTED),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        ui.status_pill(estado),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                ft.Row(
                    [
                        ft.Icon(ft.Icons.STORE_OUTLINED, size=14,
                                color=ui.MUTED),
                        ui.txt(
                            pedido.get("cliente_nombre")
                            or "Cliente sin registrar",
                            11, ui.INK_SOFT, ui.W_500, max_lines=1,
                            expand=True,
                        ),
                    ],
                    spacing=5,
                ),
                ft.Row(
                    [
                        ui.txt(resumen_items, 9.5, ui.MUTED),
                        ft.Container(expand=True),
                        ft.Column(
                            [
                                ui.txt(ui.money(total), 13, ui.INK, ui.W_700,
                                       align=ft.TextAlign.RIGHT),
                                ui.txt(ui.bolivares(total_bs), 9, ui.MUTED,
                                       align=ft.TextAlign.RIGHT),
                            ],
                            spacing=0,
                            horizontal_alignment=ft.CrossAxisAlignment.END,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=8,
        ),
        padding=12,
    )
    tarjeta.on_click = lambda e, p=pedido: app.show_order_detail(p)
    tarjeta.ink = True
    return tarjeta


def show_order_detail(app, pedido):
    items = pedido.get("items", []) or []
    filas = []
    for item in items:
        filas.append(
            ft.Row(
                [
                    ft.Column(
                        [
                            ui.txt(item.get("descripcion")
                                   or item.get("producto_id", "Repuesto"),
                                   11, ui.INK, ui.W_500, max_lines=2),
                            ui.txt(
                                f"{item.get('cantidad', 0)} × "
                                f"{ui.money(item.get('precio', 0))}",
                                9, ui.MUTED,
                            ),
                        ],
                        spacing=1,
                        expand=True,
                    ),
                    ui.txt(ui.money(item.get("importe", 0)), 11, ui.INK,
                           ui.W_600),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
    total = float(pedido.get("total", 0) or 0)
    total_bs = float(pedido.get("total_ves", 0) or 0) or total * float(
        app.rate or 0
    )
    contenido = ft.Column(
        [
            ft.Row(
                [
                    ui.status_pill(pedido.get("estado", "Pendiente")),
                    ft.Container(expand=True),
                    ui.txt(ui.fecha_corta(pedido.get("fecha")), 9.5, ui.MUTED),
                ]
            ),
            ui.txt(
                pedido.get("cliente_nombre") or "Cliente sin registrar",
                14, ui.INK, ui.W_600,
            ),
            ui.txt(
                f"{pedido.get('condicion', 'Contado')} · "
                f"{pedido.get('tipo_doc', 'Nota de entrega')}",
                9.5, ui.MUTED,
            ),
            ft.Divider(height=1, color=ui.BORDER),
            ft.Column(filas or [ui.txt("Sin líneas.", 10, ui.MUTED)],
                      spacing=7),
            ft.Divider(height=1, color=ui.BORDER),
            ft.Row(
                [
                    ui.txt("Total USD", 11, ui.MUTED),
                    ft.Container(expand=True),
                    ui.txt(ui.money(total), 13, ui.INK, ui.W_700),
                ]
            ),
            ft.Row(
                [
                    ui.txt("Total Bs.", 11, ui.MUTED),
                    ft.Container(expand=True),
                    ui.txt(ui.bolivares(total_bs), 12, ui.TEAL_DARK, ui.W_700),
                ]
            ),
        ],
        spacing=8,
        scroll=ft.ScrollMode.AUTO,
    )
    dialogo = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            [
                ft.Icon(ft.Icons.RECEIPT_LONG_OUTLINED, size=20,
                        color=ui.TEAL),
                ui.txt(pedido.get("pedido_id", "Pedido"), 15, ui.INK, ui.W_700),
            ],
            spacing=8,
        ),
        content=ft.Container(content=contenido, width=330, height=360),
        actions=[
            ft.TextButton(
                content=ui.txt("Cerrar", 12, ui.TEAL, ui.W_600),
                on_click=lambda e: app.page.pop_dialog(),
            )
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    app.page.show_dialog(dialogo)
