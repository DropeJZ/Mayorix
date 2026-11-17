"""
Mayorix · Pedidos recibidos
===========================
Bandeja de la red externa: auditoría, aprobación, rechazo y despacho de los
pedidos que ingresan a Mayor Disluda. Los cambios de estado se persisten en
la colección `pedidos` de MongoDB.
"""

from __future__ import annotations

import flet as ft

import data
from . import ui


def _pid(pedido) -> str:
    return str(pedido.get("pedido_id") or pedido.get("id") or "")


def _es_mes_actual(fecha: str) -> bool:
    return str(fecha).startswith(f"{data.HOY.year:04d}-{data.HOY.month:02d}")


def _cliente(pedido) -> dict:
    encontrado = data.cliente(pedido.get("cliente_id", "")) or {}
    if encontrado:
        return encontrado
    return {
        "negocio": pedido.get("cliente_nombre") or "Cliente sin registrar",
        "ciudad": pedido.get("cliente_ciudad", ""),
        "tipo": pedido.get("cliente_tipo", ""),
    }


def _vendedor(pedido) -> dict:
    encontrado = data.vendedor(pedido.get("vendedor_id", "")) or {}
    if encontrado:
        return encontrado
    return {
        "nombre": pedido.get("vendedor_nombre") or "Sin asignar",
        "zona": pedido.get("vendedor_zona", ""),
    }


def _sincronizar_estados(pedidos: list[dict]) -> None:
    """Sincroniza el estado de los pedidos para las m?tricas del panel."""
    por_id = {p["id"]: p for p in data.PEDIDOS}
    for pedido in pedidos:
        local = por_id.get(_pid(pedido))
        if local:
            local["estado"] = pedido.get("estado", local["estado"])


def sincronizar_pedidos(db) -> int:
    """Aplica los estados guardados en MongoDB sobre la capa de dashboard."""
    try:
        pedidos = db.listar_pedidos()
    except Exception:
        return 0
    _sincronizar_estados(pedidos)
    return len(pedidos)


