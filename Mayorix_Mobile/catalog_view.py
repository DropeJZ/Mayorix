"""Catálogo móvil de repuestos en vivo."""

from __future__ import annotations

import flet as ft

import ui_mobile as ui


def catalog_view(app) -> ft.Control:
    buscador = ui.text_field(
        "Buscar código, descripción o marca…",
        value=app.catalog_q,
        on_change=lambda e: app.on_catalog_search(e.control.value),
    )

    resultados = []
    if app.catalog_loading:
        resultados.append(ui.loader("Consultando catálogo…"))
    elif app.catalog_error:
        resultados.append(
            ui.error_state(app.catalog_error,
                           lambda e: app.page.run_task(app.load_catalog, True))
        )
    elif not app.catalog_items:
        resultados.append(
            ui.empty_state(
                "Sin repuestos para esta búsqueda." if app.catalog_q
                else "El catálogo está vacío.",
                ft.Icons.SEARCH_OFF if app.catalog_q
                else ft.Icons.INVENTORY_2_OUTLINED,
                "Prueba con otro código, marca o descripción."
                if app.catalog_q else "El administrador aún no ha cargado inventario.",
            )
        )
    else:
        for item in app.catalog_items:
            resultados.append(_fila_repuesto(app, item))

    if app.catalog_items and not app.catalog_loading:
        cargados = len(app.catalog_items)
        if cargados < app.catalog_total:
            resultados.append(
                ft.Container(
                    content=ui.secondary_button(
                        f"Cargar más ({cargados} de {app.catalog_total})",
                        ft.Icons.EXPAND_MORE,
                        lambda e: app.page.run_task(app.load_catalog, False),
                    ),
                    padding=ft.Padding.only(top=6, bottom=14),
                )
            )
        else:
            resultados.append(
                ft.Container(
                    content=ui.txt(
                        f"{cargados} "
                        f"{'repuesto' if cargados == 1 else 'repuestos'} · "
                        "fin del catálogo",
                        10, ui.MUTED_2, align=ft.TextAlign.CENTER,
                    ),
                    padding=ft.Padding.only(top=6, bottom=14),
                )
            )

    tasa = (
        ui.txt(f"Tasa BCV · {ui.bolivares(app.rate)} / $", 9.5, ui.MUTED)
        if app.rate else
        ui.txt("Tasa BCV no disponible", 9.5, ui.ORANGE)
    )

    return ft.Column(
        [
            ft.Container(
                content=ft.Column(
                    [
                        ui.section_title(
                            "Catálogo",
                            f"{app.catalog_total} "
                            f"{'repuesto' if app.catalog_total == 1 else 'repuestos'} "
                            "en MongoDB",
                            trailing=ft.IconButton(
                                icon=ft.Icons.REFRESH,
                                icon_size=19,
                                icon_color=ui.MUTED,
                                tooltip="Actualizar catálogo",
                                on_click=lambda e: app.page.run_task(
                                    app.load_catalog, True
                                ),
                            ),
                        ),
                        tasa,
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Icon(ft.Icons.SEARCH, size=18,
                                            color=ui.MUTED),
                                    buscador,
                                ],
                                spacing=7,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            bgcolor=ui.WHITE,
                            border=ft.Border.all(1, ui.BORDER),
                            border_radius=13,
                            padding=ft.Padding.symmetric(horizontal=11),
                        ),
                    ],
                    spacing=9,
                ),
                padding=ft.Padding.only(left=14, right=14, top=12, bottom=4),
            ),
            ft.Column(resultados, spacing=8, scroll=ft.ScrollMode.AUTO,
                      expand=True),
        ],
        spacing=0,
        expand=True,
    )


def _fila_repuesto(app, item):
    precio = float(item.get("precio", 0) or 0)
    precio_bs = precio * float(app.rate or 0)
    en_carrito = int((app.cart.get(item.get("codigo", "")) or {}).get(
        "cantidad", 0
    ))
    marca = item.get("marca", "") or "Sin marca"
    codigo = item.get("codigo", "")

    detalle = ft.Column(
        [
            ft.Row(
                [
                    ui.pill(codigo, ui.MUTED, ui.SOFT, size=8.5),
                    ui.txt(marca, 9, ui.MUTED_2, max_lines=1, expand=True),
                ],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ui.txt(item.get("descripcion", "—"), 13.5, ui.INK, ui.W_600,
                   max_lines=2),
        ],
        spacing=4,
        expand=True,
    )

    precios = ft.Column(
        [
            ui.txt(ui.money(precio), 14, ui.INK, ui.W_700,
                   align=ft.TextAlign.RIGHT),
            ui.txt(ui.bolivares(precio_bs), 9.5, ui.MUTED,
                   align=ft.TextAlign.RIGHT),
            ui.txt(f"En carrito: {en_carrito}" if en_carrito else "",
                   8.5, ui.TEAL, ui.W_600, align=ft.TextAlign.RIGHT),
        ],
        spacing=1,
        horizontal_alignment=ft.CrossAxisAlignment.END,
    )

    agregar = ft.Container(
        content=ft.Icon(ft.Icons.ADD, size=21, color=ui.WHITE),
        width=42, height=42,
        bgcolor=ui.TEAL,
        border_radius=12,
        alignment=ft.Alignment.CENTER,
        on_click=lambda e, d=item: app.add_to_cart(d),
        tooltip="Agregar al carrito",
        ink=True,
    )

    return ui.card(
        ft.Row(
            [detalle, precios, agregar],
            spacing=9,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=12,
    )