def pedidos_view(app) -> ft.Control:
    db = app.db
    estado = {"estado": "Todos", "doc": "Todos", "q": ""}
    rows_host = ft.Column(spacing=0)
    chips_host = ft.Row(spacing=6, wrap=True)
    footer_label = ui.txt("", 10.5, ui.MUTED)
    footer_total = ui.txt("", 10.5, ui.INK, ui.W_600)

    try:
        pedidos = db.listar_pedidos()
        _sincronizar_estados(pedidos)
        error_db = ""
    except Exception as exc:
        pedidos = [
            {**p, "pedido_id": p.get("id", "")} for p in data.PEDIDOS
        ]
        error_db = str(exc)

    if db.conectado:
        status_pill = ui.pill(db.estado_texto, ui.TEAL, ui.TEAL_SOFT,
                             icon=ft.Icons.CLOUD_DONE_OUTLINED, size=9.5)
    else:
        status_pill = ui.pill(db.estado_texto, ui.ORANGE, ui.ORANGE_SOFT,
                             icon=ft.Icons.CLOUD_OFF_OUTLINED, size=9.5)

    def recargar(update=True):
        nonlocal pedidos, error_db
        try:
            pedidos = db.listar_pedidos()
            _sincronizar_estados(pedidos)
            error_db = ""
        except Exception as exc:
            error_db = str(exc)
        render_chips()
        render(update=update)

    def cambiar_estado(pedido, nuevo):
        pedido_id = _pid(pedido)
        try:
            db.actualizar_estado_pedido(pedido_id, nuevo)
        except Exception as exc:
            app.toast(f"No se pudo actualizar el pedido en MongoDB: {exc}", "error")
            return
        pedido["estado"] = nuevo
        for local in data.PEDIDOS:
            if local["id"] == pedido_id:
                local["estado"] = nuevo
        titulos = {
            "En revisión": "Pedido enviado a revisión",
            "Aprobado": "Pedido aprobado",
            "En despacho": "Pedido en despacho",
            "Entregado": "Pedido entregado",
            "Rechazado": "Pedido rechazado",
        }
        data.registrar_actividad(
            "pedido", titulos.get(nuevo, f"Pedido {nuevo.lower()}"),
            f"{_cliente(pedido).get('negocio', 'Cliente')} · {pedido_id}",
            pedido.get("total", 0), nuevo,
        )
        data.recalcular_ventas()
        app.refresh()
        app.toast(f"{pedido_id} actualizado a “{nuevo}”.",
                  "warning" if nuevo == "Rechazado" else "success")

    def menu_acciones(pedido):
        items = [
            ft.PopupMenuItem(
                content=ui.txt("Ver desglose", 12),
                icon=ft.Icons.VISIBILITY_OUTLINED,
                on_click=lambda e, p=pedido: abrir_detalle(p),
            )
        ]
        siguientes = {
            "Pendiente": [
                ("Iniciar revisión", "En revisión", ft.Icons.VISIBILITY_OUTLINED),
                ("Aprobar pedido", "Aprobado", ft.Icons.CHECK),
            ],
            "En revisión": [
                ("Aprobar pedido", "Aprobado", ft.Icons.CHECK),
            ],
            "Aprobado": [
                ("Pasar a despacho", "En despacho",
                 ft.Icons.LOCAL_SHIPPING_OUTLINED),
            ],
            "En despacho": [
                ("Marcar entregado", "Entregado", ft.Icons.DONE_ALL),
            ],
        }
        for etiqueta, nuevo, icono in siguientes.get(pedido.get("estado"), []):
            items.append(
                ft.PopupMenuItem(
                    content=ui.txt(etiqueta, 12),
                    icon=icono,
                    on_click=lambda e, p=pedido, n=nuevo: cambiar_estado(p, n),
                )
            )
        if pedido.get("estado") in ("Pendiente", "En revisión"):
            items.append(
                ft.PopupMenuItem(
                    content=ui.txt("Rechazar pedido", 12, ui.RED),
                    icon=ft.Icons.CANCEL_OUTLINED,
                    on_click=lambda e, p=pedido: cambiar_estado(p, "Rechazado"),
                )
            )
        return ft.PopupMenuButton(
            items=items,
            icon=ft.Icons.MORE_HORIZ,
            icon_size=18,
            icon_color=ui.MUTED,
            tooltip="Más acciones",
            style=ft.ButtonStyle(padding=5, shape=ft.RoundedRectangleBorder(radius=6)),
        )

    def fila_pedido(pedido):
        cliente = _cliente(pedido)
        vendedor = _vendedor(pedido)
        acciones = []
        if pedido.get("estado") in ("Pendiente", "En revisión"):
            acciones.append(
                ui.text_button(
                    "Aprobar", ft.Icons.CHECK,
                    lambda e, p=pedido: cambiar_estado(p, "Aprobado"),
                    size=10.5, height=28,
                )
            )
        acciones.append(menu_acciones(pedido))
        return ui.table_row(
            [
                ui.cell(
                    ft.Column(
                        [
                            ui.txt(_pid(pedido), 11.5, ui.INK, ui.W_700),
                            ui.txt(ui.fecha_corta(pedido.get("fecha", "")),
                                   9.5, ui.MUTED, ui.W_400),
                        ],
                        spacing=1,
                    ),
                    2,
                ),
                ui.cell(
                    ft.Column(
                        [
                            ui.txt(cliente.get("negocio", "Cliente"), 11.5, ui.INK,
                                   ui.W_600, max_lines=1),
                            ui.txt(cliente.get("ciudad", ""), 9.5, ui.MUTED,
                                   ui.W_400),
                        ],
                        spacing=1,
                    ),
                    3.2,
                ),
                ui.cell(
                    ft.Row(
                        [
                            ui.avatar(vendedor.get("nombre", "?"),
                                      vendedor.get("color", ui.MUTED), 24, 9),
                            ui.txt(vendedor.get("nombre", "Sin asignar"), 10.5,
                                   "#475569", ui.W_500, max_lines=1),
                        ],
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    2.4,
                ),
                ui.cell(ui.doc_pill(pedido.get("tipo_doc", "")), 2.3),
                ui.cell(
                    ft.Column(
                        [
                            ui.txt(ui.money(pedido.get("total", 0), 2), 11.5,
                                   ui.INK, ui.W_600),
                            ui.txt(pedido.get("condicion", ""), 9.5, ui.MUTED,
                                   ui.W_400),
                        ],
                        spacing=1,
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                    ),
                    2.2,
                    ui.ALIGN_RIGHT,
                ),
                ui.cell(ui.estado_pedido_pill(pedido.get("estado", "Pendiente")), 1.8),
                ui.cell(
                    ft.Row(
                        acciones,
                        spacing=2,
                        tight=True,
                        alignment=ft.MainAxisAlignment.END,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    2.1,
                    ui.ALIGN_RIGHT,
                ),
            ],
            on_click=lambda e, p=pedido: abrir_detalle(p),
            padding_v=9,
        )

    def render_chips():
        conteos = {
            nombre: len([p for p in pedidos if p.get("estado") == nombre])
            for nombre in ui.ESTADOS_PEDIDO
        }
        opciones = ["Todos"] + list(ui.ESTADOS_PEDIDO.keys())
        chips_host.controls = [
            ui.filter_chip(
                opcion,
                estado["estado"] == opcion,
                lambda e, valor=opcion: seleccionar_estado(valor),
                count=len(pedidos) if opcion == "Todos" else conteos.get(opcion, 0),
            )
            for opcion in opciones
        ]

    def seleccionar_estado(valor):
        estado["estado"] = valor
        render_chips()
        render()
        app.page.update()

    def render(update=False):
        q = estado["q"].strip().lower()
        filtrados = []
        for pedido in pedidos:
            cliente = _cliente(pedido)
            vendedor = _vendedor(pedido)
            coincide_estado = (
                estado["estado"] == "Todos" or pedido.get("estado") == estado["estado"]
            )
            coincide_doc = (
                estado["doc"] == "Todos" or pedido.get("tipo_doc") == estado["doc"]
            )
            coincide_q = (
                q in _pid(pedido).lower()
                or q in cliente.get("negocio", "").lower()
                or q in vendedor.get("nombre", "").lower()
            )
            if coincide_estado and coincide_doc and coincide_q:
                filtrados.append(pedido)
        rows_host.controls = [fila_pedido(p) for p in filtrados] or [
            ui.empty_state("No hay pedidos que coincidan con los filtros.",
                           ft.Icons.REQUEST_QUOTE_OUTLINED)
        ]
        total = sum(float(p.get("total", 0) or 0) for p in filtrados)
        footer_label.value = (
            f"{len(filtrados)} pedidos · "
            f"{len([p for p in filtrados if p.get('tipo_doc') == 'Factura fiscal'])} "
            "facturas fiscales"
        )
        footer_total.value = f"Total filtrado: {ui.money(total, 2)}"
        if update:
            app.page.update()

    def buscar(e):
        estado["q"] = e.control.value
        render(update=True)

    def filtrar_doc(e):
        estado["doc"] = e.control.value
        render(update=True)

    def abrir_detalle(pedido):
        _dialogo_pedido(app, pedido, cambiar_estado)

    por_revisar = [p for p in pedidos
                   if p.get("estado") in ("Pendiente", "En revisión")]
    en_despacho = [p for p in pedidos if p.get("estado") == "En despacho"]
    facturado = [p for p in pedidos
                 if p.get("tipo_doc") == "Factura fiscal"
                 and p.get("estado") != "Rechazado"
                 and _es_mes_actual(p.get("fecha", ""))]

    render_chips()
    render()

    toolbar = ft.Column(
        [
            ft.Row(
                [
                    ui.search_input("Buscar pedido, cliente o vendedor…", buscar,
                                    width=300),
                    ui.toolbar_dropdown(
                        [
                            ("Todos", "Todos los documentos"),
                            ("Factura fiscal", "Factura fiscal"),
                            ("Nota de entrega", "Nota de entrega"),
                        ],
                        estado["doc"], filtrar_doc, width=200,
                    ),
                    ft.Container(expand=True),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            chips_host,
        ],
        spacing=9,
    )

    footer = ui.table_footer(
        ft.Row(
            [footer_label, ft.Container(expand=True), footer_total],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
    )

    tabla = ui.table_container(
        [
            {"label": "Pedido", "flex": 2},
            {"label": "Cliente", "flex": 3.2},
            {"label": "Vendedor", "flex": 2.4},
            {"label": "Documento", "flex": 2.3},
            {"label": "Total USD", "flex": 2.2, "align": ui.ALIGN_RIGHT},
            {"label": "Estado", "flex": 1.8},
            {"label": "Acciones", "flex": 2.1, "align": ui.ALIGN_RIGHT},
        ],
        rows_host,
        footer,
    )

    stats = ft.Row(
        [
            ui.mini_stat("Por revisar", str(len(por_revisar)),
                         ui.money(sum(p.get("total", 0) for p in por_revisar), 2),
                         ft.Icons.VISIBILITY_OUTLINED, ui.ORANGE, ui.ORANGE_SOFT),
            ui.mini_stat("En despacho", str(len(en_despacho)),
                         ui.money(sum(p.get("total", 0) for p in en_despacho), 2),
                         ft.Icons.LOCAL_SHIPPING_OUTLINED, ui.PURPLE, ui.PURPLE_SOFT),
            ui.mini_stat("Facturado del mes",
                         ui.compacto(sum(p.get("total", 0) for p in facturado)),
                         f"{len(facturado)} facturas fiscales · IVA 16% incluido",
                         ft.Icons.RECEIPT_LONG_OUTLINED, ui.TEAL, ui.TEAL_SOFT),
        ],
        spacing=14,
    )

    contenido = [
        ui.page_header(
            "Pedidos recibidos",
            "Bandeja de pedidos de la red externa.",
            [
                ui.secondary_button("Actualizar", ft.Icons.REFRESH,
                                    lambda e: recargar(update=True)),
                ui.secondary_button("Exportar", ft.Icons.DOWNLOAD,
                                    lambda e: app.toast(
                                        "Bandeja de pedidos exportada (demo).",
                                        "success")),
            ],
            eyebrow="MONGODB · GESTIÓN DE PEDIDOS",
        ),
        stats,
    ]
    if error_db:
        contenido.append(ui.info_box(
            f"No se pudieron consultar los pedidos en MongoDB: {error_db}",
            ui.RED, ui.RED_SOFT, "#FECACA", ft.Icons.ERROR_OUTLINE,
        ))
    elif not db.conectado:
        contenido.append(ui.info_box(
            f"{db.detalle_estado} Los cambios de estado se guardan en el respaldo "
            "local mientras MongoDB no esté disponible.",
            ui.ORANGE, ui.ORANGE_SOFT, ui.ORANGE_BORDER, ft.Icons.CLOUD_OFF_OUTLINED,
        ))
    contenido.extend([
        ft.Row([status_pill, ft.Container(expand=True)],
               vertical_alignment=ft.CrossAxisAlignment.CENTER),
        toolbar,
        tabla,
    ])
    return ft.Column(contenido, spacing=16)


# ---------------------------------------------------------------------------
# Detalle del pedido
# ---------------------------------------------------------------------------


def _tabla_items(pedido, moneda):
    filas = ft.Column(spacing=0)
    for item in pedido.get("items", []):
        producto = data.producto(item.get("producto_id", "")) or {}
        nombre = (producto.get("nombre") or item.get("descripcion")
                  or item.get("producto_id") or "Repuesto")
        marca = producto.get("marca", "")
        filas.controls.append(
            ui.table_row(
                [
                    ui.cell(
                        ft.Column(
                            [
                                ui.txt(nombre, 10.5, ui.INK, ui.W_500, max_lines=1),
                                ui.txt(marca, 8.5, ui.MUTED, max_lines=1),
                            ],
                            spacing=0,
                        ),
                        4.2,
                    ),
                    ui.cell(ui.txt(str(item.get("cantidad", 0)), 10.5, "#475569",
                                    ui.W_500), 1.2),
                    ui.cell(
                        ui.txt(ui.monto_segun_moneda(item.get("precio", 0), moneda),
                               10.5, "#475569", ui.W_500),
                        1.8, ui.ALIGN_RIGHT,
                    ),
                    ui.cell(
                        ui.txt(ui.monto_segun_moneda(item.get("importe", 0), moneda),
                               10.5, ui.INK, ui.W_600),
                        1.8, ui.ALIGN_RIGHT,
                    ),
                ],
                padding_v=7,
            )
        )
    return ft.Column(
        [
            ui.table_header(
                [
                    {"label": "Producto", "flex": 4.2},
                    {"label": "Cant.", "flex": 1.2},
                    {"label": "Precio", "flex": 1.8, "align": ui.ALIGN_RIGHT},
                    {"label": "Importe", "flex": 1.8, "align": ui.ALIGN_RIGHT},
                ]
            ),
            filas,
        ],
        spacing=0,
    )


def _dialogo_pedido(app, pedido, cambiar_estado):
    cliente = _cliente(pedido)
    vendedor = _vendedor(pedido)
    estado_actual = pedido.get("estado", "Pendiente")
    color, bg, icono = ui.ESTADOS_PEDIDO.get(
        estado_actual, (ui.MUTED, ui.SOFT_2, ft.Icons.CIRCLE))
    moneda = {"modo": "USD"}

    def totales(modo):
        return ft.Column(
            [
                ft.Row(
                    [
                        ui.txt("Subtotal", 10.5, ui.MUTED),
                        ft.Container(expand=True),
                        ui.txt(ui.monto_segun_moneda(pedido.get("subtotal", 0), modo),
                               10.5, ui.INK, ui.W_500),
                    ]
                ),
                ft.Row(
                    [
                        ui.txt("IVA (16%)" if pedido.get("tipo_doc") == "Factura fiscal"
                               else "IVA", 10.5, ui.MUTED),
                        ft.Container(expand=True),
                        ui.txt(ui.monto_segun_moneda(pedido.get("iva", 0), modo),
                               10.5, ui.INK, ui.W_500),
                    ]
                ),
                ft.Divider(height=1, color=ui.BORDER),
                ft.Row(
                    [
                        ui.txt("Total", 12, ui.INK, ui.W_700),
                        ft.Container(expand=True),
                        ui.txt(ui.monto_segun_moneda(pedido.get("total", 0), modo, 2),
                               16, ui.TEAL_DARK, ui.W_700),
                    ]
                ),
                ft.Row(
                    [
                        ui.txt("Condición", 9.5, ui.MUTED),
                        ft.Container(expand=True),
                        ui.txt(pedido.get("condicion", ""), 9.5, ui.INK, ui.W_500),
                    ]
                ),
                ft.Row(
                    [
                        ui.txt("Vencimiento", 9.5, ui.MUTED),
                        ft.Container(expand=True),
                        ui.txt(
                            ui.fecha_corta(pedido.get("vencimiento", ""))
                            if pedido.get("vencimiento") else "Contado",
                            9.5, ui.INK, ui.W_500,
                        ),
                    ]
                ),
            ],
            spacing=5,
        )

    items_host = ft.AnimatedSwitcher(
        content=_tabla_items(pedido, "USD"),
        duration=180,
        reverse_duration=120,
        switch_in_curve=ft.AnimationCurve.EASE_OUT,
        switch_out_curve=ft.AnimationCurve.EASE_IN,
        transition=ft.AnimatedSwitcherTransition.FADE,
    )
    totales_host = ft.AnimatedSwitcher(
        content=totales("USD"),
        duration=180,
        reverse_duration=120,
        switch_in_curve=ft.AnimationCurve.EASE_OUT,
        switch_out_curve=ft.AnimationCurve.EASE_IN,
        transition=ft.AnimatedSwitcherTransition.FADE,
    )
    etiqueta_moneda = ui.txt("Ver en bolívares (VES)", 10.5, ui.TEAL, ui.W_600)

    def alternar(e):
        moneda["modo"] = "VES" if moneda["modo"] == "USD" else "USD"
        etiqueta_moneda.value = (
            "Ver en dólares (USD)" if moneda["modo"] == "VES"
            else "Ver en bolívares (VES)"
        )
        items_host.content = _tabla_items(pedido, moneda["modo"])
        totales_host.content = totales(moneda["modo"])
        app.page.update()

    toggle = ft.OutlinedButton(
        content=ft.Row(
            [ft.Icon(ft.Icons.SWAP_HORIZ, size=14, color=ui.TEAL), etiqueta_moneda],
            spacing=6,
            tight=True,
        ),
        on_click=alternar,
        height=34,
        style=ft.ButtonStyle(
            color=ui.TEAL,
            bgcolor=ui.WHITE,
            side=ft.BorderSide(1, ui.TEAL_BORDER),
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.Padding.symmetric(horizontal=11, vertical=0),
        ),
    )

    resumen = ft.Row(
        [
            ft.Column(
                [
                    ui.txt("Cliente", 9.5, ui.MUTED, ui.W_500),
                    ui.txt(cliente.get("negocio", "—"), 12, ui.INK, ui.W_600,
                           max_lines=1),
                    ui.txt(f"{cliente.get('ciudad', '')} · {cliente.get('tipo', '')}",
                           9.5, ui.MUTED),
                ],
                spacing=2, expand=True,
            ),
            ft.Column(
                [
                    ui.txt("Vendedor", 9.5, ui.MUTED, ui.W_500),
                    ui.txt(vendedor.get("nombre", "—"), 12, ui.INK, ui.W_600,
                           max_lines=1),
                    ui.txt(vendedor.get("zona", ""), 9.5, ui.MUTED),
                ],
                spacing=2, expand=True,
            ),
            ft.Column(
                [
                    ui.txt("Estado", 9.5, ui.MUTED, ui.W_500),
                    ui.pill(estado_actual, color, bg, icon=icono),
                    ui.txt(f"Registrado el {ui.fecha_corta(pedido.get('fecha', ''))}",
                           9, ui.MUTED),
                ],
                spacing=3,
                horizontal_alignment=ft.CrossAxisAlignment.START,
            ),
        ],
        spacing=16,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    def aplicar(nuevo):
        app.close_dialog()
        cambiar_estado(pedido, nuevo)

    acciones = [
        ui.text_button("Cerrar", None, lambda e: app.close_dialog(),
                       color=ui.MUTED, size=11.5),
    ]
    if estado_actual in ("Pendiente", "En revisión"):
        acciones.append(
            ui.text_button("Rechazar", ft.Icons.CANCEL_OUTLINED,
                           lambda e: aplicar("Rechazado"), color=ui.RED, size=11)
        )
        acciones.append(
            ui.primary_button("Aprobar pedido", ft.Icons.CHECK,
                              lambda e: aplicar("Aprobado"), height=38)
        )
    elif estado_actual == "Aprobado":
        acciones.append(
            ui.primary_button("Pasar a despacho", ft.Icons.LOCAL_SHIPPING_OUTLINED,
                              lambda e: aplicar("En despacho"), height=38)
        )
    elif estado_actual == "En despacho":
        acciones.append(
            ui.primary_button("Marcar entregado", ft.Icons.DONE_ALL,
                              lambda e: aplicar("Entregado"), height=38)
        )

    cuerpo = ft.Column(
        [
            resumen,
            ui.info_box(
                "Documento fiscal. El IVA del 16% está incluido."
                if pedido.get("tipo_doc") == "Factura fiscal" else
                "Nota de entrega no fiscal. No genera IVA.",
                ui.TEAL if pedido.get("tipo_doc") == "Factura fiscal" else ui.ORANGE,
                ui.TEAL_SOFT if pedido.get("tipo_doc") == "Factura fiscal"
                else ui.ORANGE_SOFT,
                ui.TEAL_BORDER if pedido.get("tipo_doc") == "Factura fiscal"
                else ui.ORANGE_BORDER,
                ft.Icons.RECEIPT_LONG_OUTLINED,
            ),
            ft.Row(
                [
                    toggle,
                    ui.pill(f"Tasa de referencia: Bs. {data.TASA_VES:,.2f} / $",
                            ui.MUTED, ui.SOFT_2,
                            icon=ft.Icons.CURRENCY_EXCHANGE, size=9.5),
                    ft.Container(expand=True),
                ],
                spacing=9,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            items_host,
            totales_host,
            ui.info_box(
                pedido.get("nota") or "Sin observaciones adicionales para este pedido.",
                ui.MUTED, ui.SOFT, ui.BORDER, ft.Icons.NOTE_ALT_OUTLINED,
            ),
        ],
        spacing=13,
    )

    app.show_dialog(ui._dialog_base(
        f"Pedido {_pid(pedido)}",
        f"{pedido.get('tipo_doc', '')} · {pedido.get('condicion', '')} · "
        "Moneda base USD",
        cuerpo,
        acciones,
        width=640,
        icono=ft.Icons.RECEIPT_LONG_OUTLINED,
        color=color,
        bg=bg,
    ))
